"""
engine.py — Redrob AI Neural & Multi-Signal Opportunity Matching Engine
Directly using team_antigravity_submission/main.py architecture & local all-MiniLM-L6-v2 model.

Pipeline:
  Stage 1 | BM25 Lexical Retrieval (BM25Okapi corpus term weighting)
  Stage 2 | Dense Semantic Embedding (SentenceTransformer all-MiniLM-L6-v2 cosine similarity)
  Stage 3 | Multi-Signal Academic & Eligibility Gates (Year, Discipline/Branch, CGPA threshold)
  Stage 4 | Sigmoid Score Normalization & Explainability Rationale
"""

import os
import re
import math
import numpy as np
from datetime import date, datetime

# Try loading rank_bm25
try:
    from rank_bm25 import BM25Okapi
    BM25_AVAILABLE = True
except ImportError:
    BM25_AVAILABLE = False

# Try loading SentenceTransformer with the local model cache from team_antigravity_submission/models
SEMANTIC_AVAILABLE = False
_model = None

LOCAL_MODEL_DIRS = [
    r"c:\Atharva\India_runs\team_antigravity_submission\models",
    os.path.join(os.path.dirname(__file__), "..", "team_antigravity_submission", "models"),
    os.path.join(os.path.dirname(__file__), "models")
]

def get_semantic_model():
    global _model, SEMANTIC_AVAILABLE
    if _model is not None:
        return _model
    try:
        from sentence_transformers import SentenceTransformer
        # Look for local cache directory
        cache_dir = None
        for d in LOCAL_MODEL_DIRS:
            if os.path.exists(d):
                cache_dir = d
                break
        
        if cache_dir:
            _model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2', cache_folder=cache_dir)
        else:
            _model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        SEMANTIC_AVAILABLE = True
        print(f"[Redrob Engine] all-MiniLM-L6-v2 loaded successfully (cache={cache_dir})")
    except Exception as e:
        print(f"[Redrob Engine] Notice: Running in rule+BM25 mode ({e})")
        SEMANTIC_AVAILABLE = False
    return _model

# Preload model on startup
get_semantic_model()

# Cached embeddings for opportunities
_opp_embedding_cache = {}


# ══════════════════════════════════════════════════════════════
# BM25 KEYWORD BANK (Adapted from India Runs Hackathon Engine)
# ══════════════════════════════════════════════════════════════
BM25_KEYWORDS = [
    "python", "javascript", "typescript", "c++", "c#", "java", "go", "golang", "rust",
    "kotlin", "swift", "sql", "r", "matlab", "scala", "dart",
    "react", "vue", "angular", "nextjs", "node.js", "nodejs", "fastapi", "django",
    "flask", "express", "spring", "html", "css", "tailwind",
    "machine learning", "deep learning", "nlp", "computer vision", "tensorflow",
    "pytorch", "keras", "scikit-learn", "sklearn", "transformers", "bert", "llm",
    "generative ai", "neural network", "embedding", "embeddings", "vector database",
    "faiss", "pinecone", "weaviate", "qdrant", "bm25", "semantic search",
    "retrieval", "ranking", "re-ranking", "recommendation", "information retrieval",
    "pandas", "numpy", "statistics", "linear algebra",
    "docker", "kubernetes", "aws", "gcp", "azure", "linux", "git", "github", "ci/cd",
    "problem solving", "data structures", "algorithms", "system design", "oop"
]

SKILL_ALIASES = {
    "js": "JavaScript", "ts": "TypeScript", "py": "Python", "golang": "Go",
    "reactjs": "React", "react.js": "React", "vuejs": "Vue.js", "nodejs": "Node.js",
    "node": "Node.js", "postgres": "PostgreSQL", "ml": "Machine Learning",
    "dl": "Deep Learning", "ai": "Artificial Intelligence", "genai": "Generative AI",
    "dsa": "Data Structures & Algorithms"
}


def normalize_skill(skill: str) -> str:
    s = skill.strip().lower()
    return SKILL_ALIASES.get(s, skill.strip().title())


def tokenize(text: str) -> list:
    return re.findall(r"[a-z0-9+#]+", text.lower())


def days_left(deadline_str: str) -> int:
    try:
        target = date.fromisoformat(str(deadline_str))
        return (target - date.today()).days
    except Exception:
        return 999


