"""
HireWise AI — Text Field Builder
==================================
Constructs weighted text fields for each candidate for use in TF-IDF ranking.

Fields are kept separate and weighted so that career evidence carries more
weight than raw skills lists. All text is normalised to lowercase.
"""

from __future__ import annotations

from typing import Any

from config.scoring_config import TEXT_FIELD_WEIGHTS
from src.utils import get_logger, normalise_text

logger = get_logger("hirewise.text_builder")


def build_candidate_text(candidate: dict) -> dict[str, str]:
    """
    Build separate weighted text fields for a single candidate.

    Returns a dict with keys matching TEXT_FIELD_WEIGHTS:
      - "career_descriptions"
      - "current_title"
      - "career_titles"
      - "headline"
      - "summary"
      - "skills"
      - "certifications"
      - "education_field"
    """
    profile = candidate.get("profile", {})
    career = candidate.get("career_history", [])
    skills = candidate.get("skills", [])
    certs = candidate.get("certifications", [])
    education = candidate.get("education", [])

    # Career history descriptions (highest weight)
    career_descriptions = " ".join(
        normalise_text(role.get("description", ""))
        for role in career
        if isinstance(role, dict)
    )

    # Current title (from profile)
    current_title = normalise_text(str(profile.get("current_title", "")))

    # Career history titles (all roles)
    career_titles = " ".join(
        normalise_text(role.get("title", ""))
        for role in career
        if isinstance(role, dict)
    )

    # Professional headline
    headline = normalise_text(str(profile.get("headline", "")))

    # Professional summary
    summary = normalise_text(str(profile.get("summary", "")))

    # Skills — name + proficiency
    skill_parts = []
    for skill in skills:
        if isinstance(skill, dict):
            name = normalise_text(str(skill.get("name", "")))
            prof = normalise_text(str(skill.get("proficiency", "")))
            skill_parts.append(f"{name} {prof}")
    skills_text = " ".join(skill_parts)

    # Certifications
    cert_parts = []
    for cert in certs:
        if isinstance(cert, dict):
            cert_parts.append(normalise_text(str(cert.get("name", ""))))
            cert_parts.append(normalise_text(str(cert.get("issuer", ""))))
    certifications_text = " ".join(cert_parts)

    # Education field of study
    education_parts = []
    for edu in education:
        if isinstance(edu, dict):
            education_parts.append(normalise_text(str(edu.get("field_of_study", ""))))
    education_text = " ".join(education_parts)

    return {
        "career_descriptions": career_descriptions,
        "current_title": current_title,
        "career_titles": career_titles,
        "headline": headline,
        "summary": summary,
        "skills": skills_text,
        "certifications": certifications_text,
        "education_field": education_text,
    }


def build_weighted_corpus_string(text_fields: dict[str, str]) -> str:
    """
    Combine all text fields into a single weighted string for TF-IDF.

    Higher-weight fields are repeated proportionally so that TF-IDF
    gives them more influence. Weights are rounded to integers for repetition.

    Args:
        text_fields: Dict of field_name → text from build_candidate_text().

    Returns:
        A single string containing all fields with weight-proportional repetition.
    """
    parts: list[str] = []
    for field_name, text in text_fields.items():
        if not text:
            continue
        weight = TEXT_FIELD_WEIGHTS.get(field_name, 1.0)
        repeat = max(1, round(weight))  # Repeat text proportional to weight
        parts.extend([text] * repeat)
    return " ".join(parts)


def build_job_description_query(job_text: str) -> str:
    """
    Normalise the job description text for use as the TF-IDF query document.

    Args:
        job_text: Raw job description string.

    Returns:
        Normalised job description string.
    """
    return normalise_text(job_text)


def build_all_corpus(
    candidates: list[dict],
) -> tuple[list[str], list[str]]:
    """
    Build weighted corpus strings for all candidates.

    Args:
        candidates: List of validated candidate dicts.

    Returns:
        Tuple of:
          - List of candidate_ids in the same order
          - List of weighted corpus strings in the same order
    """
    ids: list[str] = []
    corpus: list[str] = []

    for cand in candidates:
        cid = cand.get("candidate_id", "")
        text_fields = build_candidate_text(cand)
        weighted_text = build_weighted_corpus_string(text_fields)
        ids.append(cid)
        corpus.append(weighted_text)

    logger.info("Built weighted corpus for %d candidates", len(candidates))
    return ids, corpus
