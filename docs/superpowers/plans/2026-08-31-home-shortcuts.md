# Home Page Shortcuts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add pinned-store shortcut cards to the home page so users can jump directly to a store's shopping list with one tap.

**Architecture:** Add `pinned` boolean to `Store`; add a pin toggle route and button on the manage page; update the home route to query pinned stores with item counts; slim the welcome card and render shortcut cards below it.

**Tech Stack:** Flask, SQLAlchemy 2.0, Flask-Migrate/Alembic, Bootstrap 5, Jinja2, pytest

## Global Constraints

- All queries use SQLAlchemy 2.0 style: `db.session.scalars(select(...))`, `db.session.scalar(select(...))`
- All routes are `@login_required`
- Fetch/JSON for the pin toggle; no full-page reload needed
- Run `python -m pytest` after every task; all tests must pass before committing

---

## File Map

**Modify:**
- `app/models.py` — add `pinned` to `Store`
- `migrations/versions/<rev>_add_store_pinned.py` — migration
- `app/stores/routes.py` — add `toggle_pin` route
- `app/home/routes.py` — query pinned stores + item counts
- `templates/home/index.html` — slim welcome card + shortcut cards
- `templates/stores/manage.html` — pin/unpin button in Store Name card

**Create:**
- `migrations/versions/<rev>_add_store_pinned.py`

---

## Task 1: Add `pinned` to `Store` model + migration

**Files:**
- Modify: `app/models.py`
- Create: `migrations/versions/<rev>_add_store_pinned.py`
- Modify: `tests/test_stores.py`

**Interfaces:**
- Produces: `Store.pinned` boolean column, default `False`; migration that applies and rolls back cleanly

- [ ] **Step 1: Write failing test**

Append to `tests/test_stores.py`:

```python
def test_store_pinned_defaults_to_false(app):
    with app.app_context():
        s = Store(name='Pinned Test')
        db.session.add(s)
        db.session.commit()
        assert db.session.get(Store, s.id).pinned is False


def test_store_can_be_pinned(app):
    with app.app_context():
        s = Store(name='Pinnable')
        db.session.add(s)
        db.session.commit()
        s.pinned = True
        db.session.commit()
        assert db.session.get(Store, s.id).pinned is True
```

- [ ] **Step 2: Run tests — expect failure**

```
python -m pytest tests/test_stores.py::test_store_pinned_defaults_to_false -v
```

Expected: FAIL — `Store` has no `pinned` attribute.

- [ ] **Step 3: Add `pinned` to `Store` in `app/models.py`**

In the `Store` class, add after `created_at`:

```python
pinned = db.Column(db.Boolean, nullable=False, default=False)
```

- [ ] **Step 4: Run tests — expect pass**

```
python -m pytest tests/test_stores.py::test_store_pinned_defaults_to_false tests/test_stores.py::test_store_can_be_pinned -v
```

Expected: 2 PASS.

- [ ] **Step 5: Generate migration skeleton**

```
python -m flask db migrate -m "add store pinned"
```

Note the generated file path. Keep the `revision` / `down_revision` values; replace `upgrade()` and `downgrade()` with:

```python
def upgrade():
    with op.batch_alter_table('store') as batch_op:
        batch_op.add_column(sa.Column('pinned', sa.Boolean(), nullable=True))

    conn = op.get_bind()
    conn.execute(sa.text("UPDATE store SET pinned = 0"))

    with op.batch_alter_table('store') as batch_op:
        batch_op.alter_column('pinned', existing_type=sa.Boolean(), nullable=False)


def downgrade():
    with op.batch_alter_table('store') as batch_op:
        batch_op.drop_column('pinned')
```

- [ ] **Step 6: Verify migration applies cleanly**

```
python -m flask db upgrade
python -m flask db downgrade -1
python -m flask db upgrade
```

All three must succeed without error.

- [ ] **Step 7: Run full test suite**

```
python -m pytest -v
```

Expected: all tests pass.

- [ ] **Step 8: Commit**

```
git add app/models.py migrations/versions/ tests/test_stores.py
git commit -m "feat: add pinned field to Store model"
```

---

## Task 2: Pin toggle route + manage page button

**Files:**
- Modify: `app/stores/routes.py`
- Modify: `templates/stores/manage.html`
- Modify: `tests/test_stores.py`

