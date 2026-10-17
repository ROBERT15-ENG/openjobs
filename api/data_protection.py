"""
User / client data protection — field filtering, masking, export, and erasure helpers.
"""

import os
import re
from typing import Any, Dict, Iterable, List, Optional

# Never expose these keys in API JSON (even to the owning user via generic dict()).
STRIP_ALWAYS = frozenset(
    {
        "password_hash",
        "confirm_token",
        "confirm_expires",
        "reset_token",
        "reset_expires",
        "google_id",
    }
)

# Resume / KYC: only via explicit endpoints with auth checks.
SENSITIVE_CONTENT_KEYS = frozenset(
    {
        "resume_text",
        "cover_letter",
        "file_path",
        "doc_number",
        "kyc_doc_number",
    }
)

USER_SELF_ALLOWED = frozenset(
    {
        "id",
        "name",
        "email",
        "role",
        "skills",
        "phone",
        "company",
        "preferred_location",
        "experience",
        "created_at",
        "kyc_status",
        "email_confirmed",
        "employer_id",
    }
)


def mask_email(email: str) -> str:
    if not email or "@" not in email:
        return "***"
    local, domain = email.rsplit("@", 1)
    if len(local) <= 1:
        shown = "*"
    else:
        shown = local[0] + "***"
    return f"{shown}@{domain}"


def should_mask_admin_pii() -> bool:
    if os.environ.get("ADMIN_MASK_PII", "").lower() in ("0", "false", "no"):
        return False
    if os.environ.get("FLASK_ENV") == "production":
        return True
    return os.environ.get("ADMIN_MASK_PII", "true").lower() in ("1", "true", "yes")


def scrub_row(row: Dict[str, Any], *, drop: Optional[Iterable[str]] = None) -> Dict[str, Any]:
    out = dict(row)
    for key in STRIP_ALWAYS:
        out.pop(key, None)
    if drop:
        for key in drop:
            out.pop(key, None)
    return out


def public_user(
    row: Dict[str, Any],
    *,
    for_self: bool = False,
    include_resume: bool = False,
) -> Dict[str, Any]:
    data = scrub_row(row)
    if not for_self:
        for key in list(data.keys()):
            if key not in ("id", "name", "role", "company", "skills", "preferred_location"):
                data.pop(key, None)
        data.pop("email", None)
        data.pop("phone", None)
    else:
        data = {k: v for k, v in data.items() if k in USER_SELF_ALLOWED or k in data and k not in STRIP_ALWAYS}
    if not include_resume:
        for key in SENSITIVE_CONTENT_KEYS:
            data.pop(key, None)
    return data


def public_application(
    row: Dict[str, Any],
    *,
    viewer_role: str,
    viewer_id: int,
    employer_id: Optional[int] = None,
) -> Dict[str, Any]:
    """Employers see applicant PII for their jobs; seekers see own; admin sees all."""
    data = scrub_row(row)
    app_user_id = data.get("user_id")
    is_owner = app_user_id == viewer_id
    is_hiring_employer = viewer_role == "employer" and employer_id is not None
    is_admin = viewer_role == "admin"

    if not (is_owner or is_hiring_employer or is_admin):
        return {"error": "forbidden"}

    if viewer_role == "employer" and not is_hiring_employer:
        return {"error": "forbidden"}

    # Seekers see their own application content; employers/admins see applicant materials.
    if is_owner or is_hiring_employer or is_admin:
        return data

    for key in SENSITIVE_CONTENT_KEYS:
        data.pop(key, None)
    return data


def admin_recent_user(row: Dict[str, Any]) -> Dict[str, Any]:
    data = scrub_row(row)
    if should_mask_admin_pii() and data.get("email"):
        data["email"] = mask_email(data["email"])
    if should_mask_admin_pii() and data.get("seeker_email"):
        data["seeker_email"] = mask_email(data["seeker_email"])
    return data


def safe_log_message(text: str, max_len: int = 200) -> str:
    """Redact emails/phones before writing to logs."""
    if not text:
        return ""
    t = str(text)[:max_len]
    t = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "[email]", t)
    t = re.sub(
        r"\b(?:\+?\d{1,3}[-.\s]?)?(?:\(\d{2,4}\)[-.\s]?)?\d{3,4}[-.\s]?\d{3,4}\b",
        "[phone]",
        t,
    )
    return t
