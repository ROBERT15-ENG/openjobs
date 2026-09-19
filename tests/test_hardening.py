"""Regression tests for the production-hardening pass.

Each test here corresponds to a defect that was confirmed against the
previous code (see PR description): enumeration, email case handling,
type-unsafe writes, pagination bounds, FK orphans, in-memory logout,
moderation bypass, and the email outbox.
"""

import sqlite3

import pytest
from conftest import auth_headers, auth_token

# --- auth ---------------------------------------------------------------------

def test_forgot_password_response_is_identical_for_known_and_unknown_email(client):
    unknown = client.post('/api/auth/forgot-password', json={'email': 'nobody@test.com'})
    known = client.post('/api/auth/forgot-password', json={'email': 'seeker@test.com'})
    assert unknown.status_code == known.status_code == 200
    assert unknown.get_json() == known.get_json()


def test_email_is_case_insensitive_for_register_and_login(client):
    dup = client.post('/api/auth/register', json={
        'name': 'Dup', 'email': 'Seeker@Test.com', 'password': 'StrongPass1',
    })
    assert dup.status_code == 409

    login = client.post('/api/auth/login', json={'email': 'SEEKER@TEST.COM', 'password': 'pass123'})
    assert login.status_code == 200
    assert login.get_json()['user']['email'] == 'seeker@test.com'


def test_register_stores_lowercased_email(client):
    res = client.post('/api/auth/register', json={
        'name': 'Mixed', 'email': 'Mixed.Case@Example.COM', 'password': 'StrongPass1',
    })
    assert res.status_code == 201
    assert res.get_json()['user']['email'] == 'mixed.case@example.com'


def test_register_rejects_malformed_payload(client):
    assert client.post('/api/auth/register', json={'name': 'x', 'email': 'nope', 'password': 'StrongPass1'}).status_code == 400
    assert client.post('/api/auth/register', json=['not', 'an', 'object']).status_code == 400
    assert client.post('/api/auth/register', json={'name': 'x', 'email': 'a@b.co'}).status_code == 400


def test_reset_token_is_stored_hashed(app, client):
    from email_notifier import SMTP_HOST  # noqa: F401 - ensure module import path works

    client.post('/api/auth/forgot-password', json={'email': 'seeker@test.com'})
    with app.app_context():
        from db import get_db
        row = get_db().execute("SELECT reset_token FROM users WHERE email = 'seeker@test.com'").fetchone()
    assert row['reset_token'] is not None
    assert len(row['reset_token']) == 64  # sha256 hex, not the raw urlsafe token
    # The stored hash must not work as a token
    res = client.post('/api/auth/reset-password', json={'token': row['reset_token'], 'password': 'NewStrong1'})
    assert res.status_code == 400


def test_logout_revokes_token_persistently(app, client):
    token = auth_token(client)
    assert client.get('/api/auth/me', headers=auth_headers(token)).status_code == 200

    assert client.post('/api/auth/logout', headers=auth_headers(token)).status_code == 200
    assert client.get('/api/auth/me', headers=auth_headers(token)).status_code == 401

    # Survives a fresh app instance (new process / other gunicorn worker)
    from app_factory import create_app
    other = create_app({'TESTING': True, 'SECRET_KEY': app.secret_key}).test_client()
    assert other.get('/api/auth/me', headers=auth_headers(token)).status_code == 401

    with app.app_context():
        from db import get_db
        assert get_db().execute('SELECT COUNT(*) FROM revoked_tokens').fetchone()[0] == 1


def test_tokens_carry_jti(app, client):
    import jwt
    token = auth_token(client)
    payload = jwt.decode(token, app.secret_key, algorithms=['HS256'])
    assert payload['jti']
    assert payload['exp'] > payload['iat']


# --- validation ---------------------------------------------------------------

