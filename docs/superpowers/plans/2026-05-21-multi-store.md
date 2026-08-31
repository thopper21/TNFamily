# Multi-Store Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the single hardcoded grocery store with a multi-store system where each store has its own aisles, staple items, and shopping list.

**Architecture:** A new `stores` blueprint replaces the `grocery` blueprint. All routes become store-scoped under `/stores/<store_id>/`. A migration seeds a "Grocery" store and re-assigns all existing data to it. The navbar Grocery dropdown becomes a dynamic Stores dropdown via a context processor.

**Tech Stack:** Flask, SQLAlchemy 2.0, Flask-Migrate/Alembic, Bootstrap 5, Jinja2, pytest

## Global Constraints

- All queries use SQLAlchemy 2.0 style: `db.session.scalars(select(...))`, `db.session.scalar(select(...))`, `db.session.execute(...)` — never `Model.query.*`
- All routes are `@login_required`
- Fetch/JSON for snappy actions; form POST + redirect for destructive/infrequent actions
- JS URLs emitted via `url_for(...) | tojson` — never hardcoded strings
- Run `python -m pytest` after every task; all tests must pass before committing
- Tests live in `tests/test_stores.py`; conftest fixtures in `tests/conftest.py`

---

## File Map

**Create:**
- `app/stores/__init__.py` — blueprint definition
- `app/stores/routes.py` — all store-scoped routes
- `migrations/versions/<rev>_add_store_model.py` — migration
- `templates/stores/index.html` — list + add stores
- `templates/stores/home.html` — shopping list management (per store)
- `templates/stores/shop.html` — shop view (per store)
- `templates/stores/manage.html` — rename store + manage aisles
- `tests/test_stores.py` — all tests

**Modify:**
- `app/models.py` — add `Store`; add `store_id` to `StoreSection`, `StapleItem`, `ShoppingListItem`; fix `StoreSection` unique constraint
- `app/__init__.py` — register `stores_bp`, remove `grocery_bp`
- `templates/base.html` — dynamic Stores navbar dropdown
- `tests/conftest.py` — add `store` fixture

**Delete (Task 6):**
- `app/grocery/` (entire directory)
- `templates/grocery/` (entire directory)
- `tests/test_grocery.py`

---

## Task 1: Store model + migration + conftest fixture

**Files:**
- Modify: `app/models.py`
- Create: `migrations/versions/<rev>_add_store_model.py`
- Modify: `tests/conftest.py`
- Create: `tests/test_stores.py`

**Interfaces:**
- Produces: `Store` model with `id`, `name`, `created_at`; `store_id` FK on `StoreSection`, `StapleItem`, `ShoppingListItem`; `store` pytest fixture

- [ ] **Step 1: Write failing model tests**

Create `tests/test_stores.py`:

```python
# tests/test_stores.py
import pytest
from sqlalchemy import func, select, update
from app.models import Store, StoreSection, StapleItem, ShoppingListItem
from app.extensions import db


def test_store_model_has_name(app):
    with app.app_context():
        s = Store(name='Target')
        db.session.add(s)
        db.session.commit()
        assert db.session.get(Store, s.id).name == 'Target'


def test_store_section_belongs_to_store(app, store):
    with app.app_context():
        section = StoreSection(name='Dairy', store_id=store.id)
        db.session.add(section)
        db.session.commit()
        assert db.session.get(StoreSection, section.id).store_id == store.id


def test_staple_item_belongs_to_store(app, store):
    with app.app_context():
        staple = StapleItem(name='Milk', store_id=store.id)
        db.session.add(staple)
        db.session.commit()
        assert db.session.get(StapleItem, staple.id).store_id == store.id


def test_shopping_list_item_belongs_to_store(app, store):
    with app.app_context():
        item = ShoppingListItem(name='Milk', store_id=store.id)
        db.session.add(item)
        db.session.commit()
        assert db.session.get(ShoppingListItem, item.id).store_id == store.id


def test_delete_staple_cascades_to_shopping_list_item(app, store):
    with app.app_context():
        staple = StapleItem(name='Milk', store_id=store.id)
        db.session.add(staple)
        db.session.flush()
        item = ShoppingListItem(name='Milk', staple_item_id=staple.id, store_id=store.id)
        db.session.add(item)
        db.session.commit()
        item_id = item.id
        db.session.delete(staple)
        db.session.commit()
        assert db.session.get(ShoppingListItem, item_id) is None


def test_section_unique_per_store(app, store):
    with app.app_context():
        db.session.add(StoreSection(name='Dairy', store_id=store.id))
        db.session.commit()
        other = Store(name='Other')
        db.session.add(other)
        db.session.commit()
        # Same name in a different store is allowed
        db.session.add(StoreSection(name='Dairy', store_id=other.id))
        db.session.commit()  # must not raise
```

- [ ] **Step 2: Run tests — expect failure**

```
python -m pytest tests/test_stores.py -v
```

Expected: FAIL — `Store` not defined, `store` fixture missing.

- [ ] **Step 3: Update `app/models.py`**

Replace the full file:

```python
# app/models.py
from datetime import datetime, timezone
from flask_login import UserMixin
from app.extensions import db, login_manager


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(128), unique=True, nullable=False)
    email = db.Column(db.String(256), unique=True, nullable=False)
    name = db.Column(db.String(256), nullable=False)
    profile_picture_url = db.Column(db.String(512))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except (ValueError, TypeError):
        return None


class Store(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


class StoreSection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('store.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(128), nullable=False)
    __table_args__ = (db.UniqueConstraint('store_id', 'name', name='uq_store_section_store_name'),)


class StapleItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('store.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(256), nullable=False)
    section_id = db.Column(
        db.Integer, db.ForeignKey('store_section.id', ondelete='SET NULL'), nullable=True
    )
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    section = db.relationship('StoreSection', foreign_keys=[section_id])
    shopping_list_item = db.relationship(
        'ShoppingListItem',
        back_populates='staple',
        uselist=False,
        cascade='all, delete-orphan',
    )


class ShoppingListItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('store.id', ondelete='CASCADE'), nullable=False)
    name = db.Column(db.String(256), nullable=False)
    section_id = db.Column(
        db.Integer, db.ForeignKey('store_section.id', ondelete='SET NULL'), nullable=True
    )
    staple_item_id = db.Column(
        db.Integer, db.ForeignKey('staple_item.id', ondelete='CASCADE'), nullable=True
    )
    checked = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    section = db.relationship('StoreSection', foreign_keys=[section_id])
    staple = db.relationship('StapleItem', back_populates='shopping_list_item')
```

- [ ] **Step 4: Add `store` fixture to `tests/conftest.py`**

Append after the `logged_in_client` fixture:

```python
@pytest.fixture
def store(app):
    from app.models import Store
    from app.extensions import db
    s = Store(name='Test Store')
    db.session.add(s)
    db.session.commit()
    return s
```

- [ ] **Step 5: Run tests — expect pass**

```
python -m pytest tests/test_stores.py -v
```

Expected: 6 PASS. (Existing test_grocery.py still passes — grocery blueprint still registered.)

- [ ] **Step 6: Generate migration skeleton**

```
flask db migrate -m "add store model"
```

Note the generated file path and the `revision` / `down_revision` values at the top. Keep those values; replace the `upgrade()` and `downgrade()` bodies with the code below.

- [ ] **Step 7: Write migration body**

Open the generated file and replace its `upgrade()` and `downgrade()` with:

```python
def upgrade():
    op.create_table(
        'store',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name'),
    )

    conn = op.get_bind()
    conn.execute(sa.text("INSERT INTO store (name) VALUES ('Grocery')"))
    default_id = conn.execute(sa.text("SELECT id FROM store WHERE name = 'Grocery'")).scalar()

    # store_section: add store_id (nullable), backfill, then alter NOT NULL + fix unique constraint
    with op.batch_alter_table('store_section') as batch_op:
        batch_op.add_column(sa.Column('store_id', sa.Integer(), nullable=True))
    conn.execute(sa.text("UPDATE store_section SET store_id = :sid"), {'sid': default_id})
    with op.batch_alter_table('store_section', recreate='always') as batch_op:
        batch_op.alter_column('store_id', existing_type=sa.Integer(), nullable=False)
        batch_op.create_foreign_key('fk_store_section_store_id', 'store', ['store_id'], ['id'])
        batch_op.create_unique_constraint('uq_store_section_store_name', ['store_id', 'name'])

    # staple_item: add store_id (nullable), backfill, alter NOT NULL + FK
    with op.batch_alter_table('staple_item') as batch_op:
        batch_op.add_column(sa.Column('store_id', sa.Integer(), nullable=True))
    conn.execute(sa.text("UPDATE staple_item SET store_id = :sid"), {'sid': default_id})
    with op.batch_alter_table('staple_item') as batch_op:
        batch_op.alter_column('store_id', existing_type=sa.Integer(), nullable=False)
        batch_op.create_foreign_key('fk_staple_item_store_id', 'store', ['store_id'], ['id'])

    # shopping_list_item: add store_id (nullable), backfill, alter NOT NULL + FK
    with op.batch_alter_table('shopping_list_item') as batch_op:
        batch_op.add_column(sa.Column('store_id', sa.Integer(), nullable=True))
    conn.execute(sa.text("UPDATE shopping_list_item SET store_id = :sid"), {'sid': default_id})
    with op.batch_alter_table('shopping_list_item') as batch_op:
        batch_op.alter_column('store_id', existing_type=sa.Integer(), nullable=False)
        batch_op.create_foreign_key('fk_shopping_list_item_store_id', 'store', ['store_id'], ['id'])


def downgrade():
    with op.batch_alter_table('shopping_list_item') as batch_op:
        batch_op.drop_constraint('fk_shopping_list_item_store_id', type_='foreignkey')
        batch_op.drop_column('store_id')
    with op.batch_alter_table('staple_item') as batch_op:
        batch_op.drop_constraint('fk_staple_item_store_id', type_='foreignkey')
        batch_op.drop_column('store_id')
    with op.batch_alter_table('store_section', recreate='always') as batch_op:
        batch_op.drop_constraint('uq_store_section_store_name', type_='unique')
        batch_op.drop_constraint('fk_store_section_store_id', type_='foreignkey')
        batch_op.drop_column('store_id')
        batch_op.create_unique_constraint('uq_store_section_name', ['name'])
    op.drop_table('store')
```

