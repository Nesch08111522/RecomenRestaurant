"""PostgreSQL document model shared by SmartResto collections."""
from __future__ import annotations

from database.repository import PostgresDocumentRepository


class DataModel:
    """Small model API backed exclusively by Supabase PostgreSQL JSONB."""

    collection: str

    @classmethod
    def _load_data(cls):
        return PostgresDocumentRepository.all(cls.collection)

    @classmethod
    def _save_data(cls, data):
        PostgresDocumentRepository.replace_all(cls.collection, data)

    @classmethod
    def all(cls):
        return cls._load_data()

    @classmethod
    def get_by_id(cls, item_id):
        return PostgresDocumentRepository.get_by_id(cls.collection, item_id)

    @classmethod
    def next_id(cls):
        """Return a usable next ID; inserts normally rely on the DB identity."""
        ids = [int(item.get("id", 0)) for item in cls._load_data()]
        return max(ids + [0]) + 1

    @classmethod
    def create(cls, new_data):
        return PostgresDocumentRepository.create(cls.collection, new_data)

    @classmethod
    def update(cls, item_id, updated_data):
        return PostgresDocumentRepository.update(cls.collection, item_id, updated_data)

    @classmethod
    def delete(cls, item_id):
        return PostgresDocumentRepository.delete(cls.collection, item_id)


