"""Database helpers."""

import os
import sqlite3

from config import DEFAULT_DB_PATH
from flask import g


def get_db_path() -> str:
    return os.environ.get('DATABASE_PATH') or DEFAULT_DB_PATH


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(get_db_path())
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(_error=None):
    db = g.pop('db', None)
    if db:
        db.close()
