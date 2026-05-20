# tests/test_nav.py


def test_navbar_has_grocery_dropdown(logged_in_client):
    resp = logged_in_client.get('/grocery/')
    assert resp.status_code == 200
    assert b'dropdown-toggle' in resp.data


def test_navbar_grocery_dropdown_has_manage_list(logged_in_client):
    resp = logged_in_client.get('/grocery/')
    assert b'Manage List' in resp.data


def test_navbar_grocery_dropdown_has_shop(logged_in_client):
    resp = logged_in_client.get('/grocery/')
    assert b'Shop' in resp.data


def test_navbar_no_standalone_shopping_link(logged_in_client):
    resp = logged_in_client.get('/grocery/')
    assert b'>Shopping<' not in resp.data


def test_navbar_grocery_dropdown_visible_on_shop_page(logged_in_client):
    resp = logged_in_client.get('/grocery/shop')
    assert resp.status_code == 200
    assert b'dropdown-toggle' in resp.data
    assert b'Manage List' in resp.data
