"""
HireWise AI — Utility Functions
================================
Shared helpers used across all modules:
  - Date parsing and comparison
  - Safe dictionary access
  - Logging setup
  - Text normalisation
  - Memory measurement
"""

from __future__ import annotations

import logging
import os
import re
import sys
from datetime import date, datetime
from typing import Any

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def get_logger(name: str = "hirewise") -> logging.Logger:
    """Return a consistently configured logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


logger = get_logger("hirewise.utils")


# ---------------------------------------------------------------------------
# Date helpers
# ---------------------------------------------------------------------------

def parse_date(value: str | None) -> date | None:
    """Parse an ISO date string (YYYY-MM-DD) to a date object. Returns None on failure."""
    if not value:
        return None
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def today() -> date:
    """Return today's date."""
    return date.today()


def months_between(start: date | None, end: date | None) -> int | None:
    """Calculate approximate months between two dates. Returns None if either is None."""
    if start is None or end is None:
        return None
    delta = end - start
    return max(0, int(delta.days / 30.44))


def date_str_to_year(value: str | None) -> int | None:
    """Extract year from an ISO date string."""
    d = parse_date(value)
    return d.year if d else None


# ---------------------------------------------------------------------------
# Safe data access
# ---------------------------------------------------------------------------

def safe_get(obj: dict, *keys: str, default: Any = None) -> Any:
    """Safely traverse nested dicts. Returns default if any key is missing."""
    current = obj
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key, default)
        if current is None:
            return default
    return current


def safe_float(value: Any, default: float = 0.0) -> float:
    """Convert value to float safely."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    """Convert value to int safely."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_bool(value: Any, default: bool = False) -> bool:
    """Convert value to bool safely."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "yes", "1")
    return default


# ---------------------------------------------------------------------------
# Text normalisation
# ---------------------------------------------------------------------------

def normalise_text(text: str) -> str:
    """Lowercase, collapse whitespace, strip leading/trailing spaces."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_text_from_list(items: list[Any], field: str) -> str:
    """Extract and join a field from a list of dicts."""
    if not items:
        return ""
    parts = []
    for item in items:
        if isinstance(item, dict):
            val = item.get(field, "")
            if val:
                parts.append(str(val))
    return " ".join(parts)


# ---------------------------------------------------------------------------
# Memory measurement
# ---------------------------------------------------------------------------

def get_peak_memory_mb() -> float:
    """Return current process RSS memory in MB (cross-platform best effort)."""
    try:
        import resource  # type: ignore  # Unix only
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    except ImportError:
        pass
    try:
        import psutil
        return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
    except ImportError:
        pass
    return 0.0


# ---------------------------------------------------------------------------
# Clamp / normalise
# ---------------------------------------------------------------------------

def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp a value to [lo, hi]."""
    return max(lo, min(hi, value))


def normalise_to_01(values: list[float]) -> list[float]:
    """Min-max normalise a list of floats to [0, 1]."""
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi == lo:
        return [0.5] * len(values)
    return [(v - lo) / (hi - lo) for v in values]


# ---------------------------------------------------------------------------
# Candidate ID helpers
# ---------------------------------------------------------------------------

CAND_ID_RE = re.compile(r"^CAND_\d{7}$")


def is_valid_candidate_id(cid: str) -> bool:
    """Check if the candidate ID matches the required format CAND_XXXXXXX."""
    return bool(CAND_ID_RE.match(str(cid)))


# ---------------------------------------------------------------------------
# String similarity helpers (no external dependency)
# ---------------------------------------------------------------------------

def keyword_in_text(keyword: str, text: str) -> bool:
    """Check if a keyword appears as a whole word or phrase in text."""
    if not keyword or not text:
        return False
    pattern = re.escape(keyword.lower())
    return bool(re.search(rf"\b{pattern}\b", text.lower()))


def count_keyword_hits(keywords: list[str], text: str) -> int:
    """Count how many keywords appear in text."""
    text_lower = text.lower()
    return sum(1 for kw in keywords if kw.lower() in text_lower)


# ---------------------------------------------------------------------------
# Score capping
# ---------------------------------------------------------------------------

def score_to_category(score: float) -> str:
    """Map a final score to a recommendation category label."""
    from config.scoring_config import RECOMMENDATION_CATEGORIES
    for threshold, label in RECOMMENDATION_CATEGORIES:
        if score >= threshold:
            return label
    return "Limited fit"
