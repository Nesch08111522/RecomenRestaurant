# models/category.py
from models.base import JSONModel
from config import Config

class CategoryModel(JSONModel):
    file_path = Config.CATEGORIES_FILE
    
    @classmethod
    def get_by_id(cls, category_id):
        data = cls._load_data()
        return next((cat for cat in data if cat.get('id') == category_id), None)
    
    @classmethod
    def get_by_slug(cls, slug):
        data = cls._load_data()
        return next((cat for cat in data if cat.get('slug') == slug), None)
    
    @classmethod
    def get_all_names(cls):
        data = cls._load_data()
        return {cat['id']: cat['name'] for cat in data}