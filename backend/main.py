import os
import json
import urllib.request
import urllib.error
import ssl
import certifi
from routes.jobs import router as jobs_router
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from dotenv import load_dotenv
load_dotenv()

from database import Base, engine
from routes.auth import router as auth_router
from routes.career import router as career_router
from routes.resume import router as resume_router
from routes.interview import router as interview_router
from models import Profile
from sqlalchemy.orm import Session
from fastapi import Depends
from database import get_db

# Load environment variables
load_dotenv()


# Create database tables
Base.metadata.create_all(bind=engine)


# FastAPI app
app = FastAPI(
    title="AI Career & Placement Copilot",
    version="1.0.0"
)


# CORS
# Comma-separated origins are supplied through CORS_ORIGINS.
# Local origins remain available by default for development.
_cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Routers
app.include_router(
    auth_router,
    prefix="/api/auth",
    tags=["Auth"]
)

app.include_router(
    resume_router,
    prefix="/api/resume",
    tags=["Resume"]
)

app.include_router(
    career_router,
    prefix="/api/career",
    tags=["Career"]
)

app.include_router(
    interview_router,
    prefix="/api/interview",
    tags=["Interview"]
)
app.include_router(
    jobs_router,
    prefix="/api/jobs",
    tags=["Jobs"]
)

# SSL certificate context
SSL_CONTEXT = ssl.create_default_context(
    cafile=certifi.where()
)


@app.get("/")
def root():
    return {
        "message": "AI Career & Placement Copilot API is running"
    }


@app.post("/api/profile")
def save_profile(
    profile: dict,
    db: Session = Depends(get_db)
):
    user_id = profile.get("user_id")

    if not user_id:
        return {
            "error": "user_id is required"
        }

    existing = (
        db.query(Profile)
        .filter(Profile.user_id == user_id)
        .first()
    )

    if existing:
        existing.name = profile.get("name", "")
        existing.education = profile.get("education", "")
        existing.branch = profile.get("branch", "")
        existing.interests = profile.get("interests", "")
        existing.target_role = profile.get(
            "target_role",
            ""
        )
        existing.skills = json.dumps(
            profile.get("skills", [])
        )
        existing.profile_photo = profile.get(
        "profile_photo",
        ""
)
        db.commit()

        return {
            "message": "Profile updated"
        }

    new_profile = Profile(
    user_id=user_id,
    name=profile.get("name", ""),
    education=profile.get("education", ""),
    branch=profile.get("branch", ""),
    interests=profile.get("interests", ""),
    target_role=profile.get("target_role", ""),
    skills=json.dumps(
        profile.get("skills", [])
    ),
    profile_photo=profile.get(
        "profile_photo",
        ""
    )
)

    db.add(new_profile)
    db.commit()

    return {
        "message": "Profile saved"
    }
@app.get("/api/profile/{user_id}")
def get_profile(
    user_id: int,
    db: Session = Depends(get_db)
):

    profile = (
        db.query(Profile)
        .filter(Profile.user_id == user_id)
        .first()
    )

    if not profile:
        return {
            "profile": None
        }

    try:
        skills = json.loads(
            profile.skills or "[]"
        )
    except (json.JSONDecodeError, TypeError):
        skills = []

    return {
        "profile": {
            "id": profile.id,
            "user_id": profile.user_id,
            "name": profile.name or "",
            "education": profile.education or "",
            "branch": profile.branch or "",
            "interests": profile.interests or "",
            "target_role": profile.target_role or "",
            "skills": skills,
            "profile_photo": profile.profile_photo or ""
        }
    }

@app.post("/api/ai/advice")
def ai_advice(payload: dict):

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        return {
            "error": (
                "GEMINI_API_KEY is not configured. "
                "Check the backend .env file."
            )
        }

    skills = payload.get("skills", [])
    profile = payload.get("profile", {})
    target = payload.get(
        "target",
        "AI/ML Engineer"
    )

    # Safely convert skills into text
    if isinstance(skills, list):
        skills_text = ", ".join(
            str(skill) for skill in skills
        )
    else:
        skills_text = str(skills)

    # Prompt for Gemini
    prompt = f"""
You are an AI career advisor helping a college student
prepare for software engineering placements.

Student Profile:

Name:
{profile.get("name", "")}

Education:
{profile.get("education", "")}

Branch:
{profile.get("branch", "")}

Interests:
{profile.get("interests", "")}

Target Role:
{target}

Skills detected from resume:
{skills_text}

Give practical, personalized and realistic career advice.

Include exactly these sections:

1. Current Strengths

2. Skill Gaps

3. Top 5 Learning Priorities

4. 3 Project Ideas

5. Interview Preparation Tips

For each section provide useful and specific advice.

Do not give generic motivational statements.

Focus on helping the student become placement-ready.

Keep the answer student-friendly, actionable,
and relevant to the student's target role.
"""

    # Gemini Interactions API request
    body = json.dumps({
        "model": "gemini-3.6-flash",
        "input": prompt
    }).encode("utf-8")

    url = (
        "https://generativelanguage.googleapis.com/"
        "v1beta/interactions"
    )

    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key
        },
        method="POST"
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=60,
            context=SSL_CONTEXT
        ) as response:

            data = json.loads(
                response.read().decode("utf-8")
            )

        # Interactions API response
        steps = data.get("steps", [])

        for step in steps:

            if step.get("type") == "model_output":

                content = step.get(
                    "content",
                    []
                )

                for item in content:

                    if item.get("type") == "text":

                        text = item.get(
                            "text",
                            ""
                        )

                        if text:
                            return {
                                "advice": text
                            }

        return {
            "error": (
                "Gemini returned an empty response."
            )
        }

    except urllib.error.HTTPError as e:

        error_body = e.read().decode(
            "utf-8",
            errors="replace"
        )

        return {
            "error": (
                f"Gemini API error {e.code}: "
                f"{error_body}"
            )
        }

    except urllib.error.URLError as e:

        return {
            "error": (
                "Gemini connection error: "
                f"{str(e.reason)}"
            )
        }

    except Exception as e:

        return {
            "error": (
                f"Gemini unexpected error: "
                f"{str(e)}"
            )
        }