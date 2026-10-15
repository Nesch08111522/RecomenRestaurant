"""Modelo de reservas (almacenamiento en JSON, mismo enfoque que el resto de modelos)."""

import json
import os
import threading
from datetime import datetime

from config import Config

_lock = threading.Lock()


def _file_path():
    data_dir = getattr(Config, "DATA_DIR", None) or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"
    )
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, "reservations.json")


class ReservationModel:
    @staticmethod
    def all():
        path = _file_path()
        if not os.path.exists(path):
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except (json.JSONDecodeError, OSError):
            return []

    @staticmethod
    def create(user_id, restaurant_id, date, time, guests):
        """Crea una reserva y la devuelve. Retorna None si falla el guardado."""
        with _lock:
            reservations = ReservationModel.all()
            new_id = max((r.get("id", 0) for r in reservations), default=0) + 1
            reservation = {
                "id": new_id,
                "user_id": user_id,
                "restaurant_id": restaurant_id,
                "date": date,
                "time": time,
                "guests": guests,
                "status": "pendiente",
                "created_at": datetime.now().isoformat(timespec="seconds"),
            }
            reservations.append(reservation)

            path = _file_path()
            tmp_path = path + ".tmp"
            try:
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(reservations, f, ensure_ascii=False, indent=2)
                os.replace(tmp_path, path)
            except OSError:
                return None
            return reservation

    @staticmethod
    def get_by_user(user_id):
        return [r for r in ReservationModel.all() if r.get("user_id") == user_id]

    @staticmethod
    def get_by_restaurant(restaurant_id):
        return [
            r for r in ReservationModel.all() if r.get("restaurant_id") == restaurant_id
        ]
