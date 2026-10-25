"""Auditoría de acciones sensibles sin guardar secretos ni cuerpos completos."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from typing import Any

from flask import has_request_context, request, session

from config import Config
from models.base import DataModel
from utils.security import normalize_text


class AuditEventModel(DataModel):
    collection = "audit_events"


SENSITIVE_ACTIONS = {
    "ADMIN_USER_UPDATE",
    "ADMIN_USER_DELETE",
    "ADMIN_RESTAURANT_CREATE",
    "ADMIN_RESTAURANT_UPDATE",
    "ADMIN_RESTAURANT_DELETE",
    "ADMIN_APPROVAL_DECISION",
    "ADMIN_APPROVAL_REVERT",
    "ADMIN_USER_SUSPEND",
    "ADMIN_CATEGORY_UPDATE",
    "ADMIN_CATEGORY_DELETE",
}


def _safe_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    """Limitar metadatos a valores pequeños y no sensibles."""
    if not isinstance(metadata, dict):
        return {}
    safe: dict[str, Any] = {}
    for key, value in metadata.items():
        key = normalize_text(key, max_length=60)
        if not key or key.lower() in {"password", "password_hash", "token", "secret", "cookie", "authorization"}:
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            safe[key] = normalize_text(value, max_length=300) if isinstance(value, str) else value
        elif isinstance(value, list):
            safe[key] = [normalize_text(item, max_length=120) for item in value[:20]]
    return safe


def record_event(action: str, *, resource_type: str | None = None, resource_id: int | None = None,
                 metadata: dict[str, Any] | None = None, actor_user_id: int | None = None) -> dict[str, Any]:
    """Registrar una acción sensible y devolver el evento persistido."""
    if action not in SENSITIVE_ACTIONS:
        raise ValueError(f"Acción de auditoría no permitida: {action}")
    if actor_user_id is None:
        raw = session.get("user_id") if has_request_context() else None
        try:
            actor_user_id = int(raw) if raw is not None else None
        except (TypeError, ValueError):
            actor_user_id = None
    event = {
        "actor_user_id": actor_user_id,
        "action": action,
        "resource_type": normalize_text(resource_type, max_length=60) if resource_type else None,
        "resource_id": resource_id,
        "request_id": normalize_text(request.headers.get("X-Request-ID"), max_length=120) if has_request_context() else None,
        "ip_hash": hashlib.sha256(
            f"{Config.SECRET_KEY}:{request.remote_addr}".encode("utf-8")
        ).hexdigest() if has_request_context() and request.remote_addr else None,
        "metadata": _safe_metadata(metadata),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return AuditEventModel.create(event)
