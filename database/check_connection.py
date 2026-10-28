"""Diagnóstico de conectividad Supabase/PostgreSQL sin mostrar secretos.

Uso: python -m database.check_connection
"""
from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)

from database.connection import DatabaseConfigurationError, check_connection


def main() -> int:
    try:
        if not check_connection():
            print("Conexión no confirmada: PostgreSQL no devolvió SELECT 1.")
            return 1
    except DatabaseConfigurationError as exc:
        print(f"Configuración incompleta: {exc}")
        return 2
    except Exception as exc:
        # Las excepciones de drivers pueden incluir host/usuario. No imprimimos
        # su texto para evitar filtrar accidentalmente partes de la URI.
        print(f"No se pudo conectar ({type(exc).__name__}). Revisa DATABASE_URL, SSL y acceso de red.")
        return 1

    print("Conexión PostgreSQL confirmada (SELECT 1).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
