# Grocery List Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add grocery list management with an at-home planning view and an in-store shopping view.

**Architecture:** Three new SQLAlchemy models (StoreSection, StapleItem, ShoppingListItem) back a new `grocery` Flask blueprint. Interactive actions (toggling and adding items) use vanilla `fetch` to JSON endpoints; destructive actions use standard form POST with redirect. Bootstrap 5 accordion powers the grouped shopping view.

**Tech Stack:** Flask blueprints, SQLAlchemy, Bootstrap 5 accordion, vanilla JS fetch

---

## File Map

| File | Action |
|------|--------|
| `app/models.py` | Modify — add StoreSection, StapleItem, ShoppingListItem |
| `app/__init__.py` | Modify — register grocery blueprint |
| `app/grocery/__init__.py` | Create — blueprint definition |
| `app/grocery/routes.py` | Create — all grocery routes |
| `templates/base.html` | Modify — move navbar here, add Grocery/Shopping links |
| `templates/home/index.html` | Modify — remove navbar block |
| `templates/grocery/home.html` | Create — at-home view |
| `templates/grocery/shop.html` | Create — shopping view |
| `templates/grocery/sections.html` | Create — section management |
| `tests/test_grocery.py` | Create — all grocery tests |

---

### Task 1: Data models

**Files:**
- Modify: `app/models.py`
- Create: `tests/test_grocery.py`

- [ ] **Step 1: Write the failing model tests**

Create `tests/test_grocery.py`:

```python
# tests/test_grocery.py
import pytest
from app.models import StoreSection, StapleItem, ShoppingListItem
from app.extensions import db


def test_staple_item_defaults(app):
    with app.app_context():
        staple = StapleItem(name='Milk')
        db.session.add(staple)
        db.session.commit()
        assert db.session.get(StapleItem, staple.id).name == 'Milk'
        assert staple.on_shopping_list is False


def test_delete_staple_cascades_to_shopping_list_item(app):
    with app.app_context():
        staple = StapleItem(name='Milk', on_shopping_list=True)
        db.session.add(staple)
        db.session.flush()
        item = ShoppingListItem(name='Milk', staple_item_id=staple.id)
        db.session.add(item)
        db.session.commit()
        item_id = item.id
        db.session.delete(staple)
        db.session.commit()
        assert db.session.get(ShoppingListItem, item_id) is None


def test_section_delete_nulls_item_references(app):
    with app.app_context():
        section = StoreSection(name='Produce')
        db.session.add(section)
        db.session.flush()
        staple = StapleItem(name='Apples', section_id=section.id)
        list_item = ShoppingListItem(name='Apples', section_id=section.id)
        db.session.add_all([staple, list_item])
        db.session.commit()
        staple_id, item_id = staple.id, list_item.id
        # Mirrors what delete_section route does (SQLite doesn't enforce FK cascades)
        StapleItem.query.filter_by(section_id=section.id).update({'section_id': None})
        ShoppingListItem.query.filter_by(section_id=section.id).update({'section_id': None})
        db.session.delete(section)
        db.session.commit()
        assert db.session.get(StapleItem, staple_id).section_id is None
        assert db.session.get(ShoppingListItem, item_id).section_id is None
```

- [ ] **Step 2: Run tests — expect ImportError**

```
pytest tests/test_grocery.py -v
```

Expected: FAIL with `ImportError: cannot import name 'StoreSection' from 'app.models'`

- [ ] **Step 3: Add models to app/models.py**

Full replacement of `app/models.py`:

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
    try:
        return db.session.get(User, int(user_id))
    except (ValueError, TypeError):
        return None


class StoreSection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)


class StapleItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False)
    section_id = db.Column(
        db.Integer, db.ForeignKey('store_section.id', ondelete='SET NULL'), nullable=True
    )
    on_shopping_list = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    section = db.relationship('StoreSection', foreign_keys=[section_id])
    shopping_list_item = db.relationship(
        'ShoppingListItem',
        back_populates='staple',
        uselist=False,
        cascade='all, delete-orphan',
    )


class ShoppingListItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False)
    section_id = db.Column(
        db.Integer, db.ForeignKey('store_section.id', ondelete='SET NULL'), nullable=True
    )
    staple_item_id = db.Column(
        db.Integer, db.ForeignKey('staple_item.id', ondelete='CASCADE'), nullable=True
    )
    checked = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    section = db.relationship('StoreSection', foreign_keys=[section_id])
    staple = db.relationship('StapleItem', back_populates='shopping_list_item')
