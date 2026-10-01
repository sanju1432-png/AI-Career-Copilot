import os
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from jose import jwt
from passlib.context import CryptContext

SECRET_KEY = os.getenv('SECRET_KEY', 'change-this-secret-before-production')
ALGORITHM = 'HS256'
TOKEN_HOURS = int(os.getenv('TOKEN_HOURS', '24'))
pwd = CryptContext(schemes=['bcrypt'], deprecated='auto')


def hash_password(password: str) -> str:
    return pwd.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd.verify(password, hashed)


def create_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {'sub': str(user_id), 'iat': int(now.timestamp()), 'exp': now + timedelta(hours=TOKEN_HOURS)}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_user_id(token: str) -> int:
    try:
        return int(jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])['sub'])
    except Exception as exc:
        raise HTTPException(status_code=401, detail='Invalid or expired session') from exc
