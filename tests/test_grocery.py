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
        item = ShoppingListItem.query.filter_by(name='Sriracha').first()
        assert item is not None
        assert item.staple_item_id is None


def test_add_one_off_item_missing_name_returns_400(logged_in_client):
    resp = logged_in_client.post('/grocery/list/add', json={'name': ''})
    assert resp.status_code == 400


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


def test_toggle_list_item_not_found_returns_404(logged_in_client):
    resp = logged_in_client.post('/grocery/list/9999/toggle')
    assert resp.status_code == 404
    assert resp.get_json()['ok'] is False


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
        staple = StapleItem(name='Milk', on_shopping_list=True)
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
        section_id = StoreSection.query.filter_by(name='Dairy').first().id
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
