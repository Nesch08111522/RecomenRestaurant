"""Almacén de anclas de reseñas.

Interfaz + implementación en memoria (tests) + implementación PostgreSQL (producción).
Una fila por (review_id, kind, hash): así cada edición conserva su propia ancla
y la cadena prev_hash se puede reconstruir completa.
"""
from __future__ import annotations

import os
import threading
from datetime import datetime, timezone
from typing import Any, Protocol

from database.repository import PostgresDocumentRepository as Repo

ANCHOR_COLLECTION = "trust_anchors"
KIND_VERIFIED = "review.verified"
KIND_AMENDED = "review.amended"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _latest(rows):
    return max(rows, key=lambda r: r.get("created_at", "")) if rows else None


def _current(rows):
    """Ancla vigente: la edición más reciente o, si no hay, el alta original."""
    amended = [r for r in rows if r.get("kind") == KIND_AMENDED]
    verified = [r for r in rows if r.get("kind") == KIND_VERIFIED]
    return _latest(amended) or _latest(verified)


def _build_row(review, order, anchor_hash, kind, prev_hash):
    return {
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


class AnchorStore(Protocol):
    def add_pending(self, review: dict[str, Any], order: dict[str, Any], anchor_hash: str,
                    kind: str = KIND_VERIFIED, prev_hash: str | None = None) -> dict[str, Any]: ...
    def get_by_review(self, review_id: int) -> dict[str, Any] | None: ...
    def list_by_review(self, review_id: int) -> list[dict[str, Any]]: ...
    def pending(self, limit: int = 50) -> list[dict[str, Any]]: ...
    def mark(self, review_id: int, status: str, tx_hash: str | None = None,
             error: str | None = None, kind: str = KIND_VERIFIED,
             anchor_hash: str | None = None) -> dict[str, Any] | None: ...


class InMemoryAnchorStore:
    """Implementación en memoria. Una fila por (review_id, kind, hash)."""

    def __init__(self) -> None:
        self._rows: dict[tuple[int, str, str], dict[str, Any]] = {}
        self._lock = threading.Lock()

    def add_pending(self, review, order, anchor_hash, kind=KIND_VERIFIED, prev_hash=None):
        key = (int(review["id"]), kind, anchor_hash)
        with self._lock:
            if key in self._rows:
                return self._rows[key]
            row = _build_row(review, order, anchor_hash, kind, prev_hash)
            self._rows[key] = row
            return row

    def _for_review(self, review_id):
        return [row for (rid, _, _), row in self._rows.items() if rid == int(review_id)]

    def get_by_review(self, review_id: int):
        with self._lock:
            return _current(self._for_review(review_id))

    def list_by_review(self, review_id: int):
        with self._lock:
            return sorted(self._for_review(review_id), key=lambda r: r["created_at"])

    def pending(self, limit: int = 50):
        with self._lock:
            return [row for row in self._rows.values() if row["status"] == "pending"][:limit]

    def mark(self, review_id, status, tx_hash=None, error=None, kind=KIND_VERIFIED, anchor_hash=None):
        with self._lock:
            rows = [r for r in self._for_review(review_id)
                    if r["kind"] == kind and (anchor_hash is None or r["hash"] == anchor_hash)]
            row = _latest(rows)
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
    """Producción: una fila en public.app_records por (review_id, kind, hash).

    Idempotente: si ya existe una fila con el mismo review_id, kind y hash,
    la devuelve sin duplicar. Una edición nueva tiene hash distinto y se guarda aparte.
    """

    def add_pending(self, review, order, anchor_hash, kind=KIND_VERIFIED, prev_hash=None):
        existing = self._find(review["id"], kind, anchor_hash)
        if existing:
            return existing
        return Repo.create(ANCHOR_COLLECTION, _build_row(review, order, anchor_hash, kind, prev_hash))

    def get_by_review(self, review_id: int):
        return _current(self._rows_for(review_id))

    def list_by_review(self, review_id: int):
        return sorted(self._rows_for(review_id), key=lambda r: r.get("created_at", ""))

    def pending(self, limit: int = 50):
        rows = [row for row in Repo.all(ANCHOR_COLLECTION) if row.get("status") == "pending"]
        rows.sort(key=lambda r: r.get("created_at", ""))
        return rows[:limit]

    def mark(self, review_id, status, tx_hash=None, error=None, kind=KIND_VERIFIED, anchor_hash=None):
        row = self._find(review_id, kind, anchor_hash)
        if not row:
            return None
        changes = {"status": status, "attempts": int(row.get("attempts", 0)) + 1}
        if tx_hash:
            changes["tx_hash"] = tx_hash
        if error:
            changes["last_error"] = error[:200]
        return Repo.update(ANCHOR_COLLECTION, row["id"], changes)

    def _rows_for(self, review_id: int):
        return [row for row in Repo.all(ANCHOR_COLLECTION)
                if int(row.get("review_id", -1)) == int(review_id)]

    def _find(self, review_id: int, kind: str, anchor_hash: str | None = None):
        rows = [r for r in self._rows_for(review_id)
                if r.get("kind") == kind and (anchor_hash is None or r.get("hash") == anchor_hash)]
        return _latest(rows)


_MEMORY = InMemoryAnchorStore()


def get_anchor_store() -> AnchorStore:
    """Selector. Por defecto memoria; postgres solo si se pide explícitamente."""
    if os.environ.get("ANCHOR_STORE", "memory").lower() == "postgres":
        return PostgresAnchorStore()
    return _MEMORY