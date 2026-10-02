"""
engine.py — India Runs Matching & Candidate Discovery Engine
Adapted from team_antigravity_submission/main.py for PS-09 (Student Skill-to-Opportunity Platform)

Pipeline:
  Stage 1 | Lexical & Keyword Matching (BM25-style inverted indexing & frequency weighting)
  Stage 2 | Multi-Signal Rule Scoring (Skill coverage, bonus competencies, eligibility gates)
  Stage 3 | Sigmoid Score Calibration & Normalized Match Percentage
  Stage 4 | Explainability Engine (Human-readable rationale, skill-gap analysis, actionable steps)
"""

import re
import math
from datetime import date, datetime

# ══════════════════════════════════════════════════════════════
# BM25 KEYWORD BANK (Adapted from India Runs Hackathon Engine)
# ══════════════════════════════════════════════════════════════
BM25_KEYWORDS = [
    # Core Languages & Systems
    "python", "javascript", "typescript", "c++", "c#", "java", "go", "golang", "rust",
    "kotlin", "swift", "sql", "r", "matlab", "scala", "dart",
    # Frameworks & Full-Stack
    "react", "vue", "angular", "nextjs", "node.js", "nodejs", "fastapi", "django",
    "flask", "express", "spring", "html", "css", "tailwind",
    # AI / Machine Learning / Data (India Runs Core)
    "machine learning", "deep learning", "nlp", "computer vision", "tensorflow",
    "pytorch", "keras", "scikit-learn", "sklearn", "transformers", "bert", "llm",
    "generative ai", "neural network", "embedding", "embeddings", "vector database",
    "faiss", "pinecone", "weaviate", "qdrant", "bm25", "semantic search",
    "retrieval", "ranking", "re-ranking", "recommendation", "information retrieval",
    "pandas", "numpy", "statistics", "linear algebra",
    # Cloud & Infrastructure
    "docker", "kubernetes", "aws", "gcp", "azure", "linux", "git", "github", "ci/cd",
    # General Competencies
    "problem solving", "data structures", "algorithms", "system design", "oop"
]

SKILL_ALIASES = {
    "js": "JavaScript",
    "ts": "TypeScript",
    "py": "Python",
    "golang": "Go",
    "reactjs": "React",
    "react.js": "React",
    "vuejs": "Vue.js",
    "nodejs": "Node.js",
    "node": "Node.js",
    "postgres": "PostgreSQL",
    "ml": "Machine Learning",
    "dl": "Deep Learning",
    "ai": "Artificial Intelligence",
    "genai": "Generative AI",
    "dsa": "Data Structures & Algorithms"
}


def normalize_skill(skill: str) -> str:
    s = skill.strip().lower()
    return SKILL_ALIASES.get(s, skill.strip().title())


def tokenize(text: str) -> list:
    return re.findall(r'[a-z0-9+#]+', text.lower())


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
    """
    Applies India Runs lexical extraction on unstructured text (resumes/PDFs/announcements).
    """
    text_lower = text.lower()
    found = set()

    for kw in BM25_KEYWORDS:
        pattern = r'\b' + re.escape(kw) + r'\b'
        if re.search(pattern, text_lower):
            found.add(normalize_skill(kw))

    # Remove subsumed duplicates (e.g. if 'Machine Learning' exists, don't keep redundant sub-terms)
    deduped = set()
    for s in found:
        subsumed = any(s.lower() in other.lower() and s.lower() != other.lower() for other in found)
        if not subsumed:
            deduped.add(s)

    return sorted(deduped)


