import os, uuid, json
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request
from sqlalchemy.orm import Session
from database import get_db
from models import Resume
from auth import get_user_id
from services.resume_parser import extract_text
from services.ai_service import analyze_resume
router=APIRouter(); UPLOAD_DIR='uploads'; os.makedirs(UPLOAD_DIR,exist_ok=True)
@router.post('/analyze')
async def analyze(file:UploadFile=File(...),request:Request=None,db:Session=Depends(get_db)):
    uid=get_user_id(request); ext=os.path.splitext(file.filename)[1].lower()
    if ext not in ['.pdf','.docx','.txt']: raise HTTPException(400,'Upload PDF, DOCX or TXT')
    path=os.path.join(UPLOAD_DIR,f'{uuid.uuid4()}{ext}')
    with open(path,'wb') as f: f.write(await file.read())
    try:
        text=extract_text(path); result=analyze_resume(text)
        r=Resume(user_id=uid,filename=file.filename,text=text,analysis=json.dumps(result)); db.add(r); db.commit(); db.refresh(r)
        result.update({'resume_id':r.id,'filename':r.filename,'ats':{'keyword_coverage':min(100,40+len(result['skills'])*6),'format_score':90 if len(text)>300 else 65,'impact_score':70 if any(x in text.lower() for x in ['%','increased','reduced','built','deployed']) else 45,'suggestions':result['suggestions']}})
        r.analysis=json.dumps(result); db.commit(); return result
    finally:
        try: os.remove(path)
        except OSError: pass
@router.get('/history')
def history(request:Request,db:Session=Depends(get_db)):
    uid=get_user_id(request); rows=db.query(Resume).filter(Resume.user_id==uid).order_by(Resume.id.desc()).all(); return {'resumes':[{'id':r.id,'filename':r.filename,'created_at':(r.created_at or __import__('datetime').datetime.utcnow()).isoformat(),'analysis':json.loads(r.analysis or '{}')} for r in rows]}
