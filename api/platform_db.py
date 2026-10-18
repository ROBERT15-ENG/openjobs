"""
Schema migrations and DB helpers for OpenJobs platform hardening.
"""

import os
import sqlite3
import datetime
from typing import List

MIGRATIONS_DIR = os.path.join(os.path.dirname(__file__), "..", "migrations")


def _migration_files() -> List[str]:
    if not os.path.isdir(MIGRATIONS_DIR):
        return []
    return sorted(
        f for f in os.listdir(MIGRATIONS_DIR) if f.endswith(".sql")
    )


def apply_pending_migrations(db_path: str) -> List[str]:
    """Apply any SQL migrations not yet recorded. Returns applied filenames."""
    applied: List[str] = []
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TEXT NOT NULL)"
        )
        done = {
            row[0]
            for row in conn.execute("SELECT version FROM schema_migrations").fetchall()
        }
        for name in _migration_files():
            if name in done:
                continue
            path = os.path.join(MIGRATIONS_DIR, name)
            sql = open(path, encoding="utf-8").read()
            conn.executescript(sql)
            conn.execute(
                "INSERT OR IGNORE INTO schema_migrations (version, applied_at) VALUES (?, ?)",
                (name, datetime.datetime.utcnow().isoformat() + "Z"),
            )
            conn.commit()
            applied.append(name)
        _apply_optional_indexes(conn)
    finally:
        conn.close()
    return applied


def _apply_optional_indexes(conn: sqlite3.Connection) -> None:
    """Create indexes when application tables exist (P1)."""
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    statements = []
    if "jobs" in tables:
        statements.extend(
            [
                "CREATE INDEX IF NOT EXISTS idx_jobs_active_created ON jobs (is_active, created_at DESC)",
                "CREATE INDEX IF NOT EXISTS idx_jobs_featured ON jobs (is_featured, created_at DESC)",
                "CREATE INDEX IF NOT EXISTS idx_jobs_location ON jobs (location)",
            ]
        )
    if "applications" in tables:
        statements.extend(
            [
                "CREATE INDEX IF NOT EXISTS idx_applications_user ON applications (user_id, applied_at DESC)",
                "CREATE INDEX IF NOT EXISTS idx_applications_job ON applications (job_id, status)",
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_applications_job_user_unique ON applications (job_id, user_id)",
            ]
        )
    if "users" in tables:
        statements.append(
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users (email)"
        )
    for sql in statements:
        try:
            conn.execute(sql)
        except sqlite3.OperationalError:
            pass
    conn.commit()


def check_db_ready(db_path: str) -> bool:
    try:
        conn = sqlite3.connect(db_path, timeout=2)
        conn.execute("SELECT 1")
        conn.close()
        return True
    except Exception:
        return False
