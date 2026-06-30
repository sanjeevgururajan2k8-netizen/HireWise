"""
HireWise AI — Page 7: Export
==============================
Download submission.csv, full breakdown, validation report, and suspicious profiles.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import streamlit as st
import yaml

st.set_page_config(page_title="Export — HireWise AI", page_icon="⬇", layout="wide")

from src.theme import apply_theme
apply_theme()

st.markdown("""
<div class="page-header header-export">
    <p class="page-title">⬇ Export & Download</p>
    <p class="page-sub">Download submission CSV · Score breakdown · Validation reports · Metadata template</p>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Check for data
# ---------------------------------------------------------------------------
top_scores = st.session_state.get("top_scores", [])
reasonings = st.session_state.get("reasonings", [])
candidates_dict = st.session_state.get("candidates_dict", {})
submission_valid = st.session_state.get("submission_valid", False)
integrity_results = st.session_state.get("integrity_results", {})
validation_results = st.session_state.get("validation_results", [])

if not top_scores:
    st.warning("⚠️ No ranking data found. Please run the pipeline first.")
    if st.button("▶ Go to Run Ranking"):
        st.switch_page("pages/2_Run_Ranking.py")
    st.stop()

# ---------------------------------------------------------------------------
# Submission CSV
# ---------------------------------------------------------------------------
st.markdown("### 📄 Submission CSV")

col1, col2 = st.columns([3, 1])
with col1:
    st.markdown(f"""
    <div class="download-card">
        <p class="download-title">🏆 submission.csv</p>
        <p class="download-desc">Final ranked candidates — exactly 100 rows · UTF-8 encoded · Validated</p>
        {"<p style='color:#16a34a; font-weight:600;'>✅ Validation: PASSED</p>" if submission_valid else "<p style='color:#dc2626; font-weight:600;'>❌ Validation: FAILED — re-run the pipeline</p>"}
    </div>
    """, unsafe_allow_html=True)

with col2:
    if submission_valid:
        # Build CSV in memory
        import csv
        import io

        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=["candidate_id", "rank", "score", "reasoning"])
        writer.writeheader()
        for rank, (cs, r) in enumerate(zip(top_scores, reasonings), start=1):
            writer.writerow({
                "candidate_id": cs.candidate_id,
                "rank": rank,
                "score": round(cs.final_score, 4),
                "reasoning": r,
            })

        st.download_button(
            label="⬇ Download submission.csv",
            data=buf.getvalue().encode("utf-8"),
            file_name="submission.csv",
            mime="text/csv",
            use_container_width=True,
            type="primary",
        )
    else:
        st.button("⬇ Download submission.csv", disabled=True, use_container_width=True)
        st.caption("Validation must pass before download is enabled.")

st.markdown("---")

# ---------------------------------------------------------------------------
# Full score breakdown
# ---------------------------------------------------------------------------
st.markdown("### 📊 Full Score Breakdown")

from src.exporter import scores_to_dataframe
breakdown_df = scores_to_dataframe(top_scores, candidates_dict, reasonings)

# Add all feature scores
feature_rows = []
for cs in top_scores:
    feature_rows.append(cs.features)

feat_df = pd.DataFrame(feature_rows)
if not feat_df.empty:
    full_df = pd.concat([breakdown_df.reset_index(drop=True), feat_df.reset_index(drop=True)], axis=1)
else:
    full_df = breakdown_df

col_a, col_b = st.columns([3, 1])
with col_a:
    st.markdown(f"""
    <div class="download-card">
        <p class="download-title">📋 full_score_breakdown.csv</p>
        <p class="download-desc">All feature scores, behaviour modifiers, integrity scores, and reasoning for all {len(top_scores)} ranked candidates</p>
    </div>
    """, unsafe_allow_html=True)

with col_b:
    breakdown_csv = full_df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇ Download Breakdown",
        data=breakdown_csv,
        file_name="full_score_breakdown.csv",
        mime="text/csv",
        use_container_width=True,
    )

st.markdown("---")

# ---------------------------------------------------------------------------
# Validation report JSON
# ---------------------------------------------------------------------------
st.markdown("### 🔍 Validation Report")

if validation_results:
    report_data = [
        {
            "candidate_id": vr.candidate_id,
            "is_valid": vr.is_valid,
            "errors": vr.errors,
            "warnings": vr.warnings,
        }
        for vr in validation_results
    ]
    report_json = json.dumps(report_data, indent=2, ensure_ascii=False).encode("utf-8")

    invalid_count = sum(1 for vr in validation_results if not vr.is_valid)
    warn_count = sum(1 for vr in validation_results if vr.warnings)

    col_c, col_d = st.columns([3, 1])
    with col_c:
        st.markdown(f"""
        <div class="download-card">
            <p class="download-title">🔍 validation_report.json</p>
            <p class="download-desc">Schema validation results for all candidates · {invalid_count} invalid · {warn_count} with warnings</p>
        </div>
        """, unsafe_allow_html=True)
    with col_d:
        st.download_button(
            label="⬇ Download Report",
            data=report_json,
            file_name="validation_report.json",
            mime="application/json",
            use_container_width=True,
        )

