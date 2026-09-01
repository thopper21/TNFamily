def test_home_returns_200_when_authenticated(logged_in_client):
    response = logged_in_client.get('/')
    assert response.status_code == 200


def test_home_contains_welcome(logged_in_client):
    response = logged_in_client.get('/')
    assert b'Welcome' in response.data


def test_home_redirects_unauthenticated_to_login(client):
    response = client.get('/')
    assert response.status_code == 302
    assert '/auth/login' in response.headers['Location']


def test_page_has_favicon_link(logged_in_client):
    response = logged_in_client.get('/')
    assert b'rel="icon"' in response.data


def test_home_shows_pinned_store_shortcut(logged_in_client, app):
    from app.models import Store
    from app.extensions import db
    with app.app_context():
        s = Store(name='Target', pinned=True)
        db.session.add(s)
        db.session.commit()
    resp = logged_in_client.get('/')
    assert b'Target' in resp.data
    assert b'Go to list' in resp.data


def test_home_does_not_show_unpinned_store(logged_in_client, app):
    from app.models import Store
    from app.extensions import db
    with app.app_context():
        s = Store(name='Hidden Store', pinned=False)
        db.session.add(s)
        db.session.commit()
    resp = logged_in_client.get('/')
    assert b'Go to list' not in resp.data


def test_home_shows_item_count_for_pinned_store(logged_in_client, app):
    from app.models import Store, ShoppingListItem
    from app.extensions import db
    with app.app_context():
        s = Store(name='Costco', pinned=True)
        db.session.add(s)
        db.session.flush()
        db.session.add(ShoppingListItem(name='Milk', store_id=s.id))
        db.session.add(ShoppingListItem(name='Eggs', store_id=s.id))
        db.session.commit()
    resp = logged_in_client.get('/')
    assert b'2' in resp.data
