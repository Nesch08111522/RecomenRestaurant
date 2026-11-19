"""Batch signing and verification for PostgreSQL audit-integrity chains."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)

from database.connection import connection
from models.ai_decision import _decision_integrity_payload
from utils.integrity import (
    acquire_stream_lock,
    root_digest,
    sign_root,
    signing_key,
    signing_key_id,
    verify_chain_records,
    verify_signature,
)


STREAMS = ("audit_events", "ai_decisions")
SIGNATURE_ALGORITHM = "HMAC-SHA256"


def _read_stream(cur: Any, stream: str) -> list[dict[str, Any]]:
    if stream == "audit_events":
        cur.execute(
            """SELECT id, payload, integrity_sequence, integrity_prev_hash,
                      integrity_payload_hash
               FROM public.app_records
               WHERE collection='audit_events' AND integrity_sequence IS NOT NULL
               ORDER BY integrity_sequence"""
        )
    else:
        cur.execute(
            """SELECT * FROM public.ai_decisions
               WHERE integrity_sequence IS NOT NULL
               ORDER BY integrity_sequence"""
        )
    return list(cur.fetchall())


def _audit_payload(record: dict[str, Any]) -> dict[str, Any]:
    payload = dict(record["payload"])
    if (
        payload.get("integrity_sequence") != record["integrity_sequence"]
        or payload.get("integrity_prev_hash") != record["integrity_prev_hash"]
        or payload.get("integrity_payload_hash") != record["integrity_payload_hash"]
    ):
        raise ValueError("Los metadatos de cadena no coinciden con la fila.")
    payload.pop("integrity_payload_hash", None)
    return payload


def _payload_for(stream: str, record: dict[str, Any]) -> dict[str, Any]:
    if stream == "audit_events":
        return _audit_payload(record)
    return _decision_integrity_payload(record)


def _verify_stream(stream: str, records: list[dict[str, Any]]) -> list[str]:
    return verify_chain_records(
        records, lambda record: _payload_for(stream, record)
    )


def _root_message(
    stream: str,
    sequence_from: int,
    sequence_to: int,
    event_count: int,
    digest: str,
    key_id: str,
) -> dict[str, Any]:
    return {
        "stream": stream,
        "sequence_from": sequence_from,
        "sequence_to": sequence_to,
        "event_count": event_count,
        "root_hash": digest,
        "signature_algorithm": SIGNATURE_ALGORITHM,
        "signing_key_id": key_id,
    }


def sign_pending_roots(*, batch_size: int = 500) -> int:
    if batch_size < 1:
        raise ValueError("batch_size debe ser mayor que cero")
    key = signing_key()
    key_id = signing_key_id(key)
    created = 0
    with connection() as conn:
        with conn.cursor() as cur:
            for stream in STREAMS:
                acquire_stream_lock(cur, stream)
            for stream in STREAMS:
                records = _read_stream(cur, stream)
                errors = _verify_stream(stream, records)
                if errors:
                    raise RuntimeError(
                        f"No se firma {stream}: cadena inválida ({errors[0]})."
                    )
                cur.execute(
                    """SELECT COALESCE(MAX(sequence_to), 0) AS last_sequence
                       FROM public.integrity_roots WHERE stream=%s""",
                    (stream,),
                )
                last_sequence = int(cur.fetchone()["last_sequence"])
                pending = [
                    record
                    for record in records
                    if int(record["integrity_sequence"]) > last_sequence
                ]
                for offset in range(0, len(pending), batch_size):
                    batch = pending[offset : offset + batch_size]
                    first, last, digest = root_digest(stream, batch)
                    message = _root_message(
                        stream, first, last, len(batch), digest, key_id
                    )
                    cur.execute(
                        """INSERT INTO public.integrity_roots
                           (stream, sequence_from, sequence_to, event_count, root_hash,
                            signature, signature_algorithm, signing_key_id,
                            verification_status, verified_at)
                           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,'verified',NOW())""",
                        (
                            stream,
                            first,
                            last,
                            len(batch),
                            digest,
                            sign_root(message, key),
                            SIGNATURE_ALGORITHM,
                            key_id,
                        ),
                    )
                    created += 1
        conn.commit()
    return created


def verify_integrity() -> tuple[list[str], int]:
    key = signing_key()
    key_id = signing_key_id(key)
    errors: list[str] = []
    checked_roots = 0
    with connection() as conn:
        with conn.cursor() as cur:
            for stream in STREAMS:
                acquire_stream_lock(cur, stream)
            for stream in STREAMS:
                records = _read_stream(cur, stream)
                stream_errors = _verify_stream(stream, records)
                errors.extend(f"{stream}: {error}" for error in stream_errors)
                cur.execute(
                    "SELECT * FROM public.integrity_roots WHERE stream=%s ORDER BY sequence_from",
                    (stream,),
                )
                roots = list(cur.fetchall())
                for root in roots:
                    checked_roots += 1
                    first = int(root["sequence_from"])
                    last = int(root["sequence_to"])
                    batch = [
                        record
                        for record in records
                        if first
                        <= int(record["integrity_sequence"])
                        <= last
                    ]
                    valid = not stream_errors
                    try:
                        calculated_from, calculated_to, digest = root_digest(
                            stream, batch
                        )
                        message = _root_message(
                            stream,
                            calculated_from,
                            calculated_to,
                            len(batch),
                            digest,
                            root["signing_key_id"],
                        )
                        valid = (
                            valid
                            and len(batch) == int(root["event_count"])
                            and calculated_from == first
                            and calculated_to == last
                            and digest == root["root_hash"]
                            and root["signature_algorithm"] == SIGNATURE_ALGORITHM
                            and root["signing_key_id"] == key_id
                            and verify_signature(message, root["signature"], key)
                        )
                    except (ValueError, IndexError):
                        valid = False
                    status = "verified" if valid else "failed"
                    if not valid:
                        errors.append(
                            f"{stream}: firma/raíz inválida para secuencias {first}-{last}"
                        )
                    cur.execute(
                        """UPDATE public.integrity_roots
                           SET verification_status=%s, verified_at=NOW() WHERE id=%s""",
                        (status, root["id"]),
                    )
        conn.commit()
    return errors, checked_roots


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    sign_parser = subparsers.add_parser("sign", help="Firmar lotes pendientes")
    sign_parser.add_argument("--batch-size", type=int, default=500)
    subparsers.add_parser("verify", help="Verificar cadenas y raíces firmadas")
    args = parser.parse_args(argv)
    try:
        if args.command == "sign":
            count = sign_pending_roots(batch_size=args.batch_size)
            print(f"Raíces firmadas: {count}")
            return 0
        errors, checked = verify_integrity()
        if errors:
            for error in errors:
                print(f"ERROR: {error}")
            print(f"Verificación fallida; raíces revisadas: {checked}")
            return 1
        print(f"Integridad válida; raíces verificadas: {checked}")
        return 0
    except Exception as error:
        print(f"No se pudo completar la operación de integridad ({type(error).__name__}).")
        return 1


if __name__ == "__main__":
    sys.exit(main())
