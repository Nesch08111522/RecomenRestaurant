"""Commercial dashboard indicators. Money values are integer PEN cents."""
from collections import Counter
from datetime import date, timedelta

from database.repository import document_transaction
from logic.market import available, now
from models.market import indicators


def reporting_period(args, today):
    days = args.get("days", "30")
    if days not in {"7", "30", "90"}:
        raise ValueError("Selecciona un período de 7, 30 o 90 días.")
    try:
        end = date.fromisoformat(args["end"]) if args.get("end") else today
        start = date.fromisoformat(args["start"]) if args.get("start") else end - timedelta(days=int(days) - 1)
    except ValueError:
        raise ValueError("Usa fechas válidas para el informe.") from None
    if end > today or start > end or (end - start).days >= 366:
        raise ValueError("Elige un intervalo pasado o actual de hasta 366 días.")
    return start, end


def scoped_records(collection, ids):
    """Filter in PostgreSQL before commercial data crosses the tenant boundary."""
    if not ids:
        return []
    with document_transaction() as conn:
        rows = conn.execute(
            "SELECT payload - 'photo' - 'destination' - 'checkout' AS payload FROM public.app_records "
            "WHERE collection=%s AND payload->>'rid' = ANY(%s) ORDER BY id",
            (collection, [str(rid) for rid in ids]),
        )
        return [row["payload"] for row in rows]


def registrations(collection, start, end, ids=None):
    where = " AND id = ANY(%s)" if ids is not None else ""
    args = [collection, start, end]
    if ids is not None:
        args.append(ids)
    with document_transaction() as conn:
        rows = conn.execute(
            "SELECT (created_at AT TIME ZONE 'America/Lima')::date AS day, count(*) AS n "
            "FROM public.app_records WHERE collection=%s AND "
            "(created_at AT TIME ZONE 'America/Lima')::date BETWEEN %s AND %s" + where + " GROUP BY day",
            args)
        return {row["day"].isoformat(): row["n"] for row in rows}


def order_report(orders, start, end, today):
    first, last = start.isoformat(), end.isoformat()
    period = [o for o in orders if first <= o.get("created", "")[:10] <= last]
    paid = [o for o in period if o["state"] == "Entregado" and o.get("paid") and not o.get("refunded")]
    perf = indicators(period)
    products = Counter()
    for order in paid:
        for line in order["lines"]:
            products[line["name"]] += line["qty"]
    costs = sum(line["cost"] * line["qty"] for o in paid
                if all(line["cost"] is not None for line in o["lines"]) for line in o["lines"])
    settled_today = [o for o in orders if o["state"] == "Entregado" and o.get("paid") and not o.get("refunded")
                     and any(h.get("state") == "Entregado" and h.get("at", "")[:10] == today.isoformat()
                             for h in o.get("history", []))]
    return dict(perf, orders=period, count=len(period), costs=costs, products=products.most_common(6),
                today=sum(o["total"] for o in settled_today),
                completed=sum(o["state"] == "Entregado" for o in period),
                states=Counter(o["state"] for o in orders),
                activity=Counter(o["created"][:10] for o in period),
                active_clients=len({o["uid"] for o in period}))


def timeline(counts, start, end):
    span = (end - start).days + 1
    stride = max(1, (span + 9) // 10)
    bars = []
    for offset in range(0, span, stride):
        first = start + timedelta(days=offset)
        last = min(first + timedelta(days=stride - 1), end)
        amount = sum(counts.get((first + timedelta(days=i)).isoformat(), 0) for i in range((last-first).days + 1))
        bars.append((first.strftime("%d/%m") if first == last else f"{first:%d/%m}–{last:%d/%m}", amount))
    return bars


def inventories(business, today, threshold):
    from models.market import kitchen
    stock = kitchen(business["id"])["pantry"]
    critical = [name for name, item in stock.items() if item["quantity"] <= 0 or item["expires"] < today]
    low = [o for o in scoped_records("market_offers", [business["id"]])
           if o["day"] >= today and o["ends"] > now().isoformat() and not o.get("paused")
           and available(o, stock, o["day"]) <= threshold]
    return critical, low
