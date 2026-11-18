"""Almacén de anclas de reseñas.

Interfaz + implementación en memoria (tests) + implementación PostgreSQL (producción).
La implementación PostgreSQL solo se usa si ANCHOR_STORE=postgres; por defecto
la app usa memoria para no requerir base durante el desarrollo del ancla.
"""
from __future__ import annotations

import os
import threading
from datetime import datetime, timezone
from typing import Any, Protocol

from database.repository import PostgresDocumentRepository as Repo

ANCHOR_COLLECTION = "trust_anchors"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class AnchorStore(Protocol):
    def add_pending(self, review: dict[str, Any], order: dict[str, Any], anchor_hash: str,
                    kind: str = "review.verified", prev_hash: str | None = None) -> dict[str, Any]: ...
    def get_by_review(self, review_id: int) -> dict[str, Any] | None: ...
    def list_by_review(self, review_id: int) -> list[dict[str, Any]]: ...
    def pending(self, limit: int = 50) -> list[dict[str, Any]]: ...
    def mark(self, review_id: int, status: str, tx_hash: str | None = None,
             error: str | None = None, kind: str = "review.verified") -> dict[str, Any] | None: ...


class InMemoryAnchorStore:
    """Implementación en memoria. Una fila por (review_id, kind)."""

    def __init__(self) -> None:
        self._rows: dict[tuple[int, str], dict[str, Any]] = {}
        self._lock = threading.Lock()

    def add_pending(self, review, order, anchor_hash, kind="review.verified", prev_hash=None):
        key = (int(review["id"]), kind)
        with self._lock:
            row = {
                "review_id": int(review["id"]),
                "business_id": int(review["restaurant_id"]),
                "order_id": int(review.get("order_id") or order.get("id") or 0),
                "kind": kind,
                "prev_hash": prev_hash,
                "hash": anchor_hash,
                "status": "pending",
                "tx_hash": None,
                "attempts": 0,
                "created_at": _now_iso(),
            }
            self._rows[key] = row
            return row

    def get_by_review(self, review_id: int):
        with self._lock:
            verified = self._rows.get((int(review_id), "review.verified"))
            amended = self._rows.get((int(review_id), "review.amended"))
            return amended or verified

    def list_by_review(self, review_id: int):
        with self._lock:
            return [row for (rid, _), row in sorted(self._rows.items()) if rid == int(review_id)]

    def pending(self, limit: int = 50):
        with self._lock:
            return [row for row in self._rows.values() if row["status"] == "pending"][:limit]

    def mark(self, review_id, status, tx_hash=None, error=None, kind="review.verified"):
        key = (int(review_id), kind)
        with self._lock:
            row = self._rows.get(key)
            if not row:
                return None
            row["status"] = status
            if tx_hash:
                row["tx_hash"] = tx_hash
            if error:
                row["last_error"] = error[:200]
            row["attempts"] += 1
            return row


class PostgresAnchorStore:
    """Producción: una fila en public.app_records por (review_id, kind).

    Idempotencia: antes de insertar, busca una fila existente con el mismo
    review_id y kind. Si existe y está pending/simulated, la devuelve; si está
    confirmed, la devuelve sin reenviar. Así el job puede reintentar sin duplicar.
    """

    def add_pending(self, review, order, anchor_hash, kind="review.verified", prev_hash=None):
        existing = self._find(review["id"], kind)
        if existing:
            return existing
        row = {
            "review_id": int(review["id"]),
            "business_id": int(review["restaurant_id"]),
            "order_id": int(review.get("order_id") or order.get("id") or 0),
            "kind": kind,
            "prev_hash": prev_hash,
            "hash": anchor_hash,
            "status": "pending",
            "tx_hash": None,
            "attempts": 0,
            "created_at": _now_iso(),
        }
        return Repo.create(ANCHOR_COLLECTION, row)

    def get_by_review(self, review_id: int):
        amended = self._find(review_id, "review.amended")
        verified = self._find(review_id, "review.verified")
        return amended or verified

    def list_by_review(self, review_id: int):
        return [row for row in Repo.all(ANCHOR_COLLECTION)
                if int(row.get("review_id", -1)) == int(review_id)]

    def pending(self, limit: int = 50):
        rows = [row for row in Repo.all(ANCHOR_COLLECTION) if row.get("status") == "pending"]
        rows.sort(key=lambda r: r.get("created_at", ""))
        return rows[:limit]

    def mark(self, review_id, status, tx_hash=None, error=None, kind="review.verified"):
        row = self._find(review_id, kind)
        if not row:
            return None
        changes = {"status": status, "attempts": int(row.get("attempts", 0)) + 1}
        if tx_hash:
            changes["tx_hash"] = tx_hash
        if error:
            changes["last_error"] = error[:200]
        return Repo.update(ANCHOR_COLLECTION, row["id"], changes)

    def _find(self, review_id: int, kind: str):
        for row in Repo.all(ANCHOR_COLLECTION):
            if int(row.get("review_id", -1)) == int(review_id) and row.get("kind") == kind:
                return row
        return None


_MEMORY = InMemoryAnchorStore()


def get_anchor_store() -> AnchorStore:
    """Selector. Por defecto memoria; postgres solo si se pide explícitamente."""
    if os.environ.get("ANCHOR_STORE", "memory").lower() == "postgres":
        return PostgresAnchorStore()
    return _MEMORY