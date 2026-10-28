from flask import (
    Blueprint,
    render_template,
    request,
    jsonify,
    session,
    current_app,
    flash,
    redirect,
    url_for,
)

from flask import Blueprint, request, jsonify
from utils.ia_qwen import obtener_recomendacion_ia

from werkzeug.routing import BuildError
from urllib.parse import quote
from models.restaurant import RestaurantModel
from models.category import CategoryModel
from models.dish import DishModel
from models.daily_menu import DailyMenuModel
from models.user import UserModel
from models.favorite import FavoriteModel
from models.notification import NotificationModel
from models.reservation import ReservationModel
from utils.functional import (
    filter_restaurants,
    enrich_with_metadata,
    rank_restaurants,
    get_statistics,
)
from logic.recommender import RecommenderEngine
from logic.hybrid_recommender import recommend as hybrid_recommend
from models.review import ReviewModel
from config import Config
from utils.security import csrf, valid_coordinate
from utils.geo import normalize_coordinates
import logging
from datetime import datetime, timedelta, timezone

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
LIMA_TIMEZONE = timezone(timedelta(hours=-5))

main_bp = Blueprint("main", __name__)

# Inicializar el recomendador
try:
    recommender = RecommenderEngine()
    logger.info("RecommenderEngine inicializado correctamente")
except Exception as e:
    logger.error(f"Error inicializando RecommenderEngine: {e}")
    recommender = None


def load_categories():
    """Load categories from the configured PostgreSQL collection."""
    return CategoryModel.all()


def load_dishes(restaurant_id):
    """Load a restaurant's dishes from the PostgreSQL collection."""
    return DishModel.get_by_restaurant(restaurant_id)


def get_user_profile():
    """Obtiene el perfil del usuario de la sesión de forma segura"""
    user_profile = {}
    user_data = session.get("user")
    if user_data:
        user_profile = user_data.get("profile", {})
        if "id" not in user_profile:
            user_profile["id"] = user_data.get("id", 999)
        if "restrictions" not in user_profile:
            user_profile["restrictions"] = []
        if "preferences" not in user_profile:
            user_profile["preferences"] = []
    else:
        user_profile = {"id": 999, "restrictions": [], "preferences": []}
    return user_profile


def get_login_url(next_path):
    """URL de login con retorno a la página actual (tolerante al nombre del endpoint)."""
    try:
        return url_for("auth.login", next=next_path)
    except BuildError:
        return "/auth/login?next=" + quote(next_path, safe="/")


def evaluate_restaurant_safe(restaurant, user_profile):
    """Evalúa un restaurante de forma segura con manejo de errores"""
    if not recommender:
        return True, ["Sistema de recomendación no disponible"]

    try:
        is_compatible, justifications = recommender.evaluate(restaurant, user_profile)
        return is_compatible, justifications
    except Exception as e:
        logger.error(f"Error evaluando restaurante {restaurant.get('id')}: {e}")
        return True, ["No se pudo evaluar completamente"]


@main_bp.route("/")
def index():
    """Página principal con lista de restaurantes y filtros"""
    try:
        # ✅ SOLO restaurantes aprobados/verificados
        restaurants = RestaurantModel.get_approved()
        categories = load_categories()
        stats = get_statistics(restaurants)

        # Agregar distancia si el usuario tiene ubicación
        user_lat = session.get("user_lat")
        user_lng = session.get("user_lng")
        if user_lat and user_lng:
            restaurants = enrich_with_metadata(restaurants, user_lat, user_lng)

        return render_template(
            "index.html",
            restaurants=restaurants,
            categories=categories,
            stats=stats,
            user_profile=get_user_profile(),
        )
    except Exception as e:
        logger.exception(f"Error en index: {e}")
        return render_template("index.html", restaurants=[], categories=[], stats={})


