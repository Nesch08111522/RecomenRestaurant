# models/__init__.py
from models.base import JSONModel
from models.user import UserModel
from models.restaurant import RestaurantModel
from models.favorite import FavoriteModel
from models.category import CategoryModel
from models.dish import DishModel
from models.daily_menu import DailyMenuModel
from models.notification import NotificationModel
from models.review import ReviewModel
from models.moderation import ModerationModel 

__all__ = [
    'JSONModel',
    'UserModel',
    'RestaurantModel',
    'FavoriteModel',
    'CategoryModel',
    'DishModel',
    'DailyMenuModel',
    'NotificationModel',
    'ReviewModel',
    'ModerationModel'  
]