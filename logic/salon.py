"""Reglas del salón: sesiones de mesa, estados, división de cuenta y espera.

Ninguna función de este módulo escribe datos. Los cálculos de ocupación y
espera se basan únicamente en sesiones, mesas y cola realmente registradas;
cuando no hay historial se usa la duración declarada por el negocio y se
informa de esa base, sin presentarla como una predicción entrenada.
"""
from __future__ import annotations

from math import ceil
from statistics import median

from logic.market import MarketError

ACTIVE_STATES = frozenset({"Abierta", "Pedido", "Preparando", "Servido", "Cuenta", "Pago"})
CLOSED_STATES = frozenset({"Finalizada", "Cancelada"})
ORDER_ACTIVE = frozenset({"Recibido", "Confirmado", "Preparando", "Listo"})
TABLE_STATES = (
    "Disponible", "Ocupada", "Pedido enviado", "En preparación", "Servido",
    "Solicita atención", "Solicita cuenta", "Pendiente de pago", "Limpieza",
)
SPLIT_LIMIT = 30


class ServiceError(MarketError):
    """Mensaje apto para el comensal o el personal del salón."""


def active(session):
    return bool(session) and session.get("status") in ACTIVE_STATES


def table_state(session, orders=(), requests=(), cleaned=True):
    """Deriva el estado visible de una mesa a partir de hechos registrados.

    Un QR escaneado no abre una sesión: solo una sesión confirmada ocupa la
    mesa. Las solicitudes pendientes tienen prioridad sobre el estado de cocina.
    """
    pending = {r.get("kind") for r in requests if r.get("status") == "Pendiente"}
    if session and session.get("status") in CLOSED_STATES:
        if session.get("status") == "Finalizada" and not cleaned:
            return "Limpieza"
        return "Disponible"
    if session and active(session):
        if "Mozo" in pending:
            return "Solicita atención"
        if "Cuenta" in pending or session.get("status") == "Cuenta":
            return "Solicita cuenta"
        if session.get("status") == "Pago":
            return "Pendiente de pago"
        states = {o.get("state") for o in orders}
        if "Preparando" in states:
            return "En preparación"
        if states & {"Recibido", "Confirmado"}:
            return "Pedido enviado"
        if states & {"Listo", "Entregado"}:
            return "Servido"
        return "Ocupada"
    return "Disponible"


def order_total(orders):
    return sum(o.get("total", 0) for o in orders if o.get("state") != "Cancelado")


def split_equal(total, people):
    """Divide céntimos sin perder ni inventar un solo céntimo."""
    people = int(people)
    if not 2 <= people <= SPLIT_LIMIT:
        raise ServiceError("Divide la cuenta entre 2 y 30 personas.")
    if total < 0:
        raise ServiceError("El total de la cuenta no es válido.")
    base, extra = divmod(int(total), people)
    return [base + 1 if index < extra else base for index in range(people)]


def validate_shares(shares, total):
    if not isinstance(shares, list) or not 2 <= len(shares) <= SPLIT_LIMIT:
        raise ServiceError("Indica entre 2 y 30 partes.")
    try:
        values = [int(value) for value in shares]
    except (TypeError, ValueError):
        raise ServiceError("Cada parte debe ser un importe válido.") from None
    if any(value < 0 for value in values) or sum(values) != int(total):
        raise ServiceError("Las partes deben sumar exactamente el total de la cuenta.")
    return values


def wait_estimate(durations, free_tables, suitable_tables, ahead, declared_minutes):
    """Estimación descriptiva, no una garantía ni un modelo entrenado.

    durations: duraciones reales de sesiones cerradas (minutos).
    ahead: turnos por delante que caben en mesas de capacidad suficiente.
    declared_minutes: duración configurada por el negocio, usada sin historial.
    """
    samples = len(durations)
    declared = max(1, int(declared_minutes or 45))
    if suitable_tables <= 0:
        return {"minutes": None, "low": None, "high": None, "basis": "sin mesas para ese tamaño",
                "samples": samples}
    if free_tables > ahead:
        return {"minutes": 0, "low": 0, "high": 0, "basis": "mesa disponible ahora", "samples": samples}
    cycle = int(median(durations)) if samples >= 3 else declared
    rounds = ceil((ahead + 1 - free_tables) / max(1, suitable_tables))
    point = max(1, rounds * cycle)
    if samples >= 3:
        deviations = [abs(value - cycle) for value in durations]
        spread = max(5, int(median(deviations)))
        basis = f"historial de {samples} sesiones cerradas"
    else:
        spread = max(5, cycle // 3)
        basis = "duración declarada por el negocio; historial insuficiente"
    return {"minutes": point, "low": max(1, point - spread), "high": point + spread,
            "basis": basis, "samples": samples}


def occupancy_snapshot(tables, sessions, requests=(), waiting=0, blocked=()):
    blocked = set(blocked or ())
    seats = sum(int(t.get("capacity") or 0) for t in tables if t.get("active", True))
    current = [s for s in sessions if active(s)]
    occupied = sum(int(s.get("party_size") or 0) for s in current)
    by_floor, by_zone = {}, {}
    for table in tables:
        if not table.get("active", True):
            continue
        floor = table.get("floor") or "Planta principal"
        zone = table.get("zone") or "General"
        by_floor.setdefault(floor, {"seats": 0, "occupied": 0, "tables": 0, "busy": 0, "free": 0})
        by_zone.setdefault(zone, {"seats": 0, "occupied": 0, "tables": 0, "busy": 0, "free": 0})
        for bucket in (by_floor[floor], by_zone[zone]):
            bucket["seats"] += int(table.get("capacity") or 0)
            bucket["tables"] += 1
        session = next((s for s in current if s.get("table_id") == table.get("id")), None)
        if session:
            for bucket in (by_floor[floor], by_zone[zone]):
                bucket["occupied"] += int(session.get("party_size") or 0)
                bucket["busy"] += 1
        elif table.get("id") not in blocked:
            for bucket in (by_floor[floor], by_zone[zone]):
                bucket["free"] += 1
    return {
        "seats": seats, "occupied": occupied, "waiting": int(waiting or 0),
        "available_tables": sum(1 for t in tables if t.get("active", True)
                                and t.get("id") not in blocked
                                and not any(s.get("table_id") == t.get("id") for s in current)),
        "busy_tables": len(current), "tables": len([t for t in tables if t.get("active", True)]),
        "cleaning_tables": len([t for t in tables if t.get("id") in blocked]),
        "occupancy": round(occupied * 100 / seats, 1) if seats else 0,
        "by_floor": by_floor, "by_zone": by_zone,
    }


def public_session(session, orders=(), requests=(), split=None):
    """Vista mínima que puede mostrarse al comensal, sin datos internos."""
    if not session:
        return None
    return {
        "id": session["id"], "status": session.get("status"), "party_size": session.get("party_size"),
        "opened_at": session.get("opened_at"), "total": order_total(orders),
        "state": table_state(session, orders, requests, cleaned=bool(session.get("cleaned_at"))),
        "orders": [{"id": o["id"], "state": o.get("state"), "total": o.get("total", 0),
                    "lines": [{"name": l.get("name"), "qty": l.get("qty")} for l in o.get("lines", [])]}
                   for o in orders if o.get("state") != "Cancelado"],
        "requests": [{"id": r["id"], "kind": r.get("kind"), "status": r.get("status")}
                     for r in requests],
        "split": split,
    }