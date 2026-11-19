from contextlib import contextmanager
from unittest.mock import Mock

import pytest
from flask import Flask
from models.notification import NotificationModel as N
from database.repository import PostgresDocumentRepository as Repo
from views.communication import bp


@pytest.fixture
def transaction(monkeypatch):
    conn = Mock()
    @contextmanager
    def tx():
        yield conn
    monkeypatch.setattr('models.notification.document_transaction', tx)
    monkeypatch.setattr('views.communication.document_transaction', tx)
    return conn


@pytest.mark.parametrize('action', ['read', 'archive', 'restore', 'delete'])
def test_scope_and_deleted(transaction, monkeypatch, action):
    update = Mock(return_value=True)
    monkeypatch.setattr(N, 'update', update)
    row = {'id': 7, 'user_id': 1}
    monkeypatch.setattr(Repo, 'get_by_id', Mock(return_value=row))
    assert not N.change_state(2, 7, action)
    update.assert_not_called()
    assert N.change_state(1, 7, action)
    row['deleted'] = True
    assert not N.change_state(1, 7, action)


def test_history_and_count_sql(transaction):
    transaction.execute.return_value = []
    N.get_by_user(42, limit=999, archived=True, before=77)
    sql, args = transaction.execute.call_args.args
    assert args == ('42', True, 77, 77, 100)
    assert 'deleted' in sql and 'archived' in sql and 'id <' in sql
    transaction.execute.return_value = Mock()
    transaction.execute.return_value.fetchone.return_value = {'n': 3}
    assert N.get_unread_count(42) == 3
    sql, args = transaction.execute.call_args.args
    assert args == ('42',)
    assert all(field in sql for field in ['read', 'deleted', 'archived'])


def test_event_key_and_legacy_classification(transaction, monkeypatch):
    create = Mock(side_effect=lambda row: dict(row, id=8))
    monkeypatch.setattr(N, 'create', create)
    transaction.execute.return_value.fetchone.return_value = None
    row = N.create_notification(1, 'Pedido confirmado', 'OK', event_key='order:1')
    assert row['type'] == 'order'
    transaction.execute.return_value.fetchone.return_value = {'payload': row}
    assert N.create_notification(1, 'Pedido confirmado', 'OK', event_key='order:1') == row
    assert create.call_count == 1
    assert transaction.execute.call_args.args[1] == ('1', 'order:1')
    assert N.create_notification(2, 'Suscripcion actualizada', 'OK')['type'] == 'subscription'
    assert N.create_notification(3, 'Nuevos prospectos', 'OK')['type'] == 'commercial'


def test_feed_auth_scope_and_actions(transaction, monkeypatch):
    app = Flask(__name__)
    app.secret_key = 'isolated'
    from flask_wtf.csrf import CSRFProtect
    CSRFProtect(app)
    app.register_blueprint(bp)
    @app.get('/token')
    def token():
        from flask_wtf.csrf import generate_csrf
        return generate_csrf()
    rows = Mock(return_value=[{'id': 9, 'user_id': 11}])
    monkeypatch.setattr(N, 'get_by_user', rows)
    monkeypatch.setattr(N, 'get_unread_count', Mock(return_value=1))
    change = Mock(return_value=False)
    monkeypatch.setattr(N, 'change_state', change)
    client = app.test_client()
    assert client.get('/bandeja/notificaciones/feed').status_code == 401
    with client.session_transaction() as session:
        session['user'] = {'id': 11, 'role': 'user'}
    response = client.get('/bandeja/notificaciones/feed?user_id=12')
    assert response.status_code == 200
    assert response.headers['Cache-Control'] == 'private, no-store'
    rows.assert_called_once_with(11, limit=100)
    assert client.post('/bandeja/notificaciones/9/delete').status_code == 400
    csrf_token = client.get('/token').get_data(as_text=True)
    assert client.post('/bandeja/notificaciones/9/delete', headers={'X-CSRFToken': csrf_token}).status_code == 404
    change.assert_called_once_with(11, 9, 'delete')
