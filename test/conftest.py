import os

import pytest


@pytest.fixture
def test_database(monkeypatch):
    from config import Config

    dsn = os.environ.get("SMARTRESTO_TEST_DATABASE_URL")
    if not dsn:
        pytest.skip("Requiere una base PostgreSQL desechable con el esquema instalado")
    monkeypatch.setattr(Config, "DATABASE_URL", dsn)
