"""Job que envía anclas pendientes a la cadena. Idempotente. Modos: off|dry_run|onchain."""
from __future__ import annotations

import os


def anchor_pending(store, limit: int = 50, mode: str | None = None) -> dict:
    mode = (mode or os.environ.get("ANCHOR_MODE", "dry_run")).lower()
    if mode == "off":
        return {"processed": 0, "mode": "off"}
    processed = 0
    for row in store.pending(limit):
        kind = row.get("kind", "review.verified")
        h = row["hash"]
        if mode == "dry_run":
            store.mark(row["review_id"], "simulated", kind=kind, anchor_hash=h)
            processed += 1
            continue
        try:
            tx = _send_onchain(h)
            store.mark(row["review_id"], "submitted", tx_hash=tx, kind=kind, anchor_hash=h)
        except Exception as exc:  # noqa: BLE001
            store.mark(row["review_id"], "failed", error=str(exc), kind=kind, anchor_hash=h)
        processed += 1
    return {"processed": processed, "mode": mode}


def _send_onchain(anchor_hash: str) -> str:
    """Stub. Se reemplaza cuando exista CHAIN_RPC_URL y ANCHOR_CONTRACT."""
    raise RuntimeError("ANCHOR_MODE=onchain requiere configurar CHAIN_RPC_URL y ANCHOR_CONTRACT.")