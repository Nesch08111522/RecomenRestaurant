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
            if (not business.get("verified") or business.get("status") in {"suspended", "archived"}
                    or channels and "Local" not in channels):
                raise MarketError("El negocio no admite reservas presenciales.")
            capacity = store.get("seats", 20)
            duration = store.get("table_minutes", 90)
            from logic.market import LIMA
            try:
                start = datetime.fromisoformat(date + "T" + time).replace(tzinfo=LIMA)
            except (TypeError, ValueError):
                raise MarketError("La fecha u hora no son validas.") from None
            if type(guests) is not int or not 1 <= guests <= 20:
                raise MarketError("El grupo debe tener entre 1 y 20 personas.")
            if not now() < start <= now() + timedelta(days=30):
                raise MarketError("Reserva un horario futuro dentro de los proximos 30 dias.")
            end = start + timedelta(minutes=duration)
            bookings = records("reservations", restaurant_id=restaurant_id)
            if any(r["user_id"] == user_id and r["date"] == date and r["time"] == time and r["guests"] == guests
                   and r["status"] != "cancelada" for r in bookings):
                return next(r for r in bookings if r["user_id"] == user_id and r["date"] == date and r["time"] == time
                            and r["guests"] == guests and r["status"] != "cancelada")
            occupied = 0
            for booking in bookings:
                existing = datetime.fromisoformat(booking["date"]+"T"+booking["time"]).replace(tzinfo=LIMA)
                if booking["status"] != "cancelada" and existing < end and existing + timedelta(minutes=booking.get("duration",duration)) > start:
                    occupied += booking["guests"]
            if occupied + guests > capacity:
                raise MarketError("No hay suficientes plazas para ese horario. Elige otra hora.")
            return super().create({"user_id":user_id,"restaurant_id":restaurant_id,"date":date,"time":time,
                                   "guests":guests,"duration":duration,"status":"pendiente","created_at":now().isoformat()})

    @classmethod
    def cancel_for_user(cls, reservation_id, user_id):
        from database.repository import PostgresDocumentRepository as Repo, document_transaction
        from logic.market import MarketError, LIMA, now
        from utils.audit import record_event
        with document_transaction():
            row = Repo.get_by_id(cls.collection, reservation_id, for_update=True)
            if not row or row.get("user_id") != user_id:
                raise MarketError("Reserva no disponible.")
            if row.get("status") == "cancelada":
                return row
            start = datetime.fromisoformat(row["date"] + "T" + row["time"]).replace(tzinfo=LIMA)
            if row.get("status") not in {"pendiente", "confirmada"} or start <= now():
                raise MarketError("Esta reserva ya no puede cancelarse.")
            result = cls.update(reservation_id, {"status": "cancelada", "cancelled_at": now().isoformat()})
            record_event("RESERVATION_CANCELLED", resource_type="reservation",
                         resource_id=reservation_id, actor_user_id=user_id)
            return result

    @classmethod
    def get_by_user(cls, user_id):
        return [item for item in cls.all() if item.get("user_id") == user_id]

    @classmethod
    def get_by_restaurant(cls, restaurant_id):
        return [item for item in cls.all() if item.get("restaurant_id") == restaurant_id]
