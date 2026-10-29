# views/owner.py
from flask import (
    Blueprint,
    Response,
    render_template,
    session,
    redirect,
    url_for,
    flash,
    jsonify,
    request,
)
from models.restaurant import RestaurantModel
from models.dish import DishModel
from models.daily_menu import DailyMenuModel
from models.category import CategoryModel
from models.user import UserModel
from config import Config
from utils.security import normalize_text
from utils.menu_documents import (
    MenuDocumentError,
    build_menu_template,
    read_menu_document,
    MAX_MENU_ROWS,
)
from utils.qwen_menu import QwenMenuError, create_menu_draft
from utils.gemini_menu import GeminiMenuError, create_photo_menu_draft
from logic.hybrid_recommender import suggest_menu
from functools import wraps
from datetime import datetime, timedelta, timezone
import json
import os
import logging

logger = logging.getLogger(__name__)

owner_bp = Blueprint("owner", __name__, url_prefix="/owner")

WEEKDAYS = (
    {"value": "lunes", "label": "Lunes"},
    {"value": "martes", "label": "Martes"},
    {"value": "miercoles", "label": "Miércoles"},
    {"value": "jueves", "label": "Jueves"},
    {"value": "viernes", "label": "Viernes"},
    {"value": "sabado", "label": "Sábado"},
    {"value": "domingo", "label": "Domingo"},
)
MEAL_TIMES = (
    {"value": "desayuno", "label": "Desayuno"},
    {"value": "almuerzo", "label": "Almuerzo"},
    {"value": "cena", "label": "Cena"},
)
DISH_CATEGORIES = (
    {"value": "Entrada", "label": "Entradas"},
    {"value": "Fondo", "label": "Platos de fondo"},
    {"value": "Postre", "label": "Postres"},
    {"value": "Bebida", "label": "Bebidas"},
)
VALID_WEEKDAYS = {day["value"] for day in WEEKDAYS}
VALID_MEAL_TIMES = {meal["value"] for meal in MEAL_TIMES}
VALID_DISH_CATEGORIES = {category["value"] for category in DISH_CATEGORIES}
VALID_MENU_TYPES = {"fixed", "daily", "mixed"}
WEEKDAY_VALUES = tuple(day["value"] for day in WEEKDAYS)
WEEKDAY_NAMES = (
    "lunes",
    "martes",
    "miércoles",
    "jueves",
    "viernes",
    "sábado",
    "domingo",
)
MONTH_NAMES = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)
LIMA_TIMEZONE = timezone(timedelta(hours=-5))


def _parse_menu_date(value):
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None
    return parsed if parsed.isoformat() == value else None


def _format_menu_date(value):
    return (
        f"{WEEKDAY_NAMES[value.weekday()]} {value.day} de "
        f"{MONTH_NAMES[value.month - 1]} del {value.year}"
    )


def _menu_date_is_past(value):
    return value < datetime.now(LIMA_TIMEZONE).date()


def _json_payload():
    payload = request.get_json(silent=True)
    return payload if isinstance(payload, dict) else None


def _number(value, *, minimum=0, maximum=100000):
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if minimum <= result <= maximum else None


def _string_list(value, *, limit=50, item_length=80):
    if not isinstance(value, list):
        return []
    return [
        normalize_text(item, max_length=item_length)
        for item in value[:limit]
        if normalize_text(item, max_length=item_length)
    ]


def _restaurant_menu_type(restaurant):
    menu_type = normalize_text(restaurant.get("menu_type"), max_length=20).lower()
    return menu_type if menu_type in VALID_MENU_TYPES else "mixed"


def owner_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session or not session.get("user"):
            flash("Debes iniciar sesión", "warning")
            return redirect(url_for("auth.login"))

        user = session.get("user")
        if user.get("role") != "business_owner":
            flash("Acceso denegado. Se requieren permisos de empresario.", "error")
            return redirect(url_for("main.index"))

        return f(*args, **kwargs)

    return decorated_function


@owner_bp.route("/dashboard")
@owner_required
def dashboard():
    """Panel de empresario - Solo ve sus restaurantes"""
    user = session.get("user")
    user_id = user.get("id")

    restaurants = RestaurantModel.get_by_owner(user_id)

    # Agregar nombre de categoría a cada restaurante
    categories = CategoryModel.all()

    cat_dict = {cat["id"]: cat["name"] for cat in categories}
    for r in restaurants:
        r["category_name"] = cat_dict.get(r.get("category_id"), "Sin categoría")

    total_rest = len(restaurants)
    avg_rating = (
        sum(r.get("rating", 0) for r in restaurants) / total_rest
        if total_rest > 0
        else 0
    )
    total_promos = sum(1 for r in restaurants if r.get("promo"))

    # Actividad reciente
    recent_activities = []
    if restaurants:
        latest = sorted(restaurants, key=lambda x: x.get("id", 0), reverse=True)[:3]
        for r in latest:
            recent_activities.append(
                {
                    "icon": "plus",
                    "message": f'Actualizaste "{r.get("name")}"',
                    "time": "Recientemente",
                }
            )

    if len(recent_activities) < 3:
        recent_activities.append(
            {
                "icon": "star",
                "message": f"Rating promedio: {avg_rating:.1f} ⭐",
                "time": "General",
            }
        )

    return render_template(
        "owner/dashboard.html",
        restaurants=restaurants,
        total_rest=total_rest,
        avg_rating=round(avg_rating, 2),
        total_promos=total_promos,
        recent_activities=recent_activities,
    )


