# models/review.py
"""
Modelo para gestionar reseñas de restaurantes
Paradigma: Orientado a Objetos
"""
from models.base import DataModel
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ReviewModel(DataModel):
    """
    Modelo para gestionar reseñas de restaurantes
    Persists reviews in Supabase PostgreSQL.
    """
    collection = "reviews"
    
    @classmethod
    def get_by_user(cls, user_id):
        """Return only this user's reviews, newest first, for their profile."""
        reviews = [row for row in cls._load_data() if row.get('user_id') == user_id]
        return sorted(reviews, key=lambda row: row.get('created_at') or '', reverse=True)

    @classmethod
    def get_by_restaurant(cls, restaurant_id):
        """
        Obtener todas las reseñas de un restaurante
        Args:
            restaurant_id: ID del restaurante
        Returns:
            list: Lista de reseñas del restaurante ordenadas por fecha
        """
        data = cls._load_data()
        reviews = [r for r in data if r.get('restaurant_id') == restaurant_id]
        # Ordenar por fecha descendente (más recientes primero)
        reviews.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return reviews
    
    @classmethod
    def get_rating_stats(cls, restaurant_id, verified_only=True):
        """
        Estadísticas de rating. Por defecto solo cuenta reseñas verificadas
        (compra entregada y pagada) no ocultas ni rechazadas.
        """
        reviews = cls.get_by_restaurant(restaurant_id)
        if verified_only:
            reviews = [
                r for r in reviews
                if r.get("verified_purchase") is True
                and not r.get("hidden")
                and r.get("status") not in {"hidden", "rejected"}
            ]
        if not reviews:
            return {
                'average': 0,
                'total': 0,
                'distribution': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
            }
        total = len(reviews)
        avg = sum(r.get('rating', 0) for r in reviews) / total
        distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for r in reviews:
            rating = r.get('rating', 0)
            if rating in distribution:
                distribution[rating] += 1
        return {'average': round(avg, 1), 'total': total, 'distribution': distribution}
    
    @classmethod
    def get_average_rating(cls, restaurant_id):
        """
        Calcular el rating promedio de un restaurante
        Args:
            restaurant_id: ID del restaurante
        Returns:
            float: Rating promedio redondeado a 1 decimal
        """
        stats = cls.get_rating_stats(restaurant_id)
        return stats.get('average', 0)
    
    @classmethod
    def add_review(cls, user_id, restaurant_id, rating, comment):
        """
        Agregar una nueva reseña
        Args:
            user_id: ID del usuario
            restaurant_id: ID del restaurante
            rating: Calificación (1-5)
            comment: Comentario de la reseña
        Returns:
            dict: La reseña creada
        """
        review_data = {
            'user_id': user_id,
            'restaurant_id': restaurant_id,
            'rating': rating,
            'comment': comment,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        from database.repository import document_transaction
        from models.restaurant import RestaurantModel
        from models.notification import NotificationModel
        with document_transaction():
            review = cls.create(review_data)
            restaurant = RestaurantModel.get_by_id(restaurant_id) or {}
            if restaurant.get("owner_id"):
                NotificationModel.create_notification(restaurant["owner_id"], "Nueva reseña",
                    f"{restaurant.get('name', 'Tu negocio')} recibió una reseña.", link=f"/restaurant/{restaurant_id}")
            return review
    
    @classmethod
    def update_review(cls, review_id, rating, comment, reason=None):
        """Edita una reseña. Si estaba verificada y anclada, emite review.amended."""
        review = cls.get_by_id(review_id)
        if not review:
            return None

        previous_hash = review.get("anchor_hash")

        history = list(review.get("edit_history") or [])
        history.append({
            "at": datetime.now().isoformat(),
            "rating": review.get("rating"),
            "comment": review.get("comment"),
            "hash": previous_hash,
        })

        review["rating"] = rating
        review["comment"] = comment
        review["updated_at"] = datetime.now().isoformat()
        review["edit_history"] = history
        review["amended"] = True
        review["amend_reason"] = (reason or "")[:200]

        updated = cls.update(review_id, review)

        if review.get("verified_purchase") and review.get("order_id"):
            try:
                from database.repository import PostgresDocumentRepository
                from utils.blockchain_anchor import canonical_hash, KIND_AMENDED
                from utils.anchor_store import get_anchor_store

                order = PostgresDocumentRepository.get_by_id("market_orders", int(review["order_id"]))
                if not order:
                    cls.update(review_id, {"anchor_error": "order_not_found"})
                    return updated

                anchored = {**updated, "order_id": int(review["order_id"])}
                new_hash = canonical_hash(anchored, order, kind=KIND_AMENDED, prev_hash=previous_hash)
                get_anchor_store().add_pending(
                    anchored,
                    order,
                    new_hash,
                    kind=KIND_AMENDED,
                    prev_hash=previous_hash,
                )
                cls.update(review_id, {"anchor_hash": new_hash, "anchor_error": None})
            except Exception:
                logger.exception(
                    "No se pudo anclar la edición de la reseña %s", review_id
                )
                cls.update(review_id, {"anchor_error": "anchor_failed"})

        return updated

    @classmethod
    def delete_review(cls, review_id):
        """
        Eliminar una reseña
        Args:
            review_id: ID de la reseña
        Returns:
            bool: True si se eliminó, False en caso contrario
        """
        return cls.delete(review_id)
    
    @classmethod
    def get_recent_reviews(cls, limit=10):
        """
        Obtener las reseñas más recientes
        Args:
            limit: Número máximo de reseñas a retornar
        Returns:
            list: Lista de reseñas recientes
        """
        data = cls._load_data()
        sorted_reviews = sorted(data, key=lambda x: x.get('created_at', ''), reverse=True)
        return sorted_reviews[:limit]


