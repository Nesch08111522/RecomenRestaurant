"""Primitivas de repositorio PostgreSQL para adopción incremental.

Las subclases deben declarar el nombre de tabla y columnas permitidas en código.
Nunca se acepta table/column desde request; los valores siempre se parametrizan.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, ClassVar
from copy import deepcopy

from database.connection import connection, transaction_limits

try:
    from psycopg.types.json import Jsonb
except ImportError:  # pragma: no cover - the configured backend requires psycopg
    Jsonb = None


class PostgresRepository:
    table: ClassVar[str]
    columns: ClassVar[frozenset[str]]

    @classmethod
    def _validate_mapping(cls, values: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(values, dict):
            raise TypeError("values debe ser un objeto")
        unknown = set(values) - set(cls.columns)
        if unknown:
            raise ValueError(f"Campos no permitidos: {sorted(unknown)}")
        return values

    @classmethod
    def all(cls, *, limit: int = 1000, offset: int = 0) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 5000))
        offset = max(0, int(offset))
        with connection() as conn, conn.cursor() as cur:
            transaction_limits(conn)
            cur.execute(f"SELECT * FROM {cls.table} ORDER BY id LIMIT %s OFFSET %s", (limit, offset))
            return list(cur.fetchall())

    @classmethod
    def get_by_id(cls, item_id: int) -> dict[str, Any] | None:
        with connection() as conn, conn.cursor() as cur:
            transaction_limits(conn)
            cur.execute(f"SELECT * FROM {cls.table} WHERE id=%s", (int(item_id),))
            return cur.fetchone()

    @classmethod
    def create(cls, values: dict[str, Any]) -> dict[str, Any]:
        values = cls._validate_mapping(values)
        if not values:
            raise ValueError("No hay campos para insertar")
        names = list(values)
        placeholders = ",".join(["%s"] * len(names))
        query = f"INSERT INTO {cls.table} ({','.join(names)}) VALUES ({placeholders}) RETURNING *"
        with connection() as conn, conn.cursor() as cur:
            transaction_limits(conn)
            cur.execute(query, tuple(values[name] for name in names))
            result = cur.fetchone()
            conn.commit()
            return result

    @classmethod
    def update(cls, item_id: int, values: dict[str, Any]) -> dict[str, Any] | None:
        values = cls._validate_mapping(values)
        if not values:
            raise ValueError("No hay campos para actualizar")
        names = list(values)
        assignments = ",".join(f"{name}=%s" for name in names)
        query = f"UPDATE {cls.table} SET {assignments}, updated_at=CURRENT_TIMESTAMP WHERE id=%s RETURNING *"
        with connection() as conn, conn.cursor() as cur:
            transaction_limits(conn)
            cur.execute(query, tuple(values[name] for name in names) + (int(item_id),))
            result = cur.fetchone()
            conn.commit()
            return result

    @classmethod
    def delete(cls, item_id: int) -> bool:
        with connection() as conn, conn.cursor() as cur:
            transaction_limits(conn)
            cur.execute(f"DELETE FROM {cls.table} WHERE id=%s", (int(item_id),))
            deleted = cur.rowcount == 1
            conn.commit()
            return deleted


_document_connection = ContextVar("document_connection", default=None)


@contextmanager
def document_transaction():
    """Share one commit or rollback across a document change and its audit event."""
    active = _document_connection.get()
    if active is not None:
        yield active
        return
    with connection() as conn, conn.transaction():
        transaction_limits(conn)
        token = _document_connection.set(conn)
        try:
            yield conn
        finally:
            _document_connection.reset(token)


class PostgresDocumentRepository:
    """Persist flexible application records in a PostgreSQL JSONB collection."""

    table = "public.app_records"

    @staticmethod
    def _request_cache():
        from flask import has_request_context, g, request
        if not has_request_context() or request.method not in {'GET', 'HEAD'} or _document_connection.get() is not None:
            return None
        if not hasattr(g, '_document_reads'):
            g._document_reads = {}
        return g._document_reads

    @staticmethod
    def _invalidate(collection):
        from flask import has_request_context, g
        if has_request_context():
            getattr(g, '_document_reads', {}).pop(collection, None)

    @classmethod
    def _jsonb(cls, value: dict[str, Any]):
        if Jsonb is None:
            raise RuntimeError("La dependencia psycopg no está instalada.")
        return Jsonb(value)

    @classmethod
    def all(cls, collection: str) -> list[dict[str, Any]]:
        cache = cls._request_cache()
        if cache is not None and collection in cache:
            return deepcopy(cache[collection])
        with document_transaction() as conn, conn.cursor() as cur:
            cur.execute(
                f"SELECT payload FROM {cls.table} WHERE collection = %s ORDER BY id",
                (collection,),
            )
            rows = [row["payload"] for row in cur.fetchall()]
        if cache is not None and len(rows) <= 1000 and len(cache) < 16:
            cache[collection] = deepcopy(rows)
        return rows

    @classmethod
    def get_by_id(cls, collection: str, item_id: int, *, for_update: bool = False) -> dict[str, Any] | None:
        with document_transaction() as conn, conn.cursor() as cur:
            cur.execute(
                f"SELECT payload FROM {cls.table} WHERE collection = %s AND id = %s"
                + (" FOR UPDATE" if for_update else ""),
                (collection, int(item_id)),
            )
            row = cur.fetchone()
            return row["payload"] if row else None

    @classmethod
    def create(cls, collection: str, values: dict[str, Any]) -> dict[str, Any]:
        cls._invalidate(collection)
        if not isinstance(values, dict):
            raise TypeError("values debe ser un objeto")
        item = dict(values)
        raw_id = item.pop("id", None)
        with document_transaction() as conn, conn.cursor() as cur:
            if raw_id is None:
                cur.execute(
                    f"INSERT INTO {cls.table} (collection, payload) VALUES (%s, %s) RETURNING id",
                    (collection, cls._jsonb(item)),
                )
                item_id = cur.fetchone()["id"]
            else:
                item_id = int(raw_id)
                cur.execute(
                    f"INSERT INTO {cls.table} (collection, id, payload) VALUES (%s, %s, %s)",
                    (collection, item_id, cls._jsonb(item)),
                )
            item["id"] = item_id
            cur.execute(
                f"UPDATE {cls.table} SET payload = %s WHERE collection = %s AND id = %s",
                (cls._jsonb(item), collection, item_id),
            )
            return item

    @classmethod
    def update(
        cls, collection: str, item_id: int, values: dict[str, Any]
    ) -> dict[str, Any] | None:
        cls._invalidate(collection)
        if not isinstance(values, dict):
            raise TypeError("values debe ser un objeto")
        changes = dict(values)
        if "id" in changes and int(changes["id"]) != int(item_id):
            raise ValueError("El id del registro no se puede cambiar")
        changes["id"] = int(item_id)
        with document_transaction() as conn, conn.cursor() as cur:
            cur.execute(
                f"""UPDATE {cls.table}
                    SET payload = payload || %s, updated_at = CURRENT_TIMESTAMP
                    WHERE collection = %s AND id = %s
                    RETURNING payload""",
                (cls._jsonb(changes), collection, int(item_id)),
            )
            row = cur.fetchone()
            return row["payload"] if row else None

    @classmethod
    def delete(cls, collection: str, item_id: int) -> bool:
        cls._invalidate(collection)
        with document_transaction() as conn, conn.cursor() as cur:
            cur.execute(
                f"DELETE FROM {cls.table} WHERE collection = %s AND id = %s",
                (collection, int(item_id)),
            )
            deleted = cur.rowcount == 1
            return deleted

    @classmethod
    def replace_all(cls, collection: str, values: list[dict[str, Any]]) -> None:
        """Replace one collection atomically; used only by legacy model helpers."""
        cls._invalidate(collection)
        if not isinstance(values, list) or any(not isinstance(item, dict) for item in values):
            raise TypeError("values debe ser una lista de objetos")
        with document_transaction() as conn, conn.cursor() as cur:
            cur.execute(f"DELETE FROM {cls.table} WHERE collection = %s", (collection,))
            for value in values:
                item = dict(value)
                raw_id = item.pop("id", None)
                if raw_id is None:
                    cur.execute(
                        f"INSERT INTO {cls.table} (collection, payload) VALUES (%s, %s) RETURNING id",
                        (collection, cls._jsonb(item)),
                    )
                    item_id = cur.fetchone()["id"]
                else:
                    item_id = int(raw_id)
                    cur.execute(
                        f"INSERT INTO {cls.table} (collection, id, payload) VALUES (%s, %s, %s)",
                        (collection, item_id, cls._jsonb(item)),
                    )
                item["id"] = item_id
                cur.execute(
                    f"UPDATE {cls.table} SET payload = %s WHERE collection = %s AND id = %s",
                    (cls._jsonb(item), collection, item_id),
                )
            cur.execute(
                f"""SELECT setval(
                    pg_get_serial_sequence('{cls.table}', 'id'),
                    COALESCE(MAX(id), 1),
                    COUNT(*) > 0
                ) FROM {cls.table}"""
            )