@owner_bp.route("/menu/<int:restaurant_id>")
@owner_required
def menu_management(restaurant_id):
    """Gestión de menú para un restaurante específico"""
    user = session.get("user")
    user_id = user.get("id")

    if not RestaurantModel.is_owner(user_id, restaurant_id):
        flash("No tienes permiso para gestionar este restaurante", "error")
        return redirect(url_for("owner.dashboard"))

    restaurant = RestaurantModel.get_by_id(restaurant_id)
    if not restaurant:
        flash("Restaurante no encontrado", "error")
        return redirect(url_for("owner.dashboard"))

    menu_type = _restaurant_menu_type(restaurant)
    restaurant["menu_type"] = menu_type

    today = datetime.now(LIMA_TIMEZONE).date()
    requested_date = request.args.get("date")
    selected_date = _parse_menu_date(requested_date) if requested_date else today
    if selected_date is None:
        flash("La fecha solicitada no es válida. Se muestra el menú de hoy.", "warning")
        selected_date = today

    dishes = DishModel.get_by_restaurant(restaurant_id)
    for dish in dishes:
        dish_date = _parse_menu_date(dish.get("menu_date"))
        dish["menu_date_label"] = _format_menu_date(dish_date) if dish_date else None

    selected_date_iso = selected_date.isoformat()
    carta_dishes = [dish for dish in dishes if not dish.get("menu_date")]
    date_dishes = [
        dish for dish in dishes if dish.get("menu_date") == selected_date_iso
    ]
    week_start = selected_date - timedelta(days=selected_date.weekday())
    week_days = [
        {
            "value": (week_start + timedelta(days=index)).isoformat(),
            "label": weekday["label"],
            "day_number": (week_start + timedelta(days=index)).day,
            "selected": (week_start + timedelta(days=index)) == selected_date,
        }
        for index, weekday in enumerate(WEEKDAYS)
    ]
    today_menu = DailyMenuModel.get_active(restaurant_id)
    history_menu = DailyMenuModel.get_by_date(restaurant_id, selected_date_iso)
    if date_dishes:
        history_menu = None

    history_date_values = set()
    for dish in dishes:
        dish_date = _parse_menu_date(dish.get("menu_date"))
        if dish_date and dish_date < today:
            history_date_values.add(dish_date)
    for saved_menu in DailyMenuModel.get_by_restaurant(restaurant_id):
        saved_date = _parse_menu_date(saved_menu.get("date"))
        if saved_date and saved_date < today:
            history_date_values.add(saved_date)
    history_dates = [
        {"value": day.isoformat(), "label": _format_menu_date(day)}
        for day in sorted(history_date_values, reverse=True)
    ]

    return render_template(
        "owner/menu_management.html",
        restaurant=restaurant,
        dishes=dishes,
        carta_dishes=carta_dishes,
        date_dishes=date_dishes,
        week_days=week_days,
        menu_type=menu_type,
        today_menu=today_menu,
        weekdays=WEEKDAYS,
        meal_times=MEAL_TIMES,
        dish_categories=DISH_CATEGORIES,
        selected_date_iso=selected_date_iso,
        today_date_iso=today.isoformat(),
        selected_date_label=_format_menu_date(selected_date),
        is_read_only=selected_date < today,
        history_menu=history_menu,
        history_dates=history_dates,
    )


