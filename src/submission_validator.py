"""
HireWise AI — Submission Validator
=====================================
Validates the final CSV output against all submission rules before download.

Checks:
  - Exactly 100 rows
  - Correct columns in correct order
  - Rank values 1 through 100 (no duplicates)
  - No duplicate candidate IDs
  - All candidate IDs exist in the input dataset
  - Scores are monotonically non-increasing
  - Score at rank 1 >= score at rank 2
  - Proper CSV encoding (UTF-8)
  - Reasoning is non-empty and properly escaped
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.utils import get_logger, is_valid_candidate_id

logger = get_logger("hirewise.submission_validator")

REQUIRED_COLUMNS = ["candidate_id", "rank", "score", "reasoning"]
EXPECTED_ROWS = 100


@dataclass
class SubmissionValidationResult:
    """Outcome of submission CSV validation."""

    is_valid: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    row_count: int = 0
    max_score: float = 0.0
    min_score: float = 0.0

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
        self.is_valid = False

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)

    def summary(self) -> str:
        status = "PASSED" if self.is_valid else "FAILED"
        lines = [f"Submission validation: {status}"]
        lines.append(f"  Rows: {self.row_count}")
        lines.append(f"  Score range: {self.min_score:.4f} – {self.max_score:.4f}")
        if self.errors:
            lines.append(f"  Errors ({len(self.errors)}):")
            for err in self.errors:
                lines.append(f"    ✗ {err}")
        if self.warnings:
            lines.append(f"  Warnings ({len(self.warnings)}):")
            for w in self.warnings:
                lines.append(f"    ⚠ {w}")
        return "\n".join(lines)


def validate_submission_csv(
    csv_path: str | Path,
    valid_candidate_ids: set[str] | None = None,
) -> SubmissionValidationResult:
    """
    Validate a submission CSV file against all hackathon rules.

    Args:
        csv_path: Path to the submission CSV file.
        valid_candidate_ids: Set of all valid candidate IDs from the input.
                             If None, skips the "ID exists in input" check.

    Returns:
        SubmissionValidationResult with pass/fail and detailed errors.
    """
    result = SubmissionValidationResult()
    path = Path(csv_path)

    # --- File exists ---
    if not path.exists():
        result.add_error(f"File not found: {path}")
        return result

    # --- Read CSV ---
    try:
        with open(path, "r", encoding="utf-8", newline="") as f:
            content = f.read()
    except UnicodeDecodeError:
        result.add_error("File is not valid UTF-8 encoding")
        return result

    try:
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
        fieldnames = reader.fieldnames or []
    except Exception as exc:
        result.add_error(f"CSV parse error: {exc}")
        return result

    # --- Column names and order ---
    if list(fieldnames) != REQUIRED_COLUMNS:
        result.add_error(
            f"Column mismatch. Expected {REQUIRED_COLUMNS}, got {list(fieldnames)}"
        )

    expected_rows = EXPECTED_ROWS
    if valid_candidate_ids is not None and len(valid_candidate_ids) < EXPECTED_ROWS:
        expected_rows = len(valid_candidate_ids)

    # --- Row count ---
    result.row_count = len(rows)
    if len(rows) != expected_rows:
        result.add_error(
            f"Expected exactly {expected_rows} rows, got {len(rows)}"
        )

    if not rows:
        return result

    # --- Parse and check each row ---
    ranks_seen: set[int] = set()
    ids_seen: set[str] = set()
    scores: list[float] = []

    for i, row in enumerate(rows):
        row_num = i + 1

        # candidate_id
        cid = row.get("candidate_id", "").strip()
        if not cid:
            result.add_error(f"Row {row_num}: Empty candidate_id")
        elif not is_valid_candidate_id(cid):
            result.add_error(f"Row {row_num}: Invalid candidate_id format: '{cid}'")
        elif cid in ids_seen:
            result.add_error(f"Row {row_num}: Duplicate candidate_id: '{cid}'")
        else:
            ids_seen.add(cid)

        if valid_candidate_ids and cid and cid not in valid_candidate_ids:
            result.add_error(
                f"Row {row_num}: candidate_id '{cid}' does not exist in the input dataset"
            )

        # rank
        rank_str = row.get("rank", "").strip()
        try:
            rank = int(rank_str)
            if rank in ranks_seen:
                result.add_error(f"Row {row_num}: Duplicate rank: {rank}")
            elif rank < 1 or rank > expected_rows:
                result.add_error(f"Row {row_num}: Rank {rank} out of range [1, {expected_rows}]")
            else:
                ranks_seen.add(rank)
        except ValueError:
            result.add_error(f"Row {row_num}: Invalid rank value: '{rank_str}'")
            rank = -1

        # score
        score_str = row.get("score", "").strip()
        try:
            score = float(score_str)
            if not (0.0 <= score <= 1.0):
                result.add_warning(f"Row {row_num}: Score {score:.4f} outside [0, 1]")
            scores.append(score)
        except ValueError:
            result.add_error(f"Row {row_num}: Invalid score value: '{score_str}'")
            scores.append(0.0)

        # reasoning
        reasoning = row.get("reasoning", "").strip()
        if not reasoning:
            result.add_error(f"Row {row_num}: Empty reasoning for candidate '{cid}'")
        elif len(reasoning) < 20:
            result.add_warning(f"Row {row_num}: Reasoning seems too short: '{reasoning}'")

    # --- Rank completeness (1..expected_rows) ---
    expected_ranks = set(range(1, expected_rows + 1))
    missing_ranks = expected_ranks - ranks_seen
    if missing_ranks:
        result.add_error(f"Missing rank values: {sorted(missing_ranks)[:10]}")

    # --- Score monotonicity ---
    if len(scores) >= 2:
        result.max_score = max(scores)
        result.min_score = min(scores)

        for i in range(1, len(scores)):
            if scores[i] > scores[i - 1] + 1e-6:  # Small epsilon for floating point
                result.add_error(
                    f"Scores not monotonically non-increasing at row {i+1}: "
                    f"{scores[i]:.6f} > {scores[i-1]:.6f}"
                )
                break  # Report first violation only

    return result


def validate_submission_from_dataframe(df: Any, valid_candidate_ids: set[str] | None = None) -> SubmissionValidationResult:
    """
    Validate a submission from a pandas DataFrame.

    Args:
        df: pandas DataFrame with columns [candidate_id, rank, score, reasoning].
        valid_candidate_ids: Set of valid IDs from input data.

    Returns:
        SubmissionValidationResult.
    """
    result = SubmissionValidationResult()

    # Write to in-memory CSV and validate
    buf = io.StringIO()
    try:
        df.to_csv(buf, index=False)
    except Exception as exc:
        result.add_error(f"Failed to serialise DataFrame to CSV: {exc}")
        return result

    buf.seek(0)
    try:
        reader = csv.DictReader(buf)
        rows = list(reader)
        fieldnames = reader.fieldnames or []
    except Exception as exc:
        result.add_error(f"CSV parse error from DataFrame: {exc}")
        return result

    # Reuse the same checks
    tmp_path = "__tmp_validate__.csv"
    tmp = Path(tmp_path)
    tmp.write_text(buf.getvalue(), encoding="utf-8")
    out = validate_submission_csv(tmp_path, valid_candidate_ids)
    tmp.unlink(missing_ok=True)
    return out
