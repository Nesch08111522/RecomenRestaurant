"""Contrato público de la arquitectura central de SmartResto."""
from __future__ import annotations

from copy import deepcopy


_MANIFEST = {
    "product": "SmartResto",
    "version": "advanced-ecosystem",
    "architecture": {
        "backend": "Flask REST API",
        "database": "PostgreSQL / Supabase",
        "background_jobs": "Native discovery worker; scheduler activation required",
        "ai_gateway": "OpenRouter (provider-agnostic)",
        "experience": "Responsive web with light/dark themes",
    },
    "modules": {
        "marketplace": {"label": "Descubrimiento y recomendación", "audiences": ["guest", "diner"]},
        "businesses": {"label": "Negocios y sucursales", "audiences": ["business_owner", "admin"]},
        "catalog": {"label": "Carta, platos y contenido", "audiences": ["diner", "business_owner", "admin"]},
        "operations": {"label": "Pedidos, reservas y cocina", "audiences": ["business_owner", "admin"]},
        "smart_flow": {"label": "Aforo, mesas y lista de espera", "audiences": ["diner", "business_owner", "admin"]},
        "rewards": {"label": "Visitas, puntos y fidelización", "audiences": ["diner", "business_owner"]},
        "home_kitchen": {"label": "Despensa y recetas en casa", "audiences": ["diner"]},
        "ai_copilot": {"label": "Copilot por rol", "audiences": ["diner", "business_owner", "admin"]},
        "business_intelligence": {"label": "Inteligencia empresarial", "audiences": ["business_owner", "admin"]},
        "trust_center": {"label": "Seguridad y confianza", "audiences": ["admin"]},
        "immersive_menu": {"label": "Menú 3D y experiencias inmersivas", "audiences": ["diner", "business_owner"]},
        "communications": {"label": "Notificaciones y mensajería", "audiences": ["diner", "business_owner", "admin"]},
    },
    "roles": {
        "guest": {"scope": "public"},
        "user": {"scope": "user", "alias_of": "diner"},
        "diner": {"scope": "user"},
        "business_owner": {"scope": "business"},
        "business_admin": {"scope": "business"},
        "manager": {"scope": "business"},
        "cashier": {"scope": "business"},
        "waiter": {"scope": "business"},
        "kitchen": {"scope": "business"},
        "admin": {"scope": "platform"},
    },
    "security": {
        "session_authentication": True,
        "csrf_protection": True,
        "audit_events": True,
        "tenant_isolation": True,
        "consent_separation": ["cookies", "notifications", "location", "marketing"],
        "server_side_validation_for_sensitive_actions": True,
    },
}


def platform_manifest() -> dict:
    """Return a defensive copy so callers cannot mutate the shared contract."""
    return deepcopy(_MANIFEST)
