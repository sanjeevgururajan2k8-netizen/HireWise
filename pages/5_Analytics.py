"""
HireWise AI — Page 5: Analytics
===================================
Visual analytics dashboard: score distributions, skills, locations, integrity.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Analytics — HireWise AI", page_icon="📊", layout="wide")

from src.theme import apply_theme
apply_theme()

st.markdown("""
<div class="page-header header-analytics">
    <div class="page-title">📊 Analytics Dashboard</div>
    <div class="page-sub">Score distributions · Skill analysis · Location map · Integrity insights</div>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Data availability check
# ---------------------------------------------------------------------------
df: pd.DataFrame | None = st.session_state.get("rankings_df")
top_scores = st.session_state.get("top_scores", [])
candidates_dict = st.session_state.get("candidates_dict", {})
integrity_results = st.session_state.get("integrity_results", {})

if df is None or df.empty:
    st.warning("⚠️ No ranking data found. Please run the pipeline first.")
    if st.button("▶ Go to Run Ranking"):
        st.switch_page("pages/2_Run_Ranking.py")
    st.stop()

# ---------------------------------------------------------------------------
# Row 1: Score distribution + Experience distribution
# ---------------------------------------------------------------------------
r1c1, r1c2 = st.columns(2)

with r1c1:
    st.markdown("#### Score Distribution (Top 100)")
    fig = px.histogram(
        df,
        x="Final Score",
        nbins=20,
        color="Category",
        color_discrete_map={
            "Excellent fit": "#16a34a",
            "Strong fit": "#2563eb",
            "Moderate fit": "#d97706",
            "Limited fit": "#dc2626",
        },
        title="",
    )
    fig.update_layout(height=300, margin=dict(l=20, r=20, t=10, b=20))
    st.plotly_chart(fig, use_container_width=True)

with r1c2:
    st.markdown("#### Experience Distribution (Top 100)")
    fig2 = px.histogram(
        df,
        x="YOE",
        nbins=15,
        color_discrete_sequence=["#3b82f6"],
        labels={"YOE": "Years of Experience"},
    )
    fig2.add_vrect(x0=5, x1=9, fillcolor="#16a34a", opacity=0.1, annotation_text="Optimal range")
    fig2.update_layout(height=300, margin=dict(l=20, r=20, t=10, b=20))
    st.plotly_chart(fig2, use_container_width=True)

# ---------------------------------------------------------------------------
# Row 2: Open-to-work + Honeypot risk distribution
# ---------------------------------------------------------------------------
r2c1, r2c2 = st.columns(2)

with r2c1:
    st.markdown("#### Open-to-Work Status")
    otw_counts = df["Open to Work"].value_counts().reset_index()
    otw_counts.columns = ["Status", "Count"]
    otw_counts["Status"] = otw_counts["Status"].map({True: "Open to Work", False: "Not Open"})
    fig3 = px.pie(
        otw_counts,
        values="Count",
        names="Status",
        color_discrete_map={"Open to Work": "#16a34a", "Not Open": "#94a3b8"},
    )
    fig3.update_layout(height=280, margin=dict(l=10, r=10, t=10, b=10))
    st.plotly_chart(fig3, use_container_width=True)

with r2c2:
    st.markdown("#### Integrity Risk Distribution")
    risk_counts = df["Honeypot Risk"].value_counts().reset_index()
    risk_counts.columns = ["Risk", "Count"]
    fig4 = px.bar(
        risk_counts,
        x="Risk",
        y="Count",
        color="Risk",
        color_discrete_map={"low": "#16a34a", "medium": "#f59e0b", "high": "#dc2626"},
    )
    fig4.update_layout(height=280, margin=dict(l=20, r=20, t=10, b=20), showlegend=False)
    st.plotly_chart(fig4, use_container_width=True)

# ---------------------------------------------------------------------------
# Row 3: Technical fit vs Behavioural score scatter + Category bar
# ---------------------------------------------------------------------------
r3c1, r3c2 = st.columns(2)

