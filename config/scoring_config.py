"""
HireWise AI — Scoring Configuration
====================================
All editable weights, thresholds, and synonym maps live here.
Change values here to adjust ranking behaviour without touching business logic.
"""

# ---------------------------------------------------------------------------
# Random seed — ensures deterministic results across runs
# ---------------------------------------------------------------------------
RANDOM_SEED: int = 42

# ---------------------------------------------------------------------------
# Text-field weights (used in text_builder.py)
# Higher weight = more important during TF-IDF scoring
# ---------------------------------------------------------------------------
TEXT_FIELD_WEIGHTS: dict[str, float] = {
    "career_descriptions": 3.0,
    "current_title":       2.5,
    "career_titles":       2.5,
    "headline":            2.0,
    "summary":             1.5,
    "skills":              1.0,
    "certifications":      0.8,
    "education_field":     0.4,
}

# ---------------------------------------------------------------------------
# Final score component weights (must sum to 1.0)
# ---------------------------------------------------------------------------
SCORE_WEIGHTS: dict[str, float] = {
    "retrieval_production_score": 0.30,  # Production retrieval/matching/ranking evidence
    "python_engineering_score":   0.10,  # Python and ML engineering
    "ml_production_score":        0.05,  # ML production deployment
    "ranking_evaluation_score":   0.15,  # Evaluation frameworks (NDCG, MRR, MAP)
    "product_shipping_score":     0.08,  # Shipping and owning products
    "startup_ownership_score":    0.04,  # Startup / product-company experience
    "vector_search_score":        0.08,  # Vector database infrastructure
    "nlp_ir_relevance_score":     0.07,  # NLP / IR domain relevance
    "learning_to_rank_score":     0.05,  # LTR / ranking systems
    "llm_finetuning_score":       0.03,  # LLM fine-tuning / LoRA / PEFT
    "experience_fit_score":       0.05,  # Experience years fit (5-9 yr sweet spot)
}
# Verify: sum(SCORE_WEIGHTS.values()) should equal 1.0

# Lexical score weight in final blend
LEXICAL_WEIGHT: float = 0.40   # TF-IDF cosine similarity component
FEATURE_WEIGHT: float = 0.60   # Evidence-based named features component

# ---------------------------------------------------------------------------
# Separate scored dimensions (displayed in UI but part of feature score)
# ---------------------------------------------------------------------------
LOCATION_WEIGHT: float = 0.03
BEHAVIOUR_WEIGHT: float = 0.05   # (This is the modifier, capped separately)

# ---------------------------------------------------------------------------
# Behavioural modifier bounds
# ---------------------------------------------------------------------------
BEHAVIOUR_MODIFIER_MIN: float = 0.75
BEHAVIOUR_MODIFIER_MAX: float = 1.10

# ---------------------------------------------------------------------------
# Integrity penalty multipliers
# ---------------------------------------------------------------------------
INTEGRITY_PENALTY: dict[str, float] = {
    "high":   0.55,   # High-risk honeypot → 45% score reduction
    "medium": 0.80,   # Medium risk → 20% reduction
    "low":    1.00,   # Low risk → no penalty
}

# ---------------------------------------------------------------------------
# Keyword-stuffing penalty
# Skills that are expert-level with zero duration and zero endorsements
# trigger this penalty.
# ---------------------------------------------------------------------------
KEYWORD_STUFFING_THRESHOLD: int = 5   # Number of suspicious skills before penalty
KEYWORD_STUFFING_PENALTY: float = 0.85  # Multiply score by this factor

# ---------------------------------------------------------------------------
# Experience fit (years)
# Optimal range: 5–9 years (smooth bell curve, not a hard cutoff)
# ---------------------------------------------------------------------------
EXPERIENCE_OPTIMAL_MIN: float = 5.0
EXPERIENCE_OPTIMAL_MAX: float = 9.0
EXPERIENCE_ABSOLUTE_MIN: float = 2.0  # Below this is very low score

