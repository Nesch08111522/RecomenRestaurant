"""User model backed by the Supabase PostgreSQL document collection."""

from models.base import DataModel
from werkzeug.security import generate_password_hash, check_password_hash


class UserModel(DataModel):
    collection = "users"

    @classmethod
    def authenticate(cls, username, password):
        """Authenticate a user by username and password."""
        data = cls._load_data()
        user = next((u for u in data if u.get("username") == username), None)

        if user and check_password_hash(user.get("password", ""), password):
            return user
        return None

    @classmethod
    def get_by_username(cls, username):
        """Find a user by username."""
        data = cls._load_data()
        return next((u for u in data if u.get("username") == username), None)

    @classmethod
    def register(cls, username, password, email, name, role="user"):
        """Register a new user."""
        if cls.get_by_username(username):
            return None

        user_data = {
            "username": username,
            "password": generate_password_hash(password),
            "role": role,
            "profile": {
                "name": name,
                "email": email,
                "preferences": [],
                "restrictions": [],
            },
        }

        return cls.create(user_data)

    @classmethod
    def get_favorites(cls, user_id):
        """Obtener favoritos de un usuario"""
        from models.favorite import FavoriteModel

        return FavoriteModel.get_by_user(user_id)

    @classmethod
    def is_admin(cls, user_id):
        """Verificar si un usuario es administrador"""
        user = cls.get_by_id(user_id)
        if not user:
            return False
        return user.get("role") == "admin"

    @classmethod
    def is_business_owner(cls, user_id):
        """Verificar si un usuario es empresario"""
        user = cls.get_by_id(user_id)
        if not user:
            return False
        return user.get("role") == "business_owner"

    @classmethod
    def can_manage_restaurant(cls, user_id, restaurant_id):
        """Verificar si un usuario puede gestionar un restaurante"""
        user = cls.get_by_id(user_id)
        if not user:
            return False

        # Admin puede gestionar todo
        if user.get("role") == "admin":
            return True

        # Empresario solo puede gestionar sus propios restaurantes
        if user.get("role") == "business_owner":
            from models.restaurant import RestaurantModel

            return RestaurantModel.is_owner(user_id, restaurant_id)

        return False

    # ---------- NUEVOS (los usa views/admin.py) ----------
    @classmethod
    def update_user(cls, user_id, changes):
        """Update a user and return the saved record, or None."""
        return cls.update(user_id, changes)

    @classmethod
    def delete_user(cls, user_id):
        """Delete a user by ID."""
        return cls.delete(user_id)
