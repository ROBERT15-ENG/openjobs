"""Password complexity checks (aligned with ekip register rules)."""

import re


def validate_password(password: str) -> str | None:
    """Return an error message if invalid, else None."""
    if not password or len(password) < 8:
        return 'Password must be at least 8 characters'
    if not re.search(r'[A-Z]', password):
        return 'Password must contain at least 1 uppercase letter'
    if not re.search(r'[a-z]', password):
        return 'Password must contain at least 1 lowercase letter'
    if not re.search(r'\d', password):
        return 'Password must contain at least 1 number'
    return None
