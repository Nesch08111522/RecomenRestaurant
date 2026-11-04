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
    interpret_moderation_query,
)
from views.admin import _fresh_session_user

logger = logging.getLogger(__name__)
admin_ai_bp = Blueprint("admin_ai", __name__, url_prefix="/admin/api/ai")


def _missing_audit_table(exc):
    return getattr(exc, "sqlstate", None) == "42P01"


def _audit_error_response(exc):
    if _missing_audit_table(exc):
        logger.error("Falta la tabla public.ai_decisions; aplica database/ai_decisions.sql")
        return jsonify(
            success=False,
            error="Falta instalar la tabla de auditoría de IA. Ejecuta database/ai_decisions.sql en el SQL Editor de Supabase.",
            code="ai_audit_schema_missing",
        ), 503
    logger.exception("No se pudo reservar auditoría de IA")
    return jsonify(success=False, error="Auditoría no disponible", code="ai_audit_unavailable"), 503


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
    except Exception as exc:
        return _audit_error_response(exc)
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


@admin_ai_bp.post("/moderation-query")
@admin_ai_required
def moderation_query():
    """Convierte lenguaje natural en filtros cerrados; nunca ejecuta acciones."""
    if not request.is_json:
        return jsonify(success=False, error="Se requiere application/json"), 415
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or set(data) != {"text"} or not isinstance(data["text"], str):
        return jsonify(success=False, error="Envía únicamente text como cadena"), 400
    text = data["text"].strip()
    if not 5 <= len(text) <= 500:
        return jsonify(success=False, error="La consulta debe tener entre 5 y 500 caracteres"), 400
    from models.restaurant import RestaurantModel

    districts = sorted({str(r.get("district", "")).strip() for r in RestaurantModel.get_pending() if r.get("district")})
    clean, digest = canonical_payload(text)
    actor = int(session["user_id"])
    started = time.monotonic()
    try:
        _, _, model, _ = provider_settings()
        reservation = AIDecisionModel.reserve(actor_user_id=actor, tipo="filtro_moderacion", entrada_hash=digest)
        if reservation is None:
            return jsonify(success=False, error="Límite de 10 solicitudes por minuto", code="rate_limit"), 429
    except AIUnavailable as exc:
        return jsonify(success=False, error="Proveedor no configurado", code=exc.code), 503
    except Exception as exc:
        return _audit_error_response(exc)

    state, output, code = "ok", None, None
    try:
        parsed, model = interpret_moderation_query(clean, districts)
        output = parsed.model_dump()
    except (AIUnavailable, AIResponseInvalid) as exc:
        state = "unavailable" if isinstance(exc, AIUnavailable) else "error"
        code = getattr(exc, "code", "invalid_ai_response")
    except Exception:
        logger.exception("Error al convertir consulta de moderación")
        state, code = "unavailable", "provider_unavailable"
    try:
        AIDecisionModel.finish(reservation, estado=state, entrada_resumida={"length": len(clean), "sha256": digest}, salida_ia=output, modelo=model, latencia_ms=int((time.monotonic() - started) * 1000), error_codigo=code)
    except Exception:
        logger.exception("Error al registrar consulta de moderación")
        return jsonify(success=False, error="No se pudo registrar el análisis"), 503
    if state != "ok":
        return jsonify(success=False, error="No se pudo interpretar la consulta", code=code), 503
    return jsonify(success=True, filters=output)
