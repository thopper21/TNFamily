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

### 4. Initialize the database

```bash
flask db upgrade
```

### 5. Run

```bash
python run.py
```

Visit `http://127.0.0.1:5000`. Sign in with an approved Google account.

## Running Tests

```bash
pytest
```

## Database Migrations

Schema changes are managed with Flask-Migrate (Alembic).

```bash
# Apply all pending migrations (run this after pulling schema changes)
flask db upgrade

# Generate a new migration after changing models
flask db migrate -m "description of change"
```

**Upgrading an existing deployment** (including those originally set up with `db.create_all()`):
```bash
flask db upgrade
```
The initial migration detects existing tables and skips creating them, so this is safe to run against any database state.

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `FLASK_ENV` | Yes | `local` or `cloud` |
| `SECRET_KEY` | Yes | Flask session signing key — generate with `secrets.token_hex(32)` |
| `GOOGLE_CLIENT_ID` | Yes | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | Yes | Google OAuth client secret |
| `APPROVED_EMAILS` | Yes | Comma-separated list of allowed email addresses |
| `APP_NAME` | No | App display name (default: `Family Hub`) |
| `CLOUD_SQL_CONNECTION_NAME` | Cloud only | Cloud SQL instance in `project:region:instance` format |
| `DB_USER` | Cloud only | Database username |
| `DB_PASSWORD` | Cloud only | Database password |
| `DB_NAME` | Cloud only | Database name |
| `DATABASE_URL` | Cloud only | Full PostgreSQL URL — fallback if the `DB_*` vars above are not set |

## Project Structure

```
TNFamily/
├── app/
│   ├── __init__.py       # Application factory
│   ├── extensions.py     # Shared Flask extensions (db, login_manager, oauth)
│   ├── models.py         # SQLAlchemy models (User, StoreSection, StapleItem, ShoppingListItem)
│   ├── auth/             # Google OAuth blueprint (/auth/*)
│   ├── home/             # Home page blueprint (/)
│   └── grocery/          # Grocery list blueprint (/grocery/*)
├── templates/            # Jinja2 + Bootstrap 5 templates
├── tests/                # pytest test suite
├── config.py             # Environment-based configuration
├── run.py                # Local dev entry point
└── .env.example          # Environment variable template
```

## Cloud Deployment (Google Cloud Run)

### Prerequisites

- Cloud SQL PostgreSQL instance with a database and user created
- Cloud Run service account granted the **Cloud SQL Client** role (`roles/cloudsql.client`)

### Steps

1. Build and push the Docker image (see `Dockerfile`)
2. Under **Connections → Cloud SQL connections** in your Cloud Run service, add your Cloud SQL instance — this makes the Unix socket available to the container
3. Set the following environment variables in Cloud Run:

   | Variable | Value |
   |---|---|
   | `FLASK_ENV` | `cloud` |
   | `SECRET_KEY` | generated value |
   | `GOOGLE_CLIENT_ID` | your OAuth client ID |
   | `GOOGLE_CLIENT_SECRET` | your OAuth client secret |
   | `APPROVED_EMAILS` | comma-separated email list |
   | `APP_NAME` | `The Achtyes-Hopper Family` |
   | `CLOUD_SQL_CONNECTION_NAME` | `project-id:region:instance-name` |
   | `DB_USER` | database username |
   | `DB_PASSWORD` | database password |
   | `DB_NAME` | database name |

4. Add the Cloud Run service URL to **Authorized redirect URIs** in Google Cloud Console: `https://<your-service>.run.app/auth/callback`

> **Before making schema changes:** integrate [Flask-Migrate](https://flask-migrate.readthedocs.io/) — `db.create_all()` will not apply column additions to existing tables.