```

- [ ] **Step 4: Run tests — expect 3 PASSED**

```
pytest tests/test_grocery.py -v
```

Expected: 3 PASSED

- [ ] **Step 5: Run full suite — no regressions**

```
pytest -v
```

Expected: all existing tests pass

- [ ] **Step 6: Commit**

```bash
git add app/models.py tests/test_grocery.py
git commit -m "feat: add StoreSection, StapleItem, ShoppingListItem models"
```

---

### Task 2: Grocery blueprint skeleton

**Files:**
- Create: `app/grocery/__init__.py`
- Create: `app/grocery/routes.py`
- Modify: `app/__init__.py`
- Modify: `tests/test_grocery.py`

- [ ] **Step 1: Append auth redirect tests to tests/test_grocery.py**

```python
def test_grocery_index_requires_login(client):
    resp = client.get('/grocery/')
    assert resp.status_code == 302
    assert '/auth/login' in resp.headers['Location']


def test_grocery_shop_requires_login(client):
    resp = client.get('/grocery/shop')
    assert resp.status_code == 302
    assert '/auth/login' in resp.headers['Location']


def test_grocery_sections_requires_login(client):
    resp = client.get('/grocery/sections')
    assert resp.status_code == 302
    assert '/auth/login' in resp.headers['Location']
```

- [ ] **Step 2: Run — expect 404 (routes don't exist yet)**

```
pytest tests/test_grocery.py::test_grocery_index_requires_login tests/test_grocery.py::test_grocery_shop_requires_login tests/test_grocery.py::test_grocery_sections_requires_login -v
```

Expected: FAIL (404, not 302)

- [ ] **Step 3: Create app/grocery/__init__.py**

```python
from flask import Blueprint

grocery_bp = Blueprint('grocery', __name__, url_prefix='/grocery')

from app.grocery import routes  # noqa: E402, F401
```

- [ ] **Step 4: Create app/grocery/routes.py with stubs for all 11 routes**

```python
# app/grocery/routes.py
from flask import render_template, request, jsonify, redirect, url_for
from flask_login import login_required
from app.grocery import grocery_bp
from app.extensions import db
from app.models import StoreSection, StapleItem, ShoppingListItem


@grocery_bp.route('/')
@login_required
def index():
    return 'OK', 200


@grocery_bp.route('/staples', methods=['POST'])
@login_required
def add_staple():
    return jsonify({'ok': True}), 200


@grocery_bp.route('/staples/<int:staple_id>/toggle', methods=['POST'])
@login_required
def toggle_staple(staple_id):
    return jsonify({'ok': True}), 200


@grocery_bp.route('/staples/<int:staple_id>/delete', methods=['POST'])
@login_required
def delete_staple(staple_id):
    return redirect(url_for('grocery.index'))


@grocery_bp.route('/list/add', methods=['POST'])
@login_required
def add_to_list():
    return jsonify({'ok': True}), 200


@grocery_bp.route('/list/<int:item_id>/toggle', methods=['POST'])
@login_required
def toggle_list_item(item_id):
    return jsonify({'ok': True}), 200


@grocery_bp.route('/list/done', methods=['POST'])
@login_required
def done_shopping():
    return redirect(url_for('grocery.index'))


@grocery_bp.route('/shop')
@login_required
def shop():
    return 'OK', 200


@grocery_bp.route('/sections')
@login_required
def sections():
    return 'OK', 200


@grocery_bp.route('/sections', methods=['POST'])
@login_required
def add_section():
    return jsonify({'ok': True}), 200


@grocery_bp.route('/sections/<int:section_id>/delete', methods=['POST'])
@login_required
def delete_section(section_id):
    return redirect(url_for('grocery.sections'))
```

- [ ] **Step 5: Register the blueprint in app/__init__.py**

Full replacement of `app/__init__.py`:

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
    from app.grocery import grocery_bp
    app.register_blueprint(auth_bp)
    app.register_blueprint(home_bp)
    app.register_blueprint(grocery_bp)

    return app
```

- [ ] **Step 6: Run redirect tests — expect 3 PASSED**

```
pytest tests/test_grocery.py::test_grocery_index_requires_login tests/test_grocery.py::test_grocery_shop_requires_login tests/test_grocery.py::test_grocery_sections_requires_login -v
```

Expected: 3 PASSED

- [ ] **Step 7: Run full suite**

```
pytest -v
```

Expected: all pass

- [ ] **Step 8: Commit**

```bash
git add app/grocery/__init__.py app/grocery/routes.py app/__init__.py tests/test_grocery.py
git commit -m "feat: add grocery blueprint skeleton with auth protection"
```

---

### Task 3: Refactor navbar to base.html

**Files:**
- Modify: `templates/base.html`
- Modify: `templates/home/index.html`

No new tests — existing home tests verify this.

