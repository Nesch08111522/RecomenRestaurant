"""Persistencia JSON compatible durante la migración incremental a PostgreSQL."""
from __future__ import annotations

import json
import os
import tempfile
from contextlib import contextmanager

from config import Config

try:
    import fcntl
except ImportError:  # pragma: no cover - compatibilidad Windows
    fcntl = None


class JSONModel:
    """Repositorio JSON con lectura tolerante y escrituras atómicas."""

    file_path = None

    @classmethod
    def _load_data(cls):
        if not cls.file_path or not os.path.exists(cls.file_path):
            return []
        try:
            with open(cls.file_path, "r", encoding="utf-8") as file:
                value = json.load(file)
                return value if isinstance(value, list) else []
        except (json.JSONDecodeError, OSError):
            return []

    @classmethod
    @contextmanager
    def _write_lock(cls):
        """Bloquea escritores del mismo archivo dentro del proceso/host."""
        if not cls.file_path:
            raise ValueError("El modelo no tiene file_path configurado")
        lock_path = f"{cls.file_path}.lock"
        os.makedirs(os.path.dirname(lock_path), exist_ok=True)
        with open(lock_path, "a+", encoding="utf-8") as lock_file:
            if fcntl is not None:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                if fcntl is not None:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    @classmethod
    def _atomic_write(cls, data):
        directory = os.path.dirname(cls.file_path) or "."
        os.makedirs(directory, exist_ok=True)
        fd, temporary_path = tempfile.mkstemp(prefix=".json-", dir=directory, text=True)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as file:
                json.dump(data, file, indent=4, ensure_ascii=False)
                file.flush()
                os.fsync(file.fileno())
            os.replace(temporary_path, cls.file_path)
        finally:
            if os.path.exists(temporary_path):
                os.unlink(temporary_path)

    @classmethod
    def _save_data(cls, data):
        with cls._write_lock():
            cls._atomic_write(data)

    @classmethod
    def all(cls):
        return cls._load_data()

    @classmethod
    def get_by_id(cls, item_id):
        data = cls._load_data()
        return next((item for item in data if item.get("id") == item_id), None)

    @classmethod
    def next_id(cls):
        """Obtener el siguiente ID bajo el mismo lock de escritura."""
        with cls._write_lock():
            data = cls._load_data()
            return max([entry.get("id", 0) for entry in data] + [0]) + 1

    @classmethod
    def create(cls, new_data):
        if not isinstance(new_data, dict):
            raise TypeError("new_data debe ser un objeto")
        with cls._write_lock():
            data = cls._load_data()
            item = dict(new_data)
            if not item.get("id"):
                item["id"] = max([entry.get("id", 0) for entry in data] + [0]) + 1
            data.append(item)
            cls._atomic_write(data)
            return item

    @classmethod
    def update(cls, item_id, updated_data):
        if not isinstance(updated_data, dict):
            raise TypeError("updated_data debe ser un objeto")
        with cls._write_lock():
            data = cls._load_data()
            for index, item in enumerate(data):
                if item.get("id") == item_id:
                    # Las rutas deben aplicar allowlists; el repositorio no
                    # reemplaza la autorización de dominio.
                    merged = dict(item)
                    merged.update(updated_data)
                    data[index] = merged
                    cls._atomic_write(data)
                    return merged
        return None

    @classmethod
    def delete(cls, item_id):
        with cls._write_lock():
            data = cls._load_data()
            new_data = [item for item in data if item.get("id") != item_id]
            if len(new_data) < len(data):
                cls._atomic_write(new_data)
                return True
        return False
