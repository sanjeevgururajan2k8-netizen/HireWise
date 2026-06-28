"""
HireWise AI — CLI Ranking Pipeline
=====================================
Usage:
  python rank.py --candidates ./candidates.jsonl --job ./job_description.docx --out ./submission.csv
  python rank.py --candidates ./candidates.jsonl.gz --job ./job_description.docx --out ./submission.csv
  python rank.py --candidates ./challenge_data/sample/sample_candidates.json --job ./challenge_data/raw/job_description.docx --out ./artifacts/submission.csv

Constraints:
  - CPU only, no GPU
  - No network calls
  - No hosted AI APIs
  - Must finish within 5 minutes for 100K candidates
  - Memory efficient (streaming)
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

# Make project root importable regardless of working directory
sys.path.insert(0, str(Path(__file__).parent))

from config.scoring_config import DEFAULT_JOB_DESC_DOCX, DEFAULT_OUTPUT_CSV, TOP_N
from src.behaviour import compute_behaviour_modifier
from src.exporter import (
    export_full_breakdown_csv,
    export_submission_csv,
    export_suspicious_profiles_csv,
    export_validation_report,
)
from src.feature_engineering import compute_features
from src.integrity import analyse_integrity
from src.lexical_ranker import LexicalRanker
from src.loaders import load_job_description, stream_candidates
from src.reasoning import generate_reasoning
from src.schema_validator import validate_candidate
from src.scoring import (
    CandidateScore,
    normalise_final_scores,
    score_candidate,
    select_top_n,
)
from src.submission_validator import validate_submission_csv
from src.text_builder import build_candidate_text, build_weighted_corpus_string
from src.utils import get_logger, get_peak_memory_mb

logger = get_logger("hirewise.rank")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="HireWise AI — Intelligent Candidate Ranking Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python rank.py --candidates ./candidates.jsonl --job ./job_description.docx --out ./submission.csv
  python rank.py --candidates ./candidates.jsonl.gz --job ./job_description.docx --out ./submission.csv
        """,
    )
    parser.add_argument(
        "--candidates",
        required=True,
        help="Path to candidate data (.json, .jsonl, or .jsonl.gz)",
    )
    parser.add_argument(
        "--job",
        default=DEFAULT_JOB_DESC_DOCX,
        help="Path to job description (.docx, .txt, or .md)",
    )
    parser.add_argument(
        "--out",
        default=DEFAULT_OUTPUT_CSV,
        help="Output path for the submission CSV",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=TOP_N,
        help=f"Number of top candidates to select (default: {TOP_N})",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose debug logging",
    )
    parser.add_argument(
        "--skip-semantic",
        action="store_true",
        default=True,
        help="Skip optional semantic re-ranking (default: True)",
    )
    return parser.parse_args()


