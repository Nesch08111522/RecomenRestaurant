"""Fidelización SmartResto: puntos, visitas verificadas, niveles e insignias.

La billetera se calcula a partir de hechos registrados (pedidos entregados y
pagados, sesiones de mesa cerradas y bonos explícitos). No se conceden puntos
por una compra cancelada, reembolsada o no pagada, y cada canje descuenta los
puntos que el pedido realmente utilizó.
"""
from __future__ import annotations

from collections import Counter, defaultdict

from database.repository import PostgresDocumentRepository as Repo, document_transaction
from logic.market import now
from models.market import records
from models.restaurant import RestaurantModel
from models.review import ReviewModel
from models.user import UserModel

BONUSES = "loyalty_bonuses"
POINTS_PER_10_SOLES = 1
VISIT_POINTS = 10
BIRTHDAY_POINTS = 50
LEVELS = (
    {"name": "Bronce", "from": 0},
    {"name": "Plata", "from": 200},
    {"name": "Oro", "from": 500},
    {"name": "Diamante", "from": 1000},
)
BADGES = {
    "first_visit": "Primera visita",
    "explorer": "Explorador de sabores",
    "frequent": "Cliente frecuente",
    "reviewer": "Voz verificada",
    "birthday": "Cumpleaños SmartResto",
    "ten_orders": "Diez compras",
}


def level_for(points):
    current = LEVELS[0]
    for level in LEVELS:
        if points >= level["from"]:
            current = level
    index = LEVELS.index(current)
    following = LEVELS[index + 1] if index + 1 < len(LEVELS) else None
    progress = None
    if following:
        span = following["from"] - current["from"]
        progress = round((points - current["from"]) * 100 / span, 1) if span else 100
    return {"name": current["name"], "from": current["from"],
            "next": following["name"] if following else None,
            "next_from": following["from"] if following else None,
            "progress": progress}


def _paid(order):
    return (order.get("state") == "Entregado" and order.get("paid")
            and not order.get("refunded"))


def _sessions(uid=None):
    rows = Repo.all("table_sessions")
    if uid is not None:
        rows = [row for row in rows if row.get("uid") == uid]
    return [row for row in rows if row.get("status") == "Finalizada" and row.get("paid")]


def _session_orders(session):
    return records("market_orders", table_session=session["id"])


def events(uid):
    rows = []
    orders = [o for o in records("market_orders", uid=uid) if o.get("state") != "Cancelado"]
    for order in orders:
        if _paid(order):
            points = int(order.get("total", 0)) // 1000 * POINTS_PER_10_SOLES
            if points:
                rows.append({"kind": "Compra", "points": points, "rid": order["rid"],
                             "business": order.get("business", ""), "ref": f"pedido:{order['id']}",
                             "at": order.get("created") or order.get("slot"), "order_id": order["id"]})
            if order.get("reward_points"):
                rows.append({"kind": "Canje", "points": -int(order["reward_points"]), "rid": order["rid"],
                             "business": order.get("business", ""), "ref": f"canje:{order['id']}",
                             "at": order.get("created") or order.get("slot"), "order_id": order["id"]})
        elif order.get("refunded") and order.get("state") == "Entregado":
            points = int(order.get("total", 0)) // 1000 * POINTS_PER_10_SOLES
            if points:
                rows.append({"kind": "Compra", "points": points, "rid": order["rid"],
                             "business": order.get("business", ""), "ref": f"pedido:{order['id']}",
                             "at": order.get("created") or order.get("slot"), "order_id": order["id"]})
                rows.append({"kind": "Reversión por reembolso", "points": -points, "rid": order["rid"],
                             "business": order.get("business", ""), "ref": f"reembolso:{order['id']}",
                             "at": order.get("created") or order.get("slot"), "order_id": order["id"]})
    for session in _sessions(uid):
        orders = _session_orders(session)
        if not any(_paid(order) for order in orders):
            continue
        rows.append({"kind": "Visita verificada", "points": VISIT_POINTS, "rid": session["rid"],
                     "business": (Repo.get_by_id("restaurants", session["rid"]) or {}).get("name", ""),
                     "ref": f"visita:{session['id']}", "at": session.get("closed_at") or session.get("opened_at"),
                     "session_id": session["id"]})
    for bonus in records(BONUSES, uid=uid):
        rows.append({"kind": bonus.get("kind", "Bono"), "points": int(bonus.get("points", 0)),
                     "rid": bonus.get("rid"), "business": bonus.get("business", "SmartResto"),
                     "ref": f"bono:{bonus['id']}", "at": bonus.get("at")})
    return sorted(rows, key=lambda row: row.get("at") or "", reverse=True)


def wallet(uid):
    rows = events(uid)
    balance = sum(row["points"] for row in rows)
    earned = sum(row["points"] for row in rows if row["points"] > 0)
    visits = _sessions(uid)
    businesses = {visit["rid"] for visit in visits}
    dishes = Counter()
    for visit in visits:
        for order in _session_orders(visit):
            if _paid(order):
                for line in order.get("lines", []):
                    dishes[line.get("name", "")] += int(line.get("qty") or 0)
    reviews = [r for r in ReviewModel.get_by_user(uid) if r.get("verified_purchase")]
    badges = []
    if visits:
        badges.append(BADGES["first_visit"])
    if len(businesses) >= 3:
        badges.append(BADGES["explorer"])
    per_business = Counter(visit["rid"] for visit in visits)
    if per_business and max(per_business.values()) >= 5:
        badges.append(BADGES["frequent"])
    if len(reviews) >= 3:
        badges.append(BADGES["reviewer"])
    if any(row.get("kind") == "Cumpleaños" for row in records(BONUSES, uid=uid)):
        badges.append(BADGES["birthday"])
    if sum(1 for order in records("market_orders", uid=uid) if _paid(order)) >= 10:
        badges.append(BADGES["ten_orders"])
    level = level_for(earned)
    return {"balance": balance, "earned": earned, "level": level, "events": rows[:50],
            "visits": visits, "businesses": len(businesses), "badges": badges,
            "dishes": dishes.most_common(10), "review_count": len(reviews)}


