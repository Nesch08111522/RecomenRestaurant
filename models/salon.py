"""Persistencia del salón: mesas, sesiones de atención y solicitudes.

Cada mesa pertenece a un establecimiento (``rid``); un negocio con varias
sucursales usa un ``rid`` por sucursal, igual que el resto de SmartResto.
Escanear el QR no crea una sesión: la sesión nace de una confirmación del
comensal autenticado o del personal, y es la única fuente de ocupación.
"""
from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

from database.repository import PostgresDocumentRepository as Repo, document_transaction
from logic.market import now
from logic.salon import (
    ACTIVE_STATES,
    ServiceError,
    active,
    occupancy_snapshot,
    order_total,
    split_equal,
    table_state,
    validate_shares,
)
from models.market import kitchen, lock_business, records, save_kitchen

TABLES = "restaurant_tables"
SESSIONS = "table_sessions"
REQUESTS = "service_requests"
VISIT_MINUTES = 360


def _text(value, limit):
    return " ".join(str(value or "").split())[:limit]


def tables(rid, *, active_only=True):
    rows = [row for row in records(TABLES, rid=rid) if row.get("active", True) or not active_only]
    return sorted(rows, key=lambda row: (row.get("floor", ""), row.get("zone", ""), row.get("label", ""), row["id"]))


def table_by_id(rid, table_id):
    row = Repo.get_by_id(TABLES, table_id)
    return row if row and row.get("rid") == rid else None


def table_by_token(token):
    if not isinstance(token, str) or len(token) != 32 or any(c not in "0123456789abcdef" for c in token):
        return None
    return next((row for row in records(TABLES, qr_token=token) if row.get("active", True)), None)


def save_table(rid, owner_id, data, table_id=None):
    label = _text(data.get("label"), 24)
    floor = _text(data.get("floor") or "Planta principal", 40)
    zone = _text(data.get("zone") or "General", 40)
    if not label:
        raise ServiceError("Indica el número o nombre de la mesa.")
    try:
        capacity = int(data.get("capacity") or 0)
        x = int(data.get("x")) if str(data.get("x", "")).strip() else None
        y = int(data.get("y")) if str(data.get("y", "")).strip() else None
    except (TypeError, ValueError):
        raise ServiceError("Revisa la capacidad y la posición de la mesa.") from None
    if not 1 <= capacity <= 40:
        raise ServiceError("La capacidad debe estar entre 1 y 40 personas.")
    if (x is not None and not 0 <= x <= 100) or (y is not None and not 0 <= y <= 100):
        raise ServiceError("La posición del plano debe estar entre 0 y 100.")
    with document_transaction():
        lock_business(rid)
        current = table_by_id(rid, table_id) if table_id else None
        if table_id and not current:
            raise ServiceError("La mesa ya no existe.")
        if any(t.get("label", "").casefold() == label.casefold()
               and (t.get("floor") or "Planta principal") == floor
               and (t.get("zone") or "General") == zone
               and t["id"] != (current or {}).get("id") for t in tables(rid, active_only=False)):
            raise ServiceError("Ya existe una mesa con ese nombre en el mismo piso y zona.")
        payload = {"rid": rid, "owner_id": owner_id, "label": label, "floor": floor, "zone": zone,
                   "capacity": capacity, "x": x, "y": y,
                   "active": (data.get("active") == "on") if table_id else data.get("active") is not False}
        if current:
            if not payload["active"] and active_session(current["id"]):
                raise ServiceError("No desactives una mesa con una sesión activa.")
            return Repo.update(TABLES, table_id, payload)
        payload.update({"qr_token": uuid4().hex, "created_at": now().isoformat()})
        return Repo.create(TABLES, payload)


def delete_table(rid, table_id):
    with document_transaction():
        table = table_by_id(rid, table_id)
        if not table:
            raise ServiceError("La mesa ya no existe.")
        if active_session(table_id):
            raise ServiceError("Cierra la sesión antes de eliminar la mesa.")
        sessions = records(SESSIONS, table_id=table_id)
        if any(s.get("status") == "Finalizada" and not s.get("cleaned_at") for s in sessions):
            raise ServiceError("Marca la mesa como limpia antes de eliminarla.")
        Repo.delete(TABLES, table_id)


def all_sessions(rid):
    return sorted(records(SESSIONS, rid=rid), key=lambda row: row.get("opened_at", ""))


def active_session(table_id):
    return next((row for row in records(SESSIONS, table_id=table_id) if active(row)), None)


def latest_session(table_id):
    rows = sorted(records(SESSIONS, table_id=table_id), key=lambda row: row.get("opened_at", ""))
    return next((row for row in reversed(rows) if active(row)), rows[-1] if rows else None)


def session_by_token(token, *, active_only=True):
    if not isinstance(token, str) or len(token) != 32:
        return None
    rows = records(SESSIONS, token=token)
    return next((row for row in rows if active(row) or not active_only), None)


