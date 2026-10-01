from pathlib import Path
from pypdf import PdfReader
from docx import Document


def extract_text(path: str) -> str:
    suffix = Path(path).suffix.lower()
    if suffix == '.pdf':
        return '\n'.join(page.extract_text() or '' for page in PdfReader(path).pages)
    if suffix == '.docx':
        return '\n'.join(p.text for p in Document(path).paragraphs)
    if suffix == '.txt':
        return Path(path).read_text(encoding='utf-8', errors='ignore')
    raise ValueError('Supported files: PDF, DOCX or TXT')