**Interfaces:**
- Consumes: `Store.pinned` (Task 1)
- Produces:
  - `POST /stores/<id>/manage/pin` → `stores.toggle_pin` — JSON `{ok, pinned}`
  - Manage page shows "Pin to home page" / "Unpin from home page" button that updates in place

- [ ] **Step 1: Write failing tests**

Append to `tests/test_stores.py`:

```python
def test_toggle_pin_pins_store(logged_in_client, store, app):
    resp = logged_in_client.post(f'/stores/{store.id}/manage/pin')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['ok'] is True
    assert data['pinned'] is True
    with app.app_context():
        assert db.session.get(Store, store.id).pinned is True


def test_toggle_pin_unpins_store(logged_in_client, store, app):
    with app.app_context():
        s = db.session.get(Store, store.id)
        s.pinned = True
        db.session.commit()
    resp = logged_in_client.post(f'/stores/{store.id}/manage/pin')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['ok'] is True
    assert data['pinned'] is False
    with app.app_context():
        assert db.session.get(Store, store.id).pinned is False


def test_toggle_pin_not_found_returns_404(logged_in_client):
    resp = logged_in_client.post('/stores/9999/manage/pin')
    assert resp.status_code == 404


def test_toggle_pin_requires_login(client, store):
    resp = client.post(f'/stores/{store.id}/manage/pin')
    assert resp.status_code == 302
    assert '/auth/login' in resp.headers['Location']


def test_manage_page_shows_pin_button(logged_in_client, store):
    resp = logged_in_client.get(f'/stores/{store.id}/manage')
    assert b'Pin to home page' in resp.data


def test_manage_page_shows_unpin_button_when_pinned(logged_in_client, store, app):
    with app.app_context():
        s = db.session.get(Store, store.id)
        s.pinned = True
        db.session.commit()
    resp = logged_in_client.get(f'/stores/{store.id}/manage')
    assert b'Unpin from home page' in resp.data
```

- [ ] **Step 2: Run tests — expect failure**

```
python -m pytest tests/test_stores.py::test_toggle_pin_pins_store -v
```

Expected: FAIL — no route `/stores/<id>/manage/pin`.

- [ ] **Step 3: Add `toggle_pin` to `app/stores/routes.py`**

Append after `rename_store`:

```python
@stores_bp.route('/<int:store_id>/manage/pin', methods=['POST'])
@login_required
def toggle_pin(store_id):
    store = db.session.get(Store, store_id)
    if not store:
        return jsonify({'ok': False, 'error': 'Not found'}), 404
    store.pinned = not store.pinned
    db.session.commit()
    return jsonify({'ok': True, 'pinned': store.pinned})
```

- [ ] **Step 4: Add pin button to `templates/stores/manage.html`**

In the Store Name card body, append after the Cancel button:

```html
        <button id="btn-pin" class="btn btn-sm btn-outline-primary ms-2"
                onclick="togglePin()">
          {% if store.pinned %}Unpin from home page{% else %}Pin to home page{% endif %}
        </button>
```

And add the JS at the bottom of the `<script>` block:

```javascript
const TOGGLE_PIN_URL = {{ url_for('stores.toggle_pin', store_id=store.id) | tojson }};

async function togglePin() {
  try {
    const resp = await fetch(TOGGLE_PIN_URL, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
    });
    const data = await resp.json();
    if (!data.ok) throw new Error(data.error);
    document.getElementById('btn-pin').textContent =
      data.pinned ? 'Unpin from home page' : 'Pin to home page';
  } catch (e) {
    showError(e.message || 'Something went wrong');
  }
}
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
git add app/stores/routes.py templates/stores/manage.html tests/test_stores.py
git commit -m "feat: add store pin toggle route and manage page button"
```

---

## Task 3: Home page shortcut cards + slim welcome card