@main_bp.route("/restaurant/<int:restaurant_id>")
def detail(restaurant_id):
    """Página de detalles de un restaurante"""
    try:
        restaurant = RestaurantModel.get_by_id(restaurant_id)
        if not restaurant:
            return render_template("404.html", message="Restaurante no encontrado"), 404

        # ✅ Verificar que el restaurante esté aprobado
        # Los restaurantes no verificados solo pueden ser vistos por administradores
        if not restaurant.get("verified", False):
            user = session.get("user") or {}
            role = str(user.get("role", user.get("rol", ""))).upper()

            if role != "ADMIN":
                return (
                    render_template("404.html", message="Restaurante no disponible"),
                    404,
                )

        # Show permanent carta items and only the variable dishes scheduled for
        # today. Future dates remain hidden until they become active.
        today_iso = datetime.now(LIMA_TIMEZONE).date().isoformat()
        dishes = [
            dish for dish in load_dishes(restaurant_id)
            if not dish.get("menu_date") or dish.get("menu_date") == today_iso
        ]

        # Obtener menú del día
        daily_menu = DailyMenuModel.get_active(restaurant_id)

        # Obtener perfil del usuario
        user_profile = get_user_profile()

        # Calcular distancia si hay ubicación
        user_lat = session.get("user_lat")
        user_lng = session.get("user_lng")
        if user_lat and user_lng and restaurant.get("lat") and restaurant.get("lng"):
            from utils.geo import haversine_distance

            distance = haversine_distance(
                user_lat, user_lng, restaurant.get("lat"), restaurant.get("lng")
            )
            restaurant["distance_km"] = round(distance, 2)

        # Evaluar con el motor lógico
        explanation = None
        if recommender:
            try:
                explanation = recommender.explain(restaurant, user_profile)
            except Exception as e:
                logger.error(f"Error en explain para restaurante {restaurant_id}: {e}")
                is_compatible, justifications = evaluate_restaurant_safe(
                    restaurant, user_profile
                )
                explanation = {
                    "compatible": is_compatible,
                    "reasons": justifications,
                    "exclusions": [],
                    "dietary_options": {
                        "vegan": "vegano" in restaurant.get("dietary_restrictions", []),
                        "vegetarian": "vegetariano"
                        in restaurant.get("dietary_restrictions", []),
                        "gluten_free": "sin gluten"
                        in restaurant.get("dietary_restrictions", []),
                    },
                }
        else:
            explanation = {
                "compatible": True,
                "reasons": ["Restaurante disponible para tus preferencias"],
                "exclusions": [],
                "dietary_options": {
                    "vegan": "vegano" in restaurant.get("dietary_restrictions", []),
                    "vegetarian": "vegetariano"
                    in restaurant.get("dietary_restrictions", []),
                    "gluten_free": "sin gluten"
                    in restaurant.get("dietary_restrictions", []),
                },
            }

        return render_template(
            "detail.html",
            restaurant=restaurant,
            dishes=dishes,
            daily_menu=daily_menu,
            explanation=explanation,
            user_profile=user_profile,
            login_url=get_login_url(request.path),
        )

    except Exception as e:
        # logger.exception imprime el traceback completo en la terminal
        logger.exception(f"Error en detail para restaurante {restaurant_id}: {e}")
        return (
            render_template("500.html", message="Error al cargar el restaurante"),
            500,
        )