- [ ] **Step 1: Replace templates/base.html**

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
  {% if current_user.is_authenticated %}
  <nav class="navbar navbar-expand-md navbar-light bg-light border-bottom">
    <div class="container">
      <a class="navbar-brand fw-bold" href="/">{{ config.APP_NAME }}</a>
      <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navContent">
        <span class="navbar-toggler-icon"></span>
      </button>
      <div class="collapse navbar-collapse" id="navContent">
        <ul class="navbar-nav me-auto">
          <li class="nav-item">
            <a class="nav-link" href="{{ url_for('grocery.index') }}">Grocery</a>
          </li>
          <li class="nav-item">
            <a class="nav-link" href="{{ url_for('grocery.shop') }}">Shopping</a>
          </li>
        </ul>
        <ul class="navbar-nav ms-auto align-items-center">
          <li class="nav-item d-flex align-items-center gap-2 me-2">
            {% if current_user.profile_picture_url %}
            <img src="{{ current_user.profile_picture_url }}" class="rounded-circle" width="32" height="32" alt="{{ current_user.name }}">
            {% endif %}
            <span class="nav-link disabled">{{ current_user.name }}</span>
          </li>
          <li class="nav-item">
            <a class="nav-link" href="{{ url_for('auth.logout') }}">Sign out</a>
          </li>
        </ul>
      </div>
    </div>
  </nav>
  {% endif %}
  <main class="container mt-4">
    {% block content %}{% endblock %}
  </main>
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
```

- [ ] **Step 2: Replace templates/home/index.html (remove navbar block)**

```html
{% extends "base.html" %}
{% block title %}Home — {{ config.APP_NAME }}{% endblock %}

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

- [ ] **Step 3: Run full suite — no regressions**

```
pytest -v
```

Expected: all pass (home tests still find `Welcome` in content)

- [ ] **Step 4: Commit**

```bash
git add templates/base.html templates/home/index.html
git commit -m "feat: move navbar to base template with Grocery and Shopping links"
```

---

### Task 4: Section management

**Files:**
- Modify: `app/grocery/routes.py`
- Modify: `tests/test_grocery.py`
- Create: `templates/grocery/sections.html`

- [ ] **Step 1: Append section tests to tests/test_grocery.py**

```python
def test_sections_page_returns_200(logged_in_client):
    resp = logged_in_client.get('/grocery/sections')
    assert resp.status_code == 200


def test_add_section(logged_in_client, app):
    resp = logged_in_client.post('/grocery/sections', json={'name': 'Dairy'})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['ok'] is True
    assert data['name'] == 'Dairy'
    with app.app_context():
        assert StoreSection.query.filter_by(name='Dairy').first() is not None


def test_add_duplicate_section_returns_409(logged_in_client, app):
    with app.app_context():
        db.session.add(StoreSection(name='Dairy'))
        db.session.commit()
    resp = logged_in_client.post('/grocery/sections', json={'name': 'Dairy'})
    assert resp.status_code == 409
    assert resp.get_json()['ok'] is False


def test_delete_section(logged_in_client, app):
    with app.app_context():
        section = StoreSection(name='Dairy')
        db.session.add(section)
        db.session.commit()
        section_id = section.id
    resp = logged_in_client.post(f'/grocery/sections/{section_id}/delete')
    assert resp.status_code == 302
    with app.app_context():
        assert db.session.get(StoreSection, section_id) is None


def test_delete_section_nulls_item_section_ids(logged_in_client, app):
    with app.app_context():
        section = StoreSection(name='Produce')
        db.session.add(section)
        db.session.flush()
        staple = StapleItem(name='Apples', section_id=section.id)
        list_item = ShoppingListItem(name='Apples', section_id=section.id)
        db.session.add_all([staple, list_item])
        db.session.commit()
        section_id, staple_id, item_id = section.id, staple.id, list_item.id
    logged_in_client.post(f'/grocery/sections/{section_id}/delete')
    with app.app_context():
        assert db.session.get(StapleItem, staple_id).section_id is None
        assert db.session.get(ShoppingListItem, item_id).section_id is None
```

- [ ] **Step 2: Run — expect failures (stubs return stub responses)**

```
pytest tests/test_grocery.py::test_sections_page_returns_200 tests/test_grocery.py::test_add_section tests/test_grocery.py::test_add_duplicate_section_returns_409 tests/test_grocery.py::test_delete_section tests/test_grocery.py::test_delete_section_nulls_item_section_ids -v
```

Expected: FAIL

- [ ] **Step 3: Replace section stubs in app/grocery/routes.py**

Replace the three section stub functions with:

