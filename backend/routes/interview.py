import json, re
from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db
from models import Profile, InterviewSession, InterviewQuestion
from auth import get_user_id
from services.ai_service import CAREERS, ai_text, ai_json, AIServiceError
router=APIRouter()
QUESTION_BANK={
'AI/ML Engineer':[('technical','Explain overfitting and two practical ways to reduce it.'),('technical','How would you design a model serving API for a production ML model?'),('scenario','A model performs well offline but poorly in production. How would you investigate?'),('project','Walk through an AI/ML project you built and the trade-offs you made.'),('behavioral','Tell me about a technical mistake you made and how you corrected it.')],
'Data Scientist':[('technical','Explain precision, recall and when you would prioritize each.'),('technical','How would you detect data leakage in a predictive model?'),('scenario','A business metric drops after a model launch. What would you analyze first?'),('project','Explain an analysis or ML project and how you communicated its business impact.'),('behavioral','Describe a time you had to work with ambiguous requirements.')],
'Full Stack Developer':[('technical','Design a secure login flow for a React application and REST backend.'),('technical','Explain how React state, effects and API calls should be organized.'),('scenario','A page is slow in production. How would you debug it end to end?'),('project','Walk through a full-stack project and explain your architecture choices.'),('behavioral','Describe a difficult bug you solved and how you approached it.')],
'Backend Developer':[('technical','How would you design a REST API for a student placement platform?'),('technical','Explain indexing and when a database query needs optimization.'),('scenario','Your API suddenly receives 10x traffic. What would you do?'),('project','Describe a backend project including database and authentication decisions.'),('behavioral','Tell me about a time you improved reliability or performance.')],
}
class StartBody(BaseModel): target:str; difficulty:str='medium'; session_type:str='mock'; skills:list[str]=[]
class AnswerBody(BaseModel): session_id:int; question_id:int; answer:str

@router.post('/start')
def start(body:StartBody,request:Request,db:Session=Depends(get_db)):
    uid=get_user_id(request)
    if body.target not in CAREERS: raise HTTPException(400,'Unsupported career')
    s=InterviewSession(user_id=uid,target_role=body.target,session_type=body.session_type,difficulty=body.difficulty); db.add(s); db.commit(); db.refresh(s)
    bank=QUESTION_BANK.get(body.target,[])
    for cat,q in bank: db.add(InterviewQuestion(session_id=s.id,question=q,category=cat,difficulty=body.difficulty))
    db.commit(); qs=db.query(InterviewQuestion).filter(InterviewQuestion.session_id==s.id).all()
    return {'session_id':s.id,'questions':[{'id':q.id,'question':q.question,'category':q.category,'difficulty':q.difficulty} for q in qs]}

@router.post('/answer')
def answer(body:AnswerBody,request:Request,db:Session=Depends(get_db)):
    uid=get_user_id(request); q=db.query(InterviewQuestion).join(InterviewSession).filter(InterviewQuestion.id==body.question_id,InterviewSession.id==body.session_id,InterviewSession.user_id==uid).first()
    if not q: raise HTTPException(404,'Interview question not found')
    q.answer=body.answer.strip(); s=q.session_id; sess=db.query(InterviewSession).get(s)
    prompt=f'You are an expert interviewer evaluating a student answer. Career: {sess.target_role}. Category: {q.category}. Question: {q.question}. Answer: {body.answer}. Return concise JSON with score 0-100, strengths array, missing_points array, feedback, ideal_answer.'
    if not body.answer.strip():
        raise HTTPException(400,'Please enter an answer before requesting AI evaluation.')
    ev=ai_json(prompt)
    if not ev:
        raise HTTPException(503,'Gemini AI evaluation is unavailable. Check GEMINI_API_KEY and try again.')
    ev['score']=max(0,min(100,float(ev.get('score',0))))
    ev.setdefault('strengths',[])
    ev.setdefault('missing_points',[])
    ev.setdefault('feedback','')
    ev.setdefault('ideal_answer','')
    q.score=float(ev.get('score',0)); q.evaluation=json.dumps(ev); db.commit(); return {'evaluation':ev}

@router.post('/finish/{session_id}')
def finish(session_id:int,request:Request,db:Session=Depends(get_db)):
    uid=get_user_id(request); sess=db.query(InterviewSession).filter(InterviewSession.id==session_id,InterviewSession.user_id==uid).first()
    if not sess: raise HTTPException(404,'Session not found')
    qs=db.query(InterviewQuestion).filter(InterviewQuestion.session_id==session_id).all(); scores=[q.score for q in qs if q.answer]
    sess.score=round(sum(scores)/len(scores),1) if scores else 0; sess.status='completed'; sess.feedback=json.dumps({'answered':len(scores),'total':len(qs)}); db.commit()
    return {'score':sess.score,'answered':len(scores),'total':len(qs)}

@router.get('/history')
def history(request:Request,db:Session=Depends(get_db)):
    uid=get_user_id(request); rows=db.query(InterviewSession).filter(InterviewSession.user_id==uid).order_by(InterviewSession.id.desc()).all(); return {'history':[{'id':s.id,'target_role':s.target_role,'type':s.session_type,'score':s.score,'status':s.status,'created_at':s.created_at.isoformat()} for s in rows]}

@router.get('/analytics')
def analytics(request:Request,db:Session=Depends(get_db)):
    uid=get_user_id(request); sessions=db.query(InterviewSession).filter(InterviewSession.user_id==uid).all(); qs=db.query(InterviewQuestion).join(InterviewSession).filter(InterviewSession.user_id==uid).all(); scores=[q.score for q in qs if q.answer]; cats={}
    for q in qs:
        if q.answer: cats.setdefault(q.category,[]).append(q.score)
    return {'attempts':len(sessions),'average_score':round(sum(scores)/len(scores),1) if scores else 0,'by_category':{k:round(sum(v)/len(v),1) for k,v in cats.items()},'trend':[{'date':s.created_at.date().isoformat(),'score':s.score,'career':s.target_role} for s in sessions[-10:]]}