def test_job_patch_rejects_wrong_types(client):
    emp = auth_token(client, 'employer@test.com')
    res = client.patch('/api/jobs/1', headers=auth_headers(emp), json={'salary_min': 'banana'})
    assert res.status_code == 400
    assert 'salary_min' in res.get_json()['error']

    res = client.patch('/api/jobs/1', headers=auth_headers(emp), json={'is_active': 'yes please'})
    assert res.status_code == 400

    # Job is untouched and still listed
    listing = client.get('/api/jobs').get_json()
    assert any(j['id'] == 1 for j in listing['jobs'])


def test_job_patch_coerces_and_validates_range(client):
    emp = auth_token(client, 'employer@test.com')
    res = client.patch('/api/jobs/1', headers=auth_headers(emp), json={'salary_min': '120,000', 'salary_max': 150000})
    assert res.status_code == 200
    assert res.get_json()['job']['salary_min'] == 120000

    res = client.patch('/api/jobs/1', headers=auth_headers(emp), json={'salary_min': 200000})
    assert res.status_code == 400
    assert 'salary_min must be <= salary_max' in res.get_json()['error']

    res = client.patch('/api/jobs/1', headers=auth_headers(emp), json={'is_active': 'false'})
    assert res.status_code == 200
    assert res.get_json()['job']['is_active'] == 0


def test_job_create_rejects_bad_enum_and_url(client):
    emp = auth_token(client, 'employer@test.com')
    base = {'title': 'T', 'company': 'C', 'location': 'Sydney', 'description': 'D'}
    assert client.post('/api/jobs', headers=auth_headers(emp), json={**base, 'work_type': 'gig'}).status_code == 400
    assert client.post('/api/jobs', headers=auth_headers(emp), json={**base, 'video_url': 'javascript:alert(1)'}).status_code == 400
    ok = client.post('/api/jobs', headers=auth_headers(emp), json={**base, 'work_type': 'Contract', 'selling_points': 'a, b'})
    assert ok.status_code == 201
    job = client.get(f"/api/jobs/{ok.get_json()['job_id']}").get_json()
    assert job['work_type'] == 'contract'
    assert job['selling_points'] == '["a", "b"]'


def test_pagination_is_clamped(client):
    res = client.get('/api/jobs?limit=-5&page=0').get_json()
    assert res['pagination'] == {'page': 1, 'limit': 1, 'total': 1, 'pages': 1}
    assert len(res['jobs']) == 1

    res = client.get('/api/jobs?limit=5000').get_json()
    assert res['pagination']['limit'] == 100


def test_profile_patch_rejects_wrong_types(client):
    tok = auth_token(client)
    assert client.patch('/api/user/profile', headers=auth_headers(tok), json={'name': ''}).status_code == 400
    assert client.patch('/api/user/profile', headers=auth_headers(tok), json={'dob': 'yesterday'}).status_code == 400
    ok = client.patch('/api/user/profile', headers=auth_headers(tok), json={'dob': '1990-05-01', 'phone': 123456})
    assert ok.status_code == 200
    assert ok.get_json()['user']['phone'] == '123456'


def test_job_alert_validation(client):
    tok = auth_token(client)
    assert client.post('/api/job_alerts', headers=auth_headers(tok), json={'keyword': ''}).status_code == 400
    assert client.post('/api/job_alerts', headers=auth_headers(tok), json={'keyword': 'py', 'salary_min': 'lots'}).status_code == 400
    ok = client.post('/api/job_alerts', headers=auth_headers(tok), json={'keyword': 'py', 'remote_only': 'true'})
    assert ok.status_code == 201
    assert ok.get_json()['alert']['remote_only'] == 1


def test_save_job_validates_job_exists(client):
    tok = auth_token(client)
    assert client.post('/api/saved_jobs', headers=auth_headers(tok), json={}).status_code == 400
    assert client.post('/api/saved_jobs', headers=auth_headers(tok), json={'job_id': 9999}).status_code == 404
    assert client.post('/api/saved_jobs', headers=auth_headers(tok), json={'job_id': 1}).status_code == 200


