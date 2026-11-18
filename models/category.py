"""Categorías de SmartResto respaldadas por PostgreSQL JSONB."""

import re
import unicodedata

from models.base import DataModel


def _key(value):
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = "".join(c for c in value if not unicodedata.combining(c))
    return " ".join(value.casefold().split())


class CategoryModel(DataModel):
    collection = "categories"

    @classmethod
    def get_by_id(cls, category_id):
        try:
            return super().get_by_id(int(category_id))
        except (ValueError, TypeError):
            return None

    @classmethod
    def get_by_slug(cls, slug):
        return next((c for c in cls.all() if c.get("slug") == slug), None)

    @classmethod
    def get_all_names(cls):
        return {cat["id"]: cat["name"] for cat in cls.all()}

    @classmethod
    def get_by_name(cls, name):
        target = _key(name)

        if not target:
            return None

        return next((c for c in cls.all() if _key(c.get("name")) == target), None)

    @classmethod
    def create_dynamic(cls, name):
        """
        Crea una categoría dinámica.

        Si ya existe, devuelve la existente.

        Retorna:
            (categoria, creada)
        """

        clean = " ".join(str(name or "").split())

        if not 2 <= len(clean) <= 80:
            raise ValueError("El nombre debe tener entre 2 y 80 caracteres.")

        # Comprobar si existe
        existing = cls.get_by_name(clean)

        if existing:
            return existing, False

        # Generar slug
        slug = re.sub(r"[^a-z0-9]+", "-", _key(clean)).strip("-")

        if not slug:
            raise ValueError("El nombre de categoría no es válido.")

        # Evitar duplicados por slug
        existing_slug = cls.get_by_slug(slug)

        if existing_slug:
            return existing_slug, False

        # Crear categoría
        payload = {"name": clean, "slug": slug, "icon": "restaurant", "image_url": ""}

        created = cls.create(payload)

        # Recuperar categoría guardada
        saved = cls.get_by_name(clean)

        if saved:
            return saved, True

        if isinstance(created, dict) and created.get("id") is not None:
            return created, True

        raise RuntimeError(
            "La categoría se insertó, " "pero no se pudo recuperar su ID."
        )