# ---------------------------------------------------------------------------
# Recommendation categories
# ---------------------------------------------------------------------------
RECOMMENDATION_CATEGORIES: list[tuple[float, str]] = [
    (0.85, "Excellent fit"),
    (0.70, "Strong fit"),
    (0.55, "Moderate fit"),
    (0.00, "Limited fit"),
]

# ---------------------------------------------------------------------------
# Location scoring: cities/regions near Pune or Noida
# ---------------------------------------------------------------------------
PREFERRED_LOCATIONS: list[str] = [
    "pune", "noida", "delhi", "new delhi", "gurgaon", "gurugram",
    "ncr", "bengaluru", "bangalore", "mumbai", "hyderabad",
    "chennai", "kolkata", "ahmedabad", "india",
]

# ---------------------------------------------------------------------------
# Synonym map for lexical ranker
# Each key is canonical; values are synonyms that map to it.
# ---------------------------------------------------------------------------
SYNONYM_MAP: dict[str, list[str]] = {
    "information retrieval": [
        "retrieval", "ir", "search", "document retrieval", "text retrieval",
    ],
    "recommendation system": [
        "recommender", "recommender system", "matching", "candidate matching",
        "content recommendation", "collaborative filtering",
    ],
    "vector search": [
        "semantic search", "nearest neighbour search", "nearest neighbor search",
        "ann search", "approximate nearest neighbour", "dense retrieval",
        "embedding search", "dense vector search",
    ],
    "ranking system": [
        "ranking", "learning to rank", "ltr", "reranking", "reranker",
        "listwise ranking", "pointwise ranking", "pairwise ranking",
    ],
    "a/b testing": [
        "ab testing", "online evaluation", "experimentation",
        "randomised controlled trial", "experiment",
    ],
    "model serving": [
        "deployment", "inference", "production ml", "model deployment",
        "model serving", "inference pipeline", "serving infrastructure",
    ],
    "elasticsearch": [
        "elastic", "es", "opensearch", "hybrid search", "bm25",
    ],
    "vector database": [
        "faiss", "pinecone", "milvus", "qdrant", "weaviate", "chroma",
        "pgvector", "vespa", "typesense",
    ],
    "sentence transformers": [
        "sentence-bert", "sbert", "bge", "e5 embedding", "bi-encoder",
        "cross-encoder", "embedding model",
    ],
    "ndcg": [
        "normalized discounted cumulative gain", "mrr", "mean reciprocal rank",
        "map", "mean average precision", "ranking metric", "ir metric",
        "retrieval evaluation",
    ],
    "llm fine-tuning": [
        "fine-tuning", "finetuning", "lora", "qlora", "peft",
        "parameter efficient fine-tuning", "instruction tuning",
        "rlhf", "dpo",
    ],
}

# ---------------------------------------------------------------------------
# Production action verbs — required for evidence scoring
# A career description must contain at least one of these near a keyword
# to count as production evidence.
# ---------------------------------------------------------------------------
PRODUCTION_ACTION_VERBS: list[str] = [
    "built", "deployed", "shipped", "designed", "maintained",
    "scaled", "monitored", "owned", "operated", "improved",
    "evaluated", "implemented", "launched", "developed", "led",
    "architected", "migrated", "optimised", "optimized", "integrated",
    "productionized", "productionised", "serving", "served",
]

# ---------------------------------------------------------------------------
# Keywords for each named feature score
# ---------------------------------------------------------------------------

RETRIEVAL_KEYWORDS: list[str] = [
    "information retrieval", "retrieval", "search", "elasticsearch", "opensearch",
    "bm25", "hybrid search", "dense retrieval", "sparse retrieval",
    "candidate matching", "recommendation", "ranking", "reranking",
    "faiss", "pinecone", "milvus", "qdrant", "weaviate", "vector search",
    "semantic search", "nearest neighbour", "ann",
]

VECTOR_SEARCH_KEYWORDS: list[str] = [
    "faiss", "pinecone", "milvus", "qdrant", "weaviate", "chroma", "pgvector",
    "vector database", "vector store", "vector index", "embedding index",
    "ann", "approximate nearest neighbour", "hnsw", "ivf",
    "sentence transformers", "bge", "e5", "bi-encoder", "embedding model",
]

