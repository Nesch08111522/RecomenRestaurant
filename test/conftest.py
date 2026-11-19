import os
from urllib.parse import urlsplit

import pytest

SERVICE_COLLECTIONS = (
    "users", "restaurants", "dishes", "reviews", "notifications", "categories",
    "restaurant_tables", "table_sessions", "service_requests", "flow_queue",
    "flow_settings", "loyalty_bonuses", "market_orders", "market_offers",
    "market_kitchens", "market_movements", "market_photos", "site_settings",
)


@pytest.fixture
def test_database(monkeypatch):
    from config import Config

    dsn = os.environ.get("SMARTRESTO_TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("Requiere una base PostgreSQL desechable con el esquema instalado")
    monkeypatch.setattr(Config, "DATABASE_URL", dsn)


@pytest.fixture
def service_db(test_database):
    """Base desechable verificada por nombre antes de borrar datos de prueba."""
    from database.connection import connection

    name = urlsplit(os.environ["SMARTRESTO_TEST_DATABASE_URL"]).path.lstrip("/")
    if name not in {"smartresto_it", "smartresto_test"}:
        pytest.skip("SMARTRESTO_TEST_DATABASE_URL no apunta a una base desechable reconocida")

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
