"""
All-occupation Australian jobs with visa/sponsorship language, filtered to skilled list matches.
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

from scrapers.au_states import AU_STATES, infer_state_code
from scrapers.mobility_language import mobility_tags_for_job
from scrapers.occupation_demand import annotate_job_occupation, match_occupation, occupation_list_version
from scrapers.sources.seek_au import search_seek
from scrapers.teaching_filters import is_australia_job, mentions_sponsorship

GENERAL_VISA_QUERIES = [
    "visa sponsorship Australia",
    "employer sponsorship 482",
    "skilled visa sponsorship",
    "relocation visa sponsorship",
    "TSS visa sponsorship",
    "international candidate sponsorship",
]

# High-volume in-demand titles (extra SEEK passes; still require list match on ad text)
OCCUPATION_SEEK_QUERIES = [
    "registered nurse visa sponsorship",
    "software engineer visa sponsorship",
    "electrician visa sponsorship",
    "chef visa sponsorship",
    "civil engineer visa sponsorship",
    "accountant visa sponsorship",
    "data scientist visa sponsorship",
    "physiotherapist visa sponsorship",
    "secondary teacher visa sponsorship",
    "mechanical engineer visa sponsorship",
]


def _passes_filters(
    job: Dict[str, Any],
    *,
    require_sponsorship: bool,
    australia_only: bool,
    require_occupation_on_demand: bool,
    min_occupation_score: int,
) -> bool:
    if australia_only and not is_australia_job(job):
        return False
    if require_sponsorship and not mentions_sponsorship(job):
        tags = mobility_tags_for_job(job)
        if not tags:
            return False
    if require_occupation_on_demand:
        occ = match_occupation(job, min_score=min_occupation_score)
        if not occ:
            return False
        annotate_job_occupation(job, occ)
    return True


def fetch_visa_sponsorship_jobs(
    location: str = "Australia",
    max_pages_per_query: int = 1,
    page_size: int = 22,
    require_sponsorship: bool = True,
    australia_only: bool = True,
    require_occupation_on_demand: bool = True,
    min_occupation_score: int = 3,
    extra_queries: Optional[List[str]] = None,
    pause_seconds: float = 0.35,
) -> List[Dict[str, Any]]:
    """
    SEEK scan across all states/territories with general + occupation-tilted queries.
    Jobs must mention sponsorship/mobility and match data/au_skilled_occupations.json when
    require_occupation_on_demand is True (default).
    """
    queries: List[str] = list(GENERAL_VISA_QUERIES) + list(OCCUPATION_SEEK_QUERIES)
    if extra_queries:
        queries = extra_queries + queries
    if os.environ.get("SCRAPER_VISA_EXTRA_QUERIES"):
        queries.extend(
            q.strip()
            for q in os.environ["SCRAPER_VISA_EXTRA_QUERIES"].split(",")
            if q.strip()
        )

    seen: set[str] = set()
    out: List[Dict[str, Any]] = []

    for state_code, where, _name in AU_STATES:
        for q in queries:
            try:
                batch = search_seek(
                    q,
                    location=where,
                    max_pages=max_pages_per_query,
                    page_size=page_size,
                )
            except Exception:
                continue
            for job in batch:
                ext = job.get("external_id") or ""
                if ext and ext in seen:
                    continue
                job["state_code"] = infer_state_code(job.get("location") or "") or state_code
                job["scrape_query"] = q
                job["scrape_state_scope"] = state_code
                job["mobility_tags"] = mobility_tags_for_job(job)
                job["source"] = "seek_au"
                job["occupation_list_version"] = occupation_list_version()
                if not _passes_filters(
                    job,
                    require_sponsorship=require_sponsorship,
                    australia_only=australia_only,
                    require_occupation_on_demand=require_occupation_on_demand,
                    min_occupation_score=min_occupation_score,
                ):
                    continue
                out.append(job)
                if ext:
                    seen.add(ext)
            time.sleep(pause_seconds)

    # National pass (broader location string)
    for q in queries[: len(GENERAL_VISA_QUERIES)]:
        try:
            batch = search_seek(
                q,
                location=location or "Australia",
                max_pages=max_pages_per_query,
                page_size=page_size,
            )
        except Exception:
            continue
        for job in batch:
            ext = job.get("external_id") or ""
            if ext and ext in seen:
                continue
            job["scrape_query"] = q
            job["mobility_tags"] = mobility_tags_for_job(job)
            job["source"] = "seek_au"
            job["occupation_list_version"] = occupation_list_version()
            if not _passes_filters(
                job,
                require_sponsorship=require_sponsorship,
                australia_only=australia_only,
                require_occupation_on_demand=require_occupation_on_demand,
                min_occupation_score=min_occupation_score,
            ):
                continue
            out.append(job)
            if ext:
                seen.add(ext)
        time.sleep(pause_seconds)

    return out
