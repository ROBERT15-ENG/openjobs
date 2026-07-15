"""HttpOnly session cookie helpers (ekip oj_session pattern)."""

import os

from constants import JWT_EXPIRY_DAYS

SESSION_COOKIE = 'oj_session'
SESSION_MAX_AGE = 60 * 60 * 24 * JWT_EXPIRY_DAYS


def session_cookie_kwargs() -> dict:
    secure = os.environ.get('FLASK_ENV') == 'production' or os.environ.get('SESSION_COOKIE_SECURE', '').lower() in (
        '1', 'true', 'yes',
    )
    return {
        'httponly': True,
        'samesite': 'Lax',
        'secure': secure,
        'path': '/',
        'max_age': SESSION_MAX_AGE,
    }


def set_session_cookie(response, token: str):
    response.set_cookie(SESSION_COOKIE, token, **session_cookie_kwargs())
    return response


def clear_session_cookie(response):
    kwargs = session_cookie_kwargs()
    kwargs['max_age'] = 0
    response.set_cookie(SESSION_COOKIE, '', **kwargs)
    return response


def extract_bearer_or_cookie_token(request) -> str | None:
    auth = request.headers.get('Authorization', '')
    if auth.startswith('Bearer '):
        token = auth.split(' ', 1)[1].strip()
        if token:
            return token
    cookie = request.cookies.get(SESSION_COOKIE, '').strip()
    return cookie or None
