# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run all tests
python -m pytest

# Run a single test
python -m pytest tests/test_stores.py::test_add_staple -v

# Run all tests in a file
python -m pytest tests/test_stores.py -v

# Run the dev server
python run.py
```

Tests use in-memory SQLite — no database setup required.

## Architecture

**Application factory** (`app/__init__.py`): `create_app()` builds the Flask app, loads config by `FLASK_ENV` (`local` → SQLite, `cloud` → PostgreSQL via Cloud SQL), and registers blueprints.

**Blueprints:**
- `auth` (`/auth/*`) — Google OAuth via Authlib. Access is gated by `APPROVED_EMAILS` config; only listed addresses can log in.
- `home` (`/`) — Landing page after login; shows shortcut cards for pinned stores.
- `stores` (`/stores/*`) — Multi-store shopping list feature (see below).

**Extensions** (`app/extensions.py`): `db` (SQLAlchemy), `login_manager`, `migrate` (Flask-Migrate), and `oauth` (Authlib) are instantiated here and initialized against the app in the factory. Import from here, not from `flask_sqlalchemy` etc.

**Models** (`app/models.py`): `User`, `Store`, `StoreSection`, `StapleItem`, and `ShoppingListItem` all live in one file.
- `Store.pinned` controls whether a store gets a shortcut card on the home page.
- `StapleItem` has a `shopping_list_item` one-to-one relationship with `cascade='all, delete-orphan'` — deleting a staple automatically deletes its shopping list row.
- `StoreSection` foreign keys use `ondelete='SET NULL'`. SQLite doesn't enforce FK cascades, so `delete_section` manually NULLs `section_id` on related rows before deleting the section.

**Stores blueprint** (`app/stores/routes.py`): Two interaction styles co-exist:
- **Fetch/JSON** for snappy actions: add store, rename store, toggle pin, add staple, toggle staple, add one-off item, toggle list item, add/edit section. Routes accept JSON bodies, return `{'ok': True/False, ...}`.
- **Form POST + redirect** for destructive/infrequent actions: delete staple, delete section, done shopping.

**Templates**: Jinja2 + Bootstrap 5. All Flask URLs in JavaScript are emitted via `url_for(...) | tojson` — never hardcoded. The pattern used in templates:
```javascript
const STORE_BASE = {{ url_for('stores.store_index', store_id=store.id) | tojson }};
// Then: STORE_BASE + 'staples/' + id + '/toggle'
```
Dynamic names in JS strings (e.g. `confirm()` dialogs) use `| tojson`, not `| e`.

**Test fixtures** (`tests/conftest.py`): Three fixtures — `app` (creates in-memory SQLite DB, tears down after each test), `client` (unauthenticated test client), `logged_in_client` (pre-seeds a `User` and sets the Flask-Login session).

## Housekeeping

After any significant change (new blueprint, new models, new routes, schema changes), update `README.md` to reflect the new state — project structure, environment variables, or architecture notes as appropriate.

## Schema notes

- Schema changes are managed with Flask-Migrate (Alembic); see `migrations/`. Generate a migration after changing models with `flask db migrate -m "..."`, and apply with `flask db upgrade`.
