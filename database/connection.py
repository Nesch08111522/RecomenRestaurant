"""Conexión PostgreSQL de SmartResto con Supabase.

El almacenamiento de la aplicación requiere DATABASE_URL y no tiene fallback
a archivos. Los cambios de esquema siguen siendo explícitos.
"""
from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator
from urllib.parse import parse_qs, parse_qsl, urlencode, urlsplit, urlunsplit

from config import Config
from time import perf_counter
from database.pool import get_pool, PoolBusy, PoolCoolingDown
from database.metrics import TimedCursor, observe

try:
    import psycopg
    from psycopg.rows import dict_row
except ImportError:  # pragma: no cover - permite ejecutar el backend JSON sin psycopg
    psycopg = None
    dict_row = None


class DatabaseConfigurationError(RuntimeError):
    """La configuración PostgreSQL está incompleta o la dependencia falta."""


class DatabaseConnectionError(RuntimeError):
    """La base no es accesible; mensaje seguro sin credenciales del driver."""


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
    try:
        parts = urlsplit(Config.DATABASE_URL)
        host, port = parts.hostname, parts.port
    except ValueError:
        raise DatabaseConfigurationError("DATABASE_URL contiene un host o puerto inválido.") from None
    if not host or port is not None and not 1 <= port <= 65535:
        raise DatabaseConfigurationError("DATABASE_URL requiere un host y puerto válidos.")
    if host.lower() in {"host_pooler", "pooler-host", "host", "region"} or any(c in host for c in '[]<>_'):
        raise DatabaseConfigurationError(
            "DATABASE_URL contiene un marcador de ejemplo, no un servidor real. "
            "Si definiste HOST_POOLER en PowerShell, ejecuta "
            "Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue "
            "para volver a usar tu .env sin modificarlo."
        )
    requested_sslmode = parse_qs(parts.query).get("sslmode", [None])[-1]
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
    """Lease a bounded connection; always rollback unfinished work before reuse."""
    require_postgres(require_enabled=require_enabled)
    # Supabase requiere SSL. Psycopg prepara consultas automáticamente después
    # de varias ejecuciones; se desactiva para que también funcione con el
    # pooler en modo transacción (puerto 6543).
    options = {
        "row_factory": dict_row,
        "prepare_threshold": None,
        "connect_timeout": max(2, min(Config.DATABASE_CONNECT_TIMEOUT, 30)),
        "cursor_factory": TimedCursor,
    }
    requested_sslmode = parse_qs(urlsplit(Config.DATABASE_URL).query).get("sslmode", [None])[-1]
    options["sslmode"] = requested_sslmode or getattr(Config, "DATABASE_SSLMODE", "require")
    dsn = _libpq_dsn(Config.DATABASE_URL)
    def connect():
        start = perf_counter()
        try:
            return psycopg.connect(dsn, **options)
        finally:
            observe('connection_establishment', perf_counter() - start)
    pool = get_pool((Config.DATABASE_URL, tuple(options.items()), Config.DATABASE_POOL_MAX, Config.DATABASE_POOL_TIMEOUT), connect,
                    maximum=max(1, min(Config.DATABASE_POOL_MAX, 16)),
                    timeout=max(.1, min(Config.DATABASE_POOL_TIMEOUT, 30)))
    start = perf_counter()
    try:
        conn, born = pool.acquire()
    except (PoolBusy, PoolCoolingDown):
        observe('pool_acquire', perf_counter() - start, failed=True)
        raise DatabaseConnectionError('La base de datos está ocupada o en pausa tras un fallo. Inténtalo más tarde.') from None
    except psycopg.OperationalError as error:
        detail = str(error).lower()
        observe('pool_acquire', perf_counter() - start, failed=True)
        if any(term in detail for term in ("getaddrinfo", "11001", "11004", "name or service not known", "could not translate host")):
            message = (
                "No se pudo resolver el host PostgreSQL. La conexión directa de Supabase "
                "puede requerir IPv6: comprueba la conectividad de tu red o usa los datos "
                "reales de Connect → Session pooler. Esto no indica que falten tablas."
            )
        elif any(term in detail for term in ("password authentication", "authentication failed", "tenant or user not found")):
            observe('authentication_failure', 0, failed=True)
            message = "PostgreSQL rechazó la autenticación. Comprueba usuario y credenciales de la conexión seleccionada."
        else:
            message = "No se pudo conectar a PostgreSQL. Comprueba acceso de red, puerto y TLS; no se modificaron datos."
        raise DatabaseConnectionError(message) from None
    observe('pool_acquire', perf_counter() - start)
    discard = False
    try:
        conn.autocommit = autocommit
        yield conn
    except psycopg.OperationalError:
        discard = True
        raise
    except Exception:
        if not autocommit:
            conn.rollback()
        raise
    finally:
        pool.release(conn, born, discard=discard)


def transaction_limits(conn):
    """LOCAL settings survive only this transaction, including on Supavisor."""
    conn.execute("SELECT set_config('statement_timeout', %s, true), set_config('lock_timeout', %s, true)",
                 (str(max(100, min(Config.DATABASE_STATEMENT_TIMEOUT_MS, 60000))),
                  str(max(100, min(Config.DATABASE_LOCK_TIMEOUT_MS, 10000)))))


def check_connection() -> bool:
    """Comprueba el acceso a PostgreSQL sin imprimir ni devolver credenciales."""
    # Verifica conectividad sin cambiar el esquema ni tocar datos.
    with connection(require_enabled=False) as conn, conn.cursor() as cur:
        transaction_limits(conn)
        cur.execute("SELECT 1 AS connected")
        row = cur.fetchone()
        return bool(row and row["connected"] == 1)


def check_application_schema() -> None:
    """Fail fast with setup instructions when the document table is missing."""
    with connection() as conn, conn.cursor() as cur:
        transaction_limits(conn)
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