```python
@grocery_bp.route('/sections')
@login_required
def sections():
    all_sections = StoreSection.query.order_by(StoreSection.name).all()
    return render_template('grocery/sections.html', sections=all_sections)


@grocery_bp.route('/sections', methods=['POST'])
@login_required
def add_section():
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'ok': False, 'error': 'Name is required'}), 400
    if StoreSection.query.filter_by(name=name).first():
        return jsonify({'ok': False, 'error': 'Section already exists'}), 409
    section = StoreSection(name=name)
    db.session.add(section)
    db.session.commit()
    return jsonify({'ok': True, 'id': section.id, 'name': section.name})


@grocery_bp.route('/sections/<int:section_id>/delete', methods=['POST'])
@login_required
def delete_section(section_id):
    section = db.session.get(StoreSection, section_id)
    if section:
        StapleItem.query.filter_by(section_id=section_id).update({'section_id': None})
        ShoppingListItem.query.filter_by(section_id=section_id).update({'section_id': None})
        db.session.delete(section)
        db.session.commit()
    return redirect(url_for('grocery.sections'))
```

- [ ] **Step 4: Create templates/grocery/sections.html**

```html
{% extends "base.html" %}
{% block title %}Sections — {{ config.APP_NAME }}{% endblock %}

{% block content %}
<div class="row">
  <div class="col-md-6">
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h2>Manage Sections</h2>
      <a href="{{ url_for('grocery.index') }}" class="btn btn-outline-secondary btn-sm">← Back</a>
    </div>
    <div class="card shadow-sm">
      <ul class="list-group list-group-flush" id="sections-list">
        {% for section in sections %}
        <li class="list-group-item d-flex justify-content-between align-items-center"
            id="section-row-{{ section.id }}">
          <span>{{ section.name }}</span>
          <form method="post" action="{{ url_for('grocery.delete_section', section_id=section.id) }}"
                onsubmit="return confirm('Delete this section? Items will lose their section.')">
            <button type="submit" class="btn btn-sm btn-outline-danger">Delete</button>
          </form>
        </li>
        {% endfor %}
      </ul>
      <div class="card-footer">
        <form id="add-section-form" class="d-flex gap-2">
          <input type="text" id="section-name" class="form-control form-control-sm"
                 placeholder="Section name" required>
          <button type="submit" class="btn btn-sm btn-primary">Add</button>
        </form>
      </div>
    </div>
  </div>
</div>

<div class="toast-container position-fixed bottom-0 end-0 p-3">
  <div id="error-toast" class="toast" role="alert">
    <div class="toast-header bg-danger text-white">
      <strong class="me-auto">Error</strong>
      <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
    </div>
    <div class="toast-body" id="error-toast-body"></div>
  </div>
</div>

<script>
function showError(msg) {
  document.getElementById('error-toast-body').textContent = msg;
  new bootstrap.Toast(document.getElementById('error-toast')).show();
}

document.getElementById('add-section-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const nameInput = document.getElementById('section-name');
  const name = nameInput.value.trim();
  if (!name) return;
  try {
    const resp = await fetch('/grocery/sections', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({name}),
    });
    const data = await resp.json();
    if (!data.ok) throw new Error(data.error);
    const li = document.createElement('li');
    li.className = 'list-group-item d-flex justify-content-between align-items-center';
    li.id = 'section-row-' + data.id;
    const nameSpan = document.createElement('span');
    nameSpan.textContent = data.name;
    const form = document.createElement('form');
    form.method = 'post';
    form.action = '/grocery/sections/' + data.id + '/delete';
    form.addEventListener('submit', (ev) => {
      if (!confirm('Delete this section? Items will lose their section.')) ev.preventDefault();
    });
    const btn = document.createElement('button');
    btn.type = 'submit';
    btn.className = 'btn btn-sm btn-outline-danger';
    btn.textContent = 'Delete';
    form.appendChild(btn);
    li.appendChild(nameSpan);
    li.appendChild(form);
    document.getElementById('sections-list').appendChild(li);
    nameInput.value = '';
  } catch (e) {
    showError(e.message || 'Something went wrong');
  }
});
</script>
{% endblock %}
```

- [ ] **Step 5: Run section tests — expect 5 PASSED**

```
pytest tests/test_grocery.py::test_sections_page_returns_200 tests/test_grocery.py::test_add_section tests/test_grocery.py::test_add_duplicate_section_returns_409 tests/test_grocery.py::test_delete_section tests/test_grocery.py::test_delete_section_nulls_item_section_ids -v
```

Expected: 5 PASSED

- [ ] **Step 6: Run full suite**

```
pytest -v
```

Expected: all pass

- [ ] **Step 7: Commit**

```bash
git add app/grocery/routes.py templates/grocery/sections.html tests/test_grocery.py
git commit -m "feat: add section management routes and template"
```

---

### Task 5: Staple management routes

**Files:**
- Modify: `app/grocery/routes.py`
- Modify: `tests/test_grocery.py`

- [ ] **Step 1: Append staple tests to tests/test_grocery.py**

