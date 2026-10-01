import json
import os
import re
import secrets
import shutil
import tempfile
from datetime import datetime, timedelta
from typing import Optional

from dotenv import load_dotenv
load_dotenv()

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import inspect, text
from sqlalchemy.orm import Session

from auth import create_token, get_user_id, hash_password, verify_password
from database import Base, engine, get_db
from models import (
    CareerSelection, Goal, InterviewQuestion, InterviewSession, Job,
    PasswordReset, PortfolioProject, PracticeAttempt, Profile, Resume, User,
)
from services.ai_service import AIServiceError, ai_json, ai_text, analyze_resume, match_careers, roadmap, skill_intelligence, CAREERS, RESOURCE_MAP
from services.resume_parser import extract_text

app = FastAPI(title='AI Career & Placement Copilot', version='2.0.0')


def cors_origins():
    raw = os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://127.0.0.1:5173')
    return [x.strip() for x in raw.split(',') if x.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

bearer = HTTPBearer(auto_error=False)


def jdump(value):
    return json.dumps(value, ensure_ascii=False)


def jload(value, default):
    try:
        return json.loads(value) if value else default
    except Exception:
        return default


def normalize_skills(items):
    if not items:
        return []
    if isinstance(items, str):
        items = [x.strip() for x in items.split(',')]
    out, seen = [], set()
    for x in items:
        s = str(x).strip()
        key = re.sub(r'\s+', ' ', s.lower())
        if s and key not in seen:
            seen.add(key)
            out.append(s)
    return out


def migrate_schema():
    Base.metadata.create_all(bind=engine)
    # Render's current SQLite database predates some of the production fields.
    # Add missing nullable/defaulted columns without destroying user data.
    if not str(engine.url).startswith('sqlite'):
        return
    additions = {
        'profiles': {
            'location': "TEXT DEFAULT ''",
            'experience_level': "VARCHAR(100) DEFAULT 'Student'",
            'bio': "TEXT DEFAULT ''",
            'profile_photo': "TEXT DEFAULT ''",
            'created_at': "DATETIME",
            'updated_at': "DATETIME",
        },
        'resumes': {
            'score': 'INTEGER DEFAULT 0',
            'skills': "TEXT DEFAULT '[]'",
            'ats': "TEXT DEFAULT '{}'",
            'created_at': 'DATETIME',
        },
        'jobs': {
            'experience_level': "VARCHAR(100) DEFAULT 'Entry level'",
            'careers': "TEXT DEFAULT '[]'",
            'active': 'BOOLEAN DEFAULT 1',
        },
    }
    with engine.begin() as conn:
        inspector = inspect(engine)
        for table, cols in additions.items():
            existing = {c['name'] for c in inspector.get_columns(table)} if inspector.has_table(table) else set()
            for name, definition in cols.items():
                if name not in existing:
                    conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {name} {definition}'))


def seed_jobs(db: Session):
    if db.query(Job).count() > 0:
        return
    jobs = [
        ('Software Engineer', 'Google', 'India / Multiple locations', 'Entry level', 'Software engineering roles across products and infrastructure.', ['Python','JavaScript','SQL','Git'], ['Full Stack Developer','Backend Developer','Frontend Developer'], 'https://careers.google.com/jobs/results/'),
        ('Software Development Engineer', 'Amazon', 'India / Multiple locations', 'Entry level', 'Software development opportunities covering distributed systems, services and customer-facing products.', ['Java','Python','SQL','Git'], ['Backend Developer','Full Stack Developer'], 'https://www.amazon.jobs/en/'),
        ('Associate Software Engineer', 'Accenture', 'India / Multiple locations', 'Entry level', 'Technology roles spanning software engineering, cloud and data.', ['Python','Java','SQL','Git'], ['Backend Developer','Full Stack Developer','Cloud Engineer'], 'https://www.accenture.com/in-en/careers/jobsearch'),
        ('Data Analyst', 'Microsoft', 'India / Multiple locations', 'Entry level', 'Data and analytics opportunities supporting products and business decisions.', ['SQL','Excel','Power BI','Statistics'], ['Data Analyst','Product Analyst','Data Scientist'], 'https://jobs.careers.microsoft.com/global/en/search'),
        ('Machine Learning Engineer', 'NVIDIA', 'India / Multiple locations', 'Entry level', 'AI and accelerated computing opportunities involving machine learning systems.', ['Python','Machine Learning','Deep Learning','Git'], ['AI/ML Engineer','Data Scientist'], 'https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite'),
        ('Cloud Engineer', 'IBM', 'India / Multiple locations', 'Entry level', 'Cloud, infrastructure and automation opportunities.', ['Linux','Cloud','Docker','Kubernetes'], ['Cloud Engineer','DevOps Engineer','Backend Developer'], 'https://www.ibm.com/careers/search'),
        ('Cybersecurity Analyst', 'Cisco', 'India / Multiple locations', 'Entry level', 'Security operations and networking opportunities.', ['Networking','Linux','Security Fundamentals','SIEM'], ['Cybersecurity Analyst'], 'https://jobs.cisco.com/jobs/SearchJobs/'),
        ('QA Automation Engineer', 'Oracle', 'India / Multiple locations', 'Entry level', 'Quality engineering and test automation opportunities.', ['Selenium','API Testing','SQL','Git'], ['QA Automation Engineer'], 'https://careers.oracle.com/jobs/'),
    ]
    for title, company, location, level, desc, skills, careers, url in jobs:
        db.add(Job(title=title, company=company, location=location, experience_level=level, description=desc, required_skills=jdump(skills), careers=jdump(careers), apply_url=url))
    db.commit()


@app.on_event('startup')
def startup():
    migrate_schema()
    db = next(get_db())
    try:
        seed_jobs(db)
    finally:
        db.close()


@app.get('/')
def root():
    return {'message': 'AI Career & Placement Copilot API is running', 'version': app.version}


@app.get('/api/health')
def health():
    db_kind = 'postgresql' if str(engine.url).startswith('postgres') else 'sqlite'
    with engine.connect() as conn:
        conn.execute(text('SELECT 1'))
    return {'status': 'ok', 'database': db_kind}


# ---------- auth ----------
class AuthBody(BaseModel):
    name: str = 'Student'
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

class ForgotBody(BaseModel):
    email: EmailStr

class ResetBody(BaseModel):
    token: str
    password: str = Field(min_length=8, max_length=128)


def current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)) -> User:
    if not credentials:
        raise HTTPException(401, 'Authentication required')
    user_id = get_user_id(credentials.credentials)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(401, 'User session is no longer valid')
    return user


