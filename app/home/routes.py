# app/home/routes.py
from flask import render_template
from flask_login import current_user, login_required
from sqlalchemy import func, select

from app.extensions import db
from app.home import home_bp
from app.models import ShoppingListItem, Store


@home_bp.route('/')
@login_required
def index():
    pinned = db.session.scalars(
        select(Store).where(Store.pinned == True).order_by(Store.name)  # noqa: E712
    ).all()
    counts = {}
    if pinned:
        counts = {
            store_id: count
            for store_id, count in db.session.execute(
                select(ShoppingListItem.store_id, func.count().label('n'))
                .where(ShoppingListItem.store_id.in_([s.id for s in pinned]))
                .group_by(ShoppingListItem.store_id)
            ).all()
        }
    pinned_stores = [(s, counts.get(s.id, 0)) for s in pinned]
    return render_template('home/index.html', user=current_user, pinned_stores=pinned_stores)
