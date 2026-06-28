"""
HireWise AI — Tests: Integrity Detection
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from tests.synthetic_candidates import (
    HONEYPOT_PROFILE,
    KEYWORD_STUFFING_MARKETING,
    STRONG_RETRIEVAL_ENGINEER,
)
from src.integrity import analyse_integrity


def test_clean_profile_has_low_risk():
    ir = analyse_integrity(STRONG_RETRIEVAL_ENGINEER)
    assert ir.honeypot_risk == "low"
    assert ir.integrity_score >= 0.80


def test_honeypot_has_high_risk():
    ir = analyse_integrity(HONEYPOT_PROFILE)
    # Honeypot has signup_date AFTER last_active_date → should flag
    assert ir.honeypot_risk in ("medium", "high")
    assert ir.integrity_score < 0.80
    assert len(ir.integrity_flags) > 0


def test_signup_after_last_active_is_flagged():
    candidate = {
        "candidate_id": "CAND_9999001",
        "profile": {
            "anonymized_name": "Test",
            "headline": "Test",
            "summary": "Test",
            "location": "Pune",
            "country": "India",
            "years_of_experience": 5.0,
            "current_title": "Engineer",
            "current_company": "TestCo",
            "current_company_size": "51-200",
            "current_industry": "Technology",
        },
        "career_history": [
            {
                "company": "TestCo",
                "title": "Engineer",
                "start_date": "2020-01-01",
                "end_date": None,
                "duration_months": 60,
                "is_current": True,
                "industry": "Technology",
                "company_size": "51-200",
                "description": "Built production systems.",
            }
        ],
        "education": [],
        "skills": [],
        "redrob_signals": {
            "signup_date": "2026-01-01",        # AFTER last_active
            "last_active_date": "2025-01-01",   # BEFORE signup
            "open_to_work_flag": True,
            "profile_completeness_score": 80.0,
            "recruiter_response_rate": 0.5,
            "avg_response_time_hours": 24,
            "skill_assessment_scores": {},
            "notice_period_days": 30,
            "preferred_work_mode": "hybrid",
            "willing_to_relocate": True,
            "github_activity_score": 10,
            "interview_completion_rate": 0.8,
            "offer_acceptance_rate": -1,
            "verified_email": True,
            "verified_phone": True,
            "linkedin_connected": True,
        },
    }
    ir = analyse_integrity(candidate)
    flagged = any("signup_date" in f and "after" in f for f in ir.integrity_flags)
    assert flagged, f"Expected signup/last_active flag, got: {ir.integrity_flags}"


def test_keyword_stuffing_detected():
    ir = analyse_integrity(KEYWORD_STUFFING_MARKETING)
    # Should have integrity flags for stuffing
    stuffing_flag = any("keyword" in f.lower() or "expert" in f.lower() or "non-technical" in f.lower() for f in ir.integrity_flags)
    assert stuffing_flag or ir.integrity_score < 1.0


def test_current_role_with_end_date_flagged():
    candidate = {
        "candidate_id": "CAND_9999002",
        "profile": {
            "anonymized_name": "Test",
            "headline": "Engineer",
            "summary": "S",
            "location": "Delhi",
            "country": "India",
            "years_of_experience": 3.0,
            "current_title": "Engineer",
            "current_company": "Co",
            "current_company_size": "11-50",
            "current_industry": "Technology",
        },
        "career_history": [
            {
                "company": "Co",
                "title": "Engineer",
                "start_date": "2022-01-01",
                "end_date": "2024-01-01",   # Has end_date but is_current=True!
                "duration_months": 24,
                "is_current": True,
                "industry": "Technology",
                "company_size": "11-50",
                "description": "Built systems.",
            }
        ],
        "education": [],
        "skills": [],
        "redrob_signals": {
            "signup_date": "2023-01-01",
            "last_active_date": "2026-01-01",
            "open_to_work_flag": True,
            "profile_completeness_score": 60.0,
            "recruiter_response_rate": 0.5,
            "avg_response_time_hours": 24,
            "skill_assessment_scores": {},
            "notice_period_days": 30,
            "preferred_work_mode": "hybrid",
            "willing_to_relocate": True,
            "github_activity_score": -1,
            "interview_completion_rate": 0.5,
            "offer_acceptance_rate": -1,
            "verified_email": True,
            "verified_phone": False,
            "linkedin_connected": False,
        },
    }
    ir = analyse_integrity(candidate)
    flagged = any("current" in f.lower() and "end_date" in f for f in ir.integrity_flags)
    assert flagged, f"Expected current+end_date flag, got: {ir.integrity_flags}"


def test_integrity_score_bounded():
    for profile in [STRONG_RETRIEVAL_ENGINEER, HONEYPOT_PROFILE, KEYWORD_STUFFING_MARKETING]:
        ir = analyse_integrity(profile)
        assert 0.0 <= ir.integrity_score <= 1.0


def test_honeypot_risk_valid_values():
    for profile in [STRONG_RETRIEVAL_ENGINEER, HONEYPOT_PROFILE, KEYWORD_STUFFING_MARKETING]:
        ir = analyse_integrity(profile)
        assert ir.honeypot_risk in ("low", "medium", "high")
