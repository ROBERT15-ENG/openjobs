"""WSGI entry point: ``gunicorn -c gunicorn.conf.py wsgi:app``."""

import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
for path in (os.path.join(ROOT, 'api'), ROOT):
    if path not in sys.path:
        sys.path.insert(0, path)

from app_factory import create_app  # noqa: E402

app = create_app()
