"""Context, discovery and explainable intelligence using existing commerce records."""
from collections import Counter, defaultdict
from datetime import timedelta
import json
import secrets

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
from database.repository import PostgresDocumentRepository as Repo, document_transaction
from logic.context import MOODS, MOMENTS, TAGS, contextualize
from logic.market import MarketError, compatible, integer, money, now, words, forecast, recipe_cost
from logic.market_discovery import discover
from models.market import catalog, records, food_preferences, kitchen, lock_business
from models.restaurant import RestaurantModel
from models.user import UserModel
from models.notification import NotificationModel
from views.market import identity, validation
from utils.security import normalize_text

bp = Blueprint("ecosystem", __name__, url_prefix="/experiencias")
bp.register_error_handler(MarketError, validation)


@bp.get('/escena')
def food_scene():
    from flask import jsonify
    user = session.get('user') or {}
    profile = food_preferences(UserModel.get_by_id(user['id'])) if user else {}
    history = records('market_orders', uid=user['id']) if user else []
    choices, _ = discover(catalog(), {}, profile, history)
    favorites = {r.get('restaurant_id') for r in records('favorites', user_id=user['id'])} if user else set()
    choices.sort(key=lambda row: (row['rid'] not in favorites, -row.get('score', 0)))
    choice = next((row for row in choices if row.get('photo_id')), None)
    if not choice:
        return jsonify(photo=None, model=None)
    response = jsonify(name=choice['name'], photo=url_for('market.offer_photo', oid=choice['id']),
                       model=url_for('ecosystem.dish_model', oid=choice['id']) if choice.get('model_id') else None)
    response.headers['Cache-Control'] = 'private, no-store'
    return response


def current_context():
    context = session.get("food_context") or {}
    if context.get("until", "") < now().isoformat():
        context = {}
    return context


@bp.get("/")
def home():
    user = session.get("user") or {}
    prefs = food_preferences(UserModel.get_by_id(user["id"])) if user else {}
    history = records("market_orders", uid=user["id"]) if user else []
    choices, filters = discover(catalog(), request.args, prefs, history)
    context = current_context()
    weather = None
    if context.get("weather") and session.get("user_lat") is not None:
        from utils.weather import conditions
        weather = conditions(session["user_lat"], session.get("user_lng"))
    choices = contextualize(choices, context, weather, history)
    return render_template("ecosystem/home.html", rows=choices[:24], moods=MOODS, moments=MOMENTS,
                           context=context, weather=weather, filters=filters)


@bp.post("/contexto")
def context():
    if request.form.get("action") == "clear":
        session.pop("food_context", None)
    else:
        mood, moment = request.form.get("mood",""), request.form.get("moment","")
        if mood and mood not in MOODS or moment and moment not in MOMENTS:
            raise MarketError("Selecciona un estado y una ocasión disponibles.")
        session["food_context"] = {"mood":mood, "moment":moment, "weather":request.form.get("weather") == "on",
                                  "until":(now()+timedelta(hours=4)).isoformat()}
    return redirect(url_for("ecosystem.home"))


@bp.route("/scan", methods=["GET","POST"])
def scan():
    identity()
    draft = None
    matches = []
    if request.method == "POST":
        from views.ai_routes import _rate_limited
        from utils.kitchen_assistant import identify
        if _rate_limited():
            raise MarketError("Espera antes de analizar otra imagen.")
        draft = identify(request.files.get("photo"))
        if draft["vision"]:
            profile = food_preferences(UserModel.get_by_id(identity()["id"]))
            matches, _ = discover(catalog(), {"q":draft["name"]}, profile, [])
    return render_template("ecosystem/scan.html", draft=draft, rows=matches[:6])


@bp.route("/grupos", methods=["GET","POST"])
def groups():
    user = identity()
    if request.method == "POST":
        title = normalize_text(request.form.get("title"), max_length=100)
        if not title:
            raise MarketError("Escribe el nombre del grupo.")
        group = Repo.create("food_groups", {"title":title,"host":user["id"],"members":[user["id"]],
                    "invite":secrets.token_urlsafe(24),"votes":{},"prefs":{},
                    "until":(now()+timedelta(days=7)).isoformat()})
        return redirect(url_for("ecosystem.group",gid=group["id"]))
    return render_template("ecosystem/groups.html", groups=records("food_groups",members=[user["id"]]))


@bp.post("/grupos/unirse")
def join_group():
    user = identity()
    invite = request.form.get("invite","")[:80]
    matching = records("food_groups",invite=invite)
    if not matching:
        abort(404)
    with document_transaction():
        group = Repo.get_by_id("food_groups", matching[0]["id"], for_update=True)
        if group["until"] <= now().isoformat():
            raise MarketError("La invitación caducó o el grupo está completo.")
        if user["id"] not in group["members"]:
            if len(group["members"]) >= 20:
                raise MarketError("El grupo está completo.")
            Repo.update("food_groups", group["id"], {"members":group["members"]+[user["id"]], "votes":{}})
    return redirect(url_for("ecosystem.group",gid=group["id"]))


