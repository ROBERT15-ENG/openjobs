"""Merged ekip + product-gaps attributes."""

from conftest import auth_headers, auth_token


def test_regions_endpoint(client):
    res = client.get('/api/regions')
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True
    assert 'au-syd' in data['regions']


def test_country_and_region_filters(client):
    au = client.get('/api/jobs?country=AU')
    assert au.status_code == 200
    assert au.get_json()['pagination']['total'] >= 1

    syd = client.get('/api/jobs?region=au-syd')
    assert syd.status_code == 200
    assert syd.get_json()['pagination']['total'] >= 1

    sg = client.get('/api/jobs?country=SG')
    assert sg.status_code == 200
    assert sg.get_json()['pagination']['total'] == 0


def test_kyc_profile_update(client):
    token = auth_token(client)
    patch = client.patch('/api/kyc/profile', headers=auth_headers(token), json={
        'country': 'AU',
        'nationality': 'Australian',
        'dob': '1990-01-01',
        'address': '1 Test St Sydney',
    })
    assert patch.status_code == 200
    assert patch.get_json()['kyc_status'] == 'submitted'

    status = client.get('/api/kyc/status', headers=auth_headers(token))
    assert status.status_code == 200
    assert status.get_json()['profile']['country'] == 'AU'


def test_logout_clears_session_cookie(client):
    client.post('/api/auth/login', json={'email': 'seeker@test.com', 'password': 'pass123'})
    assert client.get('/api/auth/me').status_code == 200
    out = client.post('/api/auth/logout')
    assert out.status_code == 200
    assert client.get('/api/auth/me').status_code == 401
