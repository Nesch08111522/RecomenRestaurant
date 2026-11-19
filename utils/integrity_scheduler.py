"""Optional background scheduler for audit-integrity signing and verification."""
from __future__ import annotations

import logging
import os
import threading
import time
from collections.abc import Mapping

logger = logging.getLogger(__name__)
_worker_lock = threading.Lock()
_worker_thread: threading.Thread | None = None


def should_start_integrity_worker(
    app_config: Mapping[str, object],
    environ: Mapping[str, str] | None = None,
) -> bool:
    """Apply testing and Werkzeug-reloader guards before starting the worker."""
    env = os.environ if environ is None else environ
    if not app_config.get("INTEGRITY_AUTO_ENABLED"):
        return False
    if app_config.get("TESTING") or "PYTEST_CURRENT_TEST" in env:
        return False
    if app_config.get("DEBUG") and env.get("WERKZEUG_RUN_MAIN") != "true":
        return False
    return True


def run_integrity_cycle(batch_size: int) -> None:
    """Run signing and verification independently so one failure does not skip the other."""
    from scripts.integrity_audit import sign_pending_roots, verify_integrity

    try:
        created = sign_pending_roots(batch_size=batch_size)
        logger.info("Integridad: raices nuevas firmadas=%s", created)
    except Exception:
        logger.exception("Fallo la firma periodica de raices de integridad.")

    try:
        errors, checked_roots = verify_integrity()
        if errors:
            logger.error(
                "Verificacion periodica de integridad fallida; raices revisadas=%s, "
                "errores=%s",
                checked_roots,
                errors,
            )
        else:
            logger.info(
                "Verificacion periodica de integridad correcta; raices revisadas=%s",
                checked_roots,
            )
    except Exception:
        logger.exception("Fallo la verificacion periodica de la cadena de integridad.")


def _worker_loop(interval_seconds: int, batch_size: int) -> None:
    while True:
        time.sleep(interval_seconds)
        run_integrity_cycle(batch_size)


def start_integrity_worker(app_config: Mapping[str, object]) -> bool:
    """Start at most one daemon worker in this process."""
    global _worker_thread
    if not should_start_integrity_worker(app_config):
        return False

    interval_seconds = max(10, int(app_config["INTEGRITY_INTERVAL_SECONDS"]))
    batch_size = max(1, int(app_config["INTEGRITY_BATCH_SIZE"]))
    with _worker_lock:
        if _worker_thread and _worker_thread.is_alive():
            return False
        _worker_thread = threading.Thread(
            target=_worker_loop,
            args=(interval_seconds, batch_size),
            name="audit-integrity-worker",
            daemon=True,
        )
        _worker_thread.start()
    logger.info(
        "Worker de integridad iniciado: intervalo=%ss, lote=%s",
        interval_seconds,
        batch_size,
    )
    return True
