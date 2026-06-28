"""
HireWise AI — Page 6: Methodology
=====================================
Explains the ranking approach, fairness design, and limitations.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import streamlit as st

st.set_page_config(page_title="Methodology — HireWise AI", page_icon="📖", layout="wide")

from src.theme import apply_theme
apply_theme()

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
[data-testid="stSidebar"] { background: linear-gradient(180deg, #0f172a, #1e3a5f); color: #f1f5f9; }
[data-testid="stSidebar"] * { color: #f1f5f9 !important; }
.page-header { background: linear-gradient(135deg, #1a1a2e, #16213e); border-radius:12px; padding:28px 36px; color:white; margin-bottom:24px; }
.page-title { font-size:1.8rem; font-weight:800; margin:0; }
.method-card { background:#f8fafc; border-left:4px solid #3b82f6; border-radius:8px; padding:16px 20px; margin:8px 0; }
.formula-block { background:#0f172a; color:#e2e8f0; border-radius:8px; padding:16px; font-family:monospace; font-size:0.88rem; margin:12px 0; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div class="page-header">
    <p class="page-title">📖 Methodology</p>
    <p style="color:#cbd5e1; margin-top:4px;">How HireWise AI ranks candidates — design decisions, fairness, and limitations</p>
</div>
""", unsafe_allow_html=True)

st.markdown("""
## Why Career Evidence > Skill Keywords

The core design principle of HireWise AI is that **what you did** matters more than **what you claim to know**.

A candidate can list "FAISS" as an expert skill with 60 months of experience in a row of checkboxes.
But if their career descriptions show no mention of vector indexes, production deployments, or retrieval systems,
that skill claim is treated as low-evidence.

The weighted text field system addresses this:

| Field | Weight | Rationale |
|---|---|---|
| Career descriptions | **3.0×** | Direct evidence of what was actually done |
| Current + career titles | **2.5×** | Job titles signal real domain exposure |
| Professional headline | **2.0×** | Candidate's own primary positioning |
| Summary | **1.5×** | Self-reported but narrative context |
| Skills list | **1.0×** | Baseline — present but not trusted alone |
| Certifications | **0.8×** | Useful supplementary signal |
| Education field | **0.4×** | Least informative for mid-senior roles |
""")

st.markdown("---")

st.markdown("""
## Hybrid Ranking Formula

The final score is computed in four steps:
""")

st.markdown("""
<div class="formula-block">
# Step 1: Base score
base = 0.40 × lexical_score + 0.60 × weighted_feature_score

# Step 2: Behavioural modifier (capped to avoid dominance)
modified = base × behaviour_modifier   # modifier ∈ [0.75, 1.10]

# Step 3: Integrity penalty
with_integrity = modified × integrity_multiplier
# multiplier: high-risk=0.55, medium=0.80, low=1.00

# Step 4: Keyword stuffing penalty
final = with_integrity × stuffing_penalty   # ∈ [0.60, 1.00]

# Scores normalised to [0, 1], monotonically non-increasing
</div>
""", unsafe_allow_html=True)

st.markdown("""
### Feature Score Weights

| Feature | Weight | What it captures |
|---|---|---|
| retrieval_production_score | **30%** | Elasticsearch, FAISS, vector DBs, search, ranking — with production evidence |
| ranking_evaluation_score | **15%** | NDCG, MRR, MAP, A/B testing, offline evaluation |
| python_engineering_score | **10%** | Python, PyTorch, FastAPI, Docker — actual usage |
| product_shipping_score | **8%** | Shipped, launched, owned, delivered production systems |
| vector_search_score | **8%** | Specific vector DB infrastructure |
| nlp_ir_relevance_score | **7%** | NLP, text processing, language models |
| ml_production_score | **5%** | MLOps, model serving, inference pipelines |
| learning_to_rank_score | **5%** | LTR algorithms, reranking, cross-encoders |
| experience_fit_score | **5%** | Smooth bell curve around 5–9 years |
| llm_finetuning_score | **3%** | LoRA, PEFT, RLHF — bonus, not primary |
| startup_ownership_score | **4%** | Startup experience, small teams, ownership |
""")

st.markdown("---")

