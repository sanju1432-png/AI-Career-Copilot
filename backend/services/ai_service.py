# AI integration point.
# For now the project uses deterministic analysis so it runs without an API key.

SKILLS = {
    "Python": ["python"],
    "Java": ["java"],
    "JavaScript": ["javascript", "js"],
    "React": ["react"],
    "SQL": ["sql", "mysql", "postgresql"],
    "Machine Learning": ["machine learning", "scikit-learn", "sklearn"],
    "Deep Learning": ["deep learning", "tensorflow", "pytorch"],
    "NLP": ["nlp", "natural language processing"],
    "Git": ["git", "github"],
    "Docker": ["docker"],
    "FastAPI": ["fastapi"],
}

CAREERS = {
    "AI/ML Engineer": ["Python", "Machine Learning", "SQL", "Git"],
    "Full Stack Developer": ["JavaScript", "React", "SQL", "Git"],
    "Data Scientist": ["Python", "SQL", "Machine Learning"],
    "Backend Developer": ["Python", "FastAPI", "SQL", "Git"],
}

def analyze_resume(text: str):
    low = text.lower()
    found = [skill for skill, terms in SKILLS.items() if any(t in low for t in terms)]
    return {
        "skills": found,
        "score": min(100, 35 + len(found) * 7),
        "strengths": found[:5],
        "suggestions": [
            "Add measurable outcomes to project descriptions.",
            "Keep technical skills grouped by category.",
            "Add 2-3 strong projects with GitHub links.",
        ],
    }

def recommend_careers(skills):
    results = []
    skillset = set(skills)
    for career, required in CAREERS.items():
        matched = [s for s in required if s in skillset]
        results.append({
            "career": career,
            "match": round(100 * len(matched) / len(required)),
            "missing": [s for s in required if s not in skillset],
        })
    return sorted(results, key=lambda x: x["match"], reverse=True)

def roadmap(skills, target):
    req = CAREERS.get(target, ["Python", "SQL", "Git"])
    missing = [s for s in req if s not in skills]
    return [
        {"week": 1, "focus": "Foundations", "tasks": ["Review core concepts", "Set up GitHub portfolio"]},
        {"week": 2, "focus": missing[0] if missing else "Advanced practice", "tasks": ["Learn concepts", "Complete 3 coding exercises"]},
        {"week": 3, "focus": "Project", "tasks": [f"Build a small {target} project", "Write README and tests"]},
        {"week": 4, "focus": "Placement", "tasks": ["Mock interview", "Improve resume", "Apply to relevant roles"]},
    ]
