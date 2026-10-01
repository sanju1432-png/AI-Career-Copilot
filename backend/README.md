# AI Career & Placement Copilot — Production Backend

This backend matches the current CareerCopilot frontend API surface.

## Render
- Root Directory: `backend`
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Python: use Render's supported Python 3.13/3.12 runtime if selectable.

Required environment variables:
- `SECRET_KEY`
- `DATABASE_URL` (SQLite for development; PostgreSQL URL for production)
- `CORS_ORIGINS`
- `GEMINI_API_KEY`
- `GEMINI_MODEL=gemini-3.6-flash`

The API includes authentication, profile, resume, career discovery, skill intelligence, roadmap, AI coach, interviews, analytics, jobs, learning/practice, portfolio and goals.
