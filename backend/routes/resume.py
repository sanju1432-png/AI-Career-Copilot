import os, uuid
from fastapi import APIRouter, UploadFile, File, HTTPException
from services.resume_parser import extract_text
from services.ai_service import analyze_resume

router = APIRouter()
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".pdf", ".docx", ".txt"]:
        raise HTTPException(400, "Upload PDF, DOCX or TXT")
    path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}{ext}")
    with open(path, "wb") as f:
        f.write(await file.read())
    try:
        text = extract_text(path)
        return analyze_resume(text)
    finally:
        try: os.remove(path)
        except OSError: pass
