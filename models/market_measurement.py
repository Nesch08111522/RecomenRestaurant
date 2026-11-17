"""Anonymous, deduplicated events for a rendered offer. Tokens contain no buyer data."""
from flask import current_app
from itsdangerous import BadSignature, URLSafeTimedSerializer

from database.repository import PostgresDocumentRepository as Repo, document_transaction
from logic.market import now
from models.market import records


def signer(purpose="recommendation"):
    return URLSafeTimedSerializer(current_app.secret_key, salt="market-" + purpose)


def observe(token, stage, expected=None):
    if not token or stage not in {"viewed", "clicked", "ordered"}:
        return False
    try:
        page, offer = signer().loads(token, max_age=86400)
    except (BadSignature, ValueError, TypeError):
        return False
    if expected is not None and offer != expected:
        return False
    visit = f"{page}-{offer}"
    with document_transaction() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (visit,))
        existing = records("market_views", visit=visit)
        changes = {"viewed": True, stage: True}
        if stage == "ordered":
            changes["clicked"] = True
        if existing:
            if not existing[0].get(stage):
                Repo.update("market_views", existing[0]["id"], changes)
        else:
            Repo.create("market_views", {"visit": visit, "offer": offer, "day": now().date().isoformat(), **changes})
    return True

