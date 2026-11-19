"""Store the searches that a SmartResto account submits."""

import re
import unicodedata
from uuid import UUID

from database.repository import PostgresDocumentRepository as Repo, document_transaction
from logic.market import key, now
from utils.security import normalize_text


COLLECTION = "recommendation_search_history"
MAX_QUERY_LENGTH = 140
HISTORY_LIMIT = 50
SUBMISSION_LIMIT = 150


def recent_searches(user_id):
    record = Repo.get_by_id(COLLECTION, user_id) or {}
    return [
        {"query": entry["query"], "count": entry["count"], "last_searched_at": entry["last_searched_at"]}
        for entry in record.get("searches", [])
    ]


def record_search(user_id, query, submission_id=None):
    if not isinstance(query, str):
        raise ValueError("Escribe un término de búsqueda válido.")
    query = normalize_text(query, max_length=MAX_QUERY_LENGTH + 1)
    term = " ".join(re.findall(r"[^\W_]+", key(query)))
    if not term or len(query) > MAX_QUERY_LENGTH or any(unicodedata.category(char) in {"Cc", "Cs"} for char in query):
        raise ValueError(f"Escribe un término de búsqueda de hasta {MAX_QUERY_LENGTH} caracteres.")

    if submission_id is not None:
        if not isinstance(submission_id, str) or len(submission_id) != 36:
            raise ValueError("El identificador de búsqueda no es válido.")
        try:
            identifier = UUID(submission_id)
        except ValueError:
            raise ValueError("El identificador de búsqueda no es válido.") from None
        if identifier.version != 4 or str(identifier) != submission_id.lower():
            raise ValueError("El identificador de búsqueda no es válido.")
        submission_id = str(identifier)

    with document_transaction() as conn:
        # Lock even when the user's first search has not yet created a row.
        conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (f"search-history:{user_id}",))
        record = Repo.get_by_id(COLLECTION, user_id, for_update=True)
        previous = record or {}
        submissions = previous.get("submissions", [])
        if submission_id in submissions:
            return

        searches = previous.get("searches", [])
        count = next((entry["count"] for entry in searches if entry["term"] == term), 0)
        entry = {"term": term, "query": query, "count": count + 1, "last_searched_at": now().isoformat()}
        searches = [entry, *(row for row in searches if row["term"] != term)]
        if submission_id:
            submissions = [submission_id, *submissions]

        changes = {"searches": searches[:HISTORY_LIMIT], "submissions": submissions[:SUBMISSION_LIMIT]}
        if record is None:
            Repo.create(COLLECTION, {"id": user_id, **changes})
        else:
            Repo.update(COLLECTION, user_id, changes)
