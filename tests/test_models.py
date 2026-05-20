# tests/test_models.py
import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from app.models import User
from app.extensions import db


def test_user_can_be_created(app):
    user = User(google_id='g-1', email='a@b.com', name='Alice')
    db.session.add(user)
    db.session.commit()
    saved = db.session.get(User, user.id)
    assert saved.email == 'a@b.com'
    assert saved.google_id == 'g-1'


def test_created_at_is_set_automatically(app):
    user = User(google_id='g-2', email='b@b.com', name='Bob')
    db.session.add(user)
    db.session.commit()
    assert isinstance(user.created_at, datetime)


def test_created_at_default_is_timezone_aware(app):
    from app.models import StapleItem, ShoppingListItem
    # SQLAlchemy wraps zero-arg callables as lambda ctx: fn(), so pass None as ctx.
    # SQLite strips tzinfo on read, so we test the default callable directly.
    for model_class in (User, StapleItem, ShoppingListItem):
        default_fn = model_class.__table__.c.created_at.default.arg
        result = default_fn(None)
        assert result.tzinfo is not None, f"{model_class.__name__}.created_at default is not tz-aware"


def test_profile_picture_is_optional(app):
    user = User(google_id='g-3', email='c@b.com', name='Carol')
    db.session.add(user)
    db.session.commit()
    assert user.profile_picture_url is None


def test_google_id_is_unique(app):
    u1 = User(google_id='same', email='d@b.com', name='Dave')
    u2 = User(google_id='same', email='e@b.com', name='Eve')
    db.session.add(u1)
    db.session.commit()
    db.session.add(u2)
    with pytest.raises(IntegrityError):
        db.session.commit()


def test_user_is_active_by_default(app):
    user = User(google_id='g-4', email='f@b.com', name='Frank')
    db.session.add(user)
    db.session.commit()
    assert user.is_active is True
