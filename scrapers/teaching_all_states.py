"""
All Australian states: official NSW feed + per-state market search (SEEK).
"""

from __future__ import annotations

from typing import Any, Dict, List

from scrapers.au_states import infer_state_code
from scrapers.sources.nsw_jobfeed import search_nsw_jobfeed
from scrapers.sources.seek_au_by_state import search_all_states
from scrapers.mobility_language import mobility_tags_for_job


def fetch_teaching_mobility_all_states(
    include_nsw_jobfeed: bool = True,
    include_seek_by_state: bool = True,
    require_mobility_language: bool = True,
    max_pages_per_query: int = 1,
) -> Dict[str, Any]:
    """
    Returns { jobs, by_state, meta } for all states/territories.
    """
    seen: set[str] = set()
    jobs: List[Dict[str, Any]] = []
    meta: Dict[str, Any] = {}

    if include_nsw_jobfeed:
        feed = search_nsw_jobfeed(require_mobility_or_sponsor=require_mobility_language)
        meta["nsw_feed_as_at"] = feed.get("feed_as_at")
        meta["nsw_applications_close"] = feed.get("applications_close")
        for job in feed.get("jobs") or []:
            ext = job.get("external_id") or ""
            if ext and ext in seen:
                continue
            job["state_code"] = "NSW"
            job["source"] = "nsw_jobfeed"
            if not job.get("mobility_tags"):
                job["mobility_tags"] = mobility_tags_for_job(job)
            jobs.append(job)
            if ext:
                seen.add(f"nsw:{ext}")

    if include_seek_by_state:
        seek_jobs = search_all_states(
            max_pages_per_query=max_pages_per_query,
            require_mobility_language=require_mobility_language,
        )
        meta["seek_states_queried"] = 8
        for job in seek_jobs:
            ext = job.get("external_id") or ""
            key = f"seek:{ext}"
            if ext and key in seen:
                continue
            if not job.get("state_code"):
                job["state_code"] = infer_state_code(job.get("location", ""))
            jobs.append(job)
            if ext:
                seen.add(key)

    by_state: Dict[str, List[Dict[str, Any]]] = {}
    for job in jobs:
        code = job.get("state_code") or "AU"
        by_state.setdefault(code, []).append(job)

    return {"jobs": jobs, "by_state": by_state, "meta": meta}
