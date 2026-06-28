"""
HireWise AI — Tests: Scoring
Tests determinism, ordering, and production engineer > keyword stuffer.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from tests.synthetic_candidates import (
    HONEYPOT_PROFILE,
    INACTIVE_STRONG_TECHNICAL,
    KEYWORD_STUFFING_MARKETING,
    PRODUCT_RETRIEVAL_ENGINEER,
    PURE_ACADEMIC,
    STRONG_RETRIEVAL_ENGINEER,
    ALL_SYNTHETIC_CANDIDATES,
)
from src.feature_engineering import compute_features
from src.integrity import analyse_integrity
from src.lexical_ranker import LexicalRanker
from src.scoring import (
    CandidateScore,
    normalise_final_scores,
    rank_candidates,
    score_candidate,
    select_top_n,
)
from src.text_builder import build_candidate_text, build_weighted_corpus_string

JOB_TEXT = """
Senior AI Engineer. Requirements: Production Python, Elasticsearch, FAISS, vector search,
embedding retrieval, NDCG evaluation, ranking systems, learning to rank, production ML deployment,
sentence transformers, information retrieval, recommendation systems.
"""


def _score_candidate(cand: dict) -> CandidateScore:
    text_fields = build_candidate_text(cand)
    corpus_text = build_weighted_corpus_string(text_fields)

    ranker = LexicalRanker()
    lexical_scores = ranker.fit_transform(
        [cand["candidate_id"]],
        [corpus_text],
        JOB_TEXT,
    )
    features = compute_features(cand)
    integrity = analyse_integrity(cand)
    return score_candidate(
        candidate=cand,
        lexical_score=lexical_scores[cand["candidate_id"]],
        features=features,
        integrity=integrity,
    )


def _score_all(candidates: list[dict]) -> list[CandidateScore]:
    ids = [c["candidate_id"] for c in candidates]
    corpus = [build_weighted_corpus_string(build_candidate_text(c)) for c in candidates]
    ranker = LexicalRanker()
    lexical_scores = ranker.fit_transform(ids, corpus, JOB_TEXT)

    scores = []
    for cand in candidates:
        cid = cand["candidate_id"]
        fs = compute_features(cand)
        ir = analyse_integrity(cand)
        cs = score_candidate(
            candidate=cand,
            lexical_score=lexical_scores[cid],
            features=fs,
            integrity=ir,
        )
        scores.append(cs)
    return scores


def test_production_retrieval_engineer_ranks_above_keyword_stuffer():
    """Core requirement: genuine engineer > keyword stuffer."""
    scores = _score_all([STRONG_RETRIEVAL_ENGINEER, KEYWORD_STUFFING_MARKETING])
    ranked = rank_candidates(scores)
    top_id = ranked[0].candidate_id
    assert top_id == STRONG_RETRIEVAL_ENGINEER["candidate_id"], (
        f"Expected STRONG_RETRIEVAL_ENGINEER to rank first, got {top_id}. "
        f"Scores: {[(cs.candidate_id, cs.final_score) for cs in ranked]}"
    )


def test_keyword_stuffing_penalty_applied():
    """Keyword stuffer should receive a penalty < 1.0."""
    features = compute_features(KEYWORD_STUFFING_MARKETING)
    assert features.keyword_stuffing_penalty < 1.0, (
        f"Expected stuffing penalty, got {features.keyword_stuffing_penalty}"
    )


def test_honeypot_has_lower_final_score():
    """Honeypot should score lower than the genuine engineer."""
    scores = _score_all([STRONG_RETRIEVAL_ENGINEER, HONEYPOT_PROFILE])
    score_map = {cs.candidate_id: cs.final_score for cs in scores}
    assert score_map[STRONG_RETRIEVAL_ENGINEER["candidate_id"]] > score_map[HONEYPOT_PROFILE["candidate_id"]]


def test_scores_are_deterministic():
    """Running the scorer twice produces the same results."""
    scores1 = _score_all(ALL_SYNTHETIC_CANDIDATES)
    scores2 = _score_all(ALL_SYNTHETIC_CANDIDATES)
    for cs1, cs2 in zip(
        sorted(scores1, key=lambda x: x.candidate_id),
        sorted(scores2, key=lambda x: x.candidate_id),
    ):
        assert abs(cs1.final_score - cs2.final_score) < 1e-9, f"Non-deterministic: {cs1.candidate_id}"


def test_scores_bounded_zero_to_one():
    """All final scores must be in [0, 1]."""
    scores = _score_all(ALL_SYNTHETIC_CANDIDATES)
    for cs in scores:
        assert 0.0 <= cs.final_score <= 1.0, f"{cs.candidate_id}: score={cs.final_score}"


def test_rank_candidates_no_duplicates():
    """No duplicate candidate IDs in output."""
    scores = _score_all(ALL_SYNTHETIC_CANDIDATES)
    ranked = rank_candidates(scores)
    ids = [cs.candidate_id for cs in ranked]
    assert len(ids) == len(set(ids)), "Duplicate candidate IDs in ranking"


def test_select_top_n_exact_count():
    """select_top_n returns exactly N candidates."""
    scores = _score_all(ALL_SYNTHETIC_CANDIDATES)
    top2 = select_top_n(scores, n=2)
    assert len(top2) == 2


def test_normalise_final_scores_monotonic():
    """Normalised scores must be monotonically non-increasing."""
    scores = _score_all(ALL_SYNTHETIC_CANDIDATES)
    ranked = rank_candidates(scores)
    normalised = normalise_final_scores(ranked)
    for i in range(1, len(normalised)):
        assert normalised[i].final_score <= normalised[i - 1].final_score + 1e-9, (
            f"Non-monotonic at index {i}: {normalised[i].final_score} > {normalised[i-1].final_score}"
        )


def test_experience_fit_score_optimal_range():
    """Experience 5-9 years should score 1.0."""
    from src.feature_engineering import _experience_score
    for yoe in [5.0, 6.5, 7.0, 8.0, 9.0]:
        score = _experience_score(yoe)
        assert score == 1.0, f"Expected 1.0 for yoe={yoe}, got {score}"


def test_experience_fit_score_low_for_very_junior():
    from src.feature_engineering import _experience_score
    score = _experience_score(0.5)
    assert score < 0.3, f"Expected low score for 0.5 yoe, got {score}"


def test_behaviour_modifier_within_bounds():
    from src.behaviour import compute_behaviour_modifier
    from config.scoring_config import BEHAVIOUR_MODIFIER_MIN, BEHAVIOUR_MODIFIER_MAX
    for cand in ALL_SYNTHETIC_CANDIDATES:
        mod = compute_behaviour_modifier(cand)
        assert BEHAVIOUR_MODIFIER_MIN <= mod <= BEHAVIOUR_MODIFIER_MAX, (
            f"{cand['candidate_id']}: modifier {mod} out of bounds"
        )
