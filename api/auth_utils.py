"""Authentication helpers and decorators."""

import datetime
import logging
import secrets
from functools import wraps

import jwt
from constants import JWT_ALGORITHM, JWT_EXPIRY_DAYS
from db import get_db
from flask import current_app, jsonify, request
from session_util import extract_bearer_or_cookie_token
from timeutil import from_timestamp, to_iso, utcnow, utcnow_iso
from werkzeug.security import check_password_hash, generate_password_hash

log = logging.getLogger(__name__)


def _employer_id_from_payload(payload: dict):
    """Return employer id only for employer accounts."""
    if payload.get('role') != 'employer':
        return None
    return payload.get('employer_id') or int(payload.get('user_id', 0) or 0)


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(password: str, pw_hash: str) -> bool:
    if not pw_hash:
        return False
    return check_password_hash(pw_hash, password)


def create_token(user) -> str:
    now = utcnow()
    payload = {
        'user_id': user['id'],
        'email': user['email'],
        'role': user['role'],
        'employer_id': user['id'] if user['role'] == 'employer' else None,
        'jti': secrets.token_urlsafe(16),
        'exp': now + datetime.timedelta(days=JWT_EXPIRY_DAYS),
        'iat': now,
    }
    token = jwt.encode(payload, current_app.secret_key, algorithm=JWT_ALGORITHM)
    return token if isinstance(token, str) else token.decode('utf-8')


def decode_token(token: str, verify_exp: bool = True):
    try:
        return jwt.decode(
            token,
            current_app.secret_key,
            algorithms=[JWT_ALGORITHM],
            options={'verify_exp': verify_exp},
        )
    except jwt.PyJWTError:
        return None


# --- Revocation -------------------------------------------------------------
#
# Tokens carry a random ``jti``. Logout writes the jti to ``revoked_tokens`` so
# revocation survives restarts and is visible to every worker. Rows are pruned
# once the token would have expired anyway.


def is_token_revoked(payload: dict) -> bool:
    jti = payload.get('jti')
    if not jti:
        return False
    row = get_db().execute('SELECT 1 FROM revoked_tokens WHERE jti = ?', (jti,)).fetchone()
    return row is not None


def revoke_token(token: str) -> bool:
    """Persist the token's jti as revoked. Returns False for tokens without a jti."""
    payload = decode_token(token, verify_exp=False)
    if not payload or not payload.get('jti'):
        return False
    exp = payload.get('exp')
    expires_at = to_iso(from_timestamp(exp)) if exp else utcnow_iso()
    db = get_db()
    db.execute(
        'INSERT OR IGNORE INTO revoked_tokens (jti, expires_at) VALUES (?, ?)',
        (payload['jti'], expires_at),
    )
    db.execute('DELETE FROM revoked_tokens WHERE expires_at < ?', (utcnow_iso(),))
    db.commit()
    return True


# --- Request context --------------------------------------------------------


def _apply_auth_payload(payload: dict) -> None:
    request.user_id = int(payload.get('user_id', 0))
    request.user_role = payload.get('role', 'user')
    request.user_email = payload.get('email', '')
    request.employer_id = _employer_id_from_payload(payload)


def _clear_auth_payload() -> None:
    request.user_id = None
    request.user_role = None
    request.user_email = None
    request.employer_id = None


def _authenticate_request():
    """Return (payload, error_response) — error_response is (json, status) or None."""
    token = extract_bearer_or_cookie_token(request)
    if not token:
        return None, (jsonify({'error': 'Missing or invalid Authorization header'}), 401)
    payload = decode_token(token)
    if not payload:
        return None, (jsonify({'error': 'Invalid or expired token'}), 401)
    if is_token_revoked(payload):
        return None, (jsonify({'error': 'Token has been revoked'}), 401)
    return payload, None


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        payload, err = _authenticate_request()
        if err:
            return err
        _apply_auth_payload(payload)
        return f(*args, **kwargs)
    return decorated


def require_role(role: str):
    def decorator(f):
        @wraps(f)
        @require_auth
        def decorated(*args, **kwargs):
            if request.user_role != role:
                return jsonify({'error': f'Requires {role} role'}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator


def require_employer(f):
    """Allow employer or admin accounts (for job management APIs)."""

    @wraps(f)
    @require_auth
    def decorated(*args, **kwargs):
        if request.user_role not in ('employer', 'admin'):
            return jsonify({'error': 'Requires employer role'}), 403
        return f(*args, **kwargs)

    return decorated


def optional_auth(f):
    """Attach user context when a valid Bearer token or session cookie is present."""

    @wraps(f)
    def decorated(*args, **kwargs):
        _clear_auth_payload()
        token = extract_bearer_or_cookie_token(request)
        if token:
            payload = decode_token(token)
            if payload and not is_token_revoked(payload):
                _apply_auth_payload(payload)
        return f(*args, **kwargs)

    return decorated