# --- moderation / authorization ----------------------------------------------

def test_employer_cannot_reactivate_moderated_job(client):
    admin = auth_token(client, 'admin@test.com')
    emp = auth_token(client, 'employer@test.com')

    res = client.post('/api/admin/jobs/bulk', headers=auth_headers(admin), json={'ids': [1], 'action': 'deactivate'})
    assert res.status_code == 200

    res = client.patch('/api/jobs/1', headers=auth_headers(emp), json={'is_active': True})
    assert res.status_code == 403
    assert client.get('/api/jobs/1').get_json()['is_active'] == 0

    res = client.post('/api/admin/jobs/bulk', headers=auth_headers(admin), json={'ids': [1], 'action': 'reactivate'})
    assert res.status_code == 200
    assert client.get('/api/jobs/1').get_json()['is_active'] == 1


def test_report_deactivation_locks_job(client):
    admin = auth_token(client, 'admin@test.com')
    emp = auth_token(client, 'employer@test.com')
    report = client.post('/api/jobs/1/report', json={'reason': 'spam'})
    assert report.status_code == 201
    report_id = client.get('/api/admin/reports', headers=auth_headers(admin)).get_json()['reports'][0]['id']
    res = client.patch(f'/api/admin/reports/{report_id}', headers=auth_headers(admin),
                       json={'status': 'resolved', 'deactivate_job': True})
    assert res.status_code == 200
    assert client.patch('/api/jobs/1', headers=auth_headers(emp), json={'is_active': 1}).status_code == 403


def test_admin_bulk_delete_actually_deletes_with_dependents(app, client):
    admin = auth_token(client, 'admin@test.com')
    seeker = auth_token(client)
    client.post('/api/applications', headers=auth_headers(seeker), json={'job_id': 1})
    client.post('/api/saved_jobs', headers=auth_headers(seeker), json={'job_id': 1})

    res = client.post('/api/admin/jobs/bulk', headers=auth_headers(admin), json={'ids': [1], 'action': 'delete'})
    assert res.status_code == 200
    assert client.get('/api/jobs/1').status_code == 404
    with app.app_context():
        from db import get_db
        db = get_db()
        assert db.execute('SELECT COUNT(*) FROM applications WHERE job_id = 1').fetchone()[0] == 0
        assert db.execute('SELECT COUNT(*) FROM saved_jobs WHERE job_id = 1').fetchone()[0] == 0
        assert db.execute('PRAGMA foreign_key_check').fetchall() == []


def test_admin_delete_user_leaves_no_orphans(app, client):
    admin = auth_token(client, 'admin@test.com')
    seeker = auth_token(client)
    client.post('/api/applications', headers=auth_headers(seeker), json={'job_id': 1})
    client.post('/api/job_alerts', headers=auth_headers(seeker), json={'keyword': 'python'})
    client.post('/api/saved_jobs', headers=auth_headers(seeker), json={'job_id': 1})
    client.post('/api/jobs/1/report', headers=auth_headers(seeker), json={'reason': 'spam'})

    res = client.delete('/api/admin/users/1', headers=auth_headers(admin))
    assert res.status_code == 200
    with app.app_context():
        from db import get_db
        db = get_db()
        assert db.execute('SELECT COUNT(*) FROM job_alerts WHERE user_id = 1').fetchone()[0] == 0
        assert db.execute('SELECT COUNT(*) FROM applications WHERE user_id = 1').fetchone()[0] == 0
        assert db.execute('SELECT reporter_id FROM job_reports').fetchone()[0] is None
        assert db.execute('PRAGMA foreign_key_check').fetchall() == []


