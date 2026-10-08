"""Primitivas de repositorio PostgreSQL para adopción incremental.

Las subclases deben declarar el nombre de tabla y columnas permitidas en código.
Nunca se acepta table/column desde request; los valores siempre se parametrizan.
"""
from __future__ import annotations

from typing import Any, ClassVar

from database.connection import connection


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
            cur.execute(f"SELECT * FROM {cls.table} ORDER BY id LIMIT %s OFFSET %s", (limit, offset))
            return list(cur.fetchall())

    @classmethod
    def get_by_id(cls, item_id: int) -> dict[str, Any] | None:
        with connection() as conn, conn.cursor() as cur:
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
            cur.execute(query, tuple(values[name] for name in names) + (int(item_id),))
            result = cur.fetchone()
            conn.commit()
            return result

    @classmethod
    def delete(cls, item_id: int) -> bool:
        with connection() as conn, conn.cursor() as cur:
            cur.execute(f"DELETE FROM {cls.table} WHERE id=%s", (int(item_id),))
            deleted = cur.rowcount == 1
            conn.commit()
            return deleted
