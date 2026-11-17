"""Server-managed business rules shared by the storefront and its dashboards."""
from database.repository import PostgresDocumentRepository as Repo, document_transaction
from logic.market import DIETS


def commerce_settings():
    return {"threshold": 3, "diets": list(DIETS), **(Repo.get_by_id("commerce_settings", 1) or {})}


def save_settings(threshold, diets):
    with document_transaction() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(hashtextextended('smartresto-commerce-settings',0))")
        fields = {"threshold": threshold, "diets": diets}
        if not Repo.update("commerce_settings", 1, fields):
            Repo.create("commerce_settings", {"id": 1, **fields})
