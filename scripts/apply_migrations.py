#!/usr/bin/env python3
"""Apply SQL migrations. Usage: python scripts/apply_migrations.py"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "api"))

from platform_db import apply_pending_migrations

DB_PATH = os.environ.get(
    "DATABASE_URL", os.path.join(ROOT, "jobs.db")
)

if __name__ == "__main__":
    applied = apply_pending_migrations(DB_PATH)
    if applied:
        print("Applied:", ", ".join(applied))
    else:
        print("No pending migrations.")
