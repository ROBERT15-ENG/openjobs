"""Phase 4: SEO, growth features, and match scoring tests."""

from conftest import auth_headers, auth_token


def test_companies_directory(client):
    response = client.get('/api/companies/directory')
    assert response.status_code == 200
    data = response.get_json()
    assert 'companies' in data
    assert isinstance(data['companies'], list)


def test_salary_insights(client):
    response = client.get('/api/salary/insights')
    assert response.status_code == 200
    data = response.get_json()
    assert 'by_category' in data
    assert 'by_location' in data


def test_sitemap_xml(client):
    response = client.get('/sitemap.xml')
    assert response.status_code == 200
    assert 'urlset' in response.get_data(as_text=True)


def test_job_seo_url_redirects_legacy(client):
    response = client.get('/job.html?id=1', follow_redirects=False)
    assert response.status_code in (301, 302, 404)


def test_job_alerts_crud(client):
    token = auth_token(client, 'seeker@test.com')
    create = client.post('/api/job_alerts', headers=auth_headers(token), json={
        'keyword': 'Python',
        'location': 'Remote',
        'remote_only': True,
    })
    assert create.status_code == 201
    alert_id = create.get_json()['alert']['id']

    listing = client.get('/api/job_alerts', headers=auth_headers(token))
    assert listing.status_code == 200
    assert any(a['id'] == alert_id for a in listing.get_json()['alerts'])

    pause = client.patch(f'/api/job_alerts/{alert_id}', headers=auth_headers(token), json={'active': 0})
    assert pause.status_code == 200

    delete = client.delete(f'/api/job_alerts/{alert_id}', headers=auth_headers(token))
    assert delete.status_code == 200


def test_jobs_include_match_score_when_authenticated(client):
    employer_token = auth_token(client, 'employer@test.com')
    client.post('/api/jobs', headers=auth_headers(employer_token), json={
        'title': 'Python Developer',
        'company': 'Acme',
        'location': 'Remote',
        'description': 'Python role',
        'skills': 'Python, Flask',
    })
    seeker_token = auth_token(client, 'seeker@test.com')
    client.patch('/api/user/profile', headers=auth_headers(seeker_token), json={
        'skills': 'Python, JavaScript',
    })
    response = client.get('/api/jobs', headers=auth_headers(seeker_token))
    assert response.status_code == 200
    jobs = response.get_json()['jobs']
    assert jobs
    assert 'score' in jobs[0]
    assert 'url' in jobs[0]


def test_apply_sets_ats_score(client):
    employer_token = auth_token(client, 'employer@test.com')
    job = client.post('/api/jobs', headers=auth_headers(employer_token), json={
        'title': 'Python Engineer',
        'company': 'Acme',
        'location': 'Remote',
        'description': 'Need Python',
        'skills': 'Python, Django',
    }).get_json()
    job_id = job['job_id']
    seeker_token = auth_token(client, 'seeker@test.com')
    response = client.post('/api/applications', headers=auth_headers(seeker_token), json={
        'job_id': job_id,
        'resume_text': 'Experienced Python developer with Django and Flask skills.',
    })
    assert response.status_code == 201
    data = response.get_json()
    assert data.get('ats_score', 0) > 0


def test_seo_slugify():
    from seo_util import job_url_path, slugify
    assert slugify('Senior Python Engineer!') == 'senior-python-engineer'
    assert job_url_path(5, 'Data Analyst') == '/jobs/5/data-analyst'
