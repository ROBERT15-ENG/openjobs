-- OpenJobs SQLite schema
-- Run: python scripts/init_db.py

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    phone TEXT,
    company TEXT,
    skills TEXT,
    preferred_location TEXT,
    experience TEXT,
    resume_text TEXT,
    cv_link TEXT,
    reset_token TEXT,
    reset_expires TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    company TEXT NOT NULL,
    location TEXT,
    description TEXT,
    salary TEXT DEFAULT 'Competitive',
    category TEXT DEFAULT 'General',
    is_active INTEGER NOT NULL DEFAULT 1,
    work_type TEXT DEFAULT 'full_time',
    work_arrangement TEXT DEFAULT 'remote',
    salary_min INTEGER,
    salary_max INTEGER,
    salary_currency TEXT DEFAULT 'AUD',
    search_summary TEXT,
    selling_points TEXT,
    video_url TEXT,
    expires_at TEXT,
    skills TEXT,
    employer_id INTEGER,
    view_count INTEGER NOT NULL DEFAULT 0,
    posted_at TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (employer_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    applied_at TEXT NOT NULL,
    resume_text TEXT,
    cover_letter TEXT,
    cv_link TEXT,
    ats_score INTEGER,
    notes TEXT,
    updated_at TEXT,
    FOREIGN KEY (job_id) REFERENCES jobs(id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    UNIQUE(job_id, user_id)
);

CREATE TABLE IF NOT EXISTS saved_jobs (
    user_id INTEGER NOT NULL,
    job_id INTEGER NOT NULL,
    saved_at TEXT NOT NULL,
    PRIMARY KEY (user_id, job_id),
    FOREIGN KEY (user_id) REFERENCES users(id),
    FOREIGN KEY (job_id) REFERENCES jobs(id)
);

CREATE TABLE IF NOT EXISTS skills_taxonomy (
    name TEXT PRIMARY KEY,
    aliases TEXT,
    category TEXT,
    demand_score INTEGER DEFAULT 50
);

CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    industry TEXT,
    website TEXT,
    description TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS job_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    keyword TEXT,
    location TEXT,
    remote_only INTEGER DEFAULT 0,
    salary_min INTEGER,
    active INTEGER DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS ai_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    endpoint TEXT,
    tokens_used INTEGER,
    model TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS crm_companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    industry TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS crm_contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    email TEXT,
    company_id INTEGER,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS crm_pipeline (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    stage TEXT,
    value REAL,
    created_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_jobs_active ON jobs(is_active);
CREATE INDEX IF NOT EXISTS idx_jobs_employer ON jobs(employer_id);
CREATE INDEX IF NOT EXISTS idx_applications_user ON applications(user_id);
CREATE INDEX IF NOT EXISTS idx_applications_job ON applications(job_id);
