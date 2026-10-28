"""Conexión PostgreSQL de SmartResto con Supabase.

El almacenamiento de la aplicación requiere DATABASE_URL y no tiene fallback
a archivos. Los cambios de esquema siguen siendo explícitos.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator
from urllib.parse import parse_qs, parse_qsl, urlencode, urlsplit, urlunsplit

from config import Config

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover - permite ejecutar el backend JSON sin psycopg
    psycopg = None
    dict_row = None


class DatabaseConfigurationError(RuntimeError):
    """La configuración PostgreSQL está incompleta o la dependencia falta."""


def _libpq_dsn(dsn: str) -> str:
    """Quitar parámetros del dashboard de Supabase que libpq no entiende."""
    parts = urlsplit(dsn)
    # Algunas URI del pooler incluyen ``pgbouncer=true``. psycopg/libpq no
    # acepta ese parámetro; el comportamiento equivalente para psycopg 3 es
    # ``prepare_threshold=None`` en connect().
    query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True)
             if key.lower() != "pgbouncer"]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


def postgres_enabled() -> bool:
    return str(getattr(Config, "DATA_BACKEND", "postgresql")).lower() in {"postgres", "postgresql"}


def require_postgres(*, require_enabled: bool = True) -> None:
    if require_enabled and not postgres_enabled():
        raise DatabaseConfigurationError(
            "SmartResto usa exclusivamente PostgreSQL. Define DATA_BACKEND=postgresql."
        )
    if not getattr(Config, "DATABASE_URL", None):
        raise DatabaseConfigurationError("DATABASE_URL no está configurada.")
    if not Config.DATABASE_URL.lower().startswith(("postgres://", "postgresql://")):
        raise DatabaseConfigurationError("DATABASE_URL debe ser una URI postgres:// o postgresql://.")
    requested_sslmode = parse_qs(urlsplit(Config.DATABASE_URL).query).get("sslmode", [None])[-1]
    sslmode = requested_sslmode or getattr(Config, "DATABASE_SSLMODE", "require")
    if sslmode not in {"require", "verify-ca", "verify-full"}:
        raise DatabaseConfigurationError(
            "La conexión a Supabase debe usar sslmode=require, verify-ca o verify-full."
        )
    if psycopg is None:
        raise DatabaseConfigurationError(
            "La dependencia psycopg no está instalada; instala requirements.txt."
        )


@contextmanager
def connection(*, autocommit: bool = False, require_enabled: bool = True) -> Iterator[object]:
    """Abrir una conexión con row factories seguras y cierre garantizado."""
    require_postgres(require_enabled=require_enabled)
    # Supabase requiere SSL. Psycopg prepara consultas automáticamente después
    # de varias ejecuciones; se desactiva para que también funcione con el
    # pooler en modo transacción (puerto 6543).
    options = {
        "row_factory": dict_row,
        "prepare_threshold": None,
        "connect_timeout": 10,
    }
    requested_sslmode = parse_qs(urlsplit(Config.DATABASE_URL).query).get("sslmode", [None])[-1]
    options["sslmode"] = requested_sslmode or getattr(Config, "DATABASE_SSLMODE", "require")
    conn = psycopg.connect(_libpq_dsn(Config.DATABASE_URL), **options)
    conn.autocommit = autocommit
    try:
        yield conn
    except Exception:
        if not autocommit:
            conn.rollback()
        raise
    finally:
        conn.close()


def check_connection() -> bool:
    """Comprueba el acceso a PostgreSQL sin imprimir ni devolver credenciales."""
    # Verifica conectividad sin cambiar el esquema ni tocar datos.
    with connection(require_enabled=False) as conn, conn.cursor() as cur:
        cur.execute("SELECT 1 AS connected")
        row = cur.fetchone()
        return bool(row and row["connected"] == 1)


def check_application_schema() -> None:
    """Fail fast with setup instructions when the document table is missing."""
    with connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT to_regclass('public.app_records') AS table_name")
        row = cur.fetchone()
        if not row or not row["table_name"]:
            raise DatabaseConfigurationError(
                "Falta public.app_records en Supabase. Ejecuta el script "
                "database/app_records.sql en el SQL Editor antes de iniciar SmartResto."
            )
        cur.execute(
            """SELECT column_name FROM information_schema.columns
               WHERE table_schema = 'public' AND table_name = 'app_records'"""
        )
        actual_columns = {column["column_name"] for column in cur.fetchall()}
        required_columns = {"collection", "id", "payload", "created_at", "updated_at"}
        if not required_columns.issubset(actual_columns):
            raise DatabaseConfigurationError(
                "public.app_records no tiene el esquema esperado. Revisa "
                "database/app_records.sql antes de iniciar SmartResto."
            )


