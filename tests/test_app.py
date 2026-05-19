# tests/test_app.py
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
