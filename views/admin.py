from collections import Counter
from analytics.management import order_report, registrations, reporting_period, scoped_records, timeline
from models.commerce_settings import commerce_settings, save_settings
from utils.moderation_explain import estado_pendiente
from logic.market import now
from flask import (
    abort,
    Blueprint,
    render_template,
    session,
    redirect,
    url_for,
    jsonify,
    request,
    flash,
)
from models.restaurant import RestaurantModel
from models.user import UserModel
from models.favorite import FavoriteModel
from models.dish import DishModel
from models.daily_menu import DailyMenuModel
from models.review import ReviewModel
from models.category import CategoryModel
from models.notification import NotificationModel
from config import Config
from database.repository import document_transaction
from utils.security import normalize_text, fresh_session_user
from utils.audit import record_event, AuditEventModel
from analytics.metrics import build_bi_snapshot
from functools import wraps
import datetime
import logging

logger = logging.getLogger(__name__)

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

SERVICE_MODES = {
    "dine_in_only",
    "dine_in_and_delivery",
    "delivery_only",
    "pickup_only",
}


def _restaurant_service_mode(restaurant):
    """Devuelve la modalidad guardada o infiere una para registros antiguos."""
    service_mode = normalize_text(restaurant.get("service_mode"), max_length=40).lower()
    if service_mode in SERVICE_MODES:
        return service_mode

    features = restaurant.get("features", [])
    if isinstance(features, list) and any(
        normalize_text(feature, max_length=100).lower() == "delivery"
        for feature in features
    ):
        return "dine_in_and_delivery"
    return "dine_in_only"


@admin_bp.app_context_processor
def inject_sidebar_restaurants():
    user = session.get("user") or {}
    role = user.get("role")
    if role == "admin":
        return {"restaurants": RestaurantModel.all()}
    if role == "business_owner":
        return {"restaurants": RestaurantModel.get_by_owner(user.get("id"))}
    return {}


def _clean_list(value, max_items=30, max_length=80):
    values = value if isinstance(value, list) else str(value or "").split(",")
    return [
        normalize_text(item, max_length=max_length)
        for item in values[:max_items]
        if normalize_text(item, max_length=max_length)
    ]


def _clean_restaurant_update(source):
    """Allowlist de campos editables de un restaurante."""
    payload = {}
    name = normalize_text(source.get("name"), max_length=160)
    district = normalize_text(source.get("district"), max_length=80)
    if name:
        payload["name"] = name
    if district:
        payload["district"] = district
    if source.get("category_id") not in (None, ""):
        try:
            payload["category_id"] = int(source.get("category_id"))
        except (TypeError, ValueError):
            raise ValueError("category_id inválido")
    for field, minimum, maximum in (
        ("lat", -90, 90),
        ("lng", -180, 180),
        ("avg_price", 0, 100000),
        ("rating", 0, 5),
    ):
        if source.get(field) not in (None, ""):
            try:
                numeric = float(source.get(field))
            except (TypeError, ValueError):
                raise ValueError(f"{field} inválido")
            if not minimum <= numeric <= maximum:
                raise ValueError(f"{field} fuera de rango")
            payload[field] = round(numeric, 4 if field in ("lat", "lng") else 2)
    for field, max_length in (
        ("open_time", 5),
        ("close_time", 5),
        ("image", 500),
        ("description", 2000),
        ("address", 300),
        ("phone", 40),
        ("promo", 500),
    ):
        if field in source:
            payload[field] = normalize_text(source.get(field), max_length=max_length)
    if "service_mode" in source:
        service_mode = normalize_text(source.get("service_mode"), max_length=40).lower()
        if service_mode not in SERVICE_MODES:
            raise ValueError("Selecciona una modalidad de atención válida")
        payload["service_mode"] = service_mode
    for field in ("tags", "features", "dietary_restrictions"):
        if field in source:
            payload[field] = _clean_list(
                source.get(field), max_items=50, max_length=100
            )
    if source.get("district_only") == "on":
        payload.update(address="", lat=None, lng=None)
    return payload


# ============================================
# DECORADORES DE AUTENTICACIÓN
# ============================================


def admin_required(f):
    """Decorador que solo permite acceso a administradores"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = fresh_session_user()
        if not user:
            flash("Debes iniciar sesión", "warning")
            return redirect(url_for("auth.login"))
        if user.get("role") != "admin":
            flash("Acceso denegado. Se requieren permisos de administrador.", "error")
            return redirect(url_for("main.index"))

        return f(*args, **kwargs)

    return decorated_function


def admin_or_owner_required(f):
    """Decorador que permite acceso a admin y empresarios (dueños de restaurantes)"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = fresh_session_user()
        if not user:
            flash("Debes iniciar sesión", "warning")
            return redirect(url_for("auth.login"))
        role = user.get("role", "user")

        if role not in ["admin", "business_owner"]:
            flash(
                "Acceso denegado. Se requieren permisos de administrador o empresario.",
                "error",
            )
            return redirect(url_for("main.index"))

        return f(*args, **kwargs)

    return decorated_function


# ============================================
# DASHBOARD
# ============================================