- [ ] **Step 8: Verify migration applies cleanly**

```
flask db upgrade
flask db downgrade
flask db upgrade
```

All three must succeed without error.

- [ ] **Step 9: Run full test suite**

```
python -m pytest -v
```

Expected: all existing tests pass.

- [ ] **Step 10: Commit**

```
git add app/models.py migrations/versions/ tests/conftest.py tests/test_stores.py
git commit -m "feat: add Store model and migration"
```

---

## Task 2: stores blueprint + store list + create + rename

**Files:**
- Create: `app/stores/__init__.py`
- Create: `app/stores/routes.py` (stores_list, create_store, rename_store, inject_all_stores)
- Modify: `app/__init__.py`
- Create: `templates/stores/index.html`
- Modify: `tests/test_stores.py`

**Interfaces:**
- Produces:
  - `GET /stores/` → `stores.stores_list`
  - `POST /stores/` → `stores.create_store` — JSON `{ok, id, name}`
  - `POST /stores/<store_id>/manage/name` → `stores.rename_store` — JSON `{ok, id, name}`
  - Context processor: `all_stores` list available in every template

- [ ] **Step 1: Write failing tests**

Append to `tests/test_stores.py`:

```python
def test_stores_list_requires_login(client):
    resp = client.get('/stores/')
    assert resp.status_code == 302
    assert '/auth/login' in resp.headers['Location']


def test_stores_list_returns_200(logged_in_client):
    resp = logged_in_client.get('/stores/')
    assert resp.status_code == 200


def test_create_store(logged_in_client):
    resp = logged_in_client.post('/stores/', json={'name': 'Target'})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['ok'] is True
    assert data['name'] == 'Target'
    assert 'id' in data


def test_create_duplicate_store_returns_409(logged_in_client, store):
    resp = logged_in_client.post('/stores/', json={'name': store.name})
    assert resp.status_code == 409
    assert resp.get_json()['ok'] is False


def test_create_store_blank_name_returns_400(logged_in_client):
    resp = logged_in_client.post('/stores/', json={'name': '  '})
    assert resp.status_code == 400
    assert resp.get_json()['ok'] is False


def test_rename_store(logged_in_client, store):
    resp = logged_in_client.post(f'/stores/{store.id}/manage/name', json={'name': 'Costco'})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['ok'] is True
    assert data['name'] == 'Costco'


def test_rename_store_duplicate_returns_409(logged_in_client, store, app):
    with app.app_context():
        from app.models import Store
        from app.extensions import db
        other = Store(name='Other Store')
        db.session.add(other)
        db.session.commit()
        other_id = other.id
    resp = logged_in_client.post(f'/stores/{other_id}/manage/name', json={'name': store.name})
    assert resp.status_code == 409


def test_rename_store_not_found_returns_404(logged_in_client):
    resp = logged_in_client.post('/stores/9999/manage/name', json={'name': 'X'})
    assert resp.status_code == 404


def test_stores_appear_in_navbar(logged_in_client, store):
    resp = logged_in_client.get('/stores/')
    assert store.name.encode() in resp.data
```

- [ ] **Step 2: Run tests — expect failure**

```
python -m pytest tests/test_stores.py::test_stores_list_requires_login -v
```

Expected: FAIL — no route `/stores/`.

- [ ] **Step 3: Create `app/stores/__init__.py`**

```python
from flask import Blueprint

stores_bp = Blueprint('stores', __name__, url_prefix='/stores')

from app.stores import routes  # noqa: E402, F401
```

- [ ] **Step 4: Create `app/stores/routes.py`** (stores_list, create_store, rename_store, context processor)

```python
# app/stores/routes.py
from flask import render_template, request, jsonify, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import joinedload
from app.stores import stores_bp
from app.extensions import db
from app.models import Store, StoreSection, StapleItem, ShoppingListItem


def _resolve_section_id(data, store_id):
    section_id = data.get('section_id') or None
    if section_id:
        section = db.session.get(StoreSection, section_id)
        if not section or section.store_id != store_id:
            return None, (jsonify({'ok': False, 'error': 'Section not found'}), 400)
    return section_id, None


@stores_bp.app_context_processor
def inject_all_stores():
    if current_user.is_authenticated:
        stores = db.session.scalars(select(Store).order_by(Store.name)).all()
    else:
        stores = []
    return {'all_stores': stores}


@stores_bp.route('/', methods=['GET'])
@login_required
def stores_list():
    stores = db.session.scalars(select(Store).order_by(Store.name)).all()
    return render_template('stores/index.html', stores=stores)


@stores_bp.route('/', methods=['POST'])
@login_required
def create_store():
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'ok': False, 'error': 'Name is required'}), 400
    if db.session.scalar(select(Store).where(Store.name == name)):
        return jsonify({'ok': False, 'error': 'Store already exists'}), 409
    store = Store(name=name)
    db.session.add(store)
    db.session.commit()
    return jsonify({'ok': True, 'id': store.id, 'name': store.name})


@stores_bp.route('/<int:store_id>/manage/name', methods=['POST'])
@login_required
def rename_store(store_id):
    store = db.session.get(Store, store_id)
    if not store:
        return jsonify({'ok': False, 'error': 'Not found'}), 404
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'ok': False, 'error': 'Name is required'}), 400
    if name != store.name and db.session.scalar(select(Store).where(Store.name == name)):
        return jsonify({'ok': False, 'error': 'Store already exists'}), 409
    store.name = name
    db.session.commit()
    return jsonify({'ok': True, 'id': store.id, 'name': store.name})
```

- [ ] **Step 5: Register stores_bp in `app/__init__.py`**

Add alongside existing grocery registration (keep grocery for now — removed in Task 6):

```python
from app.stores import stores_bp
app.register_blueprint(stores_bp)
```

Full updated imports block in `create_app()`:

```python
from app.auth import auth_bp
from app.home import home_bp
from app.grocery import grocery_bp
from app.stores import stores_bp
app.register_blueprint(auth_bp)
app.register_blueprint(home_bp)
app.register_blueprint(grocery_bp)
app.register_blueprint(stores_bp)
```

- [ ] **Step 6: Create `templates/stores/index.html`**

```html
{% extends "base.html" %}
{% block title %}Stores — {{ config.APP_NAME }}{% endblock %}

{% block content %}
<div class="d-flex justify-content-between align-items-center mb-4">
  <h2 class="mb-0">Stores</h2>
</div>

<div class="row">
  <div class="col-md-6">
    <div class="list-group mb-4">
      {% for store in stores %}
      <a href="{{ url_for('stores.store_index', store_id=store.id) }}"
         class="list-group-item list-group-item-action d-flex justify-content-between align-items-center">
        {{ store.name }}
        <span class="text-muted small">→</span>
      </a>
      {% else %}
      <div class="list-group-item text-muted">No stores yet. Add one below.</div>
      {% endfor %}
    </div>

    <div class="card shadow-sm">
      <div class="card-header"><h5 class="mb-0">Add Store</h5></div>
      <div class="card-body">
        <form id="add-store-form" class="d-flex gap-2">
          <input type="text" id="store-name" class="form-control"
                 placeholder="Store name" required>
          <button type="submit" class="btn btn-primary">Add</button>
        </form>
      </div>
    </div>
  </div>
</div>

{% include 'partials/error_toast.html' %}

<script>
const ADD_STORE_URL = {{ url_for('stores.create_store') | tojson }};
const STORES_BASE = {{ url_for('stores.stores_list') | tojson }};

function showError(msg) {
  document.getElementById('error-toast-body').textContent = msg;
  new bootstrap.Toast(document.getElementById('error-toast')).show();
}

document.getElementById('add-store-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const nameInput = document.getElementById('store-name');
  const name = nameInput.value.trim();
  if (!name) return;
  try {
    const resp = await fetch(ADD_STORE_URL, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({name}),
    });
    const data = await resp.json();
    if (!data.ok) throw new Error(data.error);
    window.location.href = STORES_BASE + data.id + '/';
  } catch (e) {
    showError(e.message || 'Something went wrong');
  }
});
</script>
{% endblock %}
```

- [ ] **Step 7: Run new tests**

