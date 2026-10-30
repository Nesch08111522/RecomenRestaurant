"""API IA de administración, protegida por sesión y CSRF global."""

from __future__ import annotations
import logging
import time
from functools import wraps
from flask import Blueprint, jsonify, request, session
from models.ai_decision import AIDecisionModel
from utils.admin_ai import (
    AIResponseInvalid,
    AIUnavailable,
    analyze,
    canonical_payload,
    provider_settings,
)
from views.admin import _fresh_session_user

logger = logging.getLogger(__name__)
admin_ai_bp = Blueprint("admin_ai", __name__, url_prefix="/admin/api/ai")


def admin_ai_required(fn):
    @wraps(fn)
    def inner(*args, **kwargs):
        user = _fresh_session_user()
        if not user:
            return jsonify(success=False, error="Autenticación requerida"), 401
        if user.get("role") != "admin":
            return jsonify(success=False, error="Acceso denegado"), 403
        return fn(*args, **kwargs)

    return inner


@admin_ai_bp.get("/health")
@admin_ai_required
def health():
    return jsonify(success=True, service="admin_ai", writes_enabled=False)


@admin_ai_bp.post("/analyze")
@admin_ai_required
def analyze_text():
    if not request.is_json:
        return jsonify(success=False, error="Se requiere application/json"), 415
    data = request.get_json(silent=True)
    if (
        not isinstance(data, dict)
        or set(data) != {"text"}
        or not isinstance(data["text"], str)
    ):
        return jsonify(success=False, error="Envía únicamente text como cadena"), 400
    text = data["text"].strip()
    if not 15 <= len(text) <= 3000:
        return (
            jsonify(
                success=False, error="text debe contener entre 15 y 3000 caracteres"
            ),
            400,
        )
    cleaned, digest = canonical_payload(text)
    actor = int(session["user_id"])
    started = time.monotonic()
    summary = {"length": len(cleaned), "sha256": digest}
    try:
        _, _, model, _ = provider_settings()
    except AIUnavailable as exc:
        return (
            jsonify(success=False, error="Proveedor no configurado", code=exc.code),
            503,
        )
    try:
        reservation = AIDecisionModel.reserve(
            actor_user_id=actor, tipo="analisis_texto", entrada_hash=digest
        )
        if reservation is None:
            return (
                jsonify(
                    success=False,
                    error="Límite de 10 solicitudes por minuto",
                    code="rate_limit",
                ),
                429,
            )
    except Exception:
        logger.exception("No se pudo reservar auditoría de IA")
        return jsonify(success=False, error="Auditoría no disponible"), 503
    state, output, confidence, code = "unavailable", None, None, None
    try:
        cached = AIDecisionModel.find_recent(
            actor_user_id=actor, tipo="analisis_texto", entrada_hash=digest, model=model
        )
        if cached:
            output, confidence, state = (
                cached["salida_ia"],
                cached["confianza"],
                "cache",
            )
        else:
            result, model, _ = analyze(cleaned)
            output, confidence, state = result.model_dump(), result.confidence, "ok"
    except (AIUnavailable, AIResponseInvalid) as exc:
        code = getattr(exc, "code", "invalid_ai_response")
        state = "unavailable" if isinstance(exc, AIUnavailable) else "error"
    except Exception:
        logger.exception("Error inesperado del proveedor de IA")
        code, state = "provider_unavailable", "unavailable"
    try:
        AIDecisionModel.finish(
            reservation,
            estado=state,
            entrada_resumida=summary,
            salida_ia=output,
            modelo=model,
            confianza=confidence,
            latencia_ms=int((time.monotonic() - started) * 1000),
            error_codigo=code,
        )
    except Exception:
        logger.exception("Error al finalizar auditoría")
        return jsonify(success=False, error="No se pudo registrar el análisis"), 503
    if state not in ("ok", "cache"):
        return (
            jsonify(
                success=False,
                error="IA no disponible; continúa con revisión manual",
                code=code,
            ),
            503,
        )
    return jsonify(
        success=True, cached=(state == "cache"), decision_id=reservation, result=output
    )
