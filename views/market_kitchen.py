"""Merchant workbench: one inventory, catalog and sales ledger per business."""
from datetime import date, timedelta
from uuid import uuid4
from math import ceil
from flask import abort, flash, redirect, render_template, request, session, url_for
from itsdangerous import BadSignature
from models.market_measurement import signer

from database.repository import PostgresDocumentRepository as Repo, document_transaction
from models.commerce_settings import commerce_settings
from logic.context import TAGS
from logic.market import (BUSINESSES, CHANNELS, OCCASIONS, MarketError, forecast, integer, key, money,
                          now, quote, recipe_cost, words)
from models.dish import DishModel
from models.market import indicators, kitchen, lock_business, records, save_kitchen, transition
from models.restaurant import RestaurantModel
from models.reservation import ReservationModel
from models.user import UserModel
from utils.kitchen_assistant import identify, menu_ideas
from utils import market_payments as payments
from utils.geo import normalize_coordinates
from views.market import identity, market_bp, parse_slot


def authorize(rid, owner_only=False):
    user = identity()
    uid = user["id"]
    restaurant = RestaurantModel.get_by_id(rid)
    if not restaurant:
        abort(404)
    is_owner = user.get("role") == "business_owner" and restaurant.get("owner_id") == uid
    if not is_owner and (owner_only or uid not in kitchen(rid)["team"]):
        abort(403)
    return restaurant


def return_desk(rid, message):
    flash(message, "success")
    return redirect(url_for("market.desk", rid=rid))


def day_value(value):
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError):
        raise MarketError("Selecciona una fecha válida.") from None


def desk_page(rid, **extra):
    business = authorize(rid)
    store = kitchen(rid)
    orders = records("market_orders", rid=rid)
    offers = records("market_offers", rid=rid)
    finished = [o for o in offers if o["ends"] <= now().isoformat() and o.get("produced")]
    produced = sum(o["produced"] for o in finished)
    surplus = sum(o["stock"] for o in finished)
    target = now().date() + timedelta(days=1)
    predictions = [(d["name"], forecast(orders, d["id"], target)) for d in records("dishes", restaurant_id=rid)]
    return render_template("market/kitchen.html", context_tags=TAGS, business=business, store=store, offers=offers[::-1],
        dishes=records("dishes", restaurant_id=rid), orders=orders[::-1], metrics=indicators(orders),
        moves=records("market_movements", rid=rid)[-12:][::-1], forecasts=predictions, target=target,
        produced=produced, surplus=surplus,
        reservations=ReservationModel.get_by_restaurant(rid), kinds=BUSINESSES, channels=CHANNELS,
        occasions=OCCASIONS, diets=commerce_settings()['diets'], today=now().date().isoformat(),
        draft_clock=signer("draft").dumps({"rid":rid, "uid":session["user_id"]}), **extra)


@market_bp.get("/cocina/<int:rid>")
def desk(rid):
    return desk_page(rid)


@market_bp.post("/cocina/<int:rid>/configurar")
def configure(rid):
    with document_transaction():
        lock_business(rid)
        authorize(rid, owner_only=True)
        store = kitchen(rid)
        form = request.form
        channels = form.getlist("channels")
        if form.get("kind") not in BUSINESSES or not channels or set(channels) - set(CHANNELS):
            raise MarketError("Selecciona un tipo de negocio y al menos una modalidad.")
        zones = [z.strip()[:80] for z in form.get("zones", "").split(",") if z.strip()][:20]
        pickup = form.get("pickup", "").strip()[:180]
        pin = None
        radius = integer(form.get("radius") or 0, 0, 100)
        if form.get("lat") or form.get("lng") or radius:
            pin = normalize_coordinates(form.get("lat"), form.get("lng"))
            if pin is None:
                raise MarketError("Indica las dos coordenadas del punto público de atención.")
        if "Delivery" in channels and not zones or "Recojo" in channels and not pickup:
            raise MarketError("Indica las zonas de delivery o el punto público de recojo.")
        staff = []
        for username in form.get("team", "").split(","):
            if username.strip():
                employee = UserModel.get_by_username(username.strip())
                if not employee or not UserModel.is_active(employee):
                    raise MarketError("Revisa los usuarios del equipo.")
                staff.append(employee["id"])
        store.update(kind=form["kind"], channels=channels, zones=zones, pickup=pickup, pin=pin, radius=radius, team=staff[:20],
                     team_names=form.get("team", "")[:500], capacity=integer(form.get("capacity", 20), 1, 200),
                     lead=integer(form.get("lead", 0), 0, 1440), loyalty=integer(form.get("loyalty", 0), 0, 30))
        store["reward"] = money(form.get("reward", str(store.get("reward",0)/100)))
        store["seats"] = integer(form.get("seats", store.get("seats",20)), 1, 500)
        store["table_minutes"] = integer(form.get("table_minutes", store.get("table_minutes",90)), 15, 240)
        save_kitchen(store)
        RestaurantModel.update(rid, {"market_channels": channels})
    return return_desk(rid, "Configuración comercial guardada.")


