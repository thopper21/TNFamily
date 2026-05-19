# The Achtyes-Hopper Family

A family utility web app for managing shared household functions — grocery lists, house todos, and more.

## Prerequisites

- Python 3.11+
- A Google Cloud project with OAuth 2.0 credentials ([setup guide](#google-oauth-setup))

## Local Setup

### 1. Clone and create a virtual environment

```bash
git clone <repo-url>
cd TNFamily
python -m venv venv

# Windows
venv\Scripts\activate
# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Google OAuth setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/) → APIs & Services → Credentials
2. Create an **OAuth 2.0 Client ID** (Application type: Web application)
3. Under **Authorized redirect URIs**, add `http://127.0.0.1:5000/auth/callback`
4. Copy the Client ID and Client Secret for the next step

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in the values. Generate a secret key with:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 4. Run

```bash
python run.py
```

Visit `http://127.0.0.1:5000`. Sign in with an approved Google account.

## Running Tests

```bash
pytest
```

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `FLASK_ENV` | Yes | `local` or `cloud` |
| `SECRET_KEY` | Yes | Flask session signing key — generate with `secrets.token_hex(32)` |
| `GOOGLE_CLIENT_ID` | Yes | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Yes | Google OAuth client secret |
| `APPROVED_EMAILS` | Yes | Comma-separated list of allowed email addresses |
| `APP_NAME` | No | App display name (default: `Family Hub`) |
| `DATABASE_URL` | Cloud only | PostgreSQL connection string |

## Project Structure

```
TNFamily/
├── app/
│   ├── __init__.py       # Application factory
│   ├── extensions.py     # Shared Flask extensions (db, login_manager, oauth)
│   ├── models.py         # SQLAlchemy models
│   ├── auth/             # Google OAuth blueprint (/auth/*)
│   └── home/             # Home page blueprint (/)
├── templates/            # Jinja2 + Bootstrap 5 templates
├── tests/                # pytest test suite
├── config.py             # Environment-based configuration
├── run.py                # Local dev entry point
└── .env.example          # Environment variable template
```

## Cloud Deployment (Google Cloud Run)

1. Build and push the Docker image (see `Dockerfile`)
2. Set all environment variables in Cloud Run (same as `.env`, minus `FLASK_ENV` which defaults to `cloud`)
3. Set `DATABASE_URL` to your Cloud SQL PostgreSQL connection string
4. Add the Cloud Run service URL to **Authorized redirect URIs** in Google Cloud Console: `https://<your-service>.run.app/auth/callback`

> **Before making schema changes:** integrate [Flask-Migrate](https://flask-migrate.readthedocs.io/) — `db.create_all()` will not apply column additions to existing tables.
