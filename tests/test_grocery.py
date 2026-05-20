# tests/test_grocery.py
import pytest
from sqlalchemy import func, select, update
from app.models import StoreSection, StapleItem, ShoppingListItem
from app.extensions import db


def test_staple_item_defaults(app):
    with app.app_context():
        staple = StapleItem(name='Milk')
        db.session.add(staple)
        db.session.commit()
        assert db.session.get(StapleItem, staple.id).name == 'Milk'
        assert staple.shopping_list_item is None


def test_delete_staple_cascades_to_shopping_list_item(app):
    with app.app_context():
        staple = StapleItem(name='Milk')
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
        db.session.execute(update(StapleItem).where(StapleItem.section_id == section.id).values(section_id=None))
        db.session.execute(update(ShoppingListItem).where(ShoppingListItem.section_id == section.id).values(section_id=None))
        db.session.delete(section)
        db.session.commit()
        assert db.session.get(StapleItem, staple_id).section_id is None
        assert db.session.get(ShoppingListItem, item_id).section_id is None


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


def test_sections_page_returns_200(logged_in_client):
    resp = logged_in_client.get('/grocery/sections')
    assert resp.status_code == 200


def test_sections_page_uses_grocery_base_url_pattern(logged_in_client):
    resp = logged_in_client.get('/grocery/sections')
    assert b"replace('/0/'," not in resp.data


def test_add_section(logged_in_client, app):
    resp = logged_in_client.post('/grocery/sections', json={'name': 'Dairy'})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['ok'] is True
    assert data['name'] == 'Dairy'
    with app.app_context():
        assert db.session.scalar(select(StoreSection).where(StoreSection.name == 'Dairy')) is not None


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


def test_add_staple(logged_in_client, app):
    resp = logged_in_client.post('/grocery/staples', json={'name': 'Eggs'})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['ok'] is True
    assert data['name'] == 'Eggs'
    with app.app_context():
        assert db.session.scalar(select(StapleItem).where(StapleItem.name == 'Eggs')) is not None


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
        assert db.session.scalar(select(ShoppingListItem).where(ShoppingListItem.staple_item_id == staple_id)) is not None


def test_toggle_staple_off_deletes_shopping_list_item(logged_in_client, app):
    with app.app_context():
        staple = StapleItem(name='Milk')
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
        assert db.session.scalar(select(ShoppingListItem).where(ShoppingListItem.staple_item_id == staple_id)) is None


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


def test_toggle_staple_not_found_returns_404(logged_in_client):
    resp = logged_in_client.post('/grocery/staples/9999/toggle')
    assert resp.status_code == 404
    assert resp.get_json()['ok'] is False


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
        item = db.session.scalar(select(ShoppingListItem).where(ShoppingListItem.name == 'Sriracha'))
        assert item is not None
        assert item.staple_item_id is None


def test_add_one_off_item_missing_name_returns_400(logged_in_client):
    resp = logged_in_client.post('/grocery/list/add', json={'name': ''})
    assert resp.status_code == 400


def test_shop_view_returns_200(logged_in_client):
    resp = logged_in_client.get('/grocery/shop')
    assert resp.status_code == 200


def test_error_toast_present_exactly_once_on_grocery_pages(logged_in_client):
    for path in ['/grocery/', '/grocery/sections', '/grocery/shop']:
        resp = logged_in_client.get(path)
        count = resp.data.count(b'id="error-toast"')
        assert count == 1, f"Expected 1 error toast on {path}, got {count}"


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


def test_toggle_list_item_not_found_returns_404(logged_in_client):
    resp = logged_in_client.post('/grocery/list/9999/toggle')
    assert resp.status_code == 404
    assert resp.get_json()['ok'] is False


def test_done_shopping_clears_list_and_resets_staples(logged_in_client, app):
    with app.app_context():
        staple = StapleItem(name='Milk')
        db.session.add(staple)
        db.session.flush()
        db.session.add(ShoppingListItem(name='Milk', staple_item_id=staple.id))
        db.session.add(ShoppingListItem(name='Sriracha'))
        db.session.commit()
        staple_id = staple.id
    resp = logged_in_client.post('/grocery/list/done')
    assert resp.status_code == 302
    with app.app_context():
        assert db.session.scalar(select(func.count()).select_from(ShoppingListItem)) == 0
        assert db.session.get(StapleItem, staple_id).shopping_list_item is None


