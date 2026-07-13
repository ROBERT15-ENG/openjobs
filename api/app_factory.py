"""Flask application factory."""

import os
import sys

from dotenv import load_dotenv
from flask import Flask

load_dotenv()

from blueprints import register_blueprints
from config import TEMPLATES_DIR
from db import close_db
from extensions import limiter

DEFAULT_SECRET = 'dev_secret_key_change_in_production'


def _resolve_secret_key(test_config=None) -> str:
    secret = os.environ.get('SECRET_KEY')
    testing = bool(test_config and test_config.get('TESTING'))
    production = os.environ.get('FLASK_ENV') == 'production'

    if testing:
        return secret or test_config.get('SECRET_KEY') or 'test-secret-key'

    if production:
        if not secret or secret == DEFAULT_SECRET:
            print('FATAL: Set a strong SECRET_KEY in production (32+ random bytes).', file=sys.stderr)
            raise RuntimeError('SECRET_KEY must be set to a non-default value in production')

    return secret or DEFAULT_SECRET


def _cors_origins() -> list[str]:
    raw = os.environ.get('CORS_ORIGINS', '').strip()
    if raw:
        return [origin.strip().rstrip('/') for origin in raw.split(',') if origin.strip()]
    base = os.environ.get('BASE_URL', 'http://localhost:5700').rstrip('/')
    return [base, 'http://localhost:5700', 'http://127.0.0.1:5700']


def create_app(test_config=None):
    app = Flask(__name__, template_folder=TEMPLATES_DIR)
    app.secret_key = _resolve_secret_key(test_config)
    app.config['BASE_URL'] = os.environ.get('BASE_URL', 'http://localhost:5700')

    if test_config:
        app.config.update(test_config)

    try:
        from flask_cors import CORS
        CORS(app, resources={r'/api/*': {'origins': _cors_origins()}})
    except ImportError:
        pass

    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response

    limiter.init_app(app)
    app.teardown_appcontext(close_db)
    register_blueprints(app)
    return app
