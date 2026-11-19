"""Worker de anclas de reseñas para una red EVM."""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any


KIND_VERIFIED = "review.verified"


def _integer_setting(name: str, default: int, minimum: int = 1) -> int:
    try:
        value = int(os.environ.get(name, str(default)))
    except ValueError as exc:
        raise ValueError(f"{name} debe ser un entero") from exc
    if value < minimum:
        raise ValueError(f"{name} debe ser al menos {minimum}")
    return value


def _iso(at: datetime) -> str:
    return at.astimezone(timezone.utc).isoformat()


def _attempt_time(row: dict[str, Any]) -> datetime:
    value = row.get("submitted_at") or row.get("created_at")
    if not value:
        return datetime.now(timezone.utc)
    at = datetime.fromisoformat(str(value))
    return at.replace(tzinfo=timezone.utc) if at.tzinfo is None else at


def _retry_at(attempt: int, now: datetime) -> str | None:
    maximum = _integer_setting("ANCHOR_MAX_ATTEMPTS", 5)
    if attempt >= maximum:
        return None
    base = _integer_setting("ANCHOR_RETRY_BASE_SECONDS", 30)
    cap = _integer_setting("ANCHOR_RETRY_MAX_SECONDS", 1800)
    delay = min(cap, base * (2 ** min(max(0, attempt - 1), 32)))
    return _iso(now + timedelta(seconds=delay))


def _safe_error(exc: Exception) -> str:
    message = str(exc)
    for name in ("CHAIN_RPC_URL", "ANCHOR_PRIVATE_KEY"):
        secret = os.environ.get(name, "").strip()
        if secret:
            message = message.replace(secret, "[redacted]")
    return f"{type(exc).__name__}: {message}"[:200]


def _receipt_status(store, row, publisher, now, result, poll_seconds, timeout_seconds):
    review_id, kind, anchor_hash = row["review_id"], row.get("kind", KIND_VERIFIED), row["hash"]
    tx_hash = row.get("tx_hash")
    try:
        receipt = publisher.receipt(tx_hash)
    except Exception as exc:
        next_attempt = _iso(now + timedelta(seconds=poll_seconds))
        store.mark(review_id, "timeout", error=f"No se pudo consultar el recibo: {_safe_error(exc)}",
                   kind=kind, anchor_hash=anchor_hash, next_attempt_at=next_attempt)
        result["failed"] += 1
        return

    if receipt is None:
        elapsed = (now - _attempt_time(row)).total_seconds()
        status = "timeout" if elapsed >= timeout_seconds else "submitted"
        store.mark(review_id, status, kind=kind, anchor_hash=anchor_hash,
                   next_attempt_at=_iso(now + timedelta(seconds=poll_seconds)))
        return

    if int(receipt.get("status", 0)) == 1:
        store.mark(review_id, "confirmed", kind=kind, anchor_hash=anchor_hash)
        result["confirmed"] += 1
    else:
        store.mark(review_id, "reverted", error="La transacción fue revertida por la red.",
                   kind=kind, anchor_hash=anchor_hash)
        result["reverted"] += 1


def anchor_pending(store, limit: int = 50, mode: str | None = None,
                   publisher=None, lease_check=None) -> dict[str, Any]:
    """Procesa un lote sin mantener abierta la transacción de la reseña."""
    mode = (mode or os.environ.get("ANCHOR_MODE", "dry_run")).strip().lower()
    if mode not in {"off", "dry_run", "onchain"}:
        raise ValueError("ANCHOR_MODE debe ser off, dry_run u onchain")
    result = {
        "processed": 0, "submitted": 0, "confirmed": 0,
        "failed": 0, "reverted": 0, "exhausted": 0, "mode": mode,
    }
    if mode == "off":
        return result

    max_attempts = _integer_setting("ANCHOR_MAX_ATTEMPTS", 5)
    rows = store.pending(max(1, min(int(limit), 500)), max_attempts=max_attempts)
    if mode == "onchain" and rows and publisher is None:
        publisher = _OnchainPublisher()

    poll_seconds = _integer_setting("ANCHOR_RECEIPT_POLL_SECONDS", 20)
    timeout_seconds = _integer_setting("ANCHOR_RECEIPT_TIMEOUT", 120)
    for row in rows:
        if lease_check:
            lease_check()
        result["processed"] += 1
        kind = row.get("kind", KIND_VERIFIED)
        anchor_hash = row["hash"]
        status = row.get("status", "pending")
        now = datetime.now(timezone.utc)

        if mode == "dry_run":
            store.mark(row["review_id"], "simulated", kind=kind, anchor_hash=anchor_hash)
            result["submitted"] += 1
            continue

        if status in {"submitted", "timeout"} and row.get("tx_hash"):
            _receipt_status(store, row, publisher, now, result, poll_seconds, timeout_seconds)
            continue

        if status == "failed":
            attempts = int(row.get("attempts", 0))
            if attempts >= max_attempts:
                continue

        try:
            tx_hash, nonce = publisher.submit(anchor_hash)
        except Exception as exc:
            attempts = int(row.get("attempts", 0)) + 1
            store.mark(
                row["review_id"], "failed", error=_safe_error(exc), kind=kind,
                anchor_hash=anchor_hash,
                next_attempt_at=_retry_at(attempts, now),
            )
            result["failed"] += 1
            if attempts >= max_attempts:
                result["exhausted"] += 1
            continue

        submitted_at = _iso(now)
        store.mark(
            row["review_id"], "submitted", tx_hash=tx_hash, tx_nonce=nonce,
            submitted_at=submitted_at, kind=kind, anchor_hash=anchor_hash,
            next_attempt_at=_iso(now + timedelta(seconds=poll_seconds)),
        )
        result["submitted"] += 1

    return result


