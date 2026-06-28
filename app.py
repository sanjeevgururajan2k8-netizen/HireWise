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
# CSS theme — blue / white / neutral-gray
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* Dark sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0f172a 0%, #1e3a5f 100%);
        color: #f1f5f9;
    }
    [data-testid="stSidebar"] * { color: #f1f5f9 !important; }
    [data-testid="stSidebar"] .stRadio label { color: #cbd5e1 !important; }

    /* Main background */
    .main { background-color: #f8fafc; }

    /* Hero header */
    .hero-container {
        background: linear-gradient(135deg, #0f172a 0%, #1e40af 50%, #0ea5e9 100%);
        border-radius: 16px;
        padding: 40px 48px;
        margin-bottom: 32px;
        color: white;
    }
    .hero-title {
        font-size: 2.8rem;
        font-weight: 800;
        letter-spacing: -0.5px;
        margin: 0;
        background: linear-gradient(90deg, #ffffff, #93c5fd);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .hero-subtitle {
        font-size: 1.1rem;
        color: #cbd5e1;
        margin-top: 8px;
    }
    .hero-badge {
        display: inline-block;
        background: rgba(255,255,255,0.15);
        border: 1px solid rgba(255,255,255,0.3);
        border-radius: 20px;
        padding: 4px 16px;
        font-size: 0.85rem;
        color: #e2e8f0;
        margin-top: 12px;
        backdrop-filter: blur(4px);
    }

    /* Stats cards */
    .stat-card {
        background: white;
        border-radius: 12px;
        padding: 24px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08), 0 4px 16px rgba(0,0,0,0.04);
        border: 1px solid #e2e8f0;
        text-align: center;
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .stat-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.12);
    }
    .stat-number {
        font-size: 2.2rem;
        font-weight: 800;
        color: #1e40af;
        margin: 0;
    }
    .stat-label {
        font-size: 0.85rem;
        color: #64748b;
        font-weight: 500;
        margin-top: 4px;
    }

    /* Section headers */
    .section-header {
        font-size: 1.4rem;
        font-weight: 700;
        color: #0f172a;
        margin: 24px 0 12px 0;
        padding-bottom: 8px;
        border-bottom: 2px solid #3b82f6;
        display: inline-block;
    }

    /* Pipeline stages */
    .stage-card {
        background: white;
        border-left: 4px solid #3b82f6;
        border-radius: 8px;
        padding: 16px 20px;
        margin: 8px 0;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }
    .stage-title { font-weight: 600; color: #1e40af; font-size: 0.95rem; }
    .stage-desc { color: #475569; font-size: 0.88rem; margin-top: 4px; }

    /* Compute constraint badge */
    .constraint-chip {
        display: inline-block;
        background: #eff6ff;
        color: #1d4ed8;
        border: 1px solid #bfdbfe;
        border-radius: 20px;
        padding: 4px 14px;
        font-size: 0.82rem;
        font-weight: 500;
        margin: 4px;
    }

    /* Launch button */
    .stButton > button {
        background: linear-gradient(135deg, #2563eb, #0ea5e9) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        padding: 12px 28px !important;
        font-size: 1rem !important;
        transition: all 0.2s !important;
    }
    .stButton > button:hover {
        opacity: 0.9 !important;
        transform: translateY(-1px) !important;
    }
</style>
""", unsafe_allow_html=True)

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
