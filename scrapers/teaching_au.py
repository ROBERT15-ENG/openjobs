"""
Australian teaching jobs with visa sponsorship — SEEK-backed aggregator.
"""

from __future__ import annotations

from typing import Any, Dict, List

from scrapers.sources.seek_au import search_seek
from scrapers.teaching_filters import is_teaching_with_sponsorship

# Queries tuned for AU education + migration-friendly wording on SEEK
DEFAULT_QUERIES = [
    "teacher visa sponsorship",
    "education visa sponsorship",
    "teacher 482 visa",
    "early childhood teacher sponsorship",
    "secondary teacher visa Australia",
]


def fetch_teaching_sponsorship_jobs(
    location: str = "Australia",
    max_pages_per_query: int = 2,
    require_sponsorship: bool = True,
    extra_query: str | None = None,
) -> List[Dict[str, Any]]:
    queries = list(DEFAULT_QUERIES)
    if extra_query:
        queries.insert(0, extra_query.strip())

    seen: set[str] = set()
    matched: List[Dict[str, Any]] = []

    for q in queries:
        try:
            batch = search_seek(q, location=location, max_pages=max_pages_per_query)
        except Exception:
            continue
        for job in batch:
            ext = job.get("external_id") or ""
            if ext and ext in seen:
                continue
            if is_teaching_with_sponsorship(job, require_sponsorship=require_sponsorship):
                job["scrape_query"] = q
                matched.append(job)
                if ext:
                    seen.add(ext)
    return matched