```
python -m pytest tests/test_stores.py -v
```

Expected: all 15 store tests pass.

- [ ] **Step 8: Run full suite**

```
python -m pytest -v
```

Expected: all tests pass.

- [ ] **Step 9: Commit**

```
git add app/stores/ app/__init__.py templates/stores/index.html tests/test_stores.py
git commit -m "feat: add stores blueprint with store list and create routes"
```

---

## Task 3: Shopping list management (`/stores/<id>/`)

**Files:**
- Modify: `app/stores/routes.py`
- Create: `templates/stores/home.html`
- Modify: `tests/test_stores.py`

**Interfaces:**
- Consumes: `store` fixture (Task 1), `stores_bp` (Task 2)
- Produces:
  - `GET /stores/<id>/` → `stores.store_index`
  - `POST /stores/<id>/staples` → `stores.add_staple`
  - `POST /stores/<id>/staples/<id>/toggle` → `stores.toggle_staple`
  - `POST /stores/<id>/staples/<id>/delete` → `stores.delete_staple`
  - `POST /stores/<id>/list/add` → `stores.add_to_list`
  - `POST /stores/<id>/list/<id>/delete` → `stores.delete_list_item`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_stores.py`:

```python
def test_store_index_requires_login(client, store):
    resp = client.get(f'/stores/{store.id}/')
    assert resp.status_code == 302
    assert '/auth/login' in resp.headers['Location']


def test_store_index_returns_200(logged_in_client, store):
    resp = logged_in_client.get(f'/stores/{store.id}/')
    assert resp.status_code == 200
    assert store.name.encode() in resp.data


def test_add_staple(logged_in_client, store, app):
    resp = logged_in_client.post(f'/stores/{store.id}/staples', json={'name': 'Eggs'})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['ok'] is True
    assert data['name'] == 'Eggs'
    with app.app_context():
        assert db.session.scalar(
            select(StapleItem).where(StapleItem.name == 'Eggs', StapleItem.store_id == store.id)
        ) is not None


def test_add_staple_missing_name_returns_400(logged_in_client, store):
    resp = logged_in_client.post(f'/stores/{store.id}/staples', json={'name': ''})
    assert resp.status_code == 400
    assert resp.get_json()['ok'] is False


def test_add_staple_invalid_section_returns_400(logged_in_client, store, app):
    with app.app_context():
        from app.models import Store, StoreSection
        other = Store(name='Other')
        db.session.add(other)
        db.session.flush()
        section = StoreSection(name='Dairy', store_id=other.id)
        db.session.add(section)
        db.session.commit()
        section_id = section.id
    resp = logged_in_client.post(f'/stores/{store.id}/staples',
                                 json={'name': 'Milk', 'section_id': section_id})
    assert resp.status_code == 400
    assert resp.get_json()['ok'] is False


def test_toggle_staple_on_creates_shopping_list_item(logged_in_client, store, app):
    with app.app_context():
        staple = StapleItem(name='Milk', store_id=store.id)
        db.session.add(staple)
        db.session.commit()
        staple_id = staple.id
    resp = logged_in_client.post(f'/stores/{store.id}/staples/{staple_id}/toggle')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['ok'] is True
    assert data['on_shopping_list'] is True
    with app.app_context():
        assert db.session.scalar(
            select(ShoppingListItem).where(ShoppingListItem.staple_item_id == staple_id)
        ) is not None


def test_toggle_staple_off_deletes_shopping_list_item(logged_in_client, store, app):
    with app.app_context():
        staple = StapleItem(name='Milk', store_id=store.id)
        db.session.add(staple)
        db.session.flush()
        item = ShoppingListItem(name='Milk', staple_item_id=staple.id, store_id=store.id)
        db.session.add(item)
        db.session.commit()
        staple_id = staple.id
    resp = logged_in_client.post(f'/stores/{store.id}/staples/{staple_id}/toggle')
    assert resp.get_json()['on_shopping_list'] is False
    with app.app_context():
        assert db.session.scalar(
            select(ShoppingListItem).where(ShoppingListItem.staple_item_id == staple_id)
        ) is None


def test_toggle_staple_not_found_returns_404(logged_in_client, store):
    resp = logged_in_client.post(f'/stores/{store.id}/staples/9999/toggle')
    assert resp.status_code == 404


def test_delete_staple(logged_in_client, store, app):
    with app.app_context():
        staple = StapleItem(name='Eggs', store_id=store.id)
        db.session.add(staple)
        db.session.commit()
        staple_id = staple.id
    resp = logged_in_client.post(f'/stores/{store.id}/staples/{staple_id}/delete')
    assert resp.status_code == 302
    with app.app_context():
        assert db.session.get(StapleItem, staple_id) is None


def test_add_one_off_item(logged_in_client, store, app):
    resp = logged_in_client.post(f'/stores/{store.id}/list/add', json={'name': 'Sriracha'})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['ok'] is True
    assert 'shopping_count' in data
    with app.app_context():
        item = db.session.scalar(
            select(ShoppingListItem).where(ShoppingListItem.name == 'Sriracha',
                                           ShoppingListItem.store_id == store.id)
        )
        assert item is not None
        assert item.staple_item_id is None


def test_add_one_off_item_missing_name_returns_400(logged_in_client, store):
    resp = logged_in_client.post(f'/stores/{store.id}/list/add', json={'name': ''})
    assert resp.status_code == 400


def test_delete_list_item(logged_in_client, store, app):
    with app.app_context():
        item = ShoppingListItem(name='Sriracha', store_id=store.id)
        db.session.add(item)
        db.session.commit()
        item_id = item.id
    resp = logged_in_client.post(f'/stores/{store.id}/list/{item_id}/delete')
    assert resp.status_code == 200
    assert resp.get_json()['ok'] is True
    with app.app_context():
        assert db.session.get(ShoppingListItem, item_id) is None


def test_delete_list_item_not_found_returns_404(logged_in_client, store):
    resp = logged_in_client.post(f'/stores/{store.id}/list/9999/delete')
    assert resp.status_code == 404


def test_store_index_shows_ad_hoc_items(logged_in_client, store, app):
    with app.app_context():
        db.session.add(ShoppingListItem(name='Sriracha', store_id=store.id))
        db.session.commit()
    resp = logged_in_client.get(f'/stores/{store.id}/')
    assert b'Sriracha' in resp.data


def test_staple_list_items_have_data_name_attribute(logged_in_client, store, app):
    with app.app_context():
        db.session.add(StapleItem(name='Milk', store_id=store.id))
        db.session.commit()
    resp = logged_in_client.get(f'/stores/{store.id}/')
    assert b'data-name="Milk"' in resp.data


def test_staple_on_list_shows_badge(logged_in_client, store, app):
    with app.app_context():
        staple = StapleItem(name='Milk', store_id=store.id)
        db.session.add(staple)
        db.session.flush()
        db.session.add(ShoppingListItem(name='Milk', staple_item_id=staple.id, store_id=store.id))
        db.session.commit()
    resp = logged_in_client.get(f'/stores/{store.id}/')
    assert b'On list' in resp.data


def test_error_toast_present_on_store_pages(logged_in_client, store):
    for path in [f'/stores/{store.id}/', f'/stores/{store.id}/shop', f'/stores/{store.id}/manage']:
        resp = logged_in_client.get(path)
        count = resp.data.count(b'id="error-toast"')
        assert count == 1, f"Expected 1 error toast on {path}, got {count}"
```

- [ ] **Step 2: Run tests — expect failure**

```
python -m pytest tests/test_stores.py::test_store_index_returns_200 -v
```

Expected: FAIL — no route `/stores/<id>/`.

- [ ] **Step 3: Add routes to `app/stores/routes.py`**

Append after `rename_store`:

```python
@stores_bp.route('/<int:store_id>/')
@login_required
def store_index(store_id):
    store = db.session.get(Store, store_id)
    if not store:
        return redirect(url_for('stores.stores_list'))
    staples = (
        db.session.scalars(
            select(StapleItem)
            .where(StapleItem.store_id == store_id)
            .options(joinedload(StapleItem.shopping_list_item))
            .order_by(StapleItem.name)
        ).unique().all()
    )
    staples.sort(key=lambda s: s.shopping_list_item is not None)
    sections = db.session.scalars(
        select(StoreSection)
        .where(StoreSection.store_id == store_id)
        .order_by(StoreSection.name)
    ).all()
    shopping_count = db.session.scalar(
        select(func.count()).select_from(ShoppingListItem)
        .where(ShoppingListItem.store_id == store_id)
    )
    ad_hoc_items = db.session.scalars(
        select(ShoppingListItem)
        .where(ShoppingListItem.store_id == store_id,
               ShoppingListItem.staple_item_id == None)  # noqa: E711
        .order_by(ShoppingListItem.created_at.desc())
    ).all()
    return render_template('stores/home.html', store=store, staples=staples,
                           sections=sections, shopping_count=shopping_count,
                           ad_hoc_items=ad_hoc_items)


