from models.base import JSONModel
from config import Config
import json
import os
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class FavoriteModel(JSONModel):
    """Modelo para gestionar favoritos de usuarios"""
    file_path = Config.FAVORITES_FILE
    
    @classmethod
    def _ensure_file_exists(cls):
        """Asegura que el archivo de favoritos existe"""
        try:
            os.makedirs(os.path.dirname(cls.file_path), exist_ok=True)
            
            if not os.path.exists(cls.file_path):
                with open(cls.file_path, 'w', encoding='utf-8') as f:
                    json.dump([], f, indent=2, ensure_ascii=False)
                logger.info(f"📁 Archivo de favoritos creado: {cls.file_path}")
        except Exception as e:
            logger.error(f"Error creando archivo de favoritos: {e}")
    
    @classmethod
    def _load_data(cls):
        """Sobrescribe para asegurar que el archivo existe"""
        cls._ensure_file_exists()
        try:
            with open(cls.file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            with open(cls.file_path, 'w', encoding='utf-8') as f:
                json.dump([], f, indent=2, ensure_ascii=False)
            return []
        except Exception as e:
            logger.error(f"Error cargando datos: {e}")
            return []
    
    @classmethod
    def _save_data(cls, data):
        """Guarda datos al archivo JSON"""
        try:
            cls._ensure_file_exists()
            with open(cls.file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error guardando datos: {e}")
    
    @classmethod
    def get_by_user(cls, user_id):
        """Obtener todos los favoritos de un usuario"""
        try:
            data = cls._load_data()
            return [item for item in data if item.get('user_id') == user_id]
        except Exception as e:
            logger.error(f"Error obteniendo favoritos del usuario {user_id}: {e}")
            return []
    
    @classmethod
    def get_by_user_and_restaurant(cls, user_id, restaurant_id):
        """Obtener un favorito específico"""
        try:
            data = cls._load_data()
            return next(
                (item for item in data 
                 if item.get('user_id') == user_id and item.get('restaurant_id') == restaurant_id),
                None
            )
        except Exception as e:
            logger.error(f"Error obteniendo favorito: {e}")
            return None
    
    @classmethod
    def toggle(cls, user_id, restaurant_id):
        """
        Alternar favorito (agregar si no existe, eliminar si existe)
        Retorna True si se agregó, False si se eliminó
        """
        try:
            if not user_id or not restaurant_id:
                logger.error(f"ID inválido: user_id={user_id}, restaurant_id={restaurant_id}")
                return False
            
            existing = cls.get_by_user_and_restaurant(user_id, restaurant_id)
            
            if existing:
                data = cls._load_data()
                data = [item for item in data if not (
                    item.get('user_id') == user_id and item.get('restaurant_id') == restaurant_id
                )]
                cls._save_data(data)
                logger.info(f"✅ Favorito eliminado: usuario {user_id}, restaurante {restaurant_id}")
                return False
            else:
                new_favorite = {
                    'user_id': user_id,
                    'restaurant_id': restaurant_id,
                    'timestamp': datetime.now().isoformat()
                }
                cls.create(new_favorite)
                logger.info(f"✅ Favorito agregado: usuario {user_id}, restaurante {restaurant_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error al alternar favorito: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    @classmethod
    def get_favorite_restaurant_ids(cls, user_id):
        """Obtener lista de IDs de restaurantes favoritos"""
        try:
            favorites = cls.get_by_user(user_id)
            return [fav.get('restaurant_id') for fav in favorites if fav.get('restaurant_id')]
        except Exception as e:
            logger.error(f"Error obteniendo IDs de favoritos: {e}")
            return []
    
    @classmethod
    def count_by_user(cls, user_id):
        """Contar cuántos favoritos tiene un usuario"""
        try:
            return len(cls.get_by_user(user_id))
        except Exception as e:
            logger.error(f"Error contando favoritos: {e}")
            return 0