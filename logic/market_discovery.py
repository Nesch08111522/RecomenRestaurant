"""Explainable ranking of real, available dishes."""
import re
from collections import Counter
from datetime import timedelta

from logic.market import CHANNELS, DIETS, compatible, key, money, now, words


def discover(rows, args, profile, orders):
    query = key(args.get("q", ""))[:300]
    amount = re.search(r"(?:s/\.?\s*|hasta\s+)(\d+(?:[.,]\d{1,2})?)", query)
    budget = args.get("budget") or (amount[1].replace(",", ".") if amount else profile.get("budget", ""))
    ceiling = money(budget) if budget else None
    if profile.get("daily"):
        total_limit = money(profile["daily"])
        spent = Counter()
        for order in orders:
            if order.get("state") != "Cancelado" and not order.get("refunded") and order.get("day"):
                spent[order["day"]] += order["total"]
    else:
        total_limit, spent = None, {}
    if amount:
        stated = money(amount[1].replace(",", "."))
        ceiling = min(stated, ceiling) if ceiling is not None else stated
        budget = str(ceiling / 100)
    channel = args.get("channel") or next((c for c in CHANNELS if key(c) in query), "")
    if not channel and "recoger" in query:
        channel = "Recojo"
    channel = channel or profile.get("channel", "")
    zone = key(args.get("zone", profile.get("zone", "")))
    avoid = sorted(set(profile.get("avoid", [])) | set(words(args.get("avoid"))))
    avoid += re.findall(r"\bsin\s+([a-z]+)", query)
    deadline = re.search(r"(\d{1,3})\s*minutos?", query)
    latest = now() + timedelta(minutes=int(deadline[1])) if deadline else None
    likes = profile.get("likes", [])
    diets = set(profile.get("diets", []))
    diets.update(d for d in DIETS if key(d) in query or d == args.get("diet"))
    previous = Counter(l["dish_id"] for o in orders if o["state"] == "Entregado" for l in o["lines"])
    day = args.get("day")
    tokens = {t for t in re.findall(r"[a-z]{3,}", query) if t not in {
        "tengo", "quiero", "algo", "para", "con", "sin", "hasta", "cerca", "recoger", "soles", "menos", "que", "por"}}
    matches = []
    for row in rows:
        if total_limit is not None and row["price"] + spent.get(row["day"], 0) > total_limit:
            continue
        if args.get("negocio") and str(row["rid"]) != args.get("negocio"):
            continue
        if latest and (row["day"] != latest.date().isoformat() or row["lead"] > int(deadline[1])):
            continue
        if ceiling is not None and row["price"] > ceiling or channel and channel not in row["channels"]:
            continue
        if day and day != row["day"] or args.get("rescue") and not row["saving"]:
            continue
        if zone and zone not in [key(z) for z in [row["district"], *row["zones"]]]:
            continue
        if not compatible(row, avoid):
            continue
        if not diets.issubset(row.get("diets", [])):
            continue
        terms = key(" ".join([row["name"], row["business"], row["occasion"], row["kind"], row["district"], row.get("category", ""), *row.get("tags", []), *row["recipe"]]))
        if any(args.get(field) and key(args[field]) != key(row.get(field, "")) for field in ("category", "occasion")):
            continue
        hits = sum(t in terms for t in tokens)
        if tokens and not hits and not (amount or channel or deadline or avoid or diets):
            continue
        reasons = [f"{row['available']} porciones para el {row['day']}"]
        if ceiling is not None:
            reasons.append("dentro de tu presupuesto")
        if channel:
            reasons.append(channel.lower() + " disponible")
        if previous[row["dish_id"]]:
            reasons.append("ya lo compraste")
        if any(l in terms for l in likes):
            reasons.append("coincide con tus gustos")
        score = 3 * hits + sum(l in terms for l in likes) + min(previous[row["dish_id"]], 2)
        matches.append({**row, "score": score, "why": " · ".join(reasons)})
    matches.sort(key=lambda r: (-r["score"], r["day"], r["price"], r["id"]))
    return matches, {"budget": budget, "channel": channel, "zone": zone}

