"""
HireWise AI — Lexical Ranker (TF-IDF + Synonym Map)
=====================================================
CPU-efficient text relevance scorer using:
  - TF-IDF with word and character n-grams
  - Cosine similarity
  - Synonym expansion before vectorisation
"""

from __future__ import annotations

import re
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from config.scoring_config import SYNONYM_MAP
from src.utils import get_logger, normalise_text

logger = get_logger("hirewise.lexical_ranker")


# ---------------------------------------------------------------------------
# Synonym expansion
# ---------------------------------------------------------------------------

def _build_synonym_expansion_map() -> dict[str, str]:
    """
    Build a flat synonym→canonical mapping for fast text substitution.

    Returns:
        Dict of synonym_phrase → canonical_phrase.
    """
    expansion: dict[str, str] = {}
    for canonical, synonyms in SYNONYM_MAP.items():
        for syn in synonyms:
            expansion[syn.lower()] = canonical.lower()
    return expansion


_SYNONYM_EXPANSION = _build_synonym_expansion_map()

# Sort by length descending so longer phrases match before shorter ones
_SORTED_SYNONYMS = sorted(_SYNONYM_EXPANSION.keys(), key=len, reverse=True)


def expand_synonyms(text: str) -> str:
    """
    Replace synonym phrases in text with their canonical forms.

    This ensures that "faiss" and "milvus" both become "vector database",
    boosting TF-IDF similarity when the job description uses one term
    and the candidate uses another.

    Args:
        text: Normalised (lowercase) text.

    Returns:
        Text with synonyms replaced by canonical forms.
    """
    for syn in _SORTED_SYNONYMS:
        pattern = re.escape(syn)
        # Use word boundary for single words, no boundary for phrases
        if " " in syn:
            text = re.sub(pattern, _SYNONYM_EXPANSION[syn], text)
        else:
            text = re.sub(rf"\b{pattern}\b", _SYNONYM_EXPANSION[syn], text)
    return text


# ---------------------------------------------------------------------------
# TF-IDF Ranker
# ---------------------------------------------------------------------------

class LexicalRanker:
    """
    Fits a TF-IDF vectoriser on the candidate corpus plus job description,
    then computes cosine similarity of each candidate against the job.
    """

    def __init__(self) -> None:
        # Word n-grams (1-3) + character n-grams (3-5) for robustness
        self._word_vectorizer = TfidfVectorizer(
            analyzer="word",
            ngram_range=(1, 3),
            min_df=1,
            max_df=0.95,
            sublinear_tf=True,
            strip_accents="unicode",
            token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z0-9/_\-\.]{1,}\b",
        )
        self._char_vectorizer = TfidfVectorizer(
            analyzer="char_wb",
            ngram_range=(3, 5),
            min_df=2,
            max_df=0.95,
            sublinear_tf=True,
            strip_accents="unicode",
        )
        self._fitted = False

    def fit_transform(
        self,
        candidate_ids: list[str],
        corpus: list[str],
        job_text: str,
    ) -> dict[str, float]:
        """
        Fit TF-IDF on all texts and compute similarity scores.

        Args:
            candidate_ids: List of candidate IDs (same order as corpus).
            corpus: List of weighted corpus strings per candidate.
            job_text: Job description text (the query).

        Returns:
            Dict mapping candidate_id → lexical_score in [0, 1].
        """
        logger.info("Fitting TF-IDF on %d candidates + job description", len(corpus))

        # Apply synonym expansion to all texts
        expanded_corpus = [expand_synonyms(normalise_text(t)) for t in corpus]
        expanded_job = expand_synonyms(normalise_text(job_text))

        all_texts = expanded_corpus + [expanded_job]

        # Word n-grams
        try:
            word_matrix = self._word_vectorizer.fit_transform(all_texts)
            word_candidate_vecs = word_matrix[:-1]
            word_job_vec = word_matrix[-1]
            word_sims = cosine_similarity(word_candidate_vecs, word_job_vec).flatten()
        except Exception as exc:
            logger.warning("Word TF-IDF failed: %s — using zeros", exc)
            word_sims = np.zeros(len(corpus))

        # Char n-grams (only if corpus is large enough)
        try:
            if len(all_texts) >= 3:
                char_matrix = self._char_vectorizer.fit_transform(all_texts)
                char_candidate_vecs = char_matrix[:-1]
                char_job_vec = char_matrix[-1]
                char_sims = cosine_similarity(char_candidate_vecs, char_job_vec).flatten()
            else:
                char_sims = np.zeros(len(corpus))
        except Exception as exc:
            logger.warning("Char TF-IDF failed: %s — using zeros", exc)
            char_sims = np.zeros(len(corpus))

        # Blend word (70%) and char (30%) similarity
        blended = 0.70 * word_sims + 0.30 * char_sims

        # Normalise to [0, 1]
        max_val = blended.max()
        if max_val > 0:
            blended = blended / max_val

        self._fitted = True

        scores: dict[str, float] = {}
        for cid, score in zip(candidate_ids, blended):
            scores[cid] = float(np.clip(score, 0.0, 1.0))

        logger.info(
            "TF-IDF scoring complete. Top score: %.4f, Mean: %.4f",
            blended.max(),
            blended.mean(),
        )
        return scores