def session_by_id(rid, session_id):
    row = Repo.get_by_id(SESSIONS, session_id)
    return row if row and row.get("rid") == rid else None


def session_orders(session):
    return records("market_orders", table_session=session["id"])


def pending_requests(session_id):
    return [row for row in records(REQUESTS, session_id=session_id) if row.get("status") == "Pendiente"]


def open_session(table, *, uid=None, party_size=1, name="", actor=None):
    try:
        party = int(party_size)
    except (TypeError, ValueError):
        raise ServiceError("Indica cuántas personas se sentarán.") from None
    if not 1 <= party <= int(table.get("capacity") or 1):
        raise ServiceError(f"La mesa admite hasta {table.get('capacity')} personas.")
    with document_transaction():
        locked = Repo.get_by_id(TABLES, table["id"], for_update=True)
        if not locked or not locked.get("active", True):
            raise ServiceError("La mesa ya no está disponible.")
        current = active_session(table["id"])
        if current:
            raise ServiceError("La mesa ya tiene una sesión de atención abierta.")
        last = latest_session(table["id"])
        if last and last.get("status") == "Finalizada" and not last.get("cleaned_at"):
            raise ServiceError("La mesa está pendiente de limpieza antes de una nueva atención.")
        flow = next((row for row in records("flow_settings", rid=locked["rid"])), None) or {}
        limit = int(flow.get("max_capacity") or 0)
        if limit:
            seated = sum(int(row.get("party_size") or 0)
                         for row in records(SESSIONS, rid=locked["rid"]) if active(row))
            if seated + party > limit:
                raise ServiceError("El aforo máximo del negocio ya no permite sentar a este grupo.")
        session = Repo.create(SESSIONS, {
            "rid": locked["rid"], "table_id": locked["id"], "token": uuid4().hex,
            "table_label": locked.get("label"), "floor": locked.get("floor"), "zone": locked.get("zone"),
            "uid": uid, "guest_name": _text(name, 80), "party_size": party,
            "status": "Abierta", "order_ids": [], "opened_at": now().isoformat(),
            "opened_by": actor or uid, "last_activity": now().isoformat(),
            "cleaned_at": None,
        })
        return session


def join_session(session, uid):
    if session.get("uid") in (None, uid):
        if session.get("uid") is None:
            return Repo.update(SESSIONS, session["id"], {"uid": uid})
        return session
    raise ServiceError("Esta mesa ya está vinculada a otra cuenta. Pide ayuda al personal.")


def close_session(session, *, paid, actor):
    with document_transaction():
        initial = Repo.get_by_id(SESSIONS, session["id"])
        if not initial:
            raise ServiceError("La sesión ya está cerrada.")
        # Same lock order as checkout: business first, then its table session.
        lock_business(initial["rid"])
        current = Repo.get_by_id(SESSIONS, session["id"], for_update=True)
        if not current or not active(current):
            raise ServiceError("La sesión ya está cerrada.")
        orders = session_orders(current)
        live = [o for o in orders if o.get("state") not in {"Entregado", "Cancelado"}]
        if live:
            raise ServiceError("Aún hay pedidos en preparación o sin servir en esta mesa.")
        total = order_total(orders)
        if total and not paid:
            raise ServiceError("Confirma el cobro antes de cerrar la mesa.")
        if total and any(o.get("method") == "Digital" and not o.get("paid") for o in orders):
            raise ServiceError("Hay un pago digital pendiente de confirmación.")
        for order in orders:
            if order.get("state") == "Entregado" and not order.get("paid"):
                Repo.update("market_orders", order["id"], {"paid": True})
        updated = Repo.update(SESSIONS, current["id"], {
            "status": "Finalizada", "closed_at": now().isoformat(), "last_activity": now().isoformat(),
            "total": total, "paid": bool(paid or not total), "closed_by": actor,
        })
        if current.get("uid"):
            from models.notification import NotificationModel
            NotificationModel.create_notification(
                current["uid"], "Gracias por tu visita",
                "Tu consumo quedó cerrado. Cuéntanos cómo estuvo la experiencia.",
                link=f"/mesa/{current['token']}",
            )
        return updated


def mark_cleaned(session, actor):
    with document_transaction():
        current = Repo.get_by_id(SESSIONS, session["id"], for_update=True)
        if not current or current.get("status") != "Finalizada":
            raise ServiceError("Solo se puede marcar una sesión finalizada.")
        return Repo.update(SESSIONS, current["id"], {
            "cleaned_at": now().isoformat(), "cleaned_by": actor,
        })


