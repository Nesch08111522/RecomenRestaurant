"""Commerce records share the existing PostgreSQL document transaction."""
from collections import Counter
import base64
from datetime import timedelta
from uuid import UUID

from database.repository import PostgresDocumentRepository as Repo, document_transaction
from models.restaurant import RestaurantModel
from models.dish import DishModel
from models.notification import NotificationModel
from utils.geo import calculate_distance, normalize_coordinates
from logic.market import MarketError, available, effective_price, integer, now, recipe_cost


def records(collection, **fields):
    with document_transaction() as conn:
        cursor = conn.execute("SELECT payload FROM public.app_records WHERE collection=%s AND payload @> %s ORDER BY id",
                              (collection, Repo._jsonb(fields)))
        return [r["payload"] for r in cursor]


def kitchen(rid):
    return Repo.get_by_id("market_kitchens", rid) or {
        "id": rid, "pantry": {}, "channels": [], "zones": [], "kind": "", "pickup": "", "team": [],
    }


def save_kitchen(data):
    if not Repo.update("market_kitchens", data["id"], data):
        Repo.create("market_kitchens", data)


def lock_business(rid):
    restaurant = Repo.get_by_id("restaurants", rid, for_update=True)
    if not restaurant:
        raise MarketError("El negocio ya no está disponible.")
    return restaurant


def private_evidence(rid, file):
    content = file.read(1024 * 1024 + 1) if file else b""
    if len(content) > 1024 * 1024 or not content.startswith(b"%PDF-"):
        raise MarketError("Adjunta un documento PDF de hasta 1 MB.")
    evidence = Repo.create("market_evidence", {"rid": rid, "content": base64.b64encode(content).decode()})
    return evidence["id"]


def catalog():
    approved = {r["id"]: r for r in RestaurantModel.get_approved()}
    kitchens = {k["id"]: k for k in Repo.all("market_kitchens")}
    dishes = {d["id"]: d for d in DishModel.all()}
    accredited = {case["rid"] for case in records("market_cases", kind="Acreditación", state="Aceptado")}
    at = now()
    rows = []
    with document_transaction() as conn:
        candidates = conn.execute("SELECT payload FROM public.app_records WHERE collection='market_offers' AND payload->>'day' >= %s ORDER BY id",
                                  (at.date().isoformat(),)).fetchall()
    for result in candidates:
        listing = result["payload"]
        if listing.get("review_state", "approved") != "approved":
            continue
        rid = listing["rid"]
        store = kitchens.get(rid)
        dish = dishes.get(listing["dish_id"])
        if rid not in approved or not store or not store["channels"] or not dish or not dish.get("is_available", True):
            continue
        if listing["day"] < at.date().isoformat() or listing["ends"] <= at.isoformat():
            continue
        qty = available(listing, store["pantry"], listing["day"])
        if qty:
            price = effective_price(listing, at)
            rows.append({"occasion": "Por encargo", "cross": "unknown", "allergens": None, **listing,
                         "available": qty, "price": price, "saving": listing["price"] - price,
                         "category": dish.get("category", ""), "tags": dish.get("tags", []), "description": dish.get("description", ""),
                         "business": approved[rid]["name"], "district": approved[rid].get("district", ""),
                         "kind": store["kind"], "channels": store["channels"], "zones": store["zones"],
                         "pickup": store["pickup"], "pin": store.get("pin"), "radius": store.get("radius", 0),
                         "lead": store.get("lead", 0), "accredited": rid in accredited, "name": dish["name"]})
    return rows


def loyalty_discount(uid, rid, subtotal, store):
    percent = store.get("loyalty", 0)
    if not percent or not any(not o.get("refunded") for o in records("market_orders", uid=uid, rid=rid, state="Entregado")):
        return 0
    return subtotal * percent // 100


def coupon_discount(store, code, subtotal):
    if not code:
        return 0
    coupon = store.get("coupon") or {}
    if code != coupon.get("code") or coupon.get("until", "") < now().date().isoformat():
        raise MarketError("El cupón ha vencido o no corresponde a este negocio.")
    return subtotal * coupon["percent"] // 100


