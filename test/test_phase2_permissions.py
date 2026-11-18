from core.permissions import can, permissions_for_role
from core.profile import normalize_profile_patch


def test_permissions_are_explicit_and_role_scoped():
    assert can("user", "profile.read") is True
    assert can("user", "business.manage") is False
    assert can("business_owner", "business.manage") is True
    assert can("business_owner", "staff.invite") is True
    assert can("admin", "platform.users.manage") is True
    assert can("admin", "business.manage") is True
    assert can("unknown", "platform.users.manage") is False


def test_permissions_for_role_returns_a_defensive_sorted_list():
    permissions = permissions_for_role("business_owner")

    assert permissions == sorted(permissions)
    assert "profile.read" in permissions
    assert "staff.manage" in permissions
    permissions.append("platform.root")
    assert "platform.root" not in permissions_for_role("business_owner")


def test_profile_patch_allowlists_private_preferences_and_consent():
    patch = normalize_profile_patch(
        {
            "name": "  Ana   Torres ",
            "email": " ANA@EXAMPLE.COM ",
            "preferences": ["criolla", "criolla", ""],
            "restrictions": ["sin gluten"],
            "daily_budget": "45.50",
            "weekly_budget": 280,
            "notification_preferences": {"transactional": True, "marketing": False},
            "location_consent": True,
            "password": "no debe entrar",
        }
    )

    assert patch["name"] == "Ana Torres"
    assert patch["email"] == "ana@example.com"
    assert patch["preferences"] == ["criolla"]
    assert patch["daily_budget"] == 45.5
    assert patch["weekly_budget"] == 280.0
    assert patch["notification_preferences"] == {"transactional": True, "marketing": False}
    assert patch["location_consent"] is True
    assert "password" not in patch