@admin_bp.route("/dashboard")
@admin_or_owner_required
def dashboard():
    if session["user"]["role"] == "business_owner":
        return redirect(url_for("owner.dashboard"))
    today = now().date()
    try:
        start, end = reporting_period(request.args, today)
    except ValueError as exc:
        flash(exc.args[0], "error")
        return redirect(url_for("admin.dashboard"))
    categories = CategoryModel.all()
    cid = request.args.get("category", "")
    businesses = [r for r in RestaurantModel.all() if not cid or str(r.get("category_id")) == cid]
    by_id = {r["id"]: r for r in businesses}
    ids = list(by_id)
    orders = scoped_records("market_orders", ids)
    report = order_report(orders, start, end, today)
    names = {str(c["id"]): c["name"] for c in categories}
    frequency = Counter(names.get(str(by_id[o["rid"]].get("category_id")), "Sin categoría") for o in report["orders"])
    traffic = Counter(by_id[o["rid"]]["name"] for o in report["orders"])
    district = Counter(r.get("district") or "Sin distrito" for r in businesses)
    cases = scoped_records("market_cases", ids)
    claims = [c for c in cases if c["kind"] == "Reclamo" and c["state"] not in {"Resuelto", "Cerrado", "Aceptado", "Desestimado"}]
    signals = [c for c in cases if c["kind"] == "Señal de revisión" and c["state"] == "Abierto"]
    pending = [r for r in businesses if estado_pendiente(r)]
    with document_transaction() as conn:
        roles = dict((r["role"], r["n"]) for r in conn.execute(
            "SELECT payload->>'role' AS role,count(*) AS n FROM public.app_records WHERE collection='users' GROUP BY role"))
        visits = conn.execute(
            "SELECT count(*) AS viewed, count(*) FILTER (WHERE v.payload->>'clicked'='true') AS clicked, "
            "count(*) FILTER (WHERE v.payload->>'ordered'='true') AS ordered "
            "FROM public.app_records v JOIN public.app_records o ON o.collection='market_offers' "
            "AND o.id::text=v.payload->>'offer' WHERE v.collection='market_views' AND o.payload->>'rid'=ANY(%s) "
            "AND v.payload->>'day' BETWEEN %s AND %s", ([str(i) for i in ids], start.isoformat(), end.isoformat())).fetchone()
    unsettled = [o for o in orders if o.get("payment_incident") or not o.get("paid") and not o.get("refunded") and (
        o["state"] == "Entregado" or (o["state"] == "Recibido" and o.get("method") == "Digital"
        and o.get("created", "")[:10] < today.isoformat()))]
    charts = [
        ("Acciones administrativas", timeline(registrations("audit_events", start, end), start, end)),
        ("Pedidos recibidos", timeline(report["activity"], start, end)),
        ("Altas de usuarios en la plataforma", timeline(registrations("users", start, end), start, end)),
        ("Negocios incorporados", timeline(registrations("restaurants", start, end, ids), start, end)),
        ("Demanda por categoría", frequency.most_common(6)), ("Negocios con más pedidos", traffic.most_common(6)),
        ("Negocios por distrito", district.most_common(6)),
        ("Recomendaciones", [("Vistas", visits["viewed"]), ("Clics", visits["clicked"]), ("Con pedido", visits["ordered"])])]
    return render_template("admin/dashboard.html", report=report, charts=charts, total_users=sum(roles.values()),
                           owners=roles.get("business_owner", 0), published=sum(bool(r.get("verified")) for r in businesses),
                           pending=pending, claims=claims, signals=signals, start=start, end=end,
                           categories=categories, cid=cid, events=recent_audit(5), unsettled=unsettled)


def recent_audit(limit):
    with document_transaction() as conn:
        rows = conn.execute("SELECT payload->>'action' AS action,payload->>'resource_type' AS resource,"
                            "payload->>'resource_id' AS subject,created_at AT TIME ZONE 'America/Lima' AS stamp "
                            "FROM public.app_records WHERE collection='audit_events' ORDER BY created_at DESC,id DESC LIMIT %s", (limit,))
        return list(rows)


@admin_bp.get("/operaciones")
@admin_required
def operations():
    state = request.args.get("estado", "")
    payment = request.args.get("pago", "")
    states = ("Recibido", "Preparando", "Listo", "Entregado", "Cancelado", "Confirmado", "En reparto")
    payments = ("Pendiente", "Pagado", "Reembolsado")
    if state and state not in states or payment and payment not in payments:
        abort(400)
    page = max(1, request.args.get("page", 1, type=int))
    with document_transaction() as conn:
        rows = list(conn.execute(
            "WITH orders AS (SELECT id,payload->>'state' AS state,payload->>'business' AS business,"
            "payload->>'total' AS total,payload->>'rid' AS rid,payload->>'method' AS method,"
            "CASE WHEN payload->>'refunded'='true' THEN 'Reembolsado' WHEN payload->>'paid'='true' THEN 'Pagado' "
            "ELSE 'Pendiente' END AS payment FROM public.app_records WHERE collection='market_orders') "
            "SELECT * FROM orders WHERE (%s='' OR state=%s) AND (%s='' OR payment=%s) ORDER BY id DESC LIMIT 31 OFFSET %s",
            (state,state,payment,payment,(page-1)*30)))
    return render_template("admin/operations.html", rows=rows[:30], more=len(rows)>30, page=page,
                           state=state,payment=payment,states=states,payments=payments)


@admin_bp.get("/operaciones/<int:oid>")
@admin_required
def operation_detail(oid):
    with document_transaction() as conn:
        item = conn.execute(
            "SELECT payload->>'business' AS business,payload->>'state' AS state,payload->>'method' AS method,"
            "payload->>'paid' AS paid,payload->>'refunded' AS refunded,payload->>'total' AS total,"
            "payload->'history' AS history FROM public.app_records WHERE collection='market_orders' AND id=%s",
            (oid,)).fetchone()
    if not item:
        abort(404)
    return render_template("admin/operation_detail.html", item=item,oid=oid)

@admin_bp.route("/controles", methods=["GET","POST"])
@admin_required
def controls():
    if request.method == "POST":
        threshold = request.form.get("threshold", type=int)
        diets = list(dict.fromkeys(normalize_text(d, max_length=60) for d in request.form.get("diets","").splitlines() if d.strip()))
        if threshold is None or not 0 <= threshold <= 100 or not 1 <= len(diets) <= 30:
            flash("Ingresa un umbral entre 0 y 100 y entre 1 y 30 etiquetas alimentarias.", "error")
        else:
            with document_transaction():
                save_settings(threshold, diets)
                record_event("ADMIN_COMMERCE_SETTINGS", resource_type="commerce_settings", resource_id=1)
            flash("Configuración comercial actualizada.", "success")
        return redirect(url_for("admin.controls"))
    return render_template("admin/controls.html", settings=commerce_settings(), events=recent_audit(50))

# ============================================
# GESTIÓN DE RESTAURANTES
# ============================================


