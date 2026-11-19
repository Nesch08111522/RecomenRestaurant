"""SmartResto Flow: aforo, cola virtual y rotación de mesas.

La cola no promete tiempos exactos. La estimación usa sesiones cerradas
reales; sin historial suficiente se apoya en la duración declarada por el
negocio y se muestra esa base al cliente y al personal.
"""
from __future__ import annotations

from datetime import datetime, time
from statistics import median
from uuid import uuid4

from database.repository import PostgresDocumentRepository as Repo, document_transaction
from logic.market import now
from logic.salon import ServiceError, active, wait_estimate
from models.market import kitchen, records
from models.salon import all_sessions, open_session, snapshot, tables

QUEUE = "flow_queue"
SETTINGS = "flow_settings"
OPEN_STATUSES = {"Esperando", "Llamado"}


def settings(rid):
    row = next(iter(records(SETTINGS, rid=rid)), None)
    base = {"rid": rid, "accepting": True, "max_capacity": 0, "note": ""}
    return {**base, **row} if row else base


def save_settings(rid, *, accepting, max_capacity, note=""):
    try:
        max_capacity = int(max_capacity or 0)
    except (TypeError, ValueError):
        raise ServiceError("Revisa el aforo máximo.") from None
    if not 0 <= max_capacity <= 5000:
        raise ServiceError("El aforo máximo debe estar entre 0 y 5000.")
    with document_transaction() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                     (f"flow-queue:{rid}",))
        current = next(iter(records(SETTINGS, rid=rid)), None)
        payload = {"rid": rid, "accepting": accepting, "max_capacity": max_capacity,
                   "note": " ".join(str(note or "").split())[:200], "updated_at": now().isoformat()}
        if current:
            return Repo.update(SETTINGS, current["id"], payload)
        return Repo.create(SETTINGS, payload)


def _today_queue(rid):
    today = now().date().isoformat()
    return sorted((row for row in records(QUEUE, rid=rid) if row.get("day") == today),
                  key=lambda row: row.get("created_at", ""))


def join(rid, name, party_size, uid=None, note=""):
    config = settings(rid)
    if not config.get("accepting"):
        raise ServiceError("El negocio no está recibiendo turnos en este momento.")
    try:
        party = int(party_size)
    except (TypeError, ValueError):
        raise ServiceError("Indica cuántas personas esperan.") from None
    if not 1 <= party <= 40:
        raise ServiceError("El grupo debe tener entre 1 y 40 personas.")
    clean = " ".join(str(name or "").split())[:60]
    if len(clean) < 2:
        raise ServiceError("Escribe un nombre para identificar tu turno.")
    with document_transaction() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
                     (f"flow-queue:{rid}",))
        if not settings(rid).get("accepting"):
            raise ServiceError("El negocio no está recibiendo turnos en este momento.")
        today = _today_queue(rid)
        if uid and any(row.get("uid") == uid and row.get("status") in OPEN_STATUSES for row in today):
            existing = next(row for row in today if row.get("uid") == uid and row.get("status") in OPEN_STATUSES)
            return existing
        code = f"T-{len(today) + 1:03d}"
        return Repo.create(QUEUE, {
            "rid": rid, "code": code, "name": clean, "party_size": party, "uid": uid,
            "status": "Esperando", "created_at": now().isoformat(), "day": now().date().isoformat(),
            "note": " ".join(str(note or "").split())[:160],
        })


def queue(rid):
    return [row for row in _today_queue(rid) if row.get("status") in OPEN_STATUSES]


def history(rid, limit=200):
    return _today_queue(rid)[-limit:]


def entry(rid, qid):
    row = Repo.get_by_id(QUEUE, qid, for_update=True)
    return row if row and row.get("rid") == rid else None


def status(rid, ids):
    waiting = queue(rid)
    config = settings(rid)
    seated = [s for s in all_sessions(rid) if active(s)]
    rows = []
    for row in waiting:
        rows.append({**row, "position": waiting.index(row) + 1,
                     "estimate": estimate(rid, row["party_size"], position=waiting.index(row) + 1)})
    mine = [row for row in rows if row["id"] in ids]
    return {"mine": mine, "waiting": len(waiting), "seated": sum(s.get("party_size") or 0 for s in seated),
            "accepting": config.get("accepting", True),
            "ahead": [{"position": row["position"], "party_size": row["party_size"], "status": row["status"]}
                      for row in rows]}


