import os
from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import HTTPException, Request

SECRET_KEY = os.getenv('SECRET_KEY', 'change-this-secret-before-production')
ALGORITHM = 'HS256'
pwd = CryptContext(schemes=['bcrypt'], deprecated='auto')


def hash_password(password: str) -> str:
    return pwd.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd.verify(password, hashed)


def create_token(user_id: int, hours: int = 24) -> str:
    return jwt.encode({'sub': str(user_id), 'exp': datetime.utcnow() + timedelta(hours=hours)}, SECRET_KEY, algorithm=ALGORITHM)


def create_reset_token(user_id: int) -> str:
    return jwt.encode({'sub': str(user_id), 'purpose': 'reset', 'exp': datetime.utcnow() + timedelta(minutes=30)}, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str, purpose: str | None = None) -> int:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if purpose and payload.get('purpose') != purpose:
            raise ValueError('wrong purpose')
        return int(payload['sub'])
    except Exception:
        raise HTTPException(status_code=401, detail='Invalid or expired session')


def get_user_id(request: Request) -> int:
    token = request.cookies.get('career_session')
    if not token:
        auth = request.headers.get('Authorization', '')
        if auth.startswith('Bearer '):
            token = auth[7:]
    if not token:
        raise HTTPException(status_code=401, detail='Please sign in')
    return decode_token(token)