def food_preferences(user):
    profile = (user or {}).get("profile") or {}
    prefs = dict((user or {}).get("market_preferences") or {})
    restrictions = set(profile.get("restrictions") or [])
    mapping = {"vegano": "Vegano", "vegetariano": "Vegetariano", "sin gluten": "Sin gluten", "celiaco": "Sin gluten"}
    prefs["diets"] = sorted(set(prefs.get("diets", [])) | {mapping[r] for r in restrictions if r in mapping})
    prefs["avoid"] = sorted(set(prefs.get("avoid", [])) | {r.removeprefix("alergia ") for r in restrictions if r.startswith("alergia ")})
    return prefs


def reward_balance(uid, rid):
    history = records("market_orders",uid=uid,rid=rid)
    earned = sum(o["total"]//1000 for o in history if o["state"]=="Entregado" and o.get("paid") and not o.get("refunded"))
    used = sum(o.get("reward_points",0) for o in history if o["state"]!="Cancelado" and not o.get("refunded"))
    return earned-used


def place_order(uid, rid, cart, channel, destination, slot, request_key, method, expected=None, coordinates=(None, None), coupon_code="", use_reward=False, table_session=None):
    try:
        request_key = str(UUID(request_key))
    except (ValueError, TypeError, AttributeError):
        raise MarketError("Actualiza el carrito antes de confirmar.") from None
    with document_transaction():
        business = lock_business(rid)
        existing = records("market_orders", uid=uid, rid=rid, request_key=request_key)
        if existing:
            return existing[0]
        store = kitchen(rid)
        if not business.get("verified") or channel not in store["channels"]:
            raise MarketError("Esta modalidad ya no está disponible.")
        table = None
        if table_session is not None:
            from logic.salon import active as session_active
            table = Repo.get_by_id("table_sessions", table_session["id"], for_update=True)
            if (not table or table.get("rid") != rid or not session_active(table)
                    or table.get("uid") not in (None, uid) or channel != "Local"):
                raise MarketError("La sesión de mesa ya no admite pedidos.")
            if table.get("uid") is None:
                table = Repo.update("table_sessions", table["id"], {"uid": uid})
            slot = now()
            destination = [f"Mesa {table.get('table_label') or table['table_id']}",
                           " · ".join(filter(None, [table.get("floor"), table.get("zone")]))]
        else:
            if channel == "Delivery" and (destination[0] not in store["zones"] or not destination[1].strip()):
                raise MarketError("Selecciona una zona de cobertura e indica la dirección de entrega.")
            if channel == "Delivery" and store.get("radius"):
                point = normalize_coordinates(*coordinates)
                if not point or calculate_distance(*store["pin"], *point) > store["radius"]:
                    raise MarketError("Indica un punto de entrega dentro del radio de cobertura del negocio.")
        at = now()
        if table is None and (slot <= at + timedelta(minutes=store.get("lead", 0)) or slot > at + timedelta(days=30)):
            raise MarketError("Selecciona una hora futura dentro de los próximos 30 días.")
        if table is None and channel == "Recojo":
            hour = slot.isoformat()[:13]
            reservations = sum(o["channel"] == channel and o["slot"][:13] == hour and o["state"] != "Cancelado"
                               for o in records("market_orders", rid=rid, day=slot.date().isoformat()))
            if reservations >= store.get("capacity", 20):
                raise MarketError("Ese turno de recojo está completo. Selecciona otra hora.")
        if not 1 <= len(cart) <= 30:
            raise MarketError("Elige entre uno y treinta productos del mismo negocio.")
        from logic.market import compatible
        prefs = food_preferences(Repo.get_by_id("users", uid))
        lines, total = [], 0
        for oid, raw_qty in sorted(cart.items()):
            qty = integer(raw_qty, 1, 100)
            offer = Repo.get_by_id("market_offers", oid)
            if not offer or offer["rid"] != rid or offer.get("review_state","approved") != "approved":
                raise MarketError("El carrito contiene un producto de otro negocio.")
            if not compatible(offer, prefs["avoid"]) or not set(prefs["diets"]).issubset(offer.get("diets", [])):
                raise MarketError("Un producto del carrito no cumple tus restricciones actuales.")
            dish = DishModel.get_by_id(offer["dish_id"])
            day = slot.date().isoformat()
            if not dish or not dish.get("is_available", True) or slot.isoformat() > offer["ends"] or qty > available(offer, store["pantry"], day):
                raise MarketError("Ya no hay suficientes porciones para ese día y hora.")
            price = effective_price(offer, at)
            if price < offer["price"] and slot.isoformat() > offer["rescue_until"]:
                raise MarketError("Selecciona una hora dentro de la oferta de últimas porciones.")
            unit_cost = recipe_cost(offer["recipe"], store["pantry"])
            usage = {}
            from decimal import Decimal, ROUND_HALF_UP
            from logic.inventory_lots import consume
            batch_cost = Decimal(0)
            for name, amount in offer["recipe"].items():
                lot = store["pantry"][name]
                allocations, consumed_cost = consume(lot, amount * qty, day)
                usage[name] = {"amount": amount * qty, "lot": allocations[0]["lot"], "lots": allocations}
                batch_cost += consumed_cost
            if offer["recipe"]:
                unit_cost = int((batch_cost / qty).quantize(Decimal(1), rounding=ROUND_HALF_UP))
            Repo.update("market_offers", oid, {"stock": offer["stock"] - qty})
            remaining = min(offer["stock"] - qty, available(offer, store["pantry"], day))
            if remaining == 0:
                NotificationModel.create_notification(business["owner_id"], "Producto agotado", dish["name"],
                                                       link=f"/mercado/cocina/{rid}")
            elif remaining <= 3 and offer["stock"] > 3:
                NotificationModel.create_notification(business["owner_id"], "Inventario bajo",
                                                       f"{dish['name']}: quedan {remaining} porciones.", link=f"/mercado/cocina/{rid}")
            lines.append({"offer": oid, "dish_id": dish["id"], "name": dish["name"], "qty": qty,
                          "unit": price, "cost": unit_cost, "saving": offer["price"] - price, "usage": usage})
            total += qty * price
        discount = max(loyalty_discount(uid, rid, total, store), coupon_discount(store, coupon_code, total))
        reward_points = 0
        if use_reward:
            reward = store.get("reward",0)
            if not reward or reward_balance(uid,rid)<10:
                raise MarketError("La recompensa ya no está disponible. Revisa tus puntos.")
            reward_points = 10
            discount = min(total, discount+reward)

        if expected is not None and total - discount != expected:
            raise MarketError("El precio cambió. Vuelve al carrito para revisar el total actualizado.")
        save_kitchen(store)
        order = Repo.create("market_orders", {"uid": uid, "rid": rid, "business": business["name"], "lines": lines,
            "day": slot.date().isoformat(), "slot": slot.isoformat(), "total": total - discount, "discount": discount, "channel": channel,
            "destination": destination if channel in {"Delivery", "Local"} else [], "method": method, "paid": False,
            "reward_points":reward_points, "coupon": coupon_code, "state": "Recibido", "request_key": request_key, "created": at.isoformat(),
            "table_id": table.get("table_id") if table else None,
            "table_session": table.get("id") if table else None,
            "table_label": table.get("table_label") if table else None,
            "service": "Salón" if table else "Pedido",
            "history": [{"state": "Recibido", "at": at.isoformat()}]})
        if table:
            Repo.update("table_sessions", table["id"], {
                "status": "Pedido", "last_activity": at.isoformat(), "split": None,
                "order_ids": list(table.get("order_ids") or []) + [order["id"]],
            })
        recipients = {business["owner_id"], *(store.get("team") or [])}
        for staff_id in recipients:
            if staff_id:
                NotificationModel.create_notification(
                    staff_id, "Nuevo pedido por mesa",
                    f"Pedido {order['id']} · mesa {table.get('table_label') if table else ''} · {slot:%d/%m %H:%M}.",
                    link=f"/salon/{rid}" if table else f"/mercado/cocina/{rid}",
                    event_key=f"order:{order['id']}:created:staff")
        NotificationModel.create_notification(uid, "Pedido confirmado", f"Pedido #{order['id']} en {business['name']}.",
                                              link=f"/mesa/{table['token']}" if table else "/mercado/pedidos",
                                              event_key=f"order:{order['id']}:created:buyer")
        return order


def transition(order, action, buyer=False):
    with document_transaction():
        business = lock_business(order["rid"])
        order = Repo.get_by_id("market_orders", order["id"], for_update=True)
        if action == order["state"]:
            return order
        transitions = {"Recibido": {"Confirmado", "Preparando", "Cancelado"}, "Confirmado": {"Preparando", "Cancelado"},
                       "Preparando": {"Listo"}, "Listo": {"En reparto"} if order["channel"] == "Delivery" else {"Entregado"},
                       "En reparto": {"Entregado"}}
        if action not in transitions.get(order["state"], set()) or (buyer and action != "Cancelado"):
            raise MarketError("La acción no corresponde al estado actual del pedido.")
        if order["method"] == "Digital" and not order["paid"] and action != "Cancelado":
            raise MarketError("Aún no hay confirmación del proveedor de pago.")
        if action == "Cancelado":
            if order["paid"] and not order.get("refunded"):
                raise MarketError("Primero confirma el reembolso del pago.")
            store = kitchen(order["rid"])
            for line in order["lines"]:
                offer = Repo.get_by_id("market_offers", line["offer"])
                if offer:
                    Repo.update("market_offers", offer["id"], {"stock": offer["stock"] + line["qty"]})
                for name, used in line["usage"].items():
                    lot = store["pantry"].get(name)
                    if lot:
                        from logic.inventory_lots import restore
                        restore(lot, used.get("lots", [{"lot": used["lot"], "amount": used["amount"]}]))
                    else:
                        raise MarketError("Falta el insumo original para restaurar el pedido.")
            save_kitchen(store)
        changes = {"state": action, "history": order["history"] + [{"state": action, "at": now().isoformat()}]}
        if action == "Entregado" and order["method"] == "Contraentrega":
            changes["paid"] = True
        updated = Repo.update("market_orders", order["id"], changes)
        NotificationModel.create_notification(order["uid"], "Seguimiento de pedido", f"Pedido {order['id']}: {action}.",
                                              link="/mercado/pedidos",
                                              event_key=f"order:{order['id']}:state:{action}:buyer")
        NotificationModel.create_notification(business["owner_id"], "Pedido actualizado", f"Pedido {order['id']}: {action}.",
                                              link=f"/mercado/cocina/{order['rid']}",
                                              event_key=f"order:{order['id']}:state:{action}:owner")
        return updated


def indicators(orders):
    sales = [o for o in orders if o["state"] == "Entregado" and o["paid"] and not o.get("refunded")]
    customers = Counter(o["uid"] for o in sales)
    known_cost_sales = [o for o in sales if all(l["cost"] is not None for l in o["lines"])]
    selling_hours = Counter(o["slot"][11:13] for o in sales if isinstance(o.get("slot"),str) and len(o["slot"])>=13)
    return {"sales": len(sales), "income": sum(o["total"] for o in sales),
            "margin": sum(o["total"] - sum(l["cost"] * l["qty"] for l in o["lines"]) for o in known_cost_sales),
            "costed": len(known_cost_sales), "peak": selling_hours.most_common(1)[0][0] if selling_hours else None,
            "repeat": sum(n > 1 for n in customers.values()), "customers": len(customers),
            "rescued": sum(l["qty"] for o in sales for l in o["lines"] if l["saving"] > 0),
            "savings": sum(l["qty"] * l["saving"] for o in sales for l in o["lines"])}

