# app/stores/routes.py
from flask import jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import joinedload

from app.extensions import db
from app.models import ShoppingListItem, StapleItem, Store, StoreSection
from app.stores import stores_bp


def _resolve_section_id(data, store_id):
    section_id = data.get('section_id') or None
    if section_id:
        section = db.session.get(StoreSection, section_id)
        if not section or section.store_id != store_id:
            return None, (jsonify({'ok': False, 'error': 'Section not found'}), 400)
    return section_id, None


@stores_bp.app_context_processor
def inject_all_stores():
    if current_user.is_authenticated:
        stores = db.session.scalars(select(Store).order_by(Store.name)).all()
    else:
        stores = []
    return {'all_stores': stores}


@stores_bp.route('/', methods=['GET'])
@login_required
def stores_list():
    stores = db.session.scalars(select(Store).order_by(Store.name)).all()
    return render_template('stores/index.html', stores=stores)


@stores_bp.route('/', methods=['POST'])
@login_required
def create_store():
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'ok': False, 'error': 'Name is required'}), 400
    if db.session.scalar(select(Store).where(Store.name == name)):
        return jsonify({'ok': False, 'error': 'Store already exists'}), 409
    store = Store(name=name)
    db.session.add(store)
    db.session.commit()
    return jsonify({'ok': True, 'id': store.id, 'name': store.name})


@stores_bp.route('/<int:store_id>/manage/name', methods=['POST'])
@login_required
def rename_store(store_id):
    store = db.session.get(Store, store_id)
    if not store:
        return jsonify({'ok': False, 'error': 'Not found'}), 404
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'ok': False, 'error': 'Name is required'}), 400
    if name != store.name and db.session.scalar(select(Store).where(Store.name == name)):
        return jsonify({'ok': False, 'error': 'Store already exists'}), 409
    store.name = name
    db.session.commit()
    return jsonify({'ok': True, 'id': store.id, 'name': store.name})


@stores_bp.route('/<int:store_id>/')
@login_required
def store_index(store_id):
    store = db.session.get(Store, store_id)
    if not store:
        return redirect(url_for('stores.stores_list'))
    staples = (
        db.session.scalars(
            select(StapleItem)
            .where(StapleItem.store_id == store_id)
            .options(joinedload(StapleItem.shopping_list_item))
            .order_by(StapleItem.name)
        ).unique().all()
    )
    sections = db.session.scalars(
        select(StoreSection)
        .where(StoreSection.store_id == store_id)
        .order_by(StoreSection.name)
    ).all()
    shopping_count = db.session.scalar(
        select(func.count()).select_from(ShoppingListItem)
        .where(ShoppingListItem.store_id == store_id)
    )
    ad_hoc_items = db.session.scalars(
        select(ShoppingListItem)
        .where(
            ShoppingListItem.store_id == store_id,
            ShoppingListItem.staple_item_id == None,  # noqa: E711
        )
        .order_by(ShoppingListItem.created_at.desc())
    ).all()
    return render_template(
        'stores/home.html',
        store=store,
        staples=staples,
        sections=sections,
        shopping_count=shopping_count,
        ad_hoc_items=ad_hoc_items,
    )


@stores_bp.route('/<int:store_id>/staples', methods=['POST'])
@login_required
def add_staple(store_id):
    store = db.session.get(Store, store_id)
    if not store:
        return jsonify({'ok': False, 'error': 'Not found'}), 404
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'ok': False, 'error': 'Name is required'}), 400
    section_id, err = _resolve_section_id(data, store_id)
    if err:
        return err
    staple = StapleItem(name=name, section_id=section_id, store_id=store_id)
    db.session.add(staple)
    db.session.commit()
    return jsonify({
        'ok': True,
        'id': staple.id,
        'name': staple.name,
        'section_id': staple.section_id,
        'section_name': staple.section.name if staple.section else None,
        'on_shopping_list': staple.shopping_list_item is not None,
    })


@stores_bp.route('/<int:store_id>/staples/<int:staple_id>/toggle', methods=['POST'])
@login_required
def toggle_staple(store_id, staple_id):
    staple = db.session.get(StapleItem, staple_id)
    if not staple or staple.store_id != store_id:
        return jsonify({'ok': False, 'error': 'Not found'}), 404
    if staple.shopping_list_item:
        db.session.delete(staple.shopping_list_item)
    else:
        db.session.add(ShoppingListItem(
            name=staple.name,
            section_id=staple.section_id,
            staple_item_id=staple.id,
            store_id=store_id,
        ))
    db.session.commit()
    shopping_count = db.session.scalar(
        select(func.count()).select_from(ShoppingListItem)
        .where(ShoppingListItem.store_id == store_id)
    )
    return jsonify({
        'ok': True,
        'on_shopping_list': staple.shopping_list_item is not None,
        'shopping_count': shopping_count,
    })


@stores_bp.route('/<int:store_id>/staples/<int:staple_id>/delete', methods=['POST'])
@login_required
def delete_staple(store_id, staple_id):
    staple = db.session.get(StapleItem, staple_id)
    if staple and staple.store_id == store_id:
        db.session.delete(staple)
        db.session.commit()
    return redirect(url_for('stores.store_index', store_id=store_id))


