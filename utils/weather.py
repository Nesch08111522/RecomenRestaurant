"""Opt-in Open-Meteo forecasts with short caching and bounded requests."""
from datetime import datetime, timezone
import json
import math
import os
import threading
import time
from urllib.parse import urlencode
from urllib.request import urlopen
from utils.geo import normalize_coordinates

_cache = {}
_lock = threading.Lock()


def conditions(lat, lng):
    point = normalize_coordinates(lat, lng)
    if point is None:
        return None
    point = tuple(round(v, 2) for v in point)
    with _lock:
        saved = _cache.get(point)
        if saved and saved[0] > time.monotonic():
            return saved[1]
    key = os.getenv("WEATHER_API_KEY", "").strip()
    base = "https://customer-api.open-meteo.com/v1/forecast" if key else "https://api.open-meteo.com/v1/forecast"
    query = {"latitude":point[0], "longitude":point[1], "timezone":"America/Lima", "forecast_days":1,
             "current":"temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,wind_speed_10m",
             "hourly":"precipitation_probability"}
    if key:
        query["apikey"] = key
    result = None
    try:
        with urlopen(base + "?" + urlencode(query), timeout=5) as response:
            data = json.loads(response.read(100000))
        current = data["current"]
        fields = ("temperature_2m","apparent_temperature","relative_humidity_2m","precipitation","wind_speed_10m")
        if any(type(current.get(k)) not in (float,int) or not math.isfinite(current[k]) for k in fields):
            raise ValueError("invalid forecast")
        hourly = data.get("hourly") or {}
        hour = current["time"][:13] + ":00"
        index = hourly.get("time", []).index(hour)
        result = {**{k:current[k] for k in fields}, "rain_probability":hourly["precipitation_probability"][index],
                  "observed":current["time"], "fetched":datetime.now(timezone.utc).isoformat(), "source":"Open-Meteo"}
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        pass
    with _lock:
        if len(_cache) >= 256:
            _cache.clear()
        _cache[point] = (time.monotonic() + (600 if result else 30), result)
    return result
