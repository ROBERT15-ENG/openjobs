"""
Auth helpers and production safety checks.
"""

import os
from functools import wraps

import jwt
from flask import jsonify, request

_INSECURE_JWT_DEFAULTS = {
    "dev_secret_do_not_use_in_production",
    "dev_secret_key_change_in_production",
}


def enforce_production_secrets():
    """Refuse to boot in production with default secrets (P1)."""
    if os.environ.get("FLASK_ENV") != "production":
        return
    jwt = os.environ.get("JWT_SECRET") or os.environ.get("SECRET_KEY") or ""
    if not jwt or jwt in _INSECURE_JWT_DEFAULTS or len(jwt) < 32:
        raise RuntimeError(
            "Production requires JWT_SECRET (or SECRET_KEY) of at least 32 random characters."
        )


def _jwt_secret() -> str:
    return (
        os.environ.get("JWT_SECRET")
        or os.environ.get("SECRET_KEY")
        or "dev_secret_do_not_use_in_production"
    )


def require_auth(f):
    """JWT bearer auth for API routes (used by scraper blueprint and others)."""

    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return jsonify({"error": "Missing or invalid Authorization header"}), 401
        token = auth.split(" ", 1)[1]
        try:
            payload = jwt.decode(token, _jwt_secret(), algorithms=["HS256"])
        except jwt.PyJWTError:
            return jsonify({"error": "Invalid or expired token"}), 401
        request.user_id = int(payload.get("user_id", 0))
        request.user_role = payload.get("role", "user")
        request.user_email = payload.get("email", "")
        request.employer_id = payload.get("employer_id") or payload.get("user_id")
        return f(*args, **kwargs)

    return decorated


def require_admin(f):
    """Must run after require_auth (sets request.user_role)."""

    @wraps(f)
    def wrapped(*args, **kwargs):
        if getattr(request, "user_role", None) != "admin":
            return jsonify({"error": "Admin access required"}), 403
        return f(*args, **kwargs)

    return wrapped


def allowed_registration_role(role: str) -> str:
    """Prevent privilege escalation at signup."""
    role = (role or "user").strip().lower()
    if role in ("user", "seeker"):
        return "user"
    if role == "employer":
        return "employer"
    return "user"
