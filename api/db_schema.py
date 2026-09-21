#!/usr/bin/env python3
"""
Database schema for OpenJobs (SQLite).

The schema is declared as data so that the same definition can both create
tables on a fresh database and add any missing columns to an existing one.
`init_db()` is idempotent and is called by server.py at startup; it can also
be run directly:

    python api/db_schema.py [--db path/to/jobs.db] [--admin user@example.com]
"""
import argparse
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# table -> ordered list of (column, declaration)
SCHEMA = {
    'users': [
        ('id',                 'INTEGER PRIMARY KEY AUTOINCREMENT'),
        ('name',               'TEXT'),
        ('email',              'TEXT UNIQUE NOT NULL'),
        ('password_hash',      'TEXT'),
        ('role',               "TEXT NOT NULL DEFAULT 'user'"),
        ('plan',               "TEXT DEFAULT 'free'"),
        ('created_at',         'TEXT DEFAULT CURRENT_TIMESTAMP'),
        ('email_confirmed',    'INTEGER NOT NULL DEFAULT 0'),
        ('confirm_token',      'TEXT'),
        ('confirm_expires',    'TEXT'),
        ('reset_token',        'TEXT'),
        ('reset_expires',      'TEXT'),
        ('google_id',          'TEXT'),
        ('skills',             'TEXT'),
        ('phone',              'TEXT'),
        ('company',            'TEXT'),
        ('preferred_location', 'TEXT'),
        ('experience',         'TEXT'),
        ('cv_link',            'TEXT'),
        ('resume_text',        'TEXT'),
        ('calendly_url',       'TEXT'),
        ('kyc_status',         "TEXT DEFAULT 'pending'"),
        ('kyc_doc_type',       'TEXT'),
        ('kyc_doc_number',     'TEXT'),
        ('salutation',         'TEXT'),
        ('dob',                'TEXT'),
        ('nationality',        'TEXT'),
        ('country',            'TEXT'),
        ('county',             'TEXT'),
        ('address',            'TEXT'),
        ('visa_status',        'TEXT'),
    ],
    'jobs': [
        ('id',                'INTEGER PRIMARY KEY AUTOINCREMENT'),
        ('title',             'TEXT NOT NULL'),
        ('company',           'TEXT NOT NULL'),
        ('location',          'TEXT'),
        ('description',       'TEXT'),
        ('salary',            'TEXT'),
        ('salary_min',        'INTEGER'),
        ('salary_max',        'INTEGER'),
        ('salary_currency',   "TEXT DEFAULT 'KES'"),
        ('category',          "TEXT DEFAULT 'General'"),
        ('work_type',         "TEXT DEFAULT 'full_time'"),
        ('work_arrangement',  "TEXT DEFAULT 'remote'"),
        ('classification',    'TEXT'),
        ('subclassification', 'TEXT'),
        ('state',             'TEXT'),
        ('skills',            'TEXT'),
        ('search_summary',    'TEXT'),
        ('selling_points',    'TEXT'),
        ('video_url',         'TEXT'),
        ('employer_id',       'INTEGER REFERENCES users(id)'),
        ('is_active',         'INTEGER NOT NULL DEFAULT 1'),
        ('is_featured',       'INTEGER NOT NULL DEFAULT 0'),
        ('company_rating',    'REAL DEFAULT 0'),
        ('view_count',        'INTEGER NOT NULL DEFAULT 0'),
        ('application_count', 'INTEGER NOT NULL DEFAULT 0'),
        ('created_at',        'TEXT DEFAULT CURRENT_TIMESTAMP'),
        ('expires_at',        'TEXT'),
    ],
    'applications': [
        ('id',           'INTEGER PRIMARY KEY AUTOINCREMENT'),
        ('job_id',       'INTEGER NOT NULL REFERENCES jobs(id)'),
        ('user_id',      'INTEGER NOT NULL REFERENCES users(id)'),
        ('status',       "TEXT NOT NULL DEFAULT 'pending'"),
        ('applied_at',   'TEXT DEFAULT CURRENT_TIMESTAMP'),
        ('updated_at',   'TEXT'),
        ('cover_letter', 'TEXT'),
        ('resume_text',  'TEXT'),
        ('cv_link',      'TEXT'),
        ('ats_score',    'REAL'),
        ('notes',        'TEXT'),
    ],
    'saved_jobs': [
        ('id',       'INTEGER PRIMARY KEY AUTOINCREMENT'),
        ('user_id',  'INTEGER NOT NULL REFERENCES users(id)'),
        ('job_id',   'INTEGER NOT NULL REFERENCES jobs(id)'),
        ('saved_at', 'TEXT DEFAULT CURRENT_TIMESTAMP'),
    ],
    'companies': [
        ('id',          'INTEGER PRIMARY KEY AUTOINCREMENT'),
        ('name',        'TEXT NOT NULL'),
        ('industry',    'TEXT'),
        ('location',    'TEXT'),
        ('website',     'TEXT'),
        ('description', 'TEXT'),
        ('created_at',  'TEXT DEFAULT CURRENT_TIMESTAMP'),
    ],
    'company_ratings': [
        ('id',         'INTEGER PRIMARY KEY AUTOINCREMENT'),
        ('company',    'TEXT NOT NULL'),
        ('user_id',    'INTEGER NOT NULL REFERENCES users(id)'),
        ('rating',     'REAL NOT NULL'),
        ('created_at', 'TEXT DEFAULT CURRENT_TIMESTAMP'),
    ],
    'skills_taxonomy': [
        ('id',           'INTEGER PRIMARY KEY AUTOINCREMENT'),
        ('name',         'TEXT UNIQUE NOT NULL'),
        ('aliases',      'TEXT'),
        ('category',     'TEXT'),
        ('demand_score', 'REAL DEFAULT 0'),
    ],
    'job_alerts': [
        ('id',               'INTEGER PRIMARY KEY AUTOINCREMENT'),
        ('user_id',          'INTEGER NOT NULL REFERENCES users(id)'),
        ('name',             'TEXT'),
        ('keywords',         'TEXT'),
        ('location',         'TEXT'),
        ('classification',   'TEXT'),
        ('work_type',        'TEXT'),
        ('work_arrangement', 'TEXT'),
        ('salary_min',       'INTEGER'),
        ('frequency',        "TEXT DEFAULT 'daily'"),   # 'instant' | 'daily'
        ('is_active',        'INTEGER NOT NULL DEFAULT 1'),
        ('last_sent_at',     'TEXT'),
        ('created_at',       'TEXT DEFAULT CURRENT_TIMESTAMP'),
    ],
    'company_reviews': [
        ('id',         'INTEGER PRIMARY KEY AUTOINCREMENT'),
        ('company',    'TEXT NOT NULL'),
        ('user_id',    'INTEGER NOT NULL REFERENCES users(id)'),
        ('rating',     'INTEGER NOT NULL'),
        ('title',      'TEXT'),
        ('pros',       'TEXT'),
        ('cons',       'TEXT'),
        ('role',       'TEXT'),
        ('is_current', 'INTEGER DEFAULT 0'),
        ('created_at', 'TEXT DEFAULT CURRENT_TIMESTAMP'),
    ],
    'kyc_documents': [
        ('id',          'INTEGER PRIMARY KEY AUTOINCREMENT'),
        ('user_id',     'INTEGER NOT NULL REFERENCES users(id)'),
        ('doc_type',    'TEXT NOT NULL'),
        ('doc_number',  'TEXT'),
        ('file_path',   'TEXT'),
        ('uploaded_at', 'TEXT DEFAULT CURRENT_TIMESTAMP'),
        ('status',      "TEXT DEFAULT 'pending'"),
    ],
    'crm_companies': [
        ('id',         'INTEGER PRIMARY KEY AUTOINCREMENT'),
        ('name',       'TEXT NOT NULL'),
        ('industry',   'TEXT'),
        ('status',     'TEXT'),
        ('created_at', 'TEXT DEFAULT CURRENT_TIMESTAMP'),
    ],
    'crm_contacts': [
        ('id',         'INTEGER PRIMARY KEY AUTOINCREMENT'),
        ('company_id', 'INTEGER REFERENCES crm_companies(id)'),
        ('name',       'TEXT'),
        ('email',      'TEXT'),
        ('phone',      'TEXT'),
        ('created_at', 'TEXT DEFAULT CURRENT_TIMESTAMP'),
    ],
    'crm_pipeline': [
        ('id',         'INTEGER PRIMARY KEY AUTOINCREMENT'),
        ('company_id', 'INTEGER REFERENCES crm_companies(id)'),
        ('stage',      'TEXT'),
        ('value',      'REAL'),
        ('created_at', 'TEXT DEFAULT CURRENT_TIMESTAMP'),
    ],
    'ai_usage': [
        ('id',          'INTEGER PRIMARY KEY AUTOINCREMENT'),
        ('endpoint',    'TEXT'),
        ('tokens_used', 'INTEGER'),
        ('model',       'TEXT'),
        ('created_at',  'TEXT DEFAULT CURRENT_TIMESTAMP'),
    ],
}

