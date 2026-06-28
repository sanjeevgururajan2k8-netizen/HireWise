"""
HireWise AI — Explainable Reasoning Generator
===============================================
Generates 1-2 sentence reasoning for each top-100 candidate.

Rules:
  - NO LLM calls — pure template-based generation from structured data
  - Every claim must trace back to candidate facts
  - Reasoning varies by candidate strength
  - Honest concerns are included when warranted
  - No invented companies, skills, or experience
"""

from __future__ import annotations

import random
from typing import Any

from config.scoring_config import RANDOM_SEED
from src.scoring import CandidateScore
from src.utils import get_logger, normalise_text, safe_float, safe_int

logger = get_logger("hirewise.reasoning")

# Seeded for reproducibility
_rng = random.Random(RANDOM_SEED)


# ---------------------------------------------------------------------------
# Helpers to extract facts from candidate data
# ---------------------------------------------------------------------------

def _get_years_exp(candidate: dict) -> float:
    return safe_float(candidate.get("profile", {}).get("years_of_experience"), 0.0)


def _get_current_title(candidate: dict) -> str:
    return candidate.get("profile", {}).get("current_title", "")


def _get_location(candidate: dict) -> str:
    loc = candidate.get("profile", {}).get("location", "")
    country = candidate.get("profile", {}).get("country", "")
    if loc and country and country.lower() != "india":
        return f"{loc}, {country}"
    return loc or country or "Unknown"


def _get_top_skills(candidate: dict, max_skills: int = 3) -> list[str]:
    """Return top skills by proficiency (expert > advanced > intermediate)."""
    skills = candidate.get("skills", [])
    order = {"expert": 0, "advanced": 1, "intermediate": 2, "beginner": 3}
    sorted_skills = sorted(
        [s for s in skills if isinstance(s, dict)],
        key=lambda s: (order.get(s.get("proficiency", "beginner"), 3), -safe_int(s.get("endorsements"), 0)),
    )
    return [s.get("name", "") for s in sorted_skills[:max_skills] if s.get("name")]


def _get_relevant_career_evidence(candidate: dict) -> list[str]:
    """Extract specific phrases from career descriptions that mention production work."""
    career = candidate.get("career_history", [])
    evidence: list[str] = []

    production_phrases = [
        "deployed", "built", "shipped", "designed", "scaled", "owned", "maintained",
        "elasticsearch", "faiss", "milvus", "qdrant", "pinecone", "vector",
        "retrieval", "search", "ranking", "recommendation", "ndcg", "mrr",
        "embedding", "sentence transformer", "lora", "peft", "fine-tun",
        "production", "inference", "serving",
    ]

    for role in career[:3]:  # Only look at recent 3 roles
        if not isinstance(role, dict):
            continue
        desc = normalise_text(role.get("description", ""))
        title = role.get("title", "")
        company = role.get("company", "")
        matched = [phrase for phrase in production_phrases if phrase in desc]
        if matched:
            evidence.append(f"{title} at {company} ({len(matched)} relevant signals: {', '.join(matched[:3])})")

    return evidence


def _get_recruiter_response(candidate: dict) -> float:
    return safe_float(candidate.get("redrob_signals", {}).get("recruiter_response_rate"), 0.0)


def _get_notice_period(candidate: dict) -> int:
    return safe_int(candidate.get("redrob_signals", {}).get("notice_period_days"), 0)


def _is_open_to_work(candidate: dict) -> bool:
    return bool(candidate.get("redrob_signals", {}).get("open_to_work_flag", False))


def _get_github_score(candidate: dict) -> float:
    return safe_float(candidate.get("redrob_signals", {}).get("github_activity_score"), -1.0)


def _get_company_info(candidate: dict) -> str:
    """Get current company and size for context."""
    profile = candidate.get("profile", {})
    company = profile.get("current_company", "")
    size = profile.get("current_company_size", "")
    return f"{company} ({size})" if company and size else company


