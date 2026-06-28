"""
HireWise AI — Optional Semantic Ranker
========================================
Loads precomputed float16 embeddings produced by precompute.py.
When embeddings are unavailable, this module gracefully returns None
and the system falls back to TF-IDF + evidence features.

No network calls are made. No models are loaded during ranking
(only precomputed .npy arrays are read).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import numpy as np

from config.scoring_config import EMBEDDINGS_IDS_PATH, EMBEDDINGS_PATH
from src.utils import get_logger

logger = get_logger("hirewise.semantic_ranker")


def load_precomputed_embeddings(
    embeddings_path: str = EMBEDDINGS_PATH,
    ids_path: str = EMBEDDINGS_IDS_PATH,
) -> tuple[Optional[np.ndarray], Optional[list[str]]]:
    """
    Load precomputed candidate embeddings from disk.

    Args:
        embeddings_path: Path to the .npy file (float16 array, shape [N, D]).
        ids_path: Path to the JSON file containing ordered candidate IDs.

    Returns:
        Tuple of (embeddings_array, candidate_ids) or (None, None) if
        files do not exist.
    """
    emb_path = Path(embeddings_path)
    ids_path_obj = Path(ids_path)

    if not emb_path.exists():
        logger.info("No precomputed embeddings found at %s", emb_path)
        return None, None

    if not ids_path_obj.exists():
        logger.warning("Embeddings file found but IDs file missing: %s", ids_path_obj)
        return None, None

    try:
        embeddings = np.load(str(emb_path)).astype(np.float32)
        with open(ids_path_obj, "r", encoding="utf-8") as f:
            candidate_ids = json.load(f)

        if embeddings.shape[0] != len(candidate_ids):
            logger.error(
                "Embedding count (%d) does not match ID count (%d)",
                embeddings.shape[0],
                len(candidate_ids),
            )
            return None, None

        logger.info(
            "Loaded precomputed embeddings: %d candidates, dim=%d",
            embeddings.shape[0],
            embeddings.shape[1],
        )
        return embeddings, candidate_ids

    except Exception as exc:
        logger.error("Failed to load precomputed embeddings: %s", exc)
        return None, None


def compute_semantic_scores(
    candidate_ids: list[str],
    embeddings: np.ndarray,
    embedding_id_map: dict[str, int],
    job_embedding: np.ndarray,
) -> dict[str, float]:
    """
    Compute cosine similarity between each candidate embedding and the job embedding.

    Args:
        candidate_ids: IDs to score (subset of precomputed IDs).
        embeddings: Full precomputed embedding matrix [N, D].
        embedding_id_map: Dict mapping candidate_id → row index in embeddings.
        job_embedding: Job description embedding vector [D].

    Returns:
        Dict mapping candidate_id → semantic_score in [0, 1].
    """
    job_norm = job_embedding / (np.linalg.norm(job_embedding) + 1e-10)

    scores: dict[str, float] = {}
    for cid in candidate_ids:
        idx = embedding_id_map.get(cid)
        if idx is None:
            scores[cid] = 0.0
            continue
        emb = embeddings[idx]
        emb_norm = emb / (np.linalg.norm(emb) + 1e-10)
        sim = float(np.dot(emb_norm, job_norm))
        scores[cid] = max(0.0, sim)  # Cosine similarity is in [-1, 1], clip to [0, 1]

    return scores


def semantic_rerank(
    candidate_ids: list[str],
    existing_scores: dict[str, float],
    embeddings_path: str = EMBEDDINGS_PATH,
    ids_path: str = EMBEDDINGS_IDS_PATH,
    job_embedding: Optional[np.ndarray] = None,
    blend_weight: float = 0.30,
) -> dict[str, float]:
    """
    Blend precomputed semantic scores into existing scores (optional step).

    If embeddings are unavailable or job_embedding is None, returns
    existing_scores unchanged.

    Args:
        candidate_ids: List of candidate IDs to re-rank.
        existing_scores: Dict of candidate_id → current score.
        embeddings_path: Path to precomputed embeddings.
        ids_path: Path to precomputed embedding IDs.
        job_embedding: Job description embedding vector.
        blend_weight: Weight of semantic score (existing gets 1-blend_weight).

    Returns:
        Dict of candidate_id → blended score.
    """
    if job_embedding is None:
        logger.info("No job embedding provided; skipping semantic reranking")
        return existing_scores

    embeddings, emb_ids = load_precomputed_embeddings(embeddings_path, ids_path)
    if embeddings is None or emb_ids is None:
        return existing_scores

    embedding_id_map = {cid: i for i, cid in enumerate(emb_ids)}
    semantic_scores = compute_semantic_scores(
        candidate_ids, embeddings, embedding_id_map, job_embedding
    )

    blended: dict[str, float] = {}
    for cid in candidate_ids:
        base = existing_scores.get(cid, 0.0)
        sem = semantic_scores.get(cid, 0.0)
        blended[cid] = (1.0 - blend_weight) * base + blend_weight * sem

    logger.info("Semantic reranking applied with blend_weight=%.2f", blend_weight)
    return blended
