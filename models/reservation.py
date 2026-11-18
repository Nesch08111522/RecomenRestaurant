"""Reservation collection stored in the Supabase PostgreSQL database."""

from datetime import datetime

from models.base import DataModel


class ReservationModel(DataModel):
    collection = "reservations"

    @classmethod
    def create(cls, user_id, restaurant_id, date, time, guests):
        from datetime import timedelta
        from logic.market import MarketError, now
        from models.market import kitchen, lock_business, records
        from database.repository import document_transaction
        with document_transaction():
            business = lock_business(restaurant_id)
            store = kitchen(restaurant_id)
            channels = business.get("market_channels")
            if not business.get("verified") or channels and "Local" not in channels:
                raise MarketError("El negocio no admite reservas presenciales.")
            capacity = store.get("seats", 20)
            duration = store.get("table_minutes", 90)
            start = datetime.fromisoformat(date + "T" + time)
            end = start + timedelta(minutes=duration)
            bookings = records("reservations", restaurant_id=restaurant_id)
            if any(r["user_id"] == user_id and r["date"] == date and r["time"] == time and r["guests"] == guests
                   and r["status"] != "cancelada" for r in bookings):
                return next(r for r in bookings if r["user_id"] == user_id and r["date"] == date and r["time"] == time
                            and r["guests"] == guests and r["status"] != "cancelada")
            occupied = 0
            for booking in bookings:
                existing = datetime.fromisoformat(booking["date"]+"T"+booking["time"])
                if booking["status"] != "cancelada" and existing < end and existing + timedelta(minutes=booking.get("duration",duration)) > start:
                    occupied += booking["guests"]
            if occupied + guests > capacity:
                raise MarketError("No hay suficientes plazas para ese horario. Elige otra hora.")
            return super().create({"user_id":user_id,"restaurant_id":restaurant_id,"date":date,"time":time,
                                   "guests":guests,"duration":duration,"status":"pendiente","created_at":now().isoformat()})

    @classmethod
    def get_by_user(cls, user_id):
        return [item for item in cls.all() if item.get("user_id") == user_id]

    @classmethod
    def get_by_restaurant(cls, restaurant_id):
        return [item for item in cls.all() if item.get("restaurant_id") == restaurant_id]
