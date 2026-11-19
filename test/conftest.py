import os
from pathlib import Path
from uuid import uuid4

import pytest

# Unit tests never inherit the operational database during application imports.
os.environ['DATABASE_URL'] = ''
os.environ.pop('SMARTRESTO_TEST_SCHEMA', None)

SERVICE_COLLECTIONS = (
    "users", "restaurants", "dishes", "reviews", "notifications", "categories",
    "restaurant_tables", "table_sessions", "service_requests", "flow_queue",
    "flow_settings", "loyalty_bonuses", "market_orders", "market_offers",
    "market_kitchens", "market_movements", "market_photos", "site_settings",
)


@pytest.fixture(scope='session')
def isolated_database():
    if os.environ.get('SMARTRESTO_RUN_ISOLATED_DB') != '1':
        pytest.skip('Requiere autorización explícita de PostgreSQL aislado')
    from dotenv import dotenv_values
    from config import Config
    from database.connection import connection
    from database.pool import close_pool

    root = Path(__file__).resolve().parents[1]
    dsn = dotenv_values(root / '.env').get('DATABASE_URL')
    if not dsn:
        pytest.fail('No se encontró conexión en .env; no se modificaron datos')
    schema = 'smartresto_qa_' + uuid4().hex
    previous = Config.DATABASE_URL
    Config.DATABASE_URL = dsn
    os.environ['SMARTRESTO_TEST_SCHEMA'] = schema
    try:
        # Fresh DDL, never LIKE INCLUDING DEFAULTS (which can share sequences).
        with connection() as conn:
            conn.execute('CREATE SCHEMA ' + schema)
            for filename in ('app_records.sql', 'platform_foundation.sql', 'ai_decisions.sql'):
                source = (root / 'database' / filename).read_text(encoding='utf-8')
                source = source.replace('BEGIN;', '').replace('COMMIT;', '')
                conn.execute(source)
            conn.commit()
        with connection() as conn:
            assert conn.execute('SELECT current_schema() AS s').fetchone()['s'] == schema
            for table in ('app_records', 'sr_businesses', 'sr_branches', 'sr_memberships', 'sr_audit_events', 'ai_decisions'):
                row = conn.execute("SELECT pg_get_serial_sequence(%s, 'id') AS s", (schema + '.' + table,)).fetchone()
                assert row['s'].startswith(schema + '.'), 'Secuencia fuera del aislamiento'
            references = conn.execute("SELECT count(*) AS n FROM pg_constraint c JOIN pg_class t ON t.oid=c.conrelid JOIN pg_namespace n ON n.oid=t.relnamespace JOIN pg_class r ON r.oid=c.confrelid JOIN pg_namespace rn ON rn.oid=r.relnamespace WHERE c.contype='f' AND n.nspname=%s AND rn.nspname<>%s", (schema, schema)).fetchone()
            assert references['n'] == 0, 'Relación fuera del aislamiento'
            assert conn.execute('SELECT count(*) AS n FROM ' + schema + '.app_records').fetchone()['n'] == 0
        print('\nAislamiento PostgreSQL verificado: ' + schema + '; identidad independiente; sin datos heredados')
        yield dsn
    finally:
        close_pool()
        Config.DATABASE_URL = previous
        os.environ.pop('SMARTRESTO_TEST_SCHEMA', None)


@pytest.fixture
def test_database(monkeypatch, isolated_database):
    from config import Config
    monkeypatch.setattr(Config, 'DATABASE_URL', isolated_database)
    import psycopg
    original = psycopg.connect
    def guarded_connect(*args, **kwargs):
        from database.metrics import TimedCursor
        from database.connection import test_schema, DatabaseConfigurationError
        expected = '-c search_path=' + test_schema() + ',pg_catalog'
        if kwargs.get('cursor_factory') is not TimedCursor or kwargs.get('options') != expected or kwargs.get('autocommit'):
            raise DatabaseConfigurationError('Conexión psycopg directa bloqueada fuera del aislamiento.')
        return original(*args, **kwargs)
    monkeypatch.setattr(psycopg, 'connect', guarded_connect)


@pytest.fixture
def service_db(test_database):
    """Base desechable verificada por nombre antes de borrar datos de prueba."""
    from database.connection import connection

    from database.connection import test_schema
    assert test_schema(), 'Limpieza bloqueada sin esquema aislado'

    def clean():
        with connection() as conn:
            conn.execute("DELETE FROM public.app_records WHERE collection = ANY(%s)",
                         (list(SERVICE_COLLECTIONS),))

    clean()
    yield
    clean()


@pytest.fixture(autouse=True)
def isolate_external_provider_keys(monkeypatch):
    # Individual provider tests can set their own test credentials after this fixture.
    for name in ("OPENROUTER_API_KEY", "AI_API_KEY", "GEMINI_API_KEY"):
        monkeypatch.setenv(name, "")
