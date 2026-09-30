from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

QUESTIONS = {
    "AI/ML Engineer": [
        "Explain overfitting and two ways to reduce it.",
        "What is the difference between precision and recall?",
        "Describe one machine-learning project you built.",
        "How would you handle missing data?",
        "Why would you choose a tree model over linear regression?"
    ],
    "Full Stack Developer": [
        "Explain REST APIs.",
        "What is the React component lifecycle?",
        "How would you secure a login endpoint?",
        "SQL JOINs: explain the common types.",
        "Describe a full-stack project you built."
    ]
}

class InterviewBody(BaseModel):
    target: str = "AI/ML Engineer"

@router.post("/questions")
def questions(body: InterviewBody):
    return {"questions": QUESTIONS.get(body.target, QUESTIONS["AI/ML Engineer"])}
