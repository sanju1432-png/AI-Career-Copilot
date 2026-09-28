import json
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models import Profile, Goal, PracticeAttempt, PortfolioProject, InterviewSession, Resume, Job
from auth import get_user_id
from services.ai_service import CAREERS, ai_text, ai_json, skill_intelligence, AIServiceError
router=APIRouter()

def uid(request): return get_user_id(request)
@router.get('/dashboard')
def dashboard(request:Request,db:Session=Depends(get_db)):
    u=uid(request); p=db.query(Profile).filter(Profile.user_id==u).first(); resumes=db.query(Resume).filter(Resume.user_id==u).count(); sessions=db.query(InterviewSession).filter(InterviewSession.user_id==u).all(); goals=db.query(Goal).filter(Goal.user_id==u).all(); projects=db.query(PortfolioProject).filter(PortfolioProject.user_id==u).all()
    target=p.target_role if p else ''; skills=json.loads(p.skills or '[]') if p else []; coverage=skill_intelligence(skills,target)['coverage'] if target in CAREERS else 0; interview=[s.score for s in sessions if s.status=='completed']; interview_avg=round(sum(interview)/len(interview)) if interview else 0; goal_rate=round(sum(1 for g in goals if g.completed)/len(goals)*100) if goals else 0
    readiness=round(0.25*min(100,20+len(skills)*8)+0.25*coverage+0.25*interview_avg+0.15*goal_rate+0.10*(90 if resumes else 0))
    return {'profile_complete':sum(bool(getattr(p,x,'')) for x in ['name','education','branch','target_role','location'])/5*100 if p else 0,'resume_count':resumes,'skills_count':len(skills),'target_role':target,'roadmap_coverage':coverage,'interview_average':interview_avg,'goals_completed':sum(g.completed for g in goals),'goals_total':len(goals),'projects':len(projects),'readiness_score':readiness,'readiness_breakdown':{'skills':round(min(100,20+len(skills)*8)),'career_skill_fit':coverage,'interview':interview_avg,'goals':goal_rate,'resume':90 if resumes else 0}}

@router.get('/goals')
def goals(request:Request,db:Session=Depends(get_db)):
    rows=db.query(Goal).filter(Goal.user_id==uid(request)).order_by(Goal.id.desc()).all(); return {'goals':[{'id':g.id,'title':g.title,'description':g.description,'category':g.category,'due_date':g.due_date,'completed':g.completed} for g in rows]}
@router.post('/goals')
def add_goal(body:dict,request:Request,db:Session=Depends(get_db)):
    g=Goal(user_id=uid(request),title=body.get('title','Untitled goal'),description=body.get('description',''),category=body.get('category','roadmap'),due_date=body.get('due_date','')); db.add(g); db.commit(); db.refresh(g); return {'goal':{'id':g.id,'title':g.title,'description':g.description,'due_date':g.due_date,'completed':g.completed}}
@router.patch('/goals/{goal_id}')
def toggle_goal(goal_id:int,body:dict,request:Request,db:Session=Depends(get_db)):
    g=db.query(Goal).filter(Goal.id==goal_id,Goal.user_id==uid(request)).first()
    if not g: raise HTTPException(404,'Goal not found')
    g.completed=bool(body.get('completed',g.completed)); db.commit(); return {'message':'Goal updated'}

PRACTICE={
 'coding':['Implement a function that returns the first non-repeating character.','Explain the time complexity of a hash-map based solution.'],
 'technical':['Explain REST vs GraphQL and when you would choose each.','What is normalization and when can denormalization help?'],
 'aptitude':['A train travels 60 km in 45 minutes. What is its average speed?','If a value rises by 20% and then falls by 20%, what is the net percentage change?'],
 'hr':['Tell me about yourself in 90 seconds.','Describe a time you received difficult feedback and what you changed.']}
@router.get('/practice')
def practice(category:str='technical'):
    return {'category':category,'questions':[{'id':i+1,'question':q} for i,q in enumerate(PRACTICE.get(category,PRACTICE['technical']))]}
@router.post('/practice/submit')
def practice_submit(body:dict,request:Request,db:Session=Depends(get_db)):
    answer=body.get('answer','').strip()
    if not answer: raise HTTPException(400,'Please enter an answer before requesting AI evaluation.')
    prompt=f'Evaluate this practice answer. Category: {body.get("category")}. Question: {body.get("question")}. Answer: {answer}. Return JSON score 0-100, feedback, key_points, strengths, missing_points, ideal_answer.'
    try:
        ev=ai_json(prompt)
    except AIServiceError as exc:
        raise HTTPException(503, str(exc))
    ev['score']=max(0,min(100,float(ev.get('score',0))))
    ev.setdefault('feedback',''); ev.setdefault('key_points',[]); ev.setdefault('strengths',[]); ev.setdefault('missing_points',[]); ev.setdefault('ideal_answer','')
    a=PracticeAttempt(user_id=uid(request),category=body.get('category','technical'),topic=body.get('topic',''),question=body.get('question',''),answer=body.get('answer',''),score=ev.get('score',0),feedback=json.dumps(ev)); db.add(a); db.commit(); return {'evaluation':ev}

@router.get('/portfolio')
def get_portfolio(request:Request,db:Session=Depends(get_db)):
    rows=db.query(PortfolioProject).filter(PortfolioProject.user_id==uid(request)).order_by(PortfolioProject.id.desc()).all(); return {'projects':[{'id':p.id,'title':p.title,'description':p.description,'tech_stack':p.tech_stack,'status':p.status,'github_url':p.github_url} for p in rows]}
@router.post('/portfolio')
def add_portfolio(body:dict,request:Request,db:Session=Depends(get_db)):
    p=PortfolioProject(user_id=uid(request),title=body.get('title','Project'),description=body.get('description',''),tech_stack=body.get('tech_stack',''),status=body.get('status','idea'),github_url=body.get('github_url','')); db.add(p); db.commit(); db.refresh(p); return {'project':{'id':p.id,'title':p.title}}

@router.post('/explain')
def explain(body:dict,request:Request,db:Session=Depends(get_db)):
    u=uid(request); p=db.query(Profile).filter(Profile.user_id==u).first(); context=f'User target: {p.target_role if p else ""}; skills: {p.skills if p else ""}. User question: {body.get("question","")}'
    try:
        text=ai_text('You are an educational career AI assistant. '+context+' Give accurate, practical, student-friendly explanation. If unsure, say so.')
    except AIServiceError as exc:
        raise HTTPException(503, str(exc))
    return {'answer':text}
