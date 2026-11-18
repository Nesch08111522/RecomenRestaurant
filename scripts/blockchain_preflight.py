"""Comprobación de solo lectura de la integración EVM.

No firma ni envía transacciones y nunca imprime la clave privada.
Ejecutar desde la raíz: python scripts/blockchain_preflight.py
"""
from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from web3 import Web3
from eth_utils import keccak

load_dotenv()


def main() -> int:
    rpc = os.getenv("CHAIN_RPC_URL", "").strip()
    contract = os.getenv("ANCHOR_CONTRACT", "").strip()
    private = os.getenv("ANCHOR_PRIVATE_KEY", "").strip().removeprefix("0x")
    expected_chain = os.getenv("CHAIN_ID", "").strip()

    print("RPC configurado:", bool(rpc))
    if not rpc:
        print("ERROR: falta CHAIN_RPC_URL")
        return 1

    web3 = Web3(Web3.HTTPProvider(rpc, request_kwargs={"timeout": 20}))
    connected = web3.is_connected()
    print("RPC conectado:", connected)
    if not connected:
        return 1

    chain_id = web3.eth.chain_id
    print("Chain ID:", chain_id)
    if expected_chain and int(expected_chain) != chain_id:
        print("ERROR: CHAIN_ID no coincide con la red del RPC")
        return 1

    valid_address = web3.is_address(contract)
    print("Contrato válido:", valid_address)
    if not valid_address:
        return 1

    checksum = Web3.to_checksum_address(contract)
    code = web3.eth.get_code(checksum)
    print("Código del contrato (bytes):", len(code))
    if not code:
        print("ERROR: no hay contrato desplegado en esa dirección")
        return 1

    selector = keccak(text="anchor(bytes32)")[:4]
    print("Método anchor(bytes32) detectado:", selector in bytes(code))

    key_shape = len(private) == 64 and all(c in "0123456789abcdefABCDEF" for c in private)
    print("Formato de clave privada válido:", key_shape)
    if not key_shape:
        print("ERROR: ANCHOR_PRIVATE_KEY debe contener 32 bytes, es decir 64 caracteres hexadecimales")
        return 1

    account = web3.eth.account.from_key(private)
    balance = web3.eth.get_balance(account.address)
    print("Wallet firmante:", account.address)
    print("Saldo (wei):", balance)
    print("Saldo suficiente para intentar gas:", balance > 0)
    if balance == 0:
        print("ERROR: la wallet no tiene saldo de testnet para gas")
        return 1

    print("PREFLIGHT OK: la integración está lista para una transacción on-chain")
    return 0


if __name__ == "__main__":
    sys.exit(main())