def test_admin_delete_employer_detaches_jobs(app, client):
    admin = auth_token(client, 'admin@test.com')
    res = client.delete('/api/admin/users/2', headers=auth_headers(admin))
    assert res.status_code == 200
    with app.app_context():
        from db import get_db
        job = get_db().execute('SELECT is_active, employer_id FROM jobs WHERE id = 1').fetchone()
    assert job['is_active'] == 0 and job['employer_id'] is None


def test_employer_bulk_status_validates_status(client):
    emp = auth_token(client, 'employer@test.com')
    res = client.post('/api/employer/applications/bulk-status', headers=auth_headers(emp),
                      json={'ids': [1], 'status': 'bogus'})
    assert res.status_code == 400
    res = client.post('/api/employer/applications/bulk-status', headers=auth_headers(emp),
                      json={'ids': 'x', 'status': 'interview'})
    assert res.status_code == 400


def test_checkout_requires_employer_and_own_job(client, monkeypatch):
    monkeypatch.setenv('STRIPE_SECRET_KEY', 'sk_test_x')
    seeker = auth_token(client)
    assert client.post('/api/payment/checkout', headers=auth_headers(seeker), json={'job_id': 1}).status_code == 403
    emp = auth_token(client, 'employer@test.com')
    assert client.post('/api/payment/checkout', headers=auth_headers(emp), json={'job_id': 999}).status_code == 404
    assert client.post('/api/payment/checkout', headers=auth_headers(emp), json={'job_id': 1, 'plan': 'gold'}).status_code == 400


# --- database -----------------------------------------------------------------

def test_connection_pragmas(app):
    with app.app_context():
        from db import get_db
        db = get_db()
        assert db.execute('PRAGMA foreign_keys').fetchone()[0] == 1
        assert db.execute('PRAGMA journal_mode').fetchone()[0].lower() == 'wal'
        assert db.execute('PRAGMA busy_timeout').fetchone()[0] >= 1000


def test_foreign_keys_enforced_on_raw_insert(app):
    with app.app_context():
        from db import get_db
        with pytest.raises(sqlite3.IntegrityError):
            get_db().execute(
                "INSERT INTO applications (job_id, user_id, status, applied_at) VALUES (9999, 1, 'applied', 'x')"
            )


def test_timestamps_are_utc_iso(client):
    emp = auth_token(client, 'employer@test.com')
    job_id = client.post('/api/jobs', headers=auth_headers(emp), json={
        'title': 'T', 'company': 'C', 'location': 'Sydney', 'description': 'D',
    }).get_json()['job_id']
    created = client.get(f'/api/jobs/{job_id}').get_json()['created_at']
    assert created.endswith('Z') and 'T' in created


def test_schema_migrate_lowercases_legacy_emails(tmp_path):
    from db import connect
    from schema_migrate import ensure_schema

    path = str(tmp_path / 'legacy.db')
    conn = connect(path)
    conn.executescript(
        """
        CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT UNIQUE, password_hash TEXT,
                            role TEXT, company TEXT, created_at TEXT);
        CREATE TABLE jobs (id INTEGER PRIMARY KEY, title TEXT, location TEXT, is_active INTEGER,
                           employer_id INTEGER, created_at TEXT);
        CREATE TABLE applications (id INTEGER PRIMARY KEY, job_id INTEGER, user_id INTEGER);
        CREATE TABLE organization_members (organization_id INTEGER, user_id INTEGER, role TEXT, created_at TEXT);
        INSERT INTO users (name, email, role, created_at) VALUES ('A', 'Mixed@Case.com', 'user', 'x');
        INSERT INTO users (name, email, role, created_at) VALUES ('B', 'clash@x.com', 'user', 'x');
        INSERT INTO users (name, email, role, created_at) VALUES ('C', 'CLASH@x.com', 'user', 'x');
        """
    )
    conn.commit()
    ensure_schema(conn)
    emails = {row['name']: row['email'] for row in conn.execute('SELECT name, email FROM users')}
    assert emails['A'] == 'mixed@case.com'
    # Colliding pair is left alone rather than destroyed
    assert {emails['B'], emails['C']} == {'clash@x.com', 'CLASH@x.com'}
    assert conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE name='idx_users_email_nocase'").fetchone()[0] == 0


