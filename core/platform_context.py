"""Contexto de request para aislamiento de identidad y tenancy."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


_ROLE_SCOPE = {
    "guest": "public",
    "diner": "user",
    "user": "user",
    "business_owner": "business",
    "business_admin": "business",
    "manager": "business",
    "owner": "business",
    "cashier": "business",
    "waiter": "business",
    "kitchen": "business",
    "admin": "platform",
}


@dataclass(frozen=True, slots=True)
class PlatformContext:
    user_id: int | None = None
    role: str = "guest"
    business_id: int | None = None
    branch_id: int | None = None

    @property
    def scope(self) -> str:
        return _ROLE_SCOPE.get(self.role, "public")

    def as_public_dict(self) -> dict[str, Any]:
        """Expose only routing metadata; never return email or private profile data."""
        return {
            "authenticated": self.user_id is not None,
            "role": self.role,
            "scope": self.scope,
            "business_id": self.business_id,
            "branch_id": self.branch_id,
        }


def _integer(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def build_platform_context(session_data: Mapping[str, Any] | None) -> PlatformContext:
    data = session_data or {}
    user = data.get("user") or {}
    if not isinstance(user, Mapping):
        user = {}
    user_id = _integer(data.get("user_id") or user.get("id"))
    role = str(user.get("role") or data.get("role") or "guest")
    if user_id is None:
        return PlatformContext()
    return PlatformContext(
        user_id=user_id,
        role=role,
        business_id=_integer(user.get("business_id") or data.get("business_id")),
        branch_id=_integer(user.get("branch_id") or data.get("branch_id")),
    )