def group_options(group):
    options = catalog()
    complete = all(str(uid) in group["prefs"] for uid in group["members"])
    if not complete:
        return []
    for uid in group["members"]:
        prefs = food_preferences(UserModel.get_by_id(uid))
        local = group["prefs"][str(uid)]
        prefs["avoid"] = list(set(prefs["avoid"]) | set(local["avoid"]))
        options, _ = discover(options, {"budget":str(local["budget"]/100)}, prefs, [])
    return [r for r in options if r["available"] >= len(group["members"])]


@bp.route("/grupos/<int:gid>", methods=["GET","POST"])
def group(gid):
    user = identity()
    with document_transaction():
        group = Repo.get_by_id("food_groups",gid,for_update=request.method=="POST")
        if not group or user["id"] not in group["members"]:
            abort(404)
        if request.method == "POST":
            if group["until"] <= now().isoformat():
                raise MarketError("El grupo ha finalizado.")
            if request.form.get("action") == "preferences":
                prefs = dict(group["prefs"])
                prefs[str(user["id"])] = {"budget":money(request.form.get("budget")), "avoid":words(request.form.get("avoid","")[:200])}
                group = Repo.update("food_groups",gid,{"prefs":prefs,"votes":{}})
            elif request.form.get("action") == "vote":
                offer = integer(request.form.get("offer"),1)
                if offer not in {r["id"] for r in group_options(group)}:
                    raise MarketError("Esta oferta ya no cumple las condiciones del grupo.")
                votes = dict(group["votes"])
                votes[str(user["id"])] = offer
                group = Repo.update("food_groups",gid,{"votes":votes})
            else:
                raise MarketError("Selecciona una acción válida.")
    choices = group_options(group)
    votes = Counter(group["votes"].values())
    choices.sort(key=lambda r:(-votes[r["id"]],r["price"],r["id"]))
    return render_template("ecosystem/group.html", group=group, rows=choices, votes=votes,
                           mine=group["prefs"].get(str(user["id"]),{}), host=user["id"]==group["host"])


@bp.get("/negocio/<int:rid>")
def business(rid):
    from views.market_kitchen import authorize
    restaurant = authorize(rid)
    store = kitchen(rid)
    orders = records("market_orders",rid=rid)
    paid = [o for o in orders if o["state"]=="Entregado" and o.get("paid") and not o.get("refunded")]
    clients = defaultdict(list)
    for order in paid:
        clients[order["uid"]].append(order)
    segments = Counter()
    for uid, purchases in clients.items():
        last = max(p["day"] for p in purchases)
        segment = "Inactivo" if last < (now().date()-timedelta(days=30)).isoformat() else "Frecuente" if len(purchases)>=3 else "Nuevo"
        segments[segment] += 1
    offers = records("market_offers",rid=rid)
    tomorrow = now().date()+timedelta(days=1)
    recommendations = []
    for offer in offers:
        cost = recipe_cost(offer["recipe"],store["pantry"])
        forecasted = forecast(paid,offer["dish_id"],tomorrow)
        recommendations.append({"id":offer["id"],"name":offer["name"],"cost":cost,
            "suggested":(cost*100+69)//70 if cost is not None else None, "forecast":forecasted,
            "ingredients":list(offer["recipe"])})
    return render_template("ecosystem/business.html", business=restaurant, store=store, segments=segments,
                suggestions=recommendations, orders=[o for o in orders if o["state"] not in {"Entregado","Cancelado"}],
                income=sum(o["total"] for o in paid if o["day"]==now().date().isoformat()),
                rescued=sum(l["qty"] for o in paid for l in o["lines"] if l.get("saving",0)>0))


@bp.post("/negocio/<int:rid>/campana")
def campaign(rid):
    from views.market_kitchen import authorize
    with document_transaction():
        lock_business(rid)
        restaurant = authorize(rid,owner_only=True)
        message = normalize_text(request.form.get("message"), max_length=300)
        if not message:
            raise MarketError("Escribe la promoción que deseas comunicar.")
        segment = request.form.get("segment")
        if segment not in {"Todos","Frecuente","Inactivo","Nuevo"}:
            raise MarketError("Selecciona un segmento válido.")
        history = records("market_orders",rid=rid,state="Entregado",paid=True)
        clients = defaultdict(list)
        for order in history:
            if not order.get("refunded"):
                clients[order["uid"]].append(order)
        sent = 0
        for uid, purchases in clients.items():
            user = UserModel.get_by_id(uid) or {}
            if not UserModel.is_active(user) or not (user.get("profile") or {}).get("promotions_opt_in"):
                continue
            last = max(p["day"] for p in purchases)
            tag = "Inactivo" if last < (now().date()-timedelta(days=30)).isoformat() else "Frecuente" if len(purchases)>=3 else "Nuevo"
            if segment != "Todos" and tag != segment:
                continue
            log = records("campaign_deliveries",rid=rid,uid=uid)
            if any(r["created"] > (now()-timedelta(days=7)).isoformat() for r in log):
                continue
            NotificationModel.create_notification(uid,restaurant["name"],message,link=f"/mercado/?negocio={rid}")
            Repo.create("campaign_deliveries",{"rid":rid,"uid":uid,"created":now().isoformat(),"segment":tag})
            sent += 1
    flash(f"Promoción publicada en {sent} bandejas con consentimiento.","success")
    return redirect(url_for("ecosystem.business",rid=rid))


