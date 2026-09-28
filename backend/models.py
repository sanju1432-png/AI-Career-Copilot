from sqlalchemy import Column, Integer, String, Text, ForeignKey, DateTime, Float, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login_at = Column(DateTime)
    is_active = Column(Boolean, default=True, nullable=False)

class Profile(Base):
    __tablename__ = 'profiles'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, nullable=False, index=True)
    name = Column(String(120), default='')
    education = Column(String(255), default='')
    branch = Column(String(255), default='')
    interests = Column(Text, default='')
    target_role = Column(String(255), default='')
    skills = Column(Text, default='[]')
    profile_photo = Column(Text, default='')
    location = Column(String(255), default='')
    experience_level = Column(String(100), default='Student')
    career_preferences = Column(Text, default='[]')
    bio = Column(Text, default='')

class Resume(Base):
    __tablename__ = 'resumes'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    text = Column(Text, default='')
    analysis = Column(Text, default='{}')
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class Job(Base):
    __tablename__ = 'jobs'
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=False)
    location = Column(String(255), default='')
    job_type = Column(String(100), default='Full-time')
    experience_level = Column(String(100), default='Entry-level')
    career = Column(String(255), default='', index=True)
    description = Column(Text, default='')
    required_skills = Column(Text, default='')
    apply_url = Column(String(500), default='')
    source = Column(String(100), default='')

class InterviewSession(Base):
    __tablename__ = 'interview_sessions'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    target_role = Column(String(255), nullable=False)
    session_type = Column(String(50), default='mock')
    difficulty = Column(String(50), default='medium')
    status = Column(String(50), default='active')
    score = Column(Float, default=0)
    feedback = Column(Text, default='{}')
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class InterviewQuestion(Base):
    __tablename__ = 'interview_questions'
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('interview_sessions.id'), nullable=False, index=True)
    question = Column(Text, nullable=False)
    category = Column(String(100), default='technical')
    difficulty = Column(String(50), default='medium')
    answer = Column(Text, default='')
    evaluation = Column(Text, default='{}')
    score = Column(Float, default=0)

class Goal(Base):
    __tablename__ = 'goals'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, default='')
    category = Column(String(100), default='roadmap')
    due_date = Column(String(50), default='')
    completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class PracticeAttempt(Base):
    __tablename__ = 'practice_attempts'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    category = Column(String(100), nullable=False)
    topic = Column(String(255), default='')
    question = Column(Text, default='')
    answer = Column(Text, default='')
    score = Column(Float, default=0)
    feedback = Column(Text, default='{}')
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

class PortfolioProject(Base):
    __tablename__ = 'portfolio_projects'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, default='')
    tech_stack = Column(Text, default='')
    status = Column(String(50), default='idea')
    github_url = Column(String(500), default='')
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
