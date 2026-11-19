"""Datos de prueba explícitos para las fases 8 a 12 (nunca datos de producción)."""
from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

from database.repository import PostgresDocumentRepository as Repo
from logic.market import now
from models.dish import DishModel
from models.market import kitchen, save_kitchen
from models.restaurant import RestaurantModel
from models.user import UserModel


def make_user(username="ana", role="user", name="Ana Torres", profile=None):
    return UserModel.create({
        "username": username, "role": role, "status": "ACTIVE",
        "profile": {"name": name, "email": f"{username}@example.test", **(profile or {})},
        "auth_epoch": 0,
    })


def make_business(owner_id, name="Sabor Norteño", channels=("Local",), verified=True):
    return RestaurantModel.create({
        "owner_id": owner_id, "name": name, "verified": verified,
        "status": "active", "district": "Trujillo", "description": "Cocina de prueba",
        "market_channels": list(channels),
    })


def make_store(rid, pantry=None, team=None, channels=("Local",), table_minutes=90):
    store = kitchen(rid)
    store.update({
        "channels": list(channels), "kind": "Restaurante", "team": list(team or []),
        "team_names": "", "zones": [], "pickup": "Av. Prueba 100", "pin": None,
        "radius": 0, "capacity": 20, "lead": 0, "loyalty": 0, "reward": 0,
        "seats": 20, "table_minutes": table_minutes,
        "pantry": pantry or {
            "arroz": {"quantity": 5000, "expires": (now().date() + timedelta(days=20)).isoformat(),
                      "unit": "g", "cost": 500, "basis": 1000, "substitutes": [], "lot": uuid4().hex},
        },
    })
    save_kitchen(store)
    return store


def make_dish(rid, name="Arroz con pollo", price=18):
    return DishModel.create({
        "restaurant_id": rid, "name": name, "price": price, "category": "Fondo",
        "description": "Plato de prueba", "ingredients": ["arroz", "pollo"],
        "allergens": [], "is_available": True, "tags": [], "meal_time": "almuerzo",
    })


def make_offer(rid, dish, stock=10, price=1800):
    at = now()
    offer = Repo.create("market_offers", {
        "rid": rid, "dish_id": dish["id"], "day": at.date().isoformat(), "stock": stock,
        "price": price, "recipe": {"arroz": 100}, "diets": [], "context_tags": [],
        "seasons": [], "variant": "", "name": dish["name"], "occasion": "Almuerzo",
        "cross": "declared", "ends": (at + timedelta(days=1)).isoformat(),
        "rescue_price": None, "rescue_until": None, "allergens": [], "origin": "Cocina de prueba",
        "preparation": "Prueba", "prepared": at.isoformat(), "review_state": "approved",
        "produced": stock, "created": at.isoformat(), "paused": False,
    })
    return offer


def login(client, user):
    from utils.security import session_identity
    with client.session_transaction() as flask_session:
        flask_session["user_id"] = user["id"]
        flask_session["user"] = session_identity(user)
        flask_session["role"] = user["role"]
        flask_session["username"] = user["username"]
        flask_session["auth_epoch"] = user.get("auth_epoch", 0)