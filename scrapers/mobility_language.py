"""
Australian teaching roles: visa sponsorship and equivalent wording.

Employers rarely use one phrase; this module classifies common variants.
"""

import re
from typing import Any, Dict, List, Tuple

# Explicit visa / employer sponsorship language
VISA_SPONSOR_RE = re.compile(
    r"\b("
    r"visa\s+sponsor(?:ship)?|sponsor(?:ship)?\s+(?:available|provided|offered)?|"
    r"employer\s+sponsor(?:ship)?|nomination|"
    r"subclass\s*(?:482|186|494|187)|\b482\b|\b186\b|\b494\b|"
    r"tss\b|temporary\s+skill\s+shortage|skilled\s+visa|"
    r"work\s+permit|right\s+to\s+work|work\s+rights|"
    r"international(?:ly)?\s+(?:qualified|trained)?\s*teacher|"
    r"overseas\s+(?:trained|qualified)|migrat(?:e|ion)\s+to\s+australia|"
    r"eligible\s+for\s+sponsor"
    r")\b",
    re.I,
)

# Government / rural incentives (often the only “sponsorship-like” offer for public schools)
RELOCATION_INCENTIVE_RE = re.compile(
    r"\b("
    r"relocation\s+support|relocation\s+assistance|relocation\s+package|"
    r"recruitment\s+bonus|sign[- ]on\s+bonus|"
    r"benefits\s+and\s+incentives|"
    r"international\s+recruitment|"
    r"overseas\s+applicant|overseas\s+candidate"
    r")\b",
    re.I,
)

# DAMA / regional programs
REGIONAL_PROGRAM_RE = re.compile(
    r"\b(DAMA|designated\s+area\s+migration|regional\s+visa)\b",
    re.I,
)


def classify_mobility_text(text: str) -> List[str]:
    """Return human-readable tags for matched mobility language."""
    if not text:
        return []
    tags: List[str] = []
    if VISA_SPONSOR_RE.search(text):
        tags.append("visa_or_sponsor")
    if RELOCATION_INCENTIVE_RE.search(text):
        tags.append("relocation_or_incentive")
    if REGIONAL_PROGRAM_RE.search(text):
        tags.append("regional_program")
    return tags


def mobility_tags_for_job(job: Dict[str, Any]) -> List[str]:
    blob = " ".join(
        str(job.get(k) or "")
        for k in ("title", "description", "teaser", "company", "location", "search_summary")
    )
    return classify_mobility_text(blob)


def has_mobility_language(job: Dict[str, Any]) -> bool:
    return bool(mobility_tags_for_job(job))


def mobility_snippet(text: str, max_len: int = 120) -> str:
    """Short excerpt around first mobility keyword match."""
    for pattern in (VISA_SPONSOR_RE, RELOCATION_INCENTIVE_RE, REGIONAL_PROGRAM_RE):
        m = pattern.search(text or "")
        if m:
            start = max(0, m.start() - 40)
            end = min(len(text), m.end() + 40)
            snippet = text[start:end].strip()
            if len(snippet) > max_len:
                snippet = snippet[: max_len - 3] + "..."
            return snippet
    return ""
