from utils.integrity import (
    GENESIS_HASH,
    digest_payload,
    root_digest,
    sign_root,
    verify_chain_records,
    verify_signature,
)


def _record(sequence, previous_hash, payload):
    record = {
        "integrity_sequence": sequence,
        "integrity_prev_hash": previous_hash,
        "content": payload,
    }
    record["integrity_payload_hash"] = digest_payload(record)
    return record


def test_chain_verification_detects_tampered_middle_event():
    first = _record(1, GENESIS_HASH, "first")
    second = _record(2, first["integrity_payload_hash"], "second")
    third = _record(3, second["integrity_payload_hash"], "third")
    records = [first, second, third]

    def payload_for(record):
        return {key: value for key, value in record.items() if key != "integrity_payload_hash"}

    assert verify_chain_records(records, payload_for) == []

    second["content"] = "altered"
    errors = verify_chain_records(records, payload_for)
    assert "secuencia 2: payload_hash no coincide" in errors

    second["integrity_payload_hash"] = digest_payload(payload_for(second))
    errors = verify_chain_records(records, payload_for)
    assert "secuencia 2: payload_hash no coincide" not in errors
    assert "secuencia 3: prev_hash no coincide" in errors


def test_root_signature_covers_range_count_and_hashes():
    record = _record(1, GENESIS_HASH, "event")
    first, last, digest = root_digest("audit_events", [record])
    message = {
        "stream": "audit_events",
        "sequence_from": first,
        "sequence_to": last,
        "event_count": 1,
        "root_hash": digest,
    }
    key = b"test-signing-key-that-is-at-least-32-bytes"
    signature = sign_root(message, key)

    assert verify_signature(message, signature, key)
    assert not verify_signature({**message, "event_count": 2}, signature, key)
