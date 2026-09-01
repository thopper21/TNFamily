# Home Page Shortcuts Design

**Goal:** Add pinned-store shortcuts to the home page so users can jump directly to a store's shopping list without navigating through the Stores dropdown.

**Architecture:** A `pinned` boolean is added to the `Store` model. The manage page gets a pin toggle. The home page queries pinned stores with their current item counts and renders a card per store.

**Tech Stack:** Flask, SQLAlchemy 2.0, Flask-Migrate/Alembic, Bootstrap 5, Jinja2

---

## Data Model

### Modified table: `Store`

Add one column:

| Column | Type | Notes |
|---|---|---|
| `pinned` | Boolean | NOT NULL, default `False` |

### Migration

1. Add `pinned` column (nullable)
2. Backfill all existing rows with `False`
3. Alter to NOT NULL

---

## Routes

| Method | URL | Purpose |
|---|---|---|
| POST | `/stores/<id>/manage/pin` | Toggle store pinned state — JSON `{ok, pinned}` |
| GET | `/` | Home page — updated to include pinned stores + item counts |

The home blueprint's `GET /` route is the only change to the home blueprint. It queries `Store.pinned == True` and for each store fetches the current shopping list item count.

---

## Templates & UI

### `templates/home/index.html`

- Welcome card is slimmed to a compact header strip: smaller avatar (40×40), `h5` heading, tighter padding (`py-2 px-3`), no subtitle — reads as a greeting, not a hero section
- Below the welcome strip: a row of Bootstrap cards for pinned stores
  - Card header: store name
  - Card body: item count badge ("3 items on list" / "Empty list")
  - Card footer: "Go to list" button → `/stores/<id>/`
- If no stores are pinned, nothing extra is shown below the welcome strip

### `templates/stores/manage.html`

- In the Store Name card, add a "Pin to home page" / "Unpin from home page" button
- Button state reflects current `store.pinned` value on page load
- Click sends `POST /stores/<id>/manage/pin` (fetch/JSON), updates button text in place on success

---

## Out of Scope

- Shortcut ordering / drag-to-reorder (can add a `pin_order` integer to `Store` later)
- Per-user pin preferences (all users see the same pinned stores)
- Shop-view shortcut (only list management for now)
