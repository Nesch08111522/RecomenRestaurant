"""Seller-scoped Mercado Pago Checkout Pro integration. Credentials stay on the server."""
import hashlib
import hmac
import json
import os
import urllib.request
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from uuid import NAMESPACE_URL, uuid5

from logic.market import MarketError


def token(rid):
    return os.getenv(f"MP_ACCESS_TOKEN_{rid}", "")


def enabled(rid):
    return bool(token(rid) and os.getenv("MP_WEBHOOK_SECRET") and public_url().startswith("https://"))


def public_url():
    return os.getenv("MARKET_PUBLIC_URL", "").rstrip("/")


def reference(order):
    return str(uuid5(NAMESPACE_URL, f"{public_url()}/mercado/pedidos/{order['id']}/{order['request_key']}"))


def call(rid, path, body=None, idem=None):
    headers = {"Authorization": "Bearer " + token(rid), "Content-Type": "application/json"}
    if idem:
        headers["X-Idempotency-Key"] = idem
    request = urllib.request.Request("https://api.mercadopago.com" + path,
                                     data=json.dumps(body).encode() if body is not None else None,
                                     headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            return json.load(response)
    except (HTTPError, URLError, TimeoutError, ValueError) as exc:
        raise MarketError("El proveedor no pudo confirmar la operación. Reintenta desde el pedido.") from exc


def checkout(order):
    if not enabled(order["rid"]):
        raise MarketError("El negocio no tiene cobro digital habilitado.")
    back = public_url() + "/mercado/pedidos"
    data = call(order["rid"], "/checkout/preferences", {
        "external_reference": reference(order), "metadata": {"order_id": order["id"]},
        "items": [{"id": str(order["id"]), "title": f"Pedido {order['id']} · {order['business']}",
                   "currency_id": "PEN", "quantity": 1, "unit_price": order["total"] / 100}],
        "notification_url": public_url() + f"/mercado/pagos/{order['rid']}/notificar",
        "back_urls": {"success": back, "failure": back, "pending": back},
        "expires": True, "expiration_date_to": order["slot"],
    }, reference(order))
    url = data.get("init_point", "")
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname not in {"www.mercadopago.com.pe", "www.mercadopago.com", "www.mercadopago.com.ar"}:
        raise MarketError("El proveedor no devolvió un enlace de pago válido.")
    return url


def signed(payment_id, request_id, signature):
    secret = os.getenv("MP_WEBHOOK_SECRET", "")
    fields = dict(part.strip().split("=", 1) for part in signature.split(",") if "=" in part)
    ts = fields.get("ts", "")
    if not secret or not payment_id.isascii() or not payment_id.isdigit() or not request_id or not ts.isdigit():
        return False
    manifest = f"id:{payment_id};request-id:{request_id};ts:{ts};"
    expected = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, fields.get("v1", ""))


def refund(rid, pid):
    result = call(rid, f"/v1/payments/{pid}/refunds", {}, str(uuid5(NAMESPACE_URL, f"{public_url()}/refund/{pid}")))
    if result.get("status") != "approved":
        raise MarketError("El reembolso aún requiere confirmación del proveedor.")