# Constraints that cannot be expressed as a column declaration.
UNIQUE_INDEXES = [
    ('idx_saved_jobs_user_job',    'saved_jobs',    ['user_id', 'job_id']),
    ('idx_kyc_documents_user_type', 'kyc_documents', ['user_id', 'doc_type']),
    ('idx_company_ratings_unique',  'company_ratings', ['company', 'user_id']),
    ('idx_company_reviews_unique',  'company_reviews', ['company', 'user_id']),
]

INDEXES = [
    ('idx_jobs_active_created',   'jobs',         ['is_active', 'created_at']),
    ('idx_jobs_employer',         'jobs',         ['employer_id']),
    ('idx_jobs_classification',   'jobs',         ['classification']),
    ('idx_jobs_state',            'jobs',         ['state']),
    ('idx_jobs_company',          'jobs',         ['company']),
    ('idx_applications_job',      'applications', ['job_id']),
    ('idx_applications_user',     'applications', ['user_id']),
    ('idx_job_alerts_user',       'job_alerts',   ['user_id']),
]

# Full-text index over jobs (SQLite FTS5, external-content table kept in sync by triggers).
# Column order matters: bm25() weights in the search code refer to these positions.
FTS_COLUMNS = ['title', 'company', 'location', 'description', 'skills', 'search_summary', 'classification']