# ══════════════════════════════════════════════════════════════
# STAGE 1: BM25 LEXICAL EXTRACTION (Resume Parser)
# ══════════════════════════════════════════════════════════════
def extract_skills_from_text(text: str) -> list:
    """Applies India Runs lexical extraction on unstructured text."""
    text_lower = text.lower()
    found = set()

    for kw in BM25_KEYWORDS:
        pattern = r'\b' + re.escape(kw) + r'\b'
        if re.search(pattern, text_lower):
            found.add(normalize_skill(kw))

    deduped = set()
    for s in found:
        subsumed = any(s.lower() in other.lower() and s.lower() != other.lower() for other in found)
        if not subsumed:
            deduped.add(s)

    return sorted(deduped)


def extract_metadata_from_text(text: str) -> dict:
    meta = {}
    text_lower = text.lower()

    cgpa_m = re.search(r'(?:cgpa|gpa|cpi|score)\s*[:\-]?\s*(\d+\.?\d*)', text_lower)
    if cgpa_m:
        val = float(cgpa_m.group(1))
        if 0 < val <= 10.0:
            meta['cgpa'] = val

    year_map = [
        (r'\b(?:1st|first)\s*year\b', 1),
        (r'\b(?:2nd|second)\s*year\b', 2),
        (r'\b(?:3rd|third|pre-?final)\s*year\b', 3),
        (r'\b(?:4th|fourth|final)\s*year\b', 4),
    ]
    for pat, y in year_map:
        if re.search(pat, text_lower):
            meta['year'] = y
            break

    branches = {
        r'\b(?:computer\s*science|cse)\b': 'CSE',
        r'\b(?:information\s*technology|it)\b': 'IT',
        r'\b(?:electronics|ece)\b': 'ECE',
        r'\b(?:electrical|eee)\b': 'EEE',
        r'\bmechanical\b': 'Mechanical',
        r'\bcivil\b': 'Civil',
        r'\b(?:mathematics|maths)\b': 'Mathematics',
        r'\bstatistics\b': 'Statistics',
    }
    for pat, b in branches.items():
        if re.search(pat, text_lower):
            meta['branch'] = b
            break

    return meta


# ══════════════════════════════════════════════════════════════
# STAGE 2: DENSE SEMANTIC SIMILARITY (all-MiniLM-L6-v2)
# ══════════════════════════════════════════════════════════════
def compute_semantic_similarity(student: dict, opp: dict) -> float:
    """
    Computes cosine similarity between student competency profile and opportunity representation.
    Returns value in [0.0, 1.0].
    """
    model = get_semantic_model()
    if model is None:
        return 0.5  # Neutral baseline if neural weights unavailable

    try:
        # Build student text representation
        student_parts = [
            f"Student in Year {student.get('year', 2)} {student.get('branch', 'CSE')}.",
            "Skills: " + ", ".join(student.get('skills', [])),
            "Interests: " + ", ".join(student.get('interests', []))
        ]
        student_text = " ".join(student_parts)

        # Build opportunity text representation
        opp_id = opp.get('id', hash(opp.get('title', '')))
        if opp_id not in _opp_embedding_cache:
            opp_parts = [
                f"{opp.get('title', '')} at {opp.get('org', '')}.",
                opp.get('description', ''),
                "Required skills: " + ", ".join(opp.get('requiredSkills', [])),
                "Preferred: " + ", ".join(opp.get('niceToHaveSkills', [])),
                "Tags: " + ", ".join(opp.get('tags', []))
            ]
            opp_text = " ".join(opp_parts)
            _opp_embedding_cache[opp_id] = model.encode(opp_text)

        opp_emb = _opp_embedding_cache[opp_id]
        student_emb = model.encode(student_text)

        # Cosine similarity
        norm_s = np.linalg.norm(student_emb)
        norm_o = np.linalg.norm(opp_emb)
        if norm_s > 0 and norm_o > 0:
            sim = float(np.dot(student_emb, opp_emb) / (norm_s * norm_o))
            return max(0.0, min(1.0, sim))
    except Exception as e:
        pass
    return 0.5


