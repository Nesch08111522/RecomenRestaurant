from contextlib import contextmanager
from datetime import date, timedelta
from unittest.mock import patch

from flask import Flask
from analytics.intelligence import report
from views import intelligence


def test_forecast_linear_day_calls():
    end = date(2026, 10, 31)
    orders = [{'state': 'Entregado', 'paid': True, 'created': (end-timedelta(days=i%70)).isoformat(), 'uid': i%3, 'total': 100, 'lines': []} for i in range(1000)]
    with patch('analytics.intelligence.day', wraps=intelligence.report.__globals__['day']) as calls:
        result = report(orders, [], end-timedelta(days=29), end)
    assert len(result['forecast']) == 7
    assert calls.call_count < 12 * len(orders)


def test_invalid_history_date_does_not_crash_forecast():
    result = report([{'state': 'Entregado', 'paid': True, 'created': '2026-02-99', 'uid': 1}], [], date(2026, 3, 1), date(2026, 3, 30))
    assert result['forecast'] == []


def test_period_query_scopes_dates_and_empty_scope(monkeypatch):
    queries = []
    class Connection:
        def execute(self, sql, args):
            queries.append((sql, args))
            return [{'payload': {'rid': 2}}]
    @contextmanager
    def transaction():
        yield Connection()
    monkeypatch.setattr(intelligence, 'document_transaction', transaction)
    assert intelligence.period_records('flow_queue', [], date(2026, 1, 1), date(2026, 1, 7), ('created_at',)) == []
    assert not queries
    assert intelligence.period_records('flow_queue', [2], date(2026, 1, 1), date(2026, 1, 7), ('created_at',)) == [{'rid': 2}]
    sql, args = queries[0]
    assert "payload->>'rid'=ANY(%s)" in sql
    assert 'BETWEEN %s AND %s' in sql
    assert args == ('flow_queue', ['2'], '2026-01-01', '2026-01-07')


def test_snapshot_query_count_independent_of_businesses(monkeypatch):
    counts = []
    for size in (1, 100):
        queries = []
        class Cursor(list):
            def fetchone(self):
                return {'n': 0, 'views': 0, 'clicks': 0, 'orders': 0}
        class Connection:
            def execute(self, sql, args):
                queries.append((sql, args))
                return Cursor()
        @contextmanager
        def transaction():
            yield Connection()
        monkeypatch.setattr(intelligence, 'document_transaction', transaction)
        monkeypatch.setattr(intelligence, 'fresh_session_user', lambda: {'id': 1, 'role': 'admin'})
        monkeypatch.setattr(intelligence.RestaurantModel, 'all', lambda: [{'id': i, 'name': str(i)} for i in range(size)])
        monkeypatch.setattr(intelligence, 'scoped_records', lambda *args: [])
        app = Flask(__name__)
        with app.test_request_context('/inteligencia?start=2026-01-01&end=2026-01-07'):
            data, _, _, _ = intelligence.snapshot()
        assert data['businesses'] == size
        counts.append(len(queries))
    assert counts == [10, 10]


def test_private_error_responses_and_scope_rejection(monkeypatch):
    app = Flask(__name__)
    app.register_blueprint(intelligence.bp)
    monkeypatch.setattr(intelligence, 'fresh_session_user', lambda: {'id': 1, 'role': 'business_owner'})
    monkeypatch.setattr(intelligence.RestaurantModel, 'get_by_owner', lambda uid: [{'id': 2}])
    with app.test_client() as client:
        response = client.get('/api/inteligencia?rid=3')
    assert response.status_code == 404
    assert response.headers['Cache-Control'] == 'private, no-store'
