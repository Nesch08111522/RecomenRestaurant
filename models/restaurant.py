from models.base import JSONModel
from config import Config

class RestaurantModel(JSONModel):
    file_path = Config.RESTAURANTS_FILE

    @classmethod
    def search(cls, query):
        data = cls.all()
        query = query.lower()
        return [r for r in data if query in r.get('name', '').lower() or 
                query in r.get('description', '').lower() or 
                any(query in tag.lower() for tag in r.get('tags', []))]

    @classmethod
    def filter_by_district(cls, district):
        data = cls.all()
        return [r for r in data if r.get('district', '').lower() == district.lower()]

    @classmethod
    def get_by_category(cls, category_id):
        data = cls.all()
        return [r for r in data if r.get('category_id') == category_id]

    @classmethod
    def get_top_rated(cls, n=6):
        data = cls.all()
        return sorted(data, key=lambda x: x.get('rating', 0), reverse=True)[:n]

    @classmethod
    def get_with_promotions(cls):
        data = cls.all()
        return [r for r in data if r.get('promo') is not None]
    
    @classmethod
    def get_by_ids(cls, ids):
        """Obtener restaurantes por lista de IDs"""
        data = cls.all()
        return [r for r in data if r.get('id') in ids]
    
    @classmethod
    def get_by_owner(cls, owner_id):
        """Obtener restaurantes de un dueño específico"""
        data = cls.all()
        return [r for r in data if r.get('owner_id') == owner_id]
    
    @classmethod
    def is_owner(cls, user_id, restaurant_id):
        """Verificar si un usuario es dueño de un restaurante"""
        restaurant = cls.get_by_id(restaurant_id)
        if not restaurant:
            return False
        return restaurant.get('owner_id') == user_id
    
    # ✅ NUEVO: Obtener solo restaurantes aprobados/verificados
    @classmethod
    def get_approved(cls):
        """Obtener solo restaurantes que han sido aprobados/verificados"""
        data = cls.all()
        return [r for r in data if r.get('verified', False)]
    
    # ✅ NUEVO: Obtener restaurantes pendientes de aprobación
    @classmethod
    def get_pending(cls):
        """Obtener restaurantes pendientes de aprobación"""
        data = cls.all()
        return [r for r in data if not r.get('verified', False)]