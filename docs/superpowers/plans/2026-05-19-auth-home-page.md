# The Achtyes-Hopper Family App — Auth & Home Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the project foundation: git setup, Flask app factory, Google OAuth with email allowlist, SQLAlchemy User model, and a Bootstrap home page.

**Architecture:** Application Factory + Blueprints. `app/__init__.py` creates the Flask app and registers `auth` and `home` blueprints. All secrets and config are read from environment variables; `FLASK_ENV` selects between `LocalConfig` (SQLite) and `CloudConfig` (PostgreSQL).

**Tech Stack:** Python 3.11+, Flask 3.x, Flask-Login, Flask-SQLAlchemy, Authlib, python-dotenv, Bootstrap 5 (CDN), pytest

---

## File Map

| File | Purpose |
|---|---|
| `config.py` | Config classes + `parse_approved_emails()` helper |
| `app/__init__.py` | Application factory `create_app(config_override=None)` |
| `app/extensions.py` | Shared `db`, `login_manager`, `oauth` instances |
| `app/models.py` | `User` SQLAlchemy model + Flask-Login `user_loader` |
| `app/auth/__init__.py` | Auth blueprint definition |
| `app/auth/routes.py` | `/auth/login`, `/auth/google`, `/auth/callback`, `/auth/logout` |
| `app/home/__init__.py` | Home blueprint definition |
| `app/home/routes.py` | `/` home page (login-required) |
| `templates/base.html` | Bootstrap shell + navbar block |
| `templates/auth/login.html` | Unauthenticated landing |
| `templates/auth/denied.html` | Access denied page |
| `templates/home/index.html` | Authenticated home page |
| `tests/conftest.py` | pytest fixtures: `app`, `client`, `logged_in_client` |
| `tests/test_config.py` | Config + email parsing tests |
| `tests/test_models.py` | User model tests |
| `tests/test_auth.py` | Auth route tests |
| `tests/test_home.py` | Home route tests |
| `run.py` | Local dev entry point |
| `.env.example` | Environment variable template |
| `.gitignore` | Git ignore patterns |
| `requirements.txt` | Python dependencies |

---

## Task 1: Initialize git and scaffold the project structure

**Files:**
- Create: `.gitignore`
- Create: empty `__init__.py` files throughout `app/` and `tests/`

- [ ] **Step 1: Initialize git**

```bash
git init
```
Expected: `Initialized empty Git repository in .../TNFamily/.git/`

- [ ] **Step 2: Create directory structure**

On Windows PowerShell:
```powershell
New-Item -ItemType Directory -Force app/auth, app/home, templates/auth, templates/home, tests, docs/superpowers/specs, docs/superpowers/plans
New-Item -ItemType File app/__init__.py, app/extensions.py, app/models.py
New-Item -ItemType File app/auth/__init__.py, app/auth/routes.py
New-Item -ItemType File app/home/__init__.py, app/home/routes.py
New-Item -ItemType File tests/__init__.py
```

- [ ] **Step 3: Create .gitignore**

```
.env
__pycache__/
*.pyc
*.pyo
instance/
.pytest_cache/
*.egg-info/
dist/
build/
venv/
.venv/
*.db
.DS_Store
```

- [ ] **Step 4: Commit scaffold**

```bash
git add .gitignore app/ tests/ templates/ docs/
git commit -m "chore: initialize project structure"
```

---

## Task 2: Python dependencies

**Files:**
- Create: `requirements.txt`

- [ ] **Step 1: Create requirements.txt**

```
Flask>=3.0.0
Flask-Login>=0.6.3
Flask-SQLAlchemy>=3.1.1
Authlib>=1.3.1
python-dotenv>=1.0.0
requests>=2.31.0
psycopg2-binary>=2.9.9
pytest>=8.0.0
```

- [ ] **Step 2: Create and activate a virtual environment**

```powershell
python -m venv venv
venv\Scripts\activate
```

- [ ] **Step 3: Install dependencies**

```bash
pip install -r requirements.txt
```

