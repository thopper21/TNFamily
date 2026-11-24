# tests/test_app.py
import pytest

from app import create_app


def test_app_creates_successfully(app):
    assert app is not None


def test_app_is_in_testing_mode(app):
    assert app.config['TESTING'] is True


def test_auth_blueprint_is_registered(app):
    assert 'auth' in app.blueprints


def test_home_blueprint_is_registered(app):
    assert 'home' in app.blueprints


def test_app_name_in_config(app):
    assert app.config['APP_NAME'] == 'Test Family'


def test_approved_emails_in_config(app):
    assert 'approved@example.com' in app.config['APPROVED_EMAILS']


def test_create_app_raises_when_cloud_env_missing_secret_key(monkeypatch):
    monkeypatch.setenv('FLASK_ENV', 'cloud')
    monkeypatch.delenv('SECRET_KEY', raising=False)

    with pytest.raises(RuntimeError):
        create_app()


def test_create_app_raises_when_cloud_env_uses_default_secret_key(monkeypatch):
    monkeypatch.setenv('FLASK_ENV', 'cloud')

    with pytest.raises(RuntimeError):
        create_app({'SECRET_KEY': 'dev-secret-change-me'})


def test_create_app_does_not_raise_when_cloud_env_has_real_secret_key(monkeypatch):
    monkeypatch.setenv('FLASK_ENV', 'cloud')
    monkeypatch.setenv('GOOGLE_CLIENT_ID', 'test-client-id')
    monkeypatch.setenv('GOOGLE_CLIENT_SECRET', 'test-client-secret')

    created = create_app({
        'SECRET_KEY': 'a-real-production-secret',
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_ENGINE_OPTIONS': {},
    })
    assert created is not None
