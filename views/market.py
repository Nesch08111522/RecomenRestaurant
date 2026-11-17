"""Discovery, checkout and tracking for the SmartResto food market."""
from collections import Counter, defaultdict
from statistics import median
import json
import base64
from datetime import date, datetime, timedelta
from uuid import uuid4

from flask import Blueprint, Response, abort, flash, redirect, render_template, request, session, url_for
from decimal import Decimal, InvalidOperation

from database.repository import PostgresDocumentRepository as Repo, document_transaction
from models.commerce_settings import commerce_settings
from logic.market import (CHANNELS, LIMA, MarketError, compatible, integer, key, money, now,
                          weekly_plan, words)
from models.market import reward_balance, coupon_discount, food_preferences, catalog, kitchen, lock_business, loyalty_discount, place_order, records, transition
from models.restaurant import RestaurantModel
from models.user import UserModel
from models.review import ReviewModel
from models.market_measurement import observe, signer
from utils import market_payments as payments
from utils.security import csrf
from utils.geo import calculate_distance, normalize_coordinates
from utils.ia_qwen import QwenIAError, obtener_respuesta_ia

market_bp = Blueprint("market", __name__, url_prefix="/mercado")


def identity(*roles):
    user = session.get("user") or {}
    if not user.get("id"):
        abort(401)
    if roles and user.get("role") not in roles:
        abort(403)
    return user


def parse_slot(value):
    try:
        slot = datetime.fromisoformat(value)
        return slot.replace(tzinfo=LIMA) if slot.tzinfo is None else slot.astimezone(LIMA)
    except (ValueError, TypeError):
        raise MarketError("Revisa la fecha y hora de atención en Lima.") from None


@market_bp.app_template_filter("soles")
def soles(value):
    return f"S/ {value / 100:.2f}"


@market_bp.errorhandler(MarketError)
def validation(error):
    return render_template("market/message.html", message=str(error)), 400