def request(session, kind):
    if kind not in {"Mozo", "Cuenta"}:
        raise ServiceError("Solicitud no reconocida.")
    with document_transaction():
        current = Repo.get_by_id(SESSIONS, session["id"], for_update=True)
        if not current or not active(current):
            raise ServiceError("La sesión de mesa ya está cerrada.")
        existing = next((row for row in records(REQUESTS, session_id=current["id"], kind=kind)
                         if row.get("status") == "Pendiente"), None)
        if existing:
            return existing
        row = Repo.create(REQUESTS, {"rid": current["rid"], "table_id": current["table_id"],
                                     "session_id": current["id"], "kind": kind, "status": "Pendiente",
                                     "at": now().isoformat()})
        Repo.update(SESSIONS, current["id"], {"last_activity": now().isoformat()})
        if kind == "Cuenta":
            Repo.update(SESSIONS, current["id"], {"status": "Cuenta"})
        _notify_staff(current["rid"], "Solicitud de mesa",
                      f"Mesa: {kind.lower()} solicitado en la sesión #{current['id']}.")
        return row


def resolve(request_id, rid, actor):
    with document_transaction():
        row = Repo.get_by_id(REQUESTS, request_id, for_update=True)
        if not row or row.get("rid") != rid:
            raise ServiceError("La solicitud ya no existe.")
        if row.get("status") != "Pendiente":
            return row
        return Repo.update(REQUESTS, request_id, {
            "status": "Atendida", "resolved_at": now().isoformat(), "resolved_by": actor,
        })


def set_split(session, people=None, shares=None):
    with document_transaction():
        current = Repo.get_by_id(SESSIONS, session["id"], for_update=True)
        if not current or not active(current):
            raise ServiceError("La sesión ya está cerrada.")
        orders = session_orders(current)
        total = order_total(orders)
        if not total:
            raise ServiceError("Todavía no hay consumo para dividir.")
        if shares is not None:
            amounts = validate_shares(shares, total)
            mode = "custom"
        else:
            amounts = split_equal(total, people)
            mode = "equal"
        split = {"mode": mode, "people": len(amounts), "total": total,
                 "shares": [{"n": index + 1, "amount": amount, "paid": False}
                            for index, amount in enumerate(amounts)],
                 "updated_at": now().isoformat()}
        return Repo.update(SESSIONS, current["id"], {"split": split})


def pay_share(session, number):
    with document_transaction():
        current = Repo.get_by_id(SESSIONS, session["id"], for_update=True)
        split = (current or {}).get("split") or {}
        try:
            index = int(number) - 1
            share = split["shares"][index]
        except (KeyError, IndexError, TypeError, ValueError):
            raise ServiceError("Esa parte de la cuenta no existe.") from None
        share["paid"] = True
        split["shares"][index] = share
        split["updated_at"] = now().isoformat()
        status = "Pago" if all(s.get("paid") for s in split["shares"]) else current["status"]
        return Repo.update(SESSIONS, current["id"], {"split": split, "status": status})


def table_detail(rid):
    """Estado operativo de cada mesa, sin inventar ocupación por escaneos."""
    all_rows = tables(rid, active_only=False)
    sessions = all_sessions(rid)
    requests = [row for row in records(REQUESTS, rid=rid)]
    result = []
    for table in all_rows:
        if not table.get("active", True):
            continue
        session = next((s for s in sessions if s.get("table_id") == table["id"] and active(s)), None)
        last = next((s for s in reversed(sessions)
                     if s.get("table_id") == table["id"] and s.get("status") == "Finalizada"), None)
        orders = session_orders(session) if session else []
        pending = [r for r in requests if r.get("session_id") == (session or {}).get("id")
                   and r.get("status") == "Pendiente"]
        state = table_state(session, orders, pending,
                            cleaned=bool(session or (last or {}).get("cleaned_at")))
        if not session and last and not last.get("cleaned_at"):
            state = "Limpieza"
        result.append({"table": table, "session": session, "orders": orders,
                       "requests": pending, "state": state, "total": order_total(orders),
                       "last": last})
    return result


def snapshot(rid, waiting=0):
    sessions = all_sessions(rid)
    latest = {}
    for row in sessions:
        latest[row.get("table_id")] = row
    blocked = {table_id for table_id, row in latest.items()
               if row.get("status") == "Finalizada" and not row.get("cleaned_at")}
    return occupancy_snapshot(tables(rid), [s for s in sessions if active(s)],
                              waiting=waiting, blocked=blocked)


def _notify_staff(rid, title, message):
    from models.notification import NotificationModel
    restaurant = Repo.get_by_id("restaurants", rid) or {}
    recipients = set()
    if restaurant.get("owner_id"):
        recipients.add(restaurant["owner_id"])
    recipients.update((kitchen(rid) or {}).get("team") or [])
    for uid in recipients:
        NotificationModel.create_notification(uid, title, message, link=f"/salon/{rid}")


def service_enabled(restaurant):
    if not restaurant:
        return False
    return "Local" in ((kitchen(restaurant["id"]) or {}).get("channels") or [])