class _OnchainPublisher:
    """Cliente con nonce secuencial para la vida de una ejecución del worker."""

    def __init__(self) -> None:
        rpc_url = os.environ.get("CHAIN_RPC_URL", "").strip()
        contract_address = os.environ.get("ANCHOR_CONTRACT", "").strip()
        private_key = os.environ.get("ANCHOR_PRIVATE_KEY", "").strip()
        if not rpc_url or not contract_address or not private_key:
            raise RuntimeError(
                "ANCHOR_MODE=onchain requiere CHAIN_RPC_URL, ANCHOR_CONTRACT y "
                "ANCHOR_PRIVATE_KEY."
            )
        try:
            from web3 import Web3
            from web3.exceptions import TransactionNotFound
        except ImportError as exc:  # pragma: no cover - depende del despliegue
            raise RuntimeError("Instala web3 para usar ANCHOR_MODE=onchain") from exc

        self._transaction_not_found = TransactionNotFound
        self.web3 = Web3(Web3.HTTPProvider(
            rpc_url,
            request_kwargs={"timeout": _integer_setting("ANCHOR_RPC_TIMEOUT", 30)},
        ))
        if not self.web3.is_connected():
            raise RuntimeError("No se pudo conectar al CHAIN_RPC_URL configurado")
        if not self.web3.is_address(contract_address):
            raise ValueError("ANCHOR_CONTRACT no es una dirección EVM válida")

        configured_chain_id = os.environ.get("CHAIN_ID", "").strip()
        actual_chain_id = int(self.web3.eth.chain_id)
        if configured_chain_id and int(configured_chain_id) != actual_chain_id:
            raise RuntimeError(
                f"CHAIN_ID no coincide con la red RPC ({configured_chain_id} != {actual_chain_id})"
            )

        self.account = self.web3.eth.account.from_key(private_key)
        address = self.web3.to_checksum_address(contract_address)
        if not self.web3.eth.get_code(address):
            raise RuntimeError("ANCHOR_CONTRACT no contiene bytecode en la red configurada")
        method = os.environ.get("ANCHOR_CONTRACT_METHOD", "anchor").strip()
        if method != "anchor":
            raise ValueError("La versión actual del worker requiere ANCHOR_CONTRACT_METHOD=anchor")
        abi = [{
            "inputs": [{"internalType": "bytes32", "name": "hash", "type": "bytes32"}],
            "name": "anchor",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function",
        }]
        self.contract = self.web3.eth.contract(address=address, abi=abi)
        self.chain_id = actual_chain_id
        self.next_nonce = int(self.web3.eth.get_transaction_count(self.account.address, "pending"))

    def submit(self, anchor_hash: str) -> tuple[str, int]:
        if len(anchor_hash) != 64 or any(c not in "0123456789abcdefABCDEF" for c in anchor_hash):
            raise ValueError("El hash del ancla debe ser SHA-256 hexadecimal de 64 caracteres")
        network_nonce = int(self.web3.eth.get_transaction_count(self.account.address, "pending"))
        nonce = max(self.next_nonce, network_nonce)
        transaction = self.contract.functions.anchor(bytes.fromhex(anchor_hash)).build_transaction({
            "from": self.account.address,
            "nonce": nonce,
            "chainId": self.chain_id,
            "gas": _integer_setting("ANCHOR_GAS_LIMIT", 150000),
            "gasPrice": self.web3.eth.gas_price,
        })
        signed = self.account.sign_transaction(transaction)
        tx_hash = self.web3.eth.send_raw_transaction(signed.raw_transaction).hex()
        self.next_nonce = nonce + 1
        return tx_hash, nonce

    def receipt(self, tx_hash: str):
        try:
            return self.web3.eth.get_transaction_receipt(tx_hash)
        except self._transaction_not_found:
            return None


def _send_onchain(anchor_hash: str) -> str:
    """Compatibilidad con llamadas antiguas; el worker nuevo persiste antes de esperar."""
    from web3.exceptions import TimeExhausted

    publisher = _OnchainPublisher()
    tx_hash, _ = publisher.submit(anchor_hash)
    try:
        receipt = publisher.web3.eth.wait_for_transaction_receipt(
            tx_hash,
            timeout=_integer_setting("ANCHOR_RECEIPT_TIMEOUT", 120),
            poll_latency=2,
        )
    except TimeExhausted as exc:
        raise RuntimeError(f"La transacción {tx_hash} sigue pendiente de confirmación") from exc
    if int(receipt.get("status", 0)) != 1:
        raise RuntimeError(f"La transacción {tx_hash} fue revertida")
    return tx_hash
