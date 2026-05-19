# TNFamily — Auth & Home Page Design

**Date:** 2026-05-19
**Scope:** Project foundation + authentication + home page (Phase 1)

---

## Overview

A family utility web app for managing shared household functions (grocery lists, house todos, etc.). Phase 1 establishes the project foundation: Flask application structure, Google Sign-In authentication with an email allowlist, a SQLAlchemy-backed user model, and a basic home page.

The app is designed to run locally during development and deploy to Google Cloud (e.g., Cloud Run or App Engine) with no code changes — only environment variables differ between environments.

---

## Tech Stack

| Layer | Choice |
|---|---|
| Framework | Python Flask |
| Auth | Google OAuth via Authlib + Flask-Login |
| Database | SQLAlchemy — SQLite (local), PostgreSQL (cloud) |
| Frontend | Bootstrap 5 (CDN) |
| Env config | python-dotenv |

---

## Project Structure

```
TNFamily/
├── app/
│   ├── __init__.py          ← application factory (create_app())
│   ├── extensions.py        ← shared db, login_manager, oauth instances
│   ├── models.py            ← SQLAlchemy User model
│   ├── auth/
│   │   ├── __init__.py      ← auth blueprint registration
│   │   └── routes.py        ← /auth/login, /auth/callback, /auth/logout
│   └── home/
│       ├── __init__.py      ← home blueprint registration
│       └── routes.py        ← / (home page)
├── templates/
│   ├── base.html            ← Bootstrap shell, navbar
│   ├── auth/
│   │   ├── login.html       ← unauthenticated landing page
│   │   └── denied.html      ← access denied page
│   └── home/
│       └── index.html       ← authenticated home page
├── config.py                ← LocalConfig, CloudConfig
├── .env                     ← local secrets (not committed)
├── .gitignore
├── requirements.txt
└── run.py                   ← local dev entry point
```

---

## Configuration

All settings are read from environment variables. The active config class is selected by `FLASK_ENV`.

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `FLASK_ENV` | Yes | `local` or `cloud` |
| `SECRET_KEY` | Yes | Flask session signing key |
| `GOOGLE_CLIENT_ID` | Yes | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Yes | Google OAuth client secret |
| `APPROVED_EMAILS` | Yes | Comma-separated list of allowed email addresses |
| `APP_NAME` | No | Display name (default: `Family Hub`) |
| `DATABASE_URL` | Cloud only | PostgreSQL connection string |

### Config Classes (`config.py`)

```python
class Config:                              # shared base
    APP_NAME = os.environ.get('APP_NAME', 'Family Hub')
    SECRET_KEY = os.environ.get('SECRET_KEY')
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET')
    APPROVED_EMAILS = [e.strip() for e in os.environ.get('APPROVED_EMAILS', '').split(',') if e.strip()]
    SQLALCHEMY_TRACK_MODIFICATIONS = False

class LocalConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///tnfamily.db'

class CloudConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
```

`create_app()` selects the class via:
```python
config_map = {'local': LocalConfig, 'cloud': CloudConfig}
app.config.from_object(config_map.get(os.environ.get('FLASK_ENV', 'local')))
```

### Local `.env` Example

```
FLASK_ENV=local
SECRET_KEY=replace-with-a-random-string
GOOGLE_CLIENT_ID=311367608233-1ejtk8404eladtmir1278ostji0bipq4.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-secret-here
APPROVED_EMAILS=mom@gmail.com,dad@gmail.com
APP_NAME=The Achtyes-Hopper Family
```

---

## Authentication

### Libraries

- **Authlib** — Google OAuth 2.0 flow (redirects, token exchange, user info fetch)
- **Flask-Login** — session management (`current_user`, `@login_required`)

### Flow

```
User visits protected page
        │
        ▼
   Logged in? ──No──▶ Redirect to /auth/login
        │
       Yes
        │
        ▼
   Serve page
```

Google OAuth dance (on "Sign in with Google" click):

```
1. GET  /auth/login      → renders login page with "Sign in with Google" button
2. GET  /auth/google     → redirects to Google consent screen
3.      Google           → user authenticates and consents
4. GET  /auth/callback   → receives auth code from Google
5.      App              → exchanges code for user profile (email, name, picture)
6.      App              → checks email against APPROVED_EMAILS
                              ├─ Not in list → render denied.html
                              └─ In list     → upsert User in DB
7.      Flask-Login      → login_user(user)
8.      Redirect         → to /
```

Logout: `GET /auth/logout` calls `logout_user()` and redirects to `/auth/login`.

### Routes

| Route | Auth required | Description |
|---|---|---|
| `GET /auth/login` | No | Renders login page |
| `GET /auth/google` | No | Initiates Google OAuth redirect |
| `GET /auth/callback` | No | Handles Google OAuth callback |
| `GET /auth/logout` | No | Clears session, redirects to login (no login required — safe to call when not logged in) |
| `GET /` | Yes | Home page |

---

## Database

### User Model

```python
class User(db.Model, UserMixin):
    id                  = db.Column(db.Integer, primary_key=True)
    google_id           = db.Column(db.String(128), unique=True, nullable=False)
    email               = db.Column(db.String(256), unique=True, nullable=False)
    name                = db.Column(db.String(256), nullable=False)
    profile_picture_url = db.Column(db.String(512))
    created_at          = db.Column(db.DateTime, default=datetime.utcnow)
```

No passwords are stored. Google handles all credential management.

Users are upserted on each successful login (creates on first visit, updates name/picture on subsequent visits).

---

## Pages

### Login Page (`/auth/login`)
- Shown to unauthenticated visitors
- Centered Bootstrap card with `APP_NAME` and a tagline
- Single "Sign in with Google" button
- No other content visible to unauthenticated users

### Home Page (`/`)
- Accessible only to authenticated, approved users
- **Navbar**: `APP_NAME` on the left; user profile picture + name + logout link on the right
- **Welcome card**: "Welcome back, [Name]" with Google profile picture
- **Feature grid**: Empty Bootstrap card grid — placeholder for future features (grocery lists, todos, etc.)

### Access Denied Page
- Shown when a Google-authenticated user's email is not in `APPROVED_EMAILS`
- Simple message explaining access is restricted
- Link to sign out and try a different Google account

---

## Cloud Deployment Considerations

- All secrets and config via environment variables — no code changes needed between local and cloud
- `DATABASE_URL` on cloud points to a Google Cloud SQL PostgreSQL instance
- SQLAlchemy abstracts the database difference entirely
- The app is stateless (sessions stored in signed cookies) — compatible with Cloud Run's ephemeral containers
- A `Procfile` or `Dockerfile` will be added when cloud deployment is tackled

---

## Out of Scope (Phase 1)

- Grocery lists, house todos, or any other family features
- Admin UI for managing approved users
- Email notifications
- Mobile-specific UI (basic mobile responsiveness is provided by Bootstrap at no extra cost; dedicated mobile-optimized layouts are out of scope)
- Cloud deployment setup (Dockerfile, CI/CD)
