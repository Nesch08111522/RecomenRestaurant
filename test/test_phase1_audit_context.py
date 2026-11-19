from flask import Flask, g, request

from app import create_app
from core.platform_context import PlatformContext
from utils.audit import AuditEventModel, record_event


def test_request_context_is_available_to_all_flask_routes():
    app = create_app({"TESTING": True, "SECRET_KEY": "x" * 32})

    with app.test_request_context("/"):
        app.preprocess_request()
        assert isinstance(g.platform_context, PlatformContext)
        assert g.platform_context.scope == "public"


def test_audit_uses_server_request_id_and_carries_business_context(monkeypatch):
    monkeypatch.setattr(AuditEventModel, "create", classmethod(lambda cls, event: event))
    app = Flask("audit-context-test")
    app.secret_key = "x" * 32

    with app.test_request_context("/", headers={"X-Request-ID": "client-controlled-id"}):
        request.request_id = "server-generated-id"
        g.platform_context = PlatformContext(user_id=12, role="manager", business_id=88, branch_id=4)
        event = record_event("ADMIN_USER_UPDATE", resource_type="user", resource_id=42)

    assert event["request_id"] == "server-generated-id"
    assert event["request_id"] != "client-controlled-id"
    assert event["business_id"] == 88