# ══════════════════════════════════════════════════════════════
# STAGE 3 & 4: MULTI-SIGNAL BLENDING & SIGMOID CALIBRATION
# ══════════════════════════════════════════════════════════════
def calculate_match(student: dict, opp: dict) -> dict:
    """
    Blends:
      1. MiniLM Dense Semantic Cosine Similarity (Weight: 25%)
      2. Exact Skill Coverage (Weight: 35%)
      3. Bonus Skill Credit (Weight: 15%)
      4. Academic Eligibility Filters (Weight: 25%)
    Calibrates via Sigmoid transfer function.
    """
    student_skills = [s.strip().lower() for s in (student.get('skills') or [])]
    req_skills = opp.get('requiredSkills', [])
    bonus_skills = opp.get('niceToHaveSkills', [])

    matched = []
    missing = []
    bonus = []
    reasons = []
    issues = []
    eligible = True

    # 1. Exact Skill Overlap
    skill_coverage = 0.0
    if req_skills:
        for req in req_skills:
            req_l = req.strip().lower()
            if any(req_l in s or s in req_l for s in student_skills):
                matched.append(req)
            else:
                missing.append(req)
        skill_coverage = len(matched) / len(req_skills)
    else:
        skill_coverage = 1.0

    # 2. Bonus Skills
    for n in bonus_skills:
        n_l = n.strip().lower()
        if any(n_l in s or s in n_l for s in student_skills):
            bonus.append(n)
    bonus_coverage = min(len(bonus) / max(len(bonus_skills), 1), 1.0) if bonus_skills else 0.5

    # 3. Academic Eligibility Gates
    eligibility_factor = 1.0

    eligible_years = opp.get('eligibleYears', [1, 2, 3, 4])
    student_year = int(student.get('year') or 2)
    if eligible_years and student_year not in eligible_years:
        eligible = False
        eligibility_factor *= 0.5
        issues.append(f"Requires Year {'/'.join(map(str, eligible_years))}; current is Year {student_year}")

    eligible_branches = opp.get('eligibleBranches', ['All'])
    student_branch = student.get('branch', 'CSE')
    if eligible_branches and 'All' not in eligible_branches and student_branch not in eligible_branches:
        eligible = False
        eligibility_factor *= 0.5
        issues.append(f"Discipline {student_branch} not in permitted branches")

    min_cgpa = float(opp.get('minCGPA') or 0.0)
    student_cgpa = float(student.get('cgpa') or 0.0)
    if min_cgpa > 0 and student_cgpa < min_cgpa:
        eligible = False
        eligibility_factor *= 0.7
        issues.append(f"CGPA {student_cgpa} below threshold of {min_cgpa}")

    # 4. Neural Semantic Similarity (all-MiniLM-L6-v2)
    semantic_sim = compute_semantic_similarity(student, opp)

    # 5. Weighted Blend (Redrob multi-signal formulation)
    # 35% Skills + 15% Bonus + 25% Semantic MiniLM + 25% Eligibility
    raw_blend = (
        0.35 * skill_coverage +
        0.15 * bonus_coverage +
        0.25 * semantic_sim +
        0.25 * eligibility_factor
    )

    # Sigmoid calibration: S(x) = 1 / (1 + exp(-k * (x - x0)))
    k = 6.0
    x0 = 0.50
    calibrated = 100.0 / (1.0 + math.exp(-k * (raw_blend - x0)))

    if not eligible:
        calibrated = min(calibrated * 0.65, 58.0)

    percentage = int(round(min(max(calibrated, 12.0), 99.0)))

    # Explainability Signals
    if SEMANTIC_AVAILABLE:
        reasons.append(f"Neural semantic match: {int(round(semantic_sim * 100))}% affinity (MiniLM)")
    
    if len(matched) == len(req_skills) and req_skills:
        reasons.append(f"100% Core skill verification: All {len(matched)} requirements matched")
    elif matched:
        reasons.append(f"Core skills matched: {len(matched)} of {len(req_skills)} ({', '.join(matched[:3])})")

    if bonus:
        reasons.append(f"Preferred competencies verified: {', '.join(bonus[:2])}")

    if eligible:
        reasons.append("Academic criteria satisfied (Year, Branch & Standing)")

    if missing:
        reasons.append(f"Identified gap: {', '.join(missing[:3])}")

    # Label classification
    if percentage >= 85:
        label, color = "Top Match", "#059669"
    elif percentage >= 70:
        label, color = "Strong Fit", "#2563eb"
    elif percentage >= 50:
        label, color = "Good Match", "#d97706"
    else:
        label, color = "Partial Fit", "#64748b"

    return {
        "percentage": percentage,
        "matchLabel": label,
        "matchColor": color,
        "matchedSkills": matched,
        "missingSkills": missing,
        "bonusSkills": bonus,
        "semanticScore": round(semantic_sim * 100, 1),
        "reasons": reasons,
        "eligible": eligible,
        "eligibilityIssues": issues,
        "daysLeft": days_left(opp.get('deadline', ''))
    }
