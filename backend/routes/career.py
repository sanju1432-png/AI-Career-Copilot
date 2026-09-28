from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from auth import get_user_id
from models import Profile
from services.ai_service import CAREERS, match_careers, roadmap, skill_intelligence, ai_text, AIServiceError
router=APIRouter()
class CareerBody(BaseModel): skills:list[str]=[]; target:str='';
@router.post('/recommend')
def recommend(body:CareerBody): return {'recommendations':match_careers(body.skills)}
@router.post('/roadmap')
def get_roadmap(body:CareerBody):
    if body.target not in CAREERS: raise HTTPException(400,'Select a supported career first')
    return {'roadmap':roadmap(body.skills,body.target)}
@router.post('/skills')
def skills(body:CareerBody):
    if body.target not in CAREERS: raise HTTPException(400,'Select a supported career first')
    return skill_intelligence(body.skills,body.target)
@router.get('/catalog')
def catalog(): return {'careers':[{'name':k,'requirements':v} for k,v in CAREERS.items()]}
@router.post('/portfolio')
def portfolio(body:CareerBody):
    if body.target not in CAREERS: raise HTTPException(400,'Select a career')
    ideas=[{'title':f'{body.target} Capstone','description':f'Build a production-style {body.target} project using {", ".join(body.skills[:4]) or ", ".join(CAREERS[body.target][:3])}.','milestones':['Define problem and users','Build core workflow','Add tests and documentation','Deploy and publish case study']},{'title':'Portfolio Accelerator','description':'Create a second smaller project that demonstrates one missing core skill.','milestones':['Learn missing skill','Build focused feature','Write README','Record demo']}]
    return {'projects':ideas}
@router.post('/coach')
def coach(body:dict,request:Request,db:Session=Depends(get_db)):
    uid=get_user_id(request); p=db.query(Profile).filter(Profile.user_id==uid).first(); target=body.get('target') or (p.target_role if p else '')
    if not target: raise HTTPException(400,'Select a target career first')
    skills=body.get('skills',[]); prompt=f'You are a practical AI career coach. Student target: {target}. Skills: {skills}. Profile: {p.education if p else ""}, {p.branch if p else ""}. Give concise personalized priorities, next 3 actions, project suggestion, interview focus and job-search advice. Do not invent achievements.'
    try:
        text=ai_text(prompt)
    except AIServiceError as exc:
        raise HTTPException(503, str(exc))
    return {'advice':text}
