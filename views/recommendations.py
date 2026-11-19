"""Authenticated signals and consent-aware delivery of Phase 7 recommendations."""
from datetime import date, time, timedelta
from decimal import Decimal, InvalidOperation
from hashlib import blake2s
import re

from flask import Blueprint, current_app, g, jsonify, make_response, render_template, request, session, url_for
from itsdangerous import BadSignature, URLSafeTimedSerializer

from database.repository import PostgresDocumentRepository as Repo, document_transaction
from logic.context import MOMENTS
from logic.market import CHANNELS, key as normalize_key, now
from models.category import CategoryModel
from models.dish import DishModel
from models.market import catalog, food_preferences, records
from models.recommendation_history import recent_searches
from models.restaurant import RestaurantModel
from utils import weather
from utils.geo import normalize_coordinates
from utils.security import fresh_session_user, normalize_text


bp = Blueprint("recommendations", __name__)
COLLECTION = "recommendation_feedback"
SESSION_CONTEXT = "recommendation_context"
FEEDBACK_LIMIT = 250
VIEW_LIMIT = 30
RESULT_BY_KIND = {"all": "items", "dish": "dishes", "restaurant": "restaurants", "experience": "experiences"}
CARD_KEY = re.compile(r"(?:dish|restaurant|experience)-[1-9][0-9]*")
ACTIONS = {"view": "viewed", "like": "liked", "dismiss": "dismissed"}


def _number(value, maximum):
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return float(amount) if amount.is_finite() and 0 <= amount <= maximum else None


def _active_context(key, at):
    context = session.get(key) or {}
    return context if context.get("until", "") > at.isoformat() else {}


def _location(profile, at):
    if (session.get(SESSION_CONTEXT) or {}).get("disabled"):
        return None, False, False
    context = _active_context(SESSION_CONTEXT, at)
    point = normalize_coordinates(context.get("lat"), context.get("lng"))
    if point:
        return point, True, context.get("weather") is True
    permission = profile.get("location_consent") is True
    if permission:
        point = normalize_coordinates(session.get("user_lat"), session.get("user_lng"))
    return point, permission, False


def _options(at):
    args = request.args
    saved_context = _active_context("food_context", at)
    try:
        day = date.fromisoformat(args.get("day", ""))
        if not at.date() <= day <= at.date() + timedelta(days=30):
            day = None
    except ValueError:
        day = None
    clock = args.get("time", "")
    if re.fullmatch(r"[0-9]{2}:[0-9]{2}", clock):
        try:
            clock = time.fromisoformat(clock).isoformat(timespec="minutes")
        except ValueError:
            clock = ""
    else:
        clock = ""
    kind = args.get("kind", "all")
    channel = args.get("channel", "")
    moment = args.get("moment", saved_context.get("moment", ""))
    return {
        "q": normalize_text(args.get("q"), max_length=140),
        "kind": kind if kind in RESULT_BY_KIND else "all",
        "channel": channel if channel in CHANNELS else "",
        "budget": _number(args.get("budget"), 1_000_000),
        "radius": _number(args.get("radius"), 100) or None,
        "day": day.isoformat() if day else "",
        "time": clock,
        "open_now": args.get("open_now") in {"1", "on", "true"},
        "discovery": args.get("discovery") in {"1", "on", "true"},
        "moment": moment if moment in MOMENTS else "",
        "mood": saved_context.get("mood", ""),
    }


def _signer():
    return URLSafeTimedSerializer(current_app.secret_key, salt="smartresto-phase7-feedback")


def _public_profile(profile, market_profile):
    name = normalize_text(profile.get("name"), max_length=120)
    return {
        "name": name.split(maxsplit=1)[0] if name else "",
        "preferences": profile.get("preferences") or [],
        "restrictions": profile.get("restrictions") or [],
        "daily_budget": _number(profile.get("daily_budget"), 1_000_000),
        "weekly_budget": _number(profile.get("weekly_budget"), 1_000_000),
        "channel": market_profile.get("channel", ""),
    }


def _public_restaurants():
    stores = {store["id"]: store for store in Repo.all("market_kitchens") if store.get("kind")}
    restaurants = []
    for restaurant in RestaurantModel.get_approved():
        store = stores.get(restaurant["id"])
        if store:
            pin = store.get("pin")
            point = normalize_coordinates(*pin) if isinstance(pin, (tuple, list)) and len(pin) == 2 else None
            lat, lng = point or (None, None)
            restaurant = {**restaurant, "lat": lat, "lng": lng}
        restaurants.append(restaurant)
    return restaurants


