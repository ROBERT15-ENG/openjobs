"""Authentication helpers and decorators."""

import datetime
from functools import wraps

import jwt
from constants import JWT_ALGORITHM, JWT_EXPIRY_DAYS
from extensions import BLOCKED_TOKENS
from flask import current_app, jsonify, request
from werkzeug.security import check_password_hash, generate_password_hash


def _employer_id_from_payload(payload: dict):
    """Return employer id only for employer accounts."""
    if payload.get('role') != 'employer':
        return None
    return payload.get('employer_id') or int(payload.get('user_id', 0) or 0)


def hash_password(password: str) -> str:
    return generate_password_hash(password)


def verify_password(password: str, pw_hash: str) -> bool:
    return check_password_hash(pw_hash, password)


def create_token(user) -> str:
    payload = {
        'user_id': user['id'],
        'email': user['email'],
        'role': user['role'],
        'employer_id': user['id'] if user['role'] == 'employer' else None,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=JWT_EXPIRY_DAYS),
        'iat': datetime.datetime.utcnow(),
    }
    token = jwt.encode(payload, current_app.secret_key, algorithm=JWT_ALGORITHM)
    return token if isinstance(token, str) else token.decode('utf-8')


def decode_token(token: str):
    try:
        return jwt.decode(token, current_app.secret_key, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get('Authorization', '')
        if not auth.startswith('Bearer '):
            return jsonify({'error': 'Missing or invalid Authorization header'}), 401
        token = auth.split(' ', 1)[1]
        if token in BLOCKED_TOKENS:
            return jsonify({'error': 'Token has been revoked'}), 401
        payload = decode_token(token)
        if not payload:
            return jsonify({'error': 'Invalid token'}), 401
        exp = payload.get('exp')
        if exp and datetime.datetime.utcfromtimestamp(exp) < datetime.datetime.utcnow():
            return jsonify({'error': 'Token expired'}), 401
        request.user_id = int(payload.get('user_id', 0))
        request.user_role = payload.get('role', 'user')
        request.user_email = payload.get('email', '')
        request.employer_id = _employer_id_from_payload(payload)
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
    """Attach user context when a valid Bearer token is present."""

    @wraps(f)
    def decorated(*args, **kwargs):
        request.user_id = None
        request.user_role = None
        request.user_email = None
        request.employer_id = None

        auth = request.headers.get('Authorization', '')
        if auth.startswith('Bearer '):
            token = auth.split(' ', 1)[1]
            if token not in BLOCKED_TOKENS:
                payload = decode_token(token)
                if payload:
                    exp = payload.get('exp')
                    if not exp or datetime.datetime.utcfromtimestamp(exp) >= datetime.datetime.utcnow():
                        request.user_id = int(payload.get('user_id', 0))
                        request.user_role = payload.get('role', 'user')
                        request.user_email = payload.get('email', '')
                        request.employer_id = _employer_id_from_payload(payload)
        return f(*args, **kwargs)

    return decorated
