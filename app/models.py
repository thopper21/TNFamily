# app/models.py
from datetime import datetime, timezone
from flask_login import UserMixin
from app.extensions import db, login_manager


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    google_id = db.Column(db.String(128), unique=True, nullable=False)
    email = db.Column(db.String(256), unique=True, nullable=False)
    name = db.Column(db.String(256), nullable=False)
    profile_picture_url = db.Column(db.String(512))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))


@login_manager.user_loader
def load_user(user_id):
    try:
        return db.session.get(User, int(user_id))
    except (ValueError, TypeError):
        return None


class StoreSection(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), unique=True, nullable=False)


class StapleItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False)
    section_id = db.Column(
        db.Integer, db.ForeignKey('store_section.id', ondelete='SET NULL'), nullable=True
    )
    on_shopping_list = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    section = db.relationship('StoreSection', foreign_keys=[section_id])
    shopping_list_item = db.relationship(
        'ShoppingListItem',
        back_populates='staple',
        uselist=False,
        cascade='all, delete-orphan',
    )


class ShoppingListItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False)
    section_id = db.Column(
        db.Integer, db.ForeignKey('store_section.id', ondelete='SET NULL'), nullable=True
    )
    staple_item_id = db.Column(
        db.Integer, db.ForeignKey('staple_item.id', ondelete='CASCADE'), nullable=True
    )
    checked = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    section = db.relationship('StoreSection', foreign_keys=[section_id])
    staple = db.relationship('StapleItem', back_populates='shopping_list_item')
