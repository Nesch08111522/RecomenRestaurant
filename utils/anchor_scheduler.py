"""Worker automático de anclas integrado al proceso de aplicación."""
from __future__ import annotations

import logging
import os
import threading
import time
from collections.abc import Mapping

logger = logging.getLogger(__name__)
_worker_lock = threading.Lock()
_worker_thread: threading.Thread | None = None


def should_start_anchor_worker(config: Mapping[str, object], environ=None) -> bool:
    env = os.environ if environ is None else environ
    if config.get("TESTING") or "PYTEST_CURRENT_TEST" in env:
        return False
    if str(config.get("ANCHOR_STORE", "")).lower() != "postgres":
        return False
    return str(config.get("ANCHOR_MODE", "off")).lower() in {"dry_run", "onchain"}


def _setting(name: str, default: int, minimum: int = 1) -> int:
    try:
        value = int(os.environ.get(name, str(default)))
    except ValueError as exc:
        raise ValueError(f"{name} debe ser un entero") from exc
    return max(minimum, value)


def _run_loop(app_config: Mapping[str, object]) -> None:
    # Imports tardíos: no cargan PostgreSQL/web3 durante el arranque de tests.
    from utils.anchor_job import anchor_pending
    from utils.anchor_lock import AnchorWorkerAlreadyRunning, worker_lease
    from utils.anchor_store import get_anchor_store

    interval = _setting("ANCHOR_WORKER_INTERVAL_SECONDS", 60, minimum=5)
    limit = _setting("ANCHOR_WORKER_BATCH_SIZE", 50, minimum=1)
    while True:
        try:
            with worker_lease() as lease:
                store = get_anchor_store()
                result = anchor_pending(store, limit=min(limit, 500), lease_check=lease.check)
                logger.info("Resultado del worker automático de anclaje: %s", result)
        except AnchorWorkerAlreadyRunning:
            logger.info("Otro proceso mantiene el lease del worker de anclaje.")
        except Exception:
            logger.exception("Fallo en el ciclo automático de anclaje; se reintentará.")
        time.sleep(interval)


def start_anchor_worker(app_config: Mapping[str, object]) -> bool:
    """Inicia un único hilo por proceso; el lease coordina todos los procesos."""
    global _worker_thread
    if not should_start_anchor_worker(app_config):
        return False
    with _worker_lock:
        if _worker_thread and _worker_thread.is_alive():
            return False
        _worker_thread = threading.Thread(
            target=_run_loop,
            args=(app_config,),
            name="review-anchor-worker",
            daemon=True,
        )
        _worker_thread.start()
    logger.info(
        "Worker automático de anclaje iniciado: intervalo=%ss, lote=%s, modo=%s",
        _setting("ANCHOR_WORKER_INTERVAL_SECONDS", 60, minimum=5),
        _setting("ANCHOR_WORKER_BATCH_SIZE", 50, minimum=1),
        app_config.get("ANCHOR_MODE"),
    )
    return True
