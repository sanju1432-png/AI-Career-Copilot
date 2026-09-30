from fastapi import APIRouter
from pydantic import BaseModel
from services.ai_service import recommend_careers, roadmap

router = APIRouter()

class CareerBody(BaseModel):
    skills: list[str]
    target: str = "AI/ML Engineer"

@router.post("/recommend")
def recommend(body: CareerBody):
    return {"recommendations": recommend_careers(body.skills)}

@router.post("/roadmap")
def get_roadmap(body: CareerBody):
    return {"roadmap": roadmap(body.skills, body.target)}
