"""Shared Flask-Limiter instance for server and blueprints."""

import os

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

REDIS_URL = os.environ.get('REDIS_URL')
limiter = Limiter(
    app=None,
    key_func=get_remote_address,
    default_limits=['500 per day', '100 per hour', '20 per minute'],
    storage_uri=REDIS_URL or 'memory://',
)