# ---------------------------------------------------------------------------
# Reasoning templates per score band
# ---------------------------------------------------------------------------

def generate_reasoning(
    candidate: dict,
    score: CandidateScore,
    rank: int,
) -> str:
    """
    Generate 1-2 sentence factual reasoning for a candidate.

    Args:
        candidate: Full candidate dict.
        score: Complete scoring breakdown.
        rank: Final rank (1-100).

    Returns:
        1-2 sentence reasoning string.
    """
    yoe = _get_years_exp(candidate)
    title = _get_current_title(candidate)
    location = _get_location(candidate)
    top_skills = _get_top_skills(candidate, 3)
    evidence = _get_relevant_career_evidence(candidate)
    response_rate = _get_recruiter_response(candidate)
    notice = _get_notice_period(candidate)
    open_to_work = _is_open_to_work(candidate)
    github = _get_github_score(candidate)
    company_info = _get_company_info(candidate)
    final_score = score.final_score
    integrity_risk = score.honeypot_risk
    flags = score.integrity_flags

    parts: list[str] = []

    # --- Sentence 1: Core technical profile ---
    yoe_str = f"{yoe:.1f}" if yoe > 0 else "N/A"

    if evidence:
        # Has production evidence → mention it
        evid_summary = evidence[0]
        parts.append(
            f"{yoe_str} years of experience; role as '{title}' at {company_info} "
            f"includes production evidence ({evid_summary})."
        )
    elif score.feature_score >= 0.5:
        # Good feature scores but no explicit evidence phrase
        skill_str = ", ".join(top_skills) if top_skills else "relevant AI/ML skills"
        parts.append(
            f"{yoe_str} years of experience as '{title}'; demonstrates {skill_str} "
            f"with a technical feature score of {score.feature_score:.2f}."
        )
    elif score.lexical_score >= 0.3:
        skill_str = ", ".join(top_skills) if top_skills else "some relevant skills"
        parts.append(
            f"{yoe_str} years of experience as '{title}'; profile text shows relevance "
            f"({skill_str}) with lexical similarity score {score.lexical_score:.2f}."
        )
    else:
        skill_str = ", ".join(top_skills) if top_skills else "limited AI/ML skills"
        parts.append(
            f"{yoe_str} years of experience as '{title}'; limited direct evidence "
            f"for this role's core requirements ({skill_str})."
        )

    # --- Sentence 2: Engagement + concerns ---
    positives: list[str] = []
    concerns: list[str] = []

    if open_to_work:
        positives.append("actively open to work")
    if response_rate >= 0.70:
        positives.append(f"{int(response_rate*100)}% recruiter response rate")
    if github > 50:
        positives.append(f"strong GitHub activity score ({github:.0f}/100)")
    if notice <= 30:
        positives.append(f"immediate/short notice period ({notice} days)")

    if notice > 90:
        concerns.append(f"long notice period ({notice} days)")
    if response_rate < 0.20 and response_rate >= 0:
        concerns.append(f"low recruiter response rate ({int(response_rate*100)}%)")
    if integrity_risk == "high":
        concerns.append("high-risk integrity flags detected (see flag details)")
    elif integrity_risk == "medium":
        concerns.append("some profile integrity concerns flagged")
    if score.keyword_stuffing_penalty < 0.9:
        concerns.append("keyword-stuffing penalty applied")

    if positives or concerns:
        sentence2_parts: list[str] = []
        if positives:
            sentence2_parts.append(f"Positive signals: {'; '.join(positives)}.")
        if concerns:
            sentence2_parts.append(f"Concerns: {'; '.join(concerns)}.")
        parts.append(" ".join(sentence2_parts))

    # Add location note if relevant
    if "india" not in location.lower() and "pune" not in location.lower():
        parts.append(f"Based in {location}; relocation or remote compatibility should be confirmed.")

    return " ".join(parts)
