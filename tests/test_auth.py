from conftest import auth_headers, auth_token


def test_register_and_login(client):
    response = client.post('/api/auth/register', json={
        'name': 'New User',
        'email': 'new@test.com',
        'password': 'secret12',
    })
    assert response.status_code == 201
    assert response.get_json()['token']

    login = client.post('/api/auth/login', json={'email': 'new@test.com', 'password': 'secret12'})
    assert login.status_code == 200
    assert login.get_json()['user']['role'] == 'user'


def test_register_ignores_client_role(client):
    response = client.post('/api/auth/register', json={
        'name': 'Hacker',
        'email': 'hack@test.com',
        'password': 'secret12',
        'role': 'admin',
    })
    assert response.status_code == 201
    login = client.post('/api/auth/login', json={'email': 'hack@test.com', 'password': 'secret12'})
    assert login.get_json()['user']['role'] == 'user'


def test_admin_stats_requires_auth(client):
    assert client.get('/api/admin/stats').status_code == 401


def test_admin_stats_requires_admin_role(client):
    token = auth_token(client, 'seeker@test.com')
    response = client.get('/api/admin/stats', headers=auth_headers(token))
    assert response.status_code == 403


def test_admin_stats_ok_for_admin(client):
    token = auth_token(client, 'admin@test.com')
    response = client.get('/api/admin/stats', headers=auth_headers(token))
    assert response.status_code == 200
    assert 'summary' in response.get_json()


def test_me_returns_profile(client):
    token = auth_token(client)
    response = client.get('/api/auth/me', headers=auth_headers(token))
    assert response.status_code == 200
    assert response.get_json()['user']['email'] == 'seeker@test.com'