def test_add_staple_invalid_section_returns_400(logged_in_client):
    resp = logged_in_client.post('/grocery/staples', json={'name': 'Eggs', 'section_id': 9999})
    assert resp.status_code == 400
    assert resp.get_json()['ok'] is False


def test_add_one_off_item_invalid_section_returns_400(logged_in_client):
    resp = logged_in_client.post('/grocery/list/add', json={'name': 'Sriracha', 'section_id': 9999})
    assert resp.status_code == 400
    assert resp.get_json()['ok'] is False


def test_grocery_index_shows_ad_hoc_items(logged_in_client, app):
    with app.app_context():
        db.session.add(ShoppingListItem(name='Sriracha'))
        db.session.commit()
    resp = logged_in_client.get('/grocery/')
    assert resp.status_code == 200
    assert b'Sriracha' in resp.data


def test_grocery_index_does_not_show_staple_list_items(logged_in_client, app):
    import re
    with app.app_context():
        staple = StapleItem(name='Milk')
        db.session.add(staple)
        db.session.flush()
        db.session.add(ShoppingListItem(name='Milk', staple_item_id=staple.id))
        db.session.commit()
    resp = logged_in_client.get('/grocery/')
    assert resp.status_code == 200
    # Staple-linked items must not appear as ad-hoc list entries
    assert not re.search(rb'id="ad-hoc-\d+"', resp.data)


def test_delete_list_item(logged_in_client, app):
    with app.app_context():
        item = ShoppingListItem(name='Sriracha')
        db.session.add(item)
        db.session.commit()
        item_id = item.id
    resp = logged_in_client.post(f'/grocery/list/{item_id}/delete')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['ok'] is True
    assert 'shopping_count' in data
    with app.app_context():
        assert db.session.get(ShoppingListItem, item_id) is None


def test_delete_list_item_not_found_returns_404(logged_in_client):
    resp = logged_in_client.post('/grocery/list/9999/delete')
    assert resp.status_code == 404
    assert resp.get_json()['ok'] is False


def test_staple_list_items_have_data_name_attribute(logged_in_client, app):
    with app.app_context():
        db.session.add(StapleItem(name='Milk'))
        db.session.commit()
    resp = logged_in_client.get('/grocery/')
    assert resp.status_code == 200
    assert b'data-name="Milk"' in resp.data


def test_staple_list_items_have_data_section_attribute(logged_in_client, app):
    with app.app_context():
        section = StoreSection(name='Dairy')
        db.session.add(section)
        db.session.flush()
        db.session.add(StapleItem(name='Milk', section_id=section.id))
        db.session.commit()
    resp = logged_in_client.get('/grocery/')
    assert resp.status_code == 200
    assert b'data-section="Dairy"' in resp.data


def test_staple_list_items_without_section_have_empty_data_section(logged_in_client, app):
    with app.app_context():
        db.session.add(StapleItem(name='Eggs'))
        db.session.commit()
    resp = logged_in_client.get('/grocery/')
    assert resp.status_code == 200
    assert b'data-section=""' in resp.data


def test_sort_toggle_buttons_present(logged_in_client):
    resp = logged_in_client.get('/grocery/')
    assert resp.status_code == 200
    assert b'sort-az' in resp.data
    assert b'sort-section' in resp.data


# --- edit section name (issue #3) ---

def test_edit_section_renames_section(logged_in_client, app):
    with app.app_context():
        section = StoreSection(name='Dairy')
        db.session.add(section)
        db.session.commit()
        section_id = section.id
    resp = logged_in_client.post(f'/grocery/sections/{section_id}/edit', json={'name': 'Frozen'})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['ok'] is True
    assert data['id'] == section_id
    assert data['name'] == 'Frozen'
    with app.app_context():
        assert db.session.get(StoreSection, section_id).name == 'Frozen'


