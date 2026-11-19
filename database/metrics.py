"""Bounded process-local timing aggregates. Never store SQL or parameter values."""
from collections import OrderedDict
from hashlib import sha256
import logging
from threading import Lock
from time import perf_counter
import psycopg

_lock = Lock()
_metrics = OrderedDict()
logger = logging.getLogger('smartresto.performance')


def observe(name, seconds, *, failed=False):
    with _lock:
        if name not in _metrics and len(_metrics) >= 128:
            _metrics.popitem(last=False)
        item = _metrics.setdefault(name, dict(count=0, total_ms=0, max_ms=0, errors=0))
        ms = seconds * 1000
        item['count'] += 1
        item['total_ms'] += ms
        item['max_ms'] = max(item['max_ms'], ms)
        item['errors'] += int(failed)


def snapshot():
    with _lock:
        return {name: {**row, 'mean_ms': row['total_ms'] / row['count']} for name, row in _metrics.items()}


class TimedCursor(psycopg.Cursor):
    def execute(self, query, params=None, **kwargs):
        from database.connection import isolated_query
        query = isolated_query(query, self.connection)
        # The digest distinguishes query shapes without logging their contents.
        fingerprint = sha256(str(query).encode()).hexdigest()[:12]
        start = perf_counter()
        failed = False
        try:
            return super().execute(query, params, **kwargs)
        except Exception as error:
            failed = True
            state = getattr(error, 'sqlstate', None)
            if state in {'57014', '55P03', '28P01', '28000'}:
                observe('sqlstate:' + state, 0, failed=True)
            raise
        finally:
            elapsed = perf_counter() - start
            observe('sql:' + fingerprint, elapsed, failed=failed)
            if elapsed >= 1:
                logger.warning('slow_sql fingerprint=%s elapsed_ms=%.1f failed=%s', fingerprint, elapsed * 1000, failed)