def user_payload(user):
    return {'id': user.id, 'name': user.name, 'email': user.email}


@app.post('/api/auth/register')
def register(body: AuthBody, db: Session = Depends(get_db)):
    email = str(body.email).lower().strip()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(409, 'Email already registered')
    user = User(name=body.name.strip() or 'Student', email=email, password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    db.add(Profile(user_id=user.id, name=user.name, skills='[]', experience_level='Student'))
    db.commit()
    return {'token': create_token(user.id), 'user': user_payload(user)}


@app.post('/api/auth/login')
def login(body: AuthBody, db: Session = Depends(get_db)):
    email = str(body.email).lower().strip()
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(401, 'Invalid email or password')
    return {'token': create_token(user.id), 'user': user_payload(user)}


@app.get('/api/auth/me')
def me(user: User = Depends(current_user)):
    return {'user': user_payload(user)}


@app.post('/api/auth/logout')
def logout():
    return {'message': 'Signed out'}


@app.post('/api/auth/forgot-password')
def forgot_password(body: ForgotBody, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == str(body.email).lower().strip()).first()
    # Do not disclose whether an email exists.
    response = {'message': 'If the account exists, reset instructions are ready.'}
    if not user:
        return response
    token = secrets.token_urlsafe(32)
    db.add(PasswordReset(user_id=user.id, token=token, expires_at=datetime.utcnow() + timedelta(minutes=30)))
    db.commit()
    # Production email integration can be configured later; returning the token is only for local/development flows.
    if os.getenv('RESET_TOKEN_IN_RESPONSE', 'false').lower() == 'true':
        response['development_reset_token'] = token
    return response


@app.post('/api/auth/reset-password')
def reset_password(body: ResetBody, db: Session = Depends(get_db)):
    reset = db.query(PasswordReset).filter(PasswordReset.token == body.token, PasswordReset.used == False).first()
    if not reset or reset.expires_at < datetime.utcnow():
        raise HTTPException(400, 'Invalid or expired reset token')
    user = db.query(User).filter(User.id == reset.user_id).first()
    if not user:
        raise HTTPException(400, 'Invalid reset request')
    user.password_hash = hash_password(body.password)
    reset.used = True
    db.commit()
    return {'message': 'Password reset successfully'}


# ---------- profile ----------
class ProfileBody(BaseModel):
    name: str = ''
    education: str = ''
    branch: str = ''
    location: str = ''
    experience_level: str = 'Student'
    target_role: str = ''
    interests: str = ''
    bio: str = ''
    skills: list[str] = []
    profile_photo: str = ''


def profile_dict(p: Profile):
    return {
        'id': p.id, 'user_id': p.user_id, 'name': p.name or '', 'education': p.education or '',
        'branch': p.branch or '', 'location': getattr(p, 'location', '') or '',
        'experience_level': getattr(p, 'experience_level', 'Student') or 'Student',
        'target_role': p.target_role or '', 'interests': p.interests or '', 'bio': getattr(p, 'bio', '') or '',
        'skills': normalize_skills(jload(p.skills, [])), 'profile_photo': p.profile_photo or ''
    }


@app.get('/api/profile')
def get_my_profile(user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not p:
        p = Profile(user_id=user.id, name=user.name, skills='[]', experience_level='Student')
        db.add(p); db.commit(); db.refresh(p)
    return {'profile': profile_dict(p)}


@app.put('/api/profile')
def put_profile(body: ProfileBody, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not p:
        p = Profile(user_id=user.id)
        db.add(p)
    p.name = body.name.strip() or user.name
    p.education = body.education.strip()
    p.branch = body.branch.strip()
    p.location = body.location.strip()
    p.experience_level = body.experience_level.strip() or 'Student'
    p.target_role = body.target_role.strip()
    p.interests = body.interests.strip()
    p.bio = body.bio.strip()
    p.skills = jdump(normalize_skills(body.skills))
    p.profile_photo = body.profile_photo
    db.commit(); db.refresh(p)
    return {'profile': profile_dict(p)}


# Backward compatibility with the older frontend.
@app.post('/api/profile')
def post_profile(body: dict, user: User = Depends(current_user), db: Session = Depends(get_db)):
    data = ProfileBody(**{k: v for k, v in body.items() if k in ProfileBody.model_fields})
    return put_profile(data, user, db)


# ---------- resume ----------
@app.post('/api/resume/analyze')
async def resume_analyze(file: UploadFile = File(...), user: User = Depends(current_user), db: Session = Depends(get_db)):
    ext = os.path.splitext(file.filename or '')[1].lower()
    if ext not in {'.pdf', '.docx', '.txt'}:
        raise HTTPException(400, 'Upload PDF, DOCX or TXT')
    fd, path = tempfile.mkstemp(suffix=ext)
    os.close(fd)
    try:
        with open(path, 'wb') as out:
            shutil.copyfileobj(file.file, out)
        text_content = extract_text(path)
        result = analyze_resume(text_content)
        words = re.findall(r'[A-Za-z0-9+#./-]+', text_content)
        keyword_coverage = min(100, round(len(result['skills']) / max(1, min(15, len(words) // 25 + 1)) * 100))
        result['ats'] = {
            'keyword_coverage': keyword_coverage,
            'structure': 'Pass' if len(text_content) > 800 else 'Needs improvement',
            'readability': 'Good' if len(text_content) > 500 else 'Needs improvement',
            'role_alignment': result['career_matches'][0]['match'] if result['career_matches'] else 0,
        }
        resume = Resume(user_id=user.id, filename=file.filename or 'resume', text=text_content, score=result['score'], skills=jdump(result['skills']), ats=jdump(result['ats']))
        db.add(resume)
        p = db.query(Profile).filter(Profile.user_id == user.id).first()
        if not p:
            p = Profile(user_id=user.id, name=user.name, skills='[]', experience_level='Student'); db.add(p)
        p.skills = jdump(result['skills'])
        db.commit()
        return result
    except ValueError as e:
        raise HTTPException(400, str(e)) from e
    finally:
        try: os.remove(path)
        except OSError: pass


# ---------- career ----------
class CareerBody(BaseModel):
    skills: list[str] = []
    target: str = 'AI/ML Engineer'


@app.post('/api/career/recommend')
def career_recommend(body: CareerBody, user: User = Depends(current_user)):
    return {'recommendations': match_careers(normalize_skills(body.skills))}


@app.post('/api/career/skills')
def career_skills(body: CareerBody, user: User = Depends(current_user)):
    if body.target not in CAREERS:
        raise HTTPException(400, 'Unsupported career')
    return skill_intelligence(normalize_skills(body.skills), body.target)


@app.post('/api/career/roadmap')
def career_roadmap(body: CareerBody, user: User = Depends(current_user)):
    if body.target not in CAREERS:
        raise HTTPException(400, f'Unsupported career: {body.target}')
    return {'roadmap': roadmap(normalize_skills(body.skills), body.target)}


@app.post('/api/career/coach')
def career_coach(body: CareerBody, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = db.query(Profile).filter(Profile.user_id == user.id).first()
    profile = profile_dict(p) if p else {'name': user.name, 'skills': body.skills}
    prompt = f'''You are a career coach for a college student. Give practical, specific guidance grounded in the student's actual profile.
Target career: {body.target}
Skills: {', '.join(body.skills)}
Education: {profile.get('education','')}
Branch: {profile.get('branch','')}
Location: {profile.get('location','')}
Interests: {profile.get('interests','')}
Experience: {profile.get('experience_level','Student')}

Return:
1. What the student already has
2. Highest-priority gaps
3. Next 30-day actions
4. One portfolio project
5. Interview focus
Do not invent achievements.'''
    try:
        return {'advice': ai_text(prompt)}
    except AIServiceError as e:
        raise HTTPException(503, str(e)) from e


# ---------- jobs ----------
@app.get('/api/jobs/match')
def jobs_match(career: str = '', user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = db.query(Profile).filter(Profile.user_id == user.id).first()
    skills = normalize_skills(jload(p.skills, [])) if p else []
    ss = {re.sub(r'\s+', ' ', s.lower()) for s in skills}
    jobs = db.query(Job).filter(Job.active == True).order_by(Job.id.desc()).all()
    results = []
    for j in jobs:
        req = normalize_skills(jload(j.required_skills, []))
        careers = jload(j.careers, [])
        if career and careers and career not in careers:
            continue
        matched = [s for s in req if re.sub(r'\s+', ' ', s.lower()) in ss]
        missing = [s for s in req if s not in matched]
        score = round(len(matched) / len(req) * 100) if req else 0
        results.append({'id':j.id,'title':j.title,'company':j.company,'location':j.location,'experience_level':j.experience_level,'description':j.description,'required_skills':req,'apply_url':j.apply_url,'match_percentage':score,'matched_skills':matched,'missing_skills':missing})
    results.sort(key=lambda x: (-x['match_percentage'], x['company'], x['title']))
    return {'matches': results}


# ---------- dashboard ----------
def profile_complete(p):
    if not p: return 0
    fields = [p.name, p.education, p.branch, p.location, p.target_role, p.interests, p.bio]
    filled = sum(1 for x in fields if x and str(x).strip())
    skills = normalize_skills(jload(p.skills, []))
    return round((filled / len(fields)) * 80 + min(20, len(skills) / 5 * 20), 1)


@app.get('/api/product/dashboard')
def dashboard(user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = db.query(Profile).filter(Profile.user_id == user.id).first()
    skills = normalize_skills(jload(p.skills, [])) if p else []
    target = p.target_role if p else ''
    skill_score = skill_intelligence(skills, target)['coverage'] if target in CAREERS else 0
    latest_resume = db.query(Resume).filter(Resume.user_id == user.id).order_by(Resume.id.desc()).first()
    resume_score = latest_resume.score if latest_resume else 0
    sessions = db.query(InterviewSession).filter(InterviewSession.user_id == user.id, InterviewSession.status == 'completed', InterviewSession.score.isnot(None)).all()
    interview_avg = round(sum(x.score for x in sessions) / len(sessions)) if sessions else 0
    goals = db.query(Goal).filter(Goal.user_id == user.id).all()
    projects = db.query(PortfolioProject).filter(PortfolioProject.user_id == user.id).all()
    goal_score = round(sum(1 for g in goals if g.completed) / len(goals) * 100) if goals else 0
    project_score = min(100, len(projects) * 25)
    breakdown = {'profile': round(profile_complete(p)), 'resume': resume_score, 'skill_fit': skill_score, 'interview': interview_avg}
    readiness = round(breakdown['profile'] * .20 + resume_score * .25 + skill_score * .25 + interview_avg * .25 + max(goal_score, project_score) * .05)
    return {'readiness_score': readiness, 'profile_complete': profile_complete(p), 'roadmap_coverage': skill_score, 'interview_average': interview_avg, 'readiness_breakdown': breakdown, 'skills_count': len(skills), 'resume_count': db.query(Resume).filter(Resume.user_id == user.id).count(), 'goals_count': len(goals), 'projects_count': len(projects)}


# ---------- goals / portfolio ----------
class GoalBody(BaseModel):
    title: str
    description: str = ''
    category: str = 'general'

@app.get('/api/product/goals')
def get_goals(user: User = Depends(current_user), db: Session = Depends(get_db)):
    goals = db.query(Goal).filter(Goal.user_id == user.id).order_by(Goal.id.desc()).all()
    return {'goals': [{'id':g.id,'title':g.title,'description':g.description,'category':g.category,'completed':g.completed} for g in goals]}

@app.post('/api/product/goals')
def add_goal(body: GoalBody, user: User = Depends(current_user), db: Session = Depends(get_db)):
    g = Goal(user_id=user.id, title=body.title.strip(), description=body.description.strip(), category=body.category)
    db.add(g); db.commit(); db.refresh(g)
    return {'goal': {'id':g.id,'title':g.title,'description':g.description,'category':g.category,'completed':g.completed}}

@app.patch('/api/product/goals/{goal_id}')
def update_goal(goal_id: int, body: dict, user: User = Depends(current_user), db: Session = Depends(get_db)):
    g = db.query(Goal).filter(Goal.id == goal_id, Goal.user_id == user.id).first()
    if not g: raise HTTPException(404, 'Goal not found')
    if 'completed' in body: g.completed = bool(body['completed'])
    if 'title' in body: g.title = str(body['title']).strip()
    db.commit()
    return {'message':'Goal updated'}

@app.get('/api/product/portfolio')
def get_portfolio(user: User = Depends(current_user), db: Session = Depends(get_db)):
    rows = db.query(PortfolioProject).filter(PortfolioProject.user_id == user.id).order_by(PortfolioProject.id.desc()).all()
    return {'projects':[{'id':p.id,'title':p.title,'description':p.description,'tech_stack':p.tech_stack,'status':p.status} for p in rows]}

class ProjectBody(BaseModel):
    title: str
    description: str = ''
    tech_stack: str = ''

@app.post('/api/product/portfolio')
def add_project(body: ProjectBody, user: User = Depends(current_user), db: Session = Depends(get_db)):
    p = PortfolioProject(user_id=user.id, title=body.title.strip(), description=body.description.strip(), tech_stack=body.tech_stack.strip(), status='Planned')
    db.add(p); db.commit(); db.refresh(p)
    return {'project': {'id':p.id,'title':p.title,'description':p.description,'tech_stack':p.tech_stack,'status':p.status}}


# ---------- practice ----------
PRACTICE = {
    'technical': [
        'Explain the difference between a process and a thread.',
        'What is normalization in relational databases and why is it useful?',
        'Explain REST and the role of HTTP status codes.',
    ],
    'coding': [
        'Given an array of integers, explain an O(n) approach to find the first duplicate.',
        'Design an API endpoint for creating a student profile and describe validation and error handling.',
        'Explain how you would debug a slow SQL query in production.',
    ],
    'aptitude': [
        'A value increases by 20% and then decreases by 20%. What is the net percentage change? Explain.',
        'If 5 workers finish a task in 12 days at the same rate, how many days would 8 workers take?',
        'Explain how you would reason through a time-and-work problem before calculating.',
    ],
    'hr': [
        'Tell me about a project where you had to learn something quickly.',
        'Describe a time you received difficult feedback and what you changed.',
        'Why are you interested in your chosen career path?',
    ],
}

@app.get('/api/product/practice')
def practice(category: str = 'technical', user: User = Depends(current_user)):
    if category not in PRACTICE: raise HTTPException(400, 'Unknown practice category')
    return {'questions':[{'id':i+1,'question':q,'category':category} for i,q in enumerate(PRACTICE[category])]}

class PracticeBody(BaseModel):
    category: str
    question: str
    answer: str = ''

@app.post('/api/product/practice/submit')
def submit_practice(body: PracticeBody, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if not body.answer.strip(): raise HTTPException(400, 'Write an answer before requesting feedback')
    prompt = f'''Evaluate this {body.category} practice answer for a college placement candidate.
Question: {body.question}
Answer: {body.answer}
Return JSON with score (0-100 integer), feedback (string), strengths (array of strings), improvement_points (array of strings). Be specific and do not invent facts.'''
    try:
        data = ai_json(prompt)
    except AIServiceError as e:
        raise HTTPException(503, str(e)) from e
    attempt = PracticeAttempt(user_id=user.id, category=body.category, question=body.question, answer=body.answer, score=int(data.get('score',0)), feedback=str(data.get('feedback','')))
    db.add(attempt); db.commit()
    return {'evaluation': {'score': attempt.score, 'feedback': attempt.feedback, 'strengths': data.get('strengths',[]), 'improvement_points': data.get('improvement_points',[])}}


# ---------- interviews ----------
ROLE_QUESTIONS = {
    'AI/ML Engineer': [
        ('technical','medium','Explain overfitting and two practical ways to reduce it.'),
        ('technical','medium','How would you evaluate a binary classification model when false positives and false negatives have different costs?'),
        ('project','medium','Walk me through one ML project: problem, data, model choice, evaluation and what you would improve.'),
        ('scenario','hard','A model performs well offline but poorly after deployment. What would you investigate first?'),
        ('hr','medium','Tell me about a time you had to learn a difficult technical topic quickly.'),
    ],
    'Data Scientist': [
        ('technical','medium','How do you detect data leakage in a machine-learning pipeline?'),
        ('technical','medium','Explain the trade-off between precision and recall with an example.'),
        ('project','medium','Describe an analysis where your findings changed a decision.'),
        ('scenario','hard','A stakeholder asks for a prediction model but the historical labels are unreliable. What do you do?'),
        ('hr','medium','Tell me about a time you communicated a technical result to a non-technical audience.'),
    ],
    'Full Stack Developer': [
        ('technical','medium','Explain how a React frontend communicates with a backend API and where authentication belongs.'),
        ('technical','medium','What database indexing problem can cause a slow endpoint and how would you diagnose it?'),
        ('project','medium','Walk me through a full-stack project and one architecture trade-off you made.'),
        ('scenario','hard','A production API becomes slow after a release. How would you isolate the problem?'),
        ('hr','medium','Describe a time you handled a difficult bug under time pressure.'),
    ],
    'Backend Developer': [
        ('technical','medium','What makes an API production-ready beyond simply returning correct responses?'),
        ('technical','medium','Explain database transactions and a case where rollback matters.'),
        ('project','medium','Describe a backend project and how you handled validation, errors and persistence.'),
        ('scenario','hard','An endpoint starts timing out for some users. What is your investigation sequence?'),
        ('hr','medium','Tell me about a backend issue you solved by reading documentation or source material.'),
    ],
}
ROLE_QUESTIONS['Frontend Developer'] = ROLE_QUESTIONS['Full Stack Developer']
ROLE_QUESTIONS['DevOps Engineer'] = ROLE_QUESTIONS['Backend Developer']
ROLE_QUESTIONS['Cloud Engineer'] = ROLE_QUESTIONS['Backend Developer']
ROLE_QUESTIONS['Cybersecurity Analyst'] = ROLE_QUESTIONS['Backend Developer']
ROLE_QUESTIONS['QA Automation Engineer'] = ROLE_QUESTIONS['Backend Developer']
ROLE_QUESTIONS['Mobile App Developer'] = ROLE_QUESTIONS['Frontend Developer']
ROLE_QUESTIONS['Product Analyst'] = ROLE_QUESTIONS['Data Scientist']
ROLE_QUESTIONS['Data Analyst'] = ROLE_QUESTIONS['Data Scientist']

class InterviewStart(BaseModel):
    target: str
    session_type: str = 'mock'
    difficulty: str = 'adaptive'
    skills: list[str] = []

@app.get('/api/interview/analytics')
def interview_analytics(user: User = Depends(current_user), db: Session = Depends(get_db)):
    sessions = db.query(InterviewSession).filter(InterviewSession.user_id == user.id, InterviewSession.status == 'completed', InterviewSession.score.isnot(None)).order_by(InterviewSession.id.asc()).all()
    avg = round(sum(s.score for s in sessions)/len(sessions)) if sessions else 0
    by_cat = {}
    for s in sessions:
        qs = db.query(InterviewQuestion).filter(InterviewQuestion.session_id == s.id, InterviewQuestion.score.isnot(None)).all()
        for q in qs: by_cat.setdefault(q.category, []).append(q.score)
    by_category = {k: round(sum(v)/len(v)) for k,v in by_cat.items()}
    return {'average_score':avg,'attempts':len(sessions),'by_category':by_category,'history':[{'session_id':s.id,'score':s.score,'target':s.target,'completed_at':s.completed_at.isoformat() if s.completed_at else None} for s in sessions[-10:]]}

@app.post('/api/interview/start')
def interview_start(body: InterviewStart, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if body.target not in CAREERS: raise HTTPException(400, 'Unsupported career')
    s = InterviewSession(user_id=user.id, target=body.target, session_type=body.session_type, difficulty=body.difficulty)
    db.add(s); db.flush()
    qs = ROLE_QUESTIONS.get(body.target, ROLE_QUESTIONS['Backend Developer'])
    for category,diff,q in qs:
        db.add(InterviewQuestion(session_id=s.id, category=category, difficulty=diff, question=q))
    db.commit(); db.refresh(s)
    questions = db.query(InterviewQuestion).filter(InterviewQuestion.session_id == s.id).order_by(InterviewQuestion.id).all()
    return {'session_id':s.id,'target':s.target,'questions':[{'id':q.id,'category':q.category,'difficulty':q.difficulty,'question':q.question} for q in questions]}

class AnswerBody(BaseModel):
    session_id: int
    question_id: int
    answer: str

@app.post('/api/interview/answer')
def interview_answer(body: AnswerBody, user: User = Depends(current_user), db: Session = Depends(get_db)):
    q = db.query(InterviewQuestion).join(InterviewSession, InterviewQuestion.session_id == InterviewSession.id).filter(InterviewQuestion.id == body.question_id, InterviewSession.id == body.session_id, InterviewSession.user_id == user.id).first()
    if not q: raise HTTPException(404, 'Interview question not found')
    if not body.answer.strip(): raise HTTPException(400, 'Write an answer before evaluation')
    prompt = f'''You are an interview evaluator. Evaluate a college candidate answer.
Target role: {db.query(InterviewSession).filter(InterviewSession.id==body.session_id).first().target}
Category: {q.category}
Question: {q.question}
Candidate answer: {body.answer}
Return JSON: score (0-100 integer), feedback (specific concise string), missing_points (array), ideal_answer (string), strengths (array). Score evidence in the answer only; do not assume experience not stated.'''
    try:
        data = ai_json(prompt)
    except AIServiceError as e:
        raise HTTPException(503, str(e)) from e
    q.answer = body.answer
    q.score = max(0, min(100, int(data.get('score',0))))
    q.feedback = str(data.get('feedback',''))
    q.missing_points = jdump(data.get('missing_points',[]))
    q.ideal_answer = str(data.get('ideal_answer',''))
    db.commit()
    return {'evaluation': {'score':q.score,'feedback':q.feedback,'missing_points':jload(q.missing_points,[]),'ideal_answer':q.ideal_answer,'strengths':data.get('strengths',[])}}

@app.post('/api/interview/finish/{session_id}')
def interview_finish(session_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    s = db.query(InterviewSession).filter(InterviewSession.id == session_id, InterviewSession.user_id == user.id).first()
    if not s: raise HTTPException(404, 'Interview session not found')
    qs = db.query(InterviewQuestion).filter(InterviewQuestion.session_id == s.id, InterviewQuestion.score.isnot(None)).all()
    if not qs: raise HTTPException(400, 'Evaluate at least one answer before finishing')
    s.score = round(sum(q.score for q in qs)/len(qs)); s.status='completed'; s.completed_at=datetime.utcnow()
    db.commit()
    return {'score':s.score,'session_id':s.id}


# Compatibility endpoints from the older frontend.
@app.post('/api/interview/questions')
def legacy_questions(body: dict, user: User = Depends(current_user)):
    target = body.get('target','AI/ML Engineer')
    return {'questions':[q for _,_,q in ROLE_QUESTIONS.get(target, ROLE_QUESTIONS['AI/ML Engineer'])]}

