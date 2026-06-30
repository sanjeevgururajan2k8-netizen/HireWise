"""
HireWise AI — Page 2: Run Ranking
====================================
Executes the full ranking pipeline with stage-by-stage progress display.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

st.set_page_config(page_title="Run Ranking — HireWise AI", page_icon="▶", layout="wide")

from src.theme import apply_theme
apply_theme()

from src.behaviour import compute_behaviour_modifier
from src.exporter import export_full_breakdown_csv, export_submission_csv, export_suspicious_profiles_csv, export_validation_report, scores_to_dataframe
from src.feature_engineering import compute_features
from src.integrity import analyse_integrity
from src.lexical_ranker import LexicalRanker
from src.loaders import load_job_description, stream_candidates
from src.reasoning import generate_reasoning
from src.schema_validator import validate_candidate
from src.scoring import CandidateScore, normalise_final_scores, score_candidate, select_top_n
from src.submission_validator import validate_submission_csv
from src.text_builder import build_candidate_text, build_weighted_corpus_string
from src.utils import get_logger, get_peak_memory_mb

logger = get_logger("hirewise.pages.ranking")

st.markdown("""
<style>
.stage-done { color:#10b981; font-weight:700; }
.stage-running { color:#3b82f6; font-weight:700; }
.stage-pending { color:#94a3b8; font-weight:500; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="page-header header-ranking">
    <div class="page-title">▶ Run Ranking Pipeline</div>
    <div class="page-sub">Execute all 8 ranking stages · Real-time progress · No fake delays</div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Config panel
# ---------------------------------------------------------------------------
with st.expander("⚙️ Pipeline Configuration", expanded=False):
    top_n = st.slider("Top N candidates", min_value=10, max_value=200, value=100, step=10)
    use_semantic = st.checkbox("Use semantic re-ranking (requires precomputed embeddings)", value=False)

st.markdown("---")

# Stage status placeholders
stages = [
    "🔍 Stage A: Validating profiles",
    "📝 Stage B: Extracting evidence text",
    "📐 Stage C: Calculating text relevance (TF-IDF)",
    "🔬 Stage D: Computing evidence features",
    "📡 Stage E: Analysing behavioural signals",
    "🛡 Stage F: Detecting integrity risks",
    "⚖️ Stage H: Generating final ranking",
    "📋 Stage I: Validating CSV output",
]

stage_placeholders = []
for s in stages:
    stage_placeholders.append(st.empty())

progress_bar = st.progress(0)
status_text = st.empty()

# ---------------------------------------------------------------------------
# Run button
# ---------------------------------------------------------------------------
if st.button("🚀 Start Ranking", use_container_width=True, type="primary"):

    candidates_path = st.session_state.get("candidates_path")
    job_text = st.session_state.get("job_text")

    if not candidates_path or not Path(candidates_path).exists():
        st.error("❌ No candidate file selected. Go to Upload & Validate first.")
        st.stop()

    if not job_text:
        # Try loading default
        default_jd = Path("Challenge_data/Raw/job_description.docx")
        if default_jd.exists():
            job_text = load_job_description(default_jd)
            st.session_state["job_text"] = job_text
        else:
            st.error("❌ No job description loaded. Go to Upload & Validate first.")
            st.stop()

    wall_start = time.perf_counter()

    def update_stage(idx: int, status: str = "done") -> None:
        icon = "✅" if status == "done" else "⏳"
        stage_placeholders[idx].markdown(f"{icon} {stages[idx].split(': ', 1)[1]}")
        progress_bar.progress((idx + 1) / len(stages))

    # ====== Stage A: Validate ======
    stage_placeholders[0].markdown(f"⏳ {stages[0].split(': ', 1)[1]}")
    status_text.info("Loading and validating candidates...")

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

    candidates_dict = {c["candidate_id"]: c for c in valid_candidates}
    valid_ids = set(candidates_dict.keys())
    update_stage(0)

    # ====== Stage B: Text corpus ======
    stage_placeholders[1].markdown(f"⏳ {stages[1].split(': ', 1)[1]}")
    status_text.info("Building weighted text corpus...")

    candidate_ids: list[str] = []
    corpus: list[str] = []
    for cand in valid_candidates:
        cid = cand["candidate_id"]
        text_fields = build_candidate_text(cand)
        weighted_text = build_weighted_corpus_string(text_fields)
        candidate_ids.append(cid)
        corpus.append(weighted_text)
    update_stage(1)

    # ====== Stage C: TF-IDF ======
    stage_placeholders[2].markdown(f"⏳ {stages[2].split(': ', 1)[1]}")
    status_text.info("Computing TF-IDF lexical scores...")
    ranker = LexicalRanker()
    lexical_scores = ranker.fit_transform(candidate_ids, corpus, job_text)
    update_stage(2)

    # ====== Stage D: Features ======
    stage_placeholders[3].markdown(f"⏳ {stages[3].split(': ', 1)[1]}")
    status_text.info("Computing evidence-based feature scores...")
    all_features = {}
    for cand in valid_candidates:
        cid = cand["candidate_id"]
        all_features[cid] = compute_features(cand)
    update_stage(3)

    # ====== Stage E: Behavioural ======
    stage_placeholders[4].markdown(f"⏳ {stages[4].split(': ', 1)[1]}")
    status_text.info("Analysing behavioural signals...")
    # Behaviour is computed inside score_candidate; mark as done
    update_stage(4)

    # ====== Stage F: Integrity ======
    stage_placeholders[5].markdown(f"⏳ {stages[5].split(': ', 1)[1]}")
    status_text.info("Detecting profile integrity risks...")
    integrity_results = {}
    high_risk = 0
    medium_risk = 0
    for cand in valid_candidates:
        cid = cand["candidate_id"]
        ir = analyse_integrity(cand)
        integrity_results[cid] = ir
        if ir.honeypot_risk == "high":
            high_risk += 1
        elif ir.honeypot_risk == "medium":
            medium_risk += 1
    update_stage(5)

    # ====== Stage H: Final scores ======
    stage_placeholders[6].markdown(f"⏳ {stages[6].split(': ', 1)[1]}")
    status_text.info("Computing final scores and ranking...")
    all_scores = []
    for cand in valid_candidates:
        cid = cand["candidate_id"]
        cs = score_candidate(
            candidate=cand,
            lexical_score=lexical_scores.get(cid, 0.0),
            features=all_features[cid],
            integrity=integrity_results[cid],
        )
        all_scores.append(cs)

    top_scores = select_top_n(all_scores, n=top_n)
    top_scores = normalise_final_scores(top_scores)

    # Reasoning
    reasonings = []
    for rank, cs in enumerate(top_scores, start=1):
        cand = candidates_dict[cs.candidate_id]
        reasonings.append(generate_reasoning(cand, cs, rank))
    update_stage(6)

    # ====== Export ======
    output_dir = Path("Artifacts")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "submission.csv"
    export_submission_csv(top_scores, reasonings, output_path)
    export_full_breakdown_csv(candidates_dict, top_scores, reasonings, output_dir / "full_score_breakdown.csv")
    export_validation_report(validation_results, output_dir / "validation_report.json")
    export_suspicious_profiles_csv(candidates_dict, integrity_results, output_dir / "suspicious_profiles.csv")

    # ====== Validate CSV ======
    stage_placeholders[7].markdown(f"⏳ {stages[7].split(': ', 1)[1]}")
    sub_result = validate_submission_csv(output_path, valid_ids)
    update_stage(7)

    # ====== Save to session state ======
    wall_end = time.perf_counter()
    elapsed = wall_end - wall_start

    rankings_df = scores_to_dataframe(top_scores, candidates_dict, reasonings)

    st.session_state["pipeline_stats"] = {
        "total_processed": total_processed,
        "valid_count": len(valid_candidates),
        "skipped": skipped,
        "high_risk": high_risk,
        "medium_risk": medium_risk,
        "top_score": top_scores[0].final_score if top_scores else 0.0,
        "runtime_seconds": elapsed,
        "peak_memory_mb": get_peak_memory_mb(),
    }
    st.session_state["top_scores"] = top_scores
    st.session_state["reasonings"] = reasonings
    st.session_state["candidates_dict"] = candidates_dict
    st.session_state["integrity_results"] = integrity_results
    st.session_state["rankings_df"] = rankings_df
    st.session_state["submission_valid"] = sub_result.is_valid
    st.session_state["validation_results"] = validation_results

    # ====== Results summary ======
    progress_bar.progress(1.0)
    status_text.success("✅ Ranking pipeline complete!")

    st.markdown("---")
    st.markdown("### 📊 Pipeline Results")

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Processed", total_processed)
    c2.metric("Valid", len(valid_candidates))
    c3.metric("Skipped", skipped)
    c4.metric("High-Risk Profiles", high_risk)
    c5.metric("Runtime", f"{elapsed:.1f}s")

    if sub_result.is_valid:
        st.success(f"✅ Submission CSV is valid: {output_path}")
    else:
        st.error(f"❌ Submission validation failed: {'; '.join(sub_result.errors[:3])}")

    st.info("👉 Go to **Candidate Rankings** to view and filter the top 100 candidates.")
