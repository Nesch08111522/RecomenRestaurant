import pytest

from core.platform_context import build_platform_context
from core.platform_manifest import platform_manifest


def test_platform_manifest_exposes_shared_modules_and_roles():
    manifest = platform_manifest()

    assert manifest["product"] == "SmartResto"
    assert "marketplace" in manifest["modules"]
    assert "operations" in manifest["modules"]
    assert "smart_flow" in manifest["modules"]
    assert manifest["roles"]["business_owner"]["scope"] == "business"
    assert manifest["security"]["audit_events"] is True


def test_platform_context_scopes_business_session_without_leaking_identity():
    context = build_platform_context(
        {
            "user_id": 42,
            "user": {
                "id": 42,
                "role": "business_owner",
                "business_id": 7,
                "branch_id": 3,
                "email": "private@example.com",
            },
        }
    )

    assert context.user_id == 42
    assert context.role == "business_owner"
    assert context.business_id == 7
    assert context.branch_id == 3
    assert context.as_public_dict() == {
        "authenticated": True,
        "role": "business_owner",
        "scope": "business",
        "business_id": 7,
        "branch_id": 3,
    }
    assert "email" not in context.as_public_dict()


def test_platform_context_defaults_to_public_scope():
    context = build_platform_context({})

    assert context.user_id is None
    assert context.role == "guest"
    assert context.scope == "public"
    assert context.as_public_dict()["authenticated"] is False
