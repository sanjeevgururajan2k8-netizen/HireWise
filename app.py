"""
HireWise AI — Streamlit Application Entry Point
=================================================
Page 1: Overview — Project overview, architecture, and key stats.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st

# ---------------------------------------------------------------------------
# Page configuration
# ---------------------------------------------------------------------------
from src.theme import apply_theme

st.set_page_config(
    page_title="HireWise AI — Intelligent Candidate Discovery",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_theme()

# ---------------------------------------------------------------------------
# CSS theme - load styling from theme
# ---------------------------------------------------------------------------
# Theme styling is applied globally via apply_theme() above


# ---------------------------------------------------------------------------
# Hero Section
# ---------------------------------------------------------------------------
st.markdown("""
<div class="hero-container">
    <p class="hero-title">🧠 HireWise AI</p>
    <p class="hero-subtitle">Intelligent Candidate Discovery & Ranking — Redrob Hackathon Submission</p>
    <span class="hero-badge">⚡ CPU-Only · No External APIs · Explainable AI · 100K Candidates</span>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Retrieve stats from session state (set by ranking pipeline)
# ---------------------------------------------------------------------------
stats = st.session_state.get("pipeline_stats", {})

# ---------------------------------------------------------------------------
# Key metrics
# ---------------------------------------------------------------------------
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.markdown(f"""
    <div class="stat-card">
        <p class="stat-number">{stats.get('total_processed', '—')}</p>
        <p class="stat-label">Candidates Analysed</p>
    </div>""", unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="stat-card">
        <p class="stat-number">{stats.get('valid_count', '—')}</p>
        <p class="stat-label">Valid Profiles</p>
    </div>""", unsafe_allow_html=True)

with col3:
    suspicious = stats.get('high_risk', 0) + stats.get('medium_risk', 0)
    st.markdown(f"""
    <div class="stat-card">
        <p class="stat-number">{suspicious if stats else '—'}</p>
        <p class="stat-label">Suspicious Profiles</p>
    </div>""", unsafe_allow_html=True)

with col4:
    runtime = stats.get('runtime_seconds', None)
    runtime_str = f"{runtime:.1f}s" if runtime else "—"
    st.markdown(f"""
    <div class="stat-card">
        <p class="stat-number">{runtime_str}</p>
        <p class="stat-label">Ranking Runtime</p>
    </div>""", unsafe_allow_html=True)

with col5:
    top_score = stats.get('top_score', None)
    top_str = f"{top_score:.4f}" if top_score else "—"
    st.markdown(f"""
    <div class="stat-card">
        <p class="stat-number">{top_str}</p>
        <p class="stat-label">Top Score</p>
    </div>""", unsafe_allow_html=True)

st.markdown("---")

# ---------------------------------------------------------------------------
# Two columns: Target Job + Quick Launch
# ---------------------------------------------------------------------------
left, right = st.columns([2, 1])

with left:
    st.markdown('<p class="section-header">🎯 Target Position</p>', unsafe_allow_html=True)
    st.markdown("""
    | Field | Details |
    |---|---|
    | **Role** | Senior AI Engineer — Founding Team |
    | **Company** | Redrob AI |
    | **Location** | Pune or Noida, India (Hybrid) |
    | **Experience** | ~5–9 years (not a strict cutoff) |
    | **Focus** | Retrieval · Ranking · Vector Search · Production ML |
    """)

with right:
    st.markdown('<p class="section-header">🚀 Quick Launch</p>', unsafe_allow_html=True)
    st.info("Run the full ranking pipeline from the sidebar pages, or click below to go directly.")
    if st.button("▶ Launch Ranking Pipeline", use_container_width=True):
        st.switch_page("pages/2_Run_Ranking.py")

st.markdown("---")

# ---------------------------------------------------------------------------
# Ranking Architecture
# ---------------------------------------------------------------------------
st.markdown('<p class="section-header">⚙️ Ranking Architecture</p>', unsafe_allow_html=True)

stages = [
    ("A", "Input Validation", "Validates every candidate against the schema with cross-field checks (date order, skill duration vs experience, signup vs last_active)."),
    ("B", "Weighted Text Construction", "Builds separate text fields per candidate. Career descriptions weighted 3×, titles 2.5×, skills only 1× — preventing keyword stuffing from dominating."),
    ("C", "Lexical Relevance (TF-IDF)", "TF-IDF with word n-grams (1-3) + char n-grams (3-5) and a synonym map (e.g. FAISS → vector database) for cosine similarity scoring."),
    ("D", "Evidence-Based Feature Scoring", "15 named feature scores. Production action verbs (built, deployed, shipped) required for high retrieval/ranking scores."),
    ("E", "Behavioural Modifier", "Redrob signals as a capped multiplier [0.75–1.10]. Cannot make a technically irrelevant candidate rank highly."),
    ("F", "Integrity & Honeypot Detection", "10 explicit rule checks: overlapping dates, skill duration impossibilities, title/career mismatches, templated summaries."),
    ("G", "Optional Semantic Re-ranking", "Precomputed all-MiniLM-L6-v2 embeddings blended in when available. Falls back to TF-IDF if not present."),
    ("H", "Final Score + Tie-breaking", "Weighted formula → behavioural modifier → integrity penalty → keyword stuffing penalty. Deterministic tie-breaking by integrity, then evidence, then candidate_id."),
]

cols_per_row = 2
for i in range(0, len(stages), cols_per_row):
    row_cols = st.columns(cols_per_row)
    for j, col in enumerate(row_cols):
        if i + j < len(stages):
            letter, title, desc = stages[i + j]
            with col:
                st.markdown(f"""
                <div class="stage-card">
                    <div class="stage-title">Stage {letter}: {title}</div>
                    <div class="stage-desc">{desc}</div>
                </div>""", unsafe_allow_html=True)

st.markdown("---")

# ---------------------------------------------------------------------------
# Compute Constraints
# ---------------------------------------------------------------------------
st.markdown('<p class="section-header">💻 Compute Constraints</p>', unsafe_allow_html=True)

constraints = [
    "⏱ ≤5 min wall-clock",
    "💾 ≤16 GB RAM",
    "🖥 CPU only (no GPU)",
    "🌐 No network calls",
    "🔌 No hosted AI APIs",
    "💿 ≤5 GB intermediate disk",
    "🔢 Deterministic results",
    "🔄 Streaming (no full-load into RAM)",
]

st.markdown(" ".join(f'<span class="constraint-chip">{c}</span>' for c in constraints), unsafe_allow_html=True)

st.markdown("---")

# ---------------------------------------------------------------------------
# Navigation guide
# ---------------------------------------------------------------------------
st.markdown('<p class="section-header">📍 Navigation Guide</p>', unsafe_allow_html=True)

nav_items = [
    ("📁 Upload & Validate", "Upload candidate files and validate schema"),
    ("▶ Run Ranking", "Execute the full ranking pipeline"),
    ("🏆 Candidate Rankings", "Browse and filter the top 100 ranked candidates"),
    ("👤 Candidate Detail", "Deep-dive into any candidate's full profile and scores"),
    ("📊 Analytics", "Score distributions, skill maps, integrity visualisations"),
    ("📖 Methodology", "Detailed explanation of the ranking approach"),
    ("⬇ Export", "Download submission CSV and reports"),
]

for name, desc in nav_items:
    st.markdown(f"- **{name}** — {desc}")

st.markdown("---")
st.markdown(
    "<div style='text-align:center; color:#94a3b8; font-size:0.82rem;'>"
    "HireWise AI · Redrob Hackathon · Built with Python 3.11 · Scikit-learn · Streamlit"
    "</div>",
    unsafe_allow_html=True,
)
