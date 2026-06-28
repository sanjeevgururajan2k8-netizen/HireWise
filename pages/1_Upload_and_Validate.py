"""
HireWise AI — Page 1: Upload and Validate
==========================================
Allows uploading candidate files and job descriptions,
validates schema, previews data.
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

st.set_page_config(page_title="Upload & Validate — HireWise AI", page_icon="📁", layout="wide")

from src.theme import apply_theme
apply_theme()

from src.loaders import load_job_description, stream_candidates
from src.schema_validator import validate_batch
from src.utils import get_logger

logger = get_logger("hirewise.pages.upload")

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
[data-testid="stSidebar"] { background: linear-gradient(180deg, #0f172a, #1e3a5f); color: #f1f5f9; }
[data-testid="stSidebar"] * { color: #f1f5f9 !important; }
.page-header { background: linear-gradient(135deg, #1e3a5f, #2563eb); border-radius:12px; padding:28px 36px; color:white; margin-bottom:24px; }
.page-title { font-size:1.8rem; font-weight:800; margin:0; }
.page-sub { color:#cbd5e1; margin-top:4px; font-size:0.95rem; }
.info-card { background:white; border-radius:10px; padding:20px; border:1px solid #e2e8f0; box-shadow:0 1px 3px rgba(0,0,0,0.06); margin:8px 0; }
.error-item { color:#dc2626; font-size:0.85rem; }
.warn-item { color:#d97706; font-size:0.85rem; }
.success-item { color:#16a34a; font-size:0.85rem; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="page-header">
    <p class="page-title">📁 Upload & Validate</p>
    <p class="page-sub">Upload candidate data and job description · Validate schema · Preview records</p>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Upload widgets
# ---------------------------------------------------------------------------
col_left, col_right = st.columns(2)

with col_left:
    st.markdown("### 📄 Job Description")
    jd_file = st.file_uploader(
        "Upload job description",
        type=["docx", "txt", "md"],
        key="jd_uploader",
        help="Supports .docx, .txt, .md"
    )
    use_default_jd = st.checkbox("Use bundled job_description.docx", value=True)
    if use_default_jd and not jd_file:
        default_jd_path = Path("Challenge_data/Raw/job_description.docx")
        if default_jd_path.exists():
            st.success(f"✅ Using default: {default_jd_path}")
            try:
                job_text = load_job_description(default_jd_path)
                st.session_state["job_text"] = job_text
                with st.expander("📖 Preview job description (first 800 chars)"):
                    st.text(job_text[:800] + ("..." if len(job_text) > 800 else ""))
            except Exception as e:
                st.error(f"Failed to load default JD: {e}")
        else:
            st.warning(f"Default file not found: {default_jd_path}")

    if jd_file:
        suffix = Path(jd_file.name).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(jd_file.read())
            tmp_path = tmp.name
        try:
            job_text = load_job_description(tmp_path)
            st.session_state["job_text"] = job_text
            st.success(f"✅ Job description loaded: {len(job_text)} characters")
            with st.expander("📖 Preview (first 800 chars)"):
                st.text(job_text[:800] + ("..." if len(job_text) > 800 else ""))
        except Exception as e:
            st.error(f"Failed to load job description: {e}")
        finally:
            Path(tmp_path).unlink(missing_ok=True)

with col_right:
    st.markdown("### 👥 Candidate Data")
    candidate_file = st.file_uploader(
        "Upload candidates",
        type=["json", "jsonl", "gz"],
        key="candidates_uploader",
        help="Supports .json (list), .jsonl, .jsonl.gz"
    )
    use_sample = st.checkbox("Use sample_candidates.json (demo)", value=True)

    sample_path = Path("Challenge_data/Sample/sample_candidates.json")

    if use_sample and not candidate_file:
        if sample_path.exists():
            st.success(f"✅ Using sample: {sample_path}")
            st.session_state["candidates_path"] = str(sample_path)
        else:
            st.warning(f"Sample file not found: {sample_path}")

    if candidate_file:
        suffix = "".join(Path(candidate_file.name).suffixes)
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(candidate_file.read())
            tmp_path = tmp.name

        st.session_state["candidates_path"] = tmp_path
        st.success(f"✅ Uploaded: {candidate_file.name} ({candidate_file.size / 1024:.1f} KB)")

# ---------------------------------------------------------------------------
# Validate button
# ---------------------------------------------------------------------------
st.markdown("---")
if st.button("🔍 Validate Candidates", use_container_width=True):
    cpath = st.session_state.get("candidates_path")
    if not cpath or not Path(cpath).exists():
        st.error("Please upload or select a candidates file first.")
    else:
        with st.spinner("Validating candidates..."):
            try:
                records = list(stream_candidates(cpath))
                valid_records, results = validate_batch(records)

                # Store for later stages
                st.session_state["all_candidates_raw"] = records
                st.session_state["valid_candidates"] = valid_records
                st.session_state["validation_results"] = results

                invalid = [vr for vr in results if not vr.is_valid]
                warned = [vr for vr in results if vr.warnings]

                # Summary
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total Records", len(records))
                c2.metric("Valid", len(valid_records), delta=None)
                c3.metric("Invalid", len(invalid), delta=f"-{len(invalid)}" if invalid else "0")
                c4.metric("With Warnings", len(warned))

                # Error details
                if invalid:
                    with st.expander(f"❌ Invalid Records ({len(invalid)} errors)", expanded=False):
                        for vr in invalid[:50]:
                            st.markdown(f"**{vr.candidate_id}**")
                            for err in vr.errors:
                                st.markdown(f'<span class="error-item">  ✗ {err}</span>', unsafe_allow_html=True)

                if warned:
                    with st.expander(f"⚠️ Records with Warnings ({len(warned)})", expanded=False):
                        for vr in warned[:30]:
                            if vr.warnings:
                                st.markdown(f"**{vr.candidate_id}**")
                                for w in vr.warnings[:3]:
                                    st.markdown(f'<span class="warn-item">  ⚠ {w}</span>', unsafe_allow_html=True)

                st.success(f"✅ Validation complete: {len(valid_records)} valid candidates ready for ranking.")

            except Exception as e:
                st.error(f"Validation failed: {e}")
                logger.exception("Validation error")

# ---------------------------------------------------------------------------
# Sample candidate preview
# ---------------------------------------------------------------------------
st.markdown("---")
st.markdown("### 🔎 Sample Candidate Preview")

cpath = st.session_state.get("candidates_path")
if cpath and Path(cpath).exists():
    try:
        candidates_preview = []
        for i, c in enumerate(stream_candidates(cpath)):
            candidates_preview.append(c)
            if i >= 4:
                break

        if candidates_preview:
            selected = st.selectbox(
                "Select candidate to preview",
                options=[c.get("candidate_id", f"#{i}") for i, c in enumerate(candidates_preview)],
            )
            idx = next(i for i, c in enumerate(candidates_preview) if c.get("candidate_id") == selected)
            cand = candidates_preview[idx]

            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("**Profile**")
                profile = cand.get("profile", {})
                st.markdown(f"""
                - **Name:** {profile.get('anonymized_name', 'N/A')}
                - **Title:** {profile.get('current_title', 'N/A')}
                - **YOE:** {profile.get('years_of_experience', 'N/A')} years
                - **Location:** {profile.get('location', 'N/A')}, {profile.get('country', 'N/A')}
                - **Company:** {profile.get('current_company', 'N/A')} ({profile.get('current_company_size', 'N/A')})
                - **Headline:** {profile.get('headline', 'N/A')}
                """)

            with col_b:
                st.markdown("**Redrob Signals**")
                signals = cand.get("redrob_signals", {})
                st.markdown(f"""
                - **Open to work:** {signals.get('open_to_work_flag', 'N/A')}
                - **Last active:** {signals.get('last_active_date', 'N/A')}
                - **Recruiter response rate:** {signals.get('recruiter_response_rate', 'N/A')}
                - **Notice period:** {signals.get('notice_period_days', 'N/A')} days
                - **GitHub activity:** {signals.get('github_activity_score', 'N/A')}
                - **Profile completeness:** {signals.get('profile_completeness_score', 'N/A')}%
                """)

            with st.expander("📋 Full JSON Record"):
                st.json(cand)
    except Exception as e:
        st.error(f"Could not preview candidates: {e}")
else:
    st.info("Upload or select a candidates file to preview.")
