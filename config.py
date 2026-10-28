import os


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
    SECRET_KEY = os.environ.get("SECRET_KEY")
    DEBUG = os.environ.get("FLASK_DEBUG", "0").lower() in {"1", "true", "yes"}
    TESTING = os.environ.get("FLASK_TESTING", "0").lower() in {"1", "true", "yes"}
    JSON_AS_ASCII = False
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", str(2 * 1024 * 1024)))
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "0").lower() in {"1", "true", "yes"}
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")
    PERMANENT_SESSION_LIFETIME = int(os.environ.get("SESSION_LIFETIME_SECONDS", "3600"))
    WTF_CSRF_TIME_LIMIT = int(os.environ.get("WTF_CSRF_TIME_LIMIT", "3600"))

    # Persistencia exclusiva en Supabase/PostgreSQL; no hay backend de archivos.
    DATA_BACKEND = os.environ.get("DATA_BACKEND", "postgresql").lower()
    DATABASE_URL = os.environ.get("DATABASE_URL")
    DATABASE_SSLMODE = os.environ.get("DATABASE_SSLMODE", "require").lower()

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
        if cls.DATA_BACKEND not in {"postgres", "postgresql"}:
            raise RuntimeError(
                "SmartResto usa exclusivamente Supabase/PostgreSQL. "
                "Configura DATA_BACKEND=postgresql."
            )
        if not cls.DATABASE_URL:
            raise RuntimeError(
                "DATABASE_URL no está configurada. Copia la URI PostgreSQL de "
                "Supabase al entorno del servidor; no la incluyas en el código."
            )
        if not cls.DATABASE_URL.lower().startswith(("postgres://", "postgresql://")):
            raise RuntimeError("DATABASE_URL debe ser una URI postgres:// o postgresql://.")
        if cls.DATABASE_SSLMODE not in {"require", "verify-ca", "verify-full"}:
            raise RuntimeError("DATABASE_SSLMODE debe ser require, verify-ca o verify-full.")
