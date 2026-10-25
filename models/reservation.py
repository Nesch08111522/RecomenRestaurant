"""Reservation collection stored in the Supabase PostgreSQL database."""

from datetime import datetime

from models.base import DataModel


class ReservationModel(DataModel):
    collection = "reservations"

    @classmethod
    def create(cls, user_id, restaurant_id, date, time, guests):
        return super().create(
            {
                "user_id": user_id,
                "restaurant_id": restaurant_id,
                "date": date,
                "time": time,
                "guests": guests,
                "status": "pendiente",
                "created_at": datetime.now().isoformat(timespec="seconds"),
            }
        )

    @classmethod
    def get_by_user(cls, user_id):
        return [item for item in cls.all() if item.get("user_id") == user_id]

    @classmethod
    def get_by_restaurant(cls, restaurant_id):
        return [item for item in cls.all() if item.get("restaurant_id") == restaurant_id]