def _payload():
    from logic.phase7_recommender import recommend

    user = fresh_session_user()
    account = g.account_record if user else {}
    profile = account.get("profile") or {}
    market_profile = food_preferences(account)
    at = now()
    options = _options(at)
    point, permission, weather_enabled = _location(profile, at)
    if not point:
        options["radius"] = None
    explicit_moment = request.args.get("moment", "")
    search_options = {
        **options,
        "search_mode": True,
        "moment": explicit_moment if explicit_moment in MOMENTS else "",
        "mood": "",
    }
    search_active = options["budget"] is not None or options["kind"] != "all" or any(
        search_options[field] for field in ("q", "channel", "day", "time", "radius", "open_now", "moment")
    )

    orders, visits, favorites, searches, feedback = [], [], [], [], {}
    with document_transaction():
        restaurants = _public_restaurants()
        dishes = DishModel.all()
        categories = CategoryModel.all()
        offers = catalog()
        if user:
            uid = user["id"]
            orders = records("market_orders", uid=uid)
            visits = records("reservations", user_id=uid, status="asistida")
            favorites = records("favorites", user_id=uid)
            searches = recent_searches(uid)
            feedback = Repo.get_by_id(COLLECTION, uid) or {}

    for row in offers:
        if row.get("photo_id"):
            row["image"] = url_for("market.offer_photo", oid=row["id"])
        if row.get("model_id"):
            row["model_url"] = url_for("ecosystem.dish_model", oid=row["id"])
    forecast = weather.conditions(*point) if point and weather_enabled else None
    states = feedback.get("items") or {}
    topics = [
        {**entry, "id": blake2s(normalize_key(entry["query"]).encode("utf-8"), digest_size=8).hexdigest()}
        for entry in searches
    ]
    topic_id = request.args.get("interes", "")
    focus = next((topic for topic in topics if topic["id"] == topic_id), None)
    inputs = dict(
        restaurants=restaurants, dishes=dishes, offers=offers, categories=categories,
        profile={**profile, "location_consent": bool(point)}, market_profile=market_profile,
        orders=orders, visits=visits, favorites=favorites, search_history=searches, feedback=states,
        feedback_signals=feedback.get("signals") or {},
        location=point, weather=forecast, at=at,
    )
    saved_context = _active_context("food_context", at)
    recommendation_options = {"moment": saved_context.get("moment"), "mood": saved_context.get("mood")}
    personalized = recommend(**inputs, options=recommendation_options)
    if search_active:
        result = recommend(**inputs, options=search_options)
    elif options["discovery"]:
        result = recommend(**inputs, options=options)
    else:
        result = personalized
    group_name = RESULT_BY_KIND[options["kind"]]
    for_you = personalized["for_you"]
    discovery = personalized["discovery_items"]
    if focus:
        focused_inputs = {**inputs, "search_history": [focus], "orders": []}
        focused_options = {**recommendation_options, "budget": personalized["context"]["budget"]}
        for_you = recommend(**focused_inputs, options=focused_options)["for_you"]
        # The focused deck can include products originally reserved for discovery.
        personal_products = {(card["restaurant_id"], card["dish_id"]) for card in for_you["items"]}
        discovery = {
            group: [card for card in cards if (card["restaurant_id"], card["dish_id"]) not in personal_products]
            for group, cards in discovery.items()
        }

    signer = _signer() if user else None
    tokens = {}
    groups = [*(result[group] for group in RESULT_BY_KIND.values()), *for_you.values(), *discovery.values()]
    for cards in groups:
        for card in cards:
            if "token" in card:
                continue
            if card.get("offer_id"):
                card["href"] = url_for("market.offer_detail", oid=card["offer_id"])
            else:
                anchor = f"plato-{card['dish_id']}" if card.get("dish_id") else None
                card["href"] = url_for("main.detail", restaurant_id=card["restaurant_id"], day=card.get("day"), _anchor=anchor)
            card_key = card["key"]
            if signer and card_key not in tokens:
                identity = (user["id"], card_key)
                if card["kind"] == "experience" and type(card["dish_id"]) is int:
                    identity = (*identity, card["dish_id"])
                tokens[card_key] = signer.dumps(identity)
            card["token"] = tokens.get(card_key)
            card["liked"] = states.get(card_key) == "liked"

    return {
        **result,
        "for_you": for_you,
        "discovery_items": discovery,
        "for_you_cards": for_you[group_name],
        "discovery_cards": discovery[group_name],
        "recommendations": result[group_name],
        "search_results": result[group_name] if search_active else [],
        "search_active": search_active,
        "personalized_recommendations": for_you[group_name],
        "history_topics": topics,
        "active_history_topic": focus,
        "history": {**personalized["history"], "searches": searches},
        "recurring": personalized["recurring"],
        "context": {**personalized["context"], "q": options["q"]},
        "authenticated": bool(user),
        "profile": _public_profile(profile, market_profile),
        "location_enabled": bool(point),
        "location_consent": permission,
        "weather_enabled": weather_enabled,
        "filters": {**options, "moment": search_options["moment"]},
        "channels": CHANNELS,
        "moments": MOMENTS,
        "today": at.date().isoformat(),
        "last_day": (at.date() + timedelta(days=30)).isoformat(),
    }


