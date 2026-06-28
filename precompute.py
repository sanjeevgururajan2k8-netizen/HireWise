"""
HireWise AI — Offline Semantic Embedding Precomputation
=========================================================
Run this ONCE before ranking to precompute candidate embeddings.
The ranking pipeline (rank.py) will load these embeddings when available.

Usage:
  python precompute.py --candidates ./candidates.jsonl --out ./artifacts/

Requirements:
  - sentence-transformers installed: pip install sentence-transformers
  - Enough RAM to hold all embeddings (float16, ~80MB for 100K candidates at dim=384)
  - No network calls during ranking (model must be cached locally)

Notes:
  - This step is OPTIONAL. rank.py works without it using TF-IDF only.
  - Precomputation is separate from the timed ranking step.
  - Embeddings stored as float16 to save disk space.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))

from config.scoring_config import (
    DEFAULT_CANDIDATES_JSONL,
    EMBEDDINGS_IDS_PATH,
    EMBEDDINGS_PATH,
)
from src.loaders import stream_candidates
from src.text_builder import build_candidate_text, build_weighted_corpus_string
from src.utils import get_logger, normalise_text

logger = get_logger("hirewise.precompute")

MODEL_NAME = "all-MiniLM-L6-v2"
BATCH_SIZE = 256


def precompute_embeddings(
    candidates_path: str,
    output_dir: str = "artifacts",
    model_name: str = MODEL_NAME,
    batch_size: int = BATCH_SIZE,
) -> None:
    """
    Precompute candidate embeddings and save as float16 numpy arrays.

    Args:
        candidates_path: Path to candidates file (.json, .jsonl, .jsonl.gz).
        output_dir: Directory to save embeddings.
        model_name: Sentence Transformer model name.
        batch_size: Embedding batch size.
    """
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
    except ImportError:
        logger.error("sentence-transformers not installed. Run: pip install sentence-transformers")
        sys.exit(1)

    logger.info("Loading model: %s", model_name)
    model = SentenceTransformer(model_name)

    logger.info("Streaming candidates from: %s", candidates_path)
    start = time.perf_counter()

    texts: list[str] = []
    ids: list[str] = []

    for i, cand in enumerate(stream_candidates(candidates_path)):
        cid = cand.get("candidate_id", "")
        if not cid:
            continue
        text_fields = build_candidate_text(cand)
        weighted_text = build_weighted_corpus_string(text_fields)
        texts.append(normalise_text(weighted_text)[:2048])  # Truncate for embedding
        ids.append(cid)

        if (i + 1) % 10_000 == 0:
            logger.info("  Loaded %d candidates for embedding...", i + 1)

    logger.info("Encoding %d candidates in batches of %d...", len(texts), batch_size)
    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    # Convert to float16 for storage efficiency
    embeddings_f16 = embeddings.astype(np.float16)

    # Save
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    emb_path = out_dir / Path(EMBEDDINGS_PATH).name
    ids_path = out_dir / Path(EMBEDDINGS_IDS_PATH).name

    np.save(str(emb_path), embeddings_f16)
    with open(ids_path, "w", encoding="utf-8") as f:
        json.dump(ids, f)

    elapsed = time.perf_counter() - start
    size_mb = emb_path.stat().st_size / (1024 * 1024)

    logger.info("Embeddings saved: %s (%.1f MB, %d candidates, dim=%d)", emb_path, size_mb, len(ids), embeddings.shape[1])
    logger.info("IDs saved: %s", ids_path)
    logger.info("Precomputation complete in %.1f seconds", elapsed)


def main() -> None:
    parser = argparse.ArgumentParser(description="Precompute candidate embeddings")
    parser.add_argument("--candidates", default=DEFAULT_CANDIDATES_JSONL, help="Candidates file path")
    parser.add_argument("--out", default="artifacts", help="Output directory")
    parser.add_argument("--model", default=MODEL_NAME, help="Sentence Transformer model name")
    parser.add_argument("--batch-size", type=int, default=BATCH_SIZE, help="Batch size")
    args = parser.parse_args()

    precompute_embeddings(
        candidates_path=args.candidates,
        output_dir=args.out,
        model_name=args.model,
        batch_size=args.batch_size,
    )


if __name__ == "__main__":
    main()
