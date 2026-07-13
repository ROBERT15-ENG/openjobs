"""Migrate legacy application status values."""

import os
import sqlite3

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.environ.get('DATABASE_PATH', os.path.join(PROJECT_ROOT, 'jobs.db'))

MIGRATIONS = [
    ("UPDATE applications SET status='applied' WHERE status='pending'",),
    ("UPDATE applications SET status='screening' WHERE status='reviewing'",),
]


def migrate_statuses() -> None:
    if not os.path.exists(DB_PATH):
        print(f'Database not found at {DB_PATH}')
        return
    db = sqlite3.connect(DB_PATH)
    for (sql,) in MIGRATIONS:
        db.execute(sql)
    db.commit()
    db.close()
    print(f'Migrated application statuses in {DB_PATH}')


if __name__ == '__main__':
    migrate_statuses()
