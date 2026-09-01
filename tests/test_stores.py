import pytest
from sqlalchemy import func, select, update
from app.extensions import db
from app.models import ShoppingListItem, StapleItem, Store, StoreSection


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
        db.session.add(StoreSection(name='Dairy', store_id=other.id))
        db.session.commit()  # must not raise


# ---------------------------------------------------------------------------
# Task 2: stores blueprint – list / create / rename
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Task 3: shopping list management
# ---------------------------------------------------------------------------

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
        other = Store(name='Other')
        db.session.add(other)
        db.session.flush()
        section = StoreSection(name='Dairy', store_id=other.id)
        db.session.add(section)
        db.session.commit()
        section_id = section.id
    resp = logged_in_client.post(
        f'/stores/{store.id}/staples', json={'name': 'Milk', 'section_id': section_id}
    )
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
            select(ShoppingListItem).where(
                ShoppingListItem.name == 'Sriracha',
                ShoppingListItem.store_id == store.id,
            )
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


# ---------------------------------------------------------------------------
# Task 4: shop view
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Task 5: manage page
# ---------------------------------------------------------------------------

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
            select(StoreSection).where(
                StoreSection.name == 'Dairy', StoreSection.store_id == store.id
            )
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
    resp = logged_in_client.post(
        f'/stores/{store.id}/sections/{section_id}/edit', json={'name': 'Frozen'}
    )
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
            select(StoreSection).where(
                StoreSection.name == 'Dairy', StoreSection.store_id == store.id
            )
        ).id
    resp = logged_in_client.post(
        f'/stores/{store.id}/sections/{section_id}/edit', json={'name': 'Produce'}
    )
    assert resp.status_code == 409


def test_edit_section_same_name_is_ok(logged_in_client, store, app):
    with app.app_context():
        section = StoreSection(name='Dairy', store_id=store.id)
        db.session.add(section)
        db.session.commit()
        section_id = section.id
    resp = logged_in_client.post(
        f'/stores/{store.id}/sections/{section_id}/edit', json={'name': 'Dairy'}
    )
    assert resp.status_code == 200
    assert resp.get_json()['ok'] is True


def test_toggle_pin_pins_store(logged_in_client, store, app):
    resp = logged_in_client.post(f'/stores/{store.id}/manage/pin')
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['ok'] is True
    assert data['pinned'] is True
    with app.app_context():
        assert db.session.get(Store, store.id).pinned is True


def test_toggle_pin_unpins_store(logged_in_client, store, app):
    store.pinned = True
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
    store.pinned = True
    db.session.commit()
    resp = logged_in_client.get(f'/stores/{store.id}/manage')
    assert b'Unpin from home page' in resp.data


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


def test_error_toast_present_on_store_pages(logged_in_client, store):
    for path in [f'/stores/{store.id}/', f'/stores/{store.id}/shop', f'/stores/{store.id}/manage']:
        resp = logged_in_client.get(path)
        count = resp.data.count(b'id="error-toast"')
        assert count == 1, f"Expected 1 error toast on {path}, got {count}"
