"""Auditoría de acciones sensibles sin guardar secretos ni cuerpos completos."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any

from flask import has_request_context, request, session

from config import Config
from database.repository import document_transaction
from models.base import DataModel
from utils.integrity import acquire_stream_lock, chain_head, digest_payload
from utils.security import normalize_text


class AuditEventModel(DataModel):
    collection = "audit_events"

    @classmethod
    def create(cls, event: dict[str, Any]) -> dict[str, Any]:
        """Persist an event and its chain link in one serialized transaction."""
        with document_transaction() as conn:
            with conn.cursor() as cur:
                acquire_stream_lock(cur, "audit_events")
                sequence, previous_hash = chain_head(cur, "audit_events")
                payload = dict(event)
                payload.update(
                    integrity_sequence=sequence + 1,
                    integrity_prev_hash=previous_hash,
                )
                cur.execute(
                    """INSERT INTO public.app_records
                       (collection, payload, integrity_sequence, integrity_prev_hash,
                        integrity_payload_hash)
                       VALUES ('audit_events', %s::jsonb, %s, %s, NULL)
                       RETURNING id""",
                    (
                        json.dumps(payload, ensure_ascii=False),
                        sequence + 1,
                        previous_hash,
                    ),
                )
                payload["id"] = cur.fetchone()["id"]
                payload_hash = digest_payload(payload)
                payload["integrity_payload_hash"] = payload_hash
                cur.execute(
                    """UPDATE public.app_records
                       SET payload=%s::jsonb, integrity_payload_hash=%s
                       WHERE collection='audit_events' AND id=%s""",
                    (
                        json.dumps(payload, ensure_ascii=False),
                        payload_hash,
                        payload["id"],
                    ),
                )
        return payload

    @classmethod
    def update(cls, item_id: int, updated_data: dict[str, Any]):
        raise RuntimeError("Los eventos de auditoría encadenados no se pueden editar.")

    @classmethod
    def delete(cls, item_id: int):
        raise RuntimeError("Los eventos de auditoría encadenados no se pueden eliminar.")


SENSITIVE_ACTIONS = {
    "ACCOUNT_RATE_LIMIT", "ACCOUNT_RECOVERED", "ACCOUNT_MFA_ENABLED", "PAYMENT_INCIDENT",
    "OFFER_REVIEW", "BUSINESS_PLAN_APPLIED",
    "DISCOVERY_SOURCE_REGISTER", "DISCOVERY_INGEST", "DISCOVERY_REVIEW",
    "DISCOVERY_INVITATION", "DISCOVERY_CLAIM_REQUEST", "DISCOVERY_CLAIM_REVIEW",
    "ADMIN_USER_UPDATE",
    "ADMIN_USER_DELETE",
    "ADMIN_RESTAURANT_CREATE",
    "ADMIN_RESTAURANT_UPDATE",
    "ADMIN_RESTAURANT_DELETE",
    "ADMIN_APPROVAL_DECISION",
    "ADMIN_APPROVAL_REVERT",
    "ADMIN_OWNER_IMPROVEMENT_NOTIFICATION",
    "ADMIN_USER_SUSPEND",
    "ADMIN_CATEGORY_CREATE",
    "ADMIN_CATEGORY_UPDATE",
    "ADMIN_COMMERCE_SETTINGS",
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
