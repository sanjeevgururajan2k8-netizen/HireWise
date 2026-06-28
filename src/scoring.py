"""
HireWise AI — Final Scoring Engine
=====================================
Combines lexical scores, evidence features, behavioural modifier,
and integrity multiplier into a single deterministic final score.

Score formula:
  base = LEXICAL_WEIGHT * lexical_score + FEATURE_WEIGHT * weighted_feature_score
  final = base * behaviour_modifier * integrity_multiplier * stuffing_penalty

All weights are documented in config/scoring_config.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from config.scoring_config import (
    BEHAVIOUR_MODIFIER_MAX,
    BEHAVIOUR_MODIFIER_MIN,
    FEATURE_WEIGHT,
    INTEGRITY_PENALTY,
    KEYWORD_STUFFING_PENALTY,
    LEXICAL_WEIGHT,
    SCORE_WEIGHTS,
    TOP_N,
)
from src.behaviour import compute_behaviour_modifier, compute_behaviour_score_normalised
from src.feature_engineering import FeatureScores
from src.integrity import IntegrityResult
from src.utils import clamp, get_logger

logger = get_logger("hirewise.scoring")


@dataclass
class CandidateScore:
    """Complete scoring breakdown for a single candidate."""

    candidate_id: str
    lexical_score: float = 0.0
    feature_score: float = 0.0          # Weighted combination of evidence features
    behaviour_modifier: float = 1.0
    behaviour_score: float = 0.0        # Normalised [0,1] for display
    integrity_score: float = 1.0
    honeypot_risk: str = "low"
    integrity_flags: list[str] = field(default_factory=list)
    keyword_stuffing_penalty: float = 1.0
    final_score: float = 0.0
    features: dict[str, float] = field(default_factory=dict)

    # For tie-breaking (stored separately, not part of the final score)
    production_evidence: float = 0.0
    availability: float = 0.0


def compute_weighted_feature_score(fs: FeatureScores) -> float:
    """
    Combine named feature scores using weights from SCORE_WEIGHTS.

    Args:
        fs: FeatureScores dataclass.

    Returns:
        Weighted sum in [0, 1].
    """
    total_weight = sum(SCORE_WEIGHTS.values())
    raw_score = 0.0
    for feat_name, weight in SCORE_WEIGHTS.items():
        value = getattr(fs, feat_name, 0.0)
        raw_score += weight * value

    # Normalise by total weight (in case weights don't sum to exactly 1.0)
    return clamp(raw_score / total_weight if total_weight > 0 else 0.0, 0.0, 1.0)


def score_candidate(
    candidate: dict,
    lexical_score: float,
    features: FeatureScores,
    integrity: IntegrityResult,
) -> CandidateScore:
    """
    Compute the final score for a single candidate.

    Args:
        candidate: Validated candidate dict.
        lexical_score: TF-IDF cosine similarity score.
        features: Named evidence feature scores.
        integrity: Profile integrity analysis result.

    Returns:
        CandidateScore with all components and final score.
    """
    cid = candidate.get("candidate_id", "")

    # 1. Weighted feature score from named evidence
    feature_score = compute_weighted_feature_score(features)

    # 2. Blend lexical and feature scores
    base_score = (LEXICAL_WEIGHT * lexical_score) + (FEATURE_WEIGHT * feature_score)

    # 3. Behavioural modifier
    beh_modifier = compute_behaviour_modifier(candidate)
    beh_score = compute_behaviour_score_normalised(candidate)

    # 4. Integrity multiplier
    integrity_mult = INTEGRITY_PENALTY.get(integrity.honeypot_risk, 1.0)

    # 5. Keyword stuffing penalty
    stuffing_penalty = features.keyword_stuffing_penalty

    # 6. Final score
    final = base_score * beh_modifier * integrity_mult * stuffing_penalty
    final = clamp(final, 0.0, 1.0)

    return CandidateScore(
        candidate_id=cid,
        lexical_score=lexical_score,
        feature_score=feature_score,
        behaviour_modifier=beh_modifier,
        behaviour_score=beh_score,
        integrity_score=integrity.integrity_score,
        honeypot_risk=integrity.honeypot_risk,
        integrity_flags=integrity.integrity_flags,
        keyword_stuffing_penalty=stuffing_penalty,
        final_score=final,
        features=features.as_dict(),
        production_evidence=features.retrieval_production_score,
        availability=beh_score,
    )


def rank_candidates(scores: list[CandidateScore]) -> list[CandidateScore]:
    """
    Sort candidates by final score with deterministic tie-breaking.

    Tie-breaking order (descending):
      1. Higher integrity_score
      2. Higher production_evidence (retrieval_production_score)
      3. Higher behaviour_score (availability)
      4. candidate_id ascending (lexicographic)

    Args:
        scores: List of CandidateScore objects.

    Returns:
        Sorted list (highest score first).
    """
    sorted_scores = sorted(
        scores,
        key=lambda cs: (
            cs.final_score,
            cs.integrity_score,
            cs.production_evidence,
            cs.availability,
            # Invert candidate_id for ascending tie-break
            tuple(-ord(c) for c in cs.candidate_id),
        ),
        reverse=True,
    )
    return sorted_scores


def select_top_n(scores: list[CandidateScore], n: int = TOP_N) -> list[CandidateScore]:
    """Select exactly the top N candidates."""
    ranked = rank_candidates(scores)
    return ranked[:n]


def normalise_final_scores(scores: list[CandidateScore]) -> list[CandidateScore]:
    """
    Normalise final scores so that rank 1 is highest and scores are monotonically
    non-increasing. Preserves relative ordering.

    Args:
        scores: Already-ranked CandidateScore list (highest first).

    Returns:
        Same list with scores normalised to [0, 1] monotonically.
    """
    if not scores:
        return scores

    max_score = scores[0].final_score
    min_score = scores[-1].final_score

    if max_score == min_score:
        # All equal: assign evenly spaced values
        for i, cs in enumerate(scores):
            cs.final_score = 1.0 - (i / max(len(scores) - 1, 1)) * 0.5
        return scores

    for i, cs in enumerate(scores):
        # Normalise but ensure monotonically non-increasing
        normalised = (cs.final_score - min_score) / (max_score - min_score)
        cs.final_score = clamp(normalised, 0.0, 1.0)

    # Enforce monotonically non-increasing
    for i in range(1, len(scores)):
        if scores[i].final_score > scores[i - 1].final_score:
            scores[i].final_score = scores[i - 1].final_score

    return scores