def _private(response):
    response.headers["Cache-Control"] = "private, no-store"
    response.vary.add("Cookie")
    return response


@bp.get("/recomendaciones")
def index():
    return _private(make_response(render_template("recommendations.html", **_payload())))


@bp.get("/api/recomendaciones")
def api():
    return _private(jsonify(_payload()))


@bp.post("/api/recomendaciones/contexto")
def location():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(success=False, error="Envía un objeto JSON."), 400
    at = now()
    if data.get("clear") is True:
        session[SESSION_CONTEXT] = {"disabled": True}
        return _private(jsonify(success=True, location_enabled=False, weather_enabled=False))

    weather_enabled = data.get("weather", False)
    if not isinstance(weather_enabled, bool):
        return jsonify(success=False, error="Indica si autorizas la consulta del clima."), 400
    if "lat" in data or "lng" in data:
        lat, lng = data.get("lat"), data.get("lng")
        point = None
        if type(lat) in (float, int) and type(lng) in (float, int) and -90 <= lat <= 90 and -180 <= lng <= 180:
            point = normalize_coordinates(lat, lng)
    else:
        user = fresh_session_user()
        point, _, _ = _location((g.account_record.get("profile") or {}) if user else {}, at)
    if point is None:
        return jsonify(success=False, error="Indica una ubicación válida."), 400
    until = (at + timedelta(hours=4)).isoformat()
    session[SESSION_CONTEXT] = {"lat": point[0], "lng": point[1], "weather": weather_enabled, "until": until}
    return _private(jsonify(success=True, location_enabled=True, weather_enabled=weather_enabled))


@bp.post("/api/recomendaciones/interaccion")
def interaction():
    user = fresh_session_user()
    if not user:
        return jsonify(success=False, error="Inicia sesión para guardar tu actividad."), 401
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(success=False, error="Envía un objeto JSON."), 400
    token, action = data.get("token"), data.get("action")
    if not isinstance(token, str) or len(token) > 700 or not isinstance(action, str) or action not in (*ACTIONS, "undo"):
        return jsonify(success=False, error="La interacción no es válida."), 400
    try:
        uid, key, *details = _signer().loads(token, max_age=86400)
        if uid != user["id"] or not isinstance(key, str) or not CARD_KEY.fullmatch(key):
            raise ValueError
        dish_id = None
        if details:
            dish_id, = details
            if not key.startswith("experience-") or type(dish_id) is not int or dish_id <= 0:
                raise ValueError
    except (BadSignature, TypeError, ValueError):
        return jsonify(success=False, error="Actualiza las recomendaciones antes de guardar."), 400

    with document_transaction() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (f"phase7-feedback:{uid}",))
        existing = Repo.get_by_id(COLLECTION, uid, for_update=True) or {}
        items = dict(existing.get("items") or {})
        signals = dict(existing.get("signals") or {})
        signal = dict(signals.get(key) or {})
        previous = items.get(key)
        state = (previous or ACTIONS[action]) if action == "view" else ACTIONS.get(action)
        if state != previous or action == "view" or (state and dish_id and dish_id != signal.get("dish_id")):
            timestamp = now().isoformat()
            if action == "view":
                signal["views"] = min(VIEW_LIMIT, (signal.get("views") or 0) + 1)
                signal["last_seen"] = timestamp
            signal["updated_at"] = timestamp
            if dish_id:
                signal["dish_id"] = dish_id
            signals[key] = signal
            items.pop(key, None)
            if state:
                items[key] = state
            elif not signal.get("views"):
                signals.pop(key)
            # Keep older items even when they were stored before view counters.
            previous_order = existing.get("recent") or []
            ordered = set(previous_order)
            older_items = [item for item in dict.fromkeys([*items, *signals]) if item not in ordered]
            recent = [*older_items, *previous_order]
            recent = [item for item in recent if item != key and (item in items or item in signals)]
            if key in items or key in signals:
                recent.append(key)
            recent = recent[-FEEDBACK_LIMIT:]
            saved = {"items": {item: items[item] for item in recent if item in items},
                     "signals": {item: signals[item] for item in recent if item in signals},
                     "recent": recent}
            if existing:
                Repo.update(COLLECTION, uid, saved)
            else:
                Repo.create(COLLECTION, {"id": uid, **saved})
    return _private(jsonify(success=True, state=state, liked=state == "liked"))
