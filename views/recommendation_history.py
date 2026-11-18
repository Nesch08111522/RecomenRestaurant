"""Authenticated search history for the recommendation engine."""

from flask import Blueprint, jsonify, request

from models.recommendation_history import recent_searches, record_search
from utils.security import fresh_session_user


bp = Blueprint("recommendation_history", __name__)


def _private_json(data, status=200):
    response = jsonify(data)
    response.status_code = status
    response.headers["Cache-Control"] = "private, no-store"
    response.vary.add("Cookie")
    return response


@bp.route("/api/recomendaciones/historial", methods=["GET", "POST"])
def history():
    user = fresh_session_user()
    if not user:
        return _private_json({"success": False, "error": "Inicia sesión para usar el historial."}, 401)
    if request.method == "GET":
        return _private_json({"success": True, "history": recent_searches(user["id"])})

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return _private_json({"success": False, "error": "Envía un objeto JSON."}, 400)
    try:
        record_search(user["id"], data.get("query"), data.get("submission_id"))
    except ValueError as error:
        return _private_json({"success": False, "error": str(error)}, 400)
    return _private_json({"success": True})
