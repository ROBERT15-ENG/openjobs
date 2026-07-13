from conftest import auth_headers, auth_token


def _create_job(client, employer_token):
    response = client.post('/api/jobs', headers=auth_headers(employer_token), json={
        'title': 'Data Analyst',
        'company': 'Acme',
        'location': 'Sydney',
        'description': 'SQL and Python required',
    })
    return response.get_json()['job_id']


def test_apply_sets_applied_status(client):
    employer_token = auth_token(client, 'employer@test.com')
    job_id = _create_job(client, employer_token)
    seeker_token = auth_token(client, 'seeker@test.com')

    response = client.post('/api/applications', headers=auth_headers(seeker_token), json={'job_id': job_id})
    assert response.status_code == 201

    apps = client.get('/api/applications', headers=auth_headers(seeker_token)).get_json()
    assert apps[0]['status'] == 'applied'


def test_seeker_only_sees_own_applications(client):
    employer_token = auth_token(client, 'employer@test.com')
    job_id = _create_job(client, employer_token)
    seeker_token = auth_token(client, 'seeker@test.com')
    client.post('/api/applications', headers=auth_headers(seeker_token), json={'job_id': job_id})

    apps = client.get('/api/applications', headers=auth_headers(seeker_token)).get_json()
    assert len(apps) == 1
    assert apps[0]['user_id'] == 1


def test_applications_hidden_without_auth(client):
    assert client.get('/api/applications').status_code == 401


def test_legacy_pending_status_normalized_on_update():
    from status import normalize_status
    assert normalize_status('pending') == 'applied'
    assert normalize_status('reviewing') == 'screening'


def test_duplicate_apply_returns_409(client):
    employer_token = auth_token(client, 'employer@test.com')
    job_id = _create_job(client, employer_token)
    seeker_token = auth_token(client, 'seeker@test.com')

    first = client.post('/api/applications', headers=auth_headers(seeker_token), json={'job_id': job_id})
    assert first.status_code == 201

    second = client.post(
        '/api/applications',
        headers=auth_headers(seeker_token),
        json={'job_id': job_id, 'cover_letter': 'Second try'},
    )
    assert second.status_code == 409
    assert 'already applied' in second.get_json()['error'].lower()


def test_apply_stores_cover_letter(client):
    employer_token = auth_token(client, 'employer@test.com')
    job_id = _create_job(client, employer_token)
    seeker_token = auth_token(client, 'seeker@test.com')

    response = client.post(
        '/api/applications',
        headers=auth_headers(seeker_token),
        json={'job_id': job_id, 'cover_letter': 'I am a great fit.'},
    )
    assert response.status_code == 201

    apps = client.get('/api/applications', headers=auth_headers(seeker_token)).get_json()
    assert apps[0]['cover_letter'] == 'I am a great fit.'
