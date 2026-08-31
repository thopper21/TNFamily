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
