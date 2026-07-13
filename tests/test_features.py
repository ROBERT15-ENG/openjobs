"""v2.5.1 feature tests: date posted, distance, report, messaging, team, bulk, legal."""

from conftest import auth_headers, auth_token


def test_date_posted_on_jobs(client):
    res = client.get('/api/jobs')
    jobs = res.get_json()['jobs']
    assert jobs
    assert jobs[0].get('date_posted')


def test_job_report(client):
    res = client.post('/api/jobs/1/report', json={'reason': 'spam', 'details': 'test'})
    assert res.status_code == 201


def test_admin_list_reports(client):
    client.post('/api/jobs/1/report', json={'reason': 'misleading'})
    token = auth_token(client, 'admin@test.com')
    res = client.get('/api/admin/reports', headers=auth_headers(token))
    assert res.status_code == 200
    assert len(res.get_json()['reports']) >= 1


def test_messaging_flow(client):
    seeker = auth_token(client, 'seeker@test.com')
    client.post('/api/applications', headers=auth_headers(seeker), json={
        'job_id': 1, 'resume_text': 'Python dev', 'auto_cover_letter': True,
    })
    apps = client.get('/api/applications', headers=auth_headers(seeker)).get_json()
    app_id = apps[0]['id']
    start = client.post('/api/conversations', headers=auth_headers(seeker), json={
        'application_id': app_id,
    })
    assert start.status_code == 200
    conv_id = start.get_json()['conversation']['id']
    post = client.post(
        f'/api/conversations/{conv_id}/messages',
        headers=auth_headers(seeker),
        json={'body': 'Hello, I am interested in this role.'},
    )
    assert post.status_code == 201


def test_employer_team_on_register(client):
    res = client.post('/api/auth/register-employer', json={
        'name': 'Acme HR', 'email': 'hr@acme.test', 'password': 'pass123', 'company': 'Acme Corp',
    })
    assert res.status_code == 201
    token = res.get_json()['token']
    team = client.get('/api/employer/team', headers=auth_headers(token))
    assert team.status_code == 200
    members = team.get_json()['members']
    assert len(members) == 1
    assert members[0]['role'] == 'owner'


def test_seeker_withdraw_application(client):
    token = auth_token(client, 'seeker@test.com')
    client.post('/api/applications', headers=auth_headers(token), json={
        'job_id': 1, 'resume_text': 'test resume',
    })
    apps = client.get('/api/applications', headers=auth_headers(token)).get_json()
    app_id = apps[0]['id']
    res = client.patch(
        f'/api/applications/{app_id}',
        headers=auth_headers(token),
        json={'status': 'withdrawn'},
    )
    assert res.status_code == 200
    assert res.get_json()['application']['status'] == 'withdrawn'


def test_admin_bulk_reject(client):
    seeker = auth_token(client, 'seeker@test.com')
    client.post('/api/applications', headers=auth_headers(seeker), json={
        'job_id': 1, 'resume_text': 'bulk test',
    })
    admin = auth_token(client, 'admin@test.com')
    apps = client.get('/api/applications', headers=auth_headers(admin)).get_json()
    app_id = apps[0]['id']
    res = client.post('/api/admin/applications/bulk', headers=auth_headers(admin), json={
        'ids': [app_id], 'status': 'rejected',
    })
    assert res.status_code == 200
    assert res.get_json()['updated'] == 1


def test_cookies_page(client):
    res = client.get('/cookies')
    assert res.status_code == 200
    assert b'Cookie Policy' in res.data


def test_geo_util_distance():
    from geo_util import geocode_location, haversine_km
    lat, lng = geocode_location('Sydney, NSW')
    assert lat is not None
    dist = haversine_km(lat, lng, lat + 0.1, lng)
    assert 0 < dist < 20