def visits(uid):
    rows = []
    for session in _sessions(uid):
        orders = [o for o in _session_orders(session) if _paid(o)]
        rows.append({
            "session_id": session["id"], "rid": session["rid"],
            "business": (Repo.get_by_id("restaurants", session["rid"]) or {}).get("name", ""),
            "at": session.get("closed_at") or session.get("opened_at"),
            "people": session.get("party_size"), "total": sum(o.get("total", 0) for o in orders),
            "dishes": [(line.get("name"), line.get("qty")) for order in orders for line in order.get("lines", [])],
            "reviewed": bool(session.get("review")),
        })
    return sorted(rows, key=lambda row: row["at"] or "", reverse=True)


def birthday_claim(uid):
    user = UserModel.get_by_id(uid) or {}
    birthday = str((user.get("profile") or {}).get("birthday") or "")[:10]
    if len(birthday) < 10:
        raise ValueError("Registra tu fecha de cumpleaños en el perfil para reclamar el beneficio.")
    today = now().date()
    try:
        month, day = int(birthday[5:7]), int(birthday[8:10])
    except ValueError:
        raise ValueError("La fecha de cumpleaños registrada no es válida.") from None
    if (month, day) != (today.month, today.day):
        raise ValueError("El beneficio de cumpleaños solo se puede reclamar el día de tu cumpleaños.")
    year = today.year
    if any(row.get("kind") == "Cumpleaños" and str(row.get("at", ""))[:4] == str(year)
           for row in records(BONUSES, uid=uid)):
        raise ValueError("Ya reclamaste el beneficio de este año.")
    with document_transaction():
        return Repo.create(BONUSES, {"uid": uid, "kind": "Cumpleaños", "points": BIRTHDAY_POINTS,
                                     "at": now().isoformat(), "business": "SmartResto",
                                     "note": f"Beneficio anual {year}"})


def save_preferences(uid, *, marketing, visits_visible, birthday_visible):
    user = UserModel.get_by_id(uid) or {}
    profile = dict(user.get("profile") or {})
    profile["loyalty"] = {"marketing": bool(marketing), "visits_visible": bool(visits_visible),
                          "birthday_visible": bool(birthday_visible)}
    UserModel.update(uid, {"profile": profile})


def review_session(session, rating, comment, photos=None):
    if session.get("status") != "Finalizada" or not session.get("paid"):
        raise ValueError("Solo puedes valorar una visita cerrada y pagada.")
    if session.get("review"):
        raise ValueError("Esta visita ya tiene una valoración.")
    orders = [o for o in _session_orders(session) if _paid(o)]
    if not orders:
        raise ValueError("La visita no registra un consumo pagado.")
    with document_transaction():
        review = ReviewModel.add_review(session["uid"], session["rid"], rating, comment)
        ReviewModel.update(review["id"], {"session_id": session["id"], "verified_purchase": True,
                                          "visit": True, "photos": list(photos or [])[:4]})
        Repo.update("table_sessions", session["id"], {"review": review["id"]})
        RestaurantModel.update(session["rid"], {"rating": ReviewModel.get_rating_stats(session["rid"])["average"]})
        return ReviewModel.get_by_id(review["id"])


def owner_customers(rid, days=60):
    """Clientes nuevos, frecuentes e inactivos a partir de compras reales."""
    cutoff = now().timestamp() - days * 86400
    orders = [o for o in records("market_orders", rid=rid) if _paid(o)]
    stats = {}
    for order in orders:
        uid = order.get("uid")
        if uid in (None, ""):
            continue
        item = stats.setdefault(uid, {"orders": 0, "spent": 0, "first": None, "last": None})
        item["orders"] += 1
        item["spent"] += int(order.get("total", 0))
        at = order.get("created") or order.get("slot") or ""
        item["first"] = min(filter(None, [item["first"], at])) if item["first"] else at
        item["last"] = max(filter(None, [item["last"], at])) if item["last"] else at
    rows = []
    for uid, item in stats.items():
        user = UserModel.get_by_id(uid) or {}
        name = (user.get("profile") or {}).get("name") or f"Cliente #{uid}"
        active = bool(item["last"]) and _timestamp(item["last"]) >= cutoff
        rows.append({"uid": uid, "name": name, **item, "active": active,
                     "frequent": item["orders"] >= 3})
    dishes = Counter()
    for order in orders:
        for line in order.get("lines", []):
            dishes[line.get("name", "")] += int(line.get("qty") or 0)
    return {"customers": sorted(rows, key=lambda row: row["last"] or "", reverse=True),
            "new": sum(1 for row in rows if row["first"] and _timestamp(row["first"]) >= cutoff),
            "frequent": sum(1 for row in rows if row["frequent"]),
            "inactive": sum(1 for row in rows if not row["active"]),
            "dishes": dishes.most_common(10)}


def _timestamp(value):
    from datetime import datetime
    try:
        return datetime.fromisoformat(str(value)).timestamp()
    except ValueError:
        return 0