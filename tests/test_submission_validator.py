"""
HireWise AI — Tests: Submission Validator
Tests all 12 submission rules.
"""
import csv
import io
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest

from src.submission_validator import validate_submission_csv, EXPECTED_ROWS, REQUIRED_COLUMNS


def _write_csv(rows: list[dict], columns: list[str] | None = None) -> str:
    """Write rows to a temp CSV and return its path."""
    cols = columns or REQUIRED_COLUMNS
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=cols)
    writer.writeheader()
    writer.writerows(rows)
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, encoding="utf-8")
    tmp.write(buf.getvalue())
    tmp.close()
    return tmp.name


def _make_valid_rows(n: int = 100) -> list[dict]:
    rows = []
    for i in range(1, n + 1):
        score = round(1.0 - (i - 1) * 0.005, 4)
        rows.append({
            "candidate_id": f"CAND_{i:07d}",
            "rank": i,
            "score": score,
            "reasoning": f"This candidate has {i} years of relevant experience in production AI systems.",
        })
    return rows


def test_valid_submission_passes():
    rows = _make_valid_rows(100)
    path = _write_csv(rows)
    result = validate_submission_csv(path)
    Path(path).unlink()
    assert result.is_valid, f"Expected valid, got errors: {result.errors}"


def test_wrong_row_count_fails():
    rows = _make_valid_rows(50)
    path = _write_csv(rows)
    result = validate_submission_csv(path)
    Path(path).unlink()
    assert not result.is_valid
    assert any("100" in e or "50" in e for e in result.errors)


def test_wrong_columns_fails():
    rows = [{"id": "CAND_0000001", "rank": 1, "score": 0.9, "reasoning": "OK"}]
    path = _write_csv(rows, columns=["id", "rank", "score", "reasoning"])
    result = validate_submission_csv(path)
    Path(path).unlink()
    assert not result.is_valid


def test_duplicate_candidate_id_fails():
    rows = _make_valid_rows(100)
    rows[50]["candidate_id"] = rows[0]["candidate_id"]  # duplicate ID
    path = _write_csv(rows)
    result = validate_submission_csv(path)
    Path(path).unlink()
    assert not result.is_valid
    assert any("duplicate" in e.lower() or "Duplicate" in e for e in result.errors)


def test_duplicate_rank_fails():
    rows = _make_valid_rows(100)
    rows[50]["rank"] = 1  # duplicate rank
    path = _write_csv(rows)
    result = validate_submission_csv(path)
    Path(path).unlink()
    assert not result.is_valid


def test_non_monotonic_scores_fails():
    rows = _make_valid_rows(100)
    rows[10]["score"] = 0.999  # Higher than rank 1 score at position 10
    path = _write_csv(rows)
    result = validate_submission_csv(path)
    Path(path).unlink()
    assert not result.is_valid
    assert any("monoton" in e.lower() for e in result.errors)


def test_empty_reasoning_fails():
    rows = _make_valid_rows(100)
    rows[5]["reasoning"] = ""
    path = _write_csv(rows)
    result = validate_submission_csv(path)
    Path(path).unlink()
    assert not result.is_valid
    assert any("reasoning" in e.lower() for e in result.errors)


def test_invalid_candidate_id_format_fails():
    rows = _make_valid_rows(100)
    rows[0]["candidate_id"] = "INVALID_ID"
    path = _write_csv(rows)
    result = validate_submission_csv(path)
    Path(path).unlink()
    assert not result.is_valid


def test_candidate_id_not_in_input_fails():
    rows = _make_valid_rows(100)
    valid_ids = {f"CAND_{i:07d}" for i in range(1, 101)}
    rows[0]["candidate_id"] = "CAND_9999999"  # Not in valid set
    path = _write_csv(rows)
    result = validate_submission_csv(path, valid_candidate_ids=valid_ids)
    Path(path).unlink()
    assert not result.is_valid


def test_ranks_must_be_one_through_hundred():
    rows = _make_valid_rows(100)
    rows[99]["rank"] = 200  # Rank 200 instead of 100
    path = _write_csv(rows)
    result = validate_submission_csv(path)
    Path(path).unlink()
    assert not result.is_valid


def test_missing_file_fails():
    result = validate_submission_csv("/nonexistent/path/submission.csv")
    assert not result.is_valid
    assert any("not found" in e.lower() or "File" in e for e in result.errors)
