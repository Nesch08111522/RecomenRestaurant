from __future__ import annotations

import logging
import math
import time
from typing import Any

from geopy.geocoders import Nominatim
from haversine import haversine

logger = logging.getLogger(__name__)
_geocode_cache: dict[str, str] = {}


def valid_coordinate(value: Any, minimum: float, maximum: float) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(number) and minimum <= number <= maximum


def normalize_coordinates(lat: Any, lng: Any) -> tuple[float, float] | None:
    if not valid_coordinate(lat, -90, 90) or not valid_coordinate(lng, -180, 180):
        return None
    return round(float(lat), 7), round(float(lng), 7)


def calculate_distance(lat1: Any, lon1: Any, lat2: Any, lon2: Any) -> float:
    """Distancia aproximada en km; 999.99 significa coordenada no disponible."""
    origin = normalize_coordinates(lat1, lon1)
    destination = normalize_coordinates(lat2, lon2)
    if not origin or not destination:
        return 999.99
    try:
        return round(float(haversine(origin, destination)), 2)
    except (TypeError, ValueError):
        return 999.99


def get_address_from_coords(lat: Any, lng: Any) -> str:
    """Geocodificación opcional y cacheada; no se ejecuta en cada búsqueda."""
    coordinates = normalize_coordinates(lat, lng)
    if not coordinates:
        return "Coordenadas no válidas"
    cache_key = f"{coordinates[0]},{coordinates[1]}"
    if cache_key in _geocode_cache:
        return _geocode_cache[cache_key]
    try:
        geolocator = Nominatim(user_agent="smart_resto_app/1.0", timeout=5)
        time.sleep(1)
        location = geolocator.reverse(f"{coordinates[0]}, {coordinates[1]}")
        address = location.address if location else "Dirección no encontrada"
        _geocode_cache[cache_key] = address[:500]
        return _geocode_cache[cache_key]
    except Exception:
        logger.exception("Error controlado en geocodificación")
        return "Servicio de geolocalización no disponible"
