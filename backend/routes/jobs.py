import re
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Job, Profile
from auth import get_user_id
from services.ai_service import CAREERS
router=APIRouter()

def norm(s): return re.sub(r'[^a-z0-9+#/ ]','',s.lower()).strip()
def skills(s): return {norm(x) for x in (s or '').split(',') if x.strip()}

def seed(db):
    if db.query(Job).count(): return
    rows=[
    ('Junior AI/ML Engineer','TechNova','Hyderabad','AI/ML Engineer','Python, Machine Learning, SQL, FastAPI, Git','https://www.linkedin.com/jobs/search/?keywords=AI%20ML%20Engineer&location=Hyderabad'),
    ('Data Scientist - Graduate','DataWorks','Bengaluru','Data Scientist','Python, SQL, Statistics, Machine Learning, Pandas','https://www.linkedin.com/jobs/search/?keywords=Data%20Scientist&location=Bengaluru'),
    ('Frontend Engineer - Graduate','WebCraft','Hyderabad','Frontend Developer','JavaScript, React, HTML/CSS, Git','https://www.linkedin.com/jobs/search/?keywords=Frontend%20Developer&location=Hyderabad'),
    ('Backend Engineer - Graduate','CloudStack','Pune','Backend Developer','Python, FastAPI, SQL, Docker, Git','https://www.linkedin.com/jobs/search/?keywords=Backend%20Developer&location=Pune'),
    ('Data Analyst - Graduate','Insight Labs','Chennai','Data Analyst','SQL, Excel, Python, Statistics, Power BI','https://www.linkedin.com/jobs/search/?keywords=Data%20Analyst&location=Chennai'),
    ('DevOps Associate','InfraCloud','Hyderabad','DevOps Engineer','Linux, Git, Docker, CI/CD, Cloud','https://www.linkedin.com/jobs/search/?keywords=DevOps%20Engineer&location=Hyderabad')]
    for title,company,loc,career,req,url in rows: db.add(Job(title=title,company=company,location=loc,career=career,required_skills=req,apply_url=url,description=f'Entry-level opportunity aligned with {career}. Verify the employer and application details before applying.',experience_level='Entry-level',source='Career Copilot catalog'))
    db.commit()

@router.get('/')
def get_jobs(db:Session=Depends(get_db)):
    seed(db); return {'jobs':[pack(j) for j in db.query(Job).order_by(Job.id.desc()).all()]}

def pack(j): return {'id':j.id,'title':j.title,'company':j.company,'location':j.location,'job_type':j.job_type,'experience_level':j.experience_level,'career':j.career,'description':j.description,'required_skills':j.required_skills,'apply_url':j.apply_url,'source':j.source}

@router.get('/match')
def match(request:Request,career:str='',location:str='',db:Session=Depends(get_db)):
    uid=get_user_id(request); seed(db); p=db.query(Profile).filter(Profile.user_id==uid).first(); target=career or (p.target_role if p else '')
    if not target: raise HTTPException(400,'Select a target career first')
    student={norm(x) for x in ((p.skills if p else '') or '').replace('[','').replace(']','').replace('"','').split(',') if x.strip()}
    jobs=db.query(Job).all(); results=[]
    for j in jobs:
        if j.career and j.career != target: continue
        if location and location.lower() not in (j.location or '').lower(): continue
        req=skills(j.required_skills); matched=req & student; missing=req-student; score=round(len(matched)/len(req)*100) if req else 0
        results.append({**pack(j),'match_percentage':score,'matched_skills':sorted(matched),'missing_skills':sorted(missing)})
    results.sort(key=lambda x:x['match_percentage'],reverse=True)
    return {'career':target,'matches':results}
