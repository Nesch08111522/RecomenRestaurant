import hashlib
from pathlib import Path

from database.repository import PostgresRepository
from migrations.migrate_json import load_dataset, manifest, validate


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def test_real_json_dataset_is_migration_ready():
    datasets = load_dataset(DATA)
    report = validate(datasets)
    assert report["valid"] is True
    assert report["errors"] == []
    assert len(datasets["users"]) == 3
    assert len(datasets["restaurants"]) == 24
    assert len(datasets["dishes"]) == 84


def test_manifest_is_deterministic_and_source_files_are_not_modified():
    before = hashlib.sha256((DATA / "restaurants.json").read_bytes()).hexdigest()
    datasets = load_dataset(DATA)
    first = manifest(DATA, datasets)
    second = manifest(DATA, datasets)
    after = hashlib.sha256((DATA / "restaurants.json").read_bytes()).hexdigest()
    assert first == second
    assert before == after
    assert first["files"]["restaurants.json"]["sha256"] == before


def test_repository_rejects_unknown_columns_before_database_access():
    class RestaurantRepository(PostgresRepository):
        table = "restaurants"
        columns = frozenset({"name", "description"})

    assert RestaurantRepository._validate_mapping({"name": "Demo"}) == {"name": "Demo"}
    try:
        RestaurantRepository._validate_mapping({"name": "Demo", "approval_status": "SUSPENDED"})
    except ValueError as error:
        assert "approval_status" in str(error)
    else:
        raise AssertionError("La allowlist debía rechazar approval_status")


def test_legacy_approval_statuses_are_supported():
    datasets = load_dataset(DATA)
    statuses = {str(row.get("status", "pending")).lower() for row in datasets["moderation"]}
    assert statuses <= {"pending", "approved", "rejected", "suspended"}
