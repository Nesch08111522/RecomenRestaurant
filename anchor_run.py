"""Ejecuta una pasada del worker o lo mantiene en modo recurrente."""
from __future__ import annotations

import argparse
import json
import logging
import os
import time

from app import create_app
from utils.anchor_job import anchor_pending
from utils.anchor_lock import worker_lease
from utils.anchor_store import get_anchor_store

logger = logging.getLogger("anchor_worker")


def _arguments():
    parser = argparse.ArgumentParser(description="Worker de anclaje de reseñas")
    parser.add_argument("--watch", action="store_true", help="Ejecutar periódicamente")
    parser.add_argument(
        "--interval",
        type=int,
        default=int(os.environ.get("ANCHOR_WORKER_INTERVAL_SECONDS", "60")),
        help="Intervalo de sondeo en segundos",
    )
    parser.add_argument("--limit", type=int, default=50, help="Máximo de anclas por pasada")
    return parser.parse_args()


def main():
    args = _arguments()
    if args.interval < 1:
        raise ValueError("--interval debe ser al menos 1 segundo")
    if not 1 <= args.limit <= 500:
        raise ValueError("--limit debe estar entre 1 y 500")
    if os.environ.get("ANCHOR_STORE", "memory").strip().lower() != "postgres":
        raise RuntimeError("El worker recurrente requiere ANCHOR_STORE=postgres.")

    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"))
    app = create_app()
    with app.app_context(), worker_lease() as lease:
        store = get_anchor_store()
        while True:
            lease.check()
            result = anchor_pending(
                store, limit=args.limit, lease_check=lease.check
            )
            logger.info("Resultado del worker de anclaje: %s", json.dumps(result, sort_keys=True))
            if not args.watch:
                return
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
