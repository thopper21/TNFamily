# Multi-Store Support Design

**Goal:** Replace the single hardcoded grocery store with a multi-store system where each store has its own aisles, staple items, and shopping list.

**Architecture:** A new `stores` blueprint replaces the `grocery` blueprint. All routes become store-scoped under `/stores/<id>/`. An Alembic migration seeds a default "Grocery" store and re-assigns all existing data to it. The navbar Grocery dropdown is replaced by a dynamic Stores dropdown.

**Tech Stack:** Flask, SQLAlchemy 2.0, Flask-Migrate/Alembic, Bootstrap 5, Jinja2

---

## Data Model

### New table: `Store`

| Column | Type | Notes |
|---|---|---|
| `id` | Integer | Primary key |
| `name` | String(128) | Unique, not null |
| `created_at` | DateTime | UTC default |

### Modified tables

`StoreSection`, `StapleItem`, and `ShoppingListItem` each gain:

| Column | Type | Notes |
|---|---|---|
| `store_id` | Integer | FK → `store.id`, NOT NULL, `ondelete='CASCADE'` |

`StoreSection.name` uniqueness changes from globally unique to unique per store (unique constraint on `(store_id, name)`).

Deleting a store cascades to its sections, staples, and shopping list items. Store deletion is not exposed in the UI for now.

### Migration

1. Create `store` table
2. Insert a default "Grocery" store
3. Add `store_id` column (nullable) to the three tables
4. Backfill all existing rows with the default store's id
5. Alter `store_id` to NOT NULL
6. Drop the global unique constraint on `store_section.name`
7. Add unique constraint on `(store_section.store_id, store_section.name)`

---

## Routes & Blueprint

New `stores` blueprint registered at `/stores`. All routes are login-required.

| Method | URL | Purpose |
|---|---|---|
| GET | `/stores/` | List all stores; inline add-store form |
| POST | `/stores/` | Create a new store |
| GET | `/stores/<id>/` | Manage shopping list for this store |
| GET | `/stores/<id>/shop` | Shop view for this store |
| POST | `/stores/<id>/list/done` | Clear shopping list (done shopping) |
| GET | `/stores/<id>/manage` | Store settings: rename + manage aisles |
| POST | `/stores/<id>/manage/name` | Rename the store (JSON, returns `{ok, name}`) |
| POST | `/stores/<id>/sections` | Add an aisle (JSON) |
| POST | `/stores/<id>/sections/<sid>/edit` | Rename an aisle (JSON) |
| POST | `/stores/<id>/sections/<sid>/delete` | Delete an aisle (form POST + redirect) |
| POST | `/stores/<id>/staples` | Add a staple item (JSON) |
| POST | `/stores/<id>/staples/<sid>/toggle` | Toggle staple on/off shopping list (JSON) |
| POST | `/stores/<id>/staples/<sid>/delete` | Delete a staple (form POST + redirect) |
| POST | `/stores/<id>/list/add` | Add one-off shopping list item (JSON) |
| POST | `/stores/<id>/list/<iid>/toggle` | Toggle list item checked (JSON) |
| POST | `/stores/<id>/list/<iid>/delete` | Delete list item (JSON) |

Interaction style follows existing conventions: fetch/JSON for snappy actions, form POST + redirect for destructive/infrequent actions.

---

## Templates & UI

All templates live under `templates/stores/` and follow existing Bootstrap 5 + Jinja2 patterns.

- **`stores/index.html`** — Lists all stores as links. Inline form to add a new store by name.
- **`stores/home.html`** — Shopping list management for one store. Mirrors current `grocery/home.html`; staples and ad-hoc items scoped to this store.
- **`stores/shop.html`** — Shop view for one store. Mirrors current `grocery/shop.html`; items scoped to this store.
- **`stores/manage.html`** — Store settings page. "Store name" edit field at top, followed by aisle management (add/rename/delete). Mirrors current `grocery/sections.html` for the aisle section.

### Navbar

The hardcoded "Grocery" dropdown is replaced by a **Stores** dropdown listing all stores dynamically. Store list is injected via a `context_processor` registered on the `stores` blueprint so it is available in every template without explicit route-level queries.

### JS URL pattern

All in-page JS URLs follow the existing pattern — emitted via `url_for(...) | tojson` and never hardcoded:

```javascript
const STORE_BASE = {{ url_for('stores.index', store_id=store.id) | tojson }};
```

---

## Out of Scope

- Store deletion UI (can be added later)
- Home page shortcuts (separate spec)
- Per-user store preferences
