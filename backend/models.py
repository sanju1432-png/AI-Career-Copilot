from sqlalchemy import Column, Integer, String, Text, ForeignKey
from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    text = Column(Text, default="")


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        unique=True,
        nullable=False
    )

    name = Column(String(120), default="")
    education = Column(String(255), default="")
    branch = Column(String(255), default="")
    interests = Column(Text, default="")
    target_role = Column(String(255), default="")
    skills = Column(Text, default="")
    profile_photo = Column(Text, default="")

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=False)
    location = Column(String(255), default="")
    job_type = Column(String(100), default="Full-time")
    description = Column(Text, default="")
    required_skills = Column(Text, default="")
    apply_url = Column(String(500), default="")    