@main_bp.route("/restaurant/<int:restaurant_id>/reserve", methods=["POST"])
def reserve(restaurant_id):
    """Crea una reserva. Solo para usuarios con sesión iniciada."""
    detail_url = url_for("main.detail", restaurant_id=restaurant_id)

    # La validación real vive en el servidor, no solo en el botón
    user = session.get("user")
    if not user:
        flash("Inicia sesión para reservar.", "warning")
        return redirect(get_login_url(detail_url))

    restaurant = RestaurantModel.get_by_id(restaurant_id)
    if not restaurant or not restaurant.get("verified", False):
        flash("Restaurante no disponible.", "error")
        return redirect(url_for("main.index"))

    date_str = (request.form.get("date") or "").strip()
    time_str = (request.form.get("time") or "").strip()
    guests = request.form.get("guests", type=int)

    try:
        reservation_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    except ValueError:
        flash("La fecha u hora no son válidas.", "error")
        return redirect(detail_url)

    if reservation_dt < datetime.now():
        flash("La fecha y hora de la reserva ya pasaron.", "error")
        return redirect(detail_url)

    if not guests or not (1 <= guests <= 20):
        flash("El número de personas debe estar entre 1 y 20.", "error")
        return redirect(detail_url)

    try:
        reservation = ReservationModel.create(
            user_id=user.get("id"),
            restaurant_id=restaurant_id,
            date=date_str,
            time=time_str,
            guests=guests,
        )
    except Exception:
        logger.exception("Error guardando reserva")
        reservation = None

    if not reservation:
        flash("No se pudo guardar la reserva. Intenta de nuevo.", "error")
        return redirect(detail_url)

    flash(
        f"¡Reserva registrada en {restaurant.get('name', 'el restaurante')} "
        f"para el {date_str} a las {time_str}!",
        "success",
    )
    return redirect(detail_url)


@main_bp.route("/api/search", methods=["POST"])
@csrf.exempt  # Endpoint de lectura; las mutaciones siguen protegidas por CSRF.
def search():
    """API de búsqueda con filtros y recomendaciones"""
    try:
        filters = request.get_json(silent=True) or {}
        if not isinstance(filters, dict):
            return jsonify({"error": "Los filtros deben ser un objeto JSON"}), 400
        # ✅ SOLO restaurantes aprobados/verificados
        all_restaurants = RestaurantModel.get_approved()
        all_dishes = DishModel.all()

        restaurants = all_restaurants

        # 1. Búsqueda por plato específico
        dish_query = filters.get("dish_query", "").strip().lower()
        if dish_query:
            matching_dishes = []
            for d in all_dishes:
                name_match = dish_query in d.get("name", "").lower()
                desc_match = dish_query in d.get("description", "").lower()
                ing_match = any(
                    dish_query in ing.lower() for ing in d.get("ingredients", [])
                )
                if name_match or desc_match or ing_match:
                    matching_dishes.append(d)

            restaurant_ids = list(
                set(
                    d.get("restaurant_id")
                    for d in matching_dishes
                    if d.get("restaurant_id")
                )
            )
            restaurants = [r for r in all_restaurants if r.get("id") in restaurant_ids]

            for r in restaurants:
                r["matching_dishes"] = [
                    d for d in matching_dishes if d.get("restaurant_id") == r.get("id")
                ]

        # 2. Búsqueda por ingrediente
        ingredient_filter = filters.get("ingredient", "").strip().lower()
        if ingredient_filter:
            ingredient_dishes = []
            for d in all_dishes:
                if any(
                    ingredient_filter in ing.lower() for ing in d.get("ingredients", [])
                ):
                    ingredient_dishes.append(d)
            ingredient_restaurant_ids = list(
                set(d.get("restaurant_id") for d in ingredient_dishes)
            )
            restaurants = [
                r for r in restaurants if r.get("id") in ingredient_restaurant_ids
            ]

        # 3. Filtrar por restricciones alimenticias
        dietary_restrictions = filters.get("dietary_restrictions", [])
        if dietary_restrictions:
            compatible_dishes = []
            for d in all_dishes:
                dish_dietary = d.get("dietary_info", [])
                if all(r in dish_dietary for r in dietary_restrictions):
                    compatible_dishes.append(d)

            compatible_restaurant_ids = list(
                set(d.get("restaurant_id") for d in compatible_dishes)
            )
            restaurants = [
                r for r in restaurants if r.get("id") in compatible_restaurant_ids
            ]

        # 4. Búsqueda por tipo de menú
        menu_type = filters.get("menu_type")
        if menu_type:
            restaurants = [r for r in restaurants if r.get("menu_type") == menu_type]

        # 5. Filtros existentes
        filtered = filter_restaurants(restaurants, filters)

        # 6. Enriquecer con metadatos
        user_lat = filters.get("lat", Config.COORDENADAS_CENTRO[0])
        user_lng = filters.get("lng", Config.COORDENADAS_CENTRO[1])
        enriched = enrich_with_metadata(filtered, user_lat, user_lng)

        # 7. Evaluar con motor lógico
        user_profile = get_user_profile()
        final_results = []

        if recommender and enriched:
            for r in enriched:
                try:
                    is_compatible, justifications = recommender.evaluate(
                        r, user_profile
                    )
                    if is_compatible:
                        r["justifications"] = justifications
                        final_results.append(r)
                except Exception as e:
                    logger.error(f"Error evaluando restaurante {r.get('id')}: {e}")
                    r["justifications"] = ["No se pudo evaluar completamente"]
                    final_results.append(r)
        else:
            final_results = enriched
            for r in final_results:
                r["justifications"] = []

        # 8. Ranking híbrido explicable. Si no hay interacciones suficientes,
        # se activa explícitamente el fallback content + reglas + contexto.
        ranked = hybrid_recommend(
            final_results,
            user_profile,
            {"max_price": filters.get("max_price"), "budget": filters.get("budget")},
            favorites=FavoriteModel.all(),
            reviews=ReviewModel.all(),
        )

        # Compatibilidad: el contrato histórico devuelve directamente una lista.
        # Los metadatos se mantienen en cabeceras para clientes que los necesiten.
        response = jsonify(ranked)
        response.headers["X-Search-Total"] = str(len(ranked))
        return response

    except Exception as e:
        logger.exception("Error en search")
        return (
            jsonify({"error": "Error en la búsqueda", "results": [], "total": 0}),
            500,
        )


