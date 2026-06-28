"""
HireWise AI — Behavioural Signal Modifier
==========================================
Computes a behavioural availability modifier in the range [0.75, 1.10].

This modifier is applied as a MULTIPLIER on the technical score.
A technically irrelevant candidate CANNOT rank highly through behaviour alone.
A strong technical candidate with good engagement gets a small boost.
"""

from __future__ import annotations

from datetime import date, timedelta

from config.scoring_config import BEHAVIOUR_MODIFIER_MAX, BEHAVIOUR_MODIFIER_MIN
from src.utils import clamp, get_logger, parse_date, safe_bool, safe_float, safe_int

logger = get_logger("hirewise.behaviour")

TODAY: date = date.today()
INACTIVE_THRESHOLD_DAYS: int = 180  # 6 months inactive → significant penalty
SLOW_RESPONSE_THRESHOLD_HOURS: float = 96.0  # 4 days avg response → penalty
LONG_NOTICE_DAYS: int = 90  # 90+ days notice → moderate penalty


def compute_behaviour_modifier(candidate: dict) -> float:
    """
    Compute a behavioural modifier for a candidate based on Redrob signals.

    Components considered:
      + open_to_work_flag (positive)
      + recent last_active_date (positive)
      + high recruiter_response_rate (positive)
      + fast avg_response_time_hours (positive)
      + high interview_completion_rate (positive)
      + offer_acceptance_rate > 0 (positive)
      + github_activity_score > 0 (positive)
      + profile_completeness_score (positive)
      + saved_by_recruiters_30d (mild positive)
      + verified_email + verified_phone (positive)
      - long notice_period_days (negative)
      - very slow response (negative)
      - very long inactivity (negative)

    Returns:
        Modifier float in [BEHAVIOUR_MODIFIER_MIN, BEHAVIOUR_MODIFIER_MAX]
    """
    signals = candidate.get("redrob_signals", {})

    score_raw: float = 0.0

    # --- Positive signals ---

    # 1. Open to work (most important availability signal)
    if safe_bool(signals.get("open_to_work_flag"), False):
        score_raw += 0.20

    # 2. Recent activity
    last_active = parse_date(signals.get("last_active_date"))
    if last_active:
        days_inactive = (TODAY - last_active).days
        if days_inactive <= 30:
            score_raw += 0.15
        elif days_inactive <= 90:
            score_raw += 0.08
        elif days_inactive <= INACTIVE_THRESHOLD_DAYS:
            score_raw += 0.02
        else:
            score_raw -= 0.10  # Very stale profile

    # 3. Recruiter response rate
    rr = safe_float(signals.get("recruiter_response_rate"), 0.0)
    score_raw += rr * 0.15  # 100% response rate adds 0.15

    # 4. Average response time
    avg_rt = safe_float(signals.get("avg_response_time_hours"), 999.0)
    if avg_rt <= 24:
        score_raw += 0.10
    elif avg_rt <= 48:
        score_raw += 0.05
    elif avg_rt > SLOW_RESPONSE_THRESHOLD_HOURS:
        score_raw -= 0.05

    # 5. Interview completion rate
    icr = safe_float(signals.get("interview_completion_rate"), 0.0)
    score_raw += icr * 0.10

    # 6. Offer acceptance rate (only if historically set)
    oar = safe_float(signals.get("offer_acceptance_rate"), -1.0)
    if oar >= 0:
        score_raw += oar * 0.05

    # 7. GitHub activity (proxy for recent hands-on coding)
    gh = safe_float(signals.get("github_activity_score"), -1.0)
    if gh > 0:
        score_raw += (gh / 100.0) * 0.08

    # 8. Profile completeness
    pc = safe_float(signals.get("profile_completeness_score"), 0.0)
    score_raw += (pc / 100.0) * 0.05

    # 9. Saved by recruiters (social proof of interest)
    saved = safe_int(signals.get("saved_by_recruiters_30d"), 0)
    score_raw += min(saved / 20.0, 1.0) * 0.04

    # 10. Verification
    if safe_bool(signals.get("verified_email"), False):
        score_raw += 0.02
    if safe_bool(signals.get("verified_phone"), False):
        score_raw += 0.02

    # --- Negative signals ---

    # 11. Long notice period
    notice = safe_int(signals.get("notice_period_days"), 0)
    if notice >= LONG_NOTICE_DAYS:
        score_raw -= 0.05
    if notice >= 120:
        score_raw -= 0.05

    # 12. Work mode compatibility (job is hybrid Pune/Noida)
    preferred_mode = signals.get("preferred_work_mode", "")
    if preferred_mode in ("hybrid", "flexible"):
        score_raw += 0.03

    # Normalise raw score to a [0, 1] utility
    # Raw score can range roughly from -0.25 to 0.79
    # Map this to [BEHAVIOUR_MODIFIER_MIN, BEHAVIOUR_MODIFIER_MAX]
    normalized = clamp((score_raw + 0.25) / 1.04, 0.0, 1.0)
    modifier = BEHAVIOUR_MODIFIER_MIN + normalized * (BEHAVIOUR_MODIFIER_MAX - BEHAVIOUR_MODIFIER_MIN)

    return clamp(modifier, BEHAVIOUR_MODIFIER_MIN, BEHAVIOUR_MODIFIER_MAX)


def compute_behaviour_score_normalised(candidate: dict) -> float:
    """
    Return the behavioural score as a normalised [0, 1] value for display
    purposes (not the multiplier — just a comparable score for the UI).
    """
    modifier = compute_behaviour_modifier(candidate)
    # Map [BEHAVIOUR_MODIFIER_MIN, BEHAVIOUR_MODIFIER_MAX] → [0, 1]
    lo = BEHAVIOUR_MODIFIER_MIN
    hi = BEHAVIOUR_MODIFIER_MAX
    return clamp((modifier - lo) / (hi - lo), 0.0, 1.0)