```python
def test_add_staple(logged_in_client, app):
    resp = logged_in_client.post('/grocery/staples', json={'name': 'Eggs'})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['ok'] is True
    assert data['name'] == 'Eggs'
    with app.app_context():
        assert StapleItem.query.filter_by(name='Eggs').first() is not None


def test_add_staple_missing_name_returns_400(logged_in_client):
    resp = logged_in_client.post('/grocery/staples', json={'name': ''})
    assert resp.status_code == 400
    assert resp.get_json()['ok'] is False


def test_toggle_staple_on_creates_shopping_list_item(logged_in_client, app):
    with app.app_context():
        staple = StapleItem(name='Milk')
        db.session.add(staple)
        db.session.commit()
        staple_id = staple.id
    resp = logged_in_client.post(f'/grocery/staples/{staple_id}/toggle')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['ok'] is True
    assert data['on_shopping_list'] is True
    with app.app_context():
        assert db.session.get(StapleItem, staple_id).on_shopping_list is True
        assert ShoppingListItem.query.filter_by(staple_item_id=staple_id).first() is not None


def test_toggle_staple_off_deletes_shopping_list_item(logged_in_client, app):
    with app.app_context():
        staple = StapleItem(name='Milk', on_shopping_list=True)
        db.session.add(staple)
        db.session.flush()
        item = ShoppingListItem(name='Milk', staple_item_id=staple.id)
        db.session.add(item)
        db.session.commit()
        staple_id = staple.id
    resp = logged_in_client.post(f'/grocery/staples/{staple_id}/toggle')
    assert resp.status_code == 200
    assert resp.get_json()['on_shopping_list'] is False
    with app.app_context():
        assert db.session.get(StapleItem, staple_id).on_shopping_list is False
        assert ShoppingListItem.query.filter_by(staple_item_id=staple_id).first() is None


def test_delete_staple(logged_in_client, app):
    with app.app_context():
        staple = StapleItem(name='Eggs')
        db.session.add(staple)
        db.session.commit()
        staple_id = staple.id
    resp = logged_in_client.post(f'/grocery/staples/{staple_id}/delete')
    assert resp.status_code == 302
    with app.app_context():
        assert db.session.get(StapleItem, staple_id) is None
```

- [ ] **Step 2: Run — expect failures**

```
pytest tests/test_grocery.py::test_add_staple tests/test_grocery.py::test_add_staple_missing_name_returns_400 tests/test_grocery.py::test_toggle_staple_on_creates_shopping_list_item tests/test_grocery.py::test_toggle_staple_off_deletes_shopping_list_item tests/test_grocery.py::test_delete_staple -v
```

Expected: FAIL

- [ ] **Step 3: Replace staple stubs in app/grocery/routes.py**

```python
@grocery_bp.route('/staples', methods=['POST'])
@login_required
def add_staple():
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'ok': False, 'error': 'Name is required'}), 400
    section_id = data.get('section_id') or None
    staple = StapleItem(name=name, section_id=section_id)
    db.session.add(staple)
    db.session.commit()
    return jsonify({
        'ok': True,
        'id': staple.id,
        'name': staple.name,
        'section_id': staple.section_id,
        'section_name': staple.section.name if staple.section else None,
        'on_shopping_list': staple.on_shopping_list,
    })


@grocery_bp.route('/staples/<int:staple_id>/toggle', methods=['POST'])
@login_required
def toggle_staple(staple_id):
    staple = db.session.get(StapleItem, staple_id)
    if not staple:
        return jsonify({'ok': False, 'error': 'Not found'}), 404
    if staple.on_shopping_list:
        if staple.shopping_list_item:
            db.session.delete(staple.shopping_list_item)
        staple.on_shopping_list = False
    else:
        item = ShoppingListItem(
            name=staple.name, section_id=staple.section_id, staple_item_id=staple.id
        )
        db.session.add(item)
        staple.on_shopping_list = True
    db.session.commit()
    return jsonify({
        'ok': True,
        'on_shopping_list': staple.on_shopping_list,
        'shopping_count': ShoppingListItem.query.count(),
    })


@grocery_bp.route('/staples/<int:staple_id>/delete', methods=['POST'])
@login_required
def delete_staple(staple_id):
    staple = db.session.get(StapleItem, staple_id)
    if staple:
        db.session.delete(staple)
        db.session.commit()
    return redirect(url_for('grocery.index'))
```

- [ ] **Step 4: Run staple tests — expect 5 PASSED**

```
pytest tests/test_grocery.py::test_add_staple tests/test_grocery.py::test_add_staple_missing_name_returns_400 tests/test_grocery.py::test_toggle_staple_on_creates_shopping_list_item tests/test_grocery.py::test_toggle_staple_off_deletes_shopping_list_item tests/test_grocery.py::test_delete_staple -v
```

Expected: 5 PASSED

- [ ] **Step 5: Run full suite**

