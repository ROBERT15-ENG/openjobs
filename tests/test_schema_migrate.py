"""Schema upgrade path for existing production DBs."""

import os
import sqlite3
import sys

import pytest
from werkzeug.security import generate_password_hash

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
API = os.path.join(ROOT, 'api')
sys.path.insert(0, API)
sys.path.insert(0, ROOT)

# Minimal pre–PR #8 schema (no orgs/messages/posted_at/country)
LEGACY_SCHEMA = """
CREATE TABLE users (
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
CREATE TABLE jobs (
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
    created_at TEXT NOT NULL
);
CREATE TABLE applications (
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
    UNIQUE(job_id, user_id)
);
CREATE TABLE saved_jobs (
    user_id INTEGER NOT NULL,
    job_id INTEGER NOT NULL,
    saved_at TEXT NOT NULL,
    PRIMARY KEY (user_id, job_id)
);
CREATE TABLE skills_taxonomy (
    name TEXT PRIMARY KEY,
    aliases TEXT,
    category TEXT,
    demand_score INTEGER DEFAULT 50
);
CREATE TABLE companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    industry TEXT,
    website TEXT,
    description TEXT,
    created_at TEXT
);
CREATE TABLE job_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    keyword TEXT,
    location TEXT,
    remote_only INTEGER DEFAULT 0,
    salary_min INTEGER,
    active INTEGER DEFAULT 1
);
CREATE TABLE job_alert_sends (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id INTEGER NOT NULL,
    job_id INTEGER NOT NULL,
    sent_at TEXT NOT NULL,
    UNIQUE(alert_id, job_id)
);
CREATE TABLE ai_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    endpoint TEXT,
    tokens_used INTEGER,
    model TEXT,
    created_at TEXT
);
"""


@pytest.fixture
def legacy_client(tmp_path, monkeypatch):
    db_path = tmp_path / 'legacy.db'
    conn = sqlite3.connect(db_path)
    conn.executescript(LEGACY_SCHEMA)
    now = '2026-01-01T00:00:00'
    conn.execute(
        'INSERT INTO users (name, email, password_hash, role, company, created_at) VALUES (?, ?, ?, ?, ?, ?)',
        ('Old Emp', 'oldemp@test.com', generate_password_hash('pass123'), 'employer', 'LegacyCo', now),
    )
    emp_id = conn.execute('SELECT id FROM users').fetchone()[0]
    conn.execute(
        """INSERT INTO jobs (title, company, location, description, is_active, employer_id, created_at)
           VALUES (?, ?, ?, ?, 1, ?, ?)""",
        ('Legacy Job', 'LegacyCo', 'Sydney NSW', 'A role', emp_id, now),
    )
    conn.commit()
    conn.close()

    monkeypatch.setenv('DATABASE_PATH', str(db_path))
    monkeypatch.setenv('SECRET_KEY', 'test-secret-key-32bytes-minimum!!')
    from app_factory import create_app
    app = create_app({'TESTING': True, 'SECRET_KEY': 'test-secret-key-32bytes-minimum!!'})
    return app.test_client()


def test_legacy_db_upgrades_and_lists_jobs(legacy_client):
    res = legacy_client.get('/api/jobs')
    assert res.status_code == 200
    data = res.get_json()
    assert data['pagination']['total'] >= 1
    assert data['jobs'][0].get('date_posted')


def test_legacy_employer_gets_organization(legacy_client):
    login = legacy_client.post('/api/auth/login', json={
        'email': 'oldemp@test.com', 'password': 'pass123',
    })
    assert login.status_code == 200
    token = login.get_json()['token']
    team = legacy_client.get(
        '/api/employer/team',
        headers={'Authorization': f'Bearer {token}'},
    )
    assert team.status_code == 200
    assert len(team.get_json()['members']) >= 1


def test_legacy_regions_and_report(legacy_client):
    assert legacy_client.get('/api/regions').status_code == 200
    report = legacy_client.post('/api/jobs/1/report', json={'reason': 'spam'})
    assert report.status_code == 201