def _durations(rid, days=30):
    cutoff = now().timestamp() - days * 86400
    values = []
    for session in all_sessions(rid):
        if session.get("status") != "Finalizada" or not session.get("closed_at"):
            continue
        try:
            closed = datetime.fromisoformat(session["closed_at"])
            opened = datetime.fromisoformat(session["opened_at"])
        except (KeyError, ValueError):
            continue
        if closed.timestamp() < cutoff:
            continue
        minutes = (closed - opened).total_seconds() / 60
        if 5 <= minutes <= 600:
            values.append(int(minutes))
    return values


def expected_minutes(rid):
    """Duración esperada de una mesa: mediana real o valor declarado."""
    durations = _durations(rid)
    if len(durations) >= 3:
        return {"minutes": int(median(durations)), "basis": f"historial de {len(durations)} sesiones"}
    declared = int((kitchen(rid) or {}).get("table_minutes") or 45)
    return {"minutes": declared, "basis": "duración declarada por el negocio"}


def estimate(rid, party_size, position=0):
    rows = tables(rid)
    suitable = [t for t in rows if int(t.get("capacity") or 0) >= int(party_size)]
    sessions = all_sessions(rid)
    busy = {s.get("table_id") for s in sessions if active(s)}
    latest = {}
    for session in sessions:
        latest[session.get("table_id")] = session
    cleaning = {table_id for table_id, row in latest.items()
                if row.get("status") == "Finalizada" and not row.get("cleaned_at")}
    free = [t for t in suitable if t["id"] not in busy and t["id"] not in cleaning]
    ahead = max(0, int(position) - 1)
    durations = _durations(rid)
    declared = int((kitchen(rid) or {}).get("table_minutes") or 45)
    return wait_estimate(durations, len(free), len(suitable), ahead, declared)


def call_next(rid, qid):
    with document_transaction():
        row = entry(rid, qid)
        if not row or row.get("status") != "Esperando":
            raise ServiceError("Ese turno ya no está esperando.")
        updated = Repo.update(QUEUE, qid, {"status": "Llamado", "called_at": now().isoformat()})
        _notify(row.get("uid"), "Tu mesa está casi lista",
                f"Turno {row['code']}: acércate a la entrada de { _business_name(rid) }.")
        return updated


def cancel(rid, qid, *, reason="Cancelado por el cliente"):
    with document_transaction():
        row = entry(rid, qid)
        if not row or row.get("status") not in OPEN_STATUSES:
            raise ServiceError("El turno ya no está activo.")
        return Repo.update(QUEUE, qid, {"status": "Cancelado", "cancelled_at": now().isoformat(),
                                        "reason": reason[:160]})


def no_show(rid, qid):
    return cancel(rid, qid, reason="No se presentó")


def seat(rid, qid, table_id):
    with document_transaction():
        row = entry(rid, qid)
        if not row or row.get("status") not in OPEN_STATUSES:
            raise ServiceError("El turno ya no está activo.")
        table = next((t for t in tables(rid) if t["id"] == int(table_id)), None)
        if not table:
            raise ServiceError("Selecciona una mesa del salón.")
        if int(table.get("capacity") or 0) < int(row["party_size"]):
            raise ServiceError("La mesa no tiene capacidad para ese grupo.")
        session = open_session(table, uid=row.get("uid"), party_size=row["party_size"],
                               name=row.get("name"), actor=None)
        Repo.update(QUEUE, qid, {"status": "Sentado", "seated_at": now().isoformat(),
                                 "session_id": session["id"], "table_id": table["id"]})
        _notify(row.get("uid"), "Mesa asignada",
                f"Turno {row['code']}: te esperamos en la mesa {table['label']}.")
        return session


def _notify(uid, title, message):
    if not uid:
        return
    from models.notification import NotificationModel
    from models.user import UserModel
    user = UserModel.get_by_id(uid) or {}
    prefs = (user.get("profile") or {}).get("notification_preferences") or {}
    if prefs.get("waitlist", True):
        NotificationModel.create_notification(uid, title, message, link="/puntos")


def _business_name(rid):
    return (Repo.get_by_id("restaurants", rid) or {}).get("name", "el negocio")


def demand_pattern(rid, days=30):
    """Patrón descriptivo de llegadas por día de semana y hora."""
    cutoff = now().timestamp() - days * 86400
    buckets = {}
    for row in records(QUEUE, rid=rid):
        try:
            at = datetime.fromisoformat(row["created_at"])
        except (KeyError, ValueError):
            continue
        if at.timestamp() < cutoff:
            continue
        key = (at.weekday(), at.hour)
        buckets.setdefault(key, []).append(int(row.get("party_size") or 0))
    if not buckets:
        return []
    rows = [{"weekday": key[0], "hour": key[1], "parties": len(values),
             "people": sum(values), "average": round(sum(values) / len(values), 1)}
            for key, values in buckets.items()]
    return sorted(rows, key=lambda row: (row["weekday"], row["hour"]))