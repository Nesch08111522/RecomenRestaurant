"""Job que envía anclas pendientes a una cadena EVM.

Modos: off | dry_run | onchain. La reseña solo encola; este worker publica.
"""
from __future__ import annotations

import os
from typing import Any


KIND_VERIFIED = "review.verified"


def anchor_pending(store, limit: int = 50, mode: str | None = None) -> dict[str, Any]:
    mode = (mode or os.environ.get("ANCHOR_MODE", "dry_run")).strip().lower()
    if mode not in {"off", "dry_run", "onchain"}:
        raise ValueError("ANCHOR_MODE debe ser off, dry_run u onchain")
    if mode == "off":
        return {"processed": 0, "submitted": 0, "failed": 0, "mode": mode}
    result = {"processed": 0, "submitted": 0, "failed": 0, "mode": mode}
    for row in store.pending(max(1, min(int(limit), 500))):
        kind = row.get("kind", KIND_VERIFIED)
        h = row["hash"]
        result["processed"] += 1
        if mode == "dry_run":
            store.mark(row["review_id"], "simulated", kind=kind, anchor_hash=h)
            result["submitted"] += 1
            continue
        try:
            tx = _send_onchain(h)
            store.mark(row["review_id"], "confirmed", tx_hash=tx, kind=kind, anchor_hash=h)
            result["submitted"] += 1
        except Exception as exc:  # noqa: BLE001
            store.mark(row["review_id"], "failed", error=str(exc), kind=kind, anchor_hash=h)
            result["failed"] += 1
    return result


def _send_onchain(anchor_hash: str) -> str:
    """Publica ``bytes32(anchor_hash)`` mediante ``anchor(bytes32)``.

    El nombre de la función puede cambiarse con ANCHOR_CONTRACT_METHOD. La
    clave privada se lee solo del entorno y nunca se incluye en logs.
    """
    rpc_url = os.environ.get("CHAIN_RPC_URL", "").strip()
    contract_address = os.environ.get("ANCHOR_CONTRACT", "").strip()
    private_key = os.environ.get("ANCHOR_PRIVATE_KEY", "").strip()
    if not rpc_url or not contract_address or not private_key:
        raise RuntimeError(
            "ANCHOR_MODE=onchain requiere CHAIN_RPC_URL, ANCHOR_CONTRACT y "
            "ANCHOR_PRIVATE_KEY."
        )
    if len(anchor_hash) != 64 or any(c not in "0123456789abcdefABCDEF" for c in anchor_hash):
        raise ValueError("El hash del ancla debe ser SHA-256 hexadecimal de 64 caracteres")
    try:
        from web3 import Web3
        from web3.exceptions import TimeExhausted
    except ImportError as exc:  # pragma: no cover - depende del despliegue
        raise RuntimeError("Instala web3 para usar ANCHOR_MODE=onchain") from exc

    web3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 30}))
    if not web3.is_connected():
        raise RuntimeError("No se pudo conectar al CHAIN_RPC_URL configurado")
    if not web3.is_address(contract_address):
        raise ValueError("ANCHOR_CONTRACT no es una dirección EVM válida")
    account = web3.eth.account.from_key(private_key)
    method = os.environ.get("ANCHOR_CONTRACT_METHOD", "anchor").strip()
    abi = [{
        "inputs": [{"internalType": "bytes32", "name": "hash", "type": "bytes32"}],
        "name": method,
        "outputs": [], "stateMutability": "nonpayable", "type": "function",
    }]
    contract = web3.eth.contract(address=Web3.to_checksum_address(contract_address), abi=abi)
    chain_id = os.environ.get("CHAIN_ID", "").strip()
    transaction = contract.functions[method](bytes.fromhex(anchor_hash)).build_transaction({
        "from": account.address,
        "nonce": web3.eth.get_transaction_count(account.address, "pending"),
        "chainId": int(chain_id) if chain_id else web3.eth.chain_id,
        "gas": int(os.environ.get("ANCHOR_GAS_LIMIT", "150000")),
        "gasPrice": web3.eth.gas_price,
    })
    signed = account.sign_transaction(transaction)
    tx_hash = web3.eth.send_raw_transaction(signed.raw_transaction)
    try:
        receipt = web3.eth.wait_for_transaction_receipt(
            tx_hash, timeout=int(os.environ.get("ANCHOR_RECEIPT_TIMEOUT", "120")), poll_latency=2
        )
    except TimeExhausted as exc:
        raise RuntimeError(f"La transacción {tx_hash.hex()} no confirmó a tiempo") from exc
    if receipt.get("status") != 1:
        raise RuntimeError(f"La transacción {tx_hash.hex()} fue revertida")
    return tx_hash.hex()
