-- OpenJobs SQLite schema
-- Run: python scripts/init_db.py

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS organizations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT,
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
    organization_id INTEGER,
    latitude REAL,
    longitude REAL,
    email_confirmed INTEGER NOT NULL DEFAULT 1,
    confirm_token TEXT,
    confirm_expires TEXT,
    google_id TEXT,
    kyc_status TEXT DEFAULT 'none',
    kyc_doc_type TEXT,
    kyc_doc_number TEXT,
    dob TEXT,
    nationality TEXT,
    country TEXT,
    county TEXT,
    address TEXT,
    salutation TEXT,
    visa_status TEXT,
    headline TEXT,
    bio TEXT,
    desired_role TEXT,
    expected_salary INTEGER,
    pref_work_type TEXT,
    pref_remote TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (organization_id) REFERENCES organizations(id)
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
    is_featured INTEGER NOT NULL DEFAULT 0,
    latitude REAL,
    longitude REAL,
    country TEXT,
    region TEXT,
    posted_at TEXT,
    moderation_status TEXT NOT NULL DEFAULT 'ok',
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

CREATE TABLE IF NOT EXISTS organization_members (
    organization_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    role TEXT NOT NULL DEFAULT 'recruiter',
    created_at TEXT NOT NULL,
    PRIMARY KEY (organization_id, user_id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE IF NOT EXISTS job_reports (
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
);

CREATE TABLE IF NOT EXISTS conversations (
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
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    sender_id INTEGER NOT NULL,
    body TEXT NOT NULL,
    created_at TEXT NOT NULL,
    read_at TEXT,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id),
    FOREIGN KEY (sender_id) REFERENCES users(id)
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

CREATE TABLE IF NOT EXISTS job_alert_sends (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id INTEGER NOT NULL,
    job_id INTEGER NOT NULL,
    sent_at TEXT NOT NULL,
    UNIQUE(alert_id, job_id),
    FOREIGN KEY (alert_id) REFERENCES job_alerts(id),
    FOREIGN KEY (job_id) REFERENCES jobs(id)
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

CREATE TABLE IF NOT EXISTS revoked_tokens (
    jti TEXT PRIMARY KEY,
    expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS email_outbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    to_email TEXT NOT NULL,
    subject TEXT NOT NULL,
    html_body TEXT NOT NULL,
    text_body TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    created_at TEXT NOT NULL,
    sent_at TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_users_email_nocase ON users(lower(email));
CREATE INDEX IF NOT EXISTS idx_jobs_active ON jobs(is_active);
CREATE INDEX IF NOT EXISTS idx_jobs_geo ON jobs(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_revoked_tokens_expires ON revoked_tokens(expires_at);
CREATE INDEX IF NOT EXISTS idx_email_outbox_status ON email_outbox(status, id);
CREATE INDEX IF NOT EXISTS idx_jobs_employer ON jobs(employer_id);
CREATE INDEX IF NOT EXISTS idx_applications_user ON applications(user_id);
CREATE INDEX IF NOT EXISTS idx_applications_job ON applications(job_id);
CREATE INDEX IF NOT EXISTS idx_job_reports_status ON job_reports(status);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_org_members_user ON organization_members(user_id);
