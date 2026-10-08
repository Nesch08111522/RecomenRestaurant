# models/dish.py
from models.base import JSONModel
from config import Config
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DishModel(JSONModel):
    """Modelo para gestionar platos de restaurantes"""
    file_path = Config.DISHES_FILE
    
    @classmethod
    def get_by_restaurant(cls, restaurant_id):
        """Obtener todos los platos de un restaurante"""
        data = cls._load_data()
        return [d for d in data if d.get('restaurant_id') == restaurant_id]
    
    @classmethod
    def get_by_category(cls, restaurant_id, category):
        """Obtener platos de un restaurante por categoría"""
        dishes = cls.get_by_restaurant(restaurant_id)
        return [d for d in dishes if d.get('category') == category]
    
    @classmethod
    def search_by_ingredient(cls, ingredient):
        """Buscar platos por ingrediente"""
        data = cls._load_data()
        ingredient = ingredient.lower()
        return [d for d in data if any(ingredient in ing.lower() for ing in d.get('ingredients', []))]
    
    @classmethod
    def search_by_name(cls, query):
        """Buscar platos por nombre o descripción"""
        data = cls._load_data()
        query = query.lower()
        return [d for d in data if query in d.get('name', '').lower() or
                query in d.get('description', '').lower()]
    
    @classmethod
    def get_by_dietary(cls, dietary_restrictions):
        """Obtener platos que cumplan con restricciones dietéticas"""
        data = cls._load_data()
        if not dietary_restrictions:
            return data
        return [d for d in data if all(r in d.get('dietary_info', []) for r in dietary_restrictions)]
    
    @classmethod
    def get_available(cls, restaurant_id):
        """Obtener platos disponibles de un restaurante"""
        dishes = cls.get_by_restaurant(restaurant_id)
        return [d for d in dishes if d.get('is_available', True)]
    
    @classmethod
    def update_availability(cls, dish_id, is_available):
        """Actualizar disponibilidad de un plato"""
        dish = cls.get_by_id(dish_id)
        if dish:
            dish['is_available'] = is_available
            return cls.update(dish_id, dish)
        return None
    
    @classmethod
    def get_today_menu(cls, restaurant_id):
        """Obtener el menú del día para un restaurante"""
        today = datetime.now().strftime('%Y-%m-%d')
        from models.daily_menu import DailyMenuModel
        return DailyMenuModel.get_by_date(restaurant_id, today)