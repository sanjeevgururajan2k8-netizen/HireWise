"""
HireWise AI — Page 4: Candidate Detail
=========================================
Full profile view with career timeline, skill breakdown,
score components, integrity flags, and reasoning.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Candidate Detail — HireWise AI", page_icon="👤", layout="wide")

from src.theme import apply_theme
apply_theme()

# Theme styling is applied globally via apply_theme() above


# ---------------------------------------------------------------------------
# Data availability check
# ---------------------------------------------------------------------------
top_scores = st.session_state.get("top_scores", [])
candidates_dict = st.session_state.get("candidates_dict", {})
integrity_results = st.session_state.get("integrity_results", {})
reasonings = st.session_state.get("reasonings", [])
rankings_df = st.session_state.get("rankings_df")

if not top_scores or not candidates_dict:
    st.warning("⚠️ No ranking data found. Please run the pipeline first.")
    if st.button("▶ Go to Run Ranking"):
        st.switch_page("pages/2_Run_Ranking.py")
    st.stop()

# Build lookup dicts
score_by_id = {cs.candidate_id: cs for cs in top_scores}
reasoning_by_id = {cs.candidate_id: r for cs, r in zip(top_scores, reasonings)}
rank_by_id = {cs.candidate_id: i + 1 for i, cs in enumerate(top_scores)}

# ---------------------------------------------------------------------------
# Candidate selector
# ---------------------------------------------------------------------------
selected_id = st.session_state.get("selected_candidate_id")
all_ids = [cs.candidate_id for cs in top_scores]

selected_id = st.selectbox(
    "Select candidate",
    options=all_ids,
    index=all_ids.index(selected_id) if selected_id in all_ids else 0,
    format_func=lambda cid: f"#{rank_by_id[cid]} — {cid} — {candidates_dict.get(cid, {}).get('profile', {}).get('current_title', '')}",
)

cand = candidates_dict.get(selected_id, {})
cs = score_by_id.get(selected_id)
ir = integrity_results.get(selected_id)
reasoning = reasoning_by_id.get(selected_id, "")

if not cand or not cs:
    st.error("Candidate data not found.")
    st.stop()

profile = cand.get("profile", {})
career = cand.get("career_history", [])
education = cand.get("education", [])
skills = cand.get("skills", [])
certs = cand.get("certifications", [])
signals = cand.get("redrob_signals", {})
rank_num = rank_by_id.get(selected_id, "?")

# Header
st.markdown(f"""
<div class="page-header header-detail">
    <p class="page-title">👤 {profile.get('anonymized_name', selected_id)}</p>
    <p class="page-sub">Rank #{rank_num} · {profile.get('current_title', '')} · {profile.get('location', '')} · Score: {cs.final_score:.4f}</p>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Top section: Profile + Score breakdown
# ---------------------------------------------------------------------------
left, right = st.columns([1, 1])

with left:
    st.markdown("### 📋 Basic Profile")
    st.markdown(f"""
    | Field | Value |
    |---|---|
    | **ID** | `{selected_id}` |
    | **Headline** | {profile.get('headline', 'N/A')} |
    | **Current Title** | {profile.get('current_title', 'N/A')} |
    | **Company** | {profile.get('current_company', 'N/A')} ({profile.get('current_company_size', 'N/A')}) |
    | **Industry** | {profile.get('current_industry', 'N/A')} |
    | **Experience** | {profile.get('years_of_experience', 'N/A')} years |
    | **Location** | {profile.get('location', 'N/A')}, {profile.get('country', 'N/A')} |
    """)

    st.markdown("**Professional Summary**")
    st.info(profile.get("summary", "No summary provided."))

with right:
    st.markdown("### 📊 Score Breakdown")

    # Radar chart of key feature scores
    feat = cs.features
    categories = [
        "Retrieval\nProduction", "Vector\nSearch", "Ranking\nEvaluation",
        "Python\nEngineering", "ML\nProduction", "Product\nShipping",
        "LLM\nFine-tuning", "Experience\nFit"
    ]
    feat_keys = [
        "retrieval_production_score", "vector_search_score", "ranking_evaluation_score",
        "python_engineering_score", "ml_production_score", "product_shipping_score",
        "llm_finetuning_score", "experience_fit_score"
    ]
    values = [feat.get(k, 0.0) for k in feat_keys]
    values_closed = values + [values[0]]
    categories_closed = categories + [categories[0]]

    fig = go.Figure(data=go.Scatterpolar(
        r=values_closed,
        theta=categories_closed,
        fill='toself',
        fillcolor='rgba(37, 99, 235, 0.2)',
        line=dict(color='#2563eb', width=2),
        name="Feature Scores"
    ))
    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        showlegend=False,
        height=320,
        margin=dict(l=40, r=40, t=20, b=20),
    )
    st.plotly_chart(fig, use_container_width=True)

    col_a, col_b = st.columns(2)
    col_a.metric("Final Score", f"{cs.final_score:.4f}")
    col_b.metric("Technical Fit", f"{cs.feature_score:.4f}")
    col_a.metric("Behaviour", f"{cs.behaviour_score:.4f}")
    col_b.metric("Integrity", f"{cs.integrity_score:.4f}")

