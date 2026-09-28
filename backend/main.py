import os
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text
from database import Base, engine
from routes.auth import router as auth_router
from routes.profile import router as profile_router
from routes.resume import router as resume_router
from routes.career import router as career_router
from routes.interview import router as interview_router
from routes.jobs import router as jobs_router
from routes.product import router as product_router

Base.metadata.create_all(bind=engine)

def migrate_legacy():
    # Preserve the existing SQLite database while adding new columns when they are absent.
    if not str(engine.url).startswith('sqlite'): return
    insp=inspect(engine)
    if 'users' in insp.get_table_names():
        cols={c['name'] for c in insp.get_columns('users')}
        additions={'created_at':'DATETIME','last_login_at':'DATETIME','is_active':'BOOLEAN'}
        with engine.begin() as conn:
            for name,typ in additions.items():
                if name not in cols: conn.execute(text(f'ALTER TABLE users ADD COLUMN {name} {typ}'))
    if 'jobs' in insp.get_table_names():
        cols={c['name'] for c in insp.get_columns('jobs')}
        additions={'experience_level':'VARCHAR(100)','career':'VARCHAR(255)','source':'VARCHAR(100)'}
        with engine.begin() as conn:
            for name,typ in additions.items():
                if name not in cols: conn.execute(text(f'ALTER TABLE jobs ADD COLUMN {name} {typ}'))
    if 'resumes' in insp.get_table_names():
        cols={c['name'] for c in insp.get_columns('resumes')}
        with engine.begin() as conn:
            if 'analysis' not in cols: conn.execute(text("ALTER TABLE resumes ADD COLUMN analysis TEXT DEFAULT '{}'"))
            if 'created_at' not in cols: conn.execute(text("ALTER TABLE resumes ADD COLUMN created_at DATETIME"))
    if 'profiles' in insp.get_table_names():
        cols={c['name'] for c in insp.get_columns('profiles')}; additions={'location':'VARCHAR(255)','experience_level':'VARCHAR(100)','career_preferences':'TEXT','bio':'TEXT'}
        with engine.begin() as conn:
            for name,typ in additions.items():
                if name not in cols: conn.execute(text(f'ALTER TABLE profiles ADD COLUMN {name} {typ}'))

migrate_legacy()
app=FastAPI(title='AI Career & Placement Copilot',version='2.0.0')
origins=[x.strip() for x in os.getenv('CORS_ORIGINS','http://localhost:5173,http://127.0.0.1:5173').split(',') if x.strip()]
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_credentials=True,allow_methods=['*'],allow_headers=['*'])
app.include_router(auth_router,prefix='/api/auth',tags=['Authentication'])
app.include_router(profile_router,prefix='/api/profile',tags=['Profile'])
app.include_router(resume_router,prefix='/api/resume',tags=['Resume'])
app.include_router(career_router,prefix='/api/career',tags=['Career'])
app.include_router(interview_router,prefix='/api/interview',tags=['Interview'])
app.include_router(jobs_router,prefix='/api/jobs',tags=['Jobs'])
app.include_router(product_router,prefix='/api/product',tags=['Product'])
@app.get('/')
def root(): return {'message':'AI Career & Placement Copilot API is running','version':'2.0.0'}
@app.get('/api/health')
def health(): return {'status':'ok','database':str(engine.url).split(':')[0]}
