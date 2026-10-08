"""Conexión PostgreSQL opcional para SmartResto.

La aplicación continúa usando JSON por defecto. Esta capa solo se activa cuando
DATA_BACKEND=postgresql y DATABASE_URL está configurada. No crea tablas ni
migra datos automáticamente para evitar cambios irreversibles durante el
arranque del servidor.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from config import Config

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover - permite ejecutar el backend JSON sin psycopg
    psycopg = None
    dict_row = None


class DatabaseConfigurationError(RuntimeError):
    """La configuración PostgreSQL está incompleta o la dependencia falta."""


def postgres_enabled() -> bool:
    return str(getattr(Config, "DATA_BACKEND", "json")).lower() in {"postgres", "postgresql"}


def require_postgres() -> None:
    if not postgres_enabled():
        raise DatabaseConfigurationError(
            "PostgreSQL no está habilitado. Define DATA_BACKEND=postgresql para usarlo."
        )
    if not getattr(Config, "DATABASE_URL", None):
        raise DatabaseConfigurationError("DATABASE_URL no está configurada.")
    if psycopg is None:
        raise DatabaseConfigurationError(
            "La dependencia psycopg no está instalada; instala requirements.txt."
        )


@contextmanager
def connection(*, autocommit: bool = False) -> Iterator[object]:
    """Abrir una conexión con row factories seguras y cierre garantizado."""
    require_postgres()
    conn = psycopg.connect(Config.DATABASE_URL, row_factory=dict_row)
    conn.autocommit = autocommit
    try:
        yield conn
    except Exception:
        if not autocommit:
            conn.rollback()
        raise
    finally:
        conn.close()


def apply_schema() -> None:
    """Aplicar el esquema explícitamente; nunca se ejecuta durante create_app."""
    require_postgres()
    from pathlib import Path

    schema = (Path(__file__).with_name("schema.sql")).read_text(encoding="utf-8")
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(schema)
        conn.commit()
