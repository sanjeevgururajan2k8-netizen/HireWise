"""
HireWise AI — Evidence-Based Feature Engineering
==================================================
Computes 15 named feature scores per candidate, each normalised to [0, 1].

Key design principles:
  - Production evidence requires ACTION VERBS (built, deployed, shipped, etc.)
  - A skill list entry alone does NOT count as production evidence
  - Career description text carries the most weight
  - Recency is considered: older experience decays slightly
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from config.scoring_config import (
    EXPERIENCE_ABSOLUTE_MIN,
    EXPERIENCE_OPTIMAL_MAX,
    EXPERIENCE_OPTIMAL_MIN,
    IRRELEVANT_SKILL_DOMAINS,
    KEYWORD_STUFFING_PENALTY,
    KEYWORD_STUFFING_THRESHOLD,
    LEARNING_TO_RANK_KEYWORDS,
    LLM_FINETUNE_KEYWORDS,
    ML_PRODUCTION_KEYWORDS,
    NLP_IR_KEYWORDS,
    PREFERRED_LOCATIONS,
    PRODUCTION_ACTION_VERBS,
    PRODUCT_SHIPPING_KEYWORDS,
    PYTHON_KEYWORDS,
    RANKING_EVAL_KEYWORDS,
    RECENT_CODING_KEYWORDS,
    RETRIEVAL_KEYWORDS,
    STARTUP_KEYWORDS,
    VECTOR_SEARCH_KEYWORDS,
)
from src.utils import (
    clamp,
    count_keyword_hits,
    get_logger,
    keyword_in_text,
    normalise_text,
    parse_date,
    safe_bool,
    safe_float,
    safe_int,
)

logger = get_logger("hirewise.features")

TODAY: date = date.today()


@dataclass
class FeatureScores:
    """Container for all named feature scores for a candidate."""

    candidate_id: str
    retrieval_production_score: float = 0.0
    vector_search_score: float = 0.0
    ranking_evaluation_score: float = 0.0
    python_engineering_score: float = 0.0
    ml_production_score: float = 0.0
    product_shipping_score: float = 0.0
    startup_ownership_score: float = 0.0
    recent_coding_score: float = 0.0
    llm_finetuning_score: float = 0.0
    learning_to_rank_score: float = 0.0
    nlp_ir_relevance_score: float = 0.0
    experience_fit_score: float = 0.0
    location_relocation_score: float = 0.0
    behaviour_availability_score: float = 0.0
    profile_integrity_score: float = 1.0
    keyword_stuffing_penalty: float = 1.0  # multiplier (1.0 = no penalty)

    def as_dict(self) -> dict[str, float]:
        return {
            "retrieval_production_score": self.retrieval_production_score,
            "vector_search_score": self.vector_search_score,
            "ranking_evaluation_score": self.ranking_evaluation_score,
            "python_engineering_score": self.python_engineering_score,
            "ml_production_score": self.ml_production_score,
            "product_shipping_score": self.product_shipping_score,
            "startup_ownership_score": self.startup_ownership_score,
            "recent_coding_score": self.recent_coding_score,
            "llm_finetuning_score": self.llm_finetuning_score,
            "learning_to_rank_score": self.learning_to_rank_score,
            "nlp_ir_relevance_score": self.nlp_ir_relevance_score,
            "experience_fit_score": self.experience_fit_score,
            "location_relocation_score": self.location_relocation_score,
            "behaviour_availability_score": self.behaviour_availability_score,
            "profile_integrity_score": self.profile_integrity_score,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _has_production_evidence(text: str, keywords: list[str]) -> float:
    """
    Score production evidence for given keywords in a text block.

    Requires both:
      1. At least one keyword appears in the text
      2. At least one production action verb appears nearby

    Returns a score in [0, 1].
    """
    text_lower = text.lower()
    keyword_hits = count_keyword_hits(keywords, text_lower)
    if keyword_hits == 0:
        return 0.0

    verb_hits = count_keyword_hits(PRODUCTION_ACTION_VERBS, text_lower)
    if verb_hits == 0:
        # Keywords present but no action verbs → lower score
        return clamp(keyword_hits * 0.05, 0.0, 0.25)

    # Both present: score based on density
    raw = (keyword_hits * 0.15) + (verb_hits * 0.05)
    return clamp(raw, 0.0, 1.0)


def _skill_score(skills: list[dict], keywords: list[str]) -> float:
    """
    Score based on skill entries matching keywords.
    Advanced/expert skills with duration are stronger signals.
    """
    score = 0.0
    for skill in skills:
        if not isinstance(skill, dict):
            continue
        name = normalise_text(skill.get("name", ""))
        prof = skill.get("proficiency", "beginner")
        dur = safe_int(skill.get("duration_months"), 0)
        endr = safe_int(skill.get("endorsements"), 0)

        if any(kw.lower() in name for kw in keywords):
            prof_mult = {"expert": 1.0, "advanced": 0.75, "intermediate": 0.5, "beginner": 0.25}.get(
                prof, 0.25
            )
            dur_mult = clamp(dur / 24.0, 0.0, 1.0)  # 24 months = full credit
            endr_mult = clamp(endr / 20.0, 0.0, 0.5)
            score += 0.1 * prof_mult * (0.5 + 0.3 * dur_mult + 0.2 * endr_mult)

    return clamp(score, 0.0, 0.4)  # Skills alone capped at 0.4


def _recency_decay(start_date_str: str | None, weight: float = 0.3) -> float:
    """
    Return a decay factor (0–1) based on how recent a role started.
    More recent = higher decay factor. Default weight controls decay rate.
    """
    start = parse_date(start_date_str)
    if not start:
        return 0.7  # Unknown date: neutral
    months_ago = max(0, int((TODAY - start).days / 30.44))
    # Roles started within 24 months = 1.0, decays over 5 years to ~0.5
    decay = 1.0 - weight * math.log1p(months_ago / 12) / math.log1p(60 / 12)
    return clamp(decay, 0.4, 1.0)


def _build_all_career_text(career: list[dict]) -> str:
    """Concatenate all career descriptions and titles."""
    parts = []
    for role in career:
        if isinstance(role, dict):
            parts.append(normalise_text(role.get("title", "")))
            parts.append(normalise_text(role.get("description", "")))
    return " ".join(parts)


def _build_weighted_career_text(career: list[dict]) -> str:
    """
    Build career text with recency weighting.
    More recent roles get their text duplicated to boost TF-IDF signal.
    """
    parts = []
    for role in career:
        if not isinstance(role, dict):
            continue
        desc = normalise_text(role.get("description", ""))
        title = normalise_text(role.get("title", ""))
        decay = _recency_decay(role.get("start_date"))
        repeat = max(1, round(decay * 3))
        parts.extend([desc, title] * repeat)
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Main feature scorer
# ---------------------------------------------------------------------------

def compute_features(candidate: dict) -> FeatureScores:
    """
    Compute all 15 named feature scores for a candidate.

    Args:
        candidate: Validated candidate dict.

    Returns:
        FeatureScores dataclass with all scores in [0, 1].
    """
    cid = candidate.get("candidate_id", "")
    profile = candidate.get("profile", {})
    career = candidate.get("career_history", [])
    skills = candidate.get("skills", [])
    signals = candidate.get("redrob_signals", {})

    fs = FeatureScores(candidate_id=cid)

    # Build full text blocks
    career_text = _build_all_career_text(career)
    weighted_career = _build_weighted_career_text(career)
    current_title = normalise_text(str(profile.get("current_title", "")))
    headline = normalise_text(str(profile.get("headline", "")))
    summary = normalise_text(str(profile.get("summary", "")))
    all_text = f"{weighted_career} {headline} {summary}"

    # -----------------------------------------------------------------------
    # 1. Retrieval & Production Evidence
    # -----------------------------------------------------------------------
    career_retrieval = _has_production_evidence(career_text, RETRIEVAL_KEYWORDS)
    skill_retrieval = _skill_score(skills, RETRIEVAL_KEYWORDS)
    # Title bonus: if current/recent title mentions retrieval/search/ranking
    title_bonus = 0.1 if any(kw in current_title for kw in ["search", "retrieval", "ranking", "recommendation", "matching"]) else 0.0
    fs.retrieval_production_score = clamp(career_retrieval + skill_retrieval * 0.3 + title_bonus, 0.0, 1.0)

    # -----------------------------------------------------------------------
    # 2. Vector Search Score
    # -----------------------------------------------------------------------
    career_vs = _has_production_evidence(career_text, VECTOR_SEARCH_KEYWORDS)
    skill_vs = _skill_score(skills, VECTOR_SEARCH_KEYWORDS)
    fs.vector_search_score = clamp(career_vs + skill_vs * 0.3, 0.0, 1.0)

    # -----------------------------------------------------------------------
    # 3. Ranking Evaluation Score
    # -----------------------------------------------------------------------
    career_re = _has_production_evidence(career_text, RANKING_EVAL_KEYWORDS)
    skill_re = _skill_score(skills, RANKING_EVAL_KEYWORDS)
    fs.ranking_evaluation_score = clamp(career_re + skill_re * 0.3, 0.0, 1.0)

    # -----------------------------------------------------------------------
    # 4. Python Engineering Score
    # -----------------------------------------------------------------------
    career_py = _has_production_evidence(career_text, PYTHON_KEYWORDS)
    skill_py = _skill_score(skills, PYTHON_KEYWORDS)
    fs.python_engineering_score = clamp(career_py + skill_py * 0.4, 0.0, 1.0)

    # -----------------------------------------------------------------------
    # 5. ML Production Score
    # -----------------------------------------------------------------------
    career_ml = _has_production_evidence(career_text, ML_PRODUCTION_KEYWORDS)
    skill_ml = _skill_score(skills, ML_PRODUCTION_KEYWORDS)
    fs.ml_production_score = clamp(career_ml + skill_ml * 0.3, 0.0, 1.0)

    # -----------------------------------------------------------------------
    # 6. Product Shipping Score
    # -----------------------------------------------------------------------
    ship_hits = count_keyword_hits(PRODUCT_SHIPPING_KEYWORDS, career_text)
    verb_hits = count_keyword_hits(PRODUCTION_ACTION_VERBS, career_text)
    fs.product_shipping_score = clamp(ship_hits * 0.06 + verb_hits * 0.03, 0.0, 1.0)

    # -----------------------------------------------------------------------
    # 7. Startup / Ownership Score
    # -----------------------------------------------------------------------
    startup_hits = count_keyword_hits(STARTUP_KEYWORDS, all_text)
    # Check if any role was at a small company (product company signal)
    small_company_count = sum(
        1 for role in career
        if isinstance(role, dict) and role.get("company_size", "") in ("1-10", "11-50", "51-200")
    )
    fs.startup_ownership_score = clamp(startup_hits * 0.08 + small_company_count * 0.1, 0.0, 1.0)

    # -----------------------------------------------------------------------
    # 8. Recent Coding Score
    # -----------------------------------------------------------------------
    # Look at the most recent role
    recent_roles = career[:2]  # Top 2 (most recent)
    recent_text = _build_all_career_text(recent_roles)
    coding_hits = count_keyword_hits(RECENT_CODING_KEYWORDS + PYTHON_KEYWORDS, recent_text)
    github_score = safe_float(signals.get("github_activity_score"), 0.0)
    github_bonus = 0.0 if github_score < 0 else clamp(github_score / 100.0, 0.0, 0.2)
    fs.recent_coding_score = clamp(coding_hits * 0.04 + github_bonus, 0.0, 1.0)

    # -----------------------------------------------------------------------
    # 9. LLM Fine-tuning Score
    # -----------------------------------------------------------------------
    career_llm = _has_production_evidence(career_text, LLM_FINETUNE_KEYWORDS)
    skill_llm = _skill_score(skills, LLM_FINETUNE_KEYWORDS)
    fs.llm_finetuning_score = clamp(career_llm + skill_llm * 0.3, 0.0, 1.0)

    # -----------------------------------------------------------------------
    # 10. Learning to Rank Score
    # -----------------------------------------------------------------------
    career_ltr = _has_production_evidence(career_text, LEARNING_TO_RANK_KEYWORDS)
    skill_ltr = _skill_score(skills, LEARNING_TO_RANK_KEYWORDS)
    fs.learning_to_rank_score = clamp(career_ltr + skill_ltr * 0.3, 0.0, 1.0)

    # -----------------------------------------------------------------------
    # 11. NLP/IR Relevance Score
    # -----------------------------------------------------------------------
    career_nlp = _has_production_evidence(career_text, NLP_IR_KEYWORDS)
    skill_nlp = _skill_score(skills, NLP_IR_KEYWORDS)
    fs.nlp_ir_relevance_score = clamp(career_nlp + skill_nlp * 0.3, 0.0, 1.0)

    # -----------------------------------------------------------------------
    # 12. Experience Fit Score (smooth bell curve around 5-9 years)
    # -----------------------------------------------------------------------
    yoe = safe_float(profile.get("years_of_experience"), 0.0)
    fs.experience_fit_score = _experience_score(yoe)

    # -----------------------------------------------------------------------
    # 13. Location / Relocation Score
    # -----------------------------------------------------------------------
    location = normalise_text(str(profile.get("location", "")))
    country = normalise_text(str(profile.get("country", "")))
    willing = safe_bool(signals.get("willing_to_relocate"), False)
    work_mode = normalise_text(str(signals.get("preferred_work_mode", "")))
    fs.location_relocation_score = _location_score(location, country, willing, work_mode)

    # -----------------------------------------------------------------------
    # 14. Keyword Stuffing Penalty
    # -----------------------------------------------------------------------
    fs.keyword_stuffing_penalty = _detect_keyword_stuffing(skills, career_text)

    return fs


def _experience_score(years: float) -> float:
    """
    Smooth experience score:
    - 5–9 years: score 1.0
    - Below 2 years: very low (0.1)
    - Above 15 years: moderate (0.6) — not disqualified, just less ideal
    """
    if years <= 0:
        return 0.05
    if years < EXPERIENCE_ABSOLUTE_MIN:
        return clamp(years / EXPERIENCE_ABSOLUTE_MIN * 0.4, 0.05, 0.4)
    if years <= EXPERIENCE_OPTIMAL_MIN:
        return clamp(0.4 + (years - EXPERIENCE_ABSOLUTE_MIN) / (EXPERIENCE_OPTIMAL_MIN - EXPERIENCE_ABSOLUTE_MIN) * 0.6, 0.4, 1.0)
    if years <= EXPERIENCE_OPTIMAL_MAX:
        return 1.0
    if years <= 12:
        return clamp(1.0 - (years - EXPERIENCE_OPTIMAL_MAX) / (12 - EXPERIENCE_OPTIMAL_MAX) * 0.3, 0.7, 1.0)
    return clamp(0.7 - (years - 12) * 0.02, 0.4, 0.7)


def _location_score(location: str, country: str, willing: bool, work_mode: str) -> float:
    """Score location compatibility with Pune/Noida hybrid role."""
    loc_str = f"{location} {country}"

    # India-based: higher base
    if "india" in loc_str:
        if any(city in loc_str for city in ["pune", "noida", "delhi", "ncr", "gurgaon", "gurugram"]):
            return 1.0  # Already in target city
        if willing or work_mode in ("hybrid", "flexible"):
            return 0.85
        return 0.65

    # Willing to relocate from abroad
    if willing:
        return 0.5

    # Remote or flexible work mode
    if work_mode in ("remote", "flexible"):
        return 0.4

    return 0.2  # Not in India, not willing to relocate


def _detect_keyword_stuffing(skills: list[dict], career_text: str) -> float:
    """
    Detect keyword stuffing: many expert skills with no duration and no
    career text support. Returns a penalty multiplier in [0.6, 1.0].
    """
    suspicious_count = 0

    for skill in skills:
        if not isinstance(skill, dict):
            continue
        name = normalise_text(skill.get("name", ""))
        prof = skill.get("proficiency", "")
        dur = safe_int(skill.get("duration_months"), 0)
        endr = safe_int(skill.get("endorsements"), 0)

        # Expert skill with no duration or endorsements
        if prof in ("expert", "advanced") and dur == 0 and endr == 0:
            suspicious_count += 1
        # Skill listed but zero evidence in career text
        elif prof == "expert" and not any(part in career_text for part in name.split()):
            suspicious_count += 1

    if suspicious_count >= KEYWORD_STUFFING_THRESHOLD:
        penalty = max(0.60, KEYWORD_STUFFING_PENALTY - (suspicious_count - KEYWORD_STUFFING_THRESHOLD) * 0.02)
        return penalty

    return 1.0  # No penalty
