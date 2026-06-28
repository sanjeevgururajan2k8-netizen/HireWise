"""
HireWise AI — Tests: Reasoning
Tests that reasoning uses only candidate facts and varies per candidate.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from tests.synthetic_candidates import (
    STRONG_RETRIEVAL_ENGINEER,
    KEYWORD_STUFFING_MARKETING,
    HONEYPOT_PROFILE,
)
from src.reasoning import generate_reasoning
from src.feature_engineering import compute_features
from src.integrity import analyse_integrity
from src.lexical_ranker import LexicalRanker
from src.scoring import CandidateScore, score_candidate
from src.text_builder import build_candidate_text, build_weighted_corpus_string

JOB_TEXT = "Senior AI Engineer, Elasticsearch, FAISS, vector search, Python, NDCG, production ML"

INVENTED_NAMES = ["Google", "Amazon", "Facebook", "Microsoft", "OpenAI", "DeepMind"]
INVENTED_SKILLS = ["Kubernetes wizardry", "TensorFlow magic", "Quantum ML"]


def _make_score(cand: dict, rank: int = 1) -> tuple[CandidateScore, str]:
    corpus = build_weighted_corpus_string(build_candidate_text(cand))
    ranker = LexicalRanker()
    lex = ranker.fit_transform([cand["candidate_id"]], [corpus], JOB_TEXT)
    fs = compute_features(cand)
    ir = analyse_integrity(cand)
    cs = score_candidate(cand, lexical_score=lex[cand["candidate_id"]], features=fs, integrity=ir)
    reasoning = generate_reasoning(cand, cs, rank)
    return cs, reasoning


def test_reasoning_not_empty():
    _, r = _make_score(STRONG_RETRIEVAL_ENGINEER, rank=1)
    assert len(r) > 20, f"Reasoning too short: '{r}'"


def test_reasoning_mentions_candidate_title():
    cand = STRONG_RETRIEVAL_ENGINEER
    _, r = _make_score(cand, rank=1)
    title = cand["profile"]["current_title"]
    assert title in r, f"Expected title '{title}' in reasoning: '{r}'"


def test_reasoning_mentions_years_of_experience():
    cand = STRONG_RETRIEVAL_ENGINEER
    _, r = _make_score(cand, rank=1)
    yoe = str(cand["profile"]["years_of_experience"])
    assert yoe in r, f"Expected yoe '{yoe}' in reasoning: '{r}'"


def test_reasoning_does_not_invent_companies():
    cand = KEYWORD_STUFFING_MARKETING
    _, r = _make_score(cand, rank=50)
    for name in INVENTED_NAMES:
        assert name not in r, f"Invented company '{name}' found in reasoning: '{r}'"


def test_reasoning_does_not_invent_skills():
    cand = STRONG_RETRIEVAL_ENGINEER
    _, r = _make_score(cand, rank=1)
    for skill in INVENTED_SKILLS:
        assert skill not in r, f"Invented skill '{skill}' found in reasoning: '{r}'"


def test_reasoning_varies_between_candidates():
    _, r1 = _make_score(STRONG_RETRIEVAL_ENGINEER, rank=1)
    _, r2 = _make_score(KEYWORD_STUFFING_MARKETING, rank=50)
    assert r1 != r2, "Reasoning should differ between different candidates"


def test_honeypot_reasoning_mentions_concern():
    cand = HONEYPOT_PROFILE
    _, r = _make_score(cand, rank=80)
    # Should mention integrity concern or risk
    concern_words = ["concern", "risk", "flag", "integrity", "penalty", "suspicious"]
    has_concern = any(word in r.lower() for word in concern_words)
    assert has_concern, f"Expected integrity concern in honeypot reasoning: '{r}'"


def test_reasoning_is_deterministic():
    """Same inputs → same reasoning."""
    _, r1 = _make_score(STRONG_RETRIEVAL_ENGINEER, rank=1)
    _, r2 = _make_score(STRONG_RETRIEVAL_ENGINEER, rank=1)
    assert r1 == r2, "Reasoning should be deterministic"
