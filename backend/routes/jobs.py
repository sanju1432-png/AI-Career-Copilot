from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Job, Profile
import json
import re

router = APIRouter()


def normalize_skill(skill):
    return re.sub(
        r"[^a-z0-9+#.]",
        "",
        skill.lower().strip()
    )


def get_skills(text):
    if not text:
        return set()

    return {
        normalize_skill(skill)
        for skill in text.split(",")
        if skill.strip()
    }


@router.get("/")
def get_jobs(db: Session = Depends(get_db)):
    jobs = db.query(Job).order_by(Job.id.desc()).all()

    return [
        {
            "id": job.id,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "job_type": job.job_type,
            "description": job.description,
            "required_skills": job.required_skills,
            "apply_url": job.apply_url,
        }
        for job in jobs
    ]


@router.post("/")
def create_job(
    job: dict,
    db: Session = Depends(get_db)
):
    if not job.get("title"):
        raise HTTPException(
            400,
            "title is required"
        )

    if not job.get("company"):
        raise HTTPException(
            400,
            "company is required"
        )

    new_job = Job(
        title=job["title"],
        company=job["company"],
        location=job.get("location", ""),
        job_type=job.get(
            "job_type",
            "Full-time"
        ),
        description=job.get(
            "description",
            ""
        ),
        required_skills=job.get(
            "required_skills",
            ""
        ),
        apply_url=job.get(
            "apply_url",
            ""
        )
    )

    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    return {
        "message": "Job created successfully",
        "job": {
            "id": new_job.id,
            "title": new_job.title,
            "company": new_job.company
        }
    }


@router.get("/match/{user_id}")
def match_jobs(
    user_id: int,
    db: Session = Depends(get_db)
):
    profile = (
        db.query(Profile)
        .filter(Profile.user_id == user_id)
        .first()
    )

    if not profile:
        raise HTTPException(
            404,
            "Student profile not found"
        )

    student_skills = set()

    # Profile skills
    if profile.skills:
        try:
            saved_skills = json.loads(
                profile.skills
            )

            if isinstance(saved_skills, list):
                student_skills.update(
                    normalize_skill(skill)
                    for skill in saved_skills
                )

        except (json.JSONDecodeError, TypeError):
            student_skills.update(
                get_skills(profile.skills)
            )

    jobs = (
        db.query(Job)
        .order_by(Job.id.desc())
        .all()
    )

    results = []

    for job in jobs:

        required_skills = get_skills(
            job.required_skills
        )

        if not required_skills:
            match_percentage = 0
            matched = set()
            missing = set()

        else:
            matched = (
                student_skills
                & required_skills
            )

            missing = (
                required_skills
                - student_skills
            )

            match_percentage = round(
                (
                    len(matched)
                    / len(required_skills)
                ) * 100
            )

        results.append({
            "id": job.id,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "job_type": job.job_type,
            "description": job.description,
            "required_skills": job.required_skills,
            "apply_url": job.apply_url,
            "match_percentage": match_percentage,
            "matched_skills": sorted(matched),
            "missing_skills": sorted(missing)
        })

    results.sort(
        key=lambda x: x["match_percentage"],
        reverse=True
    )

    return {
        "user_id": user_id,
        "total_jobs": len(results),
        "matches": results
    }