# --- email outbox -------------------------------------------------------------

def test_send_email_queues_when_configured(app, monkeypatch):
    import email_notifier as en

    monkeypatch.setattr(en, 'SMTP_HOST', 'smtp.example')
    monkeypatch.setattr(en, 'SMTP_USER', 'u')
    monkeypatch.setattr(en, 'SMTP_PASS', 'p')
    monkeypatch.setattr(en, '_drain_in_background', lambda *a, **k: None)

    with app.app_context():
        result = en.send_email('to@x.com', 'Subj', '<b>hi</b>')
        assert result['success'] and result['queued']
        from db import get_db
        row = get_db().execute('SELECT * FROM email_outbox').fetchone()
    assert row['to_email'] == 'to@x.com' and row['status'] == 'pending' and row['attempts'] == 0


def test_drain_outbox_retries_then_fails(app, monkeypatch):
    import email_notifier as en

    monkeypatch.setattr(en, 'MAX_ATTEMPTS', 2)
    with app.app_context():
        en.enqueue_email('a@x.com', 'S', 'B')
        en.enqueue_email('b@x.com', 'S', 'B')

    calls = []

    def flaky(to, subject, html, text):
        calls.append(to)
        return {'success': to == 'a@x.com', 'error': 'boom'}

    with app.app_context():
        first = en.drain_outbox(deliver=flaky)
        assert first == {'sent': 1, 'failed': 1, 'skipped': 0}
        second = en.drain_outbox(deliver=flaky)
        assert second == {'sent': 0, 'failed': 1, 'skipped': 0}
        third = en.drain_outbox(deliver=flaky)
        assert third == {'sent': 0, 'failed': 0, 'skipped': 0}

        from db import get_db
        rows = {r['to_email']: dict(r) for r in get_db().execute('SELECT * FROM email_outbox')}
    assert rows['a@x.com']['status'] == 'sent' and rows['a@x.com']['sent_at']
    assert rows['b@x.com']['status'] == 'failed' and rows['b@x.com']['attempts'] == 2
    assert rows['b@x.com']['last_error'] == 'boom'
    assert calls == ['a@x.com', 'b@x.com', 'b@x.com']


def test_admin_outbox_endpoints(app, client):
    admin = auth_token(client, 'admin@test.com')
    import email_notifier as en
    with app.app_context():
        en.enqueue_email('a@x.com', 'S', 'B')
    status = client.get('/api/admin/email/outbox', headers=auth_headers(admin)).get_json()
    assert status['counts'] == {'pending': 1}
    # SMTP not configured in tests -> drain refuses
    assert client.post('/api/admin/email/drain', headers=auth_headers(admin), json={}).status_code == 503


# --- app plumbing -------------------------------------------------------------

def test_api_404_is_json(client):
    res = client.get('/api/does-not-exist')
    assert res.status_code == 404
    assert res.get_json()['error'] == 'Not Found'


def test_hsts_only_in_production(client, monkeypatch):
    assert 'Strict-Transport-Security' not in client.get('/api/health').headers
    monkeypatch.setenv('FLASK_ENV', 'production')
    monkeypatch.setenv('SECRET_KEY', 'x' * 40)
    from app_factory import create_app
    prod = create_app({'TESTING': True}).test_client()
    assert prod.get('/api/health').headers['Strict-Transport-Security'].startswith('max-age=')


def test_radius_search_uses_bounding_box(client):
    near = client.get('/api/jobs?near=Sydney&radius_km=50').get_json()
    assert near['pagination']['total'] == 1
    assert near['jobs'][0]['distance_km'] == 0.0
    far = client.get('/api/jobs?near=Perth&radius_km=50').get_json()
    assert far['pagination']['total'] == 0
