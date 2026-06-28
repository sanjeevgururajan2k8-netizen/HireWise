# HireWise AI — Intelligent Candidate Discovery & Ranking

> **Redrob Hackathon Submission** · Explainable AI · CPU-Only · No Hosted APIs · 100K Candidates

---

## Project Overview

HireWise AI is a production-quality, explainable candidate ranking system for the **Senior AI Engineer** position at Redrob. It uses a hybrid pipeline combining TF-IDF lexical scoring with 11 evidence-based named feature scores to rank candidates by genuine technical suitability — not keyword count.

**Key design principles:**
- Career descriptions outweigh skill keyword lists (3× weight vs 1×)
- Production action verbs required for evidence credit
- Behavioural signals modify but never dominate technical scores
- Transparent honeypot detection with 10 explicit rules
- Fact-based reasoning — no LLM, no hallucination

---

## Architecture

```
Input (JSON / JSONL / JSONL.GZ)
         │
         ▼
Stage A: Schema Validation
         │
         ▼
Stage B: Weighted Text Construction
   (career descriptions 3×, titles 2.5×, skills 1×)
         │
         ▼
Stage C: TF-IDF Lexical Scoring (+ Synonym Map)
         │
Stage D: Evidence-Based Feature Scoring
   retrieval_production, vector_search, ranking_evaluation,
   python_engineering, ml_production, product_shipping,
   startup_ownership, llm_finetuning, learning_to_rank,
   nlp_ir_relevance, experience_fit
         │
Stage E: Behavioural Modifier [0.75–1.10 capped]
Stage F: Profile Integrity & Honeypot Detection
         │
Stage G: (Optional) Semantic Re-ranking
         │
Stage H: Final Score + Tie-breaking → Top 100
         │
         ▼
submission.csv (UTF-8, validated)
```

---

## Folder Structure

```
HireWise/
├── app.py                     # Streamlit entry (Overview page)
├── rank.py                    # CLI ranking pipeline
├── precompute.py              # Optional: precompute sentence-transformer embeddings
├── requirements.txt
├── README.md
├── Dockerfile
├── submission_metadata.yaml
│
├── config/
│   ├── __init__.py
│   └── scoring_config.py      # All editable weights & thresholds
│
├── src/
│   ├── loaders.py             # JSON / JSONL / JSONL.GZ streaming
│   ├── schema_validator.py    # Schema + cross-field validation
│   ├── text_builder.py        # Weighted text field construction
│   ├── feature_engineering.py # 15 named evidence feature scores
│   ├── lexical_ranker.py      # TF-IDF + synonym expansion
│   ├── semantic_ranker.py     # Optional embedding loader
│   ├── behaviour.py           # Behavioural modifier [0.75–1.10]
│   ├── integrity.py           # Honeypot & integrity detection
│   ├── scoring.py             # Final score combiner + tie-breaking
│   ├── reasoning.py           # Template-based fact-driven reasoning
│   ├── exporter.py            # CSV / JSON / YAML export
│   ├── submission_validator.py# Pre-download CSV validation
│   └── utils.py               # Shared helpers
│
├── pages/                     # Streamlit multi-page app
│   ├── 1_Upload_and_Validate.py
│   ├── 2_Run_Ranking.py
│   ├── 3_Candidate_Rankings.py
│   ├── 4_Candidate_Detail.py
│   ├── 5_Analytics.py
│   ├── 6_Methodology.py
│   └── 7_Export.py
│
├── challenge_data/
│   ├── raw/                   # Official hackathon files (read-only)
│   └── sample/               # sample_candidates.json
│
├── artifacts/                 # Generated outputs (gitignored)
└── tests/                     # pytest test suite
    ├── synthetic_candidates.py
    ├── test_loaders.py
    ├── test_integrity.py
    ├── test_scoring.py
    ├── test_reasoning.py
    └── test_submission_validator.py
```

---

## Installation

```bash
# 1. Create and activate virtual environment
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt
```

---

## Running the Streamlit App

```bash
streamlit run app.py
```

Navigate to `http://localhost:8501` in your browser.

**Pages:**
1. Overview — Architecture, stats
2. Upload & Validate — File upload and schema validation
3. Run Ranking — Execute the full pipeline
4. Candidate Rankings — Interactive filtered table
5. Candidate Detail — Full profile, scores, radar chart
6. Analytics — Score distributions, skill analysis
7. Methodology — Algorithm explanation
8. Export — Download all outputs

---

## Running the CLI Ranker

