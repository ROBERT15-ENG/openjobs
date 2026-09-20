"""Fixes for the High-severity UX audit findings."""

from conftest import auth_headers, auth_token

JOB_PAYLOAD = {
    'title': 'Platform Engineer',
    'company': 'Acme',
    'location': 'Sydney, NSW',
    'description': 'Build and run the platform. ' * 5,
    'work_type': 'full_time',
    'work_arrangement': 'hybrid',
}


# ── quick apply ───────────────────────────────────────────────────────────────

def test_quick_apply_without_resume_is_refused(client):
    token = auth_token(client, 'seeker@test.com')
    client.patch('/api/user/profile', headers=auth_headers(token), json={'resume_text': ''})
    res = client.post('/api/applications', headers=auth_headers(token), json={'job_id': 1, 'auto_cover_letter': True})
    assert res.status_code == 400
    assert res.get_json()['code'] == 'no_resume'
    # Nothing was written
    assert client.get('/api/applications', headers=auth_headers(token)).get_json() == []


def test_apply_with_own_cover_letter_and_no_resume_still_allowed(client):
    token = auth_token(client, 'seeker@test.com')
    client.patch('/api/user/profile', headers=auth_headers(token), json={'resume_text': ''})
    res = client.post('/api/applications', headers=auth_headers(token), json={
        'job_id': 1, 'cover_letter': 'I have shipped three Flask services in production.',
    })
    assert res.status_code == 201


def test_duplicate_apply_wins_over_no_resume(client):
    token = auth_token(client, 'seeker@test.com')
    assert client.post('/api/applications', headers=auth_headers(token), json={'job_id': 1}).status_code == 201
    client.patch('/api/user/profile', headers=auth_headers(token), json={'resume_text': ''})
    res = client.post('/api/applications', headers=auth_headers(token), json={'job_id': 1, 'auto_cover_letter': True})
    assert res.status_code == 409


# ── profile fields ────────────────────────────────────────────────────────────

def test_profile_preferences_round_trip(client):
    token = auth_token(client, 'seeker@test.com')
    res = client.patch('/api/user/profile', headers=auth_headers(token), json={
        'headline': 'Backend engineer',
        'bio': 'Ten years of Python.',
        'desired_role': 'Staff Engineer',
        'expected_salary': 185000,
        'pref_work_type': 'full_time',
        'pref_remote': 'remote',
    })
    assert res.status_code == 200, res.get_json()
    profile = client.get('/api/user/profile', headers=auth_headers(token)).get_json()
    assert profile['headline'] == 'Backend engineer'
    assert profile['bio'] == 'Ten years of Python.'
    assert profile['desired_role'] == 'Staff Engineer'
    assert profile['expected_salary'] == 185000
    assert profile['pref_work_type'] == 'full_time'
    assert profile['pref_remote'] == 'remote'


def test_profile_preference_enums_validated(client):
    token = auth_token(client, 'seeker@test.com')
    res = client.patch('/api/user/profile', headers=auth_headers(token), json={'pref_remote': 'moon'})
    assert res.status_code == 400
    # Clearing a preference with null is fine
    res = client.patch('/api/user/profile', headers=auth_headers(token), json={'pref_remote': None})
    assert res.status_code == 200


# ── paid listings ─────────────────────────────────────────────────────────────

def test_free_mode_publishes_immediately(client, monkeypatch):
    monkeypatch.delenv('STRIPE_SECRET_KEY', raising=False)
    token = auth_token(client, 'employer@test.com')
    res = client.post('/api/jobs', headers=auth_headers(token), json={**JOB_PAYLOAD, 'plan': 'premium'})
    assert res.status_code == 201
    body = res.get_json()
    assert body['requires_payment'] is False
    assert body['status'] == 'active'
    job = client.get(f"/api/jobs/{body['job_id']}").get_json()
    assert job['is_active'] == 1


def test_paid_mode_holds_listing_until_webhook(client, app, monkeypatch):
    monkeypatch.setenv('STRIPE_SECRET_KEY', 'sk_test_x')
    token = auth_token(client, 'employer@test.com')
    res = client.post('/api/jobs', headers=auth_headers(token), json={**JOB_PAYLOAD, 'plan': 'premium'})
    assert res.status_code == 201
    body = res.get_json()
    assert body['requires_payment'] is True
    assert body['status'] == 'pending_payment'
    job_id = body['job_id']

    # Not public
    listed = client.get('/api/jobs?limit=100').get_json()['jobs']
    assert job_id not in [j['id'] for j in listed]
    assert client.get(f'/jobs/{job_id}').status_code == 404

    # Employer still sees it, marked pending
    dash = client.get('/api/employer/dashboard', headers=auth_headers(token)).get_json()
    mine = [j for j in dash['my_jobs'] if j['id'] == job_id]
    assert mine and mine[0]['moderation_status'] == 'pending_payment' and mine[0]['plan'] == 'premium'
    assert dash['stats']['active_jobs'] == dash['stats']['total_jobs'] - 1

    # Employer cannot flip it live by hand
    res = client.patch(f'/api/jobs/{job_id}', headers=auth_headers(token), json={'is_active': True})
    assert res.status_code == 402

    # Payment confirmation publishes and features it
    from billing import activate_paid_job
    from db import connect
    with app.app_context():
        conn = connect()
        activate_paid_job(conn, job_id, 'premium')
        conn.close()
    job = client.get(f'/api/jobs/{job_id}').get_json()
    assert job['is_active'] == 1 and job['is_featured'] == 1 and job['moderation_status'] == 'ok'
    assert client.get(f'/jobs/{job_id}').status_code == 200


def test_admin_posts_are_live_even_in_paid_mode(client, monkeypatch):
    monkeypatch.setenv('STRIPE_SECRET_KEY', 'sk_test_x')
    token = auth_token(client, 'admin@test.com')
    res = client.post('/api/jobs', headers=auth_headers(token), json=JOB_PAYLOAD)
    assert res.status_code == 201
    assert res.get_json()['requires_payment'] is False


def test_pricing_reports_payment_state(client, monkeypatch):
    monkeypatch.delenv('STRIPE_SECRET_KEY', raising=False)
    assert client.get('/api/pricing').get_json()['payments_enabled'] is False
    monkeypatch.setenv('STRIPE_SECRET_KEY', 'sk_test_x')
    assert client.get('/api/pricing').get_json()['payments_enabled'] is True


# ── error pages ───────────────────────────────────────────────────────────────

def test_html_404_is_branded(client):
    res = client.get('/definitely-not-a-page')
    assert res.status_code == 404
    html = res.get_data(as_text=True)
    assert 'OpenJobs' in html and 'Browse open jobs' in html


def test_missing_job_page_is_branded_404(client):
    res = client.get('/jobs/999999')
    assert res.status_code == 404
    html = res.get_data(as_text=True)
    assert 'Page not found' in html
    assert 'Apply for this Job' not in html


def test_api_404_stays_json(client):
    res = client.get('/api/definitely-not-a-route')
    assert res.status_code == 404
    assert res.is_json