Expected: all packages install. `psycopg2-binary` is only used in cloud; it is safe to ignore build warnings on local dev.

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "chore: add Python dependencies"
```

---

## Task 3: Configuration

**Files:**
- Create: `config.py`
- Create: `tests/conftest.py`
- Create: `tests/test_config.py`

- [ ] **Step 1: Write tests/conftest.py**

```python
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
```

- [ ] **Step 2: Write failing config tests**

```python
# tests/test_config.py
from config import LocalConfig, CloudConfig, config_map, parse_approved_emails


def test_local_config_debug_is_true():
    assert LocalConfig.DEBUG is True


def test_local_config_uses_sqlite():
    assert 'sqlite' in LocalConfig.SQLALCHEMY_DATABASE_URI


def test_cloud_config_debug_is_false():
    assert CloudConfig.DEBUG is False


def test_config_map_contains_local_and_cloud():
    assert 'local' in config_map
    assert 'cloud' in config_map


def test_config_map_local_is_local_config():
    assert config_map['local'] is LocalConfig


def test_config_map_cloud_is_cloud_config():
    assert config_map['cloud'] is CloudConfig


def test_parse_approved_emails_single():
    assert parse_approved_emails('a@b.com') == ['a@b.com']


def test_parse_approved_emails_multiple():
    assert parse_approved_emails('a@b.com,c@d.com') == ['a@b.com', 'c@d.com']


def test_parse_approved_emails_strips_whitespace():
    assert parse_approved_emails('  a@b.com  ,  c@d.com  ') == ['a@b.com', 'c@d.com']


def test_parse_approved_emails_empty_string():
    assert parse_approved_emails('') == []


def test_parse_approved_emails_ignores_blank_entries():
    assert parse_approved_emails('a@b.com,,c@d.com') == ['a@b.com', 'c@d.com']
```

- [ ] **Step 3: Run tests to confirm they fail**

```bash
pytest tests/test_config.py -v
```

Expected: `ModuleNotFoundError: No module named 'config'`

- [ ] **Step 4: Implement config.py**

```python
# config.py
import os


def parse_approved_emails(value: str) -> list:
    return [e.strip() for e in value.split(',') if e.strip()]


class Config:
    APP_NAME = os.environ.get('APP_NAME', 'Family Hub')
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-change-me')
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
    APPROVED_EMAILS = parse_approved_emails(os.environ.get('APPROVED_EMAILS', ''))
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class LocalConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///tnfamily.db'


class CloudConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')


config_map = {
    'local': LocalConfig,
    'cloud': CloudConfig,
}
```

- [ ] **Step 5: Run tests to confirm they pass**

```bash
pytest tests/test_config.py -v
```

Expected: all 11 tests pass.

- [ ] **Step 6: Commit**

```bash
git add config.py tests/conftest.py tests/test_config.py
git commit -m "feat: add configuration with environment variable support"
```

---

## Task 4: Extensions and User model

**Files:**
- Modify: `app/extensions.py`
- Modify: `app/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write failing model tests**

```python
# tests/test_models.py
import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from app.models import User
from app.extensions import db


def test_user_can_be_created(app):
    user = User(google_id='g-1', email='a@b.com', name='Alice')
    db.session.add(user)
    db.session.commit()
    saved = db.session.get(User, user.id)
    assert saved.email == 'a@b.com'
    assert saved.google_id == 'g-1'


def test_created_at_is_set_automatically(app):
    user = User(google_id='g-2', email='b@b.com', name='Bob')
    db.session.add(user)
    db.session.commit()
    assert isinstance(user.created_at, datetime)


def test_profile_picture_is_optional(app):
    user = User(google_id='g-3', email='c@b.com', name='Carol')
    db.session.add(user)
    db.session.commit()
    assert user.profile_picture_url is None


def test_google_id_is_unique(app):
    u1 = User(google_id='same', email='d@b.com', name='Dave')
    u2 = User(google_id='same', email='e@b.com', name='Eve')
    db.session.add(u1)
    db.session.commit()
    db.session.add(u2)
    with pytest.raises(IntegrityError):
        db.session.commit()


def test_user_is_active_by_default(app):
    user = User(google_id='g-4', email='f@b.com', name='Frank')
    db.session.add(user)
    db.session.commit()
    assert user.is_active is True
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_models.py -v
```

Expected: `ImportError` — app modules not yet implemented.

