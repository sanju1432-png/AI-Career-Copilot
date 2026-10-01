from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from database import Base


class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    name = Column(String(120), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Profile(Base):
    __tablename__ = 'profiles'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False, index=True)
    name = Column(String(120), default='')
    education = Column(String(255), default='')
    branch = Column(String(255), default='')
    location = Column(String(255), default='')
    experience_level = Column(String(100), default='Student')
    target_role = Column(String(255), default='')
    interests = Column(Text, default='')
    bio = Column(Text, default='')
    skills = Column(Text, default='[]')
    profile_photo = Column(Text, default='')
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class Resume(Base):
    __tablename__ = 'resumes'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    text = Column(Text, default='')
    score = Column(Integer, default=0)
    skills = Column(Text, default='[]')
    ats = Column(Text, default='{}')
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class Job(Base):
    __tablename__ = 'jobs'
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=False)
    location = Column(String(255), default='')
    experience_level = Column(String(100), default='Entry level')
    description = Column(Text, default='')
    required_skills = Column(Text, default='[]')
    careers = Column(Text, default='[]')
    apply_url = Column(String(800), default='')
    active = Column(Boolean, default=True)


class Goal(Base):
    __tablename__ = 'goals'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, default='')
    category = Column(String(100), default='general')
    completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class PortfolioProject(Base):
    __tablename__ = 'portfolio_projects'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, default='')
    tech_stack = Column(String(500), default='')
    status = Column(String(50), default='Planned')
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class InterviewSession(Base):
    __tablename__ = 'interview_sessions'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    target = Column(String(255), nullable=False)
    session_type = Column(String(50), default='mock')
    difficulty = Column(String(50), default='adaptive')
    status = Column(String(50), default='active')
    score = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)


class InterviewQuestion(Base):
    __tablename__ = 'interview_questions'
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('interview_sessions.id', ondelete='CASCADE'), nullable=False, index=True)
    category = Column(String(50), nullable=False)
    difficulty = Column(String(50), default='medium')
    question = Column(Text, nullable=False)
    answer = Column(Text, default='')
    score = Column(Integer, nullable=True)
    feedback = Column(Text, default='')
    missing_points = Column(Text, default='[]')
    ideal_answer = Column(Text, default='')
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class PracticeAttempt(Base):
    __tablename__ = 'practice_attempts'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    category = Column(String(50), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, default='')
    score = Column(Integer, nullable=True)
    feedback = Column(Text, default='')
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class PasswordReset(Base):
    __tablename__ = 'password_resets'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    token = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)


class CareerSelection(Base):
    __tablename__ = 'career_selections'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    career = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    __table_args__ = (UniqueConstraint('user_id', 'career', name='uq_user_career'),)
