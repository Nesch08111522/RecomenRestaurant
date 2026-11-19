"""Read-only bounded diagnostics: python -m database.diagnose [--network]."""
import argparse
import json
from pathlib import Path
import socket
import ssl
import struct
from time import perf_counter
from urllib.parse import urlsplit


def diagnose(network=False):
    from config import Config
    from database.connection import connection, require_postgres
    from database.pool import pool_stats, close_pool
    result = {'read_only': True}
    require_postgres()
    uri = urlsplit(Config.DATABASE_URL)
    host, port = uri.hostname, uri.port or 5432
    result['connection_mode_hint'] = ('transaction_pooler' if port == 6543 else 'session_pooler') if host.endswith('.pooler.supabase.com') else 'direct_or_custom'
    result['port'] = port
    result['sslmode'] = Config.DATABASE_SSLMODE

    def measure(name, fn):
        started = perf_counter()
        try:
            value = fn()
            result[name] = {'ok': True, 'ms': round((perf_counter()-started)*1000, 2), 'result': value}
            return True
        except Exception as error:
            result[name] = {'ok': False, 'ms': round((perf_counter()-started)*1000, 2), 'error_type': type(error).__name__}
            return False

    if network:
        def dns():
            addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
            return {'ipv4': sum(a[0] == socket.AF_INET for a in addresses), 'ipv6': sum(a[0] == socket.AF_INET6 for a in addresses)}
        if not measure('dns', dns):
            return result
        def tcp():
            with socket.create_connection((host, port), timeout=5):
                return 'reachable'
        measure('tcp', tcp)
        def tls():
            with socket.create_connection((host, port), timeout=5) as raw:
                raw.sendall(struct.pack('!II', 8, 80877103))
                if raw.recv(1) != b'S':
                    raise ssl.SSLError('TLS refused')
                with ssl.create_default_context().wrap_socket(raw, server_hostname=host) as secured:
                    return secured.version()
        measure('tcp_plus_verified_tls', tls)
    try:
        started = perf_counter()
        with connection() as conn:
            result['connection_and_authentication'] = {'ok': True, 'ms': round((perf_counter()-started)*1000, 2)}
            conn.execute('SET TRANSACTION READ ONLY')
            conn.execute("SET LOCAL statement_timeout='4000ms'")
            for sample in range(3):
                if not measure('select1_' + str(sample), lambda: conn.execute('SELECT 1 AS ok').fetchone()['ok']):
                    return result
            measure('schema', lambda: conn.execute("SELECT c.relrowsecurity AS rls, (SELECT count(*) FROM pg_constraint k WHERE k.conrelid=c.oid AND k.contype='p') AS primary_keys, (SELECT count(*) FROM pg_index i WHERE i.indrelid=c.oid AND i.indisvalid) AS valid_indexes FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relname='app_records'").fetchone())
            measure('explain_read', lambda: conn.execute("EXPLAIN (ANALYZE, BUFFERS, FORMAT JSON) SELECT payload FROM public.app_records WHERE collection=%s ORDER BY id LIMIT 20", ('restaurants',)).fetchone()['QUERY PLAN'])
        result['pool'] = pool_stats()
    except Exception as error:
        result['database_error'] = {'error_type': type(error).__name__, 'no_retry': True}
    finally:
        close_pool()
    return result


def main():
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[1] / '.env', override=False)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--network', action='store_true')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        result = diagnose(args.network)
    except Exception as error:
        result = {'configuration_error_type': type(error).__name__}
    text = json.dumps(result, indent=2, ensure_ascii=False, default=str)
    if args.output:
        args.output.write_text(text, encoding='utf-8')
    print(text)
    return 1 if any(key.endswith('error') or key.endswith('error_type') or
                    isinstance(value, dict) and value.get('ok') is False
                    for key, value in result.items()) else 0


if __name__ == '__main__':
    raise SystemExit(main())
