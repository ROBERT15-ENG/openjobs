"""
SEEK Australia job search (public jobsearch API).

Respect SEEK Terms of Service in production; rate-limit and cache responses.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import requests

from api.http_safety import is_safe_egress_url

SEEK_SEARCH_URL = "https://www.seek.com.au/api/jobsearch/v5/search"
DEFAULT_SITE_KEY = "AU-Main"

_SESSION = requests.Session()
_SESSION.headers.update(
    {
        "User-Agent": "OpenJobs/1.0 (+https://github.com/ROBERT15-ENG/openjobs; job aggregation)",
        "Accept": "application/json",
    }
)


def _seek_params(
    keywords: str,
    location: str,
    page: int,
    page_size: int,
) -> Dict[str, Any]:
    return {
        "siteKey": DEFAULT_SITE_KEY,
        "keywords": keywords,
        "where": location or "Australia",
        "page": page,
        "pageSize": page_size,
    }


def fetch_seek_page(
    keywords: str,
    location: str = "Australia",
    page: int = 1,
    page_size: int = 22,
    timeout: float = 25.0,
) -> Dict[str, Any]:
    if not is_safe_egress_url(SEEK_SEARCH_URL):
        raise RuntimeError("SEEK URL blocked by egress policy")
    resp = _SESSION.get(
        SEEK_SEARCH_URL,
        params=_seek_params(keywords, location, page, page_size),
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()


def normalize_seek_job(raw: Dict[str, Any]) -> Dict[str, Any]:
    locs = raw.get("locations") or []
    location = ", ".join(
        filter(
            None,
            [
                (locs[0].get("label") if locs else None)
                or (locs[0].get("city") if locs else None)
                or "Australia",
            ],
        )
    )
    work_types = raw.get("workTypes") or []
    work_type = "full_time"
    if work_types:
        first = work_types[0]
        wt = (
            str(first.get("description", ""))
            if isinstance(first, dict)
            else str(first)
        ).lower()
        if "part" in wt:
            work_type = "part_time"
        elif "contract" in wt:
            work_type = "contract"
        elif "casual" in wt:
            work_type = "casual"

    arrangements = raw.get("workArrangements") or []
    arrangement = "on_site"
    for a in arrangements:
        desc = (
            str(a.get("description", "")) if isinstance(a, dict) else str(a)
        ).lower()
        if "remote" in desc:
            arrangement = "remote"
            break
        if "hybrid" in desc:
            arrangement = "hybrid"

    bullets = raw.get("bulletPoints") or []
    teaser = raw.get("teaser") or ""
    description = teaser
    if bullets:
        description = teaser + "\n\n" + "\n".join(f"- {b}" for b in bullets)

    seek_id = raw.get("id")
    url = f"https://www.seek.com.au/job/{seek_id}" if seek_id else ""

    return {
        "title": raw.get("title") or "Untitled role",
        "company": raw.get("companyName") or raw.get("advertiser", {}).get("description", "Unknown"),
        "location": location,
        "description": description,
        "salary": raw.get("salaryLabel") or "",
        "category": "Education & Training",
        "work_type": work_type,
        "work_arrangement": arrangement,
        "skills": "",
        "search_summary": f"seek:{seek_id} {teaser[:200]}".strip(),
        "source": "seek_au",
        "external_id": str(seek_id) if seek_id else "",
        "external_url": url,
        "teaser": teaser,
        "bulletPoints": bullets,
        "classifications": raw.get("classifications") or [],
        "companyName": raw.get("companyName"),
    }


def search_seek(
    keywords: str,
    location: str = "Australia",
    max_pages: int = 3,
    page_size: int = 22,
    pause_seconds: float = 0.4,
) -> List[Dict[str, Any]]:
    """Fetch multiple pages from SEEK; returns normalized job dicts."""
    out: List[Dict[str, Any]] = []
    for page in range(1, max_pages + 1):
        data = fetch_seek_page(keywords, location, page, page_size)
        rows = data.get("data") or []
        if not rows:
            break
        for raw in rows:
            out.append(normalize_seek_job(raw))
        if page < max_pages:
            time.sleep(pause_seconds)
    return out
