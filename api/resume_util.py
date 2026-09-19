"""Resume upload and text extraction."""

import logging
import os
import re

from config import UPLOAD_DIR

log = logging.getLogger(__name__)

ALLOWED_EXT = {'.pdf', '.doc', '.docx'}
MAX_SIZE = 5 * 1024 * 1024


def extract_resume_text(filepath: str) -> str:
    ext = os.path.splitext(filepath)[1].lower()
    try:
        if ext == '.pdf':
            import pdfplumber
            with pdfplumber.open(filepath) as pdf:
                return '\n'.join(page.extract_text() or '' for page in pdf.pages)
        if ext == '.docx':
            import docx
            document = docx.Document(filepath)
            return '\n'.join(paragraph.text for paragraph in document.paragraphs)
        with open(filepath, 'rb') as handle:
            return handle.read().decode('utf-8', errors='ignore')
    except Exception as exc:
        log.warning('Resume extract error: %s', exc)
        return ''


def save_resume_file(user_id: int, filename: str, file_storage) -> tuple[str, str]:
    safe_name = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    stored_name = f'user_{user_id}_{int(__import__("time").time())}_{safe_name}'
    filepath = os.path.join(UPLOAD_DIR, stored_name)
    file_storage.save(filepath)
    if os.path.getsize(filepath) > MAX_SIZE:
        os.remove(filepath)
        raise ValueError('File too large. Maximum size is 5 MB.')
    return stored_name, filepath