@stores_bp.route('/<int:store_id>/staples', methods=['POST'])
@login_required
def add_staple(store_id):
    store = db.session.get(Store, store_id)
    if not store:
        return jsonify({'ok': False, 'error': 'Not found'}), 404
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'ok': False, 'error': 'Name is required'}), 400
    section_id, err = _resolve_section_id(data, store_id)
    if err:
        return err
    staple = StapleItem(name=name, section_id=section_id, store_id=store_id)
    db.session.add(staple)
    db.session.commit()
    return jsonify({
        'ok': True,
        'id': staple.id,
        'name': staple.name,
        'section_id': staple.section_id,
        'section_name': staple.section.name if staple.section else None,
        'on_shopping_list': staple.shopping_list_item is not None,
    })


@stores_bp.route('/<int:store_id>/staples/<int:staple_id>/toggle', methods=['POST'])
@login_required
def toggle_staple(store_id, staple_id):
    staple = db.session.get(StapleItem, staple_id)
    if not staple or staple.store_id != store_id:
        return jsonify({'ok': False, 'error': 'Not found'}), 404
    if staple.shopping_list_item:
        db.session.delete(staple.shopping_list_item)
    else:
        db.session.add(ShoppingListItem(
            name=staple.name, section_id=staple.section_id,
            staple_item_id=staple.id, store_id=store_id,
        ))
    db.session.commit()
    shopping_count = db.session.scalar(
        select(func.count()).select_from(ShoppingListItem)
        .where(ShoppingListItem.store_id == store_id)
    )
    return jsonify({
        'ok': True,
        'on_shopping_list': staple.shopping_list_item is not None,
        'shopping_count': shopping_count,
    })


@stores_bp.route('/<int:store_id>/staples/<int:staple_id>/delete', methods=['POST'])
@login_required
def delete_staple(store_id, staple_id):
    staple = db.session.get(StapleItem, staple_id)
    if staple and staple.store_id == store_id:
        db.session.delete(staple)
        db.session.commit()
    return redirect(url_for('stores.store_index', store_id=store_id))


@stores_bp.route('/<int:store_id>/list/add', methods=['POST'])
@login_required
def add_to_list(store_id):
    store = db.session.get(Store, store_id)
    if not store:
        return jsonify({'ok': False, 'error': 'Not found'}), 404
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'ok': False, 'error': 'Name is required'}), 400
    section_id, err = _resolve_section_id(data, store_id)
    if err:
        return err
    item = ShoppingListItem(name=name, section_id=section_id, store_id=store_id)
    db.session.add(item)
    db.session.commit()
    shopping_count = db.session.scalar(
        select(func.count()).select_from(ShoppingListItem)
        .where(ShoppingListItem.store_id == store_id)
    )
    return jsonify({'ok': True, 'id': item.id, 'shopping_count': shopping_count})


@stores_bp.route('/<int:store_id>/list/<int:item_id>/delete', methods=['POST'])
@login_required
def delete_list_item(store_id, item_id):
    item = db.session.get(ShoppingListItem, item_id)
    if not item or item.store_id != store_id:
        return jsonify({'ok': False, 'error': 'Not found'}), 404
    db.session.delete(item)
    db.session.commit()
    shopping_count = db.session.scalar(
        select(func.count()).select_from(ShoppingListItem)
        .where(ShoppingListItem.store_id == store_id)
    )
    return jsonify({'ok': True, 'shopping_count': shopping_count})
```

- [ ] **Step 4: Create `templates/stores/home.html`**

```html
{% extends "base.html" %}
{% block title %}{{ store.name }} — {{ config.APP_NAME }}{% endblock %}

{% block content %}
<h2 class="mb-4">{{ store.name }}</h2>

<div class="row">
  <!-- Staples panel -->
  <div class="col-md-6 mb-4">
    <div class="card shadow-sm h-100">
      <div class="card-header d-flex justify-content-between align-items-center">
        <h5 class="mb-0">Staples</h5>
        <div class="d-flex gap-2 align-items-center">
          <div class="btn-group btn-group-sm" role="group" aria-label="Sort order">
            <button type="button" id="sort-az" class="btn btn-outline-secondary active" onclick="setSortMode('az')">A–Z</button>
            <button type="button" id="sort-section" class="btn btn-outline-secondary" onclick="setSortMode('section')">By section</button>
          </div>
          <a href="{{ url_for('stores.store_manage', store_id=store.id) }}" class="btn btn-sm btn-outline-secondary">Manage</a>
        </div>
      </div>
      <div class="card-body p-0">
        <ul class="list-group list-group-flush" id="staples-list">
          {% for staple in staples %}
          <li class="list-group-item d-flex align-items-center gap-2"
              id="staple-{{ staple.id }}"
              data-name="{{ staple.name }}"
              data-section="{{ staple.section.name if staple.section else '' }}">
            <input type="checkbox" class="form-check-input flex-shrink-0"
                   {% if staple.shopping_list_item %}checked{% endif %}
                   onchange="toggleStaple({{ staple.id }}, this)">
            <span class="flex-grow-1">{{ staple.name }}</span>
            {% if staple.shopping_list_item %}
            <span class="badge bg-success staple-on-list-badge">On list</span>
            {% endif %}
            {% if staple.section %}
            <span class="badge bg-secondary">{{ staple.section.name }}</span>
            {% endif %}
            <form method="post" action="{{ url_for('stores.delete_staple', store_id=store.id, staple_id=staple.id) }}"
                  onsubmit="return confirm('Delete ' + {{ staple.name | tojson }} + '?')">
              <button type="submit" class="btn btn-sm btn-outline-danger py-0">×</button>
            </form>
          </li>
          {% endfor %}
        </ul>
      </div>
      <div class="card-footer">
        <form id="add-staple-form" class="d-flex gap-2 flex-wrap">
          <input type="text" id="staple-name" class="form-control form-control-sm"
                 placeholder="Item name" required>
          <select id="staple-section" class="form-select form-select-sm" style="max-width:160px">
            <option value="">No section</option>
            {% for section in sections %}
            <option value="{{ section.id }}">{{ section.name }}</option>
            {% endfor %}
          </select>
          <button type="submit" class="btn btn-sm btn-primary">Add</button>
        </form>
      </div>
    </div>
  </div>

  <!-- Add to list panel -->
  <div class="col-md-6 mb-4">
    <div class="card shadow-sm h-100">
      <div class="card-header">
        <h5 class="mb-0">Add to list</h5>
      </div>
      <div class="card-body">
        <form id="add-list-form" class="d-flex gap-2 flex-wrap mb-3">
          <input type="text" id="list-item-name" class="form-control"
                 placeholder="Item name" required>
          <select id="list-item-section" class="form-select" style="max-width:160px">
            <option value="">No section</option>
            {% for section in sections %}
            <option value="{{ section.id }}">{{ section.name }}</option>
            {% endfor %}
          </select>
          <button type="submit" class="btn btn-primary">Add to list</button>
        </form>
        <div class="d-flex align-items-center gap-3 flex-wrap mb-2">
          <span class="badge bg-primary fs-6" id="shopping-count">
            {{ shopping_count }} item{{ 's' if shopping_count != 1 else '' }} on your list
          </span>
          <a href="{{ url_for('stores.store_shop', store_id=store.id) }}" class="btn btn-success">Start Shopping →</a>
        </div>
        {% if ad_hoc_items %}
        <ul class="list-group list-group-flush" id="ad-hoc-list">
          {% for item in ad_hoc_items %}
          <li class="list-group-item d-flex justify-content-between align-items-center py-1 px-0 border-0 text-muted small"
              id="ad-hoc-{{ item.id }}">
            <span>{{ item.name }}{% if item.section %} <span class="badge bg-light text-secondary fw-normal">{{ item.section.name }}</span>{% endif %}</span>
            <button class="btn btn-link btn-sm text-muted p-0 ms-2 lh-1"
                    onclick="deleteAdHocItem({{ item.id }}, this)">×</button>
          </li>
          {% endfor %}
        </ul>
        {% else %}
        <ul class="list-group list-group-flush" id="ad-hoc-list"></ul>
        {% endif %}
      </div>
    </div>
  </div>
</div>

{% include 'partials/error_toast.html' %}

<script>
const STORE_BASE = {{ url_for('stores.store_index', store_id=store.id) | tojson }};
const ADD_STAPLE_URL = {{ url_for('stores.add_staple', store_id=store.id) | tojson }};
const ADD_TO_LIST_URL = {{ url_for('stores.add_to_list', store_id=store.id) | tojson }};

function toggleStapleUrl(id) { return STORE_BASE + 'staples/' + id + '/toggle'; }
function deleteStapleUrl(id) { return STORE_BASE + 'staples/' + id + '/delete'; }
function deleteListItemUrl(id) { return STORE_BASE + 'list/' + id + '/delete'; }

function showError(msg) {
  document.getElementById('error-toast-body').textContent = msg;
  new bootstrap.Toast(document.getElementById('error-toast')).show();
}

function updateShoppingCount(count) {
  document.getElementById('shopping-count').textContent =
    count + ' item' + (count !== 1 ? 's' : '') + ' on your list';
}

let currentSortMode = 'az';

function sortKey(li) {
  const checked = li.querySelector('input[type="checkbox"]').checked ? 1 : 0;
  const name = li.dataset.name.toLowerCase();
  const section = li.dataset.section.toLowerCase();
  if (currentSortMode === 'section') {
    return [checked, section || '￿', name];
  }
  return [checked, name];
}

