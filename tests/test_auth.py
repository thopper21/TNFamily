# tests/test_auth.py
from unittest.mock import patch


def test_login_page_returns_200(client):
    response = client.get('/auth/login')
    assert response.status_code == 200


def test_login_page_contains_google_button(client):
    response = client.get('/auth/login')
    assert b'Sign in with Google' in response.data


def test_google_route_redirects(client):
    with patch('app.auth.routes.oauth') as mock_oauth:
        from flask import redirect
        mock_oauth.google.authorize_redirect.return_value = redirect('https://accounts.google.com/auth')
        response = client.get('/auth/google')
    assert response.status_code == 302


def test_callback_approved_email_redirects_to_home(client):
    mock_userinfo = {
        'sub': 'google-id-001',
        'email': 'approved@example.com',
        'name': 'Approved User',
        'picture': 'https://example.com/pic.jpg',
    }
    with patch('app.auth.routes.oauth') as mock_oauth:
        mock_oauth.google.authorize_access_token.return_value = {'userinfo': mock_userinfo}
        response = client.get('/auth/callback')
    assert response.status_code == 302
    assert response.headers['Location'] == '/'


def test_callback_unapproved_email_returns_403(client):
    mock_userinfo = {
        'sub': 'google-id-002',
        'email': 'stranger@example.com',
        'name': 'Stranger',
        'picture': None,
    }
    with patch('app.auth.routes.oauth') as mock_oauth:
        mock_oauth.google.authorize_access_token.return_value = {'userinfo': mock_userinfo}
        response = client.get('/auth/callback')
    assert response.status_code == 403
    assert b'stranger@example.com' in response.data


def test_callback_approved_email_upserts_name(client, app):
    from app.extensions import db
    from app.models import User

    existing = User(google_id='google-id-003', email='approved@example.com', name='Old Name')
    db.session.add(existing)
    db.session.commit()
    existing_id = existing.id

    mock_userinfo = {
        'sub': 'google-id-003',
        'email': 'approved@example.com',
        'name': 'New Name',
        'picture': 'https://example.com/new.jpg',
    }
    with patch('app.auth.routes.oauth') as mock_oauth:
        mock_oauth.google.authorize_access_token.return_value = {'userinfo': mock_userinfo}
        client.get('/auth/callback')

    updated = db.session.get(User, existing_id)
    assert updated.name == 'New Name'


def test_logout_redirects_to_login(logged_in_client):
    response = logged_in_client.get('/auth/logout')
    assert response.status_code == 302
    assert '/auth/login' in response.headers['Location']


def test_unauthenticated_request_to_home_redirects_to_login(client):
    response = client.get('/')
    assert response.status_code == 302
    assert '/auth/login' in response.headers['Location']
