from sqlalchemy import select
from app.extensions import db
from app.models import Todo


def test_todo_model_has_title_and_defaults(app):
    with app.app_context():
        todo = Todo(title='Clean the garage')
        db.session.add(todo)
        db.session.commit()
        saved = db.session.get(Todo, todo.id)
        assert saved.title == 'Clean the garage'
        assert saved.description is None
        assert saved.done is False
        assert saved.completed_at is None


def test_todos_index_requires_login(client):
    resp = client.get('/todos/')
    assert resp.status_code == 302
    assert '/auth/login' in resp.headers['Location']


def test_todos_index_returns_200(logged_in_client):
    resp = logged_in_client.get('/todos/')
    assert resp.status_code == 200


def test_todos_index_lists_existing_todos(logged_in_client, app):
    with app.app_context():
        db.session.add(Todo(title='Clean the garage'))
        db.session.commit()
    resp = logged_in_client.get('/todos/')
    assert b'Clean the garage' in resp.data


def test_create_todo(logged_in_client, app):
    resp = logged_in_client.post('/todos/', json={'title': 'Clean the garage'})
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['ok'] is True
    assert data['title'] == 'Clean the garage'
    with app.app_context():
        assert db.session.scalar(select(Todo).where(Todo.title == 'Clean the garage')) is not None


def test_create_todo_with_description(logged_in_client):
    resp = logged_in_client.post(
        '/todos/', json={'title': 'Clean the garage', 'description': 'Donate old tools'}
    )
    assert resp.status_code == 200
    assert resp.get_json()['description'] == 'Donate old tools'


def test_create_todo_blank_title_returns_400(logged_in_client):
    resp = logged_in_client.post('/todos/', json={'title': '  '})
    assert resp.status_code == 400
    assert resp.get_json()['ok'] is False


def test_toggle_todo_marks_done_and_sets_completed_at(logged_in_client, app):
    with app.app_context():
        todo = Todo(title='Clean the garage')
        db.session.add(todo)
        db.session.commit()
        todo_id = todo.id
    resp = logged_in_client.post(f'/todos/{todo_id}/toggle')
    assert resp.status_code == 200
    assert resp.get_json()['done'] is True
    with app.app_context():
        saved = db.session.get(Todo, todo_id)
        assert saved.done is True
        assert saved.completed_at is not None


def test_toggle_todo_off_clears_completed_at(logged_in_client, app):
    with app.app_context():
        todo = Todo(title='Clean the garage', done=True)
        db.session.add(todo)
        db.session.commit()
        todo_id = todo.id
    resp = logged_in_client.post(f'/todos/{todo_id}/toggle')
    assert resp.get_json()['done'] is False
    with app.app_context():
        assert db.session.get(Todo, todo_id).completed_at is None


def test_toggle_todo_not_found_returns_404(logged_in_client):
    resp = logged_in_client.post('/todos/9999/toggle')
    assert resp.status_code == 404


def test_edit_todo_updates_title_and_description(logged_in_client, app):
    with app.app_context():
        todo = Todo(title='Clean the garage')
        db.session.add(todo)
        db.session.commit()
        todo_id = todo.id
    resp = logged_in_client.post(
        f'/todos/{todo_id}/edit',
        json={'title': 'Clean the laundry room', 'description': 'Sort the lost socks'},
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data['ok'] is True
    assert data['title'] == 'Clean the laundry room'
    assert data['description'] == 'Sort the lost socks'


def test_edit_todo_blank_title_returns_400(logged_in_client, app):
    with app.app_context():
        todo = Todo(title='Clean the garage')
        db.session.add(todo)
        db.session.commit()
        todo_id = todo.id
    resp = logged_in_client.post(f'/todos/{todo_id}/edit', json={'title': ''})
    assert resp.status_code == 400


def test_edit_todo_not_found_returns_404(logged_in_client):
    resp = logged_in_client.post('/todos/9999/edit', json={'title': 'X'})
    assert resp.status_code == 404


def test_delete_todo(logged_in_client, app):
    with app.app_context():
        todo = Todo(title='Clean the garage')
        db.session.add(todo)
        db.session.commit()
        todo_id = todo.id
    resp = logged_in_client.post(f'/todos/{todo_id}/delete')
    assert resp.status_code == 302
    with app.app_context():
        assert db.session.get(Todo, todo_id) is None


def test_delete_todo_requires_login(client, app):
    with app.app_context():
        todo = Todo(title='Clean the garage')
        db.session.add(todo)
        db.session.commit()
        todo_id = todo.id
    resp = client.post(f'/todos/{todo_id}/delete')
    assert resp.status_code == 302
    assert '/auth/login' in resp.headers['Location']


def test_house_todos_link_in_navbar(logged_in_client):
    resp = logged_in_client.get('/todos/')
    assert b'House Todos' in resp.data


def test_error_toast_present_on_todos_page(logged_in_client):
    resp = logged_in_client.get('/todos/')
    assert resp.data.count(b'id="error-toast"') == 1