- [ ] **Step 3: Implement app/extensions.py**

```python
# app/extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from authlib.integrations.flask_client import OAuth

db = SQLAlchemy()
login_manager = LoginManager()
oauth = OAuth()
```

- [ ] **Step 4: Implement app/models.py**

```python
# app/models.py
from datetime import datetime
from flask_login import UserMixin
from app.extensions import db, login_manager


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(128), unique=True, nullable=False)
    email = db.Column(db.String(256), unique=True, nullable=False)
    name = db.Column(db.String(256), nullable=False)
    profile_picture_url = db.Column(db.String(512))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))
```

- [ ] **Step 5: Tests still fail** — app factory not yet implemented. That is expected at this step; continue to Task 5.

- [ ] **Step 6: Commit**

```bash
git add app/extensions.py app/models.py tests/test_models.py
git commit -m "feat: add SQLAlchemy extensions and User model"
```

---

## Task 5: Application factory

**Files:**
- Modify: `app/__init__.py`
- Create: `tests/test_app.py`

- [ ] **Step 1: Write failing app factory tests**

```python
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_app.py -v
```

Expected: `ImportError` — `create_app` not defined.

- [ ] **Step 3: Implement app/__init__.py**

```python
# app/__init__.py
import os
from flask import Flask
from config import config_map
from app.extensions import db, login_manager, oauth


def create_app(config_override=None):
    app = Flask(__name__, template_folder='../templates')

    env = os.environ.get('FLASK_ENV', 'local')
    app.config.from_object(config_map.get(env, config_map['local']))
    if config_override:
        app.config.update(config_override)

    db.init_app(app)
    login_manager.init_app(app)
    oauth.init_app(app)

    login_manager.login_view = 'auth.login'

    oauth.register(
        name='google',
        client_id=app.config['GOOGLE_CLIENT_ID'],
        client_secret=app.config['GOOGLE_CLIENT_SECRET'],
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        client_kwargs={'scope': 'openid email profile'},
    )

    from app.auth import auth_bp
    from app.home import home_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(home_bp)

    return app
```

- [ ] **Step 4: Run app and model tests to confirm they pass**

```bash
pytest tests/test_app.py tests/test_models.py -v
```

Expected: all 11 tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/__init__.py tests/test_app.py
git commit -m "feat: add application factory with blueprint registration"
```

---

## Task 6: Auth blueprint

**Files:**
- Modify: `app/auth/__init__.py`
- Modify: `app/auth/routes.py`
- Create: `templates/auth/login.html` (minimal — styled in Task 8)
- Create: `templates/auth/denied.html` (minimal — styled in Task 8)
- Create: `tests/test_auth.py`

- [ ] **Step 1: Write failing auth tests**

```python
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_auth.py -v
```

Expected: multiple failures — blueprints and routes not yet implemented.

- [ ] **Step 3: Implement app/auth/__init__.py**

```python
# app/auth/__init__.py
from flask import Blueprint

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

from app.auth import routes  # noqa: E402, F401
```

- [ ] **Step 4: Implement app/auth/routes.py**

```python
# app/auth/routes.py
from flask import redirect, url_for, render_template, current_app
from flask_login import login_user, logout_user
from app.auth import auth_bp
from app.extensions import db, oauth
from app.models import User


@auth_bp.route('/login')
def login():
    return render_template('auth/login.html')


