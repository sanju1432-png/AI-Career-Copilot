import os, smtplib
from email.message import EmailMessage
from fastapi import APIRouter, Depends, HTTPException, Response, Request
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session
from database import get_db
from models import User
from auth import hash_password, verify_password, create_token, create_reset_token, decode_token, get_user_id
from datetime import datetime

router=APIRouter()
class RegisterBody(BaseModel): name:str=Field(min_length=2,max_length=120); email:EmailStr; password:str=Field(min_length=8,max_length=128)
class LoginBody(BaseModel): email:EmailStr; password:str
class ResetRequest(BaseModel): email:EmailStr
class ResetConfirm(BaseModel): token:str; password:str=Field(min_length=8,max_length=128)

def set_cookie(response,token): response.set_cookie('career_session',token,httponly=True,samesite='lax',secure=os.getenv('COOKIE_SECURE','false').lower()=='true',max_age=86400,path='/')

@router.post('/register')
def register(body:RegisterBody,db:Session=Depends(get_db)):
    email=body.email.lower();
    if db.query(User).filter(User.email==email).first(): raise HTTPException(409,'An account with this email already exists')
    u=User(name=body.name.strip(),email=email,password_hash=hash_password(body.password)); db.add(u); db.commit(); db.refresh(u)
    return {'message':'Account created successfully','user':{'id':u.id,'name':u.name,'email':u.email}}

@router.post('/login')
def login(body:LoginBody,response:Response,db:Session=Depends(get_db)):
    u=db.query(User).filter(User.email==body.email.lower()).first()
    if not u or not verify_password(body.password,u.password_hash): raise HTTPException(401,'Invalid email or password')
    u.last_login_at=datetime.utcnow(); db.commit(); token=create_token(u.id); set_cookie(response,token)
    return {'message':'Signed in successfully','token':token,'user':{'id':u.id,'name':u.name,'email':u.email}}

@router.post('/logout')
def logout(response:Response): response.delete_cookie('career_session',path='/'); return {'message':'Signed out'}

@router.get('/me')
def me(request:Request,db:Session=Depends(get_db)):
    uid=get_user_id(request); u=db.query(User).get(uid)
    if not u: raise HTTPException(401,'Account not found')
    return {'user':{'id':u.id,'name':u.name,'email':u.email}}

@router.post('/forgot-password')
def forgot(body:ResetRequest,db:Session=Depends(get_db)):
    u=db.query(User).filter(User.email==body.email.lower()).first(); result={'message':'If an account exists, reset instructions have been prepared.'}
    if not u: return result
    token=create_reset_token(u.id)
    host=os.getenv('FRONTEND_URL','http://localhost:5173'); link=f'{host}/?reset={token}'
    smtp_host=os.getenv('SMTP_HOST')
    if smtp_host:
        try:
            msg=EmailMessage(); msg['Subject']='Career Copilot password reset'; msg['From']=os.getenv('SMTP_FROM','noreply@example.com'); msg['To']=u.email; msg.set_content(f'Reset your password: {link}\nThis link expires in 30 minutes.')
            with smtplib.SMTP(smtp_host,int(os.getenv('SMTP_PORT','587')),timeout=20) as s:
                s.starttls(); s.login(os.getenv('SMTP_USER',''),os.getenv('SMTP_PASSWORD','')); s.send_message(msg)
        except Exception: pass
    else:
        result['development_reset_token']=token
    return result

@router.post('/reset-password')
def reset(body:ResetConfirm,db:Session=Depends(get_db)):
    uid=decode_token(body.token,'reset'); u=db.query(User).get(uid)
    if not u: raise HTTPException(404,'Account not found')
    u.password_hash=hash_password(body.password); db.commit(); return {'message':'Password reset successfully'}