@bp.get("/ciudad")
def city():
    identity("admin")
    businesses = RestaurantModel.all()
    by_id = {r["id"]:r for r in businesses}
    supply = Counter(r.get("district") or "Sin distrito" for r in businesses if r.get("verified"))
    demand = Counter(by_id.get(o["rid"],{}).get("district") or "Sin distrito" for o in Repo.all("market_orders"))
    campaigns = records("campaign_deliveries")
    return render_template("ecosystem/city.html", zones=sorted(supply.keys()|demand.keys()), supply=supply,demand=demand,
                           campaigns=len(campaigns))


@bp.route("/publicaciones", methods=["GET","POST"])
def publications():
    identity("admin")
    if request.method == "POST":
        from utils.audit import record_event
        oid = integer(request.form.get("offer"),1)
        state = request.form.get("state")
        note = normalize_text(request.form.get("note"),max_length=500)
        if state not in {"approved","rejected"} or len(note)<5:
            raise MarketError("Indica una decisión y su motivo.")
        with document_transaction():
            initial = Repo.get_by_id("market_offers",oid)
            if not initial:
                abort(404)
            lock_business(initial["rid"])
            Repo.update("market_offers",oid,{"review_state":state,"review_note":note})
            record_event("OFFER_REVIEW",resource_type="oferta",resource_id=oid,metadata={"state":state})
        return redirect(url_for("ecosystem.publications"))
    return render_template("ecosystem/publications.html",offers=Repo.all("market_offers"))


@bp.post("/negocio/<int:rid>/modelo")
def upload_model(rid):
    import base64
    from utils.dish_model import validate_glb
    from views.market_kitchen import authorize
    authorize(rid,owner_only=True)
    oid = integer(request.form.get("offer"),1)
    file = request.files.get("model")
    if not file:
        raise MarketError("Selecciona el modelo de tu plato.")
    raw = validate_glb(file.read(1500001))
    label = normalize_text(request.form.get("description"),max_length=200)
    if not label or request.form.get("confirmed") != "on":
        raise MarketError("Describe el modelo y confirma que representa tu plato.")
    with document_transaction():
        lock_business(rid)
        authorize(rid,owner_only=True)
        offer = Repo.get_by_id("market_offers",oid,for_update=True)
        if not offer or offer["rid"] != rid:
            abort(404)
        model = Repo.create("dish_models",{"rid":rid,"data":base64.b64encode(raw).decode(),"description":label})
        Repo.update("market_offers",oid,{"model_id":model["id"],"review_state":"pending"})
    flash("Modelo guardado. La oferta requiere revisión administrativa.","success")
    return redirect(url_for("ecosystem.business",rid=rid))


@bp.get("/modelos/<int:oid>")
def dish_model(oid):
    import base64
    from flask import Response
    offer = Repo.get_by_id("market_offers",oid)
    restaurant = RestaurantModel.get_by_id(offer["rid"]) if offer else None
    reviewing = (session.get("user") or {}).get("role") == "admin"
    if not offer or not restaurant:
        abort(404)
    if not reviewing and (not restaurant.get("verified") or offer.get("review_state","approved") != "approved"):
        abort(404)
    model = Repo.get_by_id("dish_models",offer["model_id"]) if offer.get("model_id") else None
    if not model or model["rid"] != offer["rid"]:
        abort(404)
    return Response(base64.b64decode(model["data"]),mimetype="model/gltf-binary",
                    headers={"Cache-Control":"private,max-age=60","X-Content-Type-Options":"nosniff"})


@bp.post("/interaccion/<int:oid>")
def interaction(oid):
    event = request.form.get("event")
    if event not in {"model","ar","context_click"}:
        abort(400)
    offer = next((r for r in catalog() if r["id"]==oid),None)
    if not offer:
        abort(404)
    if event in {"model","ar"} and not offer.get("model_id"):
        abort(400)
    visitor = session.get("experience_visit") or secrets.token_hex(16)
    session["experience_visit"] = visitor
    with document_transaction() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))",(visitor,))
        if not records("experience_events",visitor=visitor,offer=oid,event=event):
            Repo.create("experience_events",{"visitor":visitor,"offer":oid,"event":event,"day":now().date().isoformat()})
    return "",204


@bp.get("/recompensas")
def rewards():
    uid = identity()["id"]
    orders = [o for o in records("market_orders",uid=uid,state="Entregado",paid=True) if not o.get("refunded")]
    shops = {o["rid"] for o in orders}
    dishes = {line["dish_id"] for o in orders for line in o["lines"]}
    from models.market import reward_balance
    return render_template("ecosystem/rewards.html", purchases=len(orders), shops=len(shops), dishes=len(dishes),
        balances=[{"name":(RestaurantModel.get_by_id(rid) or {}).get("name","Negocio"),"rid":rid,
                   "points":reward_balance(uid,rid),"benefit":kitchen(rid).get("reward",0)} for rid in shops])
