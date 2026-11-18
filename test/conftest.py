import os

import pytest


@pytest.fixture
def test_database(monkeypatch):
    from config import Config

    dsn = os.environ.get("SMARTRESTO_TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("Requiere una base PostgreSQL desechable con el esquema instalado")
    monkeypatch.setattr(Config, "DATABASE_URL", dsn)


@pytest.fixture(autouse=True)
def isolate_external_provider_keys(monkeypatch):
    # Individual provider tests can set their own test credentials after this fixture.
    for name in ("OPENROUTER_API_KEY", "AI_API_KEY", "GEMINI_API_KEY"):
        monkeypatch.setenv(name, "")