def run_pipeline(
    candidates_path: str,
    job_path: str,
    output_path: str,
    top_n: int = TOP_N,
    verbose: bool = False,
) -> dict:
    """
    Main ranking pipeline.

    Args:
        candidates_path: Path to candidates file.
        job_path: Path to job description file.
        output_path: Path to write submission CSV.
        top_n: Number of top candidates to select.
        verbose: Enable debug logging.

    Returns:
        Dict with pipeline statistics.
    """
    if verbose:
        import logging
        logging.getLogger("hirewise").setLevel(logging.DEBUG)

    wall_start = time.perf_counter()

    # =========================================================================
    # Stage A: Load and validate candidates (streaming)
    # =========================================================================
    logger.info("=" * 60)
    logger.info("HireWise AI — Candidate Ranking Pipeline")
    logger.info("=" * 60)
    logger.info("Candidates: %s", candidates_path)
    logger.info("Job:        %s", job_path)
    logger.info("Output:     %s", output_path)
    logger.info("=" * 60)

    logger.info("[Stage A] Loading and validating candidates...")

    # Load job description first (needed later but small)
    job_text = load_job_description(job_path)
    logger.info("Job description loaded (%d chars)", len(job_text))

    # Stream and validate candidates
    valid_candidates: list[dict] = []
    validation_results = []
    skipped = 0
    total_processed = 0

    for record in stream_candidates(candidates_path):
        total_processed += 1
        vr = validate_candidate(record)
        validation_results.append(vr)
        if vr.is_valid:
            valid_candidates.append(record)
        else:
            skipped += 1

        if total_processed % 10_000 == 0:
            logger.info(
                "  Processed %d | Valid: %d | Skipped: %d",
                total_processed,
                len(valid_candidates),
                skipped,
            )

    logger.info(
        "[Stage A] Done. Total: %d | Valid: %d | Skipped: %d",
        total_processed,
        len(valid_candidates),
        skipped,
    )

    if not valid_candidates:
        logger.error("No valid candidates to rank. Exiting.")
        sys.exit(1)

    # Build a lookup dict for quick access
    candidates_dict: dict[str, dict] = {
        c["candidate_id"]: c for c in valid_candidates
    }
    valid_ids = set(candidates_dict.keys())

    # =========================================================================
    # Stage B: Build text corpus
    # =========================================================================
    logger.info("[Stage B] Building weighted text corpus...")

    candidate_ids: list[str] = []
    corpus: list[str] = []
    for cand in valid_candidates:
        cid = cand["candidate_id"]
        text_fields = build_candidate_text(cand)
        weighted_text = build_weighted_corpus_string(text_fields)
        candidate_ids.append(cid)
        corpus.append(weighted_text)

    logger.info("[Stage B] Corpus built for %d candidates", len(corpus))

    # =========================================================================
    # Stage C: Lexical relevance scoring
    # =========================================================================
    logger.info("[Stage C] Computing TF-IDF lexical scores...")

    ranker = LexicalRanker()
    lexical_scores: dict[str, float] = ranker.fit_transform(candidate_ids, corpus, job_text)

    logger.info("[Stage C] Lexical scoring complete")

    # =========================================================================
    # Stage D+E: Feature engineering + behavioural modifier
    # =========================================================================
    logger.info("[Stage D/E] Computing evidence features + behavioural signals...")

    all_feature_scores: dict[str, object] = {}
    for cand in valid_candidates:
        cid = cand["candidate_id"]
        all_feature_scores[cid] = compute_features(cand)

    logger.info("[Stage D/E] Feature computation complete")

    # =========================================================================
    # Stage F: Profile integrity and honeypot detection
    # =========================================================================
    logger.info("[Stage F] Analysing profile integrity...")

    integrity_results: dict[str, object] = {}
    high_risk_count = 0
    medium_risk_count = 0

    for cand in valid_candidates:
        cid = cand["candidate_id"]
        ir = analyse_integrity(cand)
        integrity_results[cid] = ir
        if ir.honeypot_risk == "high":
            high_risk_count += 1
        elif ir.honeypot_risk == "medium":
            medium_risk_count += 1

    logger.info(
        "[Stage F] Integrity analysis complete. High-risk: %d | Medium-risk: %d",
        high_risk_count,
        medium_risk_count,
    )

    # =========================================================================
    # Stage H: Final scoring and ranking
    # =========================================================================
    logger.info("[Stage H] Computing final scores...")

    all_scores: list[CandidateScore] = []
    for cand in valid_candidates:
        cid = cand["candidate_id"]
        cs = score_candidate(
            candidate=cand,
            lexical_score=lexical_scores.get(cid, 0.0),
            features=all_feature_scores[cid],
            integrity=integrity_results[cid],
        )
        all_scores.append(cs)

    logger.info("[Stage H] Selecting top %d candidates...", top_n)
    top_scores = select_top_n(all_scores, n=top_n)
    top_scores = normalise_final_scores(top_scores)

    logger.info("[Stage H] Final ranking complete")

    # =========================================================================
    # Generate reasoning for each top candidate
    # =========================================================================
    logger.info("[Reasoning] Generating candidate reasoning...")

    reasonings: list[str] = []
    for rank, cs in enumerate(top_scores, start=1):
        cand = candidates_dict[cs.candidate_id]
        r = generate_reasoning(cand, cs, rank)
        reasonings.append(r)

    # =========================================================================
    # Export outputs
    # =========================================================================
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("[Export] Writing submission CSV...")
    export_submission_csv(top_scores, reasonings, output_path)

    breakdown_path = output_dir / "full_score_breakdown.csv"
    export_full_breakdown_csv(candidates_dict, top_scores, reasonings, breakdown_path)

    validation_report_path = output_dir / "validation_report.json"
    export_validation_report(validation_results, validation_report_path)

    suspicious_path = output_dir / "suspicious_profiles.csv"
    export_suspicious_profiles_csv(candidates_dict, integrity_results, suspicious_path)

    # =========================================================================
    # Validate the output CSV
    # =========================================================================
    logger.info("[Validate] Checking submission CSV...")
    sub_result = validate_submission_csv(output_path, valid_ids)
    print("\n" + sub_result.summary())

    # =========================================================================
    # Summary statistics
    # =========================================================================
    wall_end = time.perf_counter()
    elapsed = wall_end - wall_start
    peak_mem = get_peak_memory_mb()

    top_score = top_scores[0].final_score if top_scores else 0.0

    logger.info("=" * 60)
    logger.info("RANKING COMPLETE")
    logger.info("  Total candidates processed : %d", total_processed)
    logger.info("  Valid profiles             : %d", len(valid_candidates))
    logger.info("  Invalid/skipped            : %d", skipped)
    logger.info("  High-risk integrity        : %d", high_risk_count)
    logger.info("  Medium-risk integrity      : %d", medium_risk_count)
    logger.info("  Top candidate score        : %.4f", top_score)
    logger.info("  Ranking runtime            : %.2f seconds", elapsed)
    logger.info("  Peak memory (approx.)      : %.1f MB", peak_mem)
    logger.info("  Output CSV                 : %s", output_path)
    logger.info("=" * 60)

    return {
        "total_processed": total_processed,
        "valid_count": len(valid_candidates),
        "skipped": skipped,
        "high_risk": high_risk_count,
        "medium_risk": medium_risk_count,
        "top_score": top_score,
        "runtime_seconds": elapsed,
        "peak_memory_mb": peak_mem,
        "output_path": output_path,
        "submission_valid": sub_result.is_valid,
        "top_scores": top_scores,
        "reasonings": reasonings,
        "candidates_dict": candidates_dict,
        "integrity_results": integrity_results,
    }


def main() -> None:
    args = parse_args()
    run_pipeline(
        candidates_path=args.candidates,
        job_path=args.job,
        output_path=args.out,
        top_n=args.top_n,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    main()
