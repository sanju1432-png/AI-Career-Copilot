# AI Career & Placement Copilot

## Run locally

### Backend
```bash
cd backend
python3 -m pip install -r requirements.txt
cp .env.example .env
python3 -m uvicorn main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

Frontend: http://localhost:5173
Backend: http://127.0.0.1:8000

Add your own Gemini API key to `backend/.env`:
```env
GEMINI_API_KEY=your_key_here
GEMINI_MODEL=gemini-3.6-flash
```

Do not commit or share `.env`.

## AI evaluation
Interview answers, Practice Zone submissions and AI Career Coach responses use the Gemini Interactions API. There is no local/random score fallback for these AI features. If Gemini is unavailable, the API returns a clear error instead of fabricating an evaluation.

## Gemini AI setup

Create `backend/.env` locally (do not commit or share it):

```env
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3.6-flash
SECRET_KEY=replace-with-a-long-random-secret
```

The AI layer uses the Gemini Interactions API. Coach, interview evaluation, practice evaluation and explanations require a successful Gemini response; the app does not generate fake/random AI scores when Gemini is unavailable.
