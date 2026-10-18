"""
Feature flags — env-driven (P2). See notes/ENGINEERING_ROADMAP.md.
"""

import os


def _truthy(val: str) -> bool:
    return (val or "").strip().lower() in ("1", "true", "yes", "on")


def feature_enabled(name: str, default: bool = False) -> bool:
    key = f"FEATURE_{name.upper()}"
    raw = os.environ.get(key)
    if raw is None:
        return default
    return _truthy(raw)


def all_flags() -> dict:
    return {
        "ADS": feature_enabled("ADS", default=True),
        "CHATBOT": feature_enabled("CHATBOT", default=True),
        "CHATBOT_AI": feature_enabled("CHATBOT_AI", default=False),
        "OLLAMA_MATCHING": feature_enabled("OLLAMA_MATCHING", default=True),
        "GUEST_JOB_CACHE": feature_enabled("GUEST_JOB_CACHE", default=True),
    }
