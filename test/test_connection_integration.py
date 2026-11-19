"""Writes only use the explicit disposable test database fixture."""
from uuid import uuid4
import pytest
from flask import Flask
from config import Config
from database.connection import connection
from database.repository import PostgresDocumentRepository as Repo, document_transaction
from database.pool import close_pool, pool_stats


def test_isolation_blocks_other_schemas_and_destructive_sql(test_database):
    from database.connection import DatabaseConfigurationError, isolated_query, test_schema
    schema = test_schema()
    assert schema
    assert isolated_query('DELETE FROM public.app_records', None) == 'DELETE FROM ' + schema + '.app_records'
    for query in ('DROP SCHEMA public CASCADE', 'SELECT * FROM public.unknown', 'TRUNCATE app_records'):
        with pytest.raises(DatabaseConfigurationError):
            isolated_query(query, None)


def test_pool_rolls_back_uncommitted_work(test_database):
    collection = 'pool_' + uuid4().hex
    with connection() as conn:
        conn.execute('INSERT INTO public.app_records(collection,payload) VALUES (%s,%s::jsonb)', (collection, '{}'))
    assert Repo.all(collection) == []
    assert pool_stats()['in_use'] == 0


def test_document_atomicity_is_preserved(test_database):
    collection = 'pool_' + uuid4().hex
    with pytest.raises(ValueError):
        with document_transaction():
            Repo.create(collection, {'value':1})
            raise ValueError('abort whole transaction')
    assert Repo.all(collection) == []
    row = Repo.create(collection, {'value':2})
    assert Repo.get_by_id(collection, row['id'])['value'] == 2


def test_request_cache_isolated_copied_and_invalidated(test_database, monkeypatch):
    import database.repository as repository
    from contextlib import contextmanager
    collection = 'cache_' + uuid4().hex
    row = Repo.create(collection, {'value':1})
    calls = []
    original = repository.connection
    @contextmanager
    def counted(*args, **kwargs):
        calls.append(True)
        with original(*args, **kwargs) as conn: yield conn
    monkeypatch.setattr(repository, 'connection', counted)
    app = Flask(__name__)
    with app.test_request_context('/'):
        first = Repo.all(collection)
        first[0]['value'] = 900
        assert Repo.all(collection)[0]['value'] == 1
        assert len(calls) == 1
        Repo.update(collection, row['id'], {'value':2})
        assert Repo.all(collection)[0]['value'] == 2
        assert len(calls) == 3
    with app.test_request_context('/'):
        assert Repo.all(collection)[0]['value'] == 2
        assert len(calls) == 4


def test_statement_timeout_releases_pool_and_recovers(test_database, monkeypatch):
    import psycopg
    monkeypatch.setattr(Config, 'DATABASE_STATEMENT_TIMEOUT_MS', 100)
    with pytest.raises(psycopg.errors.QueryCanceled):
        with document_transaction() as conn:
            conn.execute('SELECT pg_sleep(.3)')
    assert pool_stats()['in_use'] == 0
    with document_transaction() as conn:
        assert conn.execute('SELECT 1 AS ok').fetchone()['ok'] == 1


def test_transaction_settings_do_not_leak_to_next_lease(test_database):
    with connection() as conn:
        baseline = conn.execute('SHOW statement_timeout').fetchone()['statement_timeout']
    with document_transaction() as conn:
        assert int(conn.execute("SELECT current_setting('statement_timeout')::interval = interval '8 seconds' AS ok").fetchone()['ok']) == 1
    with connection() as conn:
        assert conn.execute("SHOW statement_timeout").fetchone()['statement_timeout'] == baseline


def test_for_update_bypasses_request_cache(test_database):
    collection = 'cache_' + uuid4().hex
    row = Repo.create(collection, {'value':1})
    with Flask(__name__).test_request_context('/'):
        Repo.all(collection)
        with document_transaction():
            assert Repo.get_by_id(collection, row['id'], for_update=True)['value'] == 1
            Repo.update(collection, row['id'], {'value':2})
        assert Repo.all(collection)[0]['value'] == 2
