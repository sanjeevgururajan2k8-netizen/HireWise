"""
HireWise AI — Tests: Loaders
"""
import gzip
import json
import tempfile
from pathlib import Path

import pytest
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.loaders import load_json_list, stream_jsonl, stream_jsonl_gz, stream_candidates


SAMPLE = [
    {"candidate_id": "CAND_0000001", "profile": {"name": "Test"}},
    {"candidate_id": "CAND_0000002", "profile": {"name": "Test2"}},
]


def test_load_json_list():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(SAMPLE, f)
        path = f.name
    result = load_json_list(path)
    assert len(result) == 2
    assert result[0]["candidate_id"] == "CAND_0000001"
    Path(path).unlink()


def test_load_json_list_not_a_list():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump({"key": "value"}, f)
        path = f.name
    with pytest.raises(ValueError):
        load_json_list(path)
    Path(path).unlink()


def test_stream_jsonl():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        for record in SAMPLE:
            f.write(json.dumps(record) + "\n")
        path = f.name
    result = list(stream_jsonl(path))
    assert len(result) == 2
    Path(path).unlink()


def test_stream_jsonl_skips_blank_lines():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        f.write(json.dumps(SAMPLE[0]) + "\n")
        f.write("\n")  # blank line
        f.write("   \n")  # whitespace line
        f.write(json.dumps(SAMPLE[1]) + "\n")
        path = f.name
    result = list(stream_jsonl(path))
    assert len(result) == 2
    Path(path).unlink()


def test_stream_jsonl_skips_malformed():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        f.write(json.dumps(SAMPLE[0]) + "\n")
        f.write("{bad json here\n")
        f.write(json.dumps(SAMPLE[1]) + "\n")
        path = f.name
    result = list(stream_jsonl(path))
    assert len(result) == 2  # Bad line skipped
    Path(path).unlink()


def test_stream_jsonl_gz():
    with tempfile.NamedTemporaryFile(suffix=".jsonl.gz", delete=False) as f:
        path = f.name
    with gzip.open(path, "wt", encoding="utf-8") as gz:
        for record in SAMPLE:
            gz.write(json.dumps(record) + "\n")
    result = list(stream_jsonl_gz(path))
    assert len(result) == 2
    Path(path).unlink()


def test_stream_candidates_json():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(SAMPLE, f)
        path = f.name
    result = list(stream_candidates(path))
    assert len(result) == 2
    Path(path).unlink()


def test_stream_candidates_jsonl():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        for record in SAMPLE:
            f.write(json.dumps(record) + "\n")
        path = f.name
    result = list(stream_candidates(path))
    assert len(result) == 2
    Path(path).unlink()


def test_stream_candidates_gz():
    with tempfile.NamedTemporaryFile(suffix=".jsonl.gz", delete=False) as f:
        path = f.name
    with gzip.open(path, "wt", encoding="utf-8") as gz:
        for record in SAMPLE:
            gz.write(json.dumps(record) + "\n")
    result = list(stream_candidates(path))
    assert len(result) == 2
    Path(path).unlink()


def test_stream_candidates_unsupported():
    with pytest.raises(ValueError):
        list(stream_candidates("file.xyz"))


def test_macos_metadata_skipped():
    with tempfile.TemporaryDirectory() as tmpdir:
        bad_path = Path(tmpdir) / "._bad_file.json"
        bad_path.write_text("garbage", encoding="utf-8")
        result = list(stream_candidates(str(bad_path)))
        # Should not raise, returns empty (ValueError or empty)
