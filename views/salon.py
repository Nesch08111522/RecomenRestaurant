"""Carta digital por QR, sesiones de mesa y operación del salón (fases 8 y 9)."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from flask import (Blueprint, Response, abort, flash, jsonify, redirect, render_template,
                   request, session as browser, url_for)

from database.repository import PostgresDocumentRepository as Repo
from logic.market import MarketError, compatible, key, money, now
from logic.salon import ServiceError, active, order_total, public_session, table_state
from models.dish import DishModel
from models.market import catalog, food_preferences, kitchen, place_order
from models.restaurant import RestaurantModel
from models.review import ReviewModel
from models.salon import (SESSIONS, active_session, close_session, join_session, latest_session,
                          mark_cleaned, open_session, pay_share, request as request_service, resolve,
                          session_by_id, session_orders, set_split, table_by_token, table_detail,
                          tables, service_enabled)
from models.user import UserModel
from utils.catalog_qr import build_menu_qr

salon_bp = Blueprint("salon", __name__)
MAX_CART_LINES = 30


def user():
    return browser.get("user") or {}


def require_user():
    if not user().get("id"):
        abort(401)
    return user()


def is_staff(rid):
    from models.membership import authorized
    from utils.security import fresh_session_user
    return authorized(fresh_session_user(), rid, 'tables.service')


def require_staff(rid):
    if not is_staff(rid):
        abort(403 if user().get("id") else 401)
    return user()


def require_owner(rid):
    actor = require_user()
    restaurant = RestaurantModel.get_by_id(rid)
    if not restaurant or (actor.get("role") != "business_owner" or restaurant.get("owner_id") != actor["id"]):
        abort(404)
    return restaurant


def _restaurant(rid):
    restaurant = RestaurantModel.get_by_id(rid)
    if not restaurant or not restaurant.get("verified") or restaurant.get("status") in {"suspended", "archived"}:
        abort(404)
    return restaurant


def _tokens():
    return set(browser.get("table_tokens") or [])


def _remember(token):
    values = list(browser.get("table_tokens") or [])
    if token not in values:
        values.append(token)
    browser["table_tokens"] = values[-8:]


def _mine(session):
    actor = user()
    if not session:
        return False
    if session.get("token") in _tokens():
        return True
    return bool(actor.get("id") and session.get("uid") == actor["id"])


def _session_for(table, *, latest=False):
    if not table:
        return None
    return latest_session(table["id"]) if latest else active_session(table["id"])


@salon_bp.errorhandler(ServiceError)
def invalid(error):
    return render_template("salon/message.html", message=str(error), back=request.referrer), 400


def _menu(rid):
    offers = [row for row in catalog() if row["rid"] == rid]
    by_dish = defaultdict(list)
    for offer in offers:
        by_dish[offer["dish_id"]].append(offer)
    sections = defaultdict(list)
    for dish in DishModel.get_by_restaurant(rid):
        if not dish.get("is_available", True):
            continue
        sections[dish.get("category") or "Carta"].append({"dish": dish, "offers": by_dish.get(dish["id"], [])})
    return [{"category": name, "items": items} for name, items in sections.items()]


def _cart(token):
    carts = browser.get("table_carts") or {}
    return carts.get(token) or {"lines": {}, "key": None}


def _save_cart(token, cart):
    carts = dict(browser.get("table_carts") or {})
    carts[token] = cart
    browser["table_carts"] = {k: v for k, v in list(carts.items())[-4:]}


@salon_bp.get("/mesa/<token>")
def menu(token):
    table = table_by_token(token)
    if not table:
        abort(404)
    restaurant = _restaurant(table["rid"])
    current = active_session(table["id"])
    mine = _mine(current)
    pending = []
    orders = []
    split = None
    if current and mine:
        orders = session_orders(current)
        pending = [row for row in Repo.all("service_requests") if row.get("session_id") == current["id"]
                   and row.get("status") == "Pendiente"]
        split = current.get("split")
    cart = _cart(token) if mine else {"lines": {}}
    items = {str(row["id"]): row for row in catalog() if row["rid"] == table["rid"]}
    lines = [(items.get(oid), qty) for oid, qty in cart.get("lines", {}).items() if items.get(oid)]
    return render_template("salon/menu.html", table=table, restaurant=restaurant,
                           sections=_menu(table["rid"]), current=current, mine=mine,
                           state=table_state(current, orders, pending,
                                             cleaned=bool(current or {})),
                           cart_count=sum(qty for _, qty in lines),
                           cart_total=sum(row["price"] * qty for row, qty in lines),
                           service_enabled=service_enabled(restaurant),
                           split=split, orders=orders, pending=pending)


@salon_bp.post("/mesa/<token>/abrir")
def open_table(token):
    actor = require_user()
    table = table_by_token(token)
    if not table:
        abort(404)
    restaurant = _restaurant(table["rid"])
    if not service_enabled(restaurant):
        raise ServiceError("El negocio todavía no habilitó el servicio de mesa.")
    current = active_session(table["id"])
    if current:
        join_session(current, actor["id"])
        _remember(current["token"])
    else:
        current = open_session(table, uid=actor["id"], party_size=request.form.get("people", 1),
                               name=request.form.get("name") or (actor.get("profile") or {}).get("name"),
                               actor=actor["id"])
        _remember(current["token"])
    flash("Sesión de mesa iniciada. Escanear y abrir no cobra ni ocupa la mesa por sí solo.", "success")
    return redirect(url_for("salon.menu", token=token))


@salon_bp.post("/mesa/<token>/unirme")
def join_table(token):
    actor = require_user()
    table = table_by_token(token)
    if not table:
        abort(404)
    current = active_session(table["id"])
    if not current:
        raise ServiceError("La mesa todavía no tiene una sesión abierta.")
    join_session(current, actor["id"])
    _remember(current["token"])
    return redirect(url_for("salon.session_page", token=token))


@salon_bp.post("/mesa/<token>/carrito")
def add_to_cart(token):
    actor = require_user()
    table = table_by_token(token)
    current = active_session(table["id"]) if table else None
    if not table or not current or not _mine(current):
        raise ServiceError("Abre o únete a la sesión de la mesa antes de pedir.")
    offer = next((row for row in catalog() if row["id"] == request.form.get("offer", type=int)), None)
    if not offer or offer["rid"] != table["rid"]:
        raise ServiceError("La porción ya no está disponible.")
    qty = request.form.get("qty", 1, type=int)
    if not 1 <= qty <= 100:
        raise ServiceError("Indica una cantidad válida.")
    prefs = food_preferences(UserModel.get_by_id(actor["id"]))
    if not compatible(offer, prefs.get("avoid", [])) or not set(prefs.get("diets", [])).issubset(offer.get("diets", [])):
        raise ServiceError("Esta porción no cumple las restricciones guardadas en tu perfil.")
    cart = _cart(token)
    line = cart["lines"].get(str(offer["id"]), 0) + qty
    if line > min(offer["available"], 100) or len(cart["lines"]) >= MAX_CART_LINES:
        raise ServiceError("La cantidad supera las porciones disponibles.")
    cart["lines"][str(offer["id"])] = line
    cart["key"] = cart.get("key") or __import__("uuid").uuid4().hex
    _save_cart(token, cart)
    return redirect(url_for("salon.table_cart", token=token))


@salon_bp.get("/mesa/<token>/carrito")
def table_cart(token):
    table = table_by_token(token)
    current = active_session(table["id"]) if table else None
    if not table or not current or not _mine(current):
        abort(403)
    cart = _cart(token)
    items = {str(row["id"]): row for row in catalog() if row["rid"] == table["rid"]}
    lines = [(items[oid], qty) for oid, qty in cart["lines"].items() if oid in items]
    total = sum(row["price"] * qty for row, qty in lines)
    return render_template("salon/cart.html", table=table, restaurant=_restaurant(table["rid"]),
                           visit=current, lines=lines, total=total,
                           diners=current.get("party_size") or 1, cart=cart)


@salon_bp.post("/mesa/<token>/quitar")
def remove_line(token):
    cart = _cart(token)
    cart["lines"].pop(request.form.get("offer", ""), None)
    cart["key"] = cart.get("key") or __import__("uuid").uuid4().hex
    _save_cart(token, cart)
    return redirect(url_for("salon.table_cart", token=token))


@salon_bp.post("/mesa/<token>/pedido")
def place_table_order(token):
    actor = require_user()
    table = table_by_token(token)
    current = active_session(table["id"]) if table else None
    if not table or not current or not _mine(current):
        abort(403)
    cart = _cart(token)
    if not cart.get("lines"):
        raise ServiceError("Agrega al menos una porción antes de enviar el pedido.")
    order = place_order(actor["id"], table["rid"], cart["lines"], "Local", [], now(),
                        cart.get("key"), "Cuenta", request.form.get("total", type=int),
                        (None, None), "", False, table_session=current)
    _save_cart(token, {"lines": {}, "key": None})
    flash(f"Pedido {order['id']} enviado a la cocina.", "success")
    return redirect(url_for("salon.session_page", token=token))


@salon_bp.get("/mesa/<token>/sesion")
def session_page(token):
    table = table_by_token(token)
    current = _session_for(table, latest=True)
    if not table or not current:
        abort(404)
    if not _mine(current) and not is_staff(table["rid"]):
        abort(403)
    orders = session_orders(current)
    pending = [row for row in Repo.all("service_requests") if row.get("session_id") == current["id"]]
    review = Repo.get_by_id("reviews", current["review"]) if current.get("review") else None
    return render_template("salon/session.html", table=table, restaurant=_restaurant(table["rid"]),
                           visit=current, orders=orders, requests=[r for r in pending if r.get("status") == "Pendiente"],
                           history=pending, state=table_state(current, orders, pending,
                                                             cleaned=bool(current.get("cleaned_at"))),
                           total=order_total(orders), split=current.get("split"),
                           review=review, can_review=(current.get("status") == "Finalizada"
                                                      and current.get("paid") and not review))


@salon_bp.post("/mesa/<token>/solicitar")
def request_waiter(token):
    current = _session_for(table_by_token(token))
    if not current or not _mine(current):
        abort(403)
    row = request_service(current, request.form.get("kind", ""))
    flash("Solicitud enviada al personal." if row.get("status") == "Pendiente" else "Ya había una solicitud igual pendiente.", "success")
    return redirect(url_for("salon.session_page", token=token))


@salon_bp.post("/mesa/<token>/dividir")
def divide(token):
    current = _session_for(table_by_token(token))
    if not current or not _mine(current):
        abort(403)
    custom = request.form.get("shares", "").strip()
    if custom:
        try:
            shares = [money(value.strip()) for value in custom.split(",") if value.strip()]
        except (MarketError, InvalidOperation):
            raise ServiceError("Escribe cada parte en soles, separada por comas.") from None
        set_split(current, shares=shares)
    else:
        set_split(current, people=request.form.get("people", type=int))
    return redirect(url_for("salon.session_page", token=token))


@salon_bp.post("/mesa/<token>/valorar")
def review_table(token):
    actor = require_user()
    current = _session_for(table_by_token(token), latest=True)
    if not current or current.get("uid") != actor["id"]:
        abort(403)
    rating = request.form.get("rating", type=int)
    if not rating or not 1 <= rating <= 5:
        raise ServiceError("Selecciona una calificación entre 1 y 5.")
    from models.loyalty import review_session
    review_session(current, rating, request.form.get("comment", "").strip()[:800])
    flash("Gracias. Tu reseña de visita verificada quedó publicada.", "success")
    return redirect(url_for("salon.session_page", token=token))


@salon_bp.get("/mesa/<token>/estado.json")
def session_status(token):
    table = table_by_token(token)
    current = _session_for(table, latest=True)
    if not table or not current or not _mine(current):
        abort(404)
    orders = session_orders(current)
    pending = [row for row in Repo.all("service_requests") if row.get("session_id") == current["id"]]
    return jsonify(success=True, session=public_session(current, orders, pending, current.get("split")),
                   restaurant=table["rid"], updated=datetime.now().isoformat(timespec="seconds"))


@salon_bp.get("/owner/salon")
def manage_default():
    actor = require_user()
    restaurants = [row for row in RestaurantModel.get_by_owner(actor["id"])] if actor.get("role") == "business_owner" else []
    if not restaurants:
        flash("Registra un negocio antes de administrar mesas.", "warning")
        return redirect(url_for("owner.dashboard"))
    return redirect(url_for("salon.manage", rid=restaurants[0]["id"]))


@salon_bp.get("/owner/salon/<int:rid>")
def manage(rid):
    restaurant = require_owner(rid)
    rows = tables(rid)
    return render_template("salon/manage.html", restaurant=restaurant, tables=rows,
                           service_enabled=service_enabled(restaurant),
                           channels=(kitchen(rid) or {}).get("channels") or [])


@salon_bp.post("/owner/salon/<int:rid>/mesa")
def create_table(rid):
    require_owner(rid)
    from models.salon import save_table
    save_table(rid, user()["id"], request.form)
    flash("Mesa guardada.", "success")
    return redirect(url_for("salon.manage", rid=rid))


@salon_bp.post("/owner/salon/<int:rid>/mesa/<int:table_id>")
def edit_table(rid, table_id):
    require_owner(rid)
    from models.salon import delete_table, save_table
    if request.form.get("action") == "delete":
        delete_table(rid, table_id)
        flash("Mesa eliminada.", "success")
    else:
        save_table(rid, user()["id"], request.form, table_id)
        flash("Mesa actualizada.", "success")
    return redirect(url_for("salon.manage", rid=rid))


@salon_bp.get("/owner/salon/<int:rid>/mesa/<int:table_id>/qr.svg")
def table_qr(rid, table_id):
    require_owner(rid)
    table = next((row for row in tables(rid, active_only=False) if row["id"] == table_id), None)
    if not table:
        abort(404)
    try:
        content, url = build_menu_qr(table["qr_token"])
    except ValueError as error:
        raise ServiceError(str(error)) from None
    return Response(content, mimetype="image/svg+xml", headers={
        "Content-Disposition": f'attachment; filename="mesa-{table_id}.svg"', "Cache-Control": "no-store"})


@salon_bp.get("/salon")
def desk_default():
    actor = require_user()
    candidates = []
    if actor.get("role") == "business_owner":
        candidates = RestaurantModel.get_by_owner(actor["id"])
    if not candidates:
        candidates = [row for row in RestaurantModel.get_approved()
                      if actor["id"] in ((kitchen(row["id"]) or {}).get("team") or [])]
    if not candidates and actor.get("role") == "admin":
        candidates = RestaurantModel.get_approved()[:1]
    if not candidates:
        flash("No tienes un negocio con salón habilitado.", "warning")
        return redirect(url_for("main.index"))
    return redirect(url_for("salon.desk", rid=candidates[0]["id"]))


@salon_bp.get("/salon/<int:rid>")
def desk(rid):
    require_staff(rid)
    restaurant = RestaurantModel.get_by_id(rid) or abort(404)
    detail = table_detail(rid)
    from models.flow import expected_minutes
    expected = expected_minutes(rid)
    for row in detail:
        row["release"] = None
        row["release_basis"] = expected["basis"]
        if row["session"] and row["session"].get("opened_at"):
            try:
                opened = datetime.fromisoformat(row["session"]["opened_at"])
                row["release"] = (opened + timedelta(minutes=expected["minutes"])).strftime("%H:%M")
            except ValueError:
                row["release"] = None
    pending = [row for row in Repo.all("service_requests") if row.get("rid") == rid and row.get("status") == "Pendiente"]
    from models.flow import queue, settings
    from models.salon import snapshot
    current_queue = queue(rid)
    return render_template("salon/desk.html", restaurant=restaurant, rows=detail, pending=pending,
                           queue=current_queue, settings=settings(rid), tables=tables(rid),
                           seats=snapshot(rid, len(current_queue)),
                           service_enabled=service_enabled(restaurant))


@salon_bp.post("/salon/<int:rid>/abrir")
def staff_open(rid):
    actor = require_staff(rid)
    table = next((row for row in tables(rid) if row["id"] == request.form.get("table_id", type=int)), None)
    if not table:
        raise ServiceError("Selecciona una mesa activa.")
    current = open_session(table, party_size=request.form.get("people", 1),
                           name=request.form.get("name", ""), actor=actor["id"])
    flash(f"Mesa {table['label']} abierta.", "success")
    return redirect(url_for("salon.desk", rid=rid))


@salon_bp.post("/salon/<int:rid>/sesion/<int:session_id>/cerrar")
def staff_close(rid, session_id):
    actor = require_staff(rid)
    current = session_by_id(rid, session_id)
    if not current:
        abort(404)
    close_session(current, paid=request.form.get("paid") == "on", actor=actor["id"])
    flash("Mesa cerrada. Marca la limpieza para liberarla.", "success")
    return redirect(url_for("salon.desk", rid=rid))


@salon_bp.post("/salon/<int:rid>/sesion/<int:session_id>/limpiar")
def staff_clean(rid, session_id):
    actor = require_staff(rid)
    current = session_by_id(rid, session_id)
    if not current:
        abort(404)
    mark_cleaned(current, actor["id"])
    flash("Mesa limpia y disponible.", "success")
    return redirect(url_for("salon.desk", rid=rid))


@salon_bp.post("/salon/<int:rid>/solicitud/<int:request_id>")
def staff_resolve(rid, request_id):
    actor = require_staff(rid)
    resolve(request_id, rid, actor["id"])
    flash("Solicitud atendida.", "success")
    return redirect(url_for("salon.desk", rid=rid))


@salon_bp.post("/salon/<int:rid>/sesion/<int:session_id>/parte/<int:number>")
def staff_pay_share(rid, session_id, number):
    actor = require_staff(rid)
    current = session_by_id(rid, session_id)
    if not current:
        abort(404)
    pay_share(current, number)
    flash("Parte marcada como cobrada.", "success")
    return redirect(url_for("salon.desk", rid=rid))


@salon_bp.get("/salon/<int:rid>/estado.json")
def desk_status(rid):
    require_staff(rid)
    detail = table_detail(rid)
    return jsonify(success=True, tables=[{"id": row["table"]["id"], "state": row["state"],
                                          "total": row["total"], "session": (row["session"] or {}).get("id")}
                                         for row in detail],
                   pending=sum(len(row["requests"]) for row in detail),
                   updated=datetime.now().isoformat(timespec="seconds"))
