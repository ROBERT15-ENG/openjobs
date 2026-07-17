"""Shared Flask extensions."""

from flask import request
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


def rate_limit_key():
    """Prefer authenticated user id; fall back to client IP."""
    user_id = getattr(request, 'user_id', None)
    if user_id:
        return f'user:{user_id}'
    return get_remote_address()


def ai_rate_limit_key():
    """AI routes must be identity-based (auth required before limit check)."""
    user_id = getattr(request, 'user_id', None)
    if user_id:
        return f'ai:user:{user_id}'
    # Should not hit for @require_auth routes; keep IP as safety net.
    return f'ai:ip:{get_remote_address()}'


limiter = Limiter(
    key_func=rate_limit_key,
    default_limits=['500 per day', '100 per hour', '20 per minute'],
    storage_uri='memory://',
)

BLOCKED_TOKENS: set[str] = set()