function applySortToList() {
  const list = document.getElementById('staples-list');
  const items = Array.from(list.querySelectorAll('li'));
  items.sort((a, b) => {
    const ka = sortKey(a), kb = sortKey(b);
    for (let i = 0; i < ka.length; i++) {
      if (ka[i] < kb[i]) return -1;
      if (ka[i] > kb[i]) return 1;
    }
    return 0;
  });
  items.forEach(li => list.appendChild(li));
}

function setSortMode(mode) {
  currentSortMode = mode;
  document.getElementById('sort-az').classList.toggle('active', mode === 'az');
  document.getElementById('sort-section').classList.toggle('active', mode === 'section');
  applySortToList();
}

async function toggleStaple(stapleId, checkbox) {
  const row = document.getElementById('staple-' + stapleId);
  const wasChecked = !checkbox.checked;
  try {
    const resp = await fetch(toggleStapleUrl(stapleId), {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
    });
    const data = await resp.json();
    if (!data.ok) throw new Error(data.error);
    let badge = row.querySelector('.staple-on-list-badge');
    if (data.on_shopping_list) {
      if (!badge) {
        badge = document.createElement('span');
        badge.className = 'badge bg-success staple-on-list-badge';
        badge.textContent = 'On list';
        row.querySelector('span.flex-grow-1').insertAdjacentElement('afterend', badge);
      }
      checkbox.checked = true;
    } else {
      if (badge) badge.remove();
      checkbox.checked = false;
    }
    applySortToList();
    updateShoppingCount(data.shopping_count);
  } catch (e) {
    checkbox.checked = wasChecked;
    showError(e.message || 'Something went wrong');
  }
}

document.getElementById('add-staple-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const nameInput = document.getElementById('staple-name');
  const sectionSelect = document.getElementById('staple-section');
  const name = nameInput.value.trim();
  if (!name) return;
  try {
    const resp = await fetch(ADD_STAPLE_URL, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({name, section_id: sectionSelect.value || null}),
    });
    const data = await resp.json();
    if (!data.ok) throw new Error(data.error);
    const li = document.createElement('li');
    li.className = 'list-group-item d-flex align-items-center gap-2';
    li.id = 'staple-' + data.id;
    li.dataset.name = data.name;
    li.dataset.section = data.section_name || '';
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.className = 'form-check-input flex-shrink-0';
    checkbox.addEventListener('change', () => toggleStaple(data.id, checkbox));
    const nameSpan = document.createElement('span');
    nameSpan.className = 'flex-grow-1';
    nameSpan.textContent = data.name;
    li.appendChild(checkbox);
    li.appendChild(nameSpan);
    if (data.section_name) {
      const badge = document.createElement('span');
      badge.className = 'badge bg-secondary';
      badge.textContent = data.section_name;
      li.appendChild(badge);
    }
    const delForm = document.createElement('form');
    delForm.method = 'post';
    delForm.action = deleteStapleUrl(data.id);
    delForm.addEventListener('submit', (ev) => {
      if (!confirm('Delete ' + data.name + '?')) ev.preventDefault();
    });
    const delBtn = document.createElement('button');
    delBtn.type = 'submit';
    delBtn.className = 'btn btn-sm btn-outline-danger py-0';
    delBtn.textContent = '×';
    delForm.appendChild(delBtn);
    li.appendChild(delForm);
    document.getElementById('staples-list').appendChild(li);
    applySortToList();
    nameInput.value = '';
  } catch (e) {
    showError(e.message || 'Something went wrong');
  }
});

async function deleteAdHocItem(itemId, btn) {
  try {
    const resp = await fetch(deleteListItemUrl(itemId), {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
    });
    const data = await resp.json();
    if (!data.ok) throw new Error(data.error);
    document.getElementById('ad-hoc-' + itemId).remove();
    updateShoppingCount(data.shopping_count);
  } catch (e) {
    showError(e.message || 'Something went wrong');
  }
}

document.getElementById('add-list-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const nameInput = document.getElementById('list-item-name');
  const sectionSelect = document.getElementById('list-item-section');
  const name = nameInput.value.trim();
  if (!name) return;
  const sectionId = sectionSelect.value || null;
  const sectionText = sectionSelect.options[sectionSelect.selectedIndex].text;
  try {
    const resp = await fetch(ADD_TO_LIST_URL, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({name, section_id: sectionId}),
    });
    const data = await resp.json();
    if (!data.ok) throw new Error(data.error);
    updateShoppingCount(data.shopping_count);
    const li = document.createElement('li');
    li.className = 'list-group-item d-flex justify-content-between align-items-center py-1 px-0 border-0 text-muted small';
    li.id = 'ad-hoc-' + data.id;
    const nameSpan = document.createElement('span');
    nameSpan.textContent = name;
    if (sectionId) {
      const badge = document.createElement('span');
      badge.className = 'badge bg-light text-secondary fw-normal ms-1';
      badge.textContent = sectionText;
      nameSpan.appendChild(badge);
    }
    const delBtn = document.createElement('button');
    delBtn.className = 'btn btn-link btn-sm text-muted p-0 ms-2 lh-1';
    delBtn.textContent = '×';
    delBtn.onclick = () => deleteAdHocItem(data.id, delBtn);
    li.appendChild(nameSpan);
    li.appendChild(delBtn);
    document.getElementById('ad-hoc-list').prepend(li);
    nameInput.value = '';
    sectionSelect.value = '';
  } catch (e) {
    showError(e.message || 'Something went wrong');
  }
});
</script>
{% endblock %}
```

- [ ] **Step 5: Run new tests**

```
python -m pytest tests/test_stores.py -v
```

Expected: all store tests pass (error toast test will fail until Task 5 adds `/manage`; that's OK — it's tested together in Task 5).

- [ ] **Step 6: Run full suite**

```
python -m pytest -v
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```
git add app/stores/routes.py templates/stores/home.html tests/test_stores.py
git commit -m "feat: add store shopping list management routes and template"
```

---

## Task 4: Shop view (`/stores/<id>/shop`)

**Files:**
- Modify: `app/stores/routes.py`
- Create: `templates/stores/shop.html`
- Modify: `tests/test_stores.py`

**Interfaces:**
- Produces:
  - `GET /stores/<id>/shop` → `stores.store_shop`
  - `POST /stores/<id>/list/<id>/toggle` → `stores.toggle_list_item`
  - `POST /stores/<id>/list/done` → `stores.done_shopping`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_stores.py`:

```python
def test_store_shop_requires_login(client, store):
    resp = client.get(f'/stores/{store.id}/shop')
    assert resp.status_code == 302
    assert '/auth/login' in resp.headers['Location']


def test_shop_view_returns_200(logged_in_client, store):
    resp = logged_in_client.get(f'/stores/{store.id}/shop')
    assert resp.status_code == 200


def test_shop_view_groups_items_by_section(logged_in_client, store, app):
    with app.app_context():
        section = StoreSection(name='Produce', store_id=store.id)
        db.session.add(section)
        db.session.flush()
        db.session.add(ShoppingListItem(name='Apples', section_id=section.id, store_id=store.id))
        db.session.add(ShoppingListItem(name='Bread', store_id=store.id))
        db.session.commit()
    resp = logged_in_client.get(f'/stores/{store.id}/shop')
    assert b'Produce' in resp.data
    assert b'Apples' in resp.data
    assert b'Bread' in resp.data


def test_toggle_list_item(logged_in_client, store, app):
    with app.app_context():
        item = ShoppingListItem(name='Bread', store_id=store.id)
        db.session.add(item)
        db.session.commit()
        item_id = item.id
    resp = logged_in_client.post(f'/stores/{store.id}/list/{item_id}/toggle')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['ok'] is True
    assert data['checked'] is True


def test_toggle_list_item_not_found_returns_404(logged_in_client, store):
    resp = logged_in_client.post(f'/stores/{store.id}/list/9999/toggle')
    assert resp.status_code == 404


def test_done_shopping_clears_list(logged_in_client, store, app):
    with app.app_context():
        staple = StapleItem(name='Milk', store_id=store.id)
        db.session.add(staple)
        db.session.flush()
        db.session.add(ShoppingListItem(name='Milk', staple_item_id=staple.id, store_id=store.id))
        db.session.add(ShoppingListItem(name='Sriracha', store_id=store.id))
        db.session.commit()
        staple_id = staple.id
    resp = logged_in_client.post(f'/stores/{store.id}/list/done')
    assert resp.status_code == 302
    with app.app_context():
        assert db.session.scalar(
            select(func.count()).select_from(ShoppingListItem)
            .where(ShoppingListItem.store_id == store.id)
        ) == 0
        assert db.session.get(StapleItem, staple_id).shopping_list_item is None
```

- [ ] **Step 2: Run tests — expect failure**

```
python -m pytest tests/test_stores.py::test_shop_view_returns_200 -v
```

Expected: FAIL — no route `/stores/<id>/shop`.

- [ ] **Step 3: Add routes to `app/stores/routes.py`**

Append:

```python
@stores_bp.route('/<int:store_id>/shop')
@login_required
def store_shop(store_id):
    store = db.session.get(Store, store_id)
    if not store:
        return redirect(url_for('stores.stores_list'))
    items = db.session.scalars(
        select(ShoppingListItem)
        .where(ShoppingListItem.store_id == store_id)
        .order_by(ShoppingListItem.checked, ShoppingListItem.name)
    ).all()
    section_map = {}
    unsectioned = []
    for item in items:
        if item.section_id and item.section:
            if item.section_id not in section_map:
                section_map[item.section_id] = (item.section, [])
            section_map[item.section_id][1].append(item)
        else:
            unsectioned.append(item)
    grouped = sorted(section_map.values(), key=lambda x: x[0].name)
    return render_template('stores/shop.html', store=store, grouped=grouped,
                           unsectioned=unsectioned)


