# models/category.py

import re
import unicodedata

from models.base import DataModel


class CategoryModel(DataModel):
    collection = "categories"

    @staticmethod
    def normalize_name(value):
        """Normaliza nombres para comparar categorías."""
        text = unicodedata.normalize("NFKD", str(value or ""))
        text = "".join(char for char in text if not unicodedata.combining(char))
        return " ".join(text.casefold().split())

    @staticmethod
    def generate_slug(value):
        """Genera un slug compatible con URLs."""
        text = CategoryModel.normalize_name(value)
        return re.sub(r"[^a-z0-9]+", "-", text).strip("-")

    @classmethod
    def get_by_id(cls, category_id):
        try:
            category_id = int(category_id)
        except (TypeError, ValueError):
            return None

        return next((cat for cat in cls.all() if cat.get("id") == category_id), None)

    @classmethod
    def get_by_slug(cls, slug):
        return next((cat for cat in cls.all() if cat.get("slug") == slug), None)

    @classmethod
    def get_by_name(cls, name):
        """Busca categorías sin distinguir tildes o mayúsculas."""
        target = cls.normalize_name(name)

        if not target:
            return None

        return next(
            (cat for cat in cls.all() if cls.normalize_name(cat.get("name")) == target),
            None,
        )

    @classmethod
    def get_all_names(cls):
        return {cat["id"]: cat["name"] for cat in cls.all()}

    @classmethod
    def create_dynamic(cls, name):
        """
        Crea una categoría solo si no existe.

        Retorna:
        (categoria, creada)
        """
        name = " ".join(str(name or "").strip().split())

        if not 2 <= len(name) <= 80:
            raise ValueError("El nombre debe tener entre 2 y 80 caracteres.")

        existing = cls.get_by_name(name)

        if existing:
            return existing, False

        slug = cls.generate_slug(name)

        if not slug:
            raise ValueError("El nombre no permite generar un slug válido.")

        existing_slug = cls.get_by_slug(slug)

        if existing_slug:
            return existing_slug, False

        category = cls.create(
            {"name": name, "slug": slug, "icon": "restaurant", "image_url": ""}
        )

        return category, True