@stores_bp.route('/<int:store_id>/list/add', methods=['POST'])
@login_required
def add_to_list(store_id):
    store = db.session.get(Store, store_id)
    if not store:
        return jsonify({'ok': False, 'error': 'Not found'}), 404
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'ok': False, 'error': 'Name is required'}), 400
    section_id, err = _resolve_section_id(data, store_id)
    if err:
        return err
    item = ShoppingListItem(name=name, section_id=section_id, store_id=store_id)
    db.session.add(item)
    db.session.commit()
    shopping_count = db.session.scalar(
        select(func.count()).select_from(ShoppingListItem)
        .where(ShoppingListItem.store_id == store_id)
    )
    return jsonify({'ok': True, 'id': item.id, 'shopping_count': shopping_count})


@stores_bp.route('/<int:store_id>/list/<int:item_id>/delete', methods=['POST'])
@login_required
def delete_list_item(store_id, item_id):
    item = db.session.get(ShoppingListItem, item_id)
    if not item or item.store_id != store_id:
        return jsonify({'ok': False, 'error': 'Not found'}), 404
    db.session.delete(item)
    db.session.commit()
    shopping_count = db.session.scalar(
        select(func.count()).select_from(ShoppingListItem)
        .where(ShoppingListItem.store_id == store_id)
    )
    return jsonify({'ok': True, 'shopping_count': shopping_count})


@stores_bp.route('/<int:store_id>/shop')
@login_required
def store_shop(store_id):
    store = db.session.get(Store, store_id)
    if not store:
        return redirect(url_for('stores.stores_list'))
    items = db.session.scalars(
        select(ShoppingListItem)
        .where(ShoppingListItem.store_id == store_id)
        .order_by(ShoppingListItem.checked, ShoppingListItem.name)
    ).all()
    section_map = {}
    unsectioned = []
    for item in items:
        if item.section_id and item.section:
            if item.section_id not in section_map:
                section_map[item.section_id] = (item.section, [])
            section_map[item.section_id][1].append(item)
        else:
            unsectioned.append(item)
    grouped = sorted(section_map.values(), key=lambda x: x[0].name)
    return render_template('stores/shop.html', store=store, grouped=grouped,
                           unsectioned=unsectioned)


@stores_bp.route('/<int:store_id>/list/<int:item_id>/toggle', methods=['POST'])
@login_required
def toggle_list_item(store_id, item_id):
    item = db.session.get(ShoppingListItem, item_id)
    if not item or item.store_id != store_id:
        return jsonify({'ok': False, 'error': 'Not found'}), 404
    item.checked = not item.checked
    db.session.commit()
    return jsonify({'ok': True, 'checked': item.checked})


@stores_bp.route('/<int:store_id>/list/done', methods=['POST'])
@login_required
def done_shopping(store_id):
    db.session.execute(
        delete(ShoppingListItem).where(ShoppingListItem.store_id == store_id)
    )
    db.session.commit()
    return redirect(url_for('stores.store_index', store_id=store_id))


@stores_bp.route('/<int:store_id>/manage')
@login_required
def store_manage(store_id):
    store = db.session.get(Store, store_id)
    if not store:
        return redirect(url_for('stores.stores_list'))
    sections = db.session.scalars(
        select(StoreSection)
        .where(StoreSection.store_id == store_id)
        .order_by(StoreSection.name)
    ).all()
    return render_template('stores/manage.html', store=store, sections=sections)


@stores_bp.route('/<int:store_id>/sections', methods=['POST'])
@login_required
def add_section(store_id):
    store = db.session.get(Store, store_id)
    if not store:
        return jsonify({'ok': False, 'error': 'Not found'}), 404
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'ok': False, 'error': 'Name is required'}), 400
    if db.session.scalar(
        select(StoreSection).where(StoreSection.store_id == store_id, StoreSection.name == name)
    ):
        return jsonify({'ok': False, 'error': 'Section already exists'}), 409
    section = StoreSection(name=name, store_id=store_id)
    db.session.add(section)
    db.session.commit()
    return jsonify({'ok': True, 'id': section.id, 'name': section.name})


@stores_bp.route('/<int:store_id>/sections/<int:section_id>/edit', methods=['POST'])
@login_required
def edit_section(store_id, section_id):
    section = db.session.get(StoreSection, section_id)
    if not section or section.store_id != store_id:
        return jsonify({'ok': False, 'error': 'Not found'}), 404
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'ok': False, 'error': 'Name is required'}), 400
    if name != section.name and db.session.scalar(
        select(StoreSection).where(StoreSection.store_id == store_id, StoreSection.name == name)
    ):
        return jsonify({'ok': False, 'error': 'Section already exists'}), 409
    section.name = name
    db.session.commit()
    return jsonify({'ok': True, 'id': section.id, 'name': section.name})


@stores_bp.route('/<int:store_id>/sections/<int:section_id>/delete', methods=['POST'])
@login_required
def delete_section(store_id, section_id):
    section = db.session.get(StoreSection, section_id)
    if section and section.store_id == store_id:
        db.session.execute(
            update(StapleItem).where(StapleItem.section_id == section_id).values(section_id=None)
        )
        db.session.execute(
            update(ShoppingListItem)
            .where(ShoppingListItem.section_id == section_id)
            .values(section_id=None)
        )
        db.session.delete(section)
        db.session.commit()
    return redirect(url_for('stores.store_manage', store_id=store_id))
