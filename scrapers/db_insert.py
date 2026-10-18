"""Insert scraped jobs into OpenJobs SQLite database."""

from __future__ import annotations

import datetime
import os
import sqlite3
from typing import Any, Dict, List, Tuple

DEFAULT_DB = os.path.join(os.path.dirname(__file__), "..", "jobs.db")


def _db_path() -> str:
    raw = os.environ.get("DATABASE_URL", DEFAULT_DB)
    if raw.startswith("sqlite:///"):
        return raw.replace("sqlite:///", "", 1)
    return raw


def job_exists(conn: sqlite3.Connection, external_id: str, source: str) -> bool:
    if not external_id:
        return False
    marker = f"{source}:{external_id}"
    row = conn.execute(
        "SELECT id FROM jobs WHERE search_summary LIKE ? LIMIT 1",
        (f"%{marker}%",),
    ).fetchone()
    return row is not None


def insert_job(conn: sqlite3.Connection, job: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Insert one job. Returns (inserted, message).
    Skips duplicate external ids.
    """
    source = job.get("source") or "scraper"
    ext = job.get("external_id") or ""
    summary = job.get("search_summary") or ""
    if ext and not summary.startswith(f"{source}:{ext}"):
        summary = f"{source}:{ext} {summary}".strip()

    if job_exists(conn, ext, source):
        return False, "duplicate"

    desc = job.get("description") or ""
    url = job.get("external_url")
    if url and url not in desc:
        desc = f"{desc}\n\nApply: {url}".strip()

    now = datetime.datetime.now().isoformat()
    expires = (datetime.datetime.now() + datetime.timedelta(days=30)).isoformat()

    conn.execute(
        """INSERT INTO jobs (
            title, company, location, description, salary, category, is_active, created_at,
            work_type, work_arrangement, salary_min, salary_max, salary_currency,
            search_summary, selling_points, video_url, expires_at, skills, employer_id,
            company_rating, is_featured
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            job.get("title"),
            job.get("company"),
            job.get("location"),
            desc[:8000],
            job.get("salary") or "",
            job.get("category")
            or job.get("occupation_title")
            or "Skilled migration",
            1,
            now,
            job.get("work_type", "full_time"),
            job.get("work_arrangement", "on_site"),
            job.get("salary_min"),
            job.get("salary_max"),
            job.get("salary_currency", "AUD"),
            summary[:500],
            "[]",
            "",
            expires,
            job.get("skills", ""),
            None,
            0.0,
            0,
        ),
    )
    return True, "inserted"


def insert_jobs(jobs: List[Dict[str, Any]]) -> Dict[str, int]:
    path = _db_path()
    if not os.path.isfile(path):
        return {"inserted": 0, "skipped": 0, "error": "database_missing"}

    conn = sqlite3.connect(path)
    try:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='jobs'"
            ).fetchall()
        }
        if "jobs" not in tables:
            return {"inserted": 0, "skipped": 0, "error": "jobs_table_missing"}

        inserted = skipped = 0
        for job in jobs:
            ok, reason = insert_job(conn, job)
            if ok:
                inserted += 1
            else:
                skipped += 1
        conn.commit()
        return {"inserted": inserted, "skipped": skipped}
    finally:
        conn.close()
