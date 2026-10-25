#!/usr/bin/env python3
"""One-time, non-destructive import of legacy JSON records to PostgreSQL."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from psycopg.types.json import Jsonb

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env", override=False)

from database.connection import connection  # noqa: E402


COLLECTION_FILES = {
    "audit_events": "audit_events.json",
    "categories": "categories.json",
    "daily_menu": "daily_menu.json",
    "dishes": "dishes.json",
    "favorites": "favorites.json",
    "history": "history.json",
    "moderation": "moderation.json",
    "notifications": "notifications.json",
    "promotions": "promotions.json",
    "reservations": "reservations.json",
    "restaurants": "restaurants.json",
    "reviews": "reviews.json",
    "users": "users.json",
}


def load_records(source_dir: Path) -> dict[str, list[dict[str, Any]]]:
    records = {}
    for collection, filename in COLLECTION_FILES.items():
        path = source_dir / filename
        if not path.exists():
            continue
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
            raise ValueError(f"{filename} debe contener una lista de objetos")
        for row in value:
            if row.get("id") is None:
                raise ValueError(f"{filename} tiene un registro sin id")
            try:
                int(row["id"])
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{filename} tiene un id que no es entero") from exc
        records[collection] = value
    return records


def import_records(records: dict[str, list[dict[str, Any]]]) -> tuple[int, int]:
    imported = skipped = 0
    with connection() as conn, conn.cursor() as cur:
        for collection, rows in records.items():
            for source in rows:
                item = dict(source)
                raw_id = item.pop("id", None)
                if raw_id is None:
                    raise ValueError(f"Un registro de {collection} no tiene id; asígnalo antes de importar")
                item_id = int(raw_id)
                cur.execute(
                    """INSERT INTO public.app_records (collection, id, payload)
                       VALUES (%s, %s, %s)
                       ON CONFLICT (collection, id) DO NOTHING
                       RETURNING id""",
                    (collection, item_id, Jsonb(item)),
                )
                inserted = cur.fetchone()
                if not inserted:
                    skipped += 1
                    continue

                item["id"] = item_id
                cur.execute(
                    """UPDATE public.app_records SET payload = %s
                       WHERE collection = %s AND id = %s""",
                    (Jsonb(item), collection, item_id),
                )
                imported += 1

        # Explicit legacy IDs do not advance an identity sequence themselves.
        cur.execute(
            """SELECT setval(
                   pg_get_serial_sequence('public.app_records', 'id'),
                   COALESCE(MAX(id), 1),
                   COUNT(*) > 0
               ) FROM public.app_records"""
        )
        conn.commit()
    return imported, skipped


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, default=ROOT / "data")
    parser.add_argument("--dry-run", action="store_true", help="count source records without connecting")
    args = parser.parse_args()

    try:
        records = load_records(args.source_dir)
        total = sum(len(rows) for rows in records.values())
        if args.dry_run:
            print(f"Registros listos para importar: {total} en {len(records)} colecciones.")
            return 0
        imported, skipped = import_records(records)
    except Exception as exc:
        print(f"No se pudo importar ({type(exc).__name__}). Revisa la configuración y los archivos fuente.")
        return 1

    print(f"Importados: {imported}; ya existentes y preservados: {skipped}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
