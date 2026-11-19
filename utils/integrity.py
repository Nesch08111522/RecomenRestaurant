"""Shared primitives for PostgreSQL audit-chain integrity."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from collections.abc import Callable, Mapping
from datetime import date, datetime
from decimal import Decimal
from typing import Any


GENESIS_HASH = "0" * 64
STREAM_LOCKS = {
    "audit_events": (74932, 1),
    "ai_decisions": (74932, 2),
}


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value, "f")
    return value


def canonical_json(value: Any) -> bytes:
    """Serialize values deterministically for hashing and signatures."""
    return json.dumps(
        _json_safe(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def digest_payload(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def acquire_stream_lock(cursor: Any, stream: str) -> None:
    try:
        lock_key = STREAM_LOCKS[stream]
    except KeyError:
        raise ValueError(f"Flujo de integridad desconocido: {stream}") from None
    cursor.execute("SELECT pg_advisory_xact_lock(%s, %s)", lock_key)


def chain_head(cursor: Any, stream: str) -> tuple[int, str]:
    if stream == "ai_decisions":
        cursor.execute(
            """SELECT integrity_sequence, integrity_payload_hash
               FROM public.ai_decisions
               WHERE integrity_sequence IS NOT NULL
               ORDER BY integrity_sequence DESC LIMIT 1"""
        )
    elif stream == "audit_events":
        cursor.execute(
            """SELECT integrity_sequence, integrity_payload_hash
               FROM public.app_records
               WHERE collection = 'audit_events' AND integrity_sequence IS NOT NULL
               ORDER BY integrity_sequence DESC LIMIT 1"""
        )
    else:
        raise ValueError(f"Flujo de integridad desconocido: {stream}")
    row = cursor.fetchone()
    if not row:
        return 0, GENESIS_HASH
    return int(row["integrity_sequence"]), row["integrity_payload_hash"]


def verify_chain_records(
    records: list[Mapping[str, Any]],
    payload_for: Callable[[Mapping[str, Any]], Any],
) -> list[str]:
    """Return chain errors, including content, sequence, and link mismatches."""
    errors: list[str] = []
    previous_hash = GENESIS_HASH
    expected_sequence = 1
    for record in records:
        sequence = int(record["integrity_sequence"])
        if sequence != expected_sequence:
            errors.append(
                f"secuencia {sequence}: se esperaba {expected_sequence}"
            )
        if record["integrity_prev_hash"] != previous_hash:
            errors.append(f"secuencia {sequence}: prev_hash no coincide")
        try:
            calculated_hash = digest_payload(payload_for(record))
        except (KeyError, TypeError, ValueError):
            calculated_hash = ""
        if not hmac.compare_digest(
            str(record["integrity_payload_hash"] or ""), calculated_hash
        ):
            errors.append(f"secuencia {sequence}: payload_hash no coincide")
        previous_hash = str(record["integrity_payload_hash"] or "")
        expected_sequence = sequence + 1
    return errors


def root_digest(stream: str, records: list[Mapping[str, Any]]) -> tuple[int, int, str]:
    if not records:
        raise ValueError("No hay eventos para crear una raíz")
    first = int(records[0]["integrity_sequence"])
    last = int(records[-1]["integrity_sequence"])
    root = digest_payload(
        {
            "stream": stream,
            "sequence_from": first,
            "sequence_to": last,
            "event_count": len(records),
            "payload_hashes": [
                str(record["integrity_payload_hash"]) for record in records
            ],
        }
    )
    return first, last, root


def signing_key() -> bytes:
    configured = os.environ.get("AUDIT_SIGNING_KEY", "")
    key = configured.encode("utf-8")
    if len(key) < 32:
        raise RuntimeError(
            "AUDIT_SIGNING_KEY debe ser una clave propia de al menos 32 bytes."
        )
    return key


def signing_key_id(key: bytes) -> str:
    return hashlib.sha256(key).hexdigest()[:16]


def sign_root(message: Mapping[str, Any], key: bytes) -> str:
    return hmac.new(key, canonical_json(message), hashlib.sha256).hexdigest()


def verify_signature(message: Mapping[str, Any], signature: str, key: bytes) -> bool:
    return hmac.compare_digest(sign_root(message, key), signature)
