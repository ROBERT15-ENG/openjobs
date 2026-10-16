"""
Scrape scheduler — single-flight jobs for API triggers.
"""

from __future__ import annotations

import threading
import time
from typing import Any, Dict, Optional

from scrapers.db_insert import insert_jobs
from scrapers.sources import linkedin_au, seek_au
from scrapers.teaching_au import fetch_teaching_sponsorship_jobs
from scrapers.teaching_filters import is_teaching_with_sponsorship

_lock = threading.Lock()
_status: Dict[str, Any] = {
    "state": "idle",
    "last_result": None,
    "last_error": None,
    "started_at": None,
    "finished_at": None,
}


class ScrapeScheduler:
    def __init__(self):
        self._scheduled_stop = threading.Event()
        self._scheduled_thread: Optional[threading.Thread] = None

    @property
    def status(self) -> Dict[str, Any]:
        return dict(_status)

    def run(
        self,
        source: str = "all",
        query: str = "software engineer",
        location: str = "Australia",
        insert_db: bool = True,
        profile: str | None = None,
        require_sponsorship: bool = True,
        max_pages: int = 2,
    ) -> Dict[str, Any]:
        with _lock:
            if _status.get("state") == "running":
                return {"error": "Scrape already running", "status": self.status}
            _status.update(
                {
                    "state": "running",
                    "started_at": time.time(),
                    "finished_at": None,
                    "last_error": None,
                }
            )

        try:
            jobs = self._collect(
                source, query, location, profile, require_sponsorship, max_pages
            )
            db_stats = {"inserted": 0, "skipped": 0}
            if insert_db and jobs:
                db_stats = insert_jobs(jobs)

            result = {
                "source": source,
                "profile": profile or "default",
                "query": query,
                "location": location,
                "fetched": len(jobs),
                "insert_db": insert_db,
                "db": db_stats,
                "sample_titles": [j.get("title") for j in jobs[:5]],
            }
            with _lock:
                _status["state"] = "completed"
                _status["last_result"] = result
                _status["finished_at"] = time.time()
            return result
        except Exception as exc:
            with _lock:
                _status["state"] = "failed"
                _status["last_error"] = str(exc)
                _status["finished_at"] = time.time()
            return {"error": str(exc), "status": self.status}

    def _collect(
        self,
        source: str,
        query: str,
        location: str,
        profile: str | None,
        require_sponsorship: bool,
        max_pages: int,
    ):
        if profile == "teaching_sponsorship" or source == "teaching_au":
            return fetch_teaching_sponsorship_jobs(
                location=location,
                max_pages_per_query=max_pages,
                require_sponsorship=require_sponsorship,
                extra_query=query if query != "software engineer" else None,
            )

        jobs = []
        sources = []
        if source in ("seek", "all"):
            sources.append("seek")
        if source in ("indeed", "all"):
            sources.append("indeed")
        if source in ("linkedin", "all"):
            sources.append("linkedin")

        errors = []
        for src in sources:
            try:
                if src == "seek":
                    raw = seek_au.search_seek(query, location=location, max_pages=max_pages)
                    jobs.extend(raw)
                elif src == "indeed":
                    from scrapers.sources.indeed_au import search_indeed_au

                    jobs.extend(search_indeed_au(query, location, max_pages))
                elif src == "linkedin":
                    from scrapers.sources.linkedin_au import search_linkedin_au

                    jobs.extend(search_linkedin_au(query, location, max_pages))
            except NotImplementedError as exc:
                errors.append(f"{src}: {exc}")
            except Exception as exc:
                errors.append(f"{src}: {exc}")
        if errors and not jobs:
            raise RuntimeError("; ".join(errors))

        if profile == "teaching_sponsorship_filter":
            jobs = [
                j
                for j in jobs
                if is_teaching_with_sponsorship(j, require_sponsorship=require_sponsorship)
            ]
        return jobs

    def start_scheduled(
        self,
        interval_minutes: int,
        source: str,
        query: str,
        location: str,
        profile: str | None = None,
    ) -> threading.Thread:
        self.stop_scheduled()
        self._scheduled_stop.clear()

        def loop():
            while not self._scheduled_stop.is_set():
                self.run(
                    source=source,
                    query=query,
                    location=location,
                    insert_db=True,
                    profile=profile,
                )
                self._scheduled_stop.wait(interval_minutes * 60)

        self._scheduled_thread = threading.Thread(target=loop, daemon=True)
        self._scheduled_thread.start()
        return self._scheduled_thread

    def stop_scheduled(self):
        self._scheduled_stop.set()


_scheduler: Optional[ScrapeScheduler] = None


def get_scheduler() -> ScrapeScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = ScrapeScheduler()
    return _scheduler
