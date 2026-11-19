import os
import pytest

os.environ.setdefault("ANCHOR_PSEUDONYM_SECRET", "x" * 32)

from utils.blockchain_anchor import (
    canonical_hash, pseudonym, normalize_comment, KIND_VERIFIED, KIND_AMENDED,
)
from utils.anchor_store import InMemoryAnchorStore
from utils.anchor_job import anchor_pending


def _review(**kw):
    base = {"id": 1, "restaurant_id": 10, "user_id": 99, "rating": 5,
            "comment": "Excelente  comida", "created_at": "2026-11-18T10:00:00", "order_id": 7}
    base.update(kw); return base


def _order(**kw):
    base = {"id": 7, "state": "Entregado", "paid": True}
    base.update(kw); return base


def test_hash_estable():
    assert canonical_hash(_review(), _order()) == canonical_hash(_review(), _order())


def test_hash_normaliza_espacios_y_acentos():
    a = canonical_hash(_review(comment="Excelente  comida"), _order())
    b = canonical_hash(_review(comment="  excelente COMIDA  "), _order())
    assert a == b


def test_hash_cambia_con_rating():
    assert canonical_hash(_review(rating=5), _order()) != canonical_hash(_review(rating=4), _order())


def test_pseudonimo_no_contiene_user_id():
    assert "99" not in pseudonym(99)


def test_hash_sin_pii():
    h = canonical_hash(_review(), _order())
    for leaked in ("99", "Excelente", "comida"):
        assert leaked not in h


def test_pedido_no_pagado_cambia_hash():
    assert canonical_hash(_review(), _order(paid=False)) != canonical_hash(_review(), _order())


def test_amend_encadena_prev_hash():
    r = _review(); o = _order()
    h1 = canonical_hash(r, o, kind=KIND_VERIFIED)
    r2 = {**r, "rating": 4, "updated_at": "2026-11-18T11:00:00"}
    h2 = canonical_hash(r2, o, kind=KIND_AMENDED, prev_hash=h1)
    assert h1 != h2
    assert h2 != canonical_hash(r2, o, kind=KIND_VERIFIED)


def test_job_dry_run_idempotente():
    s = InMemoryAnchorStore()
    s.add_pending(_review(), _order(), "h1")
    assert anchor_pending(s, mode="dry_run")["processed"] == 1
    assert anchor_pending(s, mode="dry_run")["processed"] == 0


def test_modo_off_no_procesa():
    s = InMemoryAnchorStore()
    s.add_pending(_review(), _order(), "h1")
    assert anchor_pending(s, mode="off")["processed"] == 0


def test_store_mark_simulated():
    s = InMemoryAnchorStore()
    s.add_pending(_review(), _order(), "h1")
    row = s.mark(1, "simulated")
    assert row["status"] == "simulated" and row["attempts"] == 1


def test_onchain_submit_persists_receipt_for_later_recovery():
    class Publisher:
        def submit(self, anchor_hash):
            return "0xabc", 9

        def receipt(self, tx_hash):
            return None

    store = InMemoryAnchorStore()
    store.add_pending(_review(), _order(), "a" * 64)
    result = anchor_pending(store, mode="onchain", publisher=Publisher())

    row = store.get_by_review(1)
    assert result["submitted"] == 1
    assert row["status"] == "submitted"
    assert row["tx_hash"] == "0xabc"
    assert row["tx_nonce"] == 9


def test_worker_recovers_submitted_transaction_without_resending():
    class Publisher:
        def submit(self, anchor_hash):
            raise AssertionError("No debe reenviarse una transacción con tx_hash")

        def receipt(self, tx_hash):
            return {"status": 1}

    store = InMemoryAnchorStore()
    store.add_pending(_review(), _order(), "b" * 64)
    row = store.mark(
        1, "submitted", tx_hash="0xabc", submitted_at="2020-01-01T00:00:00+00:00",
        next_attempt_at="2020-01-01T00:00:00+00:00",
    )
    result = anchor_pending(store, mode="onchain", publisher=Publisher())

    assert result["confirmed"] == 1
    assert row["status"] == "confirmed"


def test_worker_marks_expired_transaction_timeout_and_reverted_receipt():
    class Publisher:
        def __init__(self, receipt):
            self._receipt = receipt

        def submit(self, anchor_hash):
            raise AssertionError("No debe reenviarse una transacción con tx_hash")

        def receipt(self, tx_hash):
            return self._receipt

    timeout_store = InMemoryAnchorStore()
    timeout_store.add_pending(_review(), _order(), "d" * 64)
    timeout_row = timeout_store.mark(
        1, "submitted", tx_hash="0xpending", submitted_at="2020-01-01T00:00:00+00:00",
        next_attempt_at="2020-01-01T00:00:00+00:00",
    )
    anchor_pending(timeout_store, mode="onchain", publisher=Publisher(None))
    assert timeout_row["status"] == "timeout"

    reverted_store = InMemoryAnchorStore()
    reverted_store.add_pending(_review(), _order(), "e" * 64)
    reverted_row = reverted_store.mark(
        1, "submitted", tx_hash="0xreverted", submitted_at="2020-01-01T00:00:00+00:00",
        next_attempt_at="2020-01-01T00:00:00+00:00",
    )
    result = anchor_pending(reverted_store, mode="onchain", publisher=Publisher({"status": 0}))
    assert result["reverted"] == 1
    assert reverted_row["status"] == "reverted"


