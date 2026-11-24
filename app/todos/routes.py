# app/todos/routes.py
from datetime import datetime, timezone

from flask import jsonify, redirect, render_template, request, url_for
from flask_login import login_required
from sqlalchemy import select

from app.extensions import db
from app.models import Todo
from app.todos import todos_bp


@todos_bp.route('/')
@login_required
def index():
    todos = db.session.scalars(
        select(Todo).order_by(Todo.done, Todo.created_at.desc())
    ).all()
    return render_template('todos/index.html', todos=todos)


@todos_bp.route('/', methods=['POST'])
@login_required
def create_todo():
    data = request.get_json() or {}
    title = (data.get('title') or '').strip()
    if not title:
        return jsonify({'ok': False, 'error': 'Title is required'}), 400
    description = (data.get('description') or '').strip() or None
    todo = Todo(title=title, description=description)
    db.session.add(todo)
    db.session.commit()
    return jsonify({
        'ok': True,
        'id': todo.id,
        'title': todo.title,
        'description': todo.description,
    })


@todos_bp.route('/<int:todo_id>/toggle', methods=['POST'])
@login_required
def toggle_todo(todo_id):
    todo = db.session.get(Todo, todo_id)
    if not todo:
        return jsonify({'ok': False, 'error': 'Not found'}), 404
    todo.done = not todo.done
    todo.completed_at = datetime.now(timezone.utc) if todo.done else None
    db.session.commit()
    return jsonify({'ok': True, 'done': todo.done})


@todos_bp.route('/<int:todo_id>/edit', methods=['POST'])
@login_required
def edit_todo(todo_id):
    todo = db.session.get(Todo, todo_id)
    if not todo:
        return jsonify({'ok': False, 'error': 'Not found'}), 404
    data = request.get_json() or {}
    title = (data.get('title') or '').strip()
    if not title:
        return jsonify({'ok': False, 'error': 'Title is required'}), 400
    todo.title = title
    todo.description = (data.get('description') or '').strip() or None
    db.session.commit()
    return jsonify({
        'ok': True,
        'title': todo.title,
        'description': todo.description,
    })


@todos_bp.route('/<int:todo_id>/delete', methods=['POST'])
@login_required
def delete_todo(todo_id):
    todo = db.session.get(Todo, todo_id)
    if todo:
        db.session.delete(todo)
        db.session.commit()
    return redirect(url_for('todos.index'))
