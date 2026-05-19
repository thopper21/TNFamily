def test_home_returns_200_when_authenticated(logged_in_client):
    response = logged_in_client.get('/')
    assert response.status_code == 200


def test_home_contains_welcome(logged_in_client):
    response = logged_in_client.get('/')
    assert b'Welcome' in response.data


def test_home_redirects_unauthenticated_to_login(client):
    response = client.get('/')
    assert response.status_code == 302
    assert '/auth/login' in response.headers['Location']
