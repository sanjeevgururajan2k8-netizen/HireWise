"""
HireWise AI — Schema Validator
================================
Validates candidate records against the candidate_schema.json.
Also performs custom cross-field checks not expressible in JSON Schema:
  - Chronological career date order
  - is_current / end_date consistency
  - Skill duration vs total experience
  - Signup date vs last_active_date
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from src.utils import get_logger, is_valid_candidate_id, parse_date, safe_float, safe_int

logger = get_logger("hirewise.schema_validator")

# Required top-level fields
REQUIRED_TOP_LEVEL: list[str] = [
    "candidate_id", "profile", "career_history", "education",
    "skills", "redrob_signals",
]

# Required profile sub-fields
REQUIRED_PROFILE: list[str] = [
    "anonymized_name", "headline", "summary", "location", "country",
    "years_of_experience", "current_title", "current_company",
    "current_company_size", "current_industry",
]

# Required redrob_signals sub-fields
REQUIRED_SIGNALS: list[str] = [
    "profile_completeness_score", "signup_date", "last_active_date",
    "open_to_work_flag", "recruiter_response_rate", "avg_response_time_hours",
    "skill_assessment_scores", "notice_period_days", "preferred_work_mode",
    "willing_to_relocate", "github_activity_score", "interview_completion_rate",
    "offer_acceptance_rate", "verified_email", "verified_phone",
    "linkedin_connected",
]

# Required career history item fields
REQUIRED_CAREER: list[str] = [
    "company", "title", "start_date", "end_date",
    "duration_months", "is_current", "description",
]

VALID_COMPANY_SIZES = {
    "1-10", "11-50", "51-200", "201-500",
    "501-1000", "1001-5000", "5001-10000", "10001+",
}

VALID_WORK_MODES = {"remote", "hybrid", "onsite", "flexible"}
VALID_PROFICIENCIES = {"beginner", "intermediate", "advanced", "expert"}


@dataclass
class ValidationResult:
    """Holds the outcome of validating a single candidate record."""

    candidate_id: str
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
        self.is_valid = False

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)


def validate_candidate(record: dict) -> ValidationResult:
    """
    Validate a single candidate record.

    Args:
        record: Raw candidate dict.

    Returns:
        ValidationResult with is_valid flag and any errors/warnings.
    """
    cid = record.get("candidate_id", "<unknown>")
    result = ValidationResult(candidate_id=str(cid), is_valid=True)

    # 1. candidate_id format
    if "candidate_id" not in record:
        result.add_error("Missing candidate_id")
    elif not is_valid_candidate_id(str(cid)):
        result.add_error(f"Invalid candidate_id format: '{cid}' (expected CAND_XXXXXXX)")

    # 2. Required top-level keys
    for key in REQUIRED_TOP_LEVEL:
        if key not in record:
            result.add_error(f"Missing required top-level field: '{key}'")

    if not result.is_valid:
        return result  # No point continuing without core structure

    profile = record.get("profile", {})
    signals = record.get("redrob_signals", {})
    career = record.get("career_history", [])
    skills = record.get("skills", [])

    # 3. Required profile fields
    for key in REQUIRED_PROFILE:
        if key not in profile or profile[key] is None:
            result.add_error(f"Missing profile field: '{key}'")

    # 4. years_of_experience range
    yoe = safe_float(profile.get("years_of_experience"), default=-1)
    if yoe < 0 or yoe > 50:
        result.add_error(f"years_of_experience out of range: {yoe}")

    # 5. Required redrob_signals fields
    for key in REQUIRED_SIGNALS:
        if key not in signals:
            result.add_warning(f"Missing redrob_signal field: '{key}'")

    # 6. Signup / last_active date cross-check
    signup = parse_date(signals.get("signup_date"))
    last_active = parse_date(signals.get("last_active_date"))
    if signup and last_active and signup > last_active:
        result.add_error(
            f"signup_date ({signup}) is after last_active_date ({last_active})"
        )

    # 7. Career history structure and date integrity
    if not isinstance(career, list):
        result.add_error("career_history must be a list")
    else:
        _validate_career(career, result)

    # 8. Skill structure and duration integrity
    if isinstance(skills, list):
        _validate_skills(skills, yoe, result)

    # 9. preferred_work_mode
    wm = signals.get("preferred_work_mode", "")
    if wm and wm not in VALID_WORK_MODES:
        result.add_warning(f"Unexpected preferred_work_mode: '{wm}'")

    return result


def _validate_career(career: list[dict], result: ValidationResult) -> None:
    """Check career history for date/duration inconsistencies."""
    if len(career) == 0:
        result.add_error("career_history must have at least 1 entry")
        return

    today = date.today()
    total_duration = 0

    for i, role in enumerate(career):
        if not isinstance(role, dict):
            result.add_error(f"career_history[{i}] is not a dict")
            continue

        # Required fields
        for key in REQUIRED_CAREER:
            if key not in role:
                result.add_warning(f"career_history[{i}] missing field: '{key}'")

        is_current = role.get("is_current", False)
        end_date_raw = role.get("end_date")
        start_date = parse_date(role.get("start_date"))
        end_date = parse_date(end_date_raw)
        duration = safe_int(role.get("duration_months"), 0)

        # is_current but end_date is set
        if is_current and end_date is not None:
            result.add_error(
                f"career_history[{i}] is_current=True but end_date='{end_date_raw}'"
            )

        # not is_current but end_date is null
        if not is_current and end_date is None:
            result.add_warning(
                f"career_history[{i}] is_current=False but end_date is null"
            )

        # start_date must be before end_date
        if start_date and end_date and start_date > end_date:
            result.add_error(
                f"career_history[{i}] start_date ({start_date}) after end_date ({end_date})"
            )

        # start_date must not be in the future
        if start_date and start_date > today:
            result.add_error(f"career_history[{i}] start_date is in the future: {start_date}")

        # Duration sanity: reported vs computed
        if start_date and end_date:
            computed = max(0, int((end_date - start_date).days / 30.44))
            if abs(computed - duration) > 3:
                result.add_warning(
                    f"career_history[{i}] duration_months ({duration}) differs from "
                    f"computed ({computed}) by more than 3 months"
                )

        total_duration += duration

    # Total duration should not be wildly greater than reported experience * 12
    # (overlapping roles can inflate this; allow up to 20% over)
    yoe = safe_float(result.candidate_id, default=0)  # Not available directly here
    # We skip cross-check against yoe here (done in feature_engineering.py)


def _validate_skills(skills: list[dict], total_exp_years: float, result: ValidationResult) -> None:
    """Check skill duration against total experience."""
    if total_exp_years <= 0:
        return

    total_exp_months = int(total_exp_years * 12)

    for i, skill in enumerate(skills):
        if not isinstance(skill, dict):
            result.add_warning(f"skills[{i}] is not a dict")
            continue

        if "name" not in skill:
            result.add_warning(f"skills[{i}] missing 'name' field")

        proficiency = skill.get("proficiency", "")
        if proficiency and proficiency not in VALID_PROFICIENCIES:
            result.add_warning(f"skills[{i}] unexpected proficiency: '{proficiency}'")

        dur = safe_int(skill.get("duration_months"), 0)
        if dur > total_exp_months + 6:
            result.add_warning(
                f"skills[{i}] ('{skill.get('name', '?')}') duration_months ({dur}) "
                f"exceeds total experience months ({total_exp_months})"
            )


def validate_batch(
    records: list[dict],
) -> tuple[list[dict], list[ValidationResult]]:
    """
    Validate a batch of candidate records.

    Args:
        records: List of raw candidate dicts.

    Returns:
        Tuple of (valid_records, all_results) where valid_records are the
        dicts that passed validation.
    """
    valid: list[dict] = []
    all_results: list[ValidationResult] = []

    for record in records:
        vr = validate_candidate(record)
        all_results.append(vr)
        if vr.is_valid:
            valid.append(record)
        else:
            logger.debug(
                "Candidate %s failed validation: %s",
                vr.candidate_id,
                "; ".join(vr.errors),
            )

    invalid_count = sum(1 for vr in all_results if not vr.is_valid)
    logger.info(
        "Validation complete: %d valid, %d invalid out of %d",
        len(valid),
        invalid_count,
        len(records),
    )
    return valid, all_results