@market_bp.post("/cocina/<int:rid>/cupon")
def configure_coupon(rid):
    import re
    from datetime import date
    with document_transaction():
        lock_business(rid)
        authorize(rid, owner_only=True)
        store = kitchen(rid)
        code = request.form.get("code", "").strip().upper()
        coupon = {}
        if code:
            if not re.fullmatch(r"[A-Z0-9-]{3,32}", code):
                raise MarketError("Usa entre 3 y 32 letras, números o guiones para el código.")
            try:
                until = date.fromisoformat(request.form.get("until", ""))
            except ValueError:
                raise MarketError("Selecciona una fecha de vencimiento válida.") from None
            if until < now().date():
                raise MarketError("El vencimiento debe ser hoy o posterior.")
            coupon = {"code": code, "until": until.isoformat(), "percent": integer(request.form.get("percent"), 1, 90)}
        store["coupon"] = coupon
        save_kitchen(store)
    return return_desk(rid, "Cupón actualizado.")


@market_bp.post("/cocina/<int:rid>/inventario")
def inventory(rid):
    f = request.form
    name = key(f.get("name", ""))[:70]
    move = f.get("move")
    qty = integer(f.get("quantity"))
    if not name or move not in {"Entrada", "Merma", "Conteo"}:
        raise MarketError("Revisa el insumo y el movimiento.")
    with document_transaction():
        lock_business(rid)
        authorize(rid)
        store = kitchen(rid)
        lot = store["pantry"].get(name)
        old = lot["quantity"] if lot else 0
        if move == "Entrada":
            expiry = day_value(f.get("expires"))
            unit = f.get("unit")
            if expiry < now().date() or unit not in {"g", "ml", "unidad"} or not qty:
                raise MarketError("Indica unidades y un vencimiento vigente.")
            cost, basis = money(f.get("cost")), integer(f.get("basis"), 1)
            if lot and old and (lot["expires"] != expiry.isoformat() or lot["unit"] != unit or lot["cost"] != cost or lot["basis"] != basis):
                raise MarketError("Para un lote con otro vencimiento o costo usa un nombre distinto.")
            lot = {"quantity": old + qty, "expires": expiry.isoformat(), "unit": unit, "cost": cost,
                   "substitutes": words(f.get("substitutes", "")[:240]),
                   "basis": basis, "lot": lot["lot"] if old else uuid4().hex}
        else:
            if not lot or move == "Merma" and qty > old:
                raise MarketError("El movimiento supera el stock registrado.")
            lot["quantity"] = qty if move == "Conteo" else old - qty
        store["pantry"][name] = lot
        save_kitchen(store)
        Repo.create("market_movements", {"rid": rid, "name": name, "move": move, "delta": lot["quantity"] - old,
                                         "actor": session["user_id"], "at": now().isoformat()})
    return return_desk(rid, "Inventario actualizado.")


def parse_recipe(text, pantry):
    recipe = {}
    for entry in filter(str.strip, text.splitlines()):
        name, separator, qty = entry.rpartition("=")
        name = key(name)
        if not separator or name not in pantry or name in recipe:
            raise MarketError("Escribe un insumo registrado y su cantidad por línea, por ejemplo arroz=100.")
        recipe[name] = integer(qty.strip(), 1)
    return recipe


