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

# Australian states/territories and country markers in SEEK location labels
AU_LOCATION_RE = re.compile(
    r"\b("
    r"NSW|VIC|QLD|WA|SA|TAS|NT|ACT|"
    r"New South Wales|Victoria|Queensland|Western Australia|"
    r"South Australia|Tasmania|Northern Territory|"
    r"Australian Capital Territory|Australia|Australian"
    r")\b",
    re.I,
)

# Overseas placement (common on seek.com.au — AU office, UK/US job)
OVERSEAS_PLACEMENT_RE = re.compile(
    r"\b("
    r"england|united kingdom|\buk\b|wales|scotland|"
    r"teachers?\s*[-–]\s*england|teaching assistants?\s*[-–]\s*uk|"
    r"teach(?:ing)?\s+in\s+(?:the\s+)?uk|"
    r"relocate\s+to\s+(?:the\s+)?uk|"
    r"new zealand|\bnz\b|singapore|dubai|united states|\busa\b"
    r")\b",
    re.I,
)


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


def is_australia_job(job: Dict[str, Any]) -> bool:
    """
    Keep roles based in Australia. Drops overseas-placement ads that still list an AU recruiter city.
    """
    title = str(job.get("title") or "")
    teaser = str(job.get("teaser") or "")
    location = str(job.get("location") or "")

    if OVERSEAS_PLACEMENT_RE.search(title):
        return False
    if OVERSEAS_PLACEMENT_RE.search(teaser):
        return False

    if AU_LOCATION_RE.search(location):
        return True

    blob = _text_blob(job)
    if AU_LOCATION_RE.search(blob):
        return True

    return False


def is_teaching_with_sponsorship(
    job: Dict[str, Any],
    require_sponsorship: bool = True,
    australia_only: bool = True,
) -> bool:
    if not is_teaching_role(job):
        return False
    if australia_only and not is_australia_job(job):
        return False
    if require_sponsorship and not mentions_sponsorship(job):
        return False
    return True
