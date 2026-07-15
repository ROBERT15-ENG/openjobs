"""Product gap fixes: easy apply, visa filter, match tiers, emails."""

from conftest import auth_headers, auth_token


def test_easy_apply_uses_profile_resume(client):
    token = auth_token(client, 'seeker@test.com')
    client.patch('/api/user/profile', headers=auth_headers(token), json={
        'skills': 'Python, Flask',
        'resume_text': 'Senior Python developer with Flask and API experience.',
    })
    res = client.post('/api/applications', headers=auth_headers(token), json={
        'job_id': 1,
        'auto_cover_letter': True,
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data['used_profile_resume'] is True
    assert data['auto_cover_letter'] is True
    assert data['ats_score'] > 0


def test_visa_filter(client):
    res = client.get('/api/jobs?visa=1')
    assert res.status_code == 200
    assert 'jobs' in res.get_json()


def test_match_tier_labels(client):
    token = auth_token(client, 'seeker@test.com')
    client.patch('/api/user/profile', headers=auth_headers(token), json={
        'resume_text': 'Python Flask developer backend APIs',
        'skills': 'Python, Flask',
    })
    res = client.get('/api/jobs', headers=auth_headers(token))
    jobs = res.get_json()['jobs']
    scored = [j for j in jobs if j.get('score')]
    if scored:
        assert scored[0].get('match_tier') in ('ELITE', 'STRONG', 'WATCHLIST', None)


def test_admin_export_applications_csv(client):
    token = auth_token(client, 'admin@test.com')
    res = client.get('/api/admin/export/applications', headers=auth_headers(token))
    assert res.status_code == 200
    assert 'text/csv' in res.content_type
    assert b'applicant' in res.data


def test_match_util_tiers():
    from match_util import match_tier
    assert match_tier(85) == 'ELITE'
    assert match_tier(75) == 'STRONG'
    assert match_tier(55) == 'WATCHLIST'
    assert match_tier(30) is None
