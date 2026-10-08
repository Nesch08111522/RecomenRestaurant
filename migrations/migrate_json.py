#!/usr/bin/env python3
"""Migración conservadora de los JSON de SmartResto a PostgreSQL.

Características:
- Nunca modifica ni elimina los JSON de origen.
- ``--dry-run`` valida estructura y referencias sin conectarse a PostgreSQL.
- La migración real se ejecuta en una transacción y registra ``migration_runs``.
- Conserva IDs legacy y snapshots donde la normalización no puede inferirse sin
  inventar información.
- Es idempotente sobre las claves legacy/IDs existentes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import uuid
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from typing import Any

try:
    import psycopg
except ImportError:  # pragma: no cover - dry-run no requiere dependencia
    psycopg = None

VALID_APPROVALS = {
    "APROBADO_AUTOMATICAMENTE",
    "PENDIENTE_REVISION",
    "RECHAZADO",
    "SUSPENDIDO",
}
LEGACY_APPROVALS = {
    "pending": "PENDIENTE_REVISION",
    "approved": "APROBADO_AUTOMATICAMENTE",
    "rejected": "RECHAZADO",
    "suspended": "SUSPENDIDO",
}


def read_json(data_dir: Path, filename: str) -> list[dict[str, Any]]:
    path = data_dir / filename
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as source:
        value = json.load(source)
    if not isinstance(value, list):
        raise ValueError(f"{filename} debe contener una lista JSON")
    if any(not isinstance(row, dict) for row in value):
        raise ValueError(f"{filename} contiene registros que no son objetos")
    return value


def json_value(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False)


def json_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def clean_text(value: Any, max_length: int | None = None) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).strip().split())
    return text[:max_length] if max_length else text


def safe_int(value: Any, default: int | None = None) -> int | None:
    try:
        if value is None or value == "":
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_float(value: Any, default: float | None = None) -> float | None:
    try:
        if value is None or value == "":
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_date(value: Any) -> str | None:
    if not value:
        return None
    text = str(value).strip()
    try:
        return date.fromisoformat(text[:10]).isoformat()
    except ValueError:
        return None


def safe_timestamp(value: Any) -> str | None:
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(text).isoformat()
    except ValueError:
        return None


def slug(value: Any) -> str | None:
    text = clean_text(value, 220)
    if not text:
        return None
    value = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return value or None


def approval_status(restaurant: dict[str, Any]) -> tuple[str, str]:
    raw = str(restaurant.get("approval_status", "")).upper()
    if raw in VALID_APPROVALS:
        return raw, "LEGACY_IMPORT"
    # ``verified`` expresa publicación histórica, no evidencia de una decisión
    # de IA. Se conserva además en legacy_verified y en el snapshot.
    if restaurant.get("verified") is True:
        return "APROBADO_AUTOMATICAMENTE", "LEGACY_IMPORT"
    return "PENDIENTE_REVISION", "LEGACY_IMPORT"


def load_dataset(data_dir: Path) -> dict[str, list[dict[str, Any]]]:
    files = {
        "categories": "categories.json",
        "users": "users.json",
        "restaurants": "restaurants.json",
        "dishes": "dishes.json",
        "daily_menu": "daily_menu.json",
        "favorites": "favorites.json",
        "history": "history.json",
        "moderation": "moderation.json",
        "notifications": "notifications.json",
        "promotions": "promotions.json",
        "reviews": "reviews.json",
    }
    return {key: read_json(data_dir, filename) for key, filename in files.items()}


def manifest(data_dir: Path, datasets: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    files = {}
    for name in datasets:
        path = data_dir / {
            "daily_menu": "daily_menu.json",
        }.get(name, f"{name}.json")
        if path.exists():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            files[path.name] = {"sha256": digest, "bytes": path.stat().st_size}
    return {"data_dir": str(data_dir), "files": files, "counts": {k: len(v) for k, v in datasets.items()}}


def validate(datasets: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    ids = {name: {row.get("id") for row in rows if row.get("id") is not None} for name, rows in datasets.items()}
    errors: list[str] = []
    warnings: list[str] = []
    checks = [
        ("restaurants", "owner_id", "users"),
        ("restaurants", "category_id", "categories"),
        ("dishes", "restaurant_id", "restaurants"),
        ("daily_menu", "restaurant_id", "restaurants"),
        ("favorites", "user_id", "users"),
        ("favorites", "restaurant_id", "restaurants"),
        ("reviews", "user_id", "users"),
        ("reviews", "restaurant_id", "restaurants"),
        ("promotions", "restaurant_id", "restaurants"),
        ("moderation", "user_id", "users"),
    ]
    for collection, field, target in checks:
        for row in datasets[collection]:
            value = row.get(field)
            if value is not None and value not in ids[target]:
                errors.append(f"{collection}.{field}={value} no referencia {target}")

    for name, rows in datasets.items():
        row_ids = [row.get("id") for row in rows if row.get("id") is not None]
        duplicates = [key for key, count in Counter(row_ids).items() if count > 1]
        if duplicates:
            errors.append(f"{name} tiene IDs duplicados: {duplicates}")

    for row in datasets["restaurants"]:
        lat = safe_float(row.get("lat"))
        lng = safe_float(row.get("lng"))
        if lat is None or lng is None:
            warnings.append(f"restaurant {row.get('id')} sin coordenadas completas")
        elif not (-90 <= lat <= 90 and -180 <= lng <= 180):
            errors.append(f"restaurant {row.get('id')} tiene coordenadas fuera de rango")

    return {"errors": errors, "warnings": warnings, "valid": not errors}


def execute_migration(dsn: str, schema_path: Path, data_dir: Path, datasets: dict[str, list[dict[str, Any]]], source_manifest: dict[str, Any]) -> dict[str, int]:
    if psycopg is None:
        raise RuntimeError("Instala psycopg[binary] para ejecutar una migración real")

    counts = Counter()
    run_id = uuid.uuid4()
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(schema_path.read_text(encoding="utf-8"))
            cur.execute(
                "INSERT INTO migration_runs (run_id, source_manifest, status) VALUES (%s, %s::jsonb, 'STARTED')",
                (str(run_id), json_value(source_manifest)),
            )

            for row in datasets["users"]:
                profile = row.get("profile") or {}
                cur.execute(
                    """INSERT INTO users (id, username, password_hash, role_code, email, display_name, preferences, legacy_source_file, legacy_source_id)
                    VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s)
                    ON CONFLICT (id) DO UPDATE SET username=EXCLUDED.username, role_code=EXCLUDED.role_code,
                      email=EXCLUDED.email, display_name=EXCLUDED.display_name, preferences=EXCLUDED.preferences,
                      updated_at=CURRENT_TIMESTAMP""",
                    (safe_int(row.get("id")), clean_text(row.get("username"), 80), row.get("password", ""),
                     row.get("role", "user"), clean_text(profile.get("email"), 255), clean_text(profile.get("name"), 160),
                     json_value({"preferences": json_list(profile.get("preferences")), "restrictions": json_list(profile.get("restrictions"))}),
                     "users.json", safe_int(row.get("id"))),
                )
                counts["users"] += 1
                for value in json_list(profile.get("preferences")):
                    cur.execute("INSERT INTO user_preferences (user_id, preference_type, value) VALUES (%s,'preference',%s) ON CONFLICT DO NOTHING", (safe_int(row.get("id")), clean_text(value, 160) or ""))
                for value in json_list(profile.get("restrictions")):
                    cur.execute("INSERT INTO user_preferences (user_id, preference_type, value) VALUES (%s,'restriction',%s) ON CONFLICT DO NOTHING", (safe_int(row.get("id")), clean_text(value, 160) or ""))

            owners = {safe_int(r.get("owner_id")) for r in datasets["restaurants"] if safe_int(r.get("owner_id"))}
            for user_id in owners:
                cur.execute("INSERT INTO businesses (user_id) VALUES (%s) ON CONFLICT (user_id) DO NOTHING", (user_id,))
                counts["businesses"] += 1

            for row in datasets["categories"]:
                cur.execute(
                    """INSERT INTO categories (id,name,slug,icon,image_url,legacy_source_file,legacy_source_id)
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (id) DO UPDATE SET name=EXCLUDED.name, slug=EXCLUDED.slug, icon=EXCLUDED.icon, image_url=EXCLUDED.image_url""",
                    (safe_int(row.get("id")), clean_text(row.get("name"), 120) or f"Categoría {row.get('id')}", slug(row.get("slug") or row.get("name")), row.get("icon"), row.get("image_url"), "categories.json", safe_int(row.get("id"))),
                )
                counts["categories"] += 1

            for row in datasets["restaurants"]:
                status, source = approval_status(row)
                verified = row.get("verified") if isinstance(row.get("verified"), bool) else None
                publication = "PUBLISHED" if verified is True else "DRAFT"
                cur.execute(
                    """INSERT INTO restaurants (id,business_id,category_id,name,slug,description,address,district,phone,image,tags,features,dietary_restrictions,avg_price,rating,review_count,open_time,close_time,promo,approval_status,publication_status,approval_source,moderation_notes,legacy_verified,legacy_source_file,legacy_source_id,source_snapshot,moderated_at)
                    VALUES (%s,(SELECT id FROM businesses WHERE user_id=%s),%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s)
                    ON CONFLICT (id) DO UPDATE SET business_id=EXCLUDED.business_id, category_id=EXCLUDED.category_id, name=EXCLUDED.name, description=EXCLUDED.description, address=EXCLUDED.address, district=EXCLUDED.district, phone=EXCLUDED.phone, image=EXCLUDED.image, tags=EXCLUDED.tags, features=EXCLUDED.features, dietary_restrictions=EXCLUDED.dietary_restrictions, avg_price=EXCLUDED.avg_price, rating=EXCLUDED.rating, review_count=EXCLUDED.review_count, open_time=EXCLUDED.open_time, close_time=EXCLUDED.close_time, promo=EXCLUDED.promo, approval_status=EXCLUDED.approval_status, publication_status=EXCLUDED.publication_status, approval_source=EXCLUDED.approval_source, moderation_notes=EXCLUDED.moderation_notes, legacy_verified=EXCLUDED.legacy_verified, source_snapshot=EXCLUDED.source_snapshot, moderated_at=EXCLUDED.moderated_at, updated_at=CURRENT_TIMESTAMP""",
                    (safe_int(row.get("id")), safe_int(row.get("owner_id")), safe_int(row.get("category_id")), clean_text(row.get("name"), 180) or f"Restaurante {row.get('id')}", slug(row.get("name")), clean_text(row.get("description")) or "", clean_text(row.get("address")) or "", clean_text(row.get("district"), 120) or "", clean_text(row.get("phone"), 60), clean_text(row.get("image")), json_value(json_list(row.get("tags"))), json_value(json_list(row.get("features"))), json_value(json_list(row.get("dietary_restrictions"))), safe_float(row.get("avg_price")), min(max(safe_float(row.get("rating"), 0) or 0, 0), 5), max(safe_int(row.get("reviews"), 0) or 0, 0), row.get("open_time"), row.get("close_time"), clean_text(row.get("promo")), status, publication, source, clean_text(row.get("moderation_notes")), verified, "restaurants.json", safe_int(row.get("id")), json_value(row), safe_timestamp(row.get("moderated_at"))),
                )
                cur.execute("INSERT INTO restaurant_locations (restaurant_id,latitude,longitude,address,district,source,geocode_status) VALUES (%s,%s,%s,%s,%s,'LEGACY_IMPORT','UNVERIFIED') ON CONFLICT (restaurant_id) DO UPDATE SET latitude=EXCLUDED.latitude, longitude=EXCLUDED.longitude, address=EXCLUDED.address, district=EXCLUDED.district", (safe_int(row.get("id")), safe_float(row.get("lat")), safe_float(row.get("lng")), clean_text(row.get("address")), clean_text(row.get("district"), 120)))
                counts["restaurants"] += 1

            dish_ids = set()
            for row in datasets["dishes"]:
                dish_id = safe_int(row.get("id"))
                dish_ids.add(dish_id)
                cur.execute(
                    """INSERT INTO dishes (id,restaurant_id,name,description,category,price,is_available,is_recommended,seasonal,preparation_time_minutes,spiciness,dietary_info,tags,nutritional_info,source_snapshot,created_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s::jsonb,%s::jsonb,%s::jsonb,COALESCE(%s,CURRENT_TIMESTAMP))
                    ON CONFLICT (id) DO UPDATE SET restaurant_id=EXCLUDED.restaurant_id,name=EXCLUDED.name,description=EXCLUDED.description,category=EXCLUDED.category,price=EXCLUDED.price,is_available=EXCLUDED.is_available,is_recommended=EXCLUDED.is_recommended,seasonal=EXCLUDED.seasonal,preparation_time_minutes=EXCLUDED.preparation_time_minutes,spiciness=EXCLUDED.spiciness,dietary_info=EXCLUDED.dietary_info,tags=EXCLUDED.tags,nutritional_info=EXCLUDED.nutritional_info,source_snapshot=EXCLUDED.source_snapshot,updated_at=CURRENT_TIMESTAMP""",
                    (dish_id, safe_int(row.get("restaurant_id")), clean_text(row.get("name"), 180) or f"Plato {dish_id}", clean_text(row.get("description")) or "", clean_text(row.get("category"), 100), max(safe_float(row.get("price"), 0) or 0, 0), bool(row.get("is_available", True)), bool(row.get("is_recommended", False)), bool(row.get("seasonal", False)), max(safe_int(row.get("preparation_time")), 0) if safe_int(row.get("preparation_time")) is not None else None, min(max(safe_int(row.get("spiciness"), 0) or 0, 0), 5), json_value(json_list(row.get("dietary_info"))), json_value(json_list(row.get("tags"))), json_value(row.get("nutritional_info") or {}), json_value(row), safe_timestamp(row.get("created_at"))),
                )
                for ingredient in json_list(row.get("ingredients")):
                    ingredient_name = clean_text(ingredient, 160)
                    if not ingredient_name:
                        continue
                    cur.execute("INSERT INTO ingredients (name) VALUES (%s) ON CONFLICT (name) DO UPDATE SET name=EXCLUDED.name RETURNING id", (ingredient_name,))
                    ingredient_id = cur.fetchone()["id"]
                    cur.execute("INSERT INTO dish_ingredients (dish_id,ingredient_id,source) VALUES (%s,%s,'LEGACY_IMPORT') ON CONFLICT DO NOTHING", (dish_id, ingredient_id))
                counts["dishes"] += 1

            for row in datasets["daily_menu"]:
                menu_id = safe_int(row.get("id"))
                cur.execute("""INSERT INTO menus (id,restaurant_id,menu_date,day_of_week,menu_type,price,specials,is_active,source_snapshot,created_at,updated_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s::jsonb,COALESCE(%s,CURRENT_TIMESTAMP),COALESCE(%s,CURRENT_TIMESTAMP))
                    ON CONFLICT (id) DO UPDATE SET restaurant_id=EXCLUDED.restaurant_id,menu_date=EXCLUDED.menu_date,day_of_week=EXCLUDED.day_of_week,menu_type=EXCLUDED.menu_type,price=EXCLUDED.price,specials=EXCLUDED.specials,is_active=EXCLUDED.is_active,source_snapshot=EXCLUDED.source_snapshot,updated_at=CURRENT_TIMESTAMP""", (menu_id, safe_int(row.get("restaurant_id")), safe_date(row.get("date")), clean_text(row.get("day_of_week"), 20), clean_text(row.get("type"), 80), safe_float(row.get("price")), json_value(json_list(row.get("specials"))), bool(row.get("is_active", True)), json_value(row), safe_timestamp(row.get("created_at")), safe_timestamp(row.get("updated_at"))))
                for order, reference in enumerate(json_list(row.get("dishes"))):
                    dish_id = safe_int(reference.get("id") if isinstance(reference, dict) else reference)
                    if dish_id in dish_ids:
                        cur.execute("INSERT INTO menu_dishes (menu_id,dish_id,display_order) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING", (menu_id, dish_id, order))
                counts["menus"] += 1

            for row in datasets["favorites"]:
                cur.execute("INSERT INTO favorites (user_id,restaurant_id,created_at) VALUES (%s,%s,COALESCE(%s,CURRENT_TIMESTAMP)) ON CONFLICT DO NOTHING", (safe_int(row.get("user_id")), safe_int(row.get("restaurant_id")), safe_timestamp(row.get("timestamp"))))
                counts["favorites"] += 1

            for row in datasets["reviews"]:
                cur.execute("""INSERT INTO ratings (id,user_id,restaurant_id,rating,comment,created_at,updated_at) VALUES (%s,%s,%s,%s,%s,COALESCE(%s,CURRENT_TIMESTAMP),COALESCE(%s,CURRENT_TIMESTAMP)) ON CONFLICT (id) DO UPDATE SET rating=EXCLUDED.rating,comment=EXCLUDED.comment,updated_at=EXCLUDED.updated_at""", (safe_int(row.get("id")), safe_int(row.get("user_id")), safe_int(row.get("restaurant_id")), min(max(safe_int(row.get("rating"), 1) or 1, 1), 5), clean_text(row.get("comment")), safe_timestamp(row.get("created_at")), safe_timestamp(row.get("updated_at"))))
                counts["ratings"] += 1

            for row in datasets["promotions"]:
                cur.execute("INSERT INTO promotions (id,restaurant_id,description,discount_percent,valid_until,source_snapshot) VALUES (%s,%s,%s,%s,%s,%s::jsonb) ON CONFLICT (id) DO UPDATE SET restaurant_id=EXCLUDED.restaurant_id,description=EXCLUDED.description,discount_percent=EXCLUDED.discount_percent,valid_until=EXCLUDED.valid_until,source_snapshot=EXCLUDED.source_snapshot", (safe_int(row.get("id")), safe_int(row.get("restaurant_id")), clean_text(row.get("description"), 1000) or "", min(max(safe_float(row.get("discount_percent"), 0) or 0, 0), 100), safe_date(row.get("valid_until")), json_value(row)))
                counts["promotions"] += 1

            for row in datasets["moderation"]:
                status = LEGACY_APPROVALS.get(str(row.get("status", "pending")).lower(), "PENDIENTE_REVISION")
                cur.execute("""INSERT INTO approvals (id,subject_type,subject_id,requested_by,final_status,reason,source_snapshot,created_at,updated_at)
                    VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb,COALESCE(%s,CURRENT_TIMESTAMP),COALESCE(%s,CURRENT_TIMESTAMP))
                    ON CONFLICT (id) DO UPDATE SET subject_type=EXCLUDED.subject_type,subject_id=EXCLUDED.subject_id,requested_by=EXCLUDED.requested_by,final_status=EXCLUDED.final_status,reason=EXCLUDED.reason,source_snapshot=EXCLUDED.source_snapshot,updated_at=CURRENT_TIMESTAMP""", (safe_int(row.get("id")), clean_text(row.get("content_type"), 40) or "unknown", safe_int(row.get("content_id")), safe_int(row.get("user_id")), status, clean_text(row.get("reason")), json_value(row.get("content_data") or {}), safe_timestamp(row.get("created_at")), safe_timestamp(row.get("updated_at"))))
                cur.execute("INSERT INTO approval_events (approval_id,actor_user_id,new_status,event_type,explanation,metadata) VALUES (%s,%s,%s,'LEGACY_IMPORT','Estado importado; no se atribuye a una decisión de IA.',%s::jsonb) ON CONFLICT DO NOTHING", (safe_int(row.get("id")), safe_int(row.get("user_id")), status, json_value({"legacy_status": row.get("status"), "flagged": row.get("flagged"), "flags": row.get("flags", [])})))
                counts["approvals"] += 1

            for row in datasets["notifications"]:
                cur.execute("INSERT INTO notifications (id,user_id,title,message,notification_type,link,is_read,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,COALESCE(%s,CURRENT_TIMESTAMP)) ON CONFLICT (id) DO UPDATE SET title=EXCLUDED.title,message=EXCLUDED.message,is_read=EXCLUDED.is_read", (safe_int(row.get("id")), safe_int(row.get("user_id")), clean_text(row.get("title"), 180) or "Notificación", clean_text(row.get("message")) or "", clean_text(row.get("type"), 40) or "GENERAL", clean_text(row.get("link")), bool(row.get("read", False)), safe_timestamp(row.get("timestamp"))))
                counts["notifications"] += 1

            for table in ("users", "categories", "restaurants", "dishes", "menus", "ratings", "promotions", "approvals", "notifications"):
                cur.execute("SELECT setval(pg_get_serial_sequence(%s, 'id'), COALESCE((SELECT MAX(id) FROM " + table + "), 1), true)", (table,))

            cur.execute("UPDATE migration_runs SET status='COMPLETED', row_counts=%s::jsonb, completed_at=CURRENT_TIMESTAMP WHERE run_id=%s", (json_value(dict(counts)), str(run_id)))
        conn.commit()
    return dict(counts)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=Path(__file__).resolve().parents[1] / "data")
    parser.add_argument("--schema", type=Path, default=Path(__file__).resolve().parents[1] / "database" / "schema.sql")
    parser.add_argument("--dsn", default=None, help="DSN PostgreSQL; requerido salvo en --dry-run")
    parser.add_argument("--dry-run", action="store_true", help="Validar datos y referencias sin escribir ni conectarse")
    args = parser.parse_args()

    datasets = load_dataset(args.data_dir)
    report = validate(datasets)
    source_manifest = manifest(args.data_dir, datasets)
    print(json.dumps({"manifest": source_manifest, "validation": report}, ensure_ascii=False, indent=2))
    if not report["valid"]:
        return 2
    if args.dry_run:
        print("dry_run=ok; no se modificaron archivos fuente ni se abrió conexión PostgreSQL")
        return 0
    if not args.dsn:
        print("ERROR: --dsn es obligatorio fuera de --dry-run", file=sys.stderr)
        return 2
    counts = execute_migration(args.dsn, args.schema, args.data_dir, datasets, source_manifest)
    print(json.dumps({"migration": "completed", "counts": counts}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