@stores_bp.route('/<int:store_id>/list/<int:item_id>/toggle', methods=['POST'])
@login_required
def toggle_list_item(store_id, item_id):
    item = db.session.get(ShoppingListItem, item_id)
    if not item or item.store_id != store_id:
        return jsonify({'ok': False, 'error': 'Not found'}), 404
    item.checked = not item.checked
    db.session.commit()
    return jsonify({'ok': True, 'checked': item.checked})


@stores_bp.route('/<int:store_id>/list/done', methods=['POST'])
@login_required
def done_shopping(store_id):
    db.session.execute(
        delete(ShoppingListItem).where(ShoppingListItem.store_id == store_id)
    )
    db.session.commit()
    return redirect(url_for('stores.store_index', store_id=store_id))
```

- [ ] **Step 4: Create `templates/stores/shop.html`**

```html
{% extends "base.html" %}
{% block title %}Shopping — {{ store.name }} — {{ config.APP_NAME }}{% endblock %}

{% block content %}
<div class="d-flex justify-content-between align-items-center mb-3 flex-wrap gap-2">
  <h2 class="mb-0">{{ store.name }} — Shopping List</h2>
  {% if grouped or unsectioned %}
  <form method="post" action="{{ url_for('stores.done_shopping', store_id=store.id) }}"
        onsubmit="return confirm('Mark shopping as done? This will clear your list.')">
    <button type="submit" class="btn btn-success">Done Shopping ✓</button>
  </form>
  {% endif %}
</div>

{% if not grouped and not unsectioned %}
<p class="text-muted">
  Your shopping list is empty.
  <a href="{{ url_for('stores.store_index', store_id=store.id) }}">Add some items</a>.
</p>
{% else %}
<div class="accordion" id="shopping-accordion">
  {% for section, items in grouped %}
  <div class="accordion-item">
    <h2 class="accordion-header" id="heading-{{ section.id }}">
      <button class="accordion-button" type="button"
              data-bs-toggle="collapse" data-bs-target="#collapse-{{ section.id }}"
              aria-expanded="true" aria-controls="collapse-{{ section.id }}">
        {{ section.name }}
        <span class="badge bg-secondary ms-2" id="badge-{{ section.id }}">
          {{ items | selectattr('checked', 'equalto', False) | list | length }}
        </span>
      </button>
    </h2>
    <div id="collapse-{{ section.id }}" class="accordion-collapse collapse show"
         aria-labelledby="heading-{{ section.id }}">
      <div class="accordion-body p-0">
        <ul class="list-group list-group-flush">
          {% for item in items %}
          <li class="list-group-item d-flex align-items-center gap-2 {% if item.checked %}text-muted{% endif %}"
              id="list-item-{{ item.id }}" style="cursor:pointer"
              onclick="toggleListItem({{ item.id }}, this, 'badge-{{ section.id }}')">
            <input type="checkbox" class="form-check-input flex-shrink-0"
                   {% if item.checked %}checked{% endif %}
                   onclick="event.stopPropagation()"
                   onchange="toggleListItem({{ item.id }}, this.closest('li'), 'badge-{{ section.id }}')">
            <span class="{% if item.checked %}text-decoration-line-through{% endif %}">{{ item.name }}</span>
          </li>
          {% endfor %}
        </ul>
      </div>
    </div>
  </div>
  {% endfor %}

  {% if unsectioned %}
  <div class="accordion-item">
    <h2 class="accordion-header" id="heading-other">
      <button class="accordion-button" type="button"
              data-bs-toggle="collapse" data-bs-target="#collapse-other"
              aria-expanded="true" aria-controls="collapse-other">
        Other
        <span class="badge bg-secondary ms-2" id="badge-other">
          {{ unsectioned | selectattr('checked', 'equalto', False) | list | length }}
        </span>
      </button>
    </h2>
    <div id="collapse-other" class="accordion-collapse collapse show" aria-labelledby="heading-other">
      <div class="accordion-body p-0">
        <ul class="list-group list-group-flush">
          {% for item in unsectioned %}
          <li class="list-group-item d-flex align-items-center gap-2 {% if item.checked %}text-muted{% endif %}"
              id="list-item-{{ item.id }}" style="cursor:pointer"
              onclick="toggleListItem({{ item.id }}, this, 'badge-other')">
            <input type="checkbox" class="form-check-input flex-shrink-0"
                   {% if item.checked %}checked{% endif %}
                   onclick="event.stopPropagation()"
                   onchange="toggleListItem({{ item.id }}, this.closest('li'), 'badge-other')">
            <span class="{% if item.checked %}text-decoration-line-through{% endif %}">{{ item.name }}</span>
          </li>
          {% endfor %}
        </ul>
      </div>
    </div>
  </div>
  {% endif %}
</div>
{% endif %}

{% include 'partials/error_toast.html' %}

<script>
const STORE_BASE = {{ url_for('stores.store_index', store_id=store.id) | tojson }};
function toggleItemUrl(id) { return STORE_BASE + 'list/' + id + '/toggle'; }

function showError(msg) {
  document.getElementById('error-toast-body').textContent = msg;
  new bootstrap.Toast(document.getElementById('error-toast')).show();
}

async function toggleListItem(itemId, row, badgeId) {
  const checkbox = row.querySelector('input[type="checkbox"]');
  const wasChecked = checkbox.checked;
  try {
    const resp = await fetch(toggleItemUrl(itemId), {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
    });
    const data = await resp.json();
    if (!data.ok) throw new Error(data.error);
    const nameEl = row.querySelector('span');
    const list = row.parentElement;
    if (data.checked) {
      row.classList.add('text-muted');
      nameEl.classList.add('text-decoration-line-through');
      checkbox.checked = true;
      list.appendChild(row);
    } else {
      row.classList.remove('text-muted');
      nameEl.classList.remove('text-decoration-line-through');
      checkbox.checked = false;
      list.prepend(row);
    }
    const badge = document.getElementById(badgeId);
    if (badge) {
      badge.textContent = list.querySelectorAll('input[type="checkbox"]:not(:checked)').length;
    }
  } catch (e) {
    checkbox.checked = wasChecked;
    showError(e.message || 'Something went wrong. Please try again.');
  }
}
</script>
{% endblock %}
```

- [ ] **Step 5: Run new tests**

```
python -m pytest tests/test_stores.py -v
```

Expected: all store tests pass.

- [ ] **Step 6: Run full suite**

```
python -m pytest -v
```

- [ ] **Step 7: Commit**

```
git add app/stores/routes.py templates/stores/shop.html tests/test_stores.py
git commit -m "feat: add store shop view routes and template"
```

---

## Task 5: Manage page (`/stores/<id>/manage`)

**Files:**
- Modify: `app/stores/routes.py`
- Create: `templates/stores/manage.html`
- Modify: `tests/test_stores.py`

**Interfaces:**
- Produces:
  - `GET /stores/<id>/manage` → `stores.store_manage`
  - `POST /stores/<id>/sections` → `stores.add_section`
  - `POST /stores/<id>/sections/<sid>/edit` → `stores.edit_section`
  - `POST /stores/<id>/sections/<sid>/delete` → `stores.delete_section`

- [ ] **Step 1: Write failing tests**

Append to `tests/test_stores.py`:

```python
def test_store_manage_requires_login(client, store):
    resp = client.get(f'/stores/{store.id}/manage')
    assert resp.status_code == 302
    assert '/auth/login' in resp.headers['Location']


def test_store_manage_returns_200(logged_in_client, store):
    resp = logged_in_client.get(f'/stores/{store.id}/manage')
    assert resp.status_code == 200
    assert store.name.encode() in resp.data


def test_add_section(logged_in_client, store, app):
    resp = logged_in_client.post(f'/stores/{store.id}/sections', json={'name': 'Dairy'})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['ok'] is True
    assert data['name'] == 'Dairy'
    with app.app_context():
        assert db.session.scalar(
            select(StoreSection).where(StoreSection.name == 'Dairy',
                                       StoreSection.store_id == store.id)
        ) is not None


def test_add_duplicate_section_returns_409(logged_in_client, store, app):
    with app.app_context():
        db.session.add(StoreSection(name='Dairy', store_id=store.id))
        db.session.commit()
    resp = logged_in_client.post(f'/stores/{store.id}/sections', json={'name': 'Dairy'})
    assert resp.status_code == 409
    assert resp.get_json()['ok'] is False


def test_same_section_name_allowed_in_different_stores(logged_in_client, store, app):
    with app.app_context():
        db.session.add(StoreSection(name='Dairy', store_id=store.id))
        other = Store(name='Other')
        db.session.add(other)
        db.session.commit()
        other_id = other.id
    resp = logged_in_client.post(f'/stores/{other_id}/sections', json={'name': 'Dairy'})
    assert resp.status_code == 200
    assert resp.get_json()['ok'] is True


