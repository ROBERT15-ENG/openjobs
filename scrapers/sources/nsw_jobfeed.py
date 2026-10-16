"""
NSW Department of Education JobFeed — official weekly teaching vacancies.

Source: https://education.nsw.gov.au/teach-nsw/find-teaching-jobs/jobfeed
Not SEEK; includes feed-as-of date for freshness checks.
"""

from __future__ import annotations

import hashlib
import re
from html import unescape
from typing import Any, Dict, List, Optional, Tuple

import requests

from api.http_safety import is_safe_egress_url

JOBFEED_URL = "https://education.nsw.gov.au/teach-nsw/find-teaching-jobs/jobfeed"

_SESSION = requests.Session()
_SESSION.headers.update(
    {
        "User-Agent": "OpenJobs/1.0 (+https://github.com/ROBERT15-ENG/openjobs)",
        "Accept": "text/html,application/xhtml+xml",
    }
)

ROLE_PREFIX = re.compile(
    r"(?:Executive Principal [A-Z]|Assistant Principal [A-Z]|Head Teacher [A-Z]|"
    r"School Counsellor(?:\s+\(| [A-Z])|Teacher [A-Z])"
)

AS_AT_RE = re.compile(
    r"Current as at\s+(\d{1,2}\s+[A-Za-z]+\s+\d{4})",
    re.I,
)

CLOSE_DATE_RE = re.compile(
    r"Applications close on\s+([^.<]+?)(?:,|\.)",
    re.I,
)


def _strip_html(html: str) -> str:
    html = re.sub(r"<script[^>]*>[\s\S]*?</script>", " ", html, flags=re.I)
    html = re.sub(r"<style[^>]*>[\s\S]*?</style>", " ", html, flags=re.I)
    # Prefer main article if present
    m = re.search(r"<main[^>]*>([\s\S]*?)</main>", html, flags=re.I)
    if m:
        html = m.group(1)
    text = re.sub(r"<[^>]+>", " ", html)
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _parse_feed_meta(text: str) -> Tuple[Optional[str], Optional[str]]:
    as_at = None
    m = AS_AT_RE.search(text)
    if m:
        as_at = m.group(1).strip()
    close = None
    m2 = CLOSE_DATE_RE.search(text)
    if m2:
        close = m2.group(1).strip()
    return as_at, close


def _split_vacancies(text: str) -> List[str]:
    """Split JobFeed plain text into vacancy chunks."""
    idxs = [m.start() for m in ROLE_PREFIX.finditer(text)]
    if not idxs:
        return []
    chunks: List[str] = []
    for i, start in enumerate(idxs):
        end = idxs[i + 1] if i + 1 < len(idxs) else len(text)
        chunk = text[start:end].strip()
        if len(chunk) > 40:
            chunks.append(chunk)
    return chunks


def _title_from_chunk(chunk: str) -> str:
    m = re.match(
        r"((?:Executive Principal|Assistant Principal|Head Teacher|School Counsellor|Teacher)"
        r"[^.]{0,120}?)(?:\s+Years\b|\.)",
        chunk,
        re.I,
    )
    if m:
        return m.group(1).strip()
    end = chunk.find(" Years ")
    return chunk[: end if end > 0 else 100].strip()


def _location_from_chunk(chunk: str) -> str:
    m = re.search(
        r"(?:Teacher|Principal|Counsellor)\s+([A-Za-z0-9' \-\.]+(?:School|College|Campus))",
        chunk,
    )
    if m:
        return m.group(1).strip()
    return "NSW, Australia"


def fetch_jobfeed_html(timeout: float = 30.0) -> str:
    if not is_safe_egress_url(JOBFEED_URL):
        raise RuntimeError("NSW JobFeed URL blocked by egress policy")
    resp = _SESSION.get(JOBFEED_URL, timeout=timeout)
    resp.raise_for_status()
    return resp.text


def search_nsw_jobfeed(
    require_mobility_or_sponsor: bool = False,
) -> Dict[str, Any]:
    """
    Returns dict with feed_as_at, applications_close, jobs list (normalized).
    """
    html = fetch_jobfeed_html()
    text = _strip_html(html)
    feed_as_at, applications_close = _parse_feed_meta(text)

    jobs: List[Dict[str, Any]] = []
    for chunk in _split_vacancies(text):
        title = _title_from_chunk(chunk)
        location = _location_from_chunk(chunk)
        ext_id = hashlib.sha256(chunk[:500].encode("utf-8")).hexdigest()[:16]
        job = {
            "title": title,
            "company": "NSW Department of Education",
            "location": f"{location}, NSW",
            "description": chunk[:4000],
            "salary": "",
            "category": "Education & Training",
            "work_type": "full_time",
            "work_arrangement": "on_site",
            "skills": "",
            "search_summary": f"nsw_jobfeed:{ext_id} as_at={feed_as_at or 'unknown'}",
            "source": "nsw_jobfeed",
            "external_id": ext_id,
            "external_url": JOBFEED_URL,
            "feed_as_at": feed_as_at,
            "applications_close": applications_close,
            "teaser": chunk[:300],
        }
        if require_mobility_or_sponsor:
            from scrapers.mobility_language import classify_mobility_text

            tags = classify_mobility_text(chunk)
            if not tags:
                continue
            job["mobility_tags"] = tags
        jobs.append(job)

    return {
        "feed_as_at": feed_as_at,
        "applications_close": applications_close,
        "jobs": jobs,
    }
