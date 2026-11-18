"""Rules for the food market. Money is stored in céntimos, inventory in base units."""
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from math import ceil
import unicodedata

LIMA = timezone(timedelta(hours=-5))
CHANNELS = ("Recojo", "Delivery", "Local")
BUSINESSES = ("Comida casera", "Cocina desde casa", "Restaurante", "Menú económico", "Cafetería",
              "Sanguchería", "Hamburguesería", "Pastelería", "Panadería", "Bodega", "Tienda de alimentos", "Catering", "Emprendimiento", "Bebidas", "Cocina oculta", "Delivery", "Otro")
OCCASIONS = ("Desayuno", "Almuerzo", "Cena", "Postre", "Bebida", "Snack", "Regional", "Por encargo", "Semanal", "Saludable")
DIETS = ("Vegetariano", "Vegano", "Sin gluten")


class MarketError(ValueError):
    """Validation message suitable for the storefront."""


def now():
    return datetime.now(LIMA)


def key(text):
    return "".join(c for c in unicodedata.normalize("NFKD", str(text).casefold()) if not unicodedata.combining(c)).strip()


def words(text):
    return sorted({key(x) for x in str(text or "").split(",") if key(x)})


def integer(value, minimum=0, maximum=1000000):
    try:
        n = int(str(value))
        if not minimum <= n <= maximum:
            raise ValueError
        return n
    except (ValueError, TypeError, OverflowError):
        raise MarketError("Revisa la cantidad indicada.") from None


def money(value):
    try:
        n = Decimal(str(value))
        if not n.is_finite() or not 0 <= n <= 100000:
            raise InvalidOperation
        return int((n * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP))
    except (ValueError, InvalidOperation):
        raise MarketError("Ingresa un importe válido en soles.") from None


def available(offer, pantry, day):
    if offer.get("day") != day or offer.get("paused"):
        return 0
    portions = offer["stock"]
    for name, amount in offer.get("recipe", {}).items():
        ingredient = pantry.get(name)
        if not ingredient or ingredient["expires"] < day:
            return 0
        portions = min(portions, ingredient["quantity"] // amount)
    return portions


def compatible(offer, excluded):
    if not excluded:
        return True
    if offer.get("cross") != "declared" or offer.get("allergens") is None:
        return False
    declared = {key(x) for x in offer["allergens"] + list(offer.get("recipe", {}))}
    return not any(key(x) in ingredient or ingredient in key(x) for x in excluded for ingredient in declared)


def quote(price, variable_cost, fixed):
    contribution = price - variable_cost
    return {"contribution": contribution, "margin": round(100 * contribution / price, 1) if price else None,
            "break_even": ceil(fixed / contribution) if contribution > 0 else None}


def recipe_cost(recipe, pantry):
    if not recipe or any(name not in pantry for name in recipe):
        return None
    cost = sum(Decimal(qty * pantry[name]["cost"]) / pantry[name]["basis"] for name, qty in recipe.items())
    return int(cost.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def weekly_plan(rows, budget, start):
    """Cover the most days first, then use spare budget for variety."""
    by_day = {}
    for offset in range(7):
        day = (start + timedelta(days=offset)).isoformat()
        options = sorted((r for r in rows if r["day"] == day and r["available"]),
                         key=lambda r: (r["price"], -r.get("score", 0), r["id"]))
        if options:
            by_day[day] = options
    selected = {}
    for day in sorted(by_day, key=lambda d: (by_day[d][0]["price"], d)):
        cheapest = by_day[day][0]
        if cheapest["price"] <= budget:
            selected[day] = cheapest
            budget -= cheapest["price"]
    plan, used = [], Counter()
    for day, cheapest in sorted(selected.items()):
        limit = budget + cheapest["price"]
        best = min((r for r in by_day[day] if r["price"] <= limit),
                   key=lambda r: (used[key(r["name"])], -r.get("score", 0), r["price"], r["id"]))
        used[key(best["name"])] += 1
        plan.append(best)
        budget = limit - best["price"]
    return plan


def forecast(orders, dish_id, target):
    """Average across previously observed matching weekdays; no invented sales."""
    totals = defaultdict(int)
    for order in orders:
        if order["state"] != "Entregado":
            continue
        day = date.fromisoformat(order["day"])
        if day.weekday() == target.weekday() and target - timedelta(weeks=8) <= day < target:
            totals[day] += sum(line["qty"] for line in order["lines"] if line["dish_id"] == dish_id)
    return {"portions": round(sum(totals.values()) / len(totals)), "days": len(totals)} if totals else None


def effective_price(offer, at):
    end = offer.get("rescue_until")
    return offer["rescue_price"] if end and at.isoformat() < end and at.date().isoformat() == offer["day"] else offer["price"]