st.markdown("""
## Production Evidence Requirement

**For high scores, keywords alone are not enough.** A career description must contain:

1. **A relevant keyword** (e.g. "FAISS", "vector index", "embedding retrieval")
2. **At least one production action verb** (e.g. *built*, *deployed*, *shipped*, *maintained*, *scaled*)

A profile saying *"interested in vector databases"* scores near 0 on `vector_search_score`.
A profile saying *"deployed a Milvus vector index serving 10M queries/day"* scores near 1.0.

The action verb list includes: `built, deployed, shipped, designed, maintained, scaled,
monitored, owned, operated, improved, evaluated, implemented, launched, developed, led,
architected, migrated, optimised, integrated, productionized, serving`
""")

st.markdown("---")

st.markdown("""
## Behavioural Signals — Modifier, Not Driver

Redrob signals adjust a technically-qualified candidate's score but cannot create rank from nothing.

The modifier is bounded: **minimum 0.75 × score, maximum 1.10 × score**.

| Signal | Effect |
|---|---|
| open_to_work_flag = True | +0.20 utility |
| Last active < 30 days | +0.15 utility |
| High recruiter response rate | +up to 0.15 utility |
| Fast avg response time (<24h) | +0.10 utility |
| High interview completion rate | +up to 0.10 utility |
| GitHub activity score > 0 | +up to 0.08 utility |
| Long notice period (>90 days) | −0.05 to −0.10 utility |
| Long inactivity (>6 months) | −0.10 utility |
| Very slow response (>96h) | −0.05 utility |
""")

st.markdown("---")

st.markdown("""
## Honeypot & Integrity Detection

Ten explicit rules are applied. All flags are visible to recruiters:

1. **Signup after last_active** — chronologically impossible
2. **Career date overlaps** — full-time jobs overlapping by >3 months
3. **Current role with end date** — contradicts is_current flag
4. **Non-current role without end date** — incomplete data
5. **Skill duration > total experience** — impossible timeline
6. **Expert skills with no career support and zero endorsements** — 5+ triggers a flag
7. **Non-technical title + large AI skill list** — marketing/HR titles with expert AI skills
8. **AI headline with no AI career history** — misleading self-positioning
9. **Templated generic summary + many AI keywords** — boilerplate with keyword stuffing
10. **Duration_months inconsistent with date range** — >6 month discrepancy
""")

st.markdown("---")

st.markdown("""
## Fairness Design

The following signals are **explicitly excluded** from ranking:

- **Anonymized name** — not used for any ranking signal
- **Gender, religion, caste, ethnicity, age, marital status** — not present in data, not inferred
- **Education institution tier** — minimally weighted (field of study at 0.4×, institution not scored)
- **Country of origin** — only location proximity to Pune/Noida is considered (practical, not biased)

Location is used only for practical compatibility (Pune/Noida hybrid role). Being India-based
with willingness to relocate is rewarded, but international candidates willing to relocate still
receive a reasonable location score (0.5).
""")

st.markdown("---")

st.markdown("""
## Reasoning Generation

Reasoning is generated by a **template-based system** — not by any LLM.

Each reasoning sentence is constructed from:
- Actual candidate facts (title, years, company, career descriptions)
- Computed score components
- Real Redrob signal values (response rate, notice period, open-to-work)

This means:
- ✅ Every claim is traceable to a specific field in the candidate record
- ✅ No facts can be invented
- ✅ Concerns are included when warranted
- ✅ Reasoning varies per candidate strength

The system cannot hallucinate because it has no language model access.
""")

st.markdown("---")

st.markdown("""
## Runtime & Memory Strategy

For 100K candidates:
- **Streaming**: candidates are read line-by-line from JSONL.GZ (never fully decompressed into RAM)
- **TF-IDF**: scikit-learn's sparse matrix representation keeps memory manageable
- **Feature scores**: computed in a single pass, stored as lightweight dataclasses
- **No redundant data copies**: IDs + scores stored separately from full candidate dicts

Tested constraints: ≤5 min wall-clock, ≤16 GB RAM, CPU-only.

## Limitations

- The synonym map covers the most important retrieval/IR terminology but is not exhaustive
- Recency weighting gives more credit to recent roles, which may disadvantage some mid-career pivots
- Integrity detection flags may occasionally misidentify legitimate career paths as suspicious
- The behavioural modifier cannot account for candidates who are excellent but slow to engage on platforms
- Semantic re-ranking requires offline precomputation (run `precompute.py` once)
""")