@owner_bp.route("/menu/<int:restaurant_id>/template/<file_format>")
@owner_required
def download_menu_template(restaurant_id, file_format):
    """Download a blank spreadsheet or Word template for the owner's menu."""
    if not RestaurantModel.is_owner(session["user"].get("id"), restaurant_id):
        flash("No tienes permiso para gestionar este restaurante", "error")
        return redirect(url_for("owner.dashboard"))
    if file_format not in {"xlsx", "docx"}:
        return jsonify({"error": "Formato de plantilla no compatible"}), 404

    try:
        stream = build_menu_template(file_format)
    except MenuDocumentError as exc:
        flash(str(exc), "error")
        return redirect(url_for("owner.menu_management", restaurant_id=restaurant_id))
    mimetype = (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        if file_format == "xlsx"
        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    content = stream.getvalue()
    response = Response(content, mimetype=mimetype)
    response.headers["Content-Disposition"] = (
        f'attachment; filename="plantilla_carta_restaurante_{restaurant_id}.{file_format}"'
    )
    response.headers["Content-Length"] = str(len(content))
    response.headers["Cache-Control"] = "no-store"
    return response


@owner_bp.route("/menu/<int:restaurant_id>/import", methods=["POST"])
@owner_required
def import_menu_preview(restaurant_id):
    """Read a filled Word/Excel template and ask Qwen through Groq for a reviewable draft."""
    user_id = session["user"].get("id")
    restaurant = RestaurantModel.get_by_id(restaurant_id)
    if not restaurant or not RestaurantModel.is_owner(user_id, restaurant_id):
        flash("No tienes permiso para gestionar este restaurante", "error")
        return redirect(url_for("owner.dashboard"))

    uploaded_file = request.files.get("menu_file")
    photo_files = [
        file for file in request.files.getlist("menu_photos") if file.filename
    ]
    if bool(uploaded_file and uploaded_file.filename) == bool(photo_files):
        flash(
            "Selecciona una plantilla Excel/Word o entre 1 y 6 fotografías.", "warning"
        )
        return redirect(url_for("owner.menu_management", restaurant_id=restaurant_id))
    try:
        if photo_files:
            draft = create_photo_menu_draft(photo_files)
            source_filename = f"{len(photo_files)} fotografía(s) de carta"
            provider = "Gemini"
        else:
            source_rows = read_menu_document(
                uploaded_file.stream, uploaded_file.filename
            )
            draft = create_menu_draft(source_rows)
            source_filename = uploaded_file.filename.replace(chr(92), "/").rsplit(
                "/", 1
            )[-1][:120]
            provider = "Qwen"
    except (MenuDocumentError, QwenMenuError, GeminiMenuError) as exc:
        flash(str(exc), "error")
        return redirect(url_for("owner.menu_management", restaurant_id=restaurant_id))
    except Exception:
        logger.exception("Error analizando carta del restaurante %s", restaurant_id)
        flash("No se pudo procesar el archivo. Inténtalo nuevamente.", "error")
        return redirect(url_for("owner.menu_management", restaurant_id=restaurant_id))
    return render_template(
        "owner/menu_import_preview.html",
        restaurant=restaurant,
        restaurants=RestaurantModel.get_by_owner(user_id),
        source_filename=source_filename,
        draft=draft,
        provider=provider,
        dish_categories=DISH_CATEGORIES,
        meal_times=MEAL_TIMES,
        today_date_iso=datetime.now(LIMA_TIMEZONE).date().isoformat(),
        review_error=None,
    )


@owner_bp.route("/menu/<int:restaurant_id>/import/apply", methods=["POST"])
@owner_required
def import_menu_apply(restaurant_id):
    """Validate the reviewed draft and save each dish as carta or for its selected date."""
    user_id = session["user"].get("id")
    restaurant = RestaurantModel.get_by_id(restaurant_id)
    if not restaurant or not RestaurantModel.is_owner(user_id, restaurant_id):
        flash("No tienes permiso para gestionar este restaurante", "error")
        return redirect(url_for("owner.dashboard"))

    try:
        draft = json.loads(request.form.get("draft_json", ""))
        dishes = draft.get("dishes") if isinstance(draft, dict) else None
        if not isinstance(dishes, list) or not 1 <= len(dishes) <= MAX_MENU_ROWS:
            raise ValueError("La carta debe contener entre 1 y 40 platos.")

        intro = normalize_text(request.form.get("introduction", ""), max_length=500)
        reviewed_dishes = []
        selected_count = 0
        for index, source in enumerate(dishes):
            if request.form.get(f"dish_{index}_include") != "on":
                continue
            selected_count += 1
            if not isinstance(source, dict):
                raise ValueError("Uno de los platos del borrador no es válido.")
            name = normalize_text(
                request.form.get(f"dish_{index}_name"), max_length=120
            )
            price = _number(
                request.form.get(f"dish_{index}_price"), minimum=0, maximum=100000
            )
            category = normalize_text(
                request.form.get(f"dish_{index}_category"), max_length=30
            )
            meal_time = normalize_text(
                request.form.get(f"dish_{index}_meal_time"), max_length=20
            ).lower()
            description = normalize_text(
                request.form.get(f"dish_{index}_description"), max_length=1000
            )
            menu_type = normalize_text(
                request.form.get(f"dish_{index}_menu_type"), max_length=20
            ).lower()
            raw_menu_date = normalize_text(
                request.form.get(f"dish_{index}_menu_date"), max_length=20
            )
            if menu_type not in {"carta", "variable"}:
                raise ValueError(
                    f'Selecciona si {name or "uno de los platos"} pertenece a la carta o al menú variable.'
                )
            menu_date = None
            if menu_type == "variable":
                parsed_menu_date = _parse_menu_date(raw_menu_date)
                if parsed_menu_date is None:
                    raise ValueError(
                        f'Selecciona una fecha válida para el menú variable de {name or "uno de los platos"}.'
                    )
                if _menu_date_is_past(parsed_menu_date):
                    raise ValueError(
                        f'La fecha del menú variable de {name or "uno de los platos"} no puede estar en el pasado.'
                    )
                menu_date = parsed_menu_date.isoformat()
            if (
                not name
                or price is None
                or category not in VALID_DISH_CATEGORIES
                or meal_time not in VALID_MEAL_TIMES
            ):
                raise ValueError(
                    f'Revisa el nombre, precio, categoría y horario de {name or "uno de los platos"}.'
                )

            source_ingredients = source.get("ingredients", [])
            source_dietary = source.get("dietary_info", [])
            preparation_time = source.get("preparation_time", 20)
            spiciness = source.get("spiciness", 0)
            try:
                preparation_time = max(1, min(int(preparation_time), 600))
            except (TypeError, ValueError):
                preparation_time = 20
            try:
                spiciness = max(0, min(int(spiciness), 5))
            except (TypeError, ValueError):
                spiciness = 0

            reviewed_dishes.append(
                {
                    "restaurant_id": restaurant_id,
                    "name": name,
                    "price": round(price, 2),
                    "category": category,
                    "menu_date": menu_date,
                    "day_of_week": (
                        WEEKDAY_VALUES[_parse_menu_date(menu_date).weekday()]
                        if menu_date
                        else None
                    ),
                    "meal_time": meal_time,
                    "description": description,
                    "ingredients": _string_list(
                        source_ingredients, limit=50, item_length=100
                    ),
                    "dietary_info": _string_list(
                        source_dietary, limit=20, item_length=60
                    ),
                    "preparation_time": preparation_time,
                    "spiciness": spiciness,
                    "is_recommended": False,
                    "is_available": True,
                    "tags": [],
                    "created_at": datetime.utcnow().isoformat(),
                }
            )

        if selected_count == 0:
            raise ValueError("Selecciona al menos un plato para importar.")
        existing_dish_keys = {
            (
                normalize_text(dish.get("name"), max_length=120).casefold(),
                dish.get("menu_date") or None,
            )
            for dish in DishModel.get_by_restaurant(restaurant_id)
        }
        imported_ids = []
        imported_dishes = []
        skipped_duplicates = 0
        seen_dish_keys = set(existing_dish_keys)
        for dish_data in reviewed_dishes:
            key = (dish_data["name"].casefold(), dish_data["menu_date"])
            if key in seen_dish_keys:
                skipped_duplicates += 1
                continue
            saved_dish = DishModel.create(dish_data)
            imported_ids.append(saved_dish.get("id"))
            imported_dishes.append(dish_data)
            seen_dish_keys.add(key)

        restaurant_dishes = restaurant.get("dishes", [])
        if not isinstance(restaurant_dishes, list):
            restaurant_dishes = []
        restaurant_dishes.extend(
            dish_id for dish_id in imported_ids if dish_id not in restaurant_dishes
        )
        updates = {"dishes": restaurant_dishes}
        updates["menu_intro"] = intro
        imported_carta_count = sum(
            1 for dish in imported_dishes if not dish["menu_date"]
        )
        imported_variable_count = len(imported_dishes) - imported_carta_count
        current_menu_type = _restaurant_menu_type(restaurant)
        # Expose the section that was previously disabled by a single-mode
        # restaurant when this import introduces dishes for the other mode.
        if imported_ids and (
            (imported_carta_count and current_menu_type == "daily")
            or (imported_variable_count and current_menu_type == "fixed")
        ):
            updates["menu_type"] = "mixed"
        RestaurantModel.update(restaurant_id, updates)

        if imported_ids:
            imported_parts = []
            if imported_carta_count:
                imported_parts.append(f"{imported_carta_count} de carta permanente")
            if imported_variable_count:
                imported_parts.append(f"{imported_variable_count} de menú variable")
            message = f'Se agregaron {len(imported_ids)} platos: {" y ".join(imported_parts)}.'
            if skipped_duplicates:
                message += f" Se omitieron {skipped_duplicates} duplicados."
            if updates.get("menu_type") == "mixed":
                message += (
                    " El tipo de menú cambió a mixto para mostrar ambas secciones."
                )
            flash(message, "success")
        elif skipped_duplicates:
            flash(
                "Todos los platos del archivo ya existían para ese tipo y fecha; no se agregaron duplicados.",
                "info",
            )
        imported_dates = sorted(
            {dish["menu_date"] for dish in imported_dishes if dish["menu_date"]}
        )
        redirect_args = {"restaurant_id": restaurant_id}
        if imported_dates:
            redirect_args["date"] = imported_dates[0]
        return redirect(url_for("owner.menu_management", **redirect_args))
    except (json.JSONDecodeError, ValueError) as exc:
        if (
            "draft" in locals()
            and isinstance(draft, dict)
            and isinstance(draft.get("dishes"), list)
        ):
            for index, dish in enumerate(draft["dishes"]):
                if not isinstance(dish, dict):
                    continue
                for field in (
                    "name",
                    "price",
                    "category",
                    "meal_time",
                    "description",
                    "menu_type",
                    "menu_date",
                ):
                    key = f"dish_{index}_{field}"
                    if key in request.form:
                        dish[field] = request.form.get(key)
                dish["include"] = request.form.get(f"dish_{index}_include") == "on"
            draft["introduction"] = request.form.get("introduction", "")[:500]
            return (
                render_template(
                    "owner/menu_import_preview.html",
                    restaurant=restaurant,
                    restaurants=RestaurantModel.get_by_owner(user_id),
                    source_filename="Borrador recuperado",
                    draft=draft,
                    provider="IA",
                    dish_categories=DISH_CATEGORIES,
                    meal_times=MEAL_TIMES,
                    today_date_iso=datetime.now(LIMA_TIMEZONE).date().isoformat(),
                    review_error=str(exc),
                ),
                400,
            )
        flash(str(exc) or "El borrador no es válido.", "error")
        return redirect(url_for("owner.menu_management", restaurant_id=restaurant_id))
    except Exception:
        logger.exception("Error importando carta para restaurante %s", restaurant_id)
        flash("No se pudo guardar la carta. Vuelve a intentarlo.", "error")
        return redirect(url_for("owner.menu_management", restaurant_id=restaurant_id))


@owner_bp.route("/dish/add", methods=["POST"])
@owner_required
def add_dish():
    """Agregar un nuevo plato a la carta del restaurante"""
    try:
        user_id = session["user"].get("id")
        data = _json_payload()
        if data is None:
            return jsonify({"error": "El cuerpo debe ser un objeto JSON"}), 400
        try:
            restaurant_id = int(data.get("restaurant_id"))
        except (TypeError, ValueError):
            return jsonify({"error": "ID de restaurante inválido"}), 400

        if not RestaurantModel.is_owner(user_id, restaurant_id):
            return jsonify({"error": "No autorizado"}), 403

        name = normalize_text(data.get("name"), max_length=120)
        price = _number(data.get("price"), minimum=0, maximum=100000)
        category = normalize_text(data.get("category"), max_length=60)
        raw_menu_date = data.get("menu_date")
        menu_date = (
            None if raw_menu_date in (None, "") else _parse_menu_date(raw_menu_date)
        )
        meal_time = normalize_text(data.get("meal_time"), max_length=20).lower()
        preparation_time = data.get("preparation_time", 20)
        try:
            preparation_time = int(preparation_time)
        except (TypeError, ValueError):
            preparation_time = 20
        if menu_date is None and raw_menu_date not in (None, ""):
            return jsonify({"error": "Selecciona una fecha válida para el menú"}), 400
        if menu_date and _menu_date_is_past(menu_date):
            return (
                jsonify({"error": "No puedes agregar platos a una fecha pasada"}),
                400,
            )
        if (
            not name
            or price is None
            or category not in VALID_DISH_CATEGORIES
            or meal_time not in VALID_MEAL_TIMES
            or not 1 <= preparation_time <= 600
        ):
            return (
                jsonify(
                    {
                        "error": "Completa nombre, precio, tipo, horario y tiempo de preparación válidos"
                    }
                ),
                400,
            )

        dish_data = {
            "restaurant_id": restaurant_id,
            "name": name,
            "price": round(price, 2),
            "category": category,
            "menu_date": menu_date.isoformat() if menu_date else None,
            "day_of_week": WEEKDAY_VALUES[menu_date.weekday()] if menu_date else None,
            "meal_time": meal_time,
            "description": normalize_text(data.get("description", ""), max_length=1000),
            "ingredients": _string_list(
                data.get("ingredients", []), limit=50, item_length=100
            ),
            "dietary_info": _string_list(
                data.get("dietary_info", []), limit=20, item_length=60
            ),
            "preparation_time": preparation_time,
            "spiciness": max(0, min(int(data.get("spiciness", 0) or 0), 5)),
            "is_recommended": bool(data.get("is_recommended", False)),
            "is_available": True,
            "tags": _string_list(data.get("tags", []), limit=20, item_length=60),
            "created_at": datetime.utcnow().isoformat(),
        }

        new_dish = DishModel.create(dish_data)

        restaurant = RestaurantModel.get_by_id(restaurant_id)
        if restaurant:
            dishes_list = restaurant.get("dishes", [])
            if isinstance(dishes_list, list):
                dishes_list.append(new_dish.get("id"))
                restaurant["dishes"] = dishes_list
                RestaurantModel.update(restaurant_id, restaurant)

        return jsonify(
            {
                "success": True,
                "dish": new_dish,
                "message": "Plato agregado exitosamente",
            }
        )

    except Exception:
        logger.exception("Error agregando plato")
        return jsonify({"error": "No se pudo agregar el plato"}), 500


@owner_bp.route("/dish/<int:dish_id>/update", methods=["PUT"])
@owner_required
def update_dish(dish_id):
    """Actualizar un plato existente"""
    try:
        user_id = session["user"].get("id")
        dish = DishModel.get_by_id(dish_id)

        if not dish:
            return jsonify({"error": "Plato no encontrado"}), 404

        restaurant_id = dish.get("restaurant_id")
        if not RestaurantModel.is_owner(user_id, restaurant_id):
            return jsonify({"error": "No autorizado"}), 403

        existing_menu_date = _parse_menu_date(dish.get("menu_date"))
        if existing_menu_date and _menu_date_is_past(existing_menu_date):
            return (
                jsonify({"error": "Los menús de fechas pasadas son de solo lectura"}),
                403,
            )

        data = _json_payload()
        if data is None:
            return jsonify({"error": "El cuerpo debe ser un objeto JSON"}), 400

        allowed = {}
        if "name" in data:
            name = normalize_text(data.get("name"), max_length=120)
            if not name:
                return jsonify({"error": "El nombre no puede estar vacío"}), 400
            allowed["name"] = name
        if "price" in data:
            price = _number(data.get("price"), minimum=0, maximum=100000)
            if price is None:
                return jsonify({"error": "Precio inválido"}), 400
            allowed["price"] = round(price, 2)
        if "category" in data:
            category = normalize_text(data.get("category"), max_length=60)
            if category not in VALID_DISH_CATEGORIES:
                return jsonify({"error": "Tipo de plato inválido"}), 400
            allowed["category"] = category
        if "menu_date" in data:
            raw_menu_date = data.get("menu_date")
            menu_date = (
                None if raw_menu_date in (None, "") else _parse_menu_date(raw_menu_date)
            )
            if menu_date is None and raw_menu_date not in (None, ""):
                return (
                    jsonify({"error": "Selecciona una fecha válida para el menú"}),
                    400,
                )
            if menu_date and _menu_date_is_past(menu_date):
                return (
                    jsonify({"error": "No puedes mover platos a una fecha pasada"}),
                    400,
                )
            allowed["menu_date"] = menu_date.isoformat() if menu_date else None
            allowed["day_of_week"] = (
                WEEKDAY_VALUES[menu_date.weekday()] if menu_date else None
            )
        if "meal_time" in data:
            meal_time = normalize_text(data.get("meal_time"), max_length=20).lower()
            if meal_time not in VALID_MEAL_TIMES:
                return jsonify({"error": "Horario de menú inválido"}), 400
            allowed["meal_time"] = meal_time
        if "description" in data:
            allowed["description"] = normalize_text(
                data.get("description"), max_length=1000
            )
        if "ingredients" in data:
            allowed["ingredients"] = _string_list(
                data.get("ingredients"), limit=50, item_length=100
            )
        if "dietary_info" in data:
            allowed["dietary_info"] = _string_list(
                data.get("dietary_info"), limit=20, item_length=60
            )
        if "tags" in data:
            allowed["tags"] = _string_list(data.get("tags"), limit=20, item_length=60)
        if "preparation_time" in data:
            try:
                preparation_time = int(data.get("preparation_time"))
            except (TypeError, ValueError):
                return jsonify({"error": "Tiempo de preparación inválido"}), 400
            if not 1 <= preparation_time <= 600:
                return jsonify({"error": "Tiempo de preparación fuera de rango"}), 400
            allowed["preparation_time"] = preparation_time
        if "spiciness" in data:
            try:
                spiciness = int(data.get("spiciness"))
            except (TypeError, ValueError):
                return jsonify({"error": "Nivel de picante inválido"}), 400
            if not 0 <= spiciness <= 5:
                return jsonify({"error": "Nivel de picante fuera de rango"}), 400
            allowed["spiciness"] = spiciness
        for boolean_field in ("is_recommended", "is_available"):
            if boolean_field in data and isinstance(data[boolean_field], bool):
                allowed[boolean_field] = data[boolean_field]
        if not allowed:
            return jsonify({"error": "No hay campos actualizables"}), 400

        updated = DishModel.update(dish_id, allowed)

        return jsonify(
            {
                "success": True,
                "dish": updated,
                "message": "Plato actualizado exitosamente",
            }
        )

    except Exception:
        logger.exception("Error actualizando plato")
        return jsonify({"error": "No se pudo actualizar el plato"}), 500


@owner_bp.route("/dish/<int:dish_id>/delete", methods=["DELETE"])
@owner_required
def delete_dish(dish_id):
    """Eliminar un plato"""
    try:
        user_id = session["user"].get("id")
        dish = DishModel.get_by_id(dish_id)

        if not dish:
            return jsonify({"error": "Plato no encontrado"}), 404

        restaurant_id = dish.get("restaurant_id")
        if not RestaurantModel.is_owner(user_id, restaurant_id):
            return jsonify({"error": "No autorizado"}), 403

        menu_date = _parse_menu_date(dish.get("menu_date"))
        if menu_date and _menu_date_is_past(menu_date):
            return (
                jsonify({"error": "No puedes eliminar platos de fechas pasadas"}),
                403,
            )

        DishModel.delete(dish_id)

        return jsonify({"success": True, "message": "Plato eliminado exitosamente"})

    except Exception as e:
        logger.error(f"Error eliminando plato: {e}")
        return jsonify({"error": str(e)}), 500


@owner_bp.route("/dish/<int:dish_id>/toggle-availability", methods=["POST"])
@owner_required
def toggle_dish_availability(dish_id):
    """Cambiar disponibilidad de un plato"""
    try:
        user_id = session["user"].get("id")
        dish = DishModel.get_by_id(dish_id)

        if not dish:
            return jsonify({"error": "Plato no encontrado"}), 404

        restaurant_id = dish.get("restaurant_id")
        if not RestaurantModel.is_owner(user_id, restaurant_id):
            return jsonify({"error": "No autorizado"}), 403

        menu_date = _parse_menu_date(dish.get("menu_date"))
        if menu_date and _menu_date_is_past(menu_date):
            return (
                jsonify({"error": "Los menús de fechas pasadas son de solo lectura"}),
                403,
            )

        data = _json_payload()
        if data is None or not isinstance(data.get("is_available"), bool):
            return jsonify({"error": "is_available debe ser booleano"}), 400
        is_available = data["is_available"]
        updated = DishModel.update_availability(dish_id, is_available)

        return jsonify(
            {
                "success": True,
                "is_available": is_available,
                "message": f"Disponibilidad actualizada",
            }
        )

    except Exception:
        logger.exception("Error cambiando disponibilidad")
        return jsonify({"error": "No se pudo cambiar la disponibilidad"}), 500


@owner_bp.route("/generate_menu", methods=["POST"])
@owner_required
def generate_menu():
    """Genera un menú aleatorio sugerido para el empresario"""
    try:
        user_id = session["user"].get("id")
        data = _json_payload()
        if data is None:
            return jsonify({"error": "El cuerpo debe ser un objeto JSON"}), 400
        try:
            restaurant_id = int(data.get("restaurant_id"))
        except (TypeError, ValueError):
            return jsonify({"error": "ID de restaurante inválido"}), 400

        menu_date = _parse_menu_date(
            data.get("menu_date", datetime.now(LIMA_TIMEZONE).strftime("%Y-%m-%d"))
        )
        if menu_date is None:
            return (
                jsonify({"error": "Selecciona una fecha válida para generar el menú"}),
                400,
            )
        if _menu_date_is_past(menu_date):
            return (
                jsonify({"error": "No puedes generar menús para fechas pasadas"}),
                400,
            )

        if not restaurant_id:
            return jsonify({"error": "ID de restaurante requerido"}), 400

        if not RestaurantModel.is_owner(user_id, restaurant_id):
            return jsonify({"error": "No autorizado"}), 403

        all_dishes = DishModel.get_by_restaurant(restaurant_id)
        available_dishes = [
            dish
            for dish in all_dishes
            if dish.get("is_available", True)
            and (
                not dish.get("menu_date")
                or dish.get("menu_date") == menu_date.isoformat()
            )
        ]

        if len(available_dishes) < 3:
            return (
                jsonify(
                    {
                        "error": "No hay suficientes platos disponibles. Agrega más platos primero."
                    }
                ),
                400,
            )

        suggested_menu = suggest_menu(available_dishes, max_items_per_category=3)
        if not any(
            suggested_menu.get(bucket)
            for bucket in ("entradas", "fondos", "postres", "bebidas")
        ):
            return (
                jsonify(
                    {
                        "error": "No hay platos disponibles con categoría y precio suficientes para proponer un menú"
                    }
                ),
                400,
            )
        suggested_menu["explanation"] = {
            "method": "catalog_rules",
            "source": "platos registrados por el empresario",
            "invented_data": False,
        }
        return jsonify(
            {
                "success": True,
                "menu": suggested_menu,
                "message": "Menú propuesto con datos registrados, sin inventar ingredientes ni precios",
            }
        )

    except Exception:
        logger.exception("Error generando menú")
        return jsonify({"error": "No se pudo generar el menú"}), 500


@owner_bp.route("/save_daily_menu", methods=["POST"])
@owner_required
def save_daily_menu():
    """Guardar menú diario"""
    try:
        user_id = session["user"].get("id")
        data = _json_payload()
        if data is None:
            return jsonify({"error": "El cuerpo debe ser un objeto JSON"}), 400
        try:
            restaurant_id = int(data.get("restaurant_id"))
        except (TypeError, ValueError):
            return jsonify({"error": "ID de restaurante inválido"}), 400
        date = normalize_text(
            data.get("date", datetime.now(LIMA_TIMEZONE).strftime("%Y-%m-%d")),
            max_length=10,
        )
        dish_ids = data.get("dish_ids", [])
        specials = _string_list(data.get("specials", []), limit=20, item_length=160)
        price = _number(data.get("price", 0), minimum=0, maximum=100000)
        if price is None or not isinstance(dish_ids, list) or len(dish_ids) > 100:
            return jsonify({"error": "Datos del menú inválidos"}), 400
        parsed_menu_date = _parse_menu_date(date)
        if parsed_menu_date is None:
            return jsonify({"error": "La fecha debe tener formato YYYY-MM-DD"}), 400
        if _menu_date_is_past(parsed_menu_date):
            return (
                jsonify({"error": "No puedes modificar menús de fechas pasadas"}),
                400,
            )

        if not restaurant_id:
            return jsonify({"error": "ID de restaurante requerido"}), 400

        if not RestaurantModel.is_owner(user_id, restaurant_id):
            return jsonify({"error": "No autorizado"}), 403

        dishes = []
        seen_ids = set()
        for raw_dish_id in dish_ids:
            try:
                dish_id = int(raw_dish_id)
            except (TypeError, ValueError):
                return jsonify({"error": "Identificador de plato inválido"}), 400
            if dish_id in seen_ids:
                continue
            seen_ids.add(dish_id)
            dish = DishModel.get_by_id(dish_id)
            if not dish or dish.get("restaurant_id") != restaurant_id:
                return (
                    jsonify({"error": "Uno de los platos no pertenece al restaurante"}),
                    400,
                )
            if not dish.get("is_available", True):
                return (
                    jsonify({"error": "No se pueden guardar platos no disponibles"}),
                    400,
                )
            dishes.append(
                {
                    "dish_id": dish.get("id"),
                    "name": normalize_text(dish.get("name"), max_length=120),
                    "price": _number(dish.get("price"), minimum=0, maximum=100000) or 0,
                    "category": dish.get("category"),
                    "meal_time": dish.get("meal_time"),
                }
            )

        menu = DailyMenuModel.create_or_update(
            restaurant_id=restaurant_id,
            date=date,
            dishes=dishes,
            specials=specials,
            price=round(price, 2),
        )

        return jsonify(
            {
                "success": True,
                "menu": menu,
                "message": "Menú diario guardado exitosamente",
            }
        )

    except Exception:
        logger.exception("Error guardando menú diario")
        return jsonify({"error": "No se pudo guardar el menú"}), 500


@owner_bp.route("/restaurant/<int:restaurant_id>/menu_type", methods=["PUT"])
@owner_required
def update_menu_type(restaurant_id):
    """Actualizar tipo de menú del restaurante"""
    try:
        user_id = session["user"].get("id")

        if not RestaurantModel.is_owner(user_id, restaurant_id):
            return jsonify({"error": "No autorizado"}), 403

        data = _json_payload()
        if data is None:
            return jsonify({"error": "El cuerpo debe ser un objeto JSON"}), 400
        menu_type = normalize_text(data.get("menu_type"), max_length=20)

        if menu_type not in ["fixed", "daily", "mixed"]:
            return jsonify({"error": "Tipo de menú inválido"}), 400

        restaurant = RestaurantModel.get_by_id(restaurant_id)
        if not restaurant:
            return jsonify({"error": "Restaurante no encontrado"}), 404

        RestaurantModel.update(restaurant_id, {"menu_type": menu_type})

        return jsonify(
            {
                "success": True,
                "menu_type": menu_type,
                "message": "Tipo de menú actualizado",
            }
        )

    except Exception:
        logger.exception("Error actualizando tipo de menú")
        return jsonify({"error": "No se pudo actualizar el tipo de menú"}), 500


@owner_bp.route("/restaurant/<int:restaurant_id>/dishes", methods=["GET"])
@owner_required
def get_restaurant_dishes(restaurant_id):
    """Obtener todos los platos de un restaurante"""
    try:
        user_id = session["user"].get("id")

        if not RestaurantModel.is_owner(user_id, restaurant_id):
            return jsonify({"error": "No autorizado"}), 403

        dishes = DishModel.get_by_restaurant(restaurant_id)

        return jsonify({"success": True, "dishes": dishes, "total": len(dishes)})

    except Exception as e:
        logger.error(f"Error obteniendo platos: {e}")
        return jsonify({"error": str(e)}), 500