@main_bp.route("/api/restaurant/<int:restaurant_id>/evaluate", methods=["GET"])
def api_evaluate_restaurant(restaurant_id):
    """API para evaluar un restaurante específico"""
    try:
        restaurant = RestaurantModel.get_by_id(restaurant_id)
        if not restaurant:
            return jsonify({"error": "Restaurante no encontrado"}), 404

        user_profile = get_user_profile()

        if recommender:
            try:
                explanation = recommender.explain(restaurant, user_profile)
                return jsonify(
                    {
                        "restaurant_id": restaurant_id,
                        "explanation": explanation,
                        "user_profile": user_profile,
                    }
                )
            except Exception as e:
                logger.error(f"Error evaluando restaurante {restaurant_id}: {e}")
                return jsonify({"error": str(e)}), 500
        else:
            return jsonify({"error": "Sistema de recomendación no disponible"}), 503

    except Exception as e:
        logger.error(f"Error en api_evaluate_restaurant: {e}")
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/categories", methods=["GET"])
def api_categories():
    """API para obtener las categorías"""
    try:
        categories = load_categories()
        return jsonify(categories)
    except Exception as e:
        logger.error(f"Error en api_categories: {e}")
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/restaurants/nearby", methods=["GET"])
def api_nearby_restaurants():
    """API para obtener restaurantes cercanos"""
    try:
        lat = request.args.get("lat", type=float)
        lng = request.args.get("lng", type=float)
        radius = request.args.get("radius", Config.RADIO_MAXIMO_KM, type=float)

        if not valid_coordinate(lat, -90, 90) or not valid_coordinate(lng, -180, 180):
            return jsonify({"error": "Las coordenadas no son válidas"}), 400
        if radius is None or radius <= 0 or radius > 100:
            return jsonify({"error": "El radio debe estar entre 0 y 100 km"}), 400

        # ✅ SOLO restaurantes aprobados; filtros siempre aplicados en backend.
        all_restaurants = RestaurantModel.get_approved()
        category_id = request.args.get("category_id", type=int)
        max_price = request.args.get("max_price", type=float)
        min_rating = request.args.get("min_rating", type=float)
        available_only = request.args.get("available_only", "").lower() in {
            "1",
            "true",
            "yes",
        }
        filters = {
            "category_id": category_id,
            "max_price": max_price,
            "min_rating": min_rating,
        }
        filtered_restaurants = filter_restaurants(all_restaurants, filters)
        if available_only:
            filtered_restaurants = [
                restaurant
                for restaurant in filtered_restaurants
                if restaurant.get("is_available", restaurant.get("available", True))
                is not False
            ]
        enriched = enrich_with_metadata(filtered_restaurants, lat, lng)

        nearby = [r for r in enriched if r.get("distance_km", 999) <= radius]
        nearby = sorted(nearby, key=lambda x: x.get("distance_km", 999))

        return jsonify(
            {
                "results": nearby,
                "total": len(nearby),
                "center": {"lat": lat, "lng": lng},
                "radius": radius,
            }
        )

    except Exception as e:
        logger.error(f"Error en api_nearby_restaurants: {e}")
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/restaurants/top-rated", methods=["GET"])
def api_top_rated():
    """API para obtener los restaurantes mejor calificados"""
    try:
        limit = request.args.get("limit", 6, type=int)
        # ✅ SOLO restaurantes aprobados
        all_restaurants = RestaurantModel.get_approved()
        top_restaurants = sorted(
            all_restaurants, key=lambda x: x.get("rating", 0), reverse=True
        )[:limit]

        user_lat = request.args.get("lat", Config.COORDENADAS_CENTRO[0], type=float)
        user_lng = request.args.get("lng", Config.COORDENADAS_CENTRO[1], type=float)
        enriched = enrich_with_metadata(top_restaurants, user_lat, user_lng)

        return jsonify({"results": enriched, "total": len(enriched)})

    except Exception as e:
        logger.error(f"Error en api_top_rated: {e}")
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/save-location", methods=["POST"])
def save_location():
    """Guarda la ubicación del usuario en la sesión"""
    try:
        data = request.get_json(silent=True)
        coordinates = normalize_coordinates(
            data.get("lat") if isinstance(data, dict) else None,
            data.get("lng") if isinstance(data, dict) else None,
        )
        if coordinates:
            lat, lng = coordinates
            session["user_lat"] = lat
            session["user_lng"] = lng
            logger.info("Ubicación válida guardada en sesión")
            return jsonify(
                {
                    "success": True,
                    "message": "Ubicación guardada correctamente",
                    "location": {"lat": lat, "lng": lng},
                }
            )
        return (
            jsonify(
                {
                    "success": False,
                    "message": "Datos inválidos - se requieren lat y lng",
                }
            ),
            400,
        )
    except Exception as e:
        logger.error(f"Error guardando ubicación: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@main_bp.route("/api/reviews/<int:restaurant_id>", methods=["GET"])
def get_reviews(restaurant_id):
    """API para obtener reseñas de un restaurante"""
    try:
        from models.review import ReviewModel

        reviews = ReviewModel.get_by_restaurant(restaurant_id)
        stats = ReviewModel.get_rating_stats(restaurant_id)

        for review in reviews:
            user = UserModel.get_by_id(review.get("user_id"))
            if user:
                profile = user.get("profile", {})
                review["user_name"] = profile.get("name", "Usuario")
                review["user_avatar"] = profile.get("avatar", "")

        return jsonify({"success": True, "reviews": reviews, "stats": stats})
    except Exception as e:
        logger.error(f"Error obteniendo reseñas: {e}")
        return jsonify({"error": str(e), "success": False}), 500


@main_bp.route("/api/reviews", methods=["POST"])
def add_review():
    """API para agregar una reseña"""
    try:
        if "user" not in session or not session.get("user"):
            return jsonify({"error": "No autenticado"}), 401

        data = request.json
        restaurant_id = data.get("restaurant_id")
        rating = data.get("rating")
        comment = data.get("comment", "").strip()

        if not restaurant_id or not rating:
            return jsonify({"error": "Datos incompletos"}), 400

        if rating < 1 or rating > 5:
            return jsonify({"error": "Rating debe ser entre 1 y 5"}), 400

        user_id = session["user"].get("id")

        from models.review import ReviewModel

        review = ReviewModel.add_review(user_id, restaurant_id, rating, comment)

        if not review:
            return jsonify({"error": "Error al guardar la reseña"}), 500

        stats = ReviewModel.get_rating_stats(restaurant_id)
        restaurant = RestaurantModel.get_by_id(restaurant_id)
        if restaurant:
            restaurant["rating"] = stats["average"]
            RestaurantModel.update(restaurant_id, restaurant)

        return jsonify({"success": True, "review": review, "stats": stats})
    except Exception as e:
        logger.error(f"Error agregando reseña: {e}")
        return jsonify({"error": str(e), "success": False}), 500


@main_bp.route("/api/notifications")
def get_notifications():
    """API para obtener notificaciones del usuario"""
    if "user" not in session or not session.get("user"):
        return jsonify({"error": "No autenticado"}), 401

    user_id = session["user"].get("id")

    try:
        notifications = NotificationModel.get_by_user(user_id)
        unread_count = NotificationModel.get_unread_count(user_id)

        return jsonify(
            {
                "notifications": notifications,
                "unread_count": unread_count,
                "total": len(notifications),
            }
        )
    except Exception as e:
        logger.error(f"Error obteniendo notificaciones: {e}")
        return jsonify({"error": str(e), "notifications": []}), 500


@main_bp.route("/api/notifications/<int:notification_id>/read", methods=["POST"])
def mark_notification_read(notification_id):
    """Marcar una notificación como leída"""
    if "user" not in session or not session.get("user"):
        return jsonify({"error": "No autenticado"}), 401

    user_id = session["user"].get("id")

    try:
        result = NotificationModel.mark_as_read(user_id, notification_id)
        return jsonify({"success": result})
    except Exception as e:
        logger.error(f"Error marcando notificación como leída: {e}")
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/notifications/read-all", methods=["POST"])
def mark_all_notifications_read():
    """Marcar todas las notificaciones como leídas"""
    if "user" not in session or not session.get("user"):
        return jsonify({"error": "No autenticado"}), 401

    user_id = session["user"].get("id")

    try:
        result = NotificationModel.mark_all_as_read(user_id)
        return jsonify({"success": result})
    except Exception as e:
        logger.error(f"Error marcando todas las notificaciones como leídas: {e}")
        return jsonify({"error": str(e)}), 500


@main_bp.route("/api/dishes/search", methods=["GET"])
def search_dishes():
    """API para buscar platos"""
    try:
        query = request.args.get("q", "").strip()
        restaurant_id = request.args.get("restaurant_id", type=int)

        if not query and not restaurant_id:
            return jsonify({"error": "Se requiere query o restaurant_id"}), 400

        dishes = DishModel.all()

        if restaurant_id:
            dishes = [d for d in dishes if d.get("restaurant_id") == restaurant_id]

        if query:
            query = query.lower()
            dishes = [
                d
                for d in dishes
                if query in d.get("name", "").lower()
                or query in d.get("description", "").lower()
                or any(query in ing.lower() for ing in d.get("ingredients", []))
            ]

        return jsonify({"success": True, "dishes": dishes, "total": len(dishes)})

    except Exception as e:
        logger.error(f"Error buscando platos: {e}")
        return jsonify({"error": str(e)}), 500


# Manejadores de errores
@main_bp.app_errorhandler(404)
def not_found_error(error):
    return render_template("404.html", message="Página no encontrada"), 404


@main_bp.app_errorhandler(500)
def internal_error(error):
    return render_template("500.html", message="Error interno del servidor"), 500


@main_bp.route("/api/preguntar-ia", methods=["POST"])
def preguntar_ia():
    # Recibimos los datos en formato JSON desde el frontend
    datos = request.get_json()
    
    if not datos or "pregunta" not in datos:
        return jsonify({"error": "No se proporcionó ninguna pregunta"}), 400
    
    pregunta_usuario = datos["pregunta"]
    
    # Llamamos a nuestro servicio de IA
    respuesta_ia = obtener_recomendacion_ia(pregunta_usuario)
    
    # Devolvemos la respuesta al frontend
    return jsonify({"respuesta": respuesta_ia})
