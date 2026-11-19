"""Small synchronous pool: bounded sockets, no autonomous authentication retries.

The caller owns each lease. No SQL is replayed, and no transaction spans requests.
"""
import atexit
import os
import random
from threading import Condition
from time import monotonic


class PoolBusy(RuntimeError):
    pass


class PoolCoolingDown(RuntimeError):
    pass


class ConnectionPool:
    def __init__(self, factory, *, maximum=4, timeout=5, idle=60, lifetime=300, cooldown=30):
        self.factory = factory
        self.maximum, self.timeout = maximum, timeout
        self.idle, self.lifetime, self.cooldown = idle, lifetime, cooldown
        self.pid = os.getpid()
        self.condition = Condition()
        self.available = []
        self.total = 0
        self.closed = False
        self.retry_after = 0
        self.failures = 0
        self.connecting = False
        self.created = 0
        self.wait_timeouts = 0

    def acquire(self):
        deadline = monotonic() + self.timeout
        while True:
            with self.condition:
                if self.closed or os.getpid() != self.pid:
                    raise PoolBusy('Pool no disponible en este proceso.')
                now = monotonic()
                if now < self.retry_after:
                    raise PoolCoolingDown('Conexión temporalmente en pausa; no se reintentó autenticar.')
                while self.available:
                    conn, born, returned = self.available.pop()
                    if conn.closed or conn.broken or now - born >= self.lifetime or now - returned >= self.idle:
                        self.total -= 1
                        conn.close()
                    else:
                        return conn, born
                # Serialize creation to prevent a burst of bad-password attempts.
                if self.total < self.maximum and not self.connecting:
                    self.total += 1
                    self.connecting = True
                    break
                remaining = deadline - now
                if remaining <= 0:
                    self.wait_timeouts += 1
                    raise PoolBusy('Tiempo de espera de conexión agotado.')
                self.condition.wait(remaining)
        try:
            conn = self.factory()
        except BaseException:
            with self.condition:
                self.total -= 1
                self.connecting = False
                self.failures += 1
                self.retry_after = monotonic() + min(300, self.cooldown * 2 ** min(self.failures - 1, 3)) * random.uniform(1, 1.1)
                self.condition.notify_all()
            raise
        with self.condition:
            self.connecting = False
            self.created += 1
            self.failures = 0
            self.retry_after = 0
            self.condition.notify_all()
            if self.closed:
                self.total -= 1
                conn.close()
                raise PoolBusy('Pool cerrado durante la conexión.')
        return conn, monotonic()

    def release(self, conn, born, *, discard=False):
        try:
            if not conn.closed and not conn.broken and not discard:
                conn.rollback()
                conn.autocommit = False
        except Exception:
            discard = True
        with self.condition:
            if self.closed or discard or conn.closed or conn.broken or monotonic() - born >= self.lifetime:
                conn.close()
                self.total -= 1
            else:
                self.available.append((conn, born, monotonic()))
            self.condition.notify_all()

    def stats(self):
        with self.condition:
            return dict(maximum=self.maximum, total=self.total, available=len(self.available),
                        in_use=self.total - len(self.available), created=self.created,
                        wait_timeouts=self.wait_timeouts, cooldown=monotonic() < self.retry_after)

    def close(self):
        with self.condition:
            self.closed = True
            for conn, _, _ in self.available:
                conn.close()
                self.total -= 1
            self.available.clear()
            self.condition.notify_all()


_pool = None
_key = None


def get_pool(key, factory, **options):
    # Only used to construct/swap pools; acquisition has its own condition.
    with _registry_lock:
        global _pool, _key
        key = (os.getpid(), key)
        if _pool is None or _key != key:
            if _pool is not None:
                _pool.close()
            _pool = ConnectionPool(factory, **options)
            _key = key
        return _pool


def close_pool():
    global _pool, _key
    with _registry_lock:
        if _pool is not None:
            _pool.close()
        _pool = _key = None


def pool_stats():
    return _pool.stats() if _pool else dict(total=0, available=0, in_use=0)


from threading import Lock
_registry_lock = Lock()
atexit.register(close_pool)