st.markdown("---")

# ---------------------------------------------------------------------------
# Suspicious profiles
# ---------------------------------------------------------------------------
st.markdown("### 🛡 Suspicious Profiles Report")

suspicious = [
    {
        "candidate_id": cid,
        "honeypot_risk": ir.honeypot_risk,
        "integrity_score": round(ir.integrity_score, 4),
        "flag_count": len(ir.integrity_flags),
        "flags": " | ".join(ir.integrity_flags),
    }
    for cid, ir in integrity_results.items()
    if ir.honeypot_risk in ("medium", "high")
]

if suspicious:
    susp_df = pd.DataFrame(suspicious)
    susp_df = susp_df.sort_values(["honeypot_risk", "flag_count"], ascending=[False, False])

    col_e, col_f = st.columns([3, 1])
    with col_e:
        st.markdown(f"""
        <div class="download-card">
            <p class="download-title">⚠️ suspicious_profiles.csv</p>
            <p class="download-desc">{len(suspicious)} medium/high-risk profiles with all integrity flags</p>
        </div>
        """, unsafe_allow_html=True)
    with col_f:
        st.download_button(
            label="⬇ Download Suspicious",
            data=susp_df.to_csv(index=False).encode("utf-8"),
            file_name="suspicious_profiles.csv",
            mime="text/csv",
            use_container_width=True,
        )
else:
    st.success("✅ No suspicious profiles detected in the current ranking set.")

st.markdown("---")

# ---------------------------------------------------------------------------
# Metadata YAML
# ---------------------------------------------------------------------------
st.markdown("### 📋 Submission Metadata YAML")

metadata = {
    "team_name": "hirewise-ai",
    "primary_contact": {
        "name": "Team HireWise",
        "email": "your@email.com",
        "phone": "+91-XXXXXXXXXX",
    },
    "team_members": [
        {"name": "Member 1", "email": "member1@email.com", "role": "ML Engineer"},
    ],
    "github_repo": "https://github.com/YOUR_USERNAME/hirewise-ai",
    "sandbox_link": "https://huggingface.co/spaces/YOUR_USERNAME/hirewise-ai",
    "reproduce_command": "python rank.py --candidates ./candidates.jsonl --job ./job_description.docx --out ./submission.csv",
    "compute": {
        "platform": "Local PC / Cloud",
        "cpu_cores": 8,
        "ram_gb": 16,
        "python_version": "3.11",
        "os": "Windows / Linux",
        "uses_gpu_for_inference": False,
        "has_network_during_ranking": False,
        "pre_computation_required": False,
        "pre_computation_time_minutes": 0,
    },
    "ai_tools_used": ["Antigravity IDE (Google DeepMind)"],
    "ai_usage_summary": "AI coding assistant used for code generation. No candidate data fed to any LLM. No hosted AI APIs used during ranking.",
    "methodology_summary": "Hybrid explainable ranker: TF-IDF (40%) + evidence-based feature scoring (60%) across 11 named dimensions. Production action verbs required for evidence credit. Behavioural modifier capped at [0.75, 1.10]. Ten explicit integrity checks for honeypot detection. Synonym expansion for IR/retrieval terminology. Deterministic tie-breaking. Streaming JSONL.GZ support.",
    "declarations": {
        "read_submission_spec": True,
        "code_is_original_work": True,
        "no_collusion": True,
        "honeypot_check_done": True,
        "reproduction_tested": True,
    },
}

yaml_str = yaml.dump(metadata, default_flow_style=False, allow_unicode=True, sort_keys=False)

col_g, col_h = st.columns([3, 1])
with col_g:
    st.markdown("""
    <div class="download-card">
        <p class="download-title">📋 submission_metadata.yaml</p>
        <p class="download-desc">Edit team details, then submit via the hackathon portal</p>
    </div>
    """, unsafe_allow_html=True)
    with st.expander("Preview YAML"):
        st.code(yaml_str, language="yaml")

with col_h:
    st.download_button(
        label="⬇ Download YAML",
        data=yaml_str.encode("utf-8"),
        file_name="submission_metadata.yaml",
        mime="text/yaml",
        use_container_width=True,
    )
