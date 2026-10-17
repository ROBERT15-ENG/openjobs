"""
Database helpers and data-subject actions for AU / Kenya compliance flows.
"""
import glob
import json
import os
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional

from legal_config import PRIVACY_POLICY_VERSION, TERMS_VERSION

USER_LEGAL_COLUMNS = [
    ("terms_accepted_at", "TEXT"),
    ("terms_version", "TEXT"),
    ("privacy_policy_version", "TEXT"),
    ("marketing_consent", "INTEGER DEFAULT 0"),
    ("marketing_consent_at", "TEXT"),
]


def init_legal_schema(db_path: str) -> None:
    """Add consent columns to users if missing."""
    if not db_path or not os.path.exists(db_path):
        return
    conn = sqlite3.connect(db_path)
    try:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
        for name, typedef in USER_LEGAL_COLUMNS:
            if name not in cols:
                conn.execute(f"ALTER TABLE users ADD COLUMN {name} {typedef}")
        conn.commit()
    finally:
        conn.close()


def record_registration_consent(
    conn: sqlite3.Connection,
    user_id: int,
    marketing_consent: bool,
) -> None:
    now = datetime.utcnow().isoformat() + "Z"
    conn.execute(
        """UPDATE users SET
            terms_accepted_at = ?,
            terms_version = ?,
            privacy_policy_version = ?,
            marketing_consent = ?,
            marketing_consent_at = ?
        WHERE id = ?""",
        (
            now,
            TERMS_VERSION,
            PRIVACY_POLICY_VERSION,
            1 if marketing_consent else 0,
            now if marketing_consent else None,
            user_id,
        ),
    )


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None


def export_user_data(conn: sqlite3.Connection, user_id: int) -> Dict[str, Any]:
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        return {}
    data = dict(user)
    export: Dict[str, Any] = {
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "privacy_policy_version": PRIVACY_POLICY_VERSION,
        "profile": data,
        "applications": [],
        "saved_jobs": [],
        "job_alerts": [],
        "posted_jobs": [],
    }
    if _table_exists(conn, "applications"):
        rows = conn.execute(
            "SELECT * FROM applications WHERE user_id = ?", (user_id,)
        ).fetchall()
        export["applications"] = [dict(r) for r in rows]
    if _table_exists(conn, "saved_jobs"):
        rows = conn.execute(
            "SELECT * FROM saved_jobs WHERE user_id = ?", (user_id,)
        ).fetchall()
        export["saved_jobs"] = [dict(r) for r in rows]
    if _table_exists(conn, "job_alerts"):
        rows = conn.execute(
            "SELECT * FROM job_alerts WHERE user_id = ?", (user_id,)
        ).fetchall()
        export["job_alerts"] = [dict(r) for r in rows]
    if data.get("role") == "employer" and _table_exists(conn, "jobs"):
        rows = conn.execute(
            "SELECT * FROM jobs WHERE employer_id = ?", (user_id,)
        ).fetchall()
        export["posted_jobs"] = [dict(r) for r in rows]
    return export


def _remove_kyc_files(user_id: int, kyc_dir: str) -> None:
    if not kyc_dir or not os.path.isdir(kyc_dir):
        return
    for path in glob.glob(os.path.join(kyc_dir, f"user_{user_id}_*")):
        try:
            os.remove(path)
        except OSError:
            pass


def delete_user_account(
    conn: sqlite3.Connection,
    user_id: int,
    upload_dir: Optional[str] = None,
    kyc_dir: Optional[str] = None,
) -> bool:
    user = conn.execute("SELECT id, role, email FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        return False

    if _table_exists(conn, "saved_jobs"):
        conn.execute("DELETE FROM saved_jobs WHERE user_id = ?", (user_id,))
    if _table_exists(conn, "job_alerts"):
        conn.execute("DELETE FROM job_alerts WHERE user_id = ?", (user_id,))
    if _table_exists(conn, "applications"):
        conn.execute("DELETE FROM applications WHERE user_id = ?", (user_id,))

    if user["role"] == "employer" and _table_exists(conn, "jobs"):
        conn.execute("UPDATE jobs SET is_active = 0 WHERE employer_id = ?", (user_id,))

    _remove_kyc_files(user_id, kyc_dir or "")
    if upload_dir and os.path.isdir(upload_dir):
        for path in glob.glob(os.path.join(upload_dir, f"user_{user_id}_*")):
            try:
                os.remove(path)
            except OSError:
                pass

    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    return True


def render_legal_html(templates_dir: str, filename: str) -> str:
    from legal_config import legal_substitutions

    path = os.path.join(templates_dir, filename)
    with open(path, encoding="utf-8") as f:
        html = f.read()
    for key, value in legal_substitutions().items():
        html = html.replace("{{" + key + "}}", value)
    return html
