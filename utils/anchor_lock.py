"""Lease de PostgreSQL para evitar workers de anclaje concurrentes."""
from __future__ import annotations

import logging
import os
import threading
import uuid

from database.connection import connection

logger = logging.getLogger(__name__)


class AnchorWorkerAlreadyRunning(RuntimeError):
    """Otra instancia tiene un lease vigente del worker de anclaje."""


class AnchorWorkerLease:
    def __init__(self) -> None:
        self.owner_id = str(uuid.uuid4())
        self.lease_name = "review-anchors"
        self.lease_seconds = self._setting("ANCHOR_WORKER_LEASE_SECONDS", 180)
        rpc_timeout = self._setting("ANCHOR_RPC_TIMEOUT", 30)
        if self.lease_seconds < rpc_timeout + 30:
            raise ValueError("ANCHOR_WORKER_LEASE_SECONDS debe superar ANCHOR_RPC_TIMEOUT por 30 segundos")
        self.heartbeat_seconds = max(5, self.lease_seconds // 3)
        self._stop = threading.Event()
        self._lost = threading.Event()
        self._thread: threading.Thread | None = None
        self._heartbeat_error: Exception | None = None

    @staticmethod
    def _setting(name: str, default: int) -> int:
        try:
            value = int(os.environ.get(name, str(default)))
        except ValueError as exc:
            raise ValueError(f"{name} debe ser un entero") from exc
        if value < 1:
            raise ValueError(f"{name} debe ser al menos 1")
        return value

    def __enter__(self):
        try:
            with connection() as conn, conn.cursor() as cur:
                cur.execute(
                    """INSERT INTO public.anchor_worker_leases (lease_name, owner_id, lease_until)
                       VALUES (%s, %s, CURRENT_TIMESTAMP + (%s * INTERVAL '1 second'))
                       ON CONFLICT (lease_name) DO UPDATE
                       SET owner_id = EXCLUDED.owner_id, lease_until = EXCLUDED.lease_until,
                           updated_at = CURRENT_TIMESTAMP
                       WHERE public.anchor_worker_leases.lease_until <= CURRENT_TIMESTAMP
                       RETURNING owner_id""",
                    (self.lease_name, self.owner_id, self.lease_seconds),
                )
                acquired = cur.fetchone()
                conn.commit()
        except Exception as exc:
            if getattr(exc, "sqlstate", None) == "42P01":
                raise RuntimeError(
                    "Falta public.anchor_worker_leases; aplica database/anchor_worker.sql."
                ) from exc
            raise
        if not acquired:
            raise AnchorWorkerAlreadyRunning("Otra instancia ya ejecuta el worker de anclaje.")
        self._thread = threading.Thread(target=self._heartbeat, name="anchor-worker-lease", daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=self.heartbeat_seconds + 1)
        try:
            with connection() as conn, conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM public.anchor_worker_leases WHERE lease_name=%s AND owner_id=%s",
                    (self.lease_name, self.owner_id),
                )
                conn.commit()
        except Exception:
            logger.exception("No se pudo liberar el lease del worker de anclaje")

    def check(self) -> None:
        if self._lost.is_set():
            raise RuntimeError("Se perdió el lease del worker de anclaje") from self._heartbeat_error

    def _heartbeat(self) -> None:
        while not self._stop.wait(self.heartbeat_seconds):
            try:
                with connection() as conn, conn.cursor() as cur:
                    cur.execute(
                        """UPDATE public.anchor_worker_leases
                           SET lease_until=CURRENT_TIMESTAMP + (%s * INTERVAL '1 second'),
                               updated_at=CURRENT_TIMESTAMP
                           WHERE lease_name=%s AND owner_id=%s
                           RETURNING owner_id""",
                        (self.lease_seconds, self.lease_name, self.owner_id),
                    )
                    renewed = cur.fetchone()
                    conn.commit()
                if not renewed:
                    self._lost.set()
                    return
            except Exception as exc:
                self._heartbeat_error = exc
                self._lost.set()
                logger.exception("Falló la renovación del lease del worker de anclaje")
                return


def worker_lease() -> AnchorWorkerLease:
    return AnchorWorkerLease()
