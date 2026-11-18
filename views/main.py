from flask import (
    Blueprint,
    abort,
    render_template,
    request,
    jsonify,
    session,
    flash,
    redirect,
    url_for,
)


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
    get_statistics,
)
from logic.recommender import RecommenderEngine
from logic.hybrid_recommender import recommend as hybrid_recommend
from models.review import ReviewModel
from config import Config
from database.repository import document_transaction, PostgresDocumentRepository
from database.connection import DatabaseConfigurationError, DatabaseConnectionError
from utils.security import csrf, valid_coordinate
from utils.geo import calculate_distance, normalize_coordinates
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
    from flask import g
    user_profile = {}
    user_data = session.get("user")
    if user_data:
        profile = getattr(g, "account_record", user_data).get("profile") or {}
        user_profile = {field: profile.get(field, []) for field in ("restrictions", "preferences")}
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
        if user_lat is not None and user_lng is not None:
            restaurants = enrich_with_metadata(restaurants, user_lat, user_lng)

        from flask import g
        from models.market import catalog, records, food_preferences
        from logic.market_discovery import discover
        account = getattr(g, "account_record", {})
        picks, _ = discover(catalog(), {}, food_preferences(account),
                           records("market_orders", uid=account["id"]) if account else [])
        by_restaurant = {str(row["id"]): row for row in restaurants}
        verified = [(review, by_restaurant[str(review["restaurant_id"])])
                    for review in ReviewModel.all()
                    if review.get("verified_purchase") and review.get("comment")
                    and str(review.get("restaurant_id")) in by_restaurant
                    and not review.get("hidden") and review.get("status") not in {"rejected", "hidden"}]
        new_businesses = sorted((row for row in restaurants if row.get("created_at")),
                                key=lambda row: row["created_at"], reverse=True)[:3]
        return render_template(
            "index.html", home_offers=picks[:3],
            home_new=new_businesses, home_reviews=sorted(verified, key=lambda item: item[0].get("created_at", ""), reverse=True)[:3],
            restaurants=restaurants,
            categories=categories,
            stats=stats,
            user_profile=get_user_profile(),
        )
    except Exception as e:
        logger.exception(f"Error en index: {e}")
        abort(500)


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
        if None not in (user_lat, user_lng, restaurant.get("lat"), restaurant.get("lng")):
            distance = calculate_distance(
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
            table_service=("Local" in restaurant["market_channels"] if restaurant.get("market_channels")
                           else restaurant.get("service_mode") not in {"delivery_only", "pickup_only"}),
            verified_reviews=[r for r in ReviewModel.get_by_restaurant(restaurant_id) if r.get("verified_purchase") and not r.get("hidden") and r.get("status") not in {"hidden","rejected"}][:5],
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
    table_service = ("Local" in restaurant["market_channels"] if restaurant.get("market_channels")
                     else restaurant.get("service_mode") not in {"delivery_only", "pickup_only"})
    if not table_service:
        flash("Este negocio recibe pedidos por el mercado.", "info")
        return redirect(url_for("market.browse", negocio=restaurant_id))
    time_str = (request.form.get("time") or "").strip()
    guests = request.form.get("guests", type=int)

    try:
        reservation_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M").replace(tzinfo=LIMA_TIMEZONE)
    except ValueError:
        flash("La fecha u hora no son válidas.", "error")
        return redirect(detail_url)

    if reservation_dt < datetime.now(LIMA_TIMEZONE):
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
    except ValueError as error:
        flash(str(error), "warning")
        return redirect(detail_url)
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
        today = datetime.now(LIMA_TIMEZONE).date().isoformat()
        all_dishes = [d for d in DishModel.all() if not d.get('menu_date') or d['menu_date'] == today]
        if filters.get('available_only'):
            all_dishes = [d for d in all_dishes if d.get('is_available') is True
                          and d.get('availability', 'available') == 'available']
        if filters.get('business_type') or filters.get('channel'):
            stores = {k['id']: k for k in PostgresDocumentRepository.all('market_kitchens')}
            all_restaurants = [dict(r, market_kind=stores.get(r['id'], {}).get('kind', r.get('market_kind', '')),
                                    market_channels=stores.get(r['id'], {}).get('channels', r.get('market_channels', [])))
                               for r in all_restaurants]
        all_restaurants = [dict(r, is_available=any(d.get('restaurant_id') == r['id']
                           and d.get('is_available') is True for d in all_dishes)) for r in all_restaurants]
        if 'lat' not in filters and 'lng' not in filters:
            filters = {**filters, 'lat': session.get('user_lat'), 'lng': session.get('user_lng')}

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

        for restaurant in restaurants:
            restaurant['matching_dishes'] = [d for d in all_dishes if d.get('restaurant_id') == restaurant['id']
                and (not dish_query or dish_query in (d.get('name', '') + ' ' + d.get('description', '')
                     + ' ' + ' '.join(d.get('ingredients') or [])).lower())
                and (not ingredient_filter or any(ingredient_filter in ing.lower() for ing in d.get('ingredients') or []))]

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

        sort_by = filters.get('sort_by')
        if sort_by in {'rating', 'price', 'distance'}:
            field = {'rating': 'rating', 'price': 'avg_price', 'distance': 'distance_km'}[sort_by]
            ranked.sort(key=lambda r: (r.get(field) is None, -(r.get(field) or 0) if sort_by == 'rating'
                                      else r.get(field, float('inf'))))

        # Compatibilidad: el contrato histórico devuelve directamente una lista.
        # Los metadatos se mantienen en cabeceras para clientes que los necesiten.
        if "page" in filters or "per_page" in filters:
            try:
                page = max(1, int(filters.get("page", 1)))
                size = min(100, max(1, int(filters.get("per_page", 20))))
            except (TypeError, ValueError, OverflowError):
                return jsonify({"error": "Paginación inválida"}), 400
            response = jsonify(ranked[(page - 1) * size:page * size])
        else:
            response = jsonify(ranked)
        response.headers["X-Search-Total"] = str(len(ranked))
        return response

    except (ValueError, TypeError, AttributeError) as e:
        return jsonify(error='Filtros invalidos', results=[]), 400
    except (DatabaseConfigurationError, DatabaseConnectionError):
        return jsonify(error='Catalogo temporalmente no disponible'), 503
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
        if not restaurant or not restaurant.get("verified"):
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
                return jsonify({"error": "Error interno del servidor."}), 500
        else:
            return jsonify({"error": "Sistema de recomendación no disponible"}), 503

    except Exception as e:
        logger.error(f"Error en api_evaluate_restaurant: {e}")
        return jsonify({"error": "Error interno del servidor."}), 500


@main_bp.route("/api/categories", methods=["GET"])
def api_categories():
    """API para obtener las categorías"""
    try:
        categories = load_categories()
        return jsonify(categories)
    except Exception as e:
        logger.error(f"Error en api_categories: {e}")
        return jsonify({"error": "Error interno del servidor."}), 500


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

        nearby = [r for r in enriched if r.get('distance_km') is not None and r['distance_km'] <= radius]
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
        return jsonify({"error": "Error interno del servidor."}), 500


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
        return jsonify({"error": "Error interno del servidor."}), 500


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
        return jsonify({"success": False, "message": "Error interno del servidor."}), 500


@main_bp.route("/api/reviews", methods=["POST"])
def add_review():
    """API para agregar una reseña"""
    try:
        if "user" not in session or not session.get("user"):
            return jsonify({"error": "No autenticado"}), 401

        data = request.get_json(silent=True)
        if not isinstance(data, dict) or set(data) - {"restaurant_id", "rating", "comment"}:
            return jsonify({"error": "Reseña inválida"}), 400
        restaurant_id = data.get("restaurant_id")
        rating = data.get("rating")
        comment = data.get("comment", "")
        if isinstance(restaurant_id, str) and restaurant_id.isascii() and restaurant_id.isdecimal() and len(restaurant_id) <= 19:
            restaurant_id = int(restaurant_id)
        if type(restaurant_id) is not int or not 0 < restaurant_id < 2**63 or not isinstance(comment, str):
            return jsonify({"error": "Restaurante o comentario inválido"}), 400
        try:
            if isinstance(rating, bool):
                raise ValueError
            rating = float(rating)
        except (TypeError, ValueError, OverflowError):
            return jsonify({"error": "La calificación debe ser numérica"}), 400
        if not 1 <= rating <= 5:
            return jsonify({"error": "La calificación debe ser un número entre 1 y 5"}), 400
        with document_transaction():
            restaurant = PostgresDocumentRepository.get_by_id(
                RestaurantModel.collection, restaurant_id, for_update=True
            )
            if not restaurant or not restaurant.get("verified"):
                return jsonify({"error": "Restaurante no disponible"}), 404
            from models.market import records
            purchases = [o for o in records("market_orders",uid=session["user"]["id"],rid=restaurant_id,state="Entregado",paid=True)
                         if not o.get("refunded") and not o.get("review")]
            if not purchases:
                return jsonify({"error":"Se requiere una compra pagada y entregada sin valoración previa."}), 403
            order = purchases[0]
            locked = PostgresDocumentRepository.get_by_id("market_orders", order["id"], for_update=True)
            if not locked or locked.get("review"):
                return jsonify({"error": "Esta compra ya fue valorada."}), 409
            review = ReviewModel.add_review(session["user"]["id"], restaurant_id, rating, comment.strip())
            ReviewModel.update(review["id"], {"verified_purchase":True,"order_id":order["id"]})
            PostgresDocumentRepository.update("market_orders",order["id"],{"review":review["id"]})
            stats = ReviewModel.get_rating_stats(restaurant_id)
            RestaurantModel.update(restaurant_id, {"rating": stats["average"]})
            try:
                from utils.blockchain_anchor import canonical_hash
                from utils.anchor_store import get_anchor_store
                anchored_review = {**review, "order_id": order["id"]}
                get_anchor_store().add_pending(
                    anchored_review,
                    locked,
                    canonical_hash(anchored_review, locked),
                )
            except Exception:
                logger.exception(
                    "No se pudo encolar el ancla de la reseña %s", review.get("id")
                )

            return jsonify({"success": True, "review": review, "stats": stats})
    except Exception as e:
        logger.error(f"Error agregando reseña: {e}")
        return jsonify({"error": "Error interno del servidor.", "success": False}), 500
    
    @main_bp.get("/api/trust/verify/<int:review_id>")
    def verify_anchor(review_id):
        """Estado público del ancla de una reseña. Solo lectura, sin cache."""
        from utils.anchor_store import get_anchor_store

        row = get_anchor_store().get_by_review(review_id)
        if not row:
            response = jsonify({"found": False, "verified_onchain": False})
            response.status_code = 404
            response.headers["Cache-Control"] = "no-store"
            return response

        response = jsonify({
            "found": True,
            "review_id": int(review_id),
            "hash": row.get("hash"),
            "kind": row.get("kind"),
            "status": row.get("status"),
            "tx_hash": row.get("tx_hash"),
            "verified_onchain": row.get("status") == "confirmed",
        })
        response.headers["Cache-Control"] = "no-store"
        return response

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
        return jsonify({"error": "Error interno del servidor.", "notifications": []}), 500


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
        return jsonify({"error": "Error interno del servidor."}), 500


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
        return jsonify({"error": "Error interno del servidor."}), 500


@main_bp.route("/api/dishes/search", methods=["GET"])
def search_dishes():
    """API para buscar platos"""
    try:
        query = request.args.get("q", "").strip()
        restaurant_id = request.args.get("restaurant_id", type=int)

        if not query and not restaurant_id:
            return jsonify({"error": "Se requiere query o restaurant_id"}), 400

        approved = {r["id"] for r in RestaurantModel.get_approved()}
        today = datetime.now(LIMA_TIMEZONE).date().isoformat()
        dishes = [d for d in DishModel.all() if d.get("restaurant_id") in approved
                  and d.get("is_available", True) and (not d.get("menu_date") or d["menu_date"] == today)]

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
        return jsonify({"error": "Error interno del servidor."}), 500


@main_bp.get('/explorar')
def explore_catalog():
    from logic.market import BUSINESSES
    return render_template('catalog/explore.html', categories=CategoryModel.all(), business_types=BUSINESSES)


@main_bp.get('/api/catalog/compare')
def compare_catalog():
    kind = request.args.get('kind', 'business')
    try:
        ids = list(dict.fromkeys(int(value) for value in request.args.get('ids', '').split(',')))
    except ValueError:
        return jsonify(error='Identificadores invalidos'), 400
    if kind not in {'business', 'product'} or not 2 <= len(ids) <= 4 or any(i <= 0 for i in ids):
        return jsonify(error='Selecciona entre dos y cuatro fichas'), 400
    approved = {r['id']: r for r in RestaurantModel.get_approved()}
    if kind == 'business':
        rows = approved
        fields = ('id', 'name', 'district', 'avg_price', 'rating', 'promo', 'open_time', 'close_time', 'market_channels')
    else:
        today = datetime.now(LIMA_TIMEZONE).date().isoformat()
        rows = {d['id']: d for d in DishModel.all() if d.get('restaurant_id') in approved
                and (not d.get('menu_date') or d['menu_date'] == today)}
        fields = ('id', 'restaurant_id', 'name', 'price', 'ingredients', 'allergens', 'availability', 'is_available')
    if any(i not in rows for i in ids):
        abort(404)
    return jsonify(kind=kind, results=[{field: rows[i].get(field) for field in fields} for i in ids])


@main_bp.get('/api/catalog/products/<int:product_id>')
def product_card(product_id):
    product = DishModel.get_by_id(product_id)
    approved = {r['id']: r for r in RestaurantModel.get_approved()}
    today = datetime.now(LIMA_TIMEZONE).date().isoformat()
    if not product or product.get('restaurant_id') not in approved or (product.get('menu_date') and product['menu_date'] != today):
        abort(404)
    fields = ('id', 'restaurant_id', 'name', 'description', 'price', 'ingredients', 'allergens',
              'images', 'availability', 'is_available', 'ingredients_confirmed', 'allergens_confirmed')
    return jsonify(product={field: product.get(field) for field in fields},
                   business_url=url_for('main.detail', restaurant_id=product['restaurant_id']))


@main_bp.get('/api/catalog/<int:restaurant_id>/map')
def business_map(restaurant_id):
    from models.market import kitchen
    restaurant = next((r for r in RestaurantModel.get_approved() if r['id'] == restaurant_id), None)
    if not restaurant:
        abort(404)
    store = kitchen(restaurant_id)
    # A kitchen pin is explicitly public; do not fall back to a hidden home's address.
    pin = store.get('pin')
    point = normalize_coordinates(*pin) if isinstance(pin, (list, tuple)) and len(pin) == 2 else None
    if not point and not store.get('kind'):
        point = normalize_coordinates(restaurant.get('lat'), restaurant.get('lng'))
    origin = normalize_coordinates(request.args.get('lat', session.get('user_lat')),
                                   request.args.get('lng', session.get('user_lng')))
    if ('lat' in request.args or 'lng' in request.args) and not origin:
        return jsonify(error='Coordenadas invalidas'), 400
    route = None
    if origin and point:
        route = 'https://www.openstreetmap.org/directions?engine=fossgis_osrm_car&route=' + quote(
            f'{origin[0]},{origin[1]};{point[0]},{point[1]}', safe='')
    radius = store.get('radius', 0)
    return jsonify(id=restaurant_id, point=point, pickup=store.get('pickup') or None,
                   zones=store.get('zones', []), radius_km=radius,
                   district=restaurant.get('district'), route_url=route,
                   distance_km=calculate_distance(*origin, *point) if origin and point else None,
                   distance_method='straight_line',
                   delivery_covered=(calculate_distance(*origin, *point) <= radius
                                     if origin and point and radius else None))


@main_bp.get("/informacion/<section>")
def information(section):
    if section not in {"privacidad", "condiciones"}:
        abort(404)
    return render_template("information.html", section=section)
