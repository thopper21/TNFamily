# app/grocery/routes.py
from flask import render_template, request, jsonify, redirect, url_for
from flask_login import login_required
from sqlalchemy.orm import joinedload
from app.grocery import grocery_bp
from app.extensions import db
from app.models import StoreSection, StapleItem, ShoppingListItem


@grocery_bp.route('/')
@login_required
def index():
    staples = (
        StapleItem.query
        .options(joinedload(StapleItem.shopping_list_item))
        .order_by(StapleItem.name)
        .all()
    )
    staples.sort(key=lambda s: s.shopping_list_item is not None)
    sections = StoreSection.query.order_by(StoreSection.name).all()
    shopping_count = ShoppingListItem.query.count()
    ad_hoc_items = (
        ShoppingListItem.query
        .filter_by(staple_item_id=None)
        .order_by(ShoppingListItem.created_at.desc())
        .all()
    )
    return render_template(
        'grocery/home.html',
        staples=staples,
        sections=sections,
        shopping_count=shopping_count,
        ad_hoc_items=ad_hoc_items,
    )


@grocery_bp.route('/staples', methods=['POST'])
@login_required
def add_staple():
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'ok': False, 'error': 'Name is required'}), 400
    section_id = data.get('section_id') or None
    if section_id and not db.session.get(StoreSection, section_id):
        return jsonify({'ok': False, 'error': 'Section not found'}), 400
    staple = StapleItem(name=name, section_id=section_id)
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


@grocery_bp.route('/staples/<int:staple_id>/toggle', methods=['POST'])
@login_required
def toggle_staple(staple_id):
    staple = db.session.get(StapleItem, staple_id)
    if not staple:
        return jsonify({'ok': False, 'error': 'Not found'}), 404
    if staple.shopping_list_item:
        db.session.delete(staple.shopping_list_item)
    else:
        db.session.add(ShoppingListItem(
            name=staple.name, section_id=staple.section_id, staple_item_id=staple.id
        ))
    db.session.commit()
    return jsonify({
        'ok': True,
        'on_shopping_list': staple.shopping_list_item is not None,
        'shopping_count': ShoppingListItem.query.count(),
    })


@grocery_bp.route('/staples/<int:staple_id>/delete', methods=['POST'])
@login_required
def delete_staple(staple_id):
    staple = db.session.get(StapleItem, staple_id)
    if staple:
        db.session.delete(staple)
        db.session.commit()
    return redirect(url_for('grocery.index'))


@grocery_bp.route('/list/add', methods=['POST'])
@login_required
def add_to_list():
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'ok': False, 'error': 'Name is required'}), 400
    section_id = data.get('section_id') or None
    if section_id and not db.session.get(StoreSection, section_id):
        return jsonify({'ok': False, 'error': 'Section not found'}), 400
    item = ShoppingListItem(name=name, section_id=section_id)
    db.session.add(item)
    db.session.commit()
    return jsonify({'ok': True, 'id': item.id, 'shopping_count': ShoppingListItem.query.count()})


@grocery_bp.route('/shop')
@login_required
def shop():
    items = ShoppingListItem.query.order_by(ShoppingListItem.checked, ShoppingListItem.name).all()
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
    return render_template('grocery/shop.html', grouped=grouped, unsectioned=unsectioned)


@grocery_bp.route('/list/<int:item_id>/delete', methods=['POST'])
@login_required
def delete_list_item(item_id):
    item = db.session.get(ShoppingListItem, item_id)
    if not item:
        return jsonify({'ok': False, 'error': 'Not found'}), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify({'ok': True, 'shopping_count': ShoppingListItem.query.count()})


@grocery_bp.route('/list/<int:item_id>/toggle', methods=['POST'])
@login_required
def toggle_list_item(item_id):
    item = db.session.get(ShoppingListItem, item_id)
    if not item:
        return jsonify({'ok': False, 'error': 'Not found'}), 404
    item.checked = not item.checked
    db.session.commit()
    return jsonify({'ok': True, 'checked': item.checked})


@grocery_bp.route('/list/done', methods=['POST'])
@login_required
def done_shopping():
    ShoppingListItem.query.delete(synchronize_session=False)
    db.session.commit()
    return redirect(url_for('grocery.index'))


@grocery_bp.route('/sections')
@login_required
def sections():
    all_sections = StoreSection.query.order_by(StoreSection.name).all()
    return render_template('grocery/sections.html', sections=all_sections)


@grocery_bp.route('/sections', methods=['POST'])
@login_required
def add_section():
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'ok': False, 'error': 'Name is required'}), 400
    if StoreSection.query.filter_by(name=name).first():
        return jsonify({'ok': False, 'error': 'Section already exists'}), 409
    section = StoreSection(name=name)
    db.session.add(section)
    db.session.commit()
    return jsonify({'ok': True, 'id': section.id, 'name': section.name})


@grocery_bp.route('/sections/<int:section_id>/edit', methods=['POST'])
@login_required
def edit_section(section_id):
    section = db.session.get(StoreSection, section_id)
    if not section:
        return jsonify({'ok': False, 'error': 'Not found'}), 404
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'ok': False, 'error': 'Name is required'}), 400
    if name != section.name and StoreSection.query.filter_by(name=name).first():
        return jsonify({'ok': False, 'error': 'Section already exists'}), 409
    section.name = name
    db.session.commit()
    return jsonify({'ok': True, 'id': section.id, 'name': section.name})


@grocery_bp.route('/sections/<int:section_id>/delete', methods=['POST'])
@login_required
def delete_section(section_id):
    section = db.session.get(StoreSection, section_id)
    if section:
        StapleItem.query.filter_by(section_id=section_id).update({'section_id': None})
        ShoppingListItem.query.filter_by(section_id=section_id).update({'section_id': None})
        db.session.delete(section)
        db.session.commit()
    return redirect(url_for('grocery.sections'))