FTS_SQL = [
    f"CREATE VIRTUAL TABLE IF NOT EXISTS jobs_fts USING fts5({', '.join(FTS_COLUMNS)}, "
    f"content='jobs', content_rowid='id', tokenize='porter unicode61')",
    "CREATE TRIGGER IF NOT EXISTS jobs_fts_ai AFTER INSERT ON jobs BEGIN "
    f"  INSERT INTO jobs_fts(rowid, {', '.join(FTS_COLUMNS)}) VALUES (new.id, {', '.join('new.' + c for c in FTS_COLUMNS)}); END",
    "CREATE TRIGGER IF NOT EXISTS jobs_fts_ad AFTER DELETE ON jobs BEGIN "
    f"  INSERT INTO jobs_fts(jobs_fts, rowid, {', '.join(FTS_COLUMNS)}) VALUES ('delete', old.id, {', '.join('old.' + c for c in FTS_COLUMNS)}); END",
    "CREATE TRIGGER IF NOT EXISTS jobs_fts_au AFTER UPDATE ON jobs BEGIN "
    f"  INSERT INTO jobs_fts(jobs_fts, rowid, {', '.join(FTS_COLUMNS)}) VALUES ('delete', old.id, {', '.join('old.' + c for c in FTS_COLUMNS)}); "
    f"  INSERT INTO jobs_fts(rowid, {', '.join(FTS_COLUMNS)}) VALUES (new.id, {', '.join('new.' + c for c in FTS_COLUMNS)}); END",
]


