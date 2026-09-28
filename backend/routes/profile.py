import json
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from database import get_db
from models import Profile
from auth import get_user_id
router=APIRouter()

def pack(p):
    return {'id':p.id,'user_id':p.user_id,'name':p.name or '','education':p.education or '','branch':p.branch or '','interests':p.interests or '','target_role':p.target_role or '','skills':json.loads(p.skills or '[]'),'profile_photo':p.profile_photo or '','location':p.location or '','experience_level':p.experience_level or 'Student','career_preferences':json.loads(p.career_preferences or '[]'),'bio':p.bio or ''}
@router.get('')
def get_profile(request:Request,db:Session=Depends(get_db)):
    uid=get_user_id(request); p=db.query(Profile).filter(Profile.user_id==uid).first(); return {'profile':pack(p) if p else None}
@router.put('')
def save_profile(payload:dict,request:Request,db:Session=Depends(get_db)):
    uid=get_user_id(request); p=db.query(Profile).filter(Profile.user_id==uid).first()
    if not p: p=Profile(user_id=uid); db.add(p)
    for key in ['name','education','branch','interests','target_role','profile_photo','location','experience_level','bio']:
        if key in payload: setattr(p,key,payload.get(key) or '')
    p.skills=json.dumps(payload.get('skills',[])); p.career_preferences=json.dumps(payload.get('career_preferences',[])); db.commit(); db.refresh(p)
    return {'message':'Profile saved','profile':pack(p)}