```bash
# Sample dataset (quick demo)
python rank.py \
  --candidates challenge_data/sample/sample_candidates.json \
  --job challenge_data/raw/job_description.docx \
  --out artifacts/submission.csv

# Full JSONL dataset
python rank.py \
  --candidates challenge_data/raw/candidates.jsonl \
  --job challenge_data/raw/job_description.docx \
  --out artifacts/submission.csv

# JSONL.GZ (memory-efficient streaming)
python rank.py \
  --candidates challenge_data/raw/candidates.jsonl.gz \
  --job challenge_data/raw/job_description.docx \
  --out artifacts/submission.csv
```

---

## Running Tests

```bash
pytest tests/ -v
```

The test suite includes:
- Loader tests (JSON, JSONL, JSONL.GZ, malformed records)
- Integrity detection (honeypot, date contradictions, keyword stuffing)
- Scoring (determinism, monotonicity, genuine engineer > keyword stuffer)
- Reasoning (fact-based, no hallucination, varies per candidate)
- Submission validator (all 12 submission rules)

---

## Docker

```bash
# Build
docker build -t hirewise-ranker .

# Run with local data mounted
docker run --rm \
  -v "${PWD}/challenge_data/raw:/app/data" \
  hirewise-ranker \
  python rank.py \
    --candidates /app/data/candidates.jsonl.gz \
    --job /app/data/job_description.docx \
    --out /app/data/submission.csv
```

---

## Optional: Precompute Semantic Embeddings

```bash
# Install sentence-transformers (not in core requirements)
pip install sentence-transformers

# Precompute embeddings (run once, before ranking)
python precompute.py \
  --candidates challenge_data/raw/candidates.jsonl.gz \
  --out artifacts/

# Ranking will automatically load embeddings from artifacts/
python rank.py --candidates ... --job ... --out ...
```

---

## Scoring Explanation

### Final Score Formula

```
base = 0.40 × lexical_score + 0.60 × feature_score
modified = base × behaviour_modifier        # ∈ [0.75, 1.10]
integrity_applied = modified × integrity_mult  # 0.55/0.80/1.00
final = integrity_applied × stuffing_penalty   # ∈ [0.60, 1.00]
```

### Feature Weights

| Feature | Weight |
|---|---|
| retrieval_production_score | 30% |
| ranking_evaluation_score | 15% |
| python_engineering_score | 10% |
| product_shipping_score | 8% |
| vector_search_score | 8% |
| nlp_ir_relevance_score | 7% |
| startup_ownership_score | 4% |
| ml_production_score | 5% |
| learning_to_rank_score | 5% |
| experience_fit_score | 5% |
| llm_finetuning_score | 3% |

### Text Field Weights

| Field | Weight |
|---|---|
| Career descriptions | 3.0× |
| Current + career titles | 2.5× |
| Headline | 2.0× |
| Summary | 1.5× |
| Skills | 1.0× |
| Certifications | 0.8× |
| Education field | 0.4× |

---

## Behavioural Modifier

Redrob signals are used as a **capped multiplier** in [0.75, 1.10].
A technically irrelevant candidate cannot rank highly through engagement alone.

Positive signals: open_to_work, recent_activity, high response rate, GitHub activity
Negative signals: long notice period, long inactivity, slow response

---

## Honeypot Detection

Ten explicit rules (all visible in Candidate Detail):
1. Signup date after last_active date
2. Overlapping full-time career roles (>3 months)
3. Current role with non-null end date
4. Non-current role without end date
5. Skill duration exceeds total experience
6. Expert skills with no career support and no endorsements
7. Non-technical title with large AI skill list
8. AI headline with no AI career history
9. Templated generic summary + many AI keywords
10. duration_months inconsistent with date range (>6 months)

---

## Fairness

- Anonymized name: not used for ranking
- Gender, religion, caste, ethnicity, age: not inferred or used
- Education tier: minimally weighted (field of study at 0.4×)
- Location: only practical compatibility with Pune/Noida hybrid role

---

## Compute Constraints

| Constraint | Target |
|---|---|
| Wall-clock time | ≤ 5 minutes |
| RAM | ≤ 16 GB |
| GPU | Not used |
| Network | Not used |
| Intermediate disk | ≤ 5 GB |

---

## Limitations

- Synonym map covers main IR/retrieval terms but is not exhaustive
- Recency weighting may disadvantage some mid-career pivots
- Integrity rules may occasionally flag legitimate career paths
- Semantic re-ranking requires offline precomputation

---

## AI Tools Declaration

This project was scaffolded with assistance from Antigravity IDE (Google DeepMind).
No candidate data was fed to any LLM. No hosted AI APIs are called during ranking.
