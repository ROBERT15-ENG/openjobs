"""Security hardening regression tests."""

from conftest import auth_headers, auth_token


def test_json_ld_escapes_script_breakout():
    from seo_util import job_posting_json_ld

    malicious = {
        'id': 1,
        'title': 'Engineer</script><script>alert(1)</script>',
        'company': 'Acme',
        'description': 'desc</script><img onerror=alert(1)>',
        'location': 'Remote',
        'created_at': '2026-01-01',
    }
    raw = job_posting_json_ld(malicious, 'http://localhost:5700')
    assert '</script>' not in raw
    assert '\\u003c' in raw or '<' not in raw


def test_seeker_has_no_employer_id_on_me(client):
    token = auth_token(client, 'seeker@test.com')
    res = client.get('/api/auth/me', headers=auth_headers(token))
    assert res.get_json()['user']['employer_id'] is None


def test_seeker_cannot_set_application_hired(client):
    seeker_token = auth_token(client, 'seeker@test.com')
    apply = client.post('/api/applications', headers=auth_headers(seeker_token), json={'job_id': 1})
    assert apply.status_code == 201
    app_id = apply.get_json()['application_id']

    patch = client.patch(
        f'/api/applications/{app_id}',
        headers=auth_headers(seeker_token),
        json={'status': 'hired'},
    )
    assert patch.status_code == 403


def test_seeker_can_withdraw_application(client):
    seeker_token = auth_token(client, 'seeker@test.com')
    apply = client.post('/api/applications', headers=auth_headers(seeker_token), json={'job_id': 1})
    app_id = apply.get_json()['application_id']

    patch = client.patch(
        f'/api/applications/{app_id}',
        headers=auth_headers(seeker_token),
        json={'status': 'withdrawn'},
    )
    assert patch.status_code == 200
    assert patch.get_json()['application']['status'] == 'withdrawn'


def test_ai_endpoints_require_auth(client):
    res = client.post('/api/ai/ollama/score/resume', json={
        'job_description': 'Python',
        'resume_text': 'Python dev',
    })
    assert res.status_code == 401


def test_security_headers_present(client):
    res = client.get('/api/health')
    assert res.headers.get('X-Content-Type-Options') == 'nosniff'
    assert res.headers.get('X-Frame-Options') == 'SAMEORIGIN'


def test_malicious_job_title_in_json_ld_template(client):
    employer_token = auth_token(client, 'employer@test.com')
    create = client.post('/api/jobs', headers=auth_headers(employer_token), json={
        'title': 'Dev</script><script>alert("xss")</script>',
        'company': 'EvilCo',
        'location': 'Remote',
        'description': 'Normal job',
    })
    job_id = create.get_json()['job_id']
    page = client.get(f'/jobs/{job_id}/dev')
    body = page.get_data(as_text=True)
    assert '<script>alert("xss")</script>' not in body
