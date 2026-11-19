from app import create_app
from core.platform_context import build_platform_context
from database import connection as db


def test_legacy_user_and_owner_roles_resolve_to_their_scopes():
    user_context = build_platform_context({"user_id": 12, "user": {"id": 12, "role": "user"}})
    owner_context = build_platform_context({"user_id": 13, "user": {"id": 13, "role": "owner"}})

    assert user_context.scope == "user"
    assert owner_context.scope == "business"


def test_health_does_not_claim_audit_available_when_database_is_down(monkeypatch):
    monkeypatch.setattr(db, "check_connection", lambda: False)
    client = create_app({"TESTING": True, "SECRET_KEY": "x" * 32}).test_client()

    response = client.get("/api/platform/health")

    assert response.status_code == 503
    assert response.json["integrations"]["audit"] is False
    assert response.json["checks"]["audit"] == "unavailable"


def test_health_reports_audit_available_only_with_database_ready(monkeypatch):
    monkeypatch.setattr(db, "check_connection", lambda: True)
    client = create_app({"TESTING": True, "SECRET_KEY": "x" * 32}).test_client()

    response = client.get("/api/platform/health")

    assert response.status_code == 200
    assert response.json["integrations"]["audit"] is True
    assert response.json["checks"]["audit"] == "available"