@market_bp.post("/cocina/<int:rid>/oferta")
def publish(rid):
    f = request.form
    with document_transaction():
        lock_business(rid)
        business = authorize(rid)
        store = kitchen(rid)
        if not store["channels"]:
            raise MarketError("Configura las modalidades de venta primero.")
        day = day_value(f.get("day"))
        at = now()
        ends = parse_slot(day.isoformat() + "T" + f.get("end", ""))
        if not at.date() <= day <= at.date() + timedelta(days=30) or ends <= at:
            raise MarketError("La oferta necesita un cierre futuro dentro de 30 días.")
        price, stock = money(f.get("price")), integer(f.get("stock"), 1, 10000)
        occasion, cross = f.get("occasion"), f.get("cross")
        if not price or occasion not in OCCASIONS or cross not in {"unknown", "possible", "declared"}:
            raise MarketError("Revisa precio, ocasión y declaración de contacto cruzado.")
        recipe = parse_recipe(f.get("recipe", ""), store["pantry"])
        rescue = money(f["rescue_price"]) if f.get("rescue_price") else None
        if rescue is not None and (not 0 < rescue < price or day != at.date()):
            raise MarketError("Últimas porciones requiere un descuento real para hoy.")
        photo = session.get("market_photo", {}) if f.get("use_photo") else {}
        if photo.get("rid") != rid:
            photo = {}
        if f.get("dish"):
            dish = DishModel.get_by_id(integer(f["dish"], 1))
            if not dish or dish.get("restaurant_id") != rid:
                abort(404)
        else:
            name = f.get("name", "").strip()[:100]
            category = f.get("category", "Fondo")
            if category not in {"Entrada", "Fondo", "Postre", "Bebida"}:
                raise MarketError("Selecciona una categoría de plato válida.")
            if not name:
                raise MarketError("Confirma el nombre del plato.")
            dish = DishModel.create({"restaurant_id": rid, "name": name, "price": price / 100, "category": category,
                "meal_time": "almuerzo" if occasion == "Almuerzo" else key(occasion), "description": f.get("description", "")[:500],
                "ingredients": list(recipe), "tags": words(f.get("tags", "")[:150]), "is_available": True, "menu_date": day.isoformat()})
        listing = {"rid": rid, "dish_id": dish["id"], "day": day.isoformat(), "stock": stock, "price": price,
                   "diets": [d for d in commerce_settings()['diets'] if d in f.getlist("diet")],
                   "context_tags": [tag for tag in TAGS if tag in f.getlist("context_tag")],
                   "variant": f.get("variant", "").strip()[:80], "name": dish["name"], "occasion": occasion, "cross": cross, "recipe": recipe, "ends": ends.isoformat(),
                   "allergens": words(f.get("allergens", "")[:300]) if f.get("declared") else None,
                   "origin": f.get("origin", "")[:240], "preparation": f.get("preparation", "")[:400],
                   "prepared": f.get("prepared", "")[:16], "rescue_price": rescue, "rescue_until": ends.isoformat() if rescue else None,
                   "photo_hash": photo.get("fingerprint"), "vision_used": bool(photo.get("vision")),
                   "vision_accepted": bool(photo.get("vision") and key(photo["name"]) == key(dish["name"])),
                   "review_state": "pending", "produced": stock, "created": at.isoformat()}
        if listing["photo_hash"] and records("market_offers", rid=rid, photo_hash=listing["photo_hash"]):
            raise MarketError("Esta fotografía ya figura en una oferta del negocio.")
        if photo:
            saved = Repo.get_by_id("market_photo_drafts", session["user_id"], for_update=True)
            if not saved or saved["rid"] != rid or saved["fingerprint"] != photo["fingerprint"]:
                raise MarketError("Selecciona la fotografía de nuevo antes de publicar.")
            image = Repo.create("market_photos", {"rid": rid, "thumbnail": saved["thumbnail"]})
            listing["photo_id"] = image["id"]
            Repo.delete("market_photo_drafts", session["user_id"])
        try:
            origin, started = signer("draft").loads(f.get("draft_clock", ""), max_age=7200, return_timestamp=True)
            if origin == {"rid":rid, "uid":session["user_id"]}:
                listing["draft_seconds"] = max(0, int((at-started).total_seconds()))
        except BadSignature:
            pass
        Repo.create("market_offers", listing)
        session.pop("market_photo", None)
    return return_desk(rid, "Oferta guardada. Solo los negocios aprobados aparecen en el mercado.")


