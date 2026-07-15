"""Idempotent schema upgrades for existing SQLite databases."""

from regions_util import infer_country_region

USER_COLUMNS = {
    'organization_id': 'INTEGER',
    'latitude': 'REAL',
    'longitude': 'REAL',
    'email_confirmed': 'INTEGER NOT NULL DEFAULT 1',
    'confirm_token': 'TEXT',
    'confirm_expires': 'TEXT',
    'google_id': 'TEXT',
    'kyc_status': "TEXT DEFAULT 'none'",
    'kyc_doc_type': 'TEXT',
    'kyc_doc_number': 'TEXT',
    'dob': 'TEXT',
    'nationality': 'TEXT',
    'country': 'TEXT',
    'county': 'TEXT',
    'address': 'TEXT',
    'salutation': 'TEXT',
    'visa_status': 'TEXT',
}

JOB_COLUMNS = {
    'is_featured': 'INTEGER NOT NULL DEFAULT 0',
    'latitude': 'REAL',
    'longitude': 'REAL',
    'country': 'TEXT',
    'region': 'TEXT',
    'posted_at': 'TEXT',
    'view_count': 'INTEGER NOT NULL DEFAULT 0',
}

TABLE_DDL = [
    """CREATE TABLE IF NOT EXISTS organizations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS organization_members (
        organization_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        role TEXT NOT NULL DEFAULT 'recruiter',
        created_at TEXT NOT NULL,
        PRIMARY KEY (organization_id, user_id),
        FOREIGN KEY (organization_id) REFERENCES organizations(id),
        FOREIGN KEY (user_id) REFERENCES users(id)
    )""",
    """CREATE TABLE IF NOT EXISTS job_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER NOT NULL,
        reporter_id INTEGER,
        reason TEXT NOT NULL,
        details TEXT,
        status TEXT NOT NULL DEFAULT 'open',
        created_at TEXT NOT NULL,
        resolved_at TEXT,
        FOREIGN KEY (job_id) REFERENCES jobs(id),
        FOREIGN KEY (reporter_id) REFERENCES users(id)
    )""",
    """CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        application_id INTEGER NOT NULL UNIQUE,
        job_id INTEGER NOT NULL,
        employer_id INTEGER NOT NULL,
        seeker_id INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (application_id) REFERENCES applications(id),
        FOREIGN KEY (job_id) REFERENCES jobs(id),
        FOREIGN KEY (employer_id) REFERENCES users(id),
        FOREIGN KEY (seeker_id) REFERENCES users(id)
    )""",
    """CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        conversation_id INTEGER NOT NULL,
        sender_id INTEGER NOT NULL,
        body TEXT NOT NULL,
        created_at TEXT NOT NULL,
        read_at TEXT,
        FOREIGN KEY (conversation_id) REFERENCES conversations(id),
        FOREIGN KEY (sender_id) REFERENCES users(id)
    )""",
]

INDEX_DDL = [
    'CREATE INDEX IF NOT EXISTS idx_jobs_active ON jobs(is_active)',
    'CREATE INDEX IF NOT EXISTS idx_jobs_employer ON jobs(employer_id)',
    'CREATE INDEX IF NOT EXISTS idx_applications_user ON applications(user_id)',
    'CREATE INDEX IF NOT EXISTS idx_applications_job ON applications(job_id)',
    'CREATE INDEX IF NOT EXISTS idx_job_reports_status ON job_reports(status)',
    'CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id)',
    'CREATE INDEX IF NOT EXISTS idx_org_members_user ON organization_members(user_id)',
]


def _existing_columns(db, table: str) -> set[str]:
    rows = db.execute(f'PRAGMA table_info({table})').fetchall()
    return {row[1] for row in rows}


def _table_exists(db, table: str) -> bool:
    row = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table,),
    ).fetchone()
    return row is not None


def ensure_schema(db) -> None:
    """Create missing tables/columns and backfill derived fields."""
    for ddl in TABLE_DDL:
        db.execute(ddl)

    if not _table_exists(db, 'users') or not _table_exists(db, 'jobs'):
        db.commit()
        return

    user_cols = _existing_columns(db, 'users')
    for name, decl in USER_COLUMNS.items():
        if name not in user_cols:
            db.execute(f'ALTER TABLE users ADD COLUMN {name} {decl}')

    job_cols = _existing_columns(db, 'jobs')
    for name, decl in JOB_COLUMNS.items():
        if name not in job_cols:
            db.execute(f'ALTER TABLE jobs ADD COLUMN {name} {decl}')

    for ddl in INDEX_DDL:
        db.execute(ddl)

    # Backfill posted_at from created_at
    job_cols = _existing_columns(db, 'jobs')
    if 'posted_at' in job_cols:
        db.execute(
            "UPDATE jobs SET posted_at = created_at "
            "WHERE posted_at IS NULL OR posted_at = ''"
        )

    # Backfill country/region from location when blank
    if 'country' in job_cols or 'country' in _existing_columns(db, 'jobs'):
        jobs = db.execute(
            "SELECT id, location, country, region FROM jobs "
            "WHERE country IS NULL OR country = ''"
        ).fetchall()
        for job in jobs:
            country, region = infer_country_region(job['location'])
            if country or region:
                db.execute(
                    "UPDATE jobs SET country = COALESCE(NULLIF(country, ''), ?), "
                    "region = COALESCE(NULLIF(region, ''), ?) WHERE id = ?",
                    (country, region, job['id']),
                )

    # Ensure employers have an organization for team features
    if 'organization_id' in _existing_columns(db, 'users') and _table_exists(db, 'organizations'):
        employers = db.execute(
            "SELECT id, company, name FROM users "
            "WHERE role = 'employer' AND (organization_id IS NULL OR organization_id = 0)"
        ).fetchall()
        import datetime
        now = datetime.datetime.now().isoformat()
        for emp in employers:
            org_name = (emp['company'] or emp['name'] or f'Employer {emp["id"]}').strip()
            cur = db.execute(
                'INSERT INTO organizations (name, created_at) VALUES (?, ?)',
                (org_name, now),
            )
            org_id = cur.lastrowid
            db.execute('UPDATE users SET organization_id = ? WHERE id = ?', (org_id, emp['id']))
            db.execute(
                """INSERT OR IGNORE INTO organization_members
                   (organization_id, user_id, role, created_at) VALUES (?, ?, 'owner', ?)""",
                (org_id, emp['id'], now),
            )

    db.commit()
