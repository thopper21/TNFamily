# app/grocery/routes.py
from flask import render_template, request, jsonify, redirect, url_for
from flask_login import login_required
from app.grocery import grocery_bp
from app.extensions import db
from app.models import StoreSection, StapleItem, ShoppingListItem


@grocery_bp.route('/')
@login_required
def index():
    return 'OK', 200


@grocery_bp.route('/staples', methods=['POST'])
@login_required
def add_staple():
    return jsonify({'ok': True}), 200


@grocery_bp.route('/staples/<int:staple_id>/toggle', methods=['POST'])
@login_required
def toggle_staple(staple_id):
    return jsonify({'ok': True}), 200


@grocery_bp.route('/staples/<int:staple_id>/delete', methods=['POST'])
@login_required
def delete_staple(staple_id):
    return redirect(url_for('grocery.index'))


@grocery_bp.route('/list/add', methods=['POST'])
@login_required
def add_to_list():
    return jsonify({'ok': True}), 200


@grocery_bp.route('/list/<int:item_id>/toggle', methods=['POST'])
@login_required
def toggle_list_item(item_id):
    return jsonify({'ok': True}), 200


@grocery_bp.route('/list/done', methods=['POST'])
@login_required
def done_shopping():
    return redirect(url_for('grocery.index'))


@grocery_bp.route('/shop')
@login_required
def shop():
    return 'OK', 200


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