```
pytest -v
```

Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add app/grocery/routes.py tests/test_grocery.py
git commit -m "feat: add staple management routes"
```

---

### Task 6: At-home view + one-off item add

**Files:**
- Modify: `app/grocery/routes.py`
- Modify: `tests/test_grocery.py`
- Create: `templates/grocery/home.html`

- [ ] **Step 1: Append at-home view tests to tests/test_grocery.py**

```python
def test_grocery_index_returns_200(logged_in_client):
    resp = logged_in_client.get('/grocery/')
    assert resp.status_code == 200
    assert b'Staples' in resp.data


def test_add_one_off_item(logged_in_client, app):
    resp = logged_in_client.post('/grocery/list/add', json={'name': 'Sriracha'})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['ok'] is True
    assert 'shopping_count' in data
    with app.app_context():
        item = ShoppingListItem.query.filter_by(name='Sriracha').first()
        assert item is not None
        assert item.staple_item_id is None


def test_add_one_off_item_missing_name_returns_400(logged_in_client):
    resp = logged_in_client.post('/grocery/list/add', json={'name': ''})
    assert resp.status_code == 400
```

- [ ] **Step 2: Run — expect failures**

```
pytest tests/test_grocery.py::test_grocery_index_returns_200 tests/test_grocery.py::test_add_one_off_item tests/test_grocery.py::test_add_one_off_item_missing_name_returns_400 -v
```

Expected: FAIL

- [ ] **Step 3: Replace index and add_to_list stubs in app/grocery/routes.py**

```python
@grocery_bp.route('/')
@login_required
def index():
    staples = StapleItem.query.order_by(StapleItem.on_shopping_list, StapleItem.name).all()
    sections = StoreSection.query.order_by(StoreSection.name).all()
    shopping_count = ShoppingListItem.query.count()
    return render_template(
        'grocery/home.html', staples=staples, sections=sections, shopping_count=shopping_count
    )


@grocery_bp.route('/list/add', methods=['POST'])
@login_required
def add_to_list():
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'ok': False, 'error': 'Name is required'}), 400
    section_id = data.get('section_id') or None
    item = ShoppingListItem(name=name, section_id=section_id)
    db.session.add(item)
    db.session.commit()
    return jsonify({'ok': True, 'id': item.id, 'shopping_count': ShoppingListItem.query.count()})
```

- [ ] **Step 4: Create templates/grocery/home.html**

```html
{% extends "base.html" %}
{% block title %}Grocery — {{ config.APP_NAME }}{% endblock %}

{% block content %}
<h2 class="mb-4">Grocery</h2>

<div class="row">
  <!-- Staples panel -->
  <div class="col-md-6 mb-4">
    <div class="card shadow-sm h-100">
      <div class="card-header d-flex justify-content-between align-items-center">
        <h5 class="mb-0">Staples</h5>
        <a href="{{ url_for('grocery.sections') }}" class="btn btn-sm btn-outline-secondary">Manage sections</a>
      </div>
      <div class="card-body p-0">
        <ul class="list-group list-group-flush" id="staples-list">
          {% for staple in staples %}
          <li class="list-group-item d-flex align-items-center gap-2 {% if staple.on_shopping_list %}text-muted{% endif %}"
              id="staple-{{ staple.id }}">
            <input type="checkbox" class="form-check-input flex-shrink-0"
                   {% if staple.on_shopping_list %}checked{% endif %}
                   onchange="toggleStaple({{ staple.id }}, this)">
            <span class="flex-grow-1 {% if staple.on_shopping_list %}text-decoration-line-through{% endif %}">
              {{ staple.name }}
            </span>
            {% if staple.section %}
            <span class="badge bg-secondary">{{ staple.section.name }}</span>
            {% endif %}
            <form method="post" action="{{ url_for('grocery.delete_staple', staple_id=staple.id) }}"
                  onsubmit="return confirm('Delete {{ staple.name | e }}?')">
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
        <div class="d-flex align-items-center gap-3 flex-wrap">
          <span class="badge bg-primary fs-6" id="shopping-count">
            {{ shopping_count }} item{{ 's' if shopping_count != 1 else '' }} on your list
          </span>
          <a href="{{ url_for('grocery.shop') }}" class="btn btn-success">Start Shopping →</a>
        </div>
      </div>
    </div>
  </div>
</div>

<div class="toast-container position-fixed bottom-0 end-0 p-3">
  <div id="error-toast" class="toast" role="alert">
    <div class="toast-header bg-danger text-white">
      <strong class="me-auto">Error</strong>
      <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast"></button>
    </div>
    <div class="toast-body" id="error-toast-body"></div>
  </div>
</div>

<script>
function showError(msg) {
  document.getElementById('error-toast-body').textContent = msg;
  new bootstrap.Toast(document.getElementById('error-toast')).show();
}

