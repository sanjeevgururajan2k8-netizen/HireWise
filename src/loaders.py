"""
HireWise AI — Candidate Data Loaders
=======================================
Supports:
  - JSON file (sample_candidates.json as a list)
  - JSONL file (one candidate per line)
  - JSONL.GZ file (gzip-compressed JSONL, streamed)

macOS metadata files beginning with "._" are filtered automatically.
Records that fail JSON parsing are skipped with a warning.
"""

from __future__ import annotations

import gzip
import json
import os
from pathlib import Path
from typing import Generator, Iterator

from src.utils import get_logger

logger = get_logger("hirewise.loaders")


def _is_macos_metadata(path: str | Path) -> bool:
    """Return True if the file is a macOS metadata artifact (starts with ._)."""
    return Path(path).name.startswith("._")


def load_json_list(path: str | Path) -> list[dict]:
    """
    Load a JSON file that contains a list of candidate dicts.
    Used for sample_candidates.json.

    Args:
        path: Path to the .json file.

    Returns:
        List of candidate dicts.
    """
    path = Path(path)
    if _is_macos_metadata(path):
        logger.warning("Skipping macOS metadata file: %s", path)
        return []

    logger.info("Loading JSON list from: %s", path)
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError(f"Expected a JSON array in {path}, got {type(data).__name__}")

    logger.info("Loaded %d candidates from JSON", len(data))
    return data


def _iter_jsonl_lines(lines: Iterator[str]) -> Generator[dict, None, None]:
    """Parse lines as JSONL, skipping blanks and malformed records."""
    for line_num, raw in enumerate(lines, start=1):
        raw = raw.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
            if isinstance(obj, dict):
                yield obj
            else:
                logger.warning("Line %d is not a JSON object — skipped", line_num)
        except json.JSONDecodeError as exc:
            logger.warning("JSON parse error on line %d: %s — skipped", line_num, exc)


def stream_jsonl(path: str | Path) -> Generator[dict, None, None]:
    """
    Stream candidate dicts from a plain JSONL file.

    Args:
        path: Path to the .jsonl file.

    Yields:
        Candidate dicts one at a time (low memory usage).
    """
    path = Path(path)
    if _is_macos_metadata(path):
        logger.warning("Skipping macOS metadata file: %s", path)
        return

    logger.info("Streaming JSONL from: %s", path)
    with open(path, "r", encoding="utf-8") as f:
        yield from _iter_jsonl_lines(f)


def stream_jsonl_gz(path: str | Path) -> Generator[dict, None, None]:
    """
    Stream candidate dicts from a gzip-compressed JSONL file.
    Reads line-by-line to avoid loading the entire decompressed file into memory.

    Args:
        path: Path to the .jsonl.gz file.

    Yields:
        Candidate dicts one at a time (low memory usage).
    """
    path = Path(path)
    if _is_macos_metadata(path):
        logger.warning("Skipping macOS metadata file: %s", path)
        return

    logger.info("Streaming JSONL.GZ from: %s", path)
    with gzip.open(path, "rt", encoding="utf-8") as f:
        yield from _iter_jsonl_lines(f)


def stream_candidates(path: str | Path) -> Generator[dict, None, None]:
    """
    Auto-detect file format and stream candidate dicts.

    Supported extensions:
      - .json   → loaded as a JSON list and yielded one by one
      - .jsonl  → streamed line-by-line
      - .gz     → streamed from gzip-compressed JSONL

    Args:
        path: Path to the candidate data file.

    Yields:
        Candidate dicts.
    """
    path = Path(path)
    ext = "".join(path.suffixes).lower()

    if ext in (".jsonl.gz", ".gz"):
        yield from stream_jsonl_gz(path)
    elif ext == ".jsonl":
        yield from stream_jsonl(path)
    elif ext == ".json":
        for record in load_json_list(path):
            yield record
    else:
        raise ValueError(
            f"Unsupported file extension: '{ext}'. "
            "Expected .json, .jsonl, or .jsonl.gz"
        )


def count_candidates(path: str | Path) -> int:
    """
    Count the total number of candidates in a file without building in memory.
    Useful for progress estimation.
    """
    path = Path(path)
    ext = "".join(path.suffixes).lower()

    if ext in (".jsonl.gz", ".gz"):
        count = 0
        with gzip.open(path, "rt", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    count += 1
        return count
    elif ext == ".jsonl":
        count = 0
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    count += 1
        return count
    elif ext == ".json":
        data = load_json_list(path)
        return len(data)
    else:
        return 0


def load_job_description(path: str | Path) -> str:
    """
    Load job description text from a .docx, .txt, or .md file.

    Args:
        path: Path to the job description file.

    Returns:
        Plain-text string of the job description.
    """
    path = Path(path)
    ext = path.suffix.lower()

    if ext == ".docx":
        try:
            from docx import Document  # type: ignore
            doc = Document(str(path))
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            return "\n".join(paragraphs)
        except ImportError:
            logger.error("python-docx not installed; cannot read .docx files.")
            raise
        except Exception as exc:
            logger.error("Failed to read DOCX %s: %s", path, exc)
            raise

    elif ext in (".txt", ".md"):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    else:
        raise ValueError(f"Unsupported job description format: '{ext}'")


def load_schema(path: str | Path) -> dict:
    """Load the candidate JSON schema."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
