"""
Australian teaching jobs — government career sources first (not SEEK by default).
"""

from __future__ import annotations

import os
from typing import Any, Dict, List

from scrapers.sources.nsw_jobfeed import search_nsw_jobfeed
from scrapers.sources import seek_au
from scrapers.sources.seek_au_by_state import search_all_states
from scrapers.teaching_filters import is_teaching_with_sponsorship

ALLOW_SEEK = os.environ.get("SCRAPER_ALLOW_SEEK", "").lower() in ("1", "true", "yes")

SEEK_QUERIES = [
    "teacher visa sponsorship Australia",
    "education visa sponsorship Australia",
]


def fetch_teaching_sponsorship_jobs(
    location: str = "Australia",
    max_pages_per_query: int = 2,
    require_sponsorship: bool = True,
    australia_only: bool = True,
    extra_query: str | None = None,
    sources: List[str] | None = None,
) -> List[Dict[str, Any]]:
    """
    Default sources: NSW JobFeed (official, dated weekly feed).
    SEEK is opt-in via sources=['seek'] or SCRAPER_ALLOW_SEEK=true.
    """
    if sources is None:
        # All states: NSW official feed + SEEK scoped per state/territory
        sources = ["nsw_jobfeed", "seek_all_states"]
        if ALLOW_SEEK and "seek_all_states" not in sources:
            sources.append("seek")

    seen: set[str] = set()
    matched: List[Dict[str, Any]] = []

    if "nsw_jobfeed" in sources:
        feed = search_nsw_jobfeed(
            require_mobility_or_sponsor=require_sponsorship,
        )
        for job in feed.get("jobs") or []:
            ext = job.get("external_id") or ""
            if ext and ext in seen:
                continue
            job["scrape_query"] = "nsw_jobfeed"
            job["source_feed_as_at"] = feed.get("feed_as_at")
            matched.append(job)
            if ext:
                seen.add(ext)

    if "seek_all_states" in sources:
        try:
            batch = search_all_states(
                max_pages_per_query=max_pages_per_query,
                require_mobility_language=require_sponsorship,
            )
        except Exception:
            batch = []
        for job in batch:
            ext = job.get("external_id") or ""
            if ext and ext in seen:
                continue
            matched.append(job)
            if ext:
                seen.add(ext)

    if "seek" in sources:
        queries = list(SEEK_QUERIES)
        if extra_query:
            queries.insert(0, extra_query.strip())
        for q in queries:
            try:
                batch = seek_au.search_seek(q, location=location, max_pages=max_pages_per_query)
            except Exception:
                continue
            for job in batch:
                ext = job.get("external_id") or ""
                if ext and ext in seen:
                    continue
                if is_teaching_with_sponsorship(
                    job,
                    require_sponsorship=require_sponsorship,
                    australia_only=australia_only,
                ):
                    job["scrape_query"] = q
                    matched.append(job)
                    if ext:
                        seen.add(ext)

    return matched