function updateShoppingCount(count) {
  document.getElementById('shopping-count').textContent =
    count + ' item' + (count !== 1 ? 's' : '') + ' on your list';
}

async function toggleStaple(stapleId, checkbox) {
  const row = document.getElementById('staple-' + stapleId);
  const wasChecked = !checkbox.checked;
  try {
    const resp = await fetch('/grocery/staples/' + stapleId + '/toggle', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
    });
    const data = await resp.json();
    if (!data.ok) throw new Error(data.error);
    const nameEl = row.querySelector('span.flex-grow-1');
    if (data.on_shopping_list) {
      row.classList.add('text-muted');
      nameEl.classList.add('text-decoration-line-through');
      checkbox.checked = true;
      document.getElementById('staples-list').appendChild(row);
    } else {
      row.classList.remove('text-muted');
      nameEl.classList.remove('text-decoration-line-through');
      checkbox.checked = false;
      document.getElementById('staples-list').prepend(row);
    }
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
    const resp = await fetch('/grocery/staples', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({name, section_id: sectionSelect.value || null}),
    });
    const data = await resp.json();
    if (!data.ok) throw new Error(data.error);
    const li = document.createElement('li');
    li.className = 'list-group-item d-flex align-items-center gap-2';
    li.id = 'staple-' + data.id;
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
    delForm.action = '/grocery/staples/' + data.id + '/delete';
    delForm.addEventListener('submit', (ev) => {
      if (!confirm('Delete ' + data.name + '?')) ev.preventDefault();
    });
    const delBtn = document.createElement('button');
    delBtn.type = 'submit';
    delBtn.className = 'btn btn-sm btn-outline-danger py-0';
    delBtn.textContent = '×';
    delForm.appendChild(delBtn);
    li.appendChild(delForm);
    document.getElementById('staples-list').prepend(li);
    nameInput.value = '';
  } catch (e) {
    showError(e.message || 'Something went wrong');
  }
});

document.getElementById('add-list-form').addEventListener('submit', async (e) => {
  e.preventDefault();
  const nameInput = document.getElementById('list-item-name');
  const sectionSelect = document.getElementById('list-item-section');
  const name = nameInput.value.trim();
  if (!name) return;
  try {
    const resp = await fetch('/grocery/list/add', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({name, section_id: sectionSelect.value || null}),
    });
    const data = await resp.json();
    if (!data.ok) throw new Error(data.error);
    updateShoppingCount(data.shopping_count);
    nameInput.value = '';
    sectionSelect.value = '';
  } catch (e) {
    showError(e.message || 'Something went wrong');
  }
});
</script>
{% endblock %}
```

- [ ] **Step 5: Run at-home tests — expect 3 PASSED**

```
pytest tests/test_grocery.py::test_grocery_index_returns_200 tests/test_grocery.py::test_add_one_off_item tests/test_grocery.py::test_add_one_off_item_missing_name_returns_400 -v
```

Expected: 3 PASSED

- [ ] **Step 6: Run full suite**

```
pytest -v
```

Expected: all pass

- [ ] **Step 7: Commit**

```bash
git add app/grocery/routes.py templates/grocery/home.html tests/test_grocery.py
git commit -m "feat: add at-home grocery view and one-off item add"
```

---

### Task 7: Shopping view + done shopping

**Files:**
- Modify: `app/grocery/routes.py`
- Modify: `tests/test_grocery.py`
- Create: `templates/grocery/shop.html`

- [ ] **Step 1: Append shopping tests to tests/test_grocery.py**

```python
def test_shop_view_returns_200(logged_in_client):
    resp = logged_in_client.get('/grocery/shop')
    assert resp.status_code == 200


def test_shop_view_groups_items_by_section(logged_in_client, app):
    with app.app_context():
        section = StoreSection(name='Produce')
        db.session.add(section)
        db.session.flush()
        db.session.add(ShoppingListItem(name='Apples', section_id=section.id))
        db.session.add(ShoppingListItem(name='Bread'))
        db.session.commit()
    resp = logged_in_client.get('/grocery/shop')
    assert resp.status_code == 200
    assert b'Produce' in resp.data
    assert b'Apples' in resp.data
    assert b'Bread' in resp.data


def test_toggle_list_item(logged_in_client, app):
    with app.app_context():
        item = ShoppingListItem(name='Bread')
        db.session.add(item)
        db.session.commit()
        item_id = item.id
    resp = logged_in_client.post(f'/grocery/list/{item_id}/toggle')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['ok'] is True
    assert data['checked'] is True
    with app.app_context():
        assert db.session.get(ShoppingListItem, item_id).checked is True


