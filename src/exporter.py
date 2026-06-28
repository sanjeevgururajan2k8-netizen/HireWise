"""
HireWise AI — CSV Exporter
============================
Writes the final submission CSV and the full score breakdown CSV.
"""

from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Any

import pandas as pd

from src.scoring import CandidateScore
from src.utils import get_logger

logger = get_logger("hirewise.exporter")

SUBMISSION_COLUMNS = ["candidate_id", "rank", "score", "reasoning"]


def export_submission_csv(
    ranked_scores: list[CandidateScore],
    reasonings: list[str],
    output_path: str | Path,
) -> Path:
    """
    Write the final submission CSV (exactly 100 rows).

    Args:
        ranked_scores: Sorted list of CandidateScore objects (rank 1 first).
        reasonings: Reasoning string for each candidate in same order.
        output_path: Destination path for the CSV.

    Returns:
        Path to the written file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for rank, (cs, reasoning) in enumerate(zip(ranked_scores, reasonings), start=1):
        rows.append({
            "candidate_id": cs.candidate_id,
            "rank": rank,
            "score": round(cs.final_score, 4),
            "reasoning": reasoning,
        })

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SUBMISSION_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)

    logger.info("Submission CSV written to: %s (%d rows)", output_path, len(rows))
    return output_path


def export_full_breakdown_csv(
    candidates: dict[str, dict],
    ranked_scores: list[CandidateScore],
    reasonings: list[str],
    output_path: str | Path,
) -> Path:
    """
    Write a detailed score breakdown CSV with all feature scores.

    Args:
        candidates: Dict of candidate_id → candidate dict.
        ranked_scores: Sorted CandidateScore list.
        reasonings: Reasoning strings in same order.
        output_path: Destination path.

    Returns:
        Path to the written file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for rank, (cs, reasoning) in enumerate(zip(ranked_scores, reasonings), start=1):
        cand = candidates.get(cs.candidate_id, {})
        profile = cand.get("profile", {})

        row = {
            "rank": rank,
            "candidate_id": cs.candidate_id,
            "anonymized_name": profile.get("anonymized_name", ""),
            "current_title": profile.get("current_title", ""),
            "years_of_experience": profile.get("years_of_experience", ""),
            "location": profile.get("location", ""),
            "country": profile.get("country", ""),
            "final_score": round(cs.final_score, 4),
            "lexical_score": round(cs.lexical_score, 4),
            "feature_score": round(cs.feature_score, 4),
            "behaviour_score": round(cs.behaviour_score, 4),
            "behaviour_modifier": round(cs.behaviour_modifier, 4),
            "integrity_score": round(cs.integrity_score, 4),
            "honeypot_risk": cs.honeypot_risk,
            "keyword_stuffing_penalty": round(cs.keyword_stuffing_penalty, 4),
        }

        # Add individual feature scores
        for feat_name, feat_val in cs.features.items():
            row[feat_name] = round(feat_val, 4)

        row["reasoning"] = reasoning
        rows.append(row)

    df = pd.DataFrame(rows)
    df.to_csv(output_path, index=False, encoding="utf-8")

    logger.info("Full breakdown CSV written to: %s", output_path)
    return output_path


def export_validation_report(
    validation_results: list[Any],
    output_path: str | Path,
) -> Path:
    """
    Export schema validation results as JSON.

    Args:
        validation_results: List of ValidationResult objects.
        output_path: Destination path.

    Returns:
        Path to the written JSON file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    data = []
    for vr in validation_results:
        data.append({
            "candidate_id": vr.candidate_id,
            "is_valid": vr.is_valid,
            "errors": vr.errors,
            "warnings": vr.warnings,
        })

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    logger.info("Validation report written to: %s", output_path)
    return output_path


def export_suspicious_profiles_csv(
    candidates: dict[str, dict],
    integrity_results: dict[str, Any],
    output_path: str | Path,
) -> Path:
    """
    Export a report of suspicious/high-risk profiles.

    Args:
        candidates: Dict of candidate_id → candidate dict.
        integrity_results: Dict of candidate_id → IntegrityResult.
        output_path: Destination path.

    Returns:
        Path to the written CSV.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    rows = []
    for cid, ir in integrity_results.items():
        if ir.honeypot_risk in ("medium", "high"):
            cand = candidates.get(cid, {})
            profile = cand.get("profile", {})
            rows.append({
                "candidate_id": cid,
                "anonymized_name": profile.get("anonymized_name", ""),
                "current_title": profile.get("current_title", ""),
                "honeypot_risk": ir.honeypot_risk,
                "integrity_score": round(ir.integrity_score, 4),
                "flags": " | ".join(ir.integrity_flags),
                "flag_count": len(ir.integrity_flags),
            })

    rows.sort(key=lambda r: (r["honeypot_risk"] == "high", r["flag_count"]), reverse=True)

    if not rows:
        rows.append({"candidate_id": "NONE", "note": "No suspicious profiles detected"})

    df = pd.DataFrame(rows)
    df.to_csv(output_path, index=False, encoding="utf-8")

    logger.info("Suspicious profiles CSV written to: %s (%d profiles)", output_path, len(rows))
    return output_path


def scores_to_dataframe(
    ranked_scores: list[CandidateScore],
    candidates: dict[str, dict],
    reasonings: list[str],
) -> pd.DataFrame:
    """Convert ranked scores to a pandas DataFrame for Streamlit display."""
    rows = []
    for rank, (cs, reasoning) in enumerate(zip(ranked_scores, reasonings), start=1):
        cand = candidates.get(cs.candidate_id, {})
        profile = cand.get("profile", {})
        signals = cand.get("redrob_signals", {})

        from src.utils import score_to_category
        rows.append({
            "Rank": rank,
            "Candidate ID": cs.candidate_id,
            "Name": profile.get("anonymized_name", ""),
            "Current Title": profile.get("current_title", ""),
            "YOE": profile.get("years_of_experience", ""),
            "Location": f"{profile.get('location', '')} ({profile.get('country', '')})",
            "Final Score": round(cs.final_score, 4),
            "Technical Fit": round(cs.feature_score, 4),
            "Behaviour Score": round(cs.behaviour_score, 4),
            "Integrity Score": round(cs.integrity_score, 4),
            "Honeypot Risk": cs.honeypot_risk,
            "Open to Work": signals.get("open_to_work_flag", False),
            "Category": score_to_category(cs.final_score),
            "Reasoning": reasoning,
        })

    return pd.DataFrame(rows)
