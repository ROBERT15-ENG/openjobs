"""
Privacy and prompt-injection guards for the OpenJobs chatbot.
"""

import os
import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

MAX_MESSAGE_LEN = int(os.environ.get("CHATBOT_MAX_MESSAGE_LEN", "500"))
MAX_HISTORY_TURNS = int(os.environ.get("CHATBOT_MAX_HISTORY_TURNS", "6"))
MAX_HISTORY_ITEM_LEN = int(os.environ.get("CHATBOT_MAX_HISTORY_ITEM_LEN", "400"))
MAX_SEARCH_LEN = 80
MAX_LOCATION_LEN = 48

# Substrings / patterns commonly used in prompt-injection or automated abuse
_INJECTION_PATTERNS = [
    re.compile(p, re.I)
    for p in [
        r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?|rules?)",
        r"disregard\s+(your\s+)?(instructions?|rules?|guidelines?)",
        r"you\s+are\s+now\s+(a|an)\s+",
        r"new\s+instructions?\s*:",
        r"system\s*prompt",
        r"reveal\s+(the\s+)?(secret|api\s*key|password|token|prompt)",
        r"print\s+(your\s+)?(instructions?|prompt)",
        r"<\s*script",
        r"javascript\s*:",
        r"\[INST\]",
        r"<\|im_start\|>",
        r"###\s*system",
        r"developer\s+mode",
        r"jailbreak",
        r"do\s+anything\s+now",
        r"repeat\s+(the\s+)?(above|system)\s+verbatim",
        r"output\s+everything\s+in\s+your\s+context",
    ]
]

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?(?:\(\d{2,4}\)[-.\s]?)?\d{3,4}[-.\s]?\d{3,4}\b")
_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def _normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    text = _CONTROL_CHARS.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def detect_injection(text: str) -> bool:
    if not text:
        return False
    for pat in _INJECTION_PATTERNS:
        if pat.search(text):
            return True
    # Excessive role-play delimiters
    if text.count("```") > 4 or text.count("---") > 6:
        return True
    return False


def redact_pii(text: str) -> str:
    text = _EMAIL_RE.sub("[email redacted]", text)
    text = _PHONE_RE.sub("[phone redacted]", text)
    return text


def escape_sql_like(value: str) -> str:
    """Escape % and _ for SQLite LIKE patterns."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def sanitize_user_message(raw: str) -> Tuple[str, Optional[str]]:
    """
    Returns (sanitized_message, block_reason).
    block_reason set → refuse request with generic reply (no LLM / no search).
    """
    text = _normalize_text(raw)
    if not text:
        return "", "empty"
    if len(text) > MAX_MESSAGE_LEN:
        text = text[:MAX_MESSAGE_LEN]

    if detect_injection(text):
        return text, "injection"

    return text, None


def sanitize_history(raw_history: Any) -> List[Dict[str, str]]:
    if not isinstance(raw_history, list):
        return []
    cleaned: List[Dict[str, str]] = []
    for item in raw_history[-MAX_HISTORY_TURNS:]:
        if not isinstance(item, dict):
            continue
        role = item.get("role")
        if role not in ("user", "assistant"):
            continue
        content = _normalize_text(str(item.get("content", "")))[:MAX_HISTORY_ITEM_LEN]
        if not content:
            continue
        if detect_injection(content):
            continue
        cleaned.append({"role": role, "content": redact_pii(content)})
    return cleaned


def clamp_search_terms(search: str, location: str) -> Tuple[str, str]:
    search = _normalize_text(search)[:MAX_SEARCH_LEN]
    location = _normalize_text(location)[:MAX_LOCATION_LEN]
    if detect_injection(search) or detect_injection(location):
        return "", ""
    return search, location


def client_may_use_ai(request_headers: Dict[str, str]) -> bool:
    """
    AI enrichment is off by default for public callers.
    Enabled only when CHATBOT_AI_ENABLED=true and caller presents CHATBOT_INTERNAL_SECRET.
    """
    if os.environ.get("CHATBOT_AI_ENABLED", "false").lower() not in ("1", "true", "yes"):
        return False
    secret = os.environ.get("CHATBOT_INTERNAL_SECRET", "").strip()
    if not secret:
        return False
    provided = (request_headers.get("X-Chatbot-Secret") or "").strip()
    return provided == secret


def safe_refusal_reply() -> Dict[str, Any]:
    return {
        "reply": (
            "I can only help with job search on OpenJobs — roles, locations, remote work, "
            "and how to apply. Try something like “remote developer in Brisbane”."
        ),
        "jobs": [],
        "suggestions": ["Remote jobs", "Visa sponsorship", "Help"],
        "blocked": True,
    }
