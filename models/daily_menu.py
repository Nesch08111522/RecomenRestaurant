# models/daily_menu.py
from models.base import JSONModel
from config import Config
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DailyMenuModel(JSONModel):
    """Modelo para gestionar menús diarios"""
    file_path = Config.DAILY_MENU_FILE
    
    @classmethod
    def get_by_restaurant(cls, restaurant_id):
        """Obtener todos los menús diarios de un restaurante"""
        data = cls._load_data()
        return [m for m in data if m.get('restaurant_id') == restaurant_id]
    
    @classmethod
    def get_by_date(cls, restaurant_id, date):
        """Obtener menú diario por fecha"""
        data = cls._load_data()
        menus = [m for m in data if m.get('restaurant_id') == restaurant_id and m.get('date') == date]
        return menus[0] if menus else None
    
    @classmethod
    def get_active(cls, restaurant_id):
        """Obtener menú diario activo"""
        data = cls._load_data()
        today = datetime.now().strftime('%Y-%m-%d')
        menus = [m for m in data if m.get('restaurant_id') == restaurant_id and 
                 m.get('date') == today and m.get('is_active', True)]
        return menus[0] if menus else None
    
    @classmethod
    def create_or_update(cls, restaurant_id, date, dishes, specials=None, price=None):
        """Crear o actualizar menú diario"""
        existing = cls.get_by_date(restaurant_id, date)
        
        menu_data = {
            'restaurant_id': restaurant_id,
            'date': date,
            'day_of_week': datetime.strptime(date, '%Y-%m-%d').strftime('%A').lower(),
            'type': 'daily',
            'dishes': dishes,
            'specials': specials or [],
            'price': price or 0,
            'is_active': True,
            'updated_at': datetime.now().isoformat()
        }
        
        if existing:
            menu_data['id'] = existing.get('id')
            return cls.update(existing.get('id'), menu_data)
        else:
            menu_data['created_at'] = datetime.now().isoformat()
            return cls.create(menu_data)
    
    @classmethod
    def deactivate(cls, menu_id):
        """Desactivar un menú diario"""
        menu = cls.get_by_id(menu_id)
        if menu:
            menu['is_active'] = False
            return cls.update(menu_id, menu)
        return None