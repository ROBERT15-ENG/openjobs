"""
Job list cache generation — bump on writes for CDN/browser invalidation (items 49–50).
"""

import os

_generation = 0

try:
    _REDIS_URL = os.environ.get("REDIS_URL")
    if _REDIS_URL:
        import redis

        _redis = redis.from_url(_REDIS_URL, decode_responses=True)
        _redis.ping()
    else:
        _redis = None
except Exception:
    _redis = None

_CACHE_KEY = "openjobs:jobs_list_generation"


def jobs_list_generation() -> int:
    if _redis:
        try:
            return int(_redis.get(_CACHE_KEY) or 0)
        except Exception:
            pass
    return _generation


def bump_jobs_list_cache() -> int:
    global _generation
    if _redis:
        try:
            return int(_redis.incr(_CACHE_KEY))
        except Exception:
            pass
    _generation += 1
    return _generation
