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


def test_kanban_move_rejects_foreign_application(client):
    """Employer A must not move applications that belong to another job."""
    emp = auth_token(client, 'employer@test.com')
    seeker = auth_token(client, 'seeker@test.com')

    job_b = client.post('/api/jobs', headers=auth_headers(emp), json={
        'title': 'Other Role',
        'company': 'Acme',
        'location': 'Sydney',
        'description': 'Second job',
    }).get_json()['job_id']

    apply_a = client.post('/api/applications', headers=auth_headers(seeker), json={'job_id': 1})
    assert apply_a.status_code == 201
    app_on_job_1 = apply_a.get_json()['application_id']

    # Try to move job-1's application via job_b's kanban endpoint
    move = client.post(
        f'/api/kanban/{job_b}/move',
        headers=auth_headers(emp),
        json={'application_id': app_on_job_1, 'stage': 'interview'},
    )
    assert move.status_code == 404

    # Application status unchanged
    apps = client.get('/api/applications', headers=auth_headers(seeker)).get_json()
    target = next(a for a in apps if a['id'] == app_on_job_1)
    assert target['status'] in ('applied', 'pending')


def test_google_auth_requires_client_id(client, monkeypatch):
    monkeypatch.delenv('GOOGLE_CLIENT_ID', raising=False)
    res = client.post('/api/auth/google', json={'token': 'fake-id-token'})
    assert res.status_code == 503
