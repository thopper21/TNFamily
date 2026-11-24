# tests/test_nav.py
from app.extensions import db
from app.models import Store


def test_navbar_has_shopping_dropdown(logged_in_client):
    resp = logged_in_client.get('/stores/')
    assert resp.status_code == 200
    assert b'dropdown-toggle' in resp.data
    assert b'Shopping' in resp.data


def test_navbar_shopping_dropdown_has_manage_shopping(logged_in_client):
    resp = logged_in_client.get('/stores/')
    assert b'Manage shopping' in resp.data


def test_navbar_shopping_dropdown_lists_stores(logged_in_client, app):
    with app.app_context():
        db.session.add(Store(name='Target'))
        db.session.commit()
    resp = logged_in_client.get('/stores/')
    assert b'Target' in resp.data


def test_navbar_shopping_dropdown_visible_on_shop_page(logged_in_client, store):
    resp = logged_in_client.get(f'/stores/{store.id}/shop')
    assert resp.status_code == 200
    assert b'dropdown-toggle' in resp.data
    assert b'Manage shopping' in resp.data
