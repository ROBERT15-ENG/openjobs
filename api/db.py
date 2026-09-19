"""Database helpers.

Every connection (request-scoped or background) goes through ``connect`` so the
SQLite pragmas that matter under concurrency are applied uniformly:

- ``journal_mode=WAL``   readers never block the writer and vice versa
- ``busy_timeout``       wait instead of failing with "database is locked"
- ``foreign_keys=ON``    the schema declares FKs; enforce them (this pragma is
                         per-connection, so ``schema.sql`` alone does nothing)
- ``synchronous=NORMAL`` safe with WAL, much cheaper than FULL
"""

import os
import sqlite3

from config import DEFAULT_DB_PATH
from flask import g

BUSY_TIMEOUT_MS = int(os.environ.get('SQLITE_BUSY_TIMEOUT_MS', '5000'))


def get_db_path() -> str:
    return os.environ.get('DATABASE_PATH') or DEFAULT_DB_PATH


def connect(path: str | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or get_db_path(), timeout=BUSY_TIMEOUT_MS / 1000)
    conn.row_factory = sqlite3.Row
    conn.execute(f'PRAGMA busy_timeout = {BUSY_TIMEOUT_MS}')
    conn.execute('PRAGMA foreign_keys = ON')
    try:
        conn.execute('PRAGMA journal_mode = WAL')
        conn.execute('PRAGMA synchronous = NORMAL')
    except sqlite3.OperationalError:
        # Read-only or unsupported filesystem; keep the default journal.
        pass
    return conn


def get_db() -> sqlite3.Connection:
    if 'db' not in g:
        g.db = connect()
    return g.db


def close_db(_error=None):
    db = g.pop('db', None)
    if db:
        db.close()
