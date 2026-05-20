# Grocery List Feature Design

## Goal

Add a grocery list management feature with two views: an at-home planning view and an in-store shopping view.

## Architecture

A new `grocery` Flask blueprint (`app/grocery/`) follows the existing `auth` and `home` blueprint pattern. Three new SQLAlchemy models are added to `app/models.py`. Interactive actions (toggling items, adding items) use vanilla `fetch` calls to JSON endpoints; infrequent destructive actions (delete, done shopping) use standard HTML form POST with redirect.

## Tech Stack

Flask blueprints, SQLAlchemy, Bootstrap 5 accordion, vanilla JS `fetch`

---

## Data Model

Three new models added to `app/models.py`:

### `StoreSection`
```
id    Integer, primary key
name  String(128), unique, not null
```
The user-managed catalog of grocery store sections (e.g. "Produce", "Dairy"). Sections are displayed in alphabetical order. Infrequently created or deleted via the section management page.

### `StapleItem`
```
id                Integer, primary key
name              String(256), not null
section_id        FK → StoreSection, nullable, on_delete SET NULL
on_shopping_list  Boolean, not null, default False
created_at        DateTime, default utcnow
```
The persistent staple catalog — items the family regularly buys. `on_shopping_list` is `True` while the item has been added to the current shopping list. Toggling a staple off (unchecking it on the at-home view) deletes its linked `ShoppingListItem` and resets `on_shopping_list = False`.

### `ShoppingListItem`
```
id              Integer, primary key
name            String(256), not null
section_id      FK → StoreSection, nullable, on_delete SET NULL
staple_item_id  FK → StapleItem, nullable, on_delete CASCADE
checked         Boolean, not null, default False
created_at      DateTime, default utcnow
```
The active shopping list. One-off items have `staple_item_id = NULL`. Deleting a `StapleItem` cascades to its linked `ShoppingListItem`. "Done shopping" deletes all rows from this table and resets all `StapleItem.on_shopping_list` to `False`.

---

## Blueprint & Routes

New blueprint at `app/grocery/`, registered in the app factory.

| Method | Path | Description | Response |
|---|---|---|---|
| `GET` | `/grocery/` | At-home view | HTML |
| `POST` | `/grocery/staples` | Add a new staple item | JSON |
| `POST` | `/grocery/staples/<id>/toggle` | Add to / remove from shopping list | JSON |
| `POST` | `/grocery/staples/<id>/delete` | Delete a staple permanently | Redirect |
| `POST` | `/grocery/list/add` | Add a one-off item to the shopping list | JSON |
| `POST` | `/grocery/list/<id>/toggle` | Check / uncheck a shopping list item | JSON |
| `POST` | `/grocery/list/done` | Clear list, reset staples | Redirect |
| `GET` | `/grocery/shop` | Shopping view | HTML |
| `GET` | `/grocery/sections` | Section management page | HTML |
| `POST` | `/grocery/sections` | Create a new section | JSON |
| `POST` | `/grocery/sections/<id>/delete` | Delete a section | Redirect |

All routes require `@login_required`.

JSON toggle endpoints return `{"ok": true}` on success or `{"ok": false, "error": "..."}` on failure, with appropriate HTTP status codes.

---

## Views

### At-home view (`/grocery/`)

Two panels — side by side on desktop (Bootstrap `col-md-6`), stacked on mobile.

**Staple items panel**
- Each staple is a checkbox row showing the item name and an optional section badge.
- Checking a staple calls `POST /grocery/staples/<id>/toggle`, which creates a `ShoppingListItem` linked to it and sets `on_shopping_list = True`. The row is greyed out and re-sorted to the bottom client-side.
- Unchecking a staple reverses the toggle: deletes the linked `ShoppingListItem` and resets `on_shopping_list = False`.
- A delete button on each row submits `POST /grocery/staples/<id>/delete` (with confirmation) and removes the row.
- An inline add form at the bottom: name field + optional section dropdown + "Add" button. Submits via `fetch` to `POST /grocery/staples`; on success, clears the form and prepends the new item.
- A "Manage sections" link below the panel opens `/grocery/sections`.

**Add to list panel**
- A form with a name field, optional section dropdown, and "Add to list" button. Submits via `fetch` to `POST /grocery/list/add`; on success, clears the form and updates the item count badge.
- A count badge ("X items on your list") and a prominent "Start Shopping →" button linking to `/grocery/shop`.

### Shopping view (`/grocery/shop`)

Optimised for phone use in-store.

- A "Done Shopping" button at the top submits `POST /grocery/list/done` (standard form POST, redirects to `/grocery/`).
- Items grouped by section, each section rendered as a Bootstrap 5 accordion panel, all expanded by default. Items with no section appear in an "Other" group at the bottom.
- Within each panel, unchecked items appear first; checked items are crossed out (`text-decoration: line-through`), faded (`opacity: 0.5`), and sorted to the bottom.
- Tapping an item row calls `POST /grocery/list/<id>/toggle` via `fetch` and re-sorts the row client-side.

### Section management (`/grocery/sections`)

Minimal page linked from the at-home view.

- List of existing sections, each with a delete button (standard form POST to `POST /grocery/sections/<id>/delete`).
- An inline add form: name field + "Add" button, submits via `fetch` to `POST /grocery/sections`; on success, appends the new section to the list.
- Deleting a section sets `section_id = NULL` on any items referencing it (via `on_delete SET NULL` at the DB level).

### Navigation

The navbar (currently in `templates/home/index.html`) is moved to `templates/base.html` so it appears on all authenticated pages. Two new links are added:
- **Grocery** → `/grocery/`
- **Shopping** → `/grocery/shop`

The navbar links are only rendered when the user is authenticated (`current_user.is_authenticated`).

---

## Interactivity

Vanilla JS `fetch` (no framework, no build step) is used for actions that benefit from no-reload UX:

| Action | Mechanism |
|---|---|
| Toggle staple on/off | `fetch POST`, row re-sorted client-side |
| Toggle shopping list item | `fetch POST`, row re-sorted client-side |
| Add new staple | `fetch POST`, form cleared, new row prepended |
| Add one-off item | `fetch POST`, form cleared, count badge updated |
| Add new section | `fetch POST`, form cleared, new section appended |

Standard HTML form POST + redirect for infrequent/destructive actions: delete staple, delete section, "Done shopping".

On `fetch` failure, the UI snaps back to its previous state and shows a Bootstrap toast error message.

---

## Testing

New file `tests/test_grocery.py` using the existing `logged_in_client` fixture and in-memory SQLite. No changes to `conftest.py`.

**Coverage:**
- Data model: cascade delete (deleting a `StapleItem` removes its linked `ShoppingListItem`), `SET NULL` on section delete
- At-home view: add staple, toggle staple on (creates `ShoppingListItem`), toggle staple off (deletes `ShoppingListItem`), add one-off item, delete staple
- Shopping view: items returned grouped by section correctly, toggle shopping list item
- "Done shopping": all `ShoppingListItem` rows deleted, all `StapleItem.on_shopping_list` reset to `False`
- Section management: add section, delete section
- Auth: all grocery routes return 302 redirect to login when unauthenticated
