"""
HireWise AI — Profile Integrity & Honeypot Detection
======================================================
Detects suspicious profiles using transparent, rule-based checks.

Returns:
  - integrity_score in [0, 1] (1.0 = fully trustworthy)
  - integrity_flags: list of human-readable flag descriptions
  - honeypot_risk: "low" | "medium" | "high"

All rules are explicitly documented and visible to users in the UI.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from src.utils import (
    clamp,
    get_logger,
    normalise_text,
    parse_date,
    safe_float,
    safe_int,
    count_keyword_hits,
)

logger = get_logger("hirewise.integrity")

TODAY: date = date.today()

# Keywords that might appear artificially in a stuffed profile
SENIOR_AI_KEYWORDS = [
    "vector", "embedding", "retrieval", "faiss", "milvus", "qdrant",
    "elasticsearch", "pinecone", "sentence transformer", "ndcg", "mrr",
    "learning to rank", "lora", "peft", "rlhf", "transformer",
]


@dataclass
class IntegrityResult:
    """Container for profile integrity analysis results."""

    candidate_id: str
    integrity_score: float = 1.0          # 1.0 = clean, 0.0 = very suspicious
    integrity_flags: list[str] = field(default_factory=list)
    honeypot_risk: str = "low"            # "low", "medium", "high"

    def add_flag(self, msg: str, severity: float = 0.05) -> None:
        """Add a flag and reduce integrity score accordingly."""
        self.integrity_flags.append(msg)
        self.integrity_score = max(0.0, self.integrity_score - severity)

    def finalise(self) -> None:
        """Set honeypot_risk based on final integrity score."""
        if self.integrity_score >= 0.80:
            self.honeypot_risk = "low"
        elif self.integrity_score >= 0.50:
            self.honeypot_risk = "medium"
        else:
            self.honeypot_risk = "high"


def analyse_integrity(candidate: dict) -> IntegrityResult:
    """
    Analyse a candidate profile for integrity issues and honeypot signals.

    Args:
        candidate: Validated candidate dict.

    Returns:
        IntegrityResult with score, flags, and risk level.
    """
    cid = candidate.get("candidate_id", "")
    result = IntegrityResult(candidate_id=cid)

    profile = candidate.get("profile", {})
    career = candidate.get("career_history", [])
    skills = candidate.get("skills", [])
    signals = candidate.get("redrob_signals", {})

    # --- Check 1: Signup date after last active date ---
    signup = parse_date(signals.get("signup_date"))
    last_active = parse_date(signals.get("last_active_date"))
    if signup and last_active and signup > last_active:
        result.add_flag(
            f"INTEGRITY: signup_date ({signup}) is after last_active_date ({last_active}). "
            "This is chronologically impossible.",
            severity=0.25,
        )

    # --- Check 2: Career date ordering and overlaps ---
    _check_career_dates(career, result)

    # --- Check 3: Current role with end date ---
    for i, role in enumerate(career):
        if not isinstance(role, dict):
            continue
        is_current = role.get("is_current", False)
        end_date = role.get("end_date")
        if is_current and end_date is not None:
            result.add_flag(
                f"INTEGRITY: Career entry {i+1} ('{role.get('title', '?')}') "
                f"is marked current but has end_date='{end_date}'.",
                severity=0.10,
            )
        if not is_current and end_date is None and i > 0:
            result.add_flag(
                f"INTEGRITY: Career entry {i+1} ('{role.get('title', '?')}') "
                "is not current but has no end_date.",
                severity=0.05,
            )

    # --- Check 4: Skill duration vs total experience ---
    total_months = safe_float(profile.get("years_of_experience"), 0.0) * 12
    _check_skill_durations(skills, total_months, result)

    # --- Check 5: Many expert skills with no evidence ---
    expert_unsupported = _count_unsupported_expert_skills(skills, career)
    if expert_unsupported >= 5:
        result.add_flag(
            f"INTEGRITY: {expert_unsupported} expert/advanced skills with no supporting "
            "career description evidence and zero endorsements — potential keyword stuffing.",
            severity=0.05 * min(expert_unsupported, 5),
        )

    # --- Check 6: Non-technical title with perfectly matching AI skill list ---
    _check_title_skill_mismatch(profile, skills, career, result)

    # --- Check 7: Headline / title completely inconsistent with career ---
    _check_headline_career_mismatch(profile, career, result)

    # --- Check 8: Artificially constructed profile (too-perfect keyword match) ---
    _check_honeypot_signal(profile, skills, career, result)

    # --- Check 9: Contradictory duration_months in career ---
    _check_duration_consistency(career, result)

    # --- Check 10: Education year sanity ---
    _check_education_years(candidate.get("education", []), result)

    result.finalise()
    return result


# ---------------------------------------------------------------------------
# Sub-checks
# ---------------------------------------------------------------------------

def _check_career_dates(career: list[dict], result: IntegrityResult) -> None:
    """Detect overlapping full-time roles and chronological issues."""
    parsed_roles: list[tuple[date | None, date | None, str]] = []

    for role in career:
        if not isinstance(role, dict):
            continue
        start = parse_date(role.get("start_date"))
        end_raw = role.get("end_date")
        end = parse_date(end_raw) if end_raw else TODAY
        title = role.get("title", "?")
        parsed_roles.append((start, end, title))

    # Check for overlapping full-time jobs
    for i in range(len(parsed_roles)):
        for j in range(i + 1, len(parsed_roles)):
            s1, e1, t1 = parsed_roles[i]
            s2, e2, t2 = parsed_roles[j]
            if s1 and e1 and s2 and e2:
                # Check overlap
                overlap_start = max(s1, s2)
                overlap_end = min(e1, e2)
                if overlap_start < overlap_end:
                    overlap_months = int((overlap_end - overlap_start).days / 30.44)
                    if overlap_months > 3:  # Allow small overlaps during transitions
                        result.add_flag(
                            f"INTEGRITY: Possible overlapping full-time roles: "
                            f"'{t1}' and '{t2}' overlap by ~{overlap_months} months.",
                            severity=0.08,
                        )


def _check_skill_durations(
    skills: list[dict], total_months: float, result: IntegrityResult
) -> None:
    """Flag skills whose duration far exceeds total experience."""
    if total_months <= 0:
        return
    for skill in skills:
        if not isinstance(skill, dict):
            continue
        dur = safe_int(skill.get("duration_months"), 0)
        name = skill.get("name", "?")
        if dur > total_months + 12:
            result.add_flag(
                f"INTEGRITY: Skill '{name}' has duration_months={dur} which exceeds "
                f"total experience ~{int(total_months)} months.",
                severity=0.05,
            )


def _count_unsupported_expert_skills(
    skills: list[dict], career: list[dict]
) -> int:
    """Count expert/advanced skills not mentioned in career descriptions."""
    career_text = " ".join(
        normalise_text(r.get("description", "") + " " + r.get("title", ""))
        for r in career if isinstance(r, dict)
    )

    count = 0
    for skill in skills:
        if not isinstance(skill, dict):
            continue
        name = normalise_text(skill.get("name", ""))
        prof = skill.get("proficiency", "")
        endr = safe_int(skill.get("endorsements"), 0)
        dur = safe_int(skill.get("duration_months"), 0)

        if prof in ("expert", "advanced"):
            # Check if skill name appears in career text
            name_parts = [p for p in name.split() if len(p) > 3]
            in_career = any(part in career_text for part in name_parts)
            if not in_career and endr == 0 and dur == 0:
                count += 1

    return count


def _check_title_skill_mismatch(
    profile: dict, skills: list[dict], career: list[dict], result: IntegrityResult
) -> None:
    """Flag profiles where the current title is non-technical but skills list is all AI."""
    current_title = normalise_text(profile.get("current_title", ""))

    non_technical_titles = [
        "hr manager", "marketing manager", "sales executive", "operations manager",
        "content writer", "accountant", "graphic designer", "customer support",
        "business analyst", "project manager", "mechanical engineer",
        "civil engineer", "financial analyst",
    ]

    is_non_technical = any(t in current_title for t in non_technical_titles)
    if not is_non_technical:
        return

    # Count AI-related skills
    skill_names = [normalise_text(s.get("name", "")) for s in skills if isinstance(s, dict)]
    ai_skills = sum(1 for name in skill_names if any(kw in name for kw in SENIOR_AI_KEYWORDS))

    if ai_skills >= 4:
        result.add_flag(
            f"INTEGRITY: Current title '{current_title}' is non-technical/non-AI but "
            f"profile lists {ai_skills} advanced AI skills — possible keyword stuffing.",
            severity=0.10,
        )


def _check_headline_career_mismatch(
    profile: dict, career: list[dict], result: IntegrityResult
) -> None:
    """Flag when headline says 'AI Engineer' but career has no AI roles."""
    headline = normalise_text(profile.get("headline", ""))
    ai_headline = any(kw in headline for kw in ["ai engineer", "ml engineer", "machine learning"])
    if not ai_headline:
        return

    career_titles = " ".join(
        normalise_text(r.get("title", "")) for r in career if isinstance(r, dict)
    )
    career_descriptions = " ".join(
        normalise_text(r.get("description", "")) for r in career if isinstance(r, dict)
    )

    ai_in_career = any(
        kw in career_titles or kw in career_descriptions
        for kw in ["machine learning", "ai", "data science", "nlp", "deep learning"]
    )

    if not ai_in_career:
        result.add_flag(
            "INTEGRITY: Headline claims AI/ML engineer role but career history shows "
            "no AI/ML related positions or descriptions.",
            severity=0.15,
        )


def _check_honeypot_signal(
    profile: dict, skills: list[dict], career: list[dict], result: IntegrityResult
) -> None:
    """
    Detect profiles that appear artificially constructed to match the job description.

    Signals:
      - Exact match of many job-specific keywords (>10) across skills + headline
      - No genuine career evidence of these skills
      - Generic summary text mixed with specific keywords
    """
    headline = normalise_text(profile.get("headline", ""))
    summary = normalise_text(profile.get("summary", ""))
    skill_names = " ".join(normalise_text(s.get("name", "")) for s in skills if isinstance(s, dict))

    skill_and_headline = f"{headline} {skill_names}"
    career_desc = " ".join(
        normalise_text(r.get("description", "")) for r in career if isinstance(r, dict)
    )

    kw_in_surface = count_keyword_hits(SENIOR_AI_KEYWORDS, skill_and_headline)
    kw_in_career = count_keyword_hits(SENIOR_AI_KEYWORDS, career_desc)

    # Many surface keywords with little career support
    if kw_in_surface >= 8 and kw_in_career <= 2:
        result.add_flag(
            f"INTEGRITY: Profile has {kw_in_surface} job-specific AI keywords in skills/headline "
            f"but only {kw_in_career} in career descriptions — artificial keyword construction suspected.",
            severity=0.20,
        )

    # Check for generic templated summary phrases
    generic_phrases = [
        "experimenting with chatgpt",
        "open to roles where i can apply",
        "i've been curious about how ai tools",
        "ai tools could augment my work",
    ]
    summary_is_generic = sum(1 for phrase in generic_phrases if phrase in summary) >= 2
    if summary_is_generic and kw_in_surface >= 5:
        result.add_flag(
            "INTEGRITY: Summary appears templated/generic (common AI-curiosity boilerplate) "
            "combined with many specific AI skill claims.",
            severity=0.10,
        )


def _check_duration_consistency(career: list[dict], result: IntegrityResult) -> None:
    """Check if reported duration_months roughly matches computed duration."""
    for i, role in enumerate(career):
        if not isinstance(role, dict):
            continue
        start = parse_date(role.get("start_date"))
        end_raw = role.get("end_date")
        end = parse_date(end_raw) if end_raw else TODAY
        reported = safe_int(role.get("duration_months"), -1)
        title = role.get("title", "?")

        if reported < 0 or start is None:
            continue

        computed = max(0, int((end - start).days / 30.44))
        if abs(computed - reported) > 6:
            result.add_flag(
                f"INTEGRITY: Role '{title}' reports duration_months={reported} but "
                f"computed duration from dates is ~{computed} months (diff > 6 months).",
                severity=0.05,
            )


def _check_education_years(education: list[dict], result: IntegrityResult) -> None:
    """Detect impossible education year ranges."""
    for i, edu in enumerate(education):
        if not isinstance(edu, dict):
            continue
        start_yr = safe_int(edu.get("start_year"), 0)
        end_yr = safe_int(edu.get("end_year"), 0)
        degree = edu.get("degree", "?")

        if start_yr > 0 and end_yr > 0:
            if end_yr < start_yr:
                result.add_flag(
                    f"INTEGRITY: Education entry {i+1} ('{degree}') has end_year ({end_yr}) "
                    f"before start_year ({start_yr}).",
                    severity=0.10,
                )
            elif (end_yr - start_yr) > 8:
                result.add_flag(
                    f"INTEGRITY: Education entry {i+1} ('{degree}') spans {end_yr - start_yr} years — unusually long.",
                    severity=0.03,
                )
