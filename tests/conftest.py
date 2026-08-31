# tests/conftest.py
import pytest


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setenv('GOOGLE_CLIENT_ID', 'test-client-id')
    monkeypatch.setenv('GOOGLE_CLIENT_SECRET', 'test-client-secret')

    from app import create_app
    application = create_app({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SECRET_KEY': 'test-secret-key',
        'GOOGLE_CLIENT_ID': 'test-client-id',
        'GOOGLE_CLIENT_SECRET': 'test-client-secret',
        'APPROVED_EMAILS': ['approved@example.com'],
        'APP_NAME': 'Test Family',
    })

    from app.extensions import db
    with application.app_context():
        db.create_all()
        yield application
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def logged_in_client(app, client):
    from app.extensions import db
    from app.models import User

    user = User(
        google_id='test-google-id',
        email='approved@example.com',
        name='Test User',
        profile_picture_url='https://example.com/pic.jpg',
    )
    db.session.add(user)
    db.session.commit()

    with client.session_transaction() as sess:
        sess['_user_id'] = str(user.id)
        sess['_fresh'] = True

    return client


@pytest.fixture
def store(app):
    from app.extensions import db
    from app.models import Store

    s = Store(name='Test Store')
    db.session.add(s)
    db.session.commit()
    return s