def test_delete_section(logged_in_client, store, app):
    with app.app_context():
        section = StoreSection(name='Dairy', store_id=store.id)
        db.session.add(section)
        db.session.commit()
        section_id = section.id
    resp = logged_in_client.post(f'/stores/{store.id}/sections/{section_id}/delete')
    assert resp.status_code == 302
    with app.app_context():
        assert db.session.get(StoreSection, section_id) is None


def test_delete_section_nulls_item_section_ids(logged_in_client, store, app):
    with app.app_context():
        section = StoreSection(name='Produce', store_id=store.id)
        db.session.add(section)
        db.session.flush()
        staple = StapleItem(name='Apples', section_id=section.id, store_id=store.id)
        list_item = ShoppingListItem(name='Apples', section_id=section.id, store_id=store.id)
        db.session.add_all([staple, list_item])
        db.session.commit()
        section_id, staple_id, item_id = section.id, staple.id, list_item.id
    logged_in_client.post(f'/stores/{store.id}/sections/{section_id}/delete')
    with app.app_context():
        assert db.session.get(StapleItem, staple_id).section_id is None
        assert db.session.get(ShoppingListItem, item_id).section_id is None


def test_edit_section_renames_section(logged_in_client, store, app):
    with app.app_context():
        section = StoreSection(name='Dairy', store_id=store.id)
        db.session.add(section)
        db.session.commit()
        section_id = section.id
    resp = logged_in_client.post(f'/stores/{store.id}/sections/{section_id}/edit',
                                 json={'name': 'Frozen'})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['ok'] is True
    assert data['name'] == 'Frozen'


def test_edit_section_not_found_returns_404(logged_in_client, store):
    resp = logged_in_client.post(f'/stores/{store.id}/sections/9999/edit', json={'name': 'X'})
    assert resp.status_code == 404


def test_edit_section_duplicate_name_returns_409(logged_in_client, store, app):
    with app.app_context():
        db.session.add(StoreSection(name='Dairy', store_id=store.id))
        db.session.add(StoreSection(name='Produce', store_id=store.id))
        db.session.commit()
        section_id = db.session.scalar(
            select(StoreSection).where(StoreSection.name == 'Dairy',
                                       StoreSection.store_id == store.id)
        ).id
    resp = logged_in_client.post(f'/stores/{store.id}/sections/{section_id}/edit',
                                 json={'name': 'Produce'})
    assert resp.status_code == 409


def test_edit_section_same_name_is_ok(logged_in_client, store, app):
    with app.app_context():
        section = StoreSection(name='Dairy', store_id=store.id)
        db.session.add(section)
        db.session.commit()
        section_id = section.id
    resp = logged_in_client.post(f'/stores/{store.id}/sections/{section_id}/edit',
                                 json={'name': 'Dairy'})
    assert resp.status_code == 200
    assert resp.get_json()['ok'] is True
```

- [ ] **Step 2: Run tests — expect failure**

```
python -m pytest tests/test_stores.py::test_store_manage_returns_200 -v
```

Expected: FAIL — no route `/stores/<id>/manage`.

- [ ] **Step 3: Add routes to `app/stores/routes.py`**

Append:

```python
@stores_bp.route('/<int:store_id>/manage')
@login_required
def store_manage(store_id):
    store = db.session.get(Store, store_id)
    if not store:
        return redirect(url_for('stores.stores_list'))
    sections = db.session.scalars(
        select(StoreSection)
        .where(StoreSection.store_id == store_id)
        .order_by(StoreSection.name)
    ).all()
    return render_template('stores/manage.html', store=store, sections=sections)


@stores_bp.route('/<int:store_id>/sections', methods=['POST'])
@login_required
def add_section(store_id):
    store = db.session.get(Store, store_id)
    if not store:
        return jsonify({'ok': False, 'error': 'Not found'}), 404
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'ok': False, 'error': 'Name is required'}), 400
    if db.session.scalar(
        select(StoreSection).where(StoreSection.store_id == store_id, StoreSection.name == name)
    ):
        return jsonify({'ok': False, 'error': 'Section already exists'}), 409
    section = StoreSection(name=name, store_id=store_id)
    db.session.add(section)
    db.session.commit()
    return jsonify({'ok': True, 'id': section.id, 'name': section.name})


@stores_bp.route('/<int:store_id>/sections/<int:section_id>/edit', methods=['POST'])
@login_required
def edit_section(store_id, section_id):
    section = db.session.get(StoreSection, section_id)
    if not section or section.store_id != store_id:
        return jsonify({'ok': False, 'error': 'Not found'}), 404
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'ok': False, 'error': 'Name is required'}), 400
    if name != section.name and db.session.scalar(
        select(StoreSection).where(StoreSection.store_id == store_id, StoreSection.name == name)
    ):
        return jsonify({'ok': False, 'error': 'Section already exists'}), 409
    section.name = name
    db.session.commit()
    return jsonify({'ok': True, 'id': section.id, 'name': section.name})


@stores_bp.route('/<int:store_id>/sections/<int:section_id>/delete', methods=['POST'])
@login_required
def delete_section(store_id, section_id):
    section = db.session.get(StoreSection, section_id)
    if section and section.store_id == store_id:
        db.session.execute(
            update(StapleItem).where(StapleItem.section_id == section_id).values(section_id=None)
        )
        db.session.execute(
            update(ShoppingListItem).where(ShoppingListItem.section_id == section_id).values(section_id=None)
        )
        db.session.delete(section)
        db.session.commit()
    return redirect(url_for('stores.store_manage', store_id=store_id))
```

- [ ] **Step 4: Create `templates/stores/manage.html`**

```html
{% extends "base.html" %}
{% block title %}Manage {{ store.name }} — {{ config.APP_NAME }}{% endblock %}

{% block content %}
<div class="row">
  <div class="col-md-6">
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h2>{{ store.name }}</h2>
      <a href="{{ url_for('stores.store_index', store_id=store.id) }}"
         class="btn btn-outline-secondary btn-sm">← Back</a>
    </div>

    <!-- Store name -->
    <div class="card shadow-sm mb-4">
      <div class="card-header"><h5 class="mb-0">Store Name</h5></div>
      <div class="card-body d-flex gap-2 align-items-center">
        <span id="store-name-display" class="flex-grow-1">{{ store.name }}</span>
        <input type="text" id="store-name-input"
               class="form-control d-none flex-grow-1" value="{{ store.name }}">
        <button id="btn-edit-name" class="btn btn-sm btn-outline-secondary">Edit</button>
        <button id="btn-save-name" class="btn btn-sm btn-success d-none">Save</button>
        <button id="btn-cancel-name" class="btn btn-sm btn-outline-secondary d-none">Cancel</button>
      </div>
    </div>

    <!-- Sections / Aisles -->
    <div class="card shadow-sm">
      <div class="card-header"><h5 class="mb-0">Aisles</h5></div>
      <ul class="list-group list-group-flush" id="sections-list">
        {% for section in sections %}
        <li class="list-group-item d-flex justify-content-between align-items-center gap-2"
            id="section-row-{{ section.id }}">
          <span class="section-name flex-grow-1">{{ section.name }}</span>
          <input type="text" class="form-control form-control-sm section-edit-input d-none flex-grow-1"
                 value="{{ section.name }}" data-id="{{ section.id }}">
          <div class="d-flex gap-1">
            <button class="btn btn-sm btn-outline-secondary btn-edit">Edit</button>
            <button class="btn btn-sm btn-success btn-save d-none">Save</button>
            <button class="btn btn-sm btn-outline-secondary btn-cancel d-none">Cancel</button>
            <form method="post"
                  action="{{ url_for('stores.delete_section', store_id=store.id, section_id=section.id) }}"
                  onsubmit="return confirm('Delete this section? Items will lose their section.')">
              <button type="submit" class="btn btn-sm btn-outline-danger">Delete</button>
            </form>
          </div>
        </li>
        {% endfor %}
      </ul>
      <div class="card-footer">
        <form id="add-section-form" class="d-flex gap-2">
          <input type="text" id="section-name" class="form-control form-control-sm"
                 placeholder="Aisle name" required>
          <button type="submit" class="btn btn-sm btn-primary">Add</button>
        </form>
      </div>
    </div>
  </div>
</div>

{% include 'partials/error_toast.html' %}

<script>
const STORE_BASE = {{ url_for('stores.store_index', store_id=store.id) | tojson }};
const RENAME_STORE_URL = {{ url_for('stores.rename_store', store_id=store.id) | tojson }};
const ADD_SECTION_URL = {{ url_for('stores.add_section', store_id=store.id) | tojson }};

function deleteSectionUrl(id) { return STORE_BASE + 'sections/' + id + '/delete'; }
function editSectionUrl(id) { return STORE_BASE + 'sections/' + id + '/edit'; }

function showError(msg) {
  document.getElementById('error-toast-body').textContent = msg;
  new bootstrap.Toast(document.getElementById('error-toast')).show();
}

// Store rename
const nameDisplay = document.getElementById('store-name-display');
const nameInput = document.getElementById('store-name-input');
const btnEdit = document.getElementById('btn-edit-name');
const btnSave = document.getElementById('btn-save-name');
const btnCancel = document.getElementById('btn-cancel-name');

