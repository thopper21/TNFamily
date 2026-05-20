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
    return 'OK', 200


@grocery_bp.route('/sections', methods=['POST'])
@login_required
def add_section():
    return jsonify({'ok': True}), 200


@grocery_bp.route('/sections/<int:section_id>/delete', methods=['POST'])
@login_required
def delete_section(section_id):
    return redirect(url_for('grocery.sections'))
