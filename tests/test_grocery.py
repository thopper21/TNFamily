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
