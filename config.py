import os
from pathlib import Path


class Config:
    # --- CONFIGURACIÓN PERSONALIZABLE ---
    CIUDAD = "Trujillo"
    COORDENADAS_CENTRO = (-8.1118, -79.0287)
    RADIO_MAXIMO_KM = 10
    MONEDA = "S/."
    IDIOMA = "es"

    # --- DISTRITOS ---
    DISTRITOS = [
        "Trujillo", "Victor Larco", "La Esperanza", "Huanchaco", "Moche",
        "El Porvenir", "Florencia de Mora"
    ]

    # --- PALETA DE COLORES ---
    PALETA_PRIMARIA = "#FF385C"
    PALETA_SECUNDARIA = "#008489"
    FUENTE_PRINCIPAL = "Inter"
    NOMBRE_APP = "SmartResto"

    # --- FLASK CONFIG ---
    # No se incluye una clave operativa en el código fuente. El arranque debe
    # recibir SECRET_KEY desde el entorno o fallar de forma explícita.
    SECRET_KEY = os.environ.get("SECRET_KEY","5ecc7f3e536e2bad1344fa792a5df89ff1cc4bc959717b59e813f93cf3437a1d")
    DEBUG = os.environ.get("FLASK_DEBUG", "0").lower() in {"1", "true", "yes"}
    TESTING = os.environ.get("FLASK_TESTING", "0").lower() in {"1", "true", "yes"}
    JSON_AS_ASCII = False
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", str(2 * 1024 * 1024)))
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "0").lower() in {"1", "true", "yes"}
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
    PERMANENT_SESSION_LIFETIME = int(os.environ.get("SESSION_LIFETIME_SECONDS", "3600"))
    WTF_CSRF_TIME_LIMIT = int(os.environ.get("WTF_CSRF_TIME_LIMIT", "3600"))

    # PostgreSQL se activa de forma opt-in después de migrar y validar datos.
    DATA_BACKEND = os.environ.get("DATA_BACKEND", "json").lower()
    DATABASE_URL = os.environ.get("DATABASE_URL")

    # --- RUTAS DE DATOS ---
    DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
    RESTAURANTS_FILE = os.path.join(DATA_DIR, "restaurants.json")
    CATEGORIES_FILE = os.path.join(DATA_DIR, "categories.json")
    USERS_FILE = os.path.join(DATA_DIR, "users.json")
    DISHES_FILE = os.path.join(DATA_DIR, "dishes.json")
    FAVORITES_FILE = os.path.join(DATA_DIR, "favorites.json")
    HISTORY_FILE = os.path.join(DATA_DIR, "history.json")
    PROMOTIONS_FILE = os.path.join(DATA_DIR, "promotions.json")
    REVIEWS_FILE = os.path.join(DATA_DIR, "reviews.json")
    NOTIFICATIONS_FILE = os.path.join(DATA_DIR, "notifications.json")
    DAILY_MENU_FILE = os.path.join(DATA_DIR, "daily_menu.json")
    MODERATION_FILE = os.path.join(DATA_DIR, "moderation.json")
    AUDIT_EVENTS_FILE = os.path.join(DATA_DIR, "audit_events.json")

    @classmethod
    def ensure_data_dir(cls):
        """Asegura que el directorio de datos existe."""
        Path(cls.DATA_DIR).mkdir(parents=True, exist_ok=True)

    @classmethod
    def validate(cls):
        """Evita arrancar con una clave de sesión predecible."""
        if not cls.SECRET_KEY:
            raise RuntimeError(
                "SECRET_KEY no está configurada. Defínela como secreto de entorno "
                "antes de iniciar SmartResto."
            )
        if len(cls.SECRET_KEY) < 32:
            raise RuntimeError("SECRET_KEY debe contener al menos 32 caracteres.")