**Files:**
- Modify: `app/home/routes.py`
- Modify: `templates/home/index.html`
- Modify: `tests/test_home.py` (or create if it doesn't exist)

**Interfaces:**
- Consumes: `Store.pinned` (Task 1), `toggle_pin` route (Task 2)
- Produces:
  - `GET /` passes `pinned_stores` (list of `(store, item_count)` tuples) to template
  - Home page renders compact welcome strip and shortcut cards for pinned stores

- [ ] **Step 1: Check for existing home tests**

```
python -m pytest tests/ -v -k "home" 2>&1 | head -20
```

Note which file they're in (likely `tests/test_home.py`). If the file doesn't exist, create it.

- [ ] **Step 2: Write failing tests**

Add to the home test file:

```python
def test_home_shows_pinned_store_shortcut(logged_in_client, app):
    from app.models import Store
    from app.extensions import db
    with app.app_context():
        s = Store(name='Target', pinned=True)
        db.session.add(s)
        db.session.commit()
    resp = logged_in_client.get('/')
    assert b'Target' in resp.data
    assert b'Go to list' in resp.data


def test_home_does_not_show_unpinned_store(logged_in_client, app):
    from app.models import Store
    from app.extensions import db
    with app.app_context():
        s = Store(name='Hidden Store', pinned=False)
        db.session.add(s)
        db.session.commit()
    resp = logged_in_client.get('/')
    assert b'Go to list' not in resp.data


def test_home_shows_item_count_for_pinned_store(logged_in_client, app):
    from app.models import Store, ShoppingListItem
    from app.extensions import db
    with app.app_context():
        s = Store(name='Costco', pinned=True)
        db.session.add(s)
        db.session.flush()
        db.session.add(ShoppingListItem(name='Milk', store_id=s.id))
        db.session.add(ShoppingListItem(name='Eggs', store_id=s.id))
        db.session.commit()
    resp = logged_in_client.get('/')
    assert b'2' in resp.data
```

- [ ] **Step 3: Run tests — expect failure**

```
python -m pytest tests/ -k "pinned_store" -v
```

Expected: FAIL — home route doesn't pass `pinned_stores`.

- [ ] **Step 4: Update `app/home/routes.py`**

```python
# app/home/routes.py
from flask import render_template
from flask_login import current_user, login_required
from sqlalchemy import func, select

from app.extensions import db
from app.home import home_bp
from app.models import ShoppingListItem, Store


@home_bp.route('/')
@login_required
def index():
    pinned = db.session.scalars(
        select(Store).where(Store.pinned == True).order_by(Store.name)  # noqa: E712
    ).all()
    counts = {
        store_id: count
        for store_id, count in db.session.execute(
            select(ShoppingListItem.store_id, func.count().label('n'))
            .where(ShoppingListItem.store_id.in_([s.id for s in pinned]))
            .group_by(ShoppingListItem.store_id)
        ).all()
    }
    pinned_stores = [(s, counts.get(s.id, 0)) for s in pinned]
    return render_template('home/index.html', user=current_user, pinned_stores=pinned_stores)
```

- [ ] **Step 5: Update `templates/home/index.html`**

Replace the entire file:

```html
{% extends "base.html" %}
{% block title %}Home — {{ config.APP_NAME }}{% endblock %}

{% block content %}
<div class="d-flex align-items-center gap-2 mb-4 py-2 px-3 bg-light rounded border">
  {% if user.profile_picture_url %}
  <img src="{{ user.profile_picture_url }}" class="rounded-circle" width="40" height="40" alt="{{ user.name }}">
  {% endif %}
  <span class="fw-semibold">Welcome back, {{ user.name }}!</span>
</div>

{% if pinned_stores %}
<div class="row row-cols-1 row-cols-md-2 row-cols-lg-3 g-3">
  {% for store, item_count in pinned_stores %}
  <div class="col">
    <div class="card shadow-sm h-100">
      <div class="card-header fw-semibold">{{ store.name }}</div>
      <div class="card-body d-flex align-items-center gap-2">
        {% if item_count > 0 %}
        <span class="badge bg-primary fs-6">{{ item_count }} item{{ 's' if item_count != 1 else '' }} on list</span>
        {% else %}
        <span class="text-muted small">List is empty</span>
        {% endif %}
      </div>
      <div class="card-footer">
        <a href="{{ url_for('stores.store_index', store_id=store.id) }}" class="btn btn-primary btn-sm">Go to list</a>
      </div>
    </div>
  </div>
  {% endfor %}
</div>
{% endif %}
{% endblock %}
```

- [ ] **Step 6: Run new tests**

```
python -m pytest tests/ -v
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```
git add app/home/routes.py templates/home/index.html tests/
git commit -m "feat: home page shortcut cards for pinned stores"
```

---

## Done

Run `python -m pytest -v` one final time to confirm everything passes, then push and open a PR.
