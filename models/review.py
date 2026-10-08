# models/review.py
"""
Modelo para gestionar reseñas de restaurantes
Paradigma: Orientado a Objetos
"""
from models.base import JSONModel
from config import Config
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ReviewModel(JSONModel):
    """
    Modelo para gestionar reseñas de restaurantes
    Hereda de JSONModel para persistencia en archivo JSON
    """
    file_path = Config.REVIEWS_FILE if hasattr(Config, 'REVIEWS_FILE') else None
    
    @classmethod
    def get_by_restaurant(cls, restaurant_id):
        """
        Obtener todas las reseñas de un restaurante
        Args:
            restaurant_id: ID del restaurante
        Returns:
            list: Lista de reseñas del restaurante ordenadas por fecha
        """
        if not cls.file_path:
            return []
        data = cls._load_data()
        reviews = [r for r in data if r.get('restaurant_id') == restaurant_id]
        # Ordenar por fecha descendente (más recientes primero)
        reviews.sort(key=lambda x: x.get('created_at', ''), reverse=True)
        return reviews
    
    @classmethod
    def get_by_user(cls, user_id):
        """
        Obtener reseñas de un usuario
        Args:
            user_id: ID del usuario
        Returns:
            list: Lista de reseñas del usuario
        """
        if not cls.file_path:
            return []
        data = cls._load_data()
        return [r for r in data if r.get('user_id') == user_id]
    
    @classmethod
    def get_rating_stats(cls, restaurant_id):
        """
        Obtener estadísticas de rating de un restaurante
        Args:
            restaurant_id: ID del restaurante
        Returns:
            dict: Estadísticas con average, total y distribución
        """
        reviews = cls.get_by_restaurant(restaurant_id)
        if not reviews:
            return {
                'average': 0,
                'total': 0,
                'distribution': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            }
        
        total = len(reviews)
        avg = sum(r.get('rating', 0) for r in reviews) / total
        
        distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for r in reviews:
            rating = r.get('rating', 0)
            if rating in distribution:
                distribution[rating] += 1
        
        return {
            'average': round(avg, 1),
            'total': total,
            'distribution': distribution
        }
    
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
        if not cls.file_path:
            return None
        
        review_data = {
            'user_id': user_id,
            'restaurant_id': restaurant_id,
            'rating': rating,
            'comment': comment,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        return cls.create(review_data)
    
    @classmethod
    def update_review(cls, review_id, rating, comment):
        """
        Actualizar una reseña existente
        Args:
            review_id: ID de la reseña
            rating: Nueva calificación
            comment: Nuevo comentario
        Returns:
            dict: La reseña actualizada o None si no existe
        """
        if not cls.file_path:
            return None
        
        review = cls.get_by_id(review_id)
        if not review:
            return None
        
        review['rating'] = rating
        review['comment'] = comment
        review['updated_at'] = datetime.now().isoformat()
        
        return cls.update(review_id, review)
    
    @classmethod
    def delete_review(cls, review_id):
        """
        Eliminar una reseña
        Args:
            review_id: ID de la reseña
        Returns:
            bool: True si se eliminó, False en caso contrario
        """
        if not cls.file_path:
            return False
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
        if not cls.file_path:
            return []
        data = cls._load_data()
        sorted_reviews = sorted(data, key=lambda x: x.get('created_at', ''), reverse=True)
        return sorted_reviews[:limit]