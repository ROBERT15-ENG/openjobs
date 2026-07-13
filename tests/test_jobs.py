from conftest import auth_headers, auth_token


def test_list_jobs_public(client):
    response = client.get('/api/jobs')
    assert response.status_code == 200
    data = response.get_json()
    assert 'jobs' in data
    assert len(data['jobs']) >= 1


def test_create_job_requires_auth(client):
    response = client.post('/api/jobs', json={
        'title': 'QA Engineer',
        'company': 'Acme',
        'location': 'Remote',
        'description': 'Testing role',
    })
    assert response.status_code == 401


def test_employer_can_create_job(client):
    token = auth_token(client, 'employer@test.com')
    response = client.post('/api/jobs', headers=auth_headers(token), json={
        'title': 'QA Engineer',
        'company': 'Acme',
        'location': 'Remote',
        'description': 'Testing role',
    })
    assert response.status_code == 201
    assert response.get_json()['job_id']


def test_seeker_cannot_delete_employer_job(client):
    employer_token = auth_token(client, 'employer@test.com')
    create = client.post('/api/jobs', headers=auth_headers(employer_token), json={
        'title': 'Protected Job',
        'company': 'Acme',
        'location': 'Remote',
        'description': 'Only employer should delete',
    })
    job_id = create.get_json()['job_id']

    seeker_token = auth_token(client, 'seeker@test.com')
    delete = client.delete(f'/api/jobs/{job_id}', headers=auth_headers(seeker_token))
    assert delete.status_code == 403
