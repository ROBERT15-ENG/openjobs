#!/usr/bin/env python3
"""Local development entry point (use gunicorn via wsgi.py in production)."""

import os
import sys

# email_notifier and friends live in the project root, one level up.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from app_factory import create_app  # noqa: E402

app = create_app()

if __name__ == '__main__':
    if os.environ.get('FLASK_ENV') == 'production':
        raise SystemExit(
            'Refusing to start the Flask dev server with FLASK_ENV=production. '
            'Run: gunicorn -c gunicorn.conf.py wsgi:app'
        )
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', '5700')), debug=False)