@admin_bp.route("/restaurants")
@admin_or_owner_required
def restaurants():
    """Gestión de restaurantes - Adaptado según rol"""
    user = session.get("user")
    user_id = user.get("id")
    role = user.get("role")

    if role == "admin":
        restaurants = RestaurantModel.all()
    else:
        restaurants = RestaurantModel.get_by_owner(user_id)

    categories = CategoryModel.all()

    cat_dict = {cat["id"]: cat["name"] for cat in categories}

    now = datetime.datetime.now().strftime("%H:%M")
    for r in restaurants:
        r["category_name"] = cat_dict.get(r.get("category_id"), "Sin categoría")
        r["is_open"] = r.get("open_time") <= now <= r.get("close_time")
        r["service_mode"] = _restaurant_service_mode(r)

    districts = getattr(
        Config,
        "DISTRITOS",
        ["Trujillo", "Victor Larco", "La Esperanza", "Huanchaco", "Moche"],
    )

    if role == "business_owner":
        return render_template(
            "owner/restaurants.html",
            restaurants=restaurants,
            categories=categories,
            districts=districts,
            total_pages=max(1, (len(restaurants) + 9) // 10),
            role=role,
            is_admin=False,
        )

    return render_template(
        "admin/restaurants.html",
        restaurants=restaurants,
        categories=categories,
        districts=districts,
        total_pages=max(1, (len(restaurants) + 9) // 10),
        role=role,
        is_admin=(role == "admin"),
    )


@admin_bp.route("/restaurant/analyze-file", methods=["POST"])
@admin_or_owner_required
def analyze_restaurant_upload():
    """
    Analiza documentos de restaurantes mediante IA.

    Detecta categorías existentes y propone nuevas.
    """

    from utils.restaurant_import_ai import analyze_restaurant_file

    uploaded = request.files.get("file")

    if not uploaded:
        return jsonify({"success": False, "error": "Selecciona un archivo."}), 400

    try:
        # Analizar documento
        extracted, provider = analyze_restaurant_file(uploaded)

        # Obtener distritos
        districts = getattr(
            Config,
            "DISTRITOS",
            ["Trujillo", "Victor Larco", "La Esperanza", "Huanchaco", "Moche"],
        )

        # ==================================
        # DETECTAR CATEGORÍA
        # ==================================

        category_name = extracted.pop("category", None)

        if category_name:

            category_name = normalize_text(category_name, max_length=100)

            # Buscar categoría registrada
            match = CategoryModel.get_by_name(category_name)

            if match:
                extracted["category_id"] = match["id"]

            else:
                # Categoría nueva detectada por IA
                extracted["category_suggestion"] = category_name

        # ==================================
        # VALIDAR DISTRITO
        # ==================================

        district_name = extracted.get("district")

        if district_name:

            district_name = normalize_text(district_name, max_length=100)

            match = next(
                (
                    district
                    for district in districts
                    if normalize_text(district, max_length=100).casefold()
                    == district_name.casefold()
                ),
                None,
            )

            if match:
                extracted["district"] = match

            else:
                extracted.pop("district", None)

                extracted["district_suggestion"] = district_name

        # ==================================
        # RESPUESTA AL FRONTEND
        # ==================================

        return jsonify({"success": True, "data": extracted, "provider": provider})

    except ValueError:
        return jsonify({"success": False, "error": "No se pudo leer el archivo. Verifica su formato y contenido."}), 400

    except Exception:
        logger.exception("Error analizando archivo de restaurante")

        return (
            jsonify(
                {
                    "success": False,
                    "error": (
                        "No fue posible analizar el archivo. "
                        "Revisa la configuración de IA."
                    ),
                }
            ),
            503,
        )


@admin_bp.route("/api/categories", methods=["POST"])
@admin_or_owner_required
def create_dynamic_category():
    """
    Permite crear categorías dinámicas.

    Roles permitidos:
    - admin
    - business_owner
    """

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({"success": False, "error": "Debes enviar un objeto JSON."}), 400

    name = data.get("name")
    if set(data) != {"name"} or not isinstance(name, str):
        return jsonify({"success": False, "error": "Envía únicamente el nombre de la categoría."}), 400

    try:
        with document_transaction():
            saved, created = CategoryModel.create_dynamic(name)
            if created:
                record_event("ADMIN_CATEGORY_CREATE", resource_type="category", resource_id=saved["id"])
        return jsonify(
            {
                "success": True,
                "created": created,
                "category": {"id": saved["id"], "name": saved["name"]},
            }
        ), (201 if created else 200)

    except ValueError:
        return jsonify({"success": False, "error": "Introduce un nombre válido de 2 a 80 caracteres."}), 400

    except Exception:
        logger.exception("Error creando categoría dinámica")

        return (
            jsonify({"success": False, "error": "No se pudo crear la categoría."}),
            500,
        )


@admin_bp.route("/restaurant/new", methods=["GET", "POST"])
@admin_or_owner_required
def new_restaurant():
    """Crear nuevo restaurante - Asigna dueño automáticamente"""
    discovery_candidate = None
    candidate_id = request.values.get('discovery_candidate_id')
    if candidate_id:
        from models.discovery import CandidateModel
        try:
            discovery_candidate = CandidateModel.get_by_id(int(candidate_id))
        except ValueError:
            abort(404)
        if (not discovery_candidate or discovery_candidate.get('status') != 'claimed'
                or discovery_candidate.get('owner_id') != session['user']['id']):
            abort(404)
        if discovery_candidate.get('commercial_restaurant_id'):
            return redirect(url_for('admin.edit_restaurant', id=discovery_candidate['commercial_restaurant_id']))
    if request.method == "POST":
        try:
            data = _clean_restaurant_update(request.form)
        except ValueError as error:
            flash(str(error), "error")
            return redirect(url_for("admin.new_restaurant"))
        data.update(
            {
                "owner_id": session["user"]["id"],
                "owner_name": (session.get("user", {}).get("profile") or {}).get("name")
                or session["user"].get("username"),
            }
        )

        if (
            not data.get("name")
            or not data.get("category_id")
            or not data.get("district")
            or not data.get("service_mode")
        ):
            flash(
                "Completa los campos requeridos, incluida la modalidad de atención",
                "error",
            )
            return redirect(url_for("admin.new_restaurant"))

        with document_transaction() as conn:
            if discovery_candidate:
                from models.discovery import CandidateModel, lock
                lock(conn)
                latest = CandidateModel.get_by_id(discovery_candidate['id'])
                if (not latest or latest.get('status') != 'claimed'
                        or latest.get('owner_id') != session['user']['id']
                        or latest.get('commercial_restaurant_id')):
                    abort(409)
                data.update(business_id=latest['business_id'], branch_id=latest['branch_id'],
                            discovery_candidate_id=latest['id'])
                data['verified'] = False
            restaurant = RestaurantModel.create(data)
            if discovery_candidate:
                CandidateModel.update(discovery_candidate['id'], {'commercial_restaurant_id': restaurant['id']})
            record_event("ADMIN_RESTAURANT_CREATE", resource_type="restaurant", resource_id=restaurant["id"])
            from models.communication import admins, notify
            notify([a["id"] for a in admins()], "Nuevo negocio por verificar", restaurant["name"],
                   url_for("admin.moderation_dashboard"))

        flash("Restaurante creado exitosamente", "success")
        return redirect(url_for("admin.restaurants"))

    categories = CategoryModel.all()

    districts = getattr(
        Config,
        "DISTRITOS",
        ["Trujillo", "Victor Larco", "La Esperanza", "Huanchaco", "Moche"],
    )

    return render_template(
        "admin/restaurant_form.html", categories=categories, districts=districts,
        discovery_candidate=discovery_candidate
    )


@admin_bp.route("/restaurant/<int:id>/edit", methods=["GET"])
@admin_or_owner_required
def edit_restaurant(id):
    """Página para editar un restaurante"""
    user = session.get("user")
    user_id = user.get("id")
    role = user.get("role")

    if role != "admin" and not RestaurantModel.is_owner(user_id, id):
        flash("No tienes permiso para editar este restaurante", "error")
        return redirect(url_for("admin.restaurants"))

    restaurant = RestaurantModel.get_by_id(id)
    if not restaurant:
        flash("Restaurante no encontrado", "error")
        return redirect(url_for("admin.restaurants"))

    categories = CategoryModel.all()

    districts = getattr(
        Config,
        "DISTRITOS",
        ["Trujillo", "Victor Larco", "La Esperanza", "Huanchaco", "Moche"],
    )

    return render_template(
        "admin/restaurant_form.html",
        restaurant=restaurant,
        categories=categories,
        districts=districts,
    )


@admin_bp.route("/restaurant/<int:id>/update", methods=["POST"])
@admin_or_owner_required
def update_restaurant(id):
    """Actualizar restaurante desde formulario"""
    user = session.get("user")
    user_id = user.get("id")
    role = user.get("role")

    if role != "admin" and not RestaurantModel.is_owner(user_id, id):
        flash("No tienes permiso para editar este restaurante", "error")
        return redirect(url_for("admin.restaurants"))

    restaurant = RestaurantModel.get_by_id(id)
    if not restaurant:
        flash("Restaurante no encontrado", "error")
        return redirect(url_for("admin.restaurants"))

    try:
        data = _clean_restaurant_update(request.form)
    except ValueError as error:
        flash(str(error), "error")
        return redirect(url_for("admin.edit_restaurant", id=id))

    if role != "admin":
        data["owner_id"] = restaurant.get("owner_id")
        data["owner_name"] = restaurant.get("owner_name")

    RestaurantModel.update(id, data)

    flash("Restaurante actualizado exitosamente", "success")
    return redirect(url_for("admin.restaurants"))


@admin_bp.route("/restaurant/<int:id>", methods=["GET", "PUT", "DELETE"])
@admin_or_owner_required
def manage_restaurant(id: int):
    """Obtener, actualizar o eliminar restaurante - Verifica permisos"""
    user = session.get("user")
    user_id = user.get("id")
    role = user.get("role")

    if role != "admin":
        if not RestaurantModel.is_owner(user_id, id):
            return (
                jsonify({"error": "No tienes permiso para gestionar este restaurante"}),
                403,
            )

    if request.method == "GET":
        restaurant = RestaurantModel.get_by_id(id)
        if restaurant:
            return jsonify(restaurant)
        return jsonify({"error": "Restaurante no encontrado"}), 404

    elif request.method == "PUT":
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return (
                jsonify(
                    {"success": False, "error": "El cuerpo debe ser un objeto JSON"}
                ),
                400,
            )
        try:
            allowed = _clean_restaurant_update(data)
        except ValueError as error:
            return jsonify({"success": False, "error": str(error)}), 400
        if not allowed:
            return (
                jsonify({"success": False, "error": "No hay campos actualizables"}),
                400,
            )
        updated = RestaurantModel.update(id, allowed)
        if updated:
            return jsonify({"success": True, "restaurant": updated})
        return jsonify({"success": False, "error": "Restaurante no encontrado"}), 404

    elif request.method == "DELETE":
        with document_transaction():
            deleted = RestaurantModel.delete(id)
            if deleted:
                record_event("ADMIN_RESTAURANT_DELETE", resource_type="restaurant", resource_id=id)
                return jsonify({"success": True})
        return jsonify({"success": False, "error": "Restaurante no encontrado"}), 404


@admin_bp.route("/restaurant/<int:id>/promo", methods=["POST"])
@admin_or_owner_required
def add_promotion(id: int):
    """Agregar promoción a un restaurante - Verifica permisos"""
    user = session.get("user")
    user_id = user.get("id")
    role = user.get("role")

    if role != "admin":
        if not RestaurantModel.is_owner(user_id, id):
            return (
                jsonify({"error": "No tienes permiso para gestionar este restaurante"}),
                403,
            )

    data = request.get_json(silent=True)
    promo = normalize_text(
        data.get("promo") if isinstance(data, dict) else "", max_length=500
    )

    if not promo:
        return jsonify({"error": "Se requiere texto de promoción"}), 400

    restaurant = RestaurantModel.get_by_id(id)

    if not restaurant:
        return jsonify({"error": "Restaurante no encontrado"}), 404

    from models.market import records
    from models.communication import notify
    with document_transaction():
        previous = PostgresDocumentRepository.get_by_id("restaurants", id, for_update=True)
        updated = RestaurantModel.update(id, {"promo": promo}) if previous else None
        if updated and updated.get("verified") and promo != previous.get("promo"):
            favorites = {f["user_id"] for f in records("favorites",restaurant_id=id)}
            subscribers = [u["id"] for u in records("users",profile={"promotions_opt_in":True})
                           if UserModel.is_active(u) and u["id"] in favorites]
            notify(subscribers, f"Promoción en {updated['name']}", promo, url_for("main.detail", restaurant_id=id))

    if updated:
        return jsonify({"success": True, "promo": promo})
    return jsonify({"error": "Error al actualizar"}), 500


# ============================================
# ANALÍTICAS - Solo admin
# ============================================


@admin_bp.route("/analytics")
@admin_required
def analytics_page():
    """Página de analíticas - Solo admin"""
    restaurants = RestaurantModel.all()
    users = UserModel.all()
    favorites = FavoriteModel.all()

    total_favorites = len(favorites)
    avg_rating = (
        sum(r.get("rating", 0) for r in restaurants) / len(restaurants)
        if restaurants
        else 0
    )
    avg_price = (
        sum(r.get("avg_price", 0) for r in restaurants) / len(restaurants)
        if restaurants
        else 0
    )

    recent_activities = []

    if restaurants:
        latest = sorted(restaurants, key=lambda x: x.get("id", 0), reverse=True)[:3]
        for r in latest:
            recent_activities.append(
                {
                    "icon": "plus",
                    "message": f'Se agregó "{r.get("name")}"',
                    "time": "Recientemente",
                }
            )

    if len(recent_activities) < 3:
        recent_activities.append(
            {
                "icon": "heart",
                "message": f"{total_favorites} restaurantes en favoritos",
                "time": "Total",
            }
        )
        recent_activities.append(
            {
                "icon": "star",
                "message": f"Rating promedio: {avg_rating:.1f} ⭐",
                "time": "General",
            }
        )

    return render_template(
        "admin/analytics.html",
        total_restaurants=len(restaurants),
        total_users=len(users),
        avg_rating=round(avg_rating, 1),
        avg_price=round(avg_price, 2),
        total_favorites=total_favorites,
        recent_activities=recent_activities,
    )


@admin_bp.route("/api/analytics")
@admin_required
def analytics_api():
    """API para datos de analíticas (gráficos) - Solo admin"""
    try:
        restaurants = RestaurantModel.all()

        # Cargar categorías para obtener nombres
        categories = CategoryModel.all()

        cat_names = {cat["id"]: cat["name"] for cat in categories}

        # Distribución por categoría (usando nombres legibles)
        cat_dist = {}
        for r in restaurants:
            cat_id = r.get("category_id")
            if cat_id:
                cat_name = cat_names.get(cat_id, f"Categoría {cat_id}")
                cat_dist[cat_name] = cat_dist.get(cat_name, 0) + 1

        # Distribución por distrito
        dist_dist = {}
        for r in restaurants:
            district = r.get("district", "Desconocido")
            dist_dist[district] = dist_dist.get(district, 0) + 1

        # ✅ Precio vs Rating - AHORA INCLUIDO
        price_rating = []
        for r in restaurants:
            price = r.get("avg_price")
            rating = r.get("rating")
            if price is not None and rating is not None:
                price_rating.append(
                    {
                        "price": price,
                        "rating": rating,
                        "name": r.get("name", "Restaurante"),
                    }
                )

        # ✅ Promociones - AHORA INCLUIDO
        with_promo = sum(1 for r in restaurants if r.get("promo"))
        without_promo = len(restaurants) - with_promo

        # Ratings y precios (para los otros gráficos)
        ratings = [
            r.get("rating", 0) for r in restaurants if r.get("rating") is not None
        ]
        prices = [
            r.get("avg_price", 0) for r in restaurants if r.get("avg_price") is not None
        ]

        return jsonify(
            {
                "categories": cat_dist,
                "districts": dist_dist,
                "ratings": ratings,
                "prices": prices,
                "price_rating": price_rating,  # ✅ NUEVO
                "promotions": {  # ✅ NUEVO
                    "with_promo": with_promo,
                    "without_promo": without_promo,
                },
                "total": len(restaurants),
            }
        )

    except Exception as e:
        logger.error(f"Error en analytics_api: {e}")
        return jsonify({"error": "Error interno del servidor."}), 500


@admin_bp.route("/api/bi/overview")
@admin_required
def bi_overview_api():
    """Snapshot BI versionado, derivado de datos existentes y sin PII sensible."""
    try:
        categories = CategoryModel.all()
        snapshot = build_bi_snapshot(
            users=UserModel.all(),
            restaurants=RestaurantModel.all(),
            dishes=DishModel.all(),
            menus=DailyMenuModel.all(),
            favorites=FavoriteModel.all(),
            reviews=ReviewModel.all(),
            audit_events=AuditEventModel.all(),
            categories=categories,
        )
        return jsonify(snapshot)
    except (OSError, ValueError, TypeError):
        logger.exception("Error generando snapshot BI")
        return jsonify({"error": "No se pudo generar el snapshot BI"}), 500


# ============================================
# GESTIÓN DE USUARIOS - Solo admin
# ============================================


@admin_bp.route("/users")
@admin_required
def users():
    """Lista de usuarios - Solo admin"""
    users = UserModel.all()
    role = request.args.get("role")
    if role in {"admin", "business_owner", "user"}:
        users = [u for u in users if u.get("role") == role]
    return render_template("admin/users.html", users=users)


@admin_bp.route("/user/<int:id>", methods=["GET", "PUT", "DELETE"])
@admin_required
def manage_user(id: int):
    """Obtener, actualizar o eliminar usuario con allowlist y auditoría."""
    user = UserModel.get_by_id(id)
    if not user:
        return jsonify({"error": "Usuario no encontrado"}), 404
    actor_id = int(session.get("user_id"))

    def public_user(value):
        result = dict(value)
        result.pop("password", None)
        result.pop("password_hash", None)
        return result

    if request.method == "GET":
        return jsonify(public_user(user))

    if id == actor_id and request.method == "DELETE":
        return (
            jsonify({"error": "No puedes eliminar tu propia cuenta administrativa"}),
            403,
        )

    if request.method == "PUT":
        data = request.get_json(silent=True) or {}
        if not isinstance(data, dict):
            return jsonify({"error": "Payload inválido"}), 400
        allowed = {"username", "role", "status", "profile"}
        unknown = set(data) - allowed
        if unknown:
            return (
                jsonify({"error": "Campos no permitidos", "fields": sorted(unknown)}),
                400,
            )
        payload = {}
        if "username" in data:
            username = normalize_text(data.get("username"), max_length=80)
            if not username:
                return jsonify({"error": "username inválido"}), 400
            payload["username"] = username
        if "role" in data:
            role = normalize_text(data.get("role"), max_length=32)
            if role not in {"user", "business_owner", "admin"}:
                return jsonify({"error": "Rol no permitido"}), 400
            if id == actor_id and role != "admin":
                return (
                    jsonify(
                        {"error": "No puedes quitarte privilegios administrativos"}
                    ),
                    403,
                )
            payload["role"] = role
        if "status" in data:
            status = normalize_text(data.get("status"), max_length=24).upper()
            if status not in {"ACTIVE", "SUSPENDED", "PENDING", "DELETED"}:
                return jsonify({"error": "Estado no permitido"}), 400
            if id == actor_id and status != "ACTIVE":
                return (
                    jsonify(
                        {"error": "No puedes suspender tu propia cuenta administrativa"}
                    ),
                    403,
                )
            payload["status"] = status
        if "profile" in data:
            profile = data.get("profile")
            if not isinstance(profile, dict):
                return jsonify({"error": "profile inválido"}), 400
            profile_allowed = {"name", "email", "preferences", "restrictions"}
            if set(profile) - profile_allowed:
                return jsonify({"error": "Campos de perfil no permitidos"}), 400
            payload["profile"] = {
                key: (
                    _clean_list(profile.get(key), max_items=30, max_length=80)
                    if key in {"preferences", "restrictions"}
                    else normalize_text(profile.get(key), max_length=255)
                )
                for key in profile
            }
        if not payload:
            return jsonify({"error": "No hay cambios permitidos"}), 400
        updated = UserModel.update(id, payload)
        if not updated:
            return jsonify({"error": "No se pudo actualizar el usuario"}), 409
        action = (
            "ADMIN_USER_SUSPEND"
            if payload.get("status") == "SUSPENDED"
            else "ADMIN_USER_UPDATE"
        )
        record_event(
            action,
            resource_type="user",
            resource_id=id,
            metadata={"changed_fields": sorted(payload)},
            actor_user_id=actor_id,
        )
        return jsonify({"success": True, "user": public_user(updated)})

    deleted = UserModel.delete(id)
    if deleted:
        record_event(
            "ADMIN_USER_DELETE",
            resource_type="user",
            resource_id=id,
            metadata={"username": user.get("username")},
            actor_user_id=actor_id,
        )
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Usuario no encontrado"}), 404


# ============================================
# GESTIÓN DE CATEGORÍAS - Solo admin
# ============================================


@admin_bp.route("/categories")
@admin_required
def categories():
    """Lista de categorías - Solo admin"""
    categories = CategoryModel.all()
    return render_template("admin/categories.html", categories=categories)


@admin_bp.route("/category", methods=["POST"])
@admin_required
def new_category():
    """Crear nueva categoría - Solo admin"""
    data = {
        "name": request.form.get("name"),
        "slug": request.form.get("slug"),
        "icon": request.form.get("icon", "restaurant"),
        "image_url": request.form.get("image_url", ""),
    }

    if not data["name"] or not data["slug"]:
        flash("Nombre y slug son requeridos", "error")
        return redirect(url_for("admin.categories"))

    with document_transaction():
        category = CategoryModel.create(data)
        record_event("ADMIN_CATEGORY_CREATE", resource_type="category", resource_id=category["id"])

    flash("Categoría creada exitosamente", "success")
    return redirect(url_for("admin.categories"))


@admin_bp.route("/category/<int:id>", methods=["DELETE"])
@admin_required
def delete_category(id: int):
    """Eliminar categoría - Solo admin"""
    with document_transaction():
        deleted = CategoryModel.delete(id)
        if deleted:
            record_event("ADMIN_CATEGORY_DELETE", resource_type="category", resource_id=id)
    return jsonify({"success": deleted}), 200 if deleted else 404


# ============================================
# ESTADÍSTICAS - Solo admin
# ============================================


@admin_bp.route("/api/stats")
@admin_required
def stats_api():
    """API para estadísticas generales - Solo admin"""
    restaurants = RestaurantModel.all()
    users = UserModel.all()
    favorites = FavoriteModel.all()

    return jsonify(
        {
            "total_restaurants": len(restaurants),
            "total_users": len(users),
            "total_favorites": len(favorites),
            "avg_rating": (
                sum(r.get("rating", 0) for r in restaurants) / len(restaurants)
                if restaurants
                else 0
            ),
            "avg_price": (
                sum(r.get("avg_price", 0) for r in restaurants) / len(restaurants)
                if restaurants
                else 0
            ),
            "with_promo": sum(1 for r in restaurants if r.get("promo")),
            "total_reviews": sum(r.get("reviews", 0) for r in restaurants),
        }
    )


@admin_bp.route("/moderation")
@admin_required
def moderation_dashboard():
    """Panel de moderación - Solo admin"""
    from models.moderation import ModerationModel
    from utils.content_filter import ContentFilter

    moderation_model = ModerationModel()

    # Estadísticas
    stats = moderation_model.get_stats()

    from utils.moderation_explain import (
        evaluar_restaurante,
        estado_pendiente,
        motivo_contenido,
    )
    from utils.admin_menu_audit import audit_restaurant_menu

    pending = moderation_model.get_pending_reviews()
    flagged = moderation_model.get_flagged_content()
    all_restaurants = RestaurantModel.all()
    restaurants_by_id = {str(r.get("id")): r for r in all_restaurants if r.get("id") is not None}
    # Las solicitudes de moderación son la fuente principal de la cola. La
    # colección restaurants se usa para enriquecer su tarjeta y para recuperar
    # registros legacy que todavía no tienen una entrada de moderación.
    pending_restaurants = []
    pending_ids = set()
    for entry in pending:
        if entry.get("content_type") != "restaurant":
            continue
        content_id = str(entry.get("content_id"))
        restaurant = restaurants_by_id.get(content_id)
        if restaurant is None:
            continue
        if content_id not in pending_ids:
            pending_restaurants.append(restaurant)
            pending_ids.add(content_id)
    for restaurant in all_restaurants:
        rid = str(restaurant.get("id"))
        if rid not in pending_ids and estado_pendiente(restaurant):
            pending_restaurants.append(restaurant)
            pending_ids.add(rid)
    evaluations = []
    for restaurant in pending_restaurants:
        evaluation = evaluar_restaurante(restaurant, ContentFilter)
        district = str(restaurant.get("district") or "").casefold()
        peer_prices = [
            peer.get("avg_price") for peer in all_restaurants
            if str(peer.get("district") or "").casefold() == district
            and peer.get("id") != restaurant.get("id")
        ]
        menu_audit = audit_restaurant_menu(
            restaurant,
            DishModel.get_by_restaurant(restaurant.get("id")),
            peer_prices,
        )
        evaluation["menu_audit"] = menu_audit
        for finding in menu_audit["findings"]:
            evaluation["issues"].extend(f"{finding['name']}: {message}" for message in finding["observations"])
        if menu_audit["price_note"] and "atípico" in menu_audit["price_note"]:
            evaluation["issues"].append(menu_audit["price_note"])
        evaluation["needs_review"] = bool(evaluation["issues"])
        evaluations.append(evaluation)
    auto_flagged = sorted(
        (r for r in evaluations if r["needs_review"]), key=lambda x: x["food_score"]
    )
    clean_pending = [
        dict(r["restaurant"], food_score=r["food_score"], menu_audit=r["menu_audit"])
        for r in evaluations if not r["needs_review"]
    ]
    pending_ids = {str(r.get("id")) for r in pending_restaurants}
    pending = [
        dict(item, display_reason=motivo_contenido(item))
        for item in pending
        if not (
            item.get("content_type") == "restaurant"
            and str(item.get("content_id")) in pending_ids
        )
    ]
    # El contador debe coincidir con las solicitudes que efectivamente se muestran,
    # incluidas las entradas legacy pendientes sin fila formal de moderación.
    stats["pending"] = len(auto_flagged) + len(clean_pending) + len(pending)
    return render_template(
        "admin/moderation.html",
        stats=stats,
        pending=pending,
        flagged=flagged,
        auto_flagged=auto_flagged,
        clean_pending=clean_pending,
        total_restaurants=len(RestaurantModel.all()),
    )


@admin_bp.route("/moderation/restaurant/<int:id>/review", methods=["POST"])
@admin_required
def review_restaurant(id):
    """Aplicar una decisión administrativa controlada y reversible."""
    from models.moderation import (
        ModerationModel,
        APPROVAL_AUTOMATIC,
        APPROVAL_PENDING,
        APPROVAL_REJECTED,
        APPROVAL_SUSPENDED,
    )

    try:
        data = request.get_json(silent=True) or {}
        action = normalize_text(data.get("action"), max_length=20).lower()
        notes = normalize_text(data.get("notes"), max_length=1000)
        action_to_status = {
            "approve": APPROVAL_AUTOMATIC,
            "reject": APPROVAL_REJECTED,
            "suspend": APPROVAL_SUSPENDED,
            "pending": APPROVAL_PENDING,
            "revert": APPROVAL_PENDING,
        }
        if action not in action_to_status:
            return jsonify({"error": "Acción de moderación no permitida"}), 400

        restaurant = RestaurantModel.get_by_id(id)
        if not restaurant:
            return jsonify({"error": "Restaurante no encontrado"}), 404
        actor_id = int(session.get("user_id"))
        entries = ModerationModel._load_data()
        entry = next(
            (
                item
                for item in entries
                if str(item.get("content_id")) == str(id)
                and item.get("content_type") == "restaurant"
            ),
            None,
        )
        if not entry:
            entry = ModerationModel.create_moderation_entry(
                "restaurant",
                id,
                restaurant,
                actor_id,
                reason="Registro creado durante revisión administrativa",
            )

        controlled_status = action_to_status[action]
        updated_entry = (
            ModerationModel.revert_content(
                entry["id"], controlled_status, notes, actor_id
            )
            if action == "revert"
            else ModerationModel.transition_status(
                entry["id"], controlled_status, actor_user_id=actor_id, notes=notes
            )
        )
        if not updated_entry:
            return jsonify({"error": "No se pudo actualizar la revisión"}), 409

        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        restaurant_update = {
            "verified": controlled_status == APPROVAL_AUTOMATIC,
            "approval_status": controlled_status,
            "moderation_notes": notes,
            "moderated_at": now,
            "rejected": controlled_status == APPROVAL_REJECTED,
            "suspended": controlled_status == APPROVAL_SUSPENDED,
            "publication_status": (
                "published"
                if controlled_status == APPROVAL_AUTOMATIC
                else "unpublished"
            ),
        }
        RestaurantModel.update(id, restaurant_update)
        record_event(
            (
                "ADMIN_APPROVAL_REVERT"
                if action == "revert"
                else "ADMIN_APPROVAL_DECISION"
            ),
            resource_type="restaurant",
            resource_id=id,
            metadata={
                "action": action,
                "status": controlled_status,
                "moderation_id": entry["id"],
                "has_notes": bool(notes),
            },
            actor_user_id=actor_id,
        )
        messages = {
            APPROVAL_AUTOMATIC: "Restaurante aprobado y visible para los usuarios.",
            APPROVAL_PENDING: "Restaurante enviado a revisión pendiente.",
            APPROVAL_REJECTED: "Restaurante rechazado y no publicado.",
            APPROVAL_SUSPENDED: "Restaurante suspendido y retirado de publicación.",
        }
        return jsonify(
            {
                "success": True,
                "status": controlled_status,
                "message": messages[controlled_status],
            }
        )
    except (TypeError, ValueError):
        return jsonify({"error": "Solicitud de moderación inválida"}), 400
    except Exception:
        logger.exception("Error controlado en revisión de restaurante")
        return jsonify({"error": "No se pudo procesar la revisión"}), 500


@admin_bp.route("/moderation/restaurant/<int:id>/history", methods=["GET"])
@admin_required
def restaurant_moderation_history(id):
    """Consultar la trazabilidad de un restaurante únicamente para administradores."""
    from models.moderation import ModerationModel

    entry = next(
        (
            item
            for item in ModerationModel._load_data()
            if str(item.get("content_id")) == str(id) and item.get("content_type") == "restaurant"
        ),
        None,
    )
    if not entry:
        return jsonify({"error": "Historial no encontrado"}), 404
    return jsonify(
        {
            "moderation_id": entry.get("id"),
            "status": ModerationModel.normalize_state(entry),
            "history": entry.get("status_history", []),
        }
    )


@admin_bp.route("/moderation/restaurant/<int:id>/notify-owner", methods=["POST"])
@admin_required
def notify_restaurant_owner(id):
    """Envía recomendaciones redactadas por el admin al dueño del restaurante."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or set(data) != {"message"}:
        return jsonify(success=False, error="Envía únicamente el mensaje."), 400

    message = normalize_text(data.get("message"), max_length=1600)
    if len(message) < 15:
        return jsonify(success=False, error="Escribe una recomendación de al menos 15 caracteres."), 400

    restaurant = RestaurantModel.get_by_id(id)
    if not restaurant:
        return jsonify(success=False, error="Restaurante no encontrado."), 404

    try:
        owner_id = int(restaurant.get("owner_id"))
    except (TypeError, ValueError):
        return jsonify(success=False, error="Este restaurante no tiene un empresario asociado."), 409
    owner = UserModel.get_by_id(owner_id)
    if not owner or owner.get("role") != "business_owner":
        return jsonify(success=False, error="No se encontró el empresario responsable."), 409

    notification = NotificationModel.create_notification(
        user_id=owner_id,
        title="Recomendaciones para tu restaurante",
        message=message,
        type_="info",
        link=url_for("owner.menu_management", restaurant_id=id),
    )
    try:
        record_event(
            "ADMIN_OWNER_IMPROVEMENT_NOTIFICATION",
            resource_type="restaurant",
            resource_id=id,
            metadata={
                "recipient_user_id": owner_id,
                "notification_id": notification.get("id") if isinstance(notification, dict) else None,
                "message_length": len(message),
            },
            actor_user_id=int(session.get("user_id")),
        )
    except Exception:
        logger.exception("No se pudo registrar la auditoría de notificación al empresario")
    return jsonify(success=True, message="La notificación se envió al empresario.")


@admin_bp.route("/moderation/auto-filter", methods=["POST"])
@admin_required
def auto_filter_restaurants():
    """Evalúa restaurantes y registra los resultados sin borrar decisiones humanas."""
    from models.moderation import (
        ModerationModel,
        APPROVAL_PENDING,
        CONTROLLED_TO_LEGACY,
    )

    actor_id = session.get("user_id")

    checked = 0
    flagged = 0
    created = 0
    updated = 0
    preserved_human_decisions = 0

    now = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()

    for restaurant in RestaurantModel.all():
        if not isinstance(restaurant, dict):
            continue

        checked += 1
        restaurant_id = restaurant.get("id")

        evaluation = ModerationModel.preliminary_evaluate(
            "restaurant",
            restaurant,
        )

        needs_review = bool(
            evaluation.get("human_review_required") or evaluation.get("issues")
        )

        if needs_review:
            flagged += 1

        entries = ModerationModel._load_data()

        existing = next(
            (
                item
                for item in entries
                if str(item.get("content_id")) == str(restaurant_id)
                and item.get("content_type") == "restaurant"
            ),
            None,
        )

        # Una decisión humana no debe ser sustituida por una nueva
        # ejecución del filtro automático.
        if existing and (
            existing.get("human_decision_at")
            or existing.get("decision_source")
            in (
                "ADMIN_REVIEW",
                "ADMIN_REVERT",
            )
        ):
            preserved_human_decisions += 1
            continue

        if existing is None:
            ModerationModel.create_moderation_entry(
                content_type="restaurant",
                content_id=restaurant_id,
                content_data=restaurant,
                user_id=actor_id,
                reason="Preevaluación automática",
                ai_evaluation=evaluation,
            )
            created += 1
            continue

        previous_status = ModerationModel.normalize_state(existing)
        new_status = evaluation.get(
            "final_status",
            APPROVAL_PENDING,
        )

        if new_status not in CONTROLLED_TO_LEGACY:
            new_status = APPROVAL_PENDING

        timestamp = now()
        history = list(existing.get("status_history") or [])

        # Registra el cambio de estado para mantener la trazabilidad.
        if previous_status != new_status:
            history.append(
                {
                    "from": previous_status,
                    "to": new_status,
                    "actor_user_id": None,
                    "source": "AI_PRECHECK",
                    "notes": "Estado actualizado por una nueva preevaluación.",
                    "timestamp": timestamp,
                }
            )

        ModerationModel.update(
            existing["id"],
            {
                "content_data": restaurant,
                "approval_status": new_status,
                "status": CONTROLLED_TO_LEGACY[new_status],
                "ai_verdict": evaluation.get("ai_verdict"),
                "ai_confidence": evaluation.get("confidence"),
                "ai_evaluation": evaluation,
                "decision_source": "AI_PRECHECK",
                "flagged": needs_review,
                "status_history": history,
                "updated_at": timestamp,
            },
        )
        updated += 1

    record_event(
        "ADMIN_APPROVAL_DECISION",
        resource_type="moderation_batch",
        metadata={
            "total_checked": checked,
            "flagged": flagged,
            "created": created,
            "updated": updated,
            "preserved_human_decisions": preserved_human_decisions,
            "action": "preliminary_filter",
        },
        actor_user_id=actor_id,
    )

    return (
        jsonify(
            {
                "success": True,
                "total_checked": checked,
                "flagged": flagged,
                "human_review_required": flagged,
                "created": created,
                "updated": updated,
                "preserved_human_decisions": preserved_human_decisions,
            }
        ),
        200,
    )