@auth_bp.route('/google')
def google():
    redirect_uri = url_for('auth.callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@auth_bp.route('/callback')
def callback():
    token = oauth.google.authorize_access_token()
    user_info = token.get('userinfo')
    email = user_info['email']

    if email not in current_app.config.get('APPROVED_EMAILS', []):
        return render_template('auth/denied.html', email=email), 403

    user = User.query.filter_by(google_id=user_info['sub']).first()
    if user is None:
        user = User(
            google_id=user_info['sub'],
            email=email,
            name=user_info['name'],
            profile_picture_url=user_info.get('picture'),
        )
        db.session.add(user)
    else:
        user.name = user_info['name']
        user.profile_picture_url = user_info.get('picture')

    db.session.commit()
    login_user(user)
    return redirect(url_for('home.index'))


@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
```

- [ ] **Step 5: Create minimal auth templates**

Create `templates/auth/login.html`:
```html
<!DOCTYPE html>
<html>
<head><title>Login</title></head>
<body>
  <h1>Sign in</h1>
  <a href="/auth/google">Sign in with Google</a>
</body>
</html>
```

Create `templates/auth/denied.html`:
```html
<!DOCTYPE html>
<html>
<head><title>Access Denied</title></head>
<body>
  <h2>Access Denied</h2>
  <p>{{ email }} is not authorized.</p>
  <a href="/auth/login">Try a different account</a>
</body>
</html>
```

- [ ] **Step 6: Run tests to confirm they pass**

```bash
pytest tests/test_auth.py -v
```

Expected: all 8 tests pass.

- [ ] **Step 7: Commit**

```bash
git add app/auth/ templates/auth/ tests/test_auth.py
git commit -m "feat: add auth blueprint with Google OAuth and email allowlist"
```

---

## Task 7: Home blueprint

**Files:**
- Modify: `app/home/__init__.py`
- Modify: `app/home/routes.py`
- Create: `templates/home/index.html` (minimal — styled in Task 8)
- Create: `tests/test_home.py`

- [ ] **Step 1: Write failing home tests**

```python
# tests/test_home.py
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_home.py -v
```

Expected: failures — home blueprint not yet implemented.

- [ ] **Step 3: Implement app/home/__init__.py**

```python
# app/home/__init__.py
from flask import Blueprint

home_bp = Blueprint('home', __name__)

from app.home import routes  # noqa: E402, F401
```

- [ ] **Step 4: Implement app/home/routes.py**

```python
# app/home/routes.py
from flask import render_template
from flask_login import login_required, current_user
from app.home import home_bp


@home_bp.route('/')
@login_required
def index():
    return render_template('home/index.html', user=current_user)
```

- [ ] **Step 5: Create minimal home template**

Create `templates/home/index.html`:
```html
<!DOCTYPE html>
<html>
<head><title>Home</title></head>
<body>
  <h1>Welcome, {{ user.name }}</h1>
</body>
</html>
```

- [ ] **Step 6: Run full test suite**

```bash
pytest -v
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add app/home/ templates/home/ tests/test_home.py
git commit -m "feat: add home blueprint with login-required protection"
```

---

## Task 8: Bootstrap templates

**Files:**
- Create: `templates/base.html`
- Modify: `templates/auth/login.html`
- Modify: `templates/auth/denied.html`
- Modify: `templates/home/index.html`

No automated tests — verify visually after `run.py` is in place (Task 9).

- [ ] **Step 1: Create templates/base.html**

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{% block title %}{{ config.APP_NAME }}{% endblock %}</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
</head>
<body>
  {% block navbar %}{% endblock %}
  <main class="container mt-4">
    {% block content %}{% endblock %}
  </main>
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
```

- [ ] **Step 2: Replace templates/auth/login.html**

```html
{% extends "base.html" %}
{% block title %}Sign In — {{ config.APP_NAME }}{% endblock %}

{% block content %}
<div class="row justify-content-center mt-5">
  <div class="col-md-4">
    <div class="card shadow-sm">
      <div class="card-body text-center p-5">
        <h1 class="h3 mb-2">{{ config.APP_NAME }}</h1>
        <p class="text-muted mb-4">Your family, organized.</p>
        <a href="{{ url_for('auth.google') }}" class="btn btn-primary btn-lg w-100">
          Sign in with Google
        </a>
      </div>
    </div>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 3: Replace templates/auth/denied.html**

```html
{% extends "base.html" %}
{% block title %}Access Denied — {{ config.APP_NAME }}{% endblock %}

{% block content %}
<div class="row justify-content-center mt-5">
  <div class="col-md-5">
    <div class="card shadow-sm border-danger">
      <div class="card-body text-center p-5">
        <h2 class="h4 mb-3">Access Denied</h2>
        <p class="text-muted">
          <strong>{{ email }}</strong> is not authorized to access this app.
        </p>
        <p class="text-muted mb-4">Please contact a family member to be added.</p>
        <a href="{{ url_for('auth.login') }}" class="btn btn-outline-secondary">
          Try a different account
        </a>
      </div>
    </div>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 4: Replace templates/home/index.html**

```html
{% extends "base.html" %}
{% block title %}Home — {{ config.APP_NAME }}{% endblock %}

{% block navbar %}
<nav class="navbar navbar-expand-md navbar-light bg-light border-bottom">
  <div class="container">
    <a class="navbar-brand fw-bold" href="/">{{ config.APP_NAME }}</a>
    <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navContent">
      <span class="navbar-toggler-icon"></span>
    </button>
    <div class="collapse navbar-collapse" id="navContent">
      <ul class="navbar-nav ms-auto align-items-center">
        <li class="nav-item d-flex align-items-center gap-2 me-2">
          {% if user.profile_picture_url %}
          <img src="{{ user.profile_picture_url }}" class="rounded-circle" width="32" height="32" alt="{{ user.name }}">
          {% endif %}
          <span class="nav-link disabled">{{ user.name }}</span>
        </li>
        <li class="nav-item">
          <a class="nav-link" href="{{ url_for('auth.logout') }}">Sign out</a>
        </li>
      </ul>
    </div>
  </div>
</nav>
{% endblock %}

{% block content %}
<div class="row">
  <div class="col">
    <div class="card shadow-sm">
      <div class="card-body p-4">
        <div class="d-flex align-items-center gap-3">
          {% if user.profile_picture_url %}
          <img src="{{ user.profile_picture_url }}" class="rounded-circle" width="56" height="56" alt="{{ user.name }}">
          {% endif %}
          <div>
            <h2 class="mb-0">Welcome back, {{ user.name }}!</h2>
            <p class="text-muted mb-0">{{ config.APP_NAME }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</div>

<div class="row mt-4">
  <div class="col">
    <p class="text-muted">More features coming soon.</p>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 5: Confirm tests still pass**

```bash
pytest -v
```

Expected: all tests still pass (template changes don't break any assertions).

- [ ] **Step 6: Commit**

```bash
git add templates/
git commit -m "feat: add Bootstrap templates for login, denied, and home pages"
```

---

## Task 9: Entry point, environment setup, and smoke test

**Files:**
- Create: `run.py`
- Create: `.env.example`
- Create: `.env` (local only — not committed)

- [ ] **Step 1: Create run.py**

```python
# run.py
from dotenv import load_dotenv
load_dotenv()

from app import create_app
from app.extensions import db

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=app.config.get('DEBUG', False))
```

- [ ] **Step 2: Create .env.example**

```
FLASK_ENV=local
SECRET_KEY=replace-with-a-random-string
GOOGLE_CLIENT_ID=311367608233-1ejtk8404eladtmir1278ostji0bipq4.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret-here
APPROVED_EMAILS=youremail@gmail.com,another@gmail.com
APP_NAME=The Achtyes-Hopper Family
```

- [ ] **Step 3: Create your local .env**

Copy `.env.example` to `.env` and fill in the real values:
- `SECRET_KEY`: generate with `python -c "import secrets; print(secrets.token_hex(32))"`
- `GOOGLE_CLIENT_SECRET`: retrieve from [Google Cloud Console](https://console.cloud.google.com/) under the OAuth 2.0 credentials for client ID `311367608233-...`
- `APPROVED_EMAILS`: your Gmail address (the one used with Google Sign-In)

Also add `http://127.0.0.1:5000/auth/callback` to the **Authorized redirect URIs** in the Google Cloud Console for this OAuth client.

- [ ] **Step 4: Run the app**

```bash
python run.py
```

Expected output:
```
 * Running on http://127.0.0.1:5000
 * Debug mode: on
```

- [ ] **Step 5: Smoke test in browser**

1. Visit `http://127.0.0.1:5000` — should redirect to `/auth/login`
2. The login page shows "The Achtyes-Hopper Family" and a "Sign in with Google" button
3. Click the button — Google consent screen appears
4. Sign in with an approved email — redirected to home page with your name and profile picture
5. Click "Sign out" — redirected back to login page
6. (Optional) Sign in with a non-approved email — see the Access Denied page

- [ ] **Step 6: Commit**

```bash
git add run.py .env.example
git commit -m "feat: add entry point and environment variable template"
```
