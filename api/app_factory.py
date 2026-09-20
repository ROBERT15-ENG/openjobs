"""Flask application factory."""

import logging
import os
import sys

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

load_dotenv()

from blueprints import register_blueprints
from config import TEMPLATES_DIR, ensure_upload_dir, is_production
from db import close_db, connect
from extensions import limiter

DEFAULT_SECRET = 'dev_secret_key_change_in_production'
LOCAL_ORIGINS = ['http://localhost:5700', 'http://127.0.0.1:5700']

log = logging.getLogger('openjobs')


def _configure_logging(testing: bool) -> None:
    if logging.getLogger().handlers:
        return
    level = os.environ.get('LOG_LEVEL', 'WARNING' if testing else 'INFO').upper()
    logging.basicConfig(
        level=level,
        format='%(asctime)s %(levelname)s %(name)s %(message)s',
        stream=sys.stdout,
    )


def _resolve_secret_key(test_config=None) -> str:
    secret = os.environ.get('SECRET_KEY')
    testing = bool(test_config and test_config.get('TESTING'))

    if testing:
        return secret or test_config.get('SECRET_KEY') or 'test-secret-key'

    if is_production():
        if not secret or secret == DEFAULT_SECRET:
            log.critical('Set a strong SECRET_KEY in production (32+ random bytes).')
            raise RuntimeError('SECRET_KEY must be set to a non-default value in production')

    return secret or DEFAULT_SECRET


def _cors_origins() -> list[str]:
    raw = os.environ.get('CORS_ORIGINS', '').strip()
    if raw:
        return [origin.strip().rstrip('/') for origin in raw.split(',') if origin.strip()]
    base = os.environ.get('BASE_URL', 'http://localhost:5700').rstrip('/')
    origins = [base]
    if not is_production():
        origins.extend(o for o in LOCAL_ORIGINS if o != base)
    return origins


def _wants_json() -> bool:
    return request.path.startswith('/api/') or request.is_json


ERROR_PAGE_COPY = {
    404: ('Page not found', "The page you're looking for doesn't exist, or the listing has closed."),
    403: ('Not allowed', "You don't have access to this page. Sign in with a different account or head back to the jobs list."),
    405: ('Not allowed', 'That action is not available here.'),
    429: ('Slow down', 'Too many requests in a short time. Wait a minute and try again.'),
    500: ('Something went wrong', 'An unexpected error occurred on our side. It has been logged; please try again shortly.'),
}


def render_error_page(code: int):
    """Branded HTML error page for non-API routes (JSON is used for /api/*)."""
    title, message = ERROR_PAGE_COPY.get(code, ERROR_PAGE_COPY[500])
    try:
        return render_template('error.html', code=code, title=title, message=message), code
    except Exception:  # template dir missing (API-only deployment)
        return f'{code} {title}', code


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(HTTPException)
    def handle_http_error(exc: HTTPException):
        if not _wants_json():
            if exc.code in ERROR_PAGE_COPY:
                return render_error_page(exc.code)
            return exc
        return jsonify({'error': exc.name, 'message': exc.description}), exc.code

    @app.errorhandler(Exception)
    def handle_unexpected_error(exc: Exception):
        log.exception('Unhandled error on %s %s', request.method, request.path)
        if app.config.get('PROPAGATE_EXCEPTIONS') or app.testing or app.debug:
            raise exc
        if not _wants_json():
            return render_error_page(500)
        return jsonify({'error': 'Internal Server Error'}), 500


def create_app(test_config=None):
    testing = bool(test_config and test_config.get('TESTING'))
    _configure_logging(testing)

    app = Flask(__name__, template_folder=TEMPLATES_DIR)
    app.secret_key = _resolve_secret_key(test_config)
    app.config['BASE_URL'] = os.environ.get('BASE_URL', 'http://localhost:5700')
    app.config['MAX_CONTENT_LENGTH'] = int(os.environ.get('MAX_CONTENT_LENGTH', 8 * 1024 * 1024))

    if test_config:
        app.config.update(test_config)

    try:
        from flask_cors import CORS
        CORS(
            app,
            resources={r'/api/*': {'origins': _cors_origins()}},
            supports_credentials=True,
        )
    except ImportError:
        pass

    production = is_production()

    @app.after_request
    def set_security_headers(response):
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        if production:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        # Pages carry their JS inline, so a heuristically cached page after a deploy
        # would talk to the new API with old code. Make browsers revalidate.
        if response.mimetype == 'text/html' and 'Cache-Control' not in response.headers:
            response.headers['Cache-Control'] = 'no-cache'
        return response

    limiter.init_app(app)
    if production and limiter._storage_uri.startswith('memory://'):
        log.warning(
            'RATELIMIT_STORAGE_URI is memory:// — limits are per-worker and reset on restart. '
            'Point it at Redis for shared, durable limits.'
        )

    app.teardown_appcontext(close_db)
    _register_error_handlers(app)
    register_blueprints(app)
    ensure_upload_dir()

    # Idempotent column/table adds for upgrades from older schema.sql
    try:
        from schema_migrate import ensure_schema
        conn = connect()
        try:
            ensure_schema(conn)
        finally:
            conn.close()
    except Exception:
        log.exception('[schema_migrate] failed')
        if not testing:
            raise

    return app
