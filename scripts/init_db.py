#!/usr/bin/env python3
"""Initialize jobs.db from schema.sql with seed users and sample data."""

import datetime
import os
import sqlite3

from werkzeug.security import generate_password_hash

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DB_PATH = os.environ.get('DATABASE_PATH') or os.path.join(PROJECT_ROOT, 'jobs.db')
SCHEMA_PATH = os.path.join(PROJECT_ROOT, 'schema.sql')
DEFAULT_ADMIN_PASSWORD = 'admin123'


def _utc_iso(delta: datetime.timedelta | None = None) -> str:
    moment = datetime.datetime.now(datetime.timezone.utc) + (delta or datetime.timedelta())
    return moment.isoformat().replace('+00:00', 'Z')


def init_db(force: bool = False) -> None:
    if os.path.exists(DB_PATH) and not force:
        print(f'Database already exists at {DB_PATH} (use --force to recreate)')
        return

    admin_password = os.environ.get('ADMIN_PASSWORD', DEFAULT_ADMIN_PASSWORD)
    if admin_password == DEFAULT_ADMIN_PASSWORD:
        if os.environ.get('FLASK_ENV') == 'production':
            raise SystemExit('Refusing to seed the default admin password in production. Set ADMIN_PASSWORD.')
        print('WARNING: Default admin password in use. Set ADMIN_PASSWORD before production deploy.')

    if force and os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
        schema = f.read()

    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.executescript(schema)

    now = _utc_iso()

    users = [
        ('Demo Seeker', 'demo@openjobs.com', generate_password_hash('TestPass123'), 'user'),
        ('Demo Employer', 'employer@openjobs.com', generate_password_hash('Employer123'), 'employer'),
        ('Platform Admin', 'admin@openjobs.com', generate_password_hash(admin_password), 'admin'),
    ]
    for name, email, pw_hash, role in users:
        db.execute(
            'INSERT INTO users (name, email, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?)',
            (name, email, pw_hash, role, now),
        )

    employer_id = db.execute("SELECT id FROM users WHERE email = 'employer@openjobs.com'").fetchone()[0]

    sample_jobs = [
        (
            'Software Engineering Intern',
            'OpenJobs',
            'Remote',
            'Build features for an AI-powered job board. Python and JavaScript required.',
            'Competitive',
            'Development',
            1,
            'internship',
            'remote',
            0,
            0,
            'AUD',
            'Internship for junior developers',
            '[]',
            '',
            _utc_iso(datetime.timedelta(days=30)),
            'Python,JavaScript,Flask',
            employer_id,
            now,
            now,
        ),
        (
            'DevOps Engineer',
            'CloudScale',
            'Sydney NSW',
            'Manage CI/CD pipelines and cloud infrastructure on AWS.',
            'AUD 130k–160k',
            'DevOps',
            1,
            'full_time',
            'hybrid',
            130000,
            160000,
            'AUD',
            'DevOps role with AWS and Kubernetes',
            '[]',
            '',
            _utc_iso(datetime.timedelta(days=30)),
            'AWS,Kubernetes,Docker,Python',
            employer_id,
            now,
            now,
        ),
    ]
    for job in sample_jobs:
        db.execute(
            """INSERT INTO jobs (
                title, company, location, description, salary, category, is_active,
                work_type, work_arrangement, salary_min, salary_max, salary_currency,
                search_summary, selling_points, video_url, expires_at, skills,
                employer_id, created_at, posted_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            job,
        )

    skills = [
        ('Python', 'py,python3', 'Development', 90),
        ('JavaScript', 'js,node,nodejs', 'Development', 88),
        ('React', 'reactjs,react.js', 'Development', 85),
        ('Flask', 'flask-api', 'Development', 70),
        ('AWS', 'amazon web services', 'Cloud', 82),
        ('Docker', 'containers', 'DevOps', 80),
        ('Kubernetes', 'k8s', 'DevOps', 78),
        ('SQL', 'sqlite,postgresql,mysql', 'Data', 75),
        ('Machine Learning', 'ml,ai', 'AI/ML', 72),
    ]
    for name, aliases, category, score in skills:
        db.execute(
            'INSERT OR IGNORE INTO skills_taxonomy (name, aliases, category, demand_score) VALUES (?, ?, ?, ?)',
            (name, aliases, category, score),
        )

    db.commit()
    db.close()
    migrate_statuses()
    print(f'Initialized database at {DB_PATH}')


def migrate_statuses() -> None:
    db = sqlite3.connect(DB_PATH)
    db.execute("UPDATE applications SET status='applied' WHERE status='pending'")
    db.execute("UPDATE applications SET status='screening' WHERE status='reviewing'")
    db.commit()
    db.close()


if __name__ == '__main__':
    import sys
    init_db(force='--force' in sys.argv)