# ---------------------------------------------------------------------------
# Career Timeline
# ---------------------------------------------------------------------------
st.markdown("---")
st.markdown("### 🗓 Career Timeline")

for role in career:
    if not isinstance(role, dict):
        continue
    start = role.get("start_date", "?")
    end = role.get("end_date", "Present") or "Present"
    is_current = role.get("is_current", False)
    badge = "🟢 Current" if is_current else ""
    st.markdown(f"""
    <div class="timeline-entry">
        <strong>{role.get('title', '?')}</strong> @ {role.get('company', '?')} {badge}<br>
        <small style="color:#64748b">{start} → {end} · {role.get('duration_months', '?')} months · {role.get('industry', '?')} · {role.get('company_size', '?')}</small><br>
        <p style="margin-top:6px; font-size:0.88rem; color:#374151">{role.get('description', '')}</p>
    </div>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Education + Skills + Certs (3 columns)
# ---------------------------------------------------------------------------
st.markdown("---")
e_col, s_col, c_col = st.columns(3)

with e_col:
    st.markdown("### 🎓 Education")
    for edu in education:
        if isinstance(edu, dict):
            st.markdown(f"""
            **{edu.get('degree', '?')}** in {edu.get('field_of_study', '?')}
            *{edu.get('institution', '?')}* · {edu.get('start_year', '?')}–{edu.get('end_year', '?')}
            Tier: `{edu.get('tier', '?')}` · Grade: {edu.get('grade', 'N/A')}
            ---
            """)

with s_col:
    st.markdown("### 🛠 Skills")
    prof_order = {"expert": 0, "advanced": 1, "intermediate": 2, "beginner": 3}
    sorted_skills = sorted(skills, key=lambda s: prof_order.get(s.get("proficiency", "beginner"), 3) if isinstance(s, dict) else 3)
    for sk in sorted_skills[:20]:
        if not isinstance(sk, dict):
            continue
        prof = sk.get("proficiency", "beginner")
        dur = sk.get("duration_months", 0)
        endr = sk.get("endorsements", 0)
        css_class = f"skill-{prof}"
        st.markdown(
            f'<span class="{css_class}" style="display:inline-block; padding:3px 10px; border-radius:12px; font-size:0.8rem; margin:2px; font-weight:500;">'
            f'{sk.get("name", "?")} ({prof}, {dur}mo, ⭐{endr})'
            f'</span>',
            unsafe_allow_html=True,
        )

with c_col:
    st.markdown("### 📜 Certifications")
    if certs:
        for cert in certs:
            if isinstance(cert, dict):
                st.markdown(f"- **{cert.get('name', '?')}** — {cert.get('issuer', '?')} ({cert.get('year', '?')})")
    else:
        st.write("No certifications listed.")

    st.markdown("### 📡 Redrob Signals")
    st.markdown(f"""
    - Open to work: `{signals.get('open_to_work_flag', 'N/A')}`
    - Last active: `{signals.get('last_active_date', 'N/A')}`
    - Response rate: `{signals.get('recruiter_response_rate', 'N/A')}`
    - Notice period: `{signals.get('notice_period_days', 'N/A')}` days
    - Work mode: `{signals.get('preferred_work_mode', 'N/A')}`
    - Relocate: `{signals.get('willing_to_relocate', 'N/A')}`
    - GitHub: `{signals.get('github_activity_score', 'N/A')}`
    - Interview completion: `{signals.get('interview_completion_rate', 'N/A')}`
    """)

# ---------------------------------------------------------------------------
# Integrity section
# ---------------------------------------------------------------------------
st.markdown("---")
st.markdown("### 🛡 Integrity Analysis")

if ir:
    risk_color = {"high": "#dc2626", "medium": "#d97706", "low": "#16a34a"}.get(ir.honeypot_risk, "#94a3b8")
    st.markdown(
        f"**Honeypot Risk:** <span style='color:{risk_color}; font-weight:700;'>{ir.honeypot_risk.upper()}</span> · "
        f"**Integrity Score:** `{ir.integrity_score:.4f}` · "
        f"**Flags:** {len(ir.integrity_flags)}",
        unsafe_allow_html=True,
    )
    if ir.integrity_flags:
        for flag in ir.integrity_flags:
            st.markdown(f'<div class="flag-item">⚑ {flag}</div>', unsafe_allow_html=True)
    else:
        st.success("✅ No integrity issues detected.")

# ---------------------------------------------------------------------------
# Reasoning
# ---------------------------------------------------------------------------
st.markdown("---")
st.markdown("### 💬 AI Reasoning")
st.info(f"**Rank #{rank_num} Reasoning:** {reasoning}")

# Feature score bar chart
st.markdown("### 📈 Feature Scores Detail")
feat_names = list(cs.features.keys())
feat_vals = [cs.features[k] for k in feat_names]

fig2 = go.Figure(go.Bar(
    x=feat_vals,
    y=feat_names,
    orientation='h',
    marker=dict(
        color=feat_vals,
        colorscale="Blues",
        showscale=False,
    ),
))
fig2.update_layout(
    height=400,
    margin=dict(l=180, r=20, t=10, b=20),
    xaxis=dict(range=[0, 1], title="Score"),
)
st.plotly_chart(fig2, use_container_width=True)
