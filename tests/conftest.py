import os
import sqlite3
import sys

import pytest
from werkzeug.security import generate_password_hash

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
API = os.path.join(ROOT, 'api')
sys.path.insert(0, API)
sys.path.insert(0, ROOT)


def _seed_db(db_path: str) -> None:
    with open(os.path.join(ROOT, 'schema.sql'), encoding='utf-8') as handle:
        schema = handle.read()
    conn = sqlite3.connect(db_path)
    conn.executescript(schema)
    now = '2026-01-01T00:00:00'
    users = [
        ('Seeker', 'seeker@test.com', 'user'),
        ('Employer', 'employer@test.com', 'employer'),
        ('Admin', 'admin@test.com', 'admin'),
    ]
    for name, email, role in users:
        conn.execute(
            'INSERT INTO users (name, email, password_hash, role, created_at) VALUES (?, ?, ?, ?, ?)',
            (name, email, generate_password_hash('pass123'), role, now),
        )
    seeker_id = conn.execute("SELECT id FROM users WHERE email='seeker@test.com'").fetchone()[0]
    conn.execute(
        'UPDATE users SET skills = ?, resume_text = ? WHERE id = ?',
        ('Python, Flask', 'Python developer with Flask API experience.', seeker_id),
    )
    employer_id = conn.execute("SELECT id FROM users WHERE email='employer@test.com'").fetchone()[0]
    conn.execute(
        """INSERT INTO jobs (
            title, company, location, description, salary, category, is_active, created_at, posted_at,
            work_type, work_arrangement, employer_id, latitude, longitude
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            'Backend Engineer', 'Acme', 'Sydney, NSW', 'Python role with visa sponsorship available for eligible candidates', '100k', 'Development', 1, now, now,
            'full_time', 'remote', employer_id, -33.8688, 151.2093,
        ),
    )
    conn.commit()
    conn.close()


@pytest.fixture
def app(tmp_path, monkeypatch):
    db_path = tmp_path / 'test.db'
    _seed_db(str(db_path))
    monkeypatch.setenv('DATABASE_PATH', str(db_path))
    monkeypatch.setenv('SECRET_KEY', 'test-secret-key')
    from app_factory import create_app
    return create_app({'TESTING': True, 'SECRET_KEY': 'test-secret-key'})


@pytest.fixture
def client(app):
    return app.test_client()


def auth_token(client, email='seeker@test.com', password='pass123'):
    response = client.post('/api/auth/login', json={'email': email, 'password': password})
    assert response.status_code == 200
    return response.get_json()['token']


def auth_headers(token):
    return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'}
