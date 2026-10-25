from datetime import datetime

from database.connection import connection
from models.base import DataModel

try:
    from psycopg.types.json import Jsonb
except ImportError:  # pragma: no cover - PostgreSQL backend requires psycopg
    Jsonb = None


class FavoriteModel(DataModel):
    """Manage user favorites in the PostgreSQL ``favorites`` collection."""

    collection = "favorites"

    @classmethod
    def get_by_user(cls, user_id):
        return [item for item in cls.all() if item.get("user_id") == user_id]

    @classmethod
    def get_by_user_and_restaurant(cls, user_id, restaurant_id):
        return next(
            (
                item
                for item in cls.all()
                if item.get("user_id") == user_id
                and item.get("restaurant_id") == restaurant_id
            ),
            None,
        )

    @classmethod
    def toggle(cls, user_id, restaurant_id):
        """Atomically toggle one favorite; return True when it was added."""
        if not user_id or not restaurant_id:
            return False
        if Jsonb is None:
            raise RuntimeError("La dependencia psycopg no está instalada.")

        lock_key = f"favorite:{user_id}:{restaurant_id}"
        with connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (lock_key,))
            cur.execute(
                """SELECT id FROM public.app_records
                   WHERE collection = %s
                     AND payload->>'user_id' = %s
                     AND payload->>'restaurant_id' = %s
                   ORDER BY id LIMIT 1 FOR UPDATE""",
                (cls.collection, str(user_id), str(restaurant_id)),
            )
            existing = cur.fetchone()
            if existing:
                cur.execute(
                    "DELETE FROM public.app_records WHERE collection = %s AND id = %s",
                    (cls.collection, existing["id"]),
                )
                conn.commit()
                return False

            item = {
                "user_id": user_id,
                "restaurant_id": restaurant_id,
                "timestamp": datetime.now().isoformat(),
            }
            cur.execute(
                "INSERT INTO public.app_records (collection, payload) VALUES (%s, %s) RETURNING id",
                (cls.collection, Jsonb(item)),
            )
            item_id = cur.fetchone()["id"]
            item["id"] = item_id
            cur.execute(
                "UPDATE public.app_records SET payload = %s WHERE collection = %s AND id = %s",
                (Jsonb(item), cls.collection, item_id),
            )
            conn.commit()
            return True

    @classmethod
    def get_favorite_restaurant_ids(cls, user_id):
        return [
            favorite.get("restaurant_id")
            for favorite in cls.get_by_user(user_id)
            if favorite.get("restaurant_id")
        ]

    @classmethod
    def count_by_user(cls, user_id):
        return len(cls.get_by_user(user_id))