btnEdit.addEventListener('click', () => {
  nameDisplay.classList.add('d-none');
  nameInput.classList.remove('d-none');
  btnEdit.classList.add('d-none');
  btnSave.classList.remove('d-none');
  btnCancel.classList.remove('d-none');
  nameInput.focus();
  nameInput.select();
});

btnCancel.addEventListener('click', () => {
  nameInput.value = nameDisplay.textContent;
  nameDisplay.classList.remove('d-none');
  nameInput.classList.add('d-none');
  btnEdit.classList.remove('d-none');
  btnSave.classList.add('d-none');
  btnCancel.classList.add('d-none');
});

async function saveStoreName() {
  const newName = nameInput.value.trim();
  if (!newName) return;
  try {
    const resp = await fetch(RENAME_STORE_URL, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({name: newName}),
    });
    const data = await resp.json();
    if (!data.ok) throw new Error(data.error);
    nameDisplay.textContent = data.name;
    nameInput.value = data.name;
    document.title = 'Manage ' + data.name + ' — {{ config.APP_NAME }}';
    nameDisplay.classList.remove('d-none');
    nameInput.classList.add('d-none');
    btnEdit.classList.remove('d-none');
    btnSave.classList.add('d-none');
    btnCancel.classList.add('d-none');
  } catch (e) {
    showError(e.message || 'Something went wrong');
  }
}

btnSave.addEventListener('click', saveStoreName);
nameInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') saveStoreName();
  if (e.key === 'Escape') btnCancel.click();
});

// Section edit/add (identical pattern to existing sections.html)
function wireEditButtons(li, sectionId) {
  const nameSpan = li.querySelector('.section-name');
  const editInput = li.querySelector('.section-edit-input');
  const btnEdit = li.querySelector('.btn-edit');
  const btnSave = li.querySelector('.btn-save');
  const btnCancel = li.querySelector('.btn-cancel');

  btnEdit.addEventListener('click', () => {
    nameSpan.classList.add('d-none');
    editInput.classList.remove('d-none');
    btnEdit.classList.add('d-none');
    btnSave.classList.remove('d-none');
    btnCancel.classList.remove('d-none');
    editInput.focus();
    editInput.select();
  });

  btnCancel.addEventListener('click', () => {
    editInput.value = nameSpan.textContent;
    nameSpan.classList.remove('d-none');
    editInput.classList.add('d-none');
    btnEdit.classList.remove('d-none');
    btnSave.classList.add('d-none');
    btnCancel.classList.add('d-none');
  });

  async function saveEdit() {
    const newName = editInput.value.trim();
    if (!newName) return;
    try {
      const resp = await fetch(editSectionUrl(sectionId), {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({name: newName}),
      });
      const data = await resp.json();
      if (!data.ok) throw new Error(data.error);
      nameSpan.textContent = data.name;
      editInput.value = data.name;
      nameSpan.classList.remove('d-none');
      editInput.classList.add('d-none');
      btnEdit.classList.remove('d-none');
      btnSave.classList.add('d-none');
      btnCancel.classList.add('d-none');
    } catch (e) {
      showError(e.message || 'Something went wrong');
    }
  }

  btnSave.addEventListener('click', saveEdit);
  editInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') saveEdit();
    if (e.key === 'Escape') btnCancel.click();
  });
}

document.querySelectorAll('#sections-list li[id^="section-row-"]').forEach((li) => {
  const sectionId = parseInt(li.id.replace('section-row-', ''), 10);
  wireEditButtons(li, sectionId);
});

document.getElementById('add-section-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const nameInput = document.getElementById('section-name');
  const name = nameInput.value.trim();
  if (!name) return;
  try {
    const resp = await fetch(ADD_SECTION_URL, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({name}),
    });
    const data = await resp.json();
    if (!data.ok) throw new Error(data.error);
    const li = document.createElement('li');
    li.className = 'list-group-item d-flex justify-content-between align-items-center gap-2';
    li.id = 'section-row-' + data.id;
    const nameSpan = document.createElement('span');
    nameSpan.className = 'section-name flex-grow-1';
    nameSpan.textContent = data.name;
    const editInput = document.createElement('input');
    editInput.type = 'text';
    editInput.className = 'form-control form-control-sm section-edit-input d-none flex-grow-1';
    editInput.value = data.name;
    editInput.dataset.id = data.id;
    const btnEdit = document.createElement('button');
    btnEdit.type = 'button';
    btnEdit.className = 'btn btn-sm btn-outline-secondary btn-edit';
    btnEdit.textContent = 'Edit';
    const btnSave = document.createElement('button');
    btnSave.type = 'button';
    btnSave.className = 'btn btn-sm btn-success btn-save d-none';
    btnSave.textContent = 'Save';
    const btnCancel = document.createElement('button');
    btnCancel.type = 'button';
    btnCancel.className = 'btn btn-sm btn-outline-secondary btn-cancel d-none';
    btnCancel.textContent = 'Cancel';
    const delForm = document.createElement('form');
    delForm.method = 'post';
    delForm.action = deleteSectionUrl(data.id);
    delForm.addEventListener('submit', (ev) => {
      if (!confirm('Delete this section? Items will lose their section.')) ev.preventDefault();
    });
    const delBtn = document.createElement('button');
    delBtn.type = 'submit';
    delBtn.className = 'btn btn-sm btn-outline-danger';
    delBtn.textContent = 'Delete';
    delForm.appendChild(delBtn);
    const btnGroup = document.createElement('div');
    btnGroup.className = 'd-flex gap-1';
    btnGroup.appendChild(btnEdit);
    btnGroup.appendChild(btnSave);
    btnGroup.appendChild(btnCancel);
    btnGroup.appendChild(delForm);
    li.appendChild(nameSpan);
    li.appendChild(editInput);
    li.appendChild(btnGroup);
    wireEditButtons(li, data.id);
    document.getElementById('sections-list').appendChild(li);
    nameInput.value = '';
  } catch (e) {
    showError(e.message || 'Something went wrong');
  }
});
</script>
{% endblock %}
```

- [ ] **Step 5: Run all store tests**

```
python -m pytest tests/test_stores.py -v
```

Expected: all store tests pass (including the error toast test that checks all three pages).

- [ ] **Step 6: Run full suite**

```
python -m pytest -v
```

- [ ] **Step 7: Commit**

```
git add app/stores/routes.py templates/stores/manage.html tests/test_stores.py
git commit -m "feat: add store manage page with section and store rename routes"
```

---

## Task 6: Dynamic navbar + remove grocery blueprint

**Files:**
- Modify: `templates/base.html`
- Modify: `app/__init__.py`
- Delete: `app/grocery/` (entire directory)
- Delete: `templates/grocery/` (entire directory)
- Delete: `tests/test_grocery.py`

- [ ] **Step 1: Update `templates/base.html` navbar**

Replace the static Grocery dropdown with a dynamic Stores dropdown. Find the `<ul class="navbar-nav me-auto">` block and replace its content:

Old:
```html
        <ul class="navbar-nav me-auto">
          <li class="nav-item dropdown">
            <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown">Grocery</a>
            <ul class="dropdown-menu">
              <li><a class="dropdown-item" href="{{ url_for('grocery.index') }}">Manage List</a></li>
              <li><a class="dropdown-item" href="{{ url_for('grocery.shop') }}">Shop</a></li>
            </ul>
          </li>
        </ul>
```

New:
```html
        <ul class="navbar-nav me-auto">
          <li class="nav-item dropdown">
            <a class="nav-link dropdown-toggle" href="#" role="button" data-bs-toggle="dropdown">Stores</a>
            <ul class="dropdown-menu">
              {% for s in all_stores %}
              <li><a class="dropdown-item" href="{{ url_for('stores.store_index', store_id=s.id) }}">{{ s.name }}</a></li>
              {% endfor %}
              <li><hr class="dropdown-divider"></li>
              <li><a class="dropdown-item" href="{{ url_for('stores.stores_list') }}">Manage stores</a></li>
            </ul>
          </li>
        </ul>
```

- [ ] **Step 2: Remove grocery blueprint from `app/__init__.py`**

Remove these two lines:

```python
from app.grocery import grocery_bp
app.register_blueprint(grocery_bp)
```

- [ ] **Step 3: Delete grocery files**

```
Remove-Item -Recurse -Force app\grocery
Remove-Item -Recurse -Force templates\grocery
Remove-Item tests\test_grocery.py
```

- [ ] **Step 4: Run full test suite**

```
python -m pytest -v
```

Expected: all store tests pass, no grocery tests (file deleted).

- [ ] **Step 5: Update README.md**

In the Project Structure section, update the blueprint list:
- Remove: `app/grocery/` line
- Add: `app/stores/` — Multi-store shopping list blueprint (`/stores/*`)
- Update routes description accordingly

- [ ] **Step 6: Commit**

```
git add templates/base.html app/__init__.py README.md
git commit -m "feat: dynamic stores navbar and remove grocery blueprint"
```

(Git will automatically stage the deletions. Verify with `git status` first.)

---

## Done

All six tasks complete. Run `python -m pytest -v` one final time to confirm everything passes, then push and open a PR.
