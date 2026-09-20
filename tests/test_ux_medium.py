"""Medium-severity UX fixes: admin moderation surface, operations panel, filters."""

from conftest import auth_headers, auth_token

JOB_PAYLOAD = {
    'title': 'Moderation Target',
    'company': 'ModCo',
    'location': 'Sydney, Australia',
    'description': 'A listing an admin will take down and republish.',
    'category': 'Engineering',
    'work_type': 'full_time',
    'work_arrangement': 'remote',
}


def test_admin_jobs_endpoint_lists_inactive_and_pending_listings(client, app, monkeypatch):
    employer = auth_token(client, 'employer@test.com')
    live = client.post('/api/jobs', headers=auth_headers(employer), json=JOB_PAYLOAD).get_json()['job_id']

    monkeypatch.setenv('STRIPE_SECRET_KEY', 'sk_test_x')
    pending = client.post('/api/jobs', headers=auth_headers(employer), json={**JOB_PAYLOAD, 'title': 'Unpaid'}).get_json()['job_id']
    monkeypatch.delenv('STRIPE_SECRET_KEY')

    admin = auth_token(client, 'admin@test.com')
    res = client.get('/api/admin/jobs', headers=auth_headers(admin))
    assert res.status_code == 200
    by_id = {j['id']: j for j in res.get_json()['jobs']}
    assert by_id[live]['is_active'] == 1 and by_id[live]['moderation_status'] == 'ok'
    assert by_id[pending]['is_active'] == 0 and by_id[pending]['moderation_status'] == 'pending_payment'

    # The public listing still hides the unpaid one.
    public_ids = [j['id'] for j in client.get('/api/jobs?limit=100').get_json()['jobs']]
    assert live in public_ids and pending not in public_ids


def test_admin_jobs_endpoint_requires_admin(client):
    employer = auth_token(client, 'employer@test.com')
    assert client.get('/api/admin/jobs', headers=auth_headers(employer)).status_code == 403
    assert client.get('/api/admin/jobs').status_code in (401, 403)


def test_take_down_then_publish_round_trip(client):
    employer = auth_token(client, 'employer@test.com')
    job_id = client.post('/api/jobs', headers=auth_headers(employer), json=JOB_PAYLOAD).get_json()['job_id']
    admin = auth_token(client, 'admin@test.com')

    res = client.post('/api/admin/jobs/bulk', headers=auth_headers(admin), json={'ids': [job_id], 'action': 'deactivate'})
    assert res.status_code == 200
    row = {j['id']: j for j in client.get('/api/admin/jobs', headers=auth_headers(admin)).get_json()['jobs']}[job_id]
    assert row['is_active'] == 0 and row['moderation_status'] == 'removed'

    # Employer cannot sneak it back on.
    sneaky = client.patch(f'/api/jobs/{job_id}', headers=auth_headers(employer), json={'is_active': True})
    assert sneaky.status_code == 403

    res = client.post('/api/admin/jobs/bulk', headers=auth_headers(admin), json={'ids': [job_id], 'action': 'reactivate'})
    assert res.status_code == 200
    row = {j['id']: j for j in client.get('/api/admin/jobs', headers=auth_headers(admin)).get_json()['jobs']}[job_id]
    assert row['is_active'] == 1 and row['moderation_status'] == 'ok'


def test_outbox_status_and_drain_without_smtp(client, monkeypatch):
    admin = auth_token(client, 'admin@test.com')
    res = client.get('/api/admin/email/outbox', headers=auth_headers(admin))
    assert res.status_code == 200
    body = res.get_json()
    assert 'counts' in body and 'recent_failures' in body

    import email_notifier

    monkeypatch.setattr(email_notifier, 'is_configured', lambda: False)
    res = client.post('/api/admin/email/drain', headers=auth_headers(admin), json={})
    assert res.status_code == 503
    assert res.get_json()['error'] == 'SMTP not configured'


def test_job_alert_dry_run_reports_counts(client):
    admin = auth_token(client, 'admin@test.com')
    res = client.post('/api/admin/job-alerts/run', headers=auth_headers(admin), json={'dry_run': True, 'since_hours': 24})
    assert res.status_code == 200
    body = res.get_json()
    assert body['success'] is True
    assert 'emails_sent' in body and 'jobs_matched' in body


def test_region_filter_matches_region_column(client):
    employer = auth_token(client, 'employer@test.com')
    client.post('/api/jobs', headers=auth_headers(employer), json={**JOB_PAYLOAD, 'title': 'Sydney role', 'region': 'au-syd', 'country': 'AU'})
    client.post('/api/jobs', headers=auth_headers(employer), json={**JOB_PAYLOAD, 'title': 'Singapore role', 'location': 'Singapore', 'region': 'sg', 'country': 'SG'})
    titles = [j['title'] for j in client.get('/api/jobs?region=au-syd&limit=100').get_json()['jobs']]
    assert 'Sydney role' in titles and 'Singapore role' not in titles
    regions = client.get('/api/regions').get_json()['regions']
    assert 'au-syd' in regions and regions['au-syd']['name'] == 'Sydney'


def test_templates_have_no_placeholder_or_prompt_dialogs():
    import pathlib

    root = pathlib.Path(__file__).resolve().parents[1] / 'templates'
    for name in ('admin.html', 'user.html', 'employer.html', 'job.html', 'index.html'):
        text = (root / name).read_text(encoding='utf-8')
        assert 'coming soon' not in text.lower(), name
        assert 'prompt(' not in text, name
    admin = (root / 'admin.html').read_text(encoding='utf-8')
    assert "alert('Settings saved!')" not in admin
    assert '/api/admin/email/outbox' in admin
    index = (root / 'index.html').read_text(encoding='utf-8')
    assert 'filterCountry' not in index and 'filterLocation' not in index
    assert '/api/regions' in index
