"""Filters for Australian teaching roles that mention visa sponsorship."""

import re
from typing import Any, Dict, List

TEACHING_RE = re.compile(
    r"\b("
    r"teacher|teaching|educator|principal|classroom|lecturer|tutor|"
    r"early\s+childhood|ect\b|education\s+officer|head\s+of\s+school|"
    r"deputy\s+principal|school\s+counsellor|curriculum"
    r")\b",
    re.I,
)

SPONSORSHIP_RE = re.compile(
    r"\b("
    r"visa|sponsor(?:ship)?|482|186|494|187|relocation|work\s+permit|"
    r"international\s+candidate|overseas\s+applicant|migrat"
    r")\b",
    re.I,
)

EDUCATION_CLASSIFICATION = "education & training"


def _text_blob(job: Dict[str, Any]) -> str:
    parts: List[str] = [
        str(job.get("title") or ""),
        str(job.get("company") or job.get("companyName") or ""),
        str(job.get("description") or ""),
        str(job.get("teaser") or ""),
        str(job.get("search_summary") or ""),
    ]
    bullets = job.get("bulletPoints") or []
    if isinstance(bullets, list):
        parts.extend(str(b) for b in bullets)
    classifications = job.get("classifications") or []
    for c in classifications:
        if isinstance(c, dict):
            cl = c.get("classification") or {}
            sub = c.get("subclassification") or {}
            parts.append(str(cl.get("description", "")))
            parts.append(str(sub.get("description", "")))
    return " ".join(parts)


def is_teaching_role(job: Dict[str, Any]) -> bool:
    blob = _text_blob(job)
    if TEACHING_RE.search(blob):
        return True
    blob_lower = blob.lower()
    return EDUCATION_CLASSIFICATION in blob_lower


def mentions_sponsorship(job: Dict[str, Any]) -> bool:
    return bool(SPONSORSHIP_RE.search(_text_blob(job)))


def is_teaching_with_sponsorship(job: Dict[str, Any], require_sponsorship: bool = True) -> bool:
    if not is_teaching_role(job):
        return False
    if require_sponsorship and not mentions_sponsorship(job):
        return False
    return True