def fts_available(con) -> bool:
    try:
        con.execute("SELECT 1 FROM jobs_fts LIMIT 1")
        return True
    except sqlite3.Error:
        return False


def _setup_fts(con):
    """Create the FTS index + triggers; (re)build it if the table is new/empty."""
    try:
        for stmt in FTS_SQL:
            con.execute(stmt)
        if con.execute("SELECT COUNT(*) FROM jobs").fetchone()[0] and \
           not con.execute("SELECT 1 FROM jobs_fts LIMIT 1").fetchone():
            con.execute("INSERT INTO jobs_fts(jobs_fts) VALUES ('rebuild')")
    except sqlite3.OperationalError as e:
        # FTS5 not compiled into this SQLite build — search falls back to LIKE.
        print(f"[db] FTS5 unavailable ({e}); keyword search will use LIKE")


def _backfill_jobs(con):
    """Populate derived columns (state, classification) on rows created before they existed."""
    from taxonomy import derive_state, normalize_classification
    rows = con.execute("SELECT id, location, category FROM jobs WHERE state IS NULL OR classification IS NULL").fetchall()
    for job_id, location, category in rows:
        con.execute("UPDATE jobs SET state = COALESCE(state, ?), classification = COALESCE(classification, ?) WHERE id = ?",
                    (derive_state(location), normalize_classification(category), job_id))


def _create_sql(table, columns):
    cols = ',\n    '.join(f'{name} {decl}' for name, decl in columns)
    return f'CREATE TABLE IF NOT EXISTS {table} (\n    {cols}\n)'


def init_db(db_path):
    """Create missing tables/columns/indexes. Safe to run on every startup."""
    os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
    con = sqlite3.connect(db_path)
    try:
        for table, columns in SCHEMA.items():
            con.execute(_create_sql(table, columns))
            existing = {row[1] for row in con.execute(f'PRAGMA table_info({table})')}
            for name, decl in columns:
                if name in existing:
                    continue
                # ALTER TABLE cannot add PRIMARY KEY / UNIQUE constraints; strip them.
                safe_decl = decl.replace('PRIMARY KEY AUTOINCREMENT', '').replace('UNIQUE', '')
                if 'NOT NULL' in safe_decl and 'DEFAULT' not in safe_decl:
                    safe_decl = safe_decl.replace('NOT NULL', '')
                con.execute(f'ALTER TABLE {table} ADD COLUMN {name} {safe_decl.strip()}')
        for idx, table, cols in UNIQUE_INDEXES:
            con.execute(f'CREATE UNIQUE INDEX IF NOT EXISTS {idx} ON {table} ({", ".join(cols)})')
        for idx, table, cols in INDEXES:
            con.execute(f'CREATE INDEX IF NOT EXISTS {idx} ON {table} ({", ".join(cols)})')
        _backfill_jobs(con)
        _setup_fts(con)
        con.commit()
    finally:
        con.close()


def make_admin(db_path, email):
    """Promote an existing user to the admin role (there is deliberately no self-serve path)."""
    con = sqlite3.connect(db_path)
    try:
        cur = con.execute("UPDATE users SET role = 'admin', email_confirmed = 1 WHERE email = ?", (email,))
        con.commit()
        return cur.rowcount
    finally:
        con.close()


if __name__ == '__main__':
    default_db = os.environ.get('DATABASE_URL',
                                os.path.join(os.path.dirname(__file__), '..', 'jobs.db'))
    ap = argparse.ArgumentParser(description='Initialise / migrate the OpenJobs SQLite database.')
    ap.add_argument('--db', default=default_db)
    ap.add_argument('--admin', metavar='EMAIL', help='promote this user to admin')
    args = ap.parse_args()
    init_db(args.db)
    print(f'Schema OK: {os.path.abspath(args.db)}')
    if args.admin:
        n = make_admin(args.db, args.admin)
        print(f'Promoted {n} user(s) to admin' if n else f'No user found with email {args.admin}')