@market_bp.post("/cocina/<int:rid>/oferta/<int:oid>/disponibilidad")
def pause_offer(rid, oid):
    with document_transaction():
        lock_business(rid)
        authorize(rid)
        offer = Repo.get_by_id("market_offers", oid, for_update=True)
        if not offer or offer["rid"] != rid:
            abort(404)
        status = request.form.get("state")
        if status not in {"pausar", "activar"}:
            raise MarketError("Estado no permitido.")
        Repo.update("market_offers", oid, {"paused": status == "pausar"})
    return return_desk(rid, "Disponibilidad actualizada.")


@market_bp.post("/cocina/<int:rid>/foto")
def photo(rid):
    authorize(rid)
    draft = identify(request.files.get("photo"))
    draft["rid"] = rid
    with document_transaction():
        Repo.get_by_id("users", session["user_id"], for_update=True)
        payload = {"id":session["user_id"], "rid":rid, "fingerprint":draft["fingerprint"],
                   "at":now().isoformat(), "thumbnail":draft.pop("thumbnail")}
        if not Repo.update("market_photo_drafts", payload["id"], payload):
            Repo.create("market_photo_drafts", payload)
    session["market_photo"] = draft
    return desk_page(rid, draft=draft)


@market_bp.post("/cocina/<int:rid>/copiloto")
def copilot(rid):
    authorize(rid)
    store = kitchen(rid)
    budget = money(request.form.get("budget"))
    portions = integer(request.form.get("portions"), 1, 500)
    suggestions = menu_ideas({k: v for k, v in store["pantry"].items() if v["expires"] >= now().date().isoformat()},
                             budget / 100, portions)
    return desk_page(rid, suggestions=suggestions)


@market_bp.post("/cocina/<int:rid>/simular")
def simulate(rid):
    authorize(rid)
    store = kitchen(rid)
    recipe = parse_recipe(request.form.get("recipe", ""), store["pantry"])
    cost = recipe_cost(recipe, store["pantry"])
    if cost is None:
        raise MarketError("Añade al menos un insumo con costo registrado.")
    result = quote(money(request.form.get("price")), cost, money(request.form.get("fixed")))
    target_margin = integer(request.form.get("target_margin") or 30, 0, 95)
    portions = integer(request.form.get("batch") or 1, 1, 500)
    needs = {}
    possible = []
    for name, per_portion in recipe.items():
        lot = store["pantry"][name]
        stocked = lot["quantity"] if lot["expires"] >= now().date().isoformat() else 0
        possible.append(stocked // per_portion)
        if stocked < per_portion * portions:
            needs[name] = {"missing": per_portion * portions - stocked, "unit": lot["unit"],
                           "alternatives": lot.get("substitutes", [])}
    return desk_page(rid, simulation={**result, "cost": cost, "batch": cost * portions,
                    "possible": min(possible), "suggested": ceil(cost * 100 / (100 - target_margin)), "needs": needs})


@market_bp.post("/cocina/<int:rid>/pedido/<int:oid>")
def manage_order(rid, oid):
    with document_transaction():
        lock_business(rid)
        authorize(rid)
        order = Repo.get_by_id("market_orders", oid, for_update=True)
        if not order or order["rid"] != rid:
            abort(404)
        action = request.form.get("action")
        if action == "Reembolsar":
            authorize(rid, owner_only=True)
            if order["state"] not in {"Recibido", "Confirmado"} or not order["paid"] or not order.get("payment_id"):
                raise MarketError("Este pedido no admite reembolso desde la cocina.")
            payments.refund(rid, order["payment_id"])
            order = Repo.update("market_orders", oid, {"refunded": True, "paid": False})
            action = "Cancelado"
        transition(order, action)
    return return_desk(rid, "Pedido actualizado.")


@market_bp.post("/cocina/<int:rid>/reserva/<int:reservation_id>")
def confirm_reservation(rid, reservation_id):
    with document_transaction():
        lock_business(rid)
        authorize(rid)
        item = Repo.get_by_id("reservations", reservation_id, for_update=True)
        status = request.form.get("status")
        if not item or item["restaurant_id"] != rid:
            abort(404)
        if status not in {"confirmada", "cancelada"} or item["status"] != "pendiente":
            raise MarketError("La reserva ya fue atendida o la acción no es válida.")
        ReservationModel.update(reservation_id, {"status": status})
        from models.notification import NotificationModel
        NotificationModel.create_notification(item["user_id"], "Reserva actualizada", f"Reserva #{reservation_id}: {status}.",
                                               link=f"/restaurant/{rid}")
    return return_desk(rid, "Reserva actualizada.")