RANKING_EVAL_KEYWORDS: list[str] = [
    "ndcg", "mrr", "map", "precision at k", "recall at k",
    "ranking metric", "retrieval evaluation", "offline evaluation",
    "online evaluation", "a/b testing", "ab testing", "experimentation",
    "model monitoring", "quality evaluation", "click-through rate", "ctr",
]

PYTHON_KEYWORDS: list[str] = [
    "python", "pytorch", "tensorflow", "scikit-learn", "sklearn", "numpy",
    "pandas", "fastapi", "flask", "celery", "asyncio", "pydantic",
    "sqlalchemy", "pytest", "docker", "kubernetes", "ci/cd",
]

ML_PRODUCTION_KEYWORDS: list[str] = [
    "production ml", "ml deployment", "model serving", "inference",
    "mlops", "ml platform", "feature store", "model registry",
    "kubeflow", "mlflow", "airflow", "ray serve", "triton",
    "latency", "throughput", "sla", "p99",
]

PRODUCT_SHIPPING_KEYWORDS: list[str] = [
    "shipped", "launched", "product", "production", "real users",
    "live traffic", "end-to-end", "ownership", "responsible",
    "delivered", "released", "go-live",
]

STARTUP_KEYWORDS: list[str] = [
    "startup", "founding team", "co-founder", "early stage", "series a",
    "series b", "pre-series", "seed stage", "zero to one",
    "product company", "saas", "marketplace", "b2c", "b2b product",
]

RECENT_CODING_KEYWORDS: list[str] = [
    "coding", "code", "implemented", "built", "engineered",
    "developed", "programmed", "wrote", "debugged", "refactored",
]

LLM_FINETUNE_KEYWORDS: list[str] = [
    "lora", "qlora", "peft", "fine-tuning", "finetuning", "instruction tuning",
    "rlhf", "dpo", "reward model", "llm", "large language model",
    "gpt", "llama", "mistral", "gemma", "phi",
]

LEARNING_TO_RANK_KEYWORDS: list[str] = [
    "learning to rank", "ltr", "ranknet", "lambdamart", "listwise",
    "pairwise ranking", "pointwise ranking", "reranking", "cross-encoder",
    "neural ranking", "rank fusion",
]

NLP_IR_KEYWORDS: list[str] = [
    "nlp", "natural language processing", "text classification",
    "named entity recognition", "ner", "question answering", "qa",
    "text embedding", "word2vec", "glove", "bert", "transformers",
    "tokenization", "language model", "text search",
]

# ---------------------------------------------------------------------------
# Skills that are irrelevant or lower-weight for this role
# ---------------------------------------------------------------------------
IRRELEVANT_SKILL_DOMAINS: list[str] = [
    "image classification", "object detection", "speech recognition",
    "tts", "text-to-speech", "computer vision", "cv", "opencv",
    "robotics", "ros", "slam", "autonomous driving",
    "photoshop", "figma", "ui/ux", "graphic design",
    "accounting", "excel", "powerpoint", "seo", "content writing",
    "marketing", "sales", "hr", "recruitment",
]

# ---------------------------------------------------------------------------
# File paths (relative to project root)
# ---------------------------------------------------------------------------
DEFAULT_CANDIDATES_JSONL: str = "Challenge_data/Raw/candidates.jsonl"
DEFAULT_CANDIDATES_GZ: str    = "Challenge_data/Raw/candidates.jsonl.gz"
DEFAULT_SAMPLE_JSON: str      = "Challenge_data/Sample/sample_candidates.json"
DEFAULT_JOB_DESC_DOCX: str   = "Challenge_data/Raw/job_description.docx"
DEFAULT_SCHEMA_JSON: str      = "Challenge_data/Raw/candidate_schema.json"
DEFAULT_OUTPUT_CSV: str       = "Artifacts/submission.csv"
EMBEDDINGS_PATH: str          = "Artifacts/embeddings.npy"
EMBEDDINGS_IDS_PATH: str      = "Artifacts/embedding_ids.json"

# Participant/team ID — used in output filename
TEAM_ID: str = "hirewise-ai"

# Top-N candidates to select
TOP_N: int = 100
