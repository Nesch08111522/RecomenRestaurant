"""Endpoints transversales de la plataforma SmartResto."""
from __future__ import annotations

from flask import Blueprint, current_app, g, jsonify, request, session

from config import Config
from core.platform_context import build_platform_context
from core.platform_manifest import platform_manifest
from core.permissions import permissions_for_role
from core.profile import normalize_profile_patch
from models.user import UserModel
from utils.security import fresh_session_user, session_identity

bp = Blueprint("platform", __name__, url_prefix="/api/platform")


@bp.get("/manifest")
def manifest():
    payload = platform_manifest()
    payload["context"] = build_platform_context(session).as_public_dict()
    return jsonify(payload)


@bp.get("/health")
def health():
    """Return non-sensitive readiness information for UI and observability."""
    from database.connection import check_connection
    from utils.llm_provider import AIUnavailable, settings
    try:
        database_ready = bool(check_connection())
    except Exception as error:
        current_app.logger.warning("PostgreSQL no disponible en health: %s", type(error).__name__)
        database_ready = False
    try:
        settings()
        ai_configured = True
    except AIUnavailable:
        ai_configured = False
    return jsonify(
        {
            "status": "ready" if database_ready else "degraded",
            "product": Config.NOMBRE_APP,
            "integrations": {
                "database": database_ready,
                "openrouter": ai_configured,
                "csrf": True,
                "audit": True,
            },
            "checks": {"database": "live", "openrouter": "configuration_only"},
        }
    ), 200 if database_ready else 503


@bp.get("/me")
def me():
    """Return the authenticated user's safe identity and effective permissions."""
    user = fresh_session_user()
    if not user:
        return jsonify({"authenticated": False, "context": build_platform_context(session).as_public_dict()}), 401
    return jsonify(
        {
            "authenticated": True,
            "user": session_identity(user),
            "context": build_platform_context(session).as_public_dict(),
            "permissions": permissions_for_role(user.get("role")),
        }
    )


@bp.patch("/me/profile")
def update_me_profile():
    """Update only allowlisted personal preferences; role data is never client-editable."""
    user = fresh_session_user()
    if not user:
        return jsonify({"success": False, "error": "No autenticado"}), 401
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"success": False, "error": "El cuerpo debe ser un objeto JSON"}), 400
    try:
        changes = normalize_profile_patch(payload)
    except ValueError as error:
        return jsonify({"success": False, "error": str(error)}), 400
    if not changes:
        return jsonify({"success": False, "error": "No hay cambios de perfil permitidos"}), 400
    profile = dict(g.account_record.get("profile") or {})
    if 'email' in changes and changes['email'] != profile.get('email',''):
        from utils.account_security import configure
        password=payload.get('current_password');otp=payload.get('otp','')
        if not isinstance(password,str) or not isinstance(otp,str):
            return jsonify(success=False,error='Confirma la contraseña actual para cambiar el correo de recuperación.'),403
        try:
            result=configure(user['id'],password,'contacts',otp,email=changes['email'],phone=profile.get('phone',''))
            session['auth_epoch']=result['epoch']
        except ValueError:
            return jsonify(success=False,error='Verifica tu contraseña y, si corresponde, el código del autenticador.'),403
    if "notification_preferences" in changes:
        changes["notification_preferences"] = {
            **(profile.get("notification_preferences") or {}),
            **changes["notification_preferences"],
        }
    profile.update(changes)
    if "notification_preferences" in changes:
        profile["promotions_opt_in"] = profile["notification_preferences"].get("marketing", profile.get("promotions_opt_in", False))
    updated = UserModel.update(user["id"], {"profile": profile})
    if not updated:
        return jsonify({"success": False, "error": "No se pudo actualizar el perfil"}), 409
    session["user"] = session_identity(updated)
    return jsonify({"success": True, "user": session_identity(updated), "profile": profile})