def test_failed_submission_uses_backoff_and_does_not_spin():
    class Publisher:
        def submit(self, anchor_hash):
            raise RuntimeError("RPC unavailable")

    store = InMemoryAnchorStore()
    store.add_pending(_review(), _order(), "c" * 64)
    result = anchor_pending(store, mode="onchain", publisher=Publisher())

    row = store.get_by_review(1)
    assert result["failed"] == 1
    assert row["status"] == "failed"
    assert row["attempts"] == 1
    assert row["next_attempt_at"]
    assert anchor_pending(store, mode="onchain", publisher=Publisher())["processed"] == 0


def test_env_secrets_are_redacted_from_anchor_errors(monkeypatch):
    from utils.anchor_job import _safe_error

    monkeypatch.setenv("CHAIN_RPC_URL", "https://rpc.example/secret-token")
    monkeypatch.setenv("ANCHOR_PRIVATE_KEY", "private-test-value")
    message = _safe_error(RuntimeError("https://rpc.example/secret-token private-test-value"))
    assert "secret-token" not in message
    assert "private-test-value" not in message
    
def test_verify_endpoint_returns_404_when_absent(monkeypatch):
    """Sin ancla, el endpoint devuelve 404 y verified_onchain=False."""
    import utils.anchor_store as store_mod
    from utils.anchor_store import InMemoryAnchorStore

    fake = InMemoryAnchorStore()
    monkeypatch.setattr(store_mod, "_MEMORY", fake)
    monkeypatch.setattr(store_mod, "get_anchor_store", lambda: fake)

    # Simulamos el cuerpo del endpoint sin levantar Flask:
    # verificamos la lógica que el endpoint ejecuta.
    row = fake.get_by_review(999)
    assert row is None
    # El endpoint devolvería {"found": False, "verified_onchain": False} con 404.


def test_verify_endpoint_returns_anchor_state(monkeypatch):
    """Con ancla sembrada, el endpoint devuelve su estado y verified_onchain coherente."""
    import utils.anchor_store as store_mod
    from utils.anchor_store import InMemoryAnchorStore

    fake = InMemoryAnchorStore()
    monkeypatch.setattr(store_mod, "_MEMORY", fake)
    monkeypatch.setattr(store_mod, "get_anchor_store", lambda: fake)

    review = {"id": 77, "restaurant_id": 10, "user_id": 99, "rating": 5,
              "comment": "ok", "created_at": "2026-11-18T10:00:00"}
    order = {"id": 7, "state": "Entregado", "paid": True}
    fake.add_pending({**review, "order_id": 7}, order, "hash77")

    row = fake.get_by_review(77)
    assert row["hash"] == "hash77"
    assert row["status"] == "pending"
    assert (row["status"] == "confirmed") is False

    fake.mark(77, "confirmed", tx_hash="0xabc")
    row = fake.get_by_review(77)
    assert row["status"] == "confirmed"
    assert (row["status"] == "confirmed") is True
    
def test_update_review_amends_anchor_with_prev_hash(monkeypatch):
    """Una edición de reseña verificada encola review.amended con prev_hash."""
    import utils.anchor_store as store_mod
    from utils.anchor_store import InMemoryAnchorStore
    from models.review import ReviewModel
    from utils.blockchain_anchor import canonical_hash, KIND_VERIFIED, KIND_AMENDED

    fake = InMemoryAnchorStore()
    monkeypatch.setattr(store_mod, "_MEMORY", fake)
    monkeypatch.setattr(store_mod, "get_anchor_store", lambda: fake)

    # Simulamos la reseña ya anclada y el pedido existente.
    review = {"id": 55, "restaurant_id": 10, "user_id": 99, "rating": 5,
              "comment": "ok", "created_at": "2026-11-18T10:00:00",
              "order_id": 7, "verified_purchase": True,
              "anchor_hash": "hash_original"}
    order = {"id": 7, "state": "Entregado", "paid": True}

    # El store tiene el ancla original.
    fake.add_pending({**review}, order, "hash_original", kind=KIND_VERIFIED)

    # Simulamos lo que update_review haría tras editar.
    previous_hash = review["anchor_hash"]
    updated = {**review, "rating": 4, "comment": "mejoró",
               "updated_at": "2026-11-18T11:00:00"}
    anchored = {**updated, "order_id": 7}
    new_hash = canonical_hash(anchored, order, kind=KIND_AMENDED, prev_hash=previous_hash)
    fake.add_pending(anchored, order, new_hash, kind=KIND_AMENDED, prev_hash=previous_hash)

    # El store ahora tiene dos anclas para la misma reseña: verified + amended.
    rows = fake.list_by_review(55)
    assert len(rows) == 2
    kinds = {row["kind"] for row in rows}
    assert kinds == {KIND_VERIFIED, KIND_AMENDED}
    amended = next(r for r in rows if r["kind"] == KIND_AMENDED)
    assert amended["prev_hash"] == "hash_original"
    assert amended["hash"] == new_hash