def test_toggle_list_item_twice_unchecks(logged_in_client, app):
    with app.app_context():
        item = ShoppingListItem(name='Bread', checked=True)
        db.session.add(item)
        db.session.commit()
        item_id = item.id
    resp = logged_in_client.post(f'/grocery/list/{item_id}/toggle')
    assert resp.get_json()['checked'] is False
    with app.app_context():
        assert db.session.get(ShoppingListItem, item_id).checked is False


def test_done_shopping_clears_list_and_resets_staples(logged_in_client, app):
    with app.app_context():
        staple = StapleItem(name='Milk', on_shopping_list=True)
        db.session.add(staple)
        db.session.flush()
        db.session.add(ShoppingListItem(name='Milk', staple_item_id=staple.id))
        db.session.add(ShoppingListItem(name='Sriracha'))
        db.session.commit()
        staple_id = staple.id
    resp = logged_in_client.post('/grocery/list/done')
    assert resp.status_code == 302
    with app.app_context():
        assert ShoppingListItem.query.count() == 0
        assert db.session.get(StapleItem, staple_id).on_shopping_list is False
```

- [ ] **Step 2: Run — expect failures**

```
pytest tests/test_grocery.py::test_shop_view_returns_200 tests/test_grocery.py::test_shop_view_groups_items_by_section tests/test_grocery.py::test_toggle_list_item tests/test_grocery.py::test_toggle_list_item_twice_unchecks tests/test_grocery.py::test_done_shopping_clears_list_and_resets_staples -v
```

Expected: FAIL

- [ ] **Step 3: Replace shop, toggle_list_item, done_shopping stubs in app/grocery/routes.py**

```python
@grocery_bp.route('/shop')
@login_required
def shop():
    items = ShoppingListItem.query.order_by(ShoppingListItem.checked, ShoppingListItem.name).all()
    section_map = {}
    unsectioned = []
    for item in items:
        if item.section_id:
            if item.section_id not in section_map:
                section_map[item.section_id] = (item.section, [])
            section_map[item.section_id][1].append(item)
        else:
            unsectioned.append(item)
    grouped = sorted(section_map.values(), key=lambda x: x[0].name)
    return render_template('grocery/shop.html', grouped=grouped, unsectioned=unsectioned)


@grocery_bp.route('/list/<int:item_id>/toggle', methods=['POST'])
@login_required
def toggle_list_item(item_id):
    item = db.session.get(ShoppingListItem, item_id)
    if not item:
        return jsonify({'ok': False, 'error': 'Not found'}), 404
    item.checked = not item.checked
    db.session.commit()
    return jsonify({'ok': True, 'checked': item.checked})


@grocery_bp.route('/list/done', methods=['POST'])
@login_required
def done_shopping():
    ShoppingListItem.query.delete(synchronize_session=False)
    StapleItem.query.update({'on_shopping_list': False}, synchronize_session=False)
    db.session.commit()
    return redirect(url_for('grocery.index'))
```

- [ ] **Step 4: Create templates/grocery/shop.html**

```html
{% extends "base.html" %}
{% block title %}Shopping — {{ config.APP_NAME }}{% endblock %}

{% block content %}
<div class="d-flex justify-content-between align-items-center mb-3 flex-wrap gap-2">
  <h2 class="mb-0">Shopping List</h2>
  {% if grouped or unsectioned %}
  <form method="post" action="{{ url_for('grocery.done_shopping') }}"
        onsubmit="return confirm('Mark shopping as done? This will clear your list.')">
    <button type="submit" class="btn btn-success">Done Shopping ✓</button>
  </form>
  {% endif %}
</div>

{% if not grouped and not unsectioned %}
<p class="text-muted">
  Your shopping list is empty. <a href="{{ url_for('grocery.index') }}">Add some items</a>.
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
                   onclick="event.stopPropagation()">
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
                   onclick="event.stopPropagation()">
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

<script>
async function toggleListItem(itemId, row, badgeId) {
  const checkbox = row.querySelector('input[type="checkbox"]');
  const wasChecked = checkbox.checked;
  try {
    const resp = await fetch('/grocery/list/' + itemId + '/toggle', {
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
    alert('Something went wrong. Please try again.');
  }
}
</script>
{% endblock %}
```

- [ ] **Step 5: Run shopping tests — expect 5 PASSED**

```
pytest tests/test_grocery.py::test_shop_view_returns_200 tests/test_grocery.py::test_shop_view_groups_items_by_section tests/test_grocery.py::test_toggle_list_item tests/test_grocery.py::test_toggle_list_item_twice_unchecks tests/test_grocery.py::test_done_shopping_clears_list_and_resets_staples -v
```

Expected: 5 PASSED

- [ ] **Step 6: Run the full test suite**

```
pytest -v
```

Expected: all tests pass

- [ ] **Step 7: Commit**

```bash
git add app/grocery/routes.py templates/grocery/shop.html tests/test_grocery.py
git commit -m "feat: add shopping view and done-shopping reset"
```