@market_bp.get("/")
def browse():
    from logic.market_discovery import discover

    user = session.get("user") or {}
    profile = food_preferences(UserModel.get_by_id(user["id"])) if user else {}
    history = records("market_orders", uid=user["id"]) if user else []
    rows, filters = discover(catalog(), request.args, profile, history)
    from views.ecosystem import current_context
    from logic.context import contextualize
    rows = contextualize(rows, current_context(), None, history)
    origin = normalize_coordinates(session.get("user_lat"), session.get("user_lng"))
    radius = integer(request.args["km"], 1, 100) if request.args.get("km") else None
    if radius and not origin:
        raise MarketError("Activa tu ubicación antes de filtrar por distancia.")
    pins = {}
    page = uuid4().hex
    sign = signer()
    for r in rows:
        r["ticket"] = sign.dumps((page, r["id"]))
        if r.get("pin"):
            pins[r["rid"]] = {"point": r["pin"], "name": r["business"], "pickup": r["pickup"], "radius": r["radius"]}
            if origin:
                r["distance"] = calculate_distance(*origin, *r["pin"])
    if radius:
        rows = [row for row in rows if row.get("distance", float("inf")) <= radius]
        pins = {row["rid"]: pins[row["rid"]] for row in rows if row["rid"] in pins}
    if origin and request.args.get("near"):
        rows.sort(key=lambda r: r.get("distance", float("inf")))
    start = now().date()
    week = request.args.get("week", profile.get("week", ""))
    plan = weekly_plan(rows, money(week), start) if week else []
    stores = RestaurantModel.get_by_owner(user.get("id")) if user.get("role") == "business_owner" else []
    if user:
        for shop in Repo.all("market_kitchens"):
            if user["id"] in shop["team"] and shop["id"] not in {s["id"] for s in stores}:
                business = RestaurantModel.get_by_id(shop["id"])
                if business:
                    stores.append(business)
    total = len(rows)
    size = 12
    pages = max(1, (total + size - 1) // size)
    number = min(max(1, request.args.get("page", 1, type=int)), pages)
    args = request.args.to_dict()
    args.pop("page", None)
    return render_template("market/browse.html", rows=rows[(number-1)*size:number*size],
                           total=total, number=number, pages=pages, page_args=args, filters=filters, plan=plan, pins=list(pins.values()), today=start.isoformat(), week=week,
                           channels=CHANNELS, diets=commerce_settings()['diets'], profile=profile, stores=stores,
                           week_total=sum(r["price"] for r in plan))


@market_bp.post("/preferencias")
def preferences():
    uid = identity()["id"]
    from decimal import Decimal
    amounts = {name: str(Decimal(money(request.form[name])) / 100) if request.form.get(name) else "" for name in ("budget", "daily", "week")}
    channel = request.form.get("channel", "")
    if channel and channel not in CHANNELS:
        raise MarketError("Selecciona una modalidad disponible.")
    UserModel.update(uid, {"market_preferences": {
        **amounts, "zone":request.form.get("zone", "").strip()[:80], "channel":channel,
        "likes": words(request.form.get("likes", "")[:300]), "avoid": words(request.form.get("avoid", "")[:300]),
        "diets": [d for d in commerce_settings()['diets'] if d in request.form.getlist("diet")],
        "reminders": request.form.get("reminders") == "on",
    }})
    flash("Preferencias guardadas.", "success")
    return redirect(url_for("market.browse"))


@market_bp.post("/consultar")
def consult():
    identity()
    from views.ai_routes import _rate_limited
    if _rate_limited():
        raise MarketError("Espera un momento antes de consultar de nuevo.")
    text = request.form.get("q", "").strip()[:300]
    if not text:
        raise MarketError("Escribe qué te gustaría encontrar.")
    filters = {"q": text}
    try:
        response = obtener_respuesta_ia(text, system_prompt=(
            "Convierte esta consulta gastronómica en un objeto JSON. Claves opcionales: budget (máximo por "
            "porción en soles), channel (Recojo, Local o Delivery), zone (distrito explícito), avoid (lista de "
            "ingredientes a excluir). Omite información ausente. No sugieras productos, no inventes datos."
        ), max_tokens=180)
        data = json.loads(response)
        if isinstance(data, dict):
            if data.get("channel") in CHANNELS:
                filters["channel"] = data["channel"]
            if isinstance(data.get("budget"), (int, float)) and type(data["budget"]) is not bool:
                filters["budget"] = str(money(data["budget"]) / 100)
            if isinstance(data.get("zone"), str) and key(data["zone"]) in key(text):
                filters["zone"] = data["zone"][:80]
            if isinstance(data.get("avoid"), list):
                filters["avoid"] = ",".join(x[:50] for x in data["avoid"][:10] if isinstance(x, str))
    except (QwenIAError, ValueError):
        flash("Se aplicó la búsqueda local al texto de tu consulta.", "info")
    return redirect(url_for("market.browse", **filters))


@market_bp.post("/carrito")
def add_cart():
    identity()
    oid = integer(request.form.get("offer"), 1)
    qty = integer(request.form.get("qty"), 1, 100)
    item = next((r for r in catalog() if r["id"] == oid), None)
    if not item:
        raise MarketError("La oferta ya no está disponible.")
    from flask import g
    prefs = food_preferences(g.account_record)
    if not compatible(item, prefs["avoid"]) or not set(prefs["diets"]).issubset(item.get("diets", [])):
        raise MarketError("Esta oferta no cumple las restricciones guardadas en tu perfil.")
    basket = session.get("market_cart", {})
    if basket and (basket["rid"] != item["rid"] or basket["day"] != item["day"]):
        raise MarketError("Finaliza o vacía el carrito antes de cambiar de negocio o día.")
    lines = basket.get("lines", {})
    lines[str(oid)] = lines.get(str(oid), 0) + qty
    if lines[str(oid)] > min(item["available"], 100) or len(lines) > 30:
        raise MarketError("La cantidad supera las porciones disponibles.")
    tickets = basket.get("tickets", {})
    ticket = request.form.get("ticket", "")
    if observe(ticket, "clicked", oid):
        # Only the random page key is needed for later attribution.
        tickets[str(oid)] = signer().loads(ticket)[0]
    session["market_cart"] = {"rid": item["rid"], "day": item["day"], "lines": lines, "tickets": tickets, "key": str(uuid4())}
    return redirect(url_for("market.cart"))


@market_bp.get("/carrito")
def cart():
    basket = session.get("market_cart", {})
    items = {str(r["id"]): r for r in catalog()} if basket else {}
    lines = [(items.get(oid), qty) for oid, qty in basket.get("lines", {}).items()]
    store = kitchen(basket["rid"]) if basket else {}
    subtotal = sum(row["price"] * qty for row, qty in lines if row)
    discount = loyalty_discount(identity()["id"], basket["rid"], subtotal, store) if basket else 0
    if basket.get("coupon"):
        try:
            discount = max(discount, coupon_discount(store, basket["coupon"], subtotal))
        except MarketError:
            basket = {k:v for k,v in basket.items() if k != "coupon"}
            session["market_cart"] = basket
            flash("El cupón caducó. Revisa el importe actualizado.", "warning")
    points = reward_balance(identity()["id"],basket["rid"]) if basket else 0
    if basket.get("reward"):
        if points>=10 and store.get("reward"):
            discount = min(subtotal,discount+store["reward"])
        else:
            basket.pop("reward",None)
            session["market_cart"]=basket
            flash("La recompensa ya no está disponible.","warning")
    diners = integer(request.args.get("personas", 1), 1, 30)
    share, extra = divmod(subtotal - discount, diners)
    return render_template("market/cart.html", points=points, cart=basket, lines=lines, store=store,
                           total=subtotal - discount, discount=discount, diners=diners, share=share, extra=extra,
                           addresses=((UserModel.get_by_id(identity()["id"]) or {}).get("profile") or {}).get("addresses", []) if basket else [],
                           digital=bool(basket and payments.enabled(basket["rid"])))


@market_bp.get("/oferta/<int:oid>")
def offer_detail(oid):
    from flask import g
    prefs = food_preferences(getattr(g, "account_record", {}))
    listing = Repo.get_by_id("market_offers", oid)
    if not listing:
        abort(404)
    variants = [r for r in catalog() if r["rid"] == listing["rid"] and r["dish_id"] == listing["dish_id"]]
    chosen = next((r for r in variants if r["id"] == oid), None)
    if not chosen:
        abort(404)
    allowed = compatible(chosen, prefs["avoid"]) and set(prefs["diets"]).issubset(chosen.get("diets", []))
    return render_template("market/dish.html", dish=chosen, variants=variants, allowed=allowed)


@market_bp.get("/oferta/<int:oid>/foto")
def offer_photo(oid):
    offer = Repo.get_by_id("market_offers", oid)
    if not offer or not offer.get("photo_id") or offer.get("paused") or offer.get("review_state","approved") != "approved":
        abort(404)
    business = RestaurantModel.get_by_id(offer["rid"])
    if not business or not business.get("verified"):
        abort(404)
    photo = Repo.get_by_id("market_photos", offer["photo_id"])
    if not photo or photo["rid"] != offer["rid"]:
        abort(404)
    return Response(base64.b64decode(photo["thumbnail"]), mimetype="image/jpeg",
                    headers={"Cache-Control":"private, max-age=60"})


@market_bp.post("/carrito/recompensa")
def cart_reward():
    identity()
    basket = session.get("market_cart")
    if not basket:
        raise MarketError("Agrega una oferta al carrito.")
    session["market_cart"] = {**basket,"reward":request.form.get("use")=="on","key":str(uuid4())}
    return redirect(url_for("market.cart"))


@market_bp.post("/carrito/cupon")
def apply_coupon():
    identity()
    basket = session.get("market_cart")
    if not basket:
        raise MarketError("Agrega un plato antes de aplicar un cupón.")
    code = request.form.get("code", "").strip().upper()
    coupon_discount(kitchen(basket["rid"]), code, 100)
    session["market_cart"] = {**basket, "coupon": code, "key": str(uuid4())}
    return redirect(url_for("market.cart"))


@market_bp.post("/carrito/vaciar")
def clear_cart():
    session.pop("market_cart", None)
    return redirect(url_for("market.browse"))


@market_bp.post("/comprar")
def buy():
    uid = identity()["id"]
    basket = session.get("market_cart")
    if not basket:
        return redirect(url_for("market.orders"))
    method = request.form.get("method")
    if method != "Contraentrega" and not (method == "Digital" and payments.enabled(basket["rid"])):
        raise MarketError("Selecciona un método de pago disponible.")
    order = place_order(uid, basket["rid"], basket["lines"], request.form.get("channel"),
                        [request.form.get("zone", "")[:100], request.form.get("address", "")[:220]],
                        parse_slot(request.form.get("slot")), basket["key"], method, integer(request.form.get("total"), 0, 2**63-1),
                        (request.form.get("lat"), request.form.get("lng")), basket.get("coupon", ""), bool(basket.get("reward")))
    for oid, page in basket.get("tickets", {}).items():
        observe(signer().dumps((page, int(oid))), "ordered", int(oid))
    session.pop("market_cart", None)
    flash(f"Pedido {order['id']} registrado.", "success")
    return redirect(url_for("market.orders"))


@market_bp.post("/interaccion")
def interaction():
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or data.get("stage") not in ("viewed", "clicked") or not isinstance(data.get("ticket"), str):
        abort(400)
    if not observe(data["ticket"][:400], data["stage"]):
        abort(400)
    return "", 204


@market_bp.get("/pedidos")
def orders():
    user = identity()
    history = records("market_orders", uid=user["id"])
    completed = [o for o in history if o["state"] == "Entregado" and not o.get("refunded")]
    reminders = (UserModel.get_by_id(user["id"]) or {}).get("market_preferences", {}).get("reminders")
    repeats = Counter(o["business"] for o in completed).most_common(1)
    due = []
    if reminders:
        by_shop = defaultdict(set)
        for o in completed:
            by_shop[(o["rid"], o["business"])].add(date.fromisoformat(o["day"]))
        for (rid, name), dates in by_shop.items():
            dates = sorted(dates)
            if len(dates) >= 3:
                interval = median((b-a).days for a,b in zip(dates, dates[1:]))
                due.append((rid, name, dates[-1] + timedelta(days=round(interval))))
    return render_template("market/orders.html", orders=history[::-1], cases=records("market_cases", uid=user["id"]),
                           spent=sum(o["total"] for o in completed),
                           points=sum(o["total"] // 1000 for o in completed),
                           repeat=repeats[0][0] if reminders and repeats else None, due=due)


@market_bp.post("/pedidos/<int:oid>/repetir")
def reorder(oid):
    uid = identity()["id"]
    order = Repo.get_by_id("market_orders", oid)
    if not order or order["uid"] != uid:
        abort(404)
    if session.get("market_cart"):
        raise MarketError("Finaliza o vacía el carrito antes de repetir un pedido.")
    profile = food_preferences(UserModel.get_by_id(uid))
    required = Counter()
    for line in order["lines"]:
        required[line["dish_id"]] += line["qty"]
    options = defaultdict(dict)
    for row in catalog():
        if row["rid"] != order["rid"] or row["dish_id"] not in required or row["available"] < required[row["dish_id"]]:
            continue
        if not compatible(row, profile.get("avoid", [])) or not set(profile.get("diets", [])).issubset(row.get("diets", [])):
            continue
        options[row["day"]][row["dish_id"]] = row["id"]
    for day, dishes in sorted(options.items()):
        if required.keys() <= dishes.keys():
            session["market_cart"] = {"rid":order["rid"], "day":day, "key":str(uuid4()),
                                      "lines":{str(dishes[d]):qty for d,qty in required.items()}}
            return redirect(url_for("market.cart"))
    raise MarketError("El combo completo no está disponible en un mismo día con tus preferencias actuales.")


@market_bp.post("/pedidos/<int:oid>/pagar")
def pay(oid):
    uid = identity()["id"]
    with document_transaction():
        order = Repo.get_by_id("market_orders", oid, for_update=True)
        if not order or order["uid"] != uid:
            abort(404)
        if order["method"] != "Digital" or order["paid"] or order["state"] != "Recibido" or order["slot"] <= now().isoformat():
            raise MarketError("Este pedido ya no admite pagos.")
        url = order.get("checkout") or payments.checkout(order)
        Repo.update("market_orders", oid, {"checkout": url})
    return redirect(url, 303)


@market_bp.post("/pagos/<int:rid>/notificar")
@csrf.exempt
def payment_notification(rid):
    pid = request.args.get("data.id", "")
    if not payments.enabled(rid) or not payments.signed(pid, request.headers.get("X-Request-Id", ""),
                                                       request.headers.get("X-Signature", "")):
        abort(403)
    try:
        canonical = payments.call(rid, "/v1/payments/" + pid)
        if str(canonical.get("id")) != pid:
            abort(400)
        oid = integer((canonical.get("metadata") or {}).get("order_id"), 1, 2**63-1)
        with document_transaction():
            lock_business(rid)
            order = Repo.get_by_id("market_orders", oid, for_update=True)
            if not order or order["rid"] != rid or order["method"] != "Digital" or canonical.get("external_reference") != payments.reference(order):
                abort(400)
            if canonical.get("currency_id") != "PEN" or Decimal(str(canonical.get("transaction_amount"))) * 100 != order["total"]:
                abort(400)
            status = canonical.get("status")
            if status == "approved":
                if order["state"] == "Cancelado" or order.get("payment_id", pid) != pid:
                    payments.refund(rid, pid)
                elif not order.get("refunded"):
                    Repo.update("market_orders", oid, {"paid": True, "payment_id": pid})
            elif status in {"rejected", "charged_back"} and order.get("payment_incident") != pid + ":" + status:
                from models.communication import admins, notify
                from utils.audit import record_event
                Repo.update("market_orders", oid, {"payment_incident":pid + ":" + status})
                record_event("PAYMENT_INCIDENT", resource_type="pedido", resource_id=oid, metadata={"status":status})
                notify([a["id"] for a in admins()], "Incidencia de pago", f"Revisa el pedido #{oid}.",
                       url_for("admin.operation_detail", oid=oid))
            elif status == "refunded" and order.get("payment_id") == pid:
                Repo.update("market_orders", oid, {"refunded": True, "paid": False})
                if order["state"] in {"Recibido","Confirmado"}:
                    transition(order, "Cancelado")
    except (MarketError, InvalidOperation):
        return "", 503
    return "", 204


@market_bp.get("/pedidos/<int:oid>/constancia")
def receipt(oid):
    uid = identity()["id"]
    order = Repo.get_by_id("market_orders", oid)
    if not order or order["uid"] != uid:
        abort(404)
    lines = ["SmartResto · Constancia de pedido", f"Pedido {oid} · {order['business']}",
             f"{order['channel']} · {order['slot']}", f"Estado: {order['state']}"]
    lines.extend(f"{l['qty']} × {l['name']} · {soles(l['qty'] * l['unit'])}" for l in order["lines"])
    lines.extend([f"Descuento: {soles(order.get('discount', 0))}", f"Total: {soles(order['total'])}",
                  "Pago: " + ("Reembolsado" if order.get("refunded") else ("Confirmado" if order["paid"] else "Pendiente")),
                  "Para el comprobante tributario, contacta con el negocio."])
    return Response("\n".join(lines), mimetype="text/plain", headers={"Cache-Control":"no-store",
        "Content-Disposition": f'attachment; filename="pedido-{oid}.txt"'})


@market_bp.cli.command("liberar-vencidos")
def expire_orders():
    """Release unpaid digital orders whose scheduled service time has passed."""
    count = 0
    for candidate in records("market_orders", state="Recibido", method="Digital", paid=False):
        if candidate["slot"] > now().isoformat():
            continue
        with document_transaction():
            lock_business(candidate["rid"])
            current = Repo.get_by_id("market_orders", candidate["id"], for_update=True)
            if current["state"] == "Recibido" and not current["paid"]:
                transition(current, "Cancelado")
                count += 1
    print(f"Pedidos liberados: {count}")


@market_bp.post("/pedidos/<int:oid>/cancelar")
def cancel(oid):
    uid = identity()["id"]
    order = Repo.get_by_id("market_orders", oid)
    if not order or order["uid"] != uid:
        abort(404)
    transition(order, "Cancelado", buyer=True)
    return redirect(url_for("market.orders"))


@market_bp.post("/pedidos/<int:oid>/reclamo")
def claim(oid):
    from models.communication import REASONS, admins, attachment, case_event, case_state

    uid = identity()["id"]
    order = Repo.get_by_id("market_orders", oid)
    if not order or order["uid"] != uid:
        abort(404)
    reason = request.form.get("reason", "").strip()
    if not 10 <= len(reason) <= 1000:
        raise MarketError("Describe el incidente entre 10 y 1000 caracteres.")
    category = request.form.get("category", "Otro")
    if category not in REASONS:
        raise MarketError("Selecciona un motivo válido.")
    with document_transaction():
        lock_business(order["rid"])
        case = next((c for c in records("market_cases", oid=oid, kind="Reclamo")
                     if case_state(c) != "Cerrado"), None)
        if not case:
            upload = request.files.get("document")
            staff = admins()
            case = Repo.create("market_cases", {"oid": oid, "rid": order["rid"], "uid": uid, "reason": reason,
                        "category": category, "priority": "Normal", "assigned": staff[0]["id"] if staff else None,
                        "evidence": attachment(upload, order["rid"]), "kind": "Reclamo", "state": "Nuevo",
                        "created": now().isoformat()})
            case_event(case, uid, "Reclamo presentado.")
    flash("El reclamo quedó en revisión.", "success")
    return redirect(url_for("comunicacion.case_detail", cid=case["id"]))


@market_bp.post("/pedidos/<int:oid>/valorar")
def verified_review(oid):
    uid = identity()["id"]
    rating = integer(request.form.get("rating"), 1, 5)
    comment = request.form.get("comment", "").strip()[:800]
    with document_transaction():
        initial = Repo.get_by_id("market_orders", oid)
        if not initial or initial["uid"] != uid:
            abort(404)
        business = lock_business(initial["rid"])
        order = Repo.get_by_id("market_orders", oid, for_update=True)
        if order["state"] != "Entregado" or not order["paid"] or order.get("refunded") or order.get("review"):
            raise MarketError("Solo puedes valorar una vez una compra entregada.")
        review = ReviewModel.add_review(uid, order["rid"], rating, comment)
        ReviewModel.update(review["id"], {"order_id": oid, "verified_purchase": True})
        Repo.update("market_orders", oid, {"review": review["id"]})
        from models.notification import NotificationModel
        NotificationModel.create_notification(business["owner_id"], "Nueva reseña verificada",
                                              f"Una compra recibió {rating}/5.", link=url_for("main.detail", restaurant_id=order["rid"]))
        RestaurantModel.update(order["rid"], {"rating": ReviewModel.get_rating_stats(order["rid"])["average"]})
    flash("Tu reseña de compra verificada quedó publicada.", "success")
    return redirect(url_for("market.orders"))

