"""Política declarativa de autorización de SmartResto.

La identidad de sesión autentica; este módulo decide qué operación puede
realizar cada rol. El alcance de negocio/sucursal se valida aparte.
"""
from __future__ import annotations

from typing import FrozenSet


_ROLE_ALIASES = {"user": "diner", "owner": "business_owner"}

_PERMISSIONS: dict[str, FrozenSet[str]] = {
    "guest": frozenset({"catalog.read", "business.read", "profile.read.public"}),
    "diner": frozenset({
        "profile.read", "profile.update", "preferences.update", "favorites.manage",
        "orders.read.own", "reviews.create.own", "notifications.manage.own",
        "location.consent.manage", "rewards.read.own", "table.session.own",
    }),
    "business_owner": frozenset({
        "profile.read", "profile.update", "preferences.update", "business.manage",
        "branch.manage", "catalog.manage", "orders.read.business", "staff.invite",
        "staff.manage", "analytics.read.business", "audit.read.business",
        "notifications.manage.business", "rewards.manage.business",
        "tables.manage", "tables.service", "flow.manage", "loyalty.manage.business",
    }),
    "business_admin": frozenset({
        "profile.read", "profile.update", "business.read", "branch.manage",
        "catalog.manage", "orders.read.business", "staff.invite", "staff.manage",
        "analytics.read.business", "notifications.manage.business",
        "tables.manage", "tables.service", "flow.manage",
    }),
    "manager": frozenset({
        "profile.read", "profile.update", "branch.read", "catalog.manage",
        "orders.read.business", "staff.invite", "analytics.read.business",
        "tables.service", "flow.manage",
    }),
    "cashier": frozenset({"profile.read", "profile.update", "branch.read", "orders.read.business", "tables.service"}),
    "waiter": frozenset({"profile.read", "profile.update", "branch.read", "orders.read.business", "tables.service"}),
    "kitchen": frozenset({"profile.read", "profile.update", "branch.read", "orders.read.business"}),
    "admin": frozenset({
        "profile.read", "profile.update", "business.manage", "branch.manage",
        "catalog.manage", "platform.users.manage", "platform.roles.manage",
        "platform.verification.manage", "platform.moderation.manage",
        "platform.audit.read", "platform.settings.manage", "analytics.read.platform",
        "tables.manage", "tables.service", "flow.manage", "loyalty.manage.business",
    }),
}


def _canonical_role(role: str | None) -> str:
    return _ROLE_ALIASES.get(str(role or "guest"), str(role or "guest"))


def permissions_for_role(role: str | None) -> list[str]:
    """Return a sorted defensive list suitable for a JSON response."""
    return sorted(_PERMISSIONS.get(_canonical_role(role), frozenset()))


def can(role: str | None, permission: str) -> bool:
    return permission in _PERMISSIONS.get(_canonical_role(role), frozenset())