def extract_metadata_from_text(text: str) -> dict:
    """Extract CGPA, Year of Study, and Branch from student resumes."""
    meta = {}
    text_lower = text.lower()

    # CGPA
    cgpa_m = re.search(r'(?:cgpa|gpa|cpi|score)\s*[:\-]?\s*(\d+\.?\d*)', text_lower)
    if cgpa_m:
        val = float(cgpa_m.group(1))
        if 0 < val <= 10.0:
            meta['cgpa'] = val

    # Year
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

    # Branch
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
# STAGE 2 & 3: MULTI-SIGNAL SCORING & SIGMOID CALIBRATION
# ══════════════════════════════════════════════════════════════
def calculate_match(student: dict, opp: dict) -> dict:
    """
    Computes calibrated match score between a student profile and an opportunity
    using India Runs multi-signal architecture.
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

    # 1. Required Skill Overlap Signal
    skill_score = 0.0
    max_skill_score = max(len(req_skills) * 20.0, 20.0)

    for req in req_skills:
        req_l = req.strip().lower()
        if any(req_l in s or s in req_l for s in student_skills):
            matched.append(req)
            skill_score += 20.0
        else:
            missing.append(req)

    # 2. Bonus / Nice-to-have Skills Signal
    bonus_score = 0.0
    for n in bonus_skills:
        n_l = n.strip().lower()
        if any(n_l in s or s in n_l for s in student_skills):
            bonus.append(n)
            bonus_score += 8.0
    bonus_score = min(bonus_score, 24.0)

    # 3. Eligibility Filter & Penalties (Year, Branch, CGPA)
    eligibility_weight = 30.0
    eligibility_score = 30.0

    # Year eligibility
    eligible_years = opp.get('eligibleYears', [1, 2, 3, 4])
    student_year = int(student.get('year') or 2)
    if eligible_years and student_year not in eligible_years:
        eligible = False
        eligibility_score -= 15.0
        issues.append(f"Requires Year {'/'.join(map(str, eligible_years))}; current is Year {student_year}")

    # Branch eligibility
    eligible_branches = opp.get('eligibleBranches', ['All'])
    student_branch = student.get('branch', 'CSE')
    if eligible_branches and 'All' not in eligible_branches and student_branch not in eligible_branches:
        eligible = False
        eligibility_score -= 15.0
        issues.append(f"Branch {student_branch} not in eligible list ({', '.join(eligible_branches)})")

    # CGPA cutoff
    min_cgpa = float(opp.get('minCGPA') or 0.0)
    student_cgpa = float(student.get('cgpa') or 0.0)
    if min_cgpa > 0:
        if student_cgpa < min_cgpa:
            eligible = False
            eligibility_score -= 10.0
            issues.append(f"CGPA {student_cgpa} below minimum requirement {min_cgpa}")

    # 4. Interest Alignment Signal
    interest_score = 0.0
    student_interests = [i.strip().lower() for i in (student.get('interests') or [])]
    opp_tags = [t.strip().lower() for t in (opp.get('tags') or [])] + [opp.get('typeKey', '').lower()]
    matched_interests = [i for i in student_interests if any(t in i or i in t for t in opp_tags)]
    if matched_interests:
        interest_score = min(len(matched_interests) * 6.0, 16.0)

    # 5. Aggregate Raw Signal
    raw_signal = (skill_score / max_skill_score) * 50.0 + bonus_score + max(eligibility_score, 0.0) + interest_score
    max_possible = 50.0 + 24.0 + 30.0 + 16.0  # 120 max

    normalized_ratio = raw_signal / max_possible

    # Sigmoid calibration: compresses extremes, centers realistic fits
    # S(x) = 100 / (1 + exp(-4 * (x - 0.5)))
    calibrated = 100.0 / (1.0 + math.exp(-5.0 * (normalized_ratio - 0.45)))
    calibrated = min(max(calibrated, 15.0), 99.0)

    if not eligible:
        calibrated = min(calibrated * 0.65, 58.0)

    percentage = int(round(calibrated))

    # STAGE 4: EXPLAINABLE RATIONALE
    if len(matched) == len(req_skills) and req_skills:
        reasons.append(f"Full skill verification: All {len(matched)} required competencies confirmed")
    elif matched:
        reasons.append(f"Core skill alignment: {len(matched)} of {len(req_skills)} verified ({', '.join(matched[:3])})")

    if bonus:
        reasons.append(f"Bonus competencies verified: {', '.join(bonus[:2])}")

    if eligible:
        reasons.append("Meets academic year, branch, and academic standing criteria")

    if matched_interests:
        reasons.append(f"Aligns with career focus: {matched_interests[0].title()}")

    if missing:
        reasons.append(f"Skill gap identified: {', '.join(missing[:3])}")

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
        "reasons": reasons,
        "eligible": eligible,
        "eligibilityIssues": issues,
        "daysLeft": days_left(opp.get('deadline', ''))
    }