def test_edit_section_preserves_staple_assignments(logged_in_client, app):
    with app.app_context():
        section = StoreSection(name='Dairy')
        db.session.add(section)
        db.session.flush()
        staple = StapleItem(name='Milk', section_id=section.id)
        db.session.add(staple)
        db.session.commit()
        section_id, staple_id = section.id, staple.id
    logged_in_client.post(f'/grocery/sections/{section_id}/edit', json={'name': 'Frozen'})
    with app.app_context():
        assert db.session.get(StapleItem, staple_id).section_id == section_id


def test_edit_section_not_found_returns_404(logged_in_client):
    resp = logged_in_client.post('/grocery/sections/9999/edit', json={'name': 'Produce'})
    assert resp.status_code == 404
    assert resp.get_json()['ok'] is False


def test_edit_section_blank_name_returns_400(logged_in_client, app):
    with app.app_context():
        section = StoreSection(name='Dairy')
        db.session.add(section)
        db.session.commit()
        section_id = section.id
    resp = logged_in_client.post(f'/grocery/sections/{section_id}/edit', json={'name': '  '})
    assert resp.status_code == 400
    assert resp.get_json()['ok'] is False


def test_edit_section_duplicate_name_returns_409(logged_in_client, app):
    with app.app_context():
        db.session.add(StoreSection(name='Dairy'))
        db.session.add(StoreSection(name='Produce'))
        db.session.commit()
        section_id = db.session.scalar(select(StoreSection).where(StoreSection.name == 'Dairy')).id
    resp = logged_in_client.post(f'/grocery/sections/{section_id}/edit', json={'name': 'Produce'})
    assert resp.status_code == 409
    assert resp.get_json()['ok'] is False


def test_edit_section_same_name_is_ok(logged_in_client, app):
    """Renaming to the same name should succeed (no-op)."""
    with app.app_context():
        section = StoreSection(name='Dairy')
        db.session.add(section)
        db.session.commit()
        section_id = section.id
    resp = logged_in_client.post(f'/grocery/sections/{section_id}/edit', json={'name': 'Dairy'})
    assert resp.status_code == 200
    assert resp.get_json()['ok'] is True


def test_edit_section_requires_login(client, app):
    with app.app_context():
        section = StoreSection(name='Dairy')
        db.session.add(section)
        db.session.commit()
        section_id = section.id
    resp = client.post(f'/grocery/sections/{section_id}/edit', json={'name': 'Frozen'})
    assert resp.status_code == 302
    assert '/auth/login' in resp.headers['Location']


# --- staple on-list indicator (issue #2) ---

def test_staple_on_list_shows_on_list_badge(logged_in_client, app):
    with app.app_context():
        staple = StapleItem(name='Milk')
        db.session.add(staple)
        db.session.flush()
        db.session.add(ShoppingListItem(name='Milk', staple_item_id=staple.id))
        db.session.commit()
    resp = logged_in_client.get('/grocery/')
    assert resp.status_code == 200
    assert b'On list' in resp.data


def test_staple_on_list_no_strikethrough(logged_in_client, app):
    with app.app_context():
        staple = StapleItem(name='Milk')
        db.session.add(staple)
        db.session.flush()
        db.session.add(ShoppingListItem(name='Milk', staple_item_id=staple.id))
        db.session.commit()
    resp = logged_in_client.get('/grocery/')
    assert b'text-decoration-line-through' not in resp.data


def test_staple_not_on_list_no_on_list_badge(logged_in_client, app):
    with app.app_context():
        db.session.add(StapleItem(name='Eggs'))
        db.session.commit()
    resp = logged_in_client.get('/grocery/')
    assert resp.status_code == 200
    # Check the rendered element, not just the string (which also appears in JS source)
    assert b'staple-on-list-badge">On list' not in resp.data


# --- sections XSS safety ---

def test_sections_page_escapes_html_in_section_names(logged_in_client, app):
    with app.app_context():
        db.session.add(StoreSection(name='<script>alert(1)</script>'))
        db.session.commit()
    resp = logged_in_client.get('/grocery/sections')
    assert resp.status_code == 200
    assert b'<script>alert(1)</script>' not in resp.data
    assert b'&lt;script&gt;' in resp.data


