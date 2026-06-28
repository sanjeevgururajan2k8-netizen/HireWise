"""
HireWise AI — Page 3: Candidate Rankings
==========================================
Interactive table of top 100 ranked candidates with filters.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Candidate Rankings — HireWise AI", page_icon="🏆", layout="wide")

from src.theme import apply_theme
apply_theme()

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
[data-testid="stSidebar"] { background: linear-gradient(180deg, #0f172a, #1e3a5f); color: #f1f5f9; }
[data-testid="stSidebar"] * { color: #f1f5f9 !important; }
.page-header { background: linear-gradient(135deg, #312e81, #4f46e5); border-radius:12px; padding:28px 36px; color:white; margin-bottom:24px; }
.page-title { font-size:1.8rem; font-weight:800; margin:0; }
.cat-excellent { background:#dcfce7; color:#15803d; padding:3px 10px; border-radius:12px; font-size:0.78rem; font-weight:600; }
.cat-strong { background:#dbeafe; color:#1d4ed8; padding:3px 10px; border-radius:12px; font-size:0.78rem; font-weight:600; }
.cat-moderate { background:#fef9c3; color:#854d0e; padding:3px 10px; border-radius:12px; font-size:0.78rem; font-weight:600; }
.cat-limited { background:#fee2e2; color:#b91c1c; padding:3px 10px; border-radius:12px; font-size:0.78rem; font-weight:600; }
.risk-high { color:#dc2626; font-weight:600; }
.risk-medium { color:#d97706; font-weight:600; }
.risk-low { color:#16a34a; font-weight:600; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="page-header">
    <p class="page-title">🏆 Candidate Rankings</p>
    <p style="color:#c7d2fe; margin-top:4px;">Filter · Sort · Explore the top-ranked candidates</p>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Check for data
# ---------------------------------------------------------------------------
df: pd.DataFrame | None = st.session_state.get("rankings_df")

if df is None or df.empty:
    st.warning("⚠️ No ranking results found. Please run the pipeline on the **Run Ranking** page first.")
    if st.button("▶ Go to Run Ranking"):
        st.switch_page("pages/2_Run_Ranking.py")
    st.stop()

# ---------------------------------------------------------------------------
# Filters sidebar
# ---------------------------------------------------------------------------
st.sidebar.markdown("## 🔽 Filters")

# Score range
score_min, score_max = st.sidebar.slider(
    "Final Score Range",
    min_value=0.0,
    max_value=1.0,
    value=(0.0, 1.0),
    step=0.01,
)

# Category
all_categories = sorted(df["Category"].unique().tolist())
selected_cats = st.sidebar.multiselect("Recommendation Category", all_categories, default=all_categories)

# Honeypot risk
all_risks = sorted(df["Honeypot Risk"].unique().tolist())
selected_risks = st.sidebar.multiselect("Honeypot Risk", all_risks, default=all_risks)

# Open to work
open_filter = st.sidebar.selectbox("Open to Work", ["All", "Yes", "No"])

# Experience range
yoe_min, yoe_max = float(df["YOE"].min()), float(df["YOE"].max())
exp_range = st.sidebar.slider(
    "Years of Experience",
    min_value=0.0,
    max_value=max(20.0, yoe_max),
    value=(0.0, max(20.0, yoe_max)),
    step=0.5,
)

# Search by title
title_search = st.sidebar.text_input("Filter by title (partial match)", "")

# ---------------------------------------------------------------------------
# Apply filters
# ---------------------------------------------------------------------------
filtered = df.copy()
filtered = filtered[filtered["Final Score"].between(score_min, score_max)]
if selected_cats:
    filtered = filtered[filtered["Category"].isin(selected_cats)]
if selected_risks:
    filtered = filtered[filtered["Honeypot Risk"].isin(selected_risks)]
if open_filter == "Yes":
    filtered = filtered[filtered["Open to Work"] == True]
elif open_filter == "No":
    filtered = filtered[filtered["Open to Work"] == False]
filtered = filtered[filtered["YOE"].between(exp_range[0], exp_range[1])]
if title_search:
    filtered = filtered[filtered["Current Title"].str.contains(title_search, case=False, na=False)]

# ---------------------------------------------------------------------------
# Summary metrics
# ---------------------------------------------------------------------------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Showing", len(filtered))
c2.metric("Excellent Fit", len(filtered[filtered["Category"] == "Excellent fit"]))
c3.metric("Strong Fit", len(filtered[filtered["Category"] == "Strong fit"]))
c4.metric("High-Risk Profiles", len(filtered[filtered["Honeypot Risk"] == "high"]))

st.markdown("---")

# ---------------------------------------------------------------------------
# Display table
# ---------------------------------------------------------------------------
display_cols = [
    "Rank", "Candidate ID", "Name", "Current Title", "YOE",
    "Location", "Final Score", "Technical Fit",
    "Behaviour Score", "Integrity Score", "Honeypot Risk",
    "Open to Work", "Category",
]

available_cols = [c for c in display_cols if c in filtered.columns]

# Format scores for display
display_df = filtered[available_cols].copy()
for col in ["Final Score", "Technical Fit", "Behaviour Score", "Integrity Score"]:
    if col in display_df.columns:
        display_df[col] = display_df[col].map(lambda x: f"{x:.4f}")

st.dataframe(
    display_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Rank": st.column_config.NumberColumn("Rank", width="small"),
        "Final Score": st.column_config.TextColumn("Score"),
        "Technical Fit": st.column_config.TextColumn("Tech Fit"),
        "Open to Work": st.column_config.CheckboxColumn("Open to Work"),
    },
    height=600,
)

# ---------------------------------------------------------------------------
# Candidate selection for detail view
# ---------------------------------------------------------------------------
st.markdown("---")
st.markdown("### 👤 View Candidate Detail")

if not filtered.empty:
    selected_id = st.selectbox(
        "Select a candidate to view full profile",
        options=filtered["Candidate ID"].tolist(),
        format_func=lambda cid: f"#{filtered.loc[filtered['Candidate ID']==cid, 'Rank'].values[0]} — {cid} — {filtered.loc[filtered['Candidate ID']==cid, 'Current Title'].values[0]}",
    )

    if st.button("👤 Open Full Profile", use_container_width=False):
        st.session_state["selected_candidate_id"] = selected_id
        st.switch_page("pages/4_Candidate_Detail.py")
