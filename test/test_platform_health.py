from app import create_app
from database import connection as db


def test_health_reports_database_outage_without_internal_details(monkeypatch):
    def unavailable():
        raise RuntimeError('private-database-password')
    monkeypatch.setattr(db, 'check_connection', unavailable)
    client = create_app({'TESTING': True, 'SECRET_KEY': 'x' * 32}).test_client()
    response = client.get('/api/platform/health')
    assert response.status_code == 503
    assert response.json['status'] == 'degraded'
    assert response.json['integrations']['database'] is False
    assert b'private-database-password' not in response.data


def test_health_reports_ready_after_successful_database_check(monkeypatch):
    monkeypatch.setattr(db, 'check_connection', lambda: True)
    client = create_app({'TESTING': True, 'SECRET_KEY': 'x' * 32}).test_client()
    response = client.get('/api/platform/health')
    assert response.status_code == 200
    assert response.json['status'] == 'ready'
    assert response.json['integrations']['database'] is True
