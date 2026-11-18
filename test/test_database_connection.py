"""Regresiones locales de conexión: nunca usan datos ni secretos reales."""
import pytest
from config import Config
from database import connection as db


@pytest.mark.parametrize('uri', [
    'postgresql://postgres:secret@HOST_POOLER:6543/postgres',
    'postgresql://postgres:secret@/postgres',
    'postgresql://postgres:secret@db.example:wrong/postgres',
])
def test_invalid_host_or_port_is_rejected_before_connect(uri, monkeypatch):
    monkeypatch.setattr(Config, 'DATABASE_URL', uri)
    with pytest.raises(db.DatabaseConfigurationError):
        db.require_postgres()


def test_dns_failure_has_actionable_diagnostic_without_secret(monkeypatch):
    uri = 'postgresql://postgres:test-secret@db.example.supabase.co:5432/postgres'
    monkeypatch.setattr(Config, 'DATABASE_URL', uri)
    def unavailable(*args, **kwargs):
        raise db.psycopg.OperationalError('[Errno 11001] getaddrinfo failed: test-secret')
    monkeypatch.setattr(db.psycopg, 'connect', unavailable)
    with pytest.raises(RuntimeError) as error:
        with db.connection():
            pass
    assert 'IPv6' in str(error.value)
    assert 'Session pooler' in str(error.value)
    assert 'test-secret' not in str(error.value)
    assert 'postgresql://' not in str(error.value)


def test_pooler_parameter_is_removed_but_tls_and_password_are_preserved():
    uri = 'postgresql://postgres.demo:p%3F@aws-1-example.pooler.supabase.com:5432/postgres?pgbouncer=true&sslmode=verify-full'
    clean = db._libpq_dsn(uri)
    assert 'pgbouncer' not in clean
    assert 'sslmode=verify-full' in clean
    assert ':p%3F@' in clean
