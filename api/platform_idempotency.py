"""Idempotency-Key handling for POST apply flows (P1)."""

import json
import datetime
from flask import jsonify


def get_idempotency_key(request) -> str:
    return (request.headers.get("Idempotency-Key") or "").strip()[:128]


def load_stored_response(db, key: str, user_id: int, route: str):
    if not key:
        return None
    row = db.execute(
        "SELECT status_code, response_body FROM idempotency_keys WHERE key = ? AND user_id = ? AND route = ?",
        (key, user_id, route),
    ).fetchone()
    if not row:
        return None
    try:
        body = json.loads(row["response_body"])
    except Exception:
        body = {"success": True, "idempotent": True}
    return jsonify(body), row["status_code"]


def store_response(db, key: str, user_id: int, route: str, status_code: int, body: dict):
    if not key:
        return
    db.execute(
        "INSERT OR REPLACE INTO idempotency_keys (key, user_id, route, status_code, response_body, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            key,
            user_id,
            route,
            status_code,
            json.dumps(body),
            datetime.datetime.utcnow().isoformat() + "Z",
        ),
    )
