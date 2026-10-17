"""
SEEK Australia — run teaching / mobility queries in every state and territory.
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from scrapers.au_states import AU_STATES, infer_state_code
from scrapers.mobility_language import mobility_tags_for_job
from scrapers.sources.seek_au import search_seek
from scrapers.teaching_filters import is_teaching_role, is_australia_job

MOBILITY_QUERIES = [
    "teacher visa sponsorship",
    "education visa sponsorship",
    "early childhood teacher sponsorship",
    "teacher relocation support",
    "teacher 482 visa",
]


def search_all_states(
    queries: Optional[List[str]] = None,
    max_pages_per_query: int = 1,
    page_size: int = 22,
    require_mobility_language: bool = True,
    teaching_only: bool = True,
    pause_seconds: float = 0.35,
) -> List[Dict[str, Any]]:
    queries = queries or MOBILITY_QUERIES
    seen: set[str] = set()
    out: List[Dict[str, Any]] = []

    for state_code, where, _name in AU_STATES:
        for q in queries:
            try:
                batch = search_seek(q, location=where, max_pages=max_pages_per_query, page_size=page_size)
            except Exception:
                continue
            for job in batch:
                ext = job.get("external_id") or ""
                if ext and ext in seen:
                    continue
                if not is_australia_job(job):
                    continue
                if teaching_only and not is_teaching_role(job):
                    continue
                tags = mobility_tags_for_job(job)
                if require_mobility_language and not tags:
                    continue
                job["state_code"] = infer_state_code(job.get("location") or "") or state_code
                job["scrape_query"] = q
                job["scrape_state_scope"] = state_code
                job["mobility_tags"] = tags
                job["source"] = "seek_au"
                out.append(job)
                if ext:
                    seen.add(ext)
            time.sleep(pause_seconds)
    return out