with r3c1:
    st.markdown("#### Technical Fit vs Behavioural Score")
    fig5 = px.scatter(
        df,
        x="Technical Fit",
        y="Behaviour Score",
        color="Category",
        hover_data=["Candidate ID", "Current Title", "Final Score"],
        color_discrete_map={
            "Excellent fit": "#16a34a",
            "Strong fit": "#2563eb",
            "Moderate fit": "#d97706",
            "Limited fit": "#dc2626",
        },
        opacity=0.8,
    )
    fig5.update_layout(height=320, margin=dict(l=20, r=20, t=10, b=20))
    st.plotly_chart(fig5, use_container_width=True)

with r3c2:
    st.markdown("#### Recommendation Categories")
    cat_counts = df["Category"].value_counts().reset_index()
    cat_counts.columns = ["Category", "Count"]
    fig6 = px.bar(
        cat_counts,
        x="Category",
        y="Count",
        color="Category",
        color_discrete_map={
            "Excellent fit": "#16a34a",
            "Strong fit": "#2563eb",
            "Moderate fit": "#d97706",
            "Limited fit": "#dc2626",
        },
    )
    fig6.update_layout(height=320, margin=dict(l=20, r=20, t=10, b=20), showlegend=False)
    st.plotly_chart(fig6, use_container_width=True)

# ---------------------------------------------------------------------------
# Row 4: Top-10 score breakdown (stacked bar)
# ---------------------------------------------------------------------------
st.markdown("---")
st.markdown("#### Top-10 Candidate Score Breakdown")

if top_scores:
    top10 = top_scores[:10]
    breakdown_data = []
    for i, cs in enumerate(top10):
        row = {"Rank": f"#{i+1}", **cs.features}
        breakdown_data.append(row)

    breakdown_df = pd.DataFrame(breakdown_data)

    feat_cols = [c for c in breakdown_df.columns if c != "Rank"]
    fig7 = go.Figure()
    color_palette = px.colors.qualitative.Plotly
    for j, feat in enumerate(feat_cols):
        fig7.add_trace(go.Bar(
            name=feat.replace("_score", "").replace("_", " ").title(),
            x=breakdown_df["Rank"],
            y=breakdown_df[feat],
            marker_color=color_palette[j % len(color_palette)],
        ))
    fig7.update_layout(
        barmode="stack",
        height=380,
        margin=dict(l=20, r=20, t=10, b=20),
        xaxis_title="Rank",
        yaxis_title="Feature Score Sum",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    st.plotly_chart(fig7, use_container_width=True)

# ---------------------------------------------------------------------------
# Row 5: Top skills analysis across all candidates
# ---------------------------------------------------------------------------
st.markdown("---")
st.markdown("#### Top Skills in Ranked Candidates")

skill_counts: dict[str, int] = {}
for cid, cand in candidates_dict.items():
    # Only include candidates in top_scores
    if cid in {cs.candidate_id for cs in top_scores}:
        for sk in cand.get("skills", []):
            if isinstance(sk, dict) and sk.get("name"):
                name = sk["name"]
                skill_counts[name] = skill_counts.get(name, 0) + 1

top_skills_df = pd.DataFrame(
    sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:25],
    columns=["Skill", "Count"],
)

if not top_skills_df.empty:
    fig8 = px.bar(
        top_skills_df,
        x="Count",
        y="Skill",
        orientation="h",
        color="Count",
        color_continuous_scale="Blues",
    )
    fig8.update_layout(height=500, margin=dict(l=160, r=20, t=10, b=20), coloraxis_showscale=False)
    st.plotly_chart(fig8, use_container_width=True)

# ---------------------------------------------------------------------------
# Pipeline stats summary
# ---------------------------------------------------------------------------
st.markdown("---")
st.markdown("#### Pipeline Stats")
stats = st.session_state.get("pipeline_stats", {})
if stats:
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total Processed", stats.get("total_processed", "—"))
    c2.metric("Valid Profiles", stats.get("valid_count", "—"))
    c3.metric("Skipped", stats.get("skipped", "—"))
    c4.metric("High-Risk", stats.get("high_risk", "—"))
    c5.metric("Runtime (s)", f"{stats.get('runtime_seconds', 0):.1f}")
