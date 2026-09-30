from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from database import get_db
from models import User
from auth import hash_password, verify_password, create_token

router = APIRouter()


class AuthBody(BaseModel):
    name: str = "Student"
    email: str
    password: str


@router.post("/register")
def register(body: AuthBody, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    name = body.name.strip() or "Student"

    if len(body.password) < 8:
        raise HTTPException(400, "Password must be at least 8 characters")

    if db.query(User).filter(User.email == email).first():
        raise HTTPException(400, "Email already registered")

    try:
        user = User(
            name=name,
            email=email,
            password_hash=hash_password(body.password),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(400, "Email already registered")
    except Exception as exc:
        db.rollback()
        raise HTTPException(500, f"Registration failed: {exc}")

    return {
        "token": create_token(user.id),
        "user": {"id": user.id, "name": user.name, "email": user.email},
    }


@router.post("/login")
def login(body: AuthBody, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Invalid email or password")
    return {
        "token": create_token(user.id),
        "user": {"id": user.id, "name": user.name, "email": user.email},
    }
