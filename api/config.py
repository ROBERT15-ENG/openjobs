"""Application configuration."""

import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
TEMPLATES_DIR = os.path.join(PROJECT_ROOT, 'templates')
UPLOAD_DIR = os.environ.get('UPLOAD_DIR') or os.path.join(PROJECT_ROOT, 'uploads')
DEFAULT_DB_PATH = os.path.join(PROJECT_ROOT, 'jobs.db')


def is_production() -> bool:
    return os.environ.get('FLASK_ENV') == 'production'


def ensure_upload_dir() -> str:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    return UPLOAD_DIR
