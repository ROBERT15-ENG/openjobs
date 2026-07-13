"""Shared Flask extensions."""

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=['500 per day', '100 per hour', '20 per minute'],
    storage_uri='memory://',
)

BLOCKED_TOKENS: set[str] = set()
