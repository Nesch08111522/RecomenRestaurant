import logging
import os
import uuid

from flask import Flask, jsonify, render_template, request
from flask_wtf.csrf import CSRFError

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None

if load_dotenv:
    load_dotenv(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"), override=False
    )

from config import Config
from context_processors import inject_globals
from utils.security import csrf
from views.admin import admin_bp
from views.admin_ai_routes import admin_ai_bp
from views.auth import auth_bp
from views.main import main_bp
from views.owner import owner_bp
from views.ai_routes import ai_bp

logger = logging.getLogger(__name__)


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)

    if test_config:
        app.config.update(test_config)

    if not app.config.get("TESTING"):
        Config.validate()

        from database.connection import check_application_schema

        check_application_schema()

    csrf.init_app(app)

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(owner_bp, url_prefix="/owner")

    app.register_blueprint(ai_bp)
    csrf.exempt(ai_bp)

    app.register_blueprint(admin_ai_bp)

    @app.context_processor
    def inject():
        return inject_globals()

    @app.before_request
    def assign_request_id():
        request.request_id = str(uuid.uuid4())

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault(
            "Referrer-Policy", "strict-origin-when-cross-origin"
        )
        response.headers.setdefault("Permissions-Policy", "geolocation=(self)")
        response.headers.setdefault(
            "X-Request-ID", getattr(request, "request_id", str(uuid.uuid4()))
        )

        if request.path.startswith("/admin/api/ai/"):
            response.headers["Cache-Control"] = "no-store"

        return response

    def is_api_request():
        return (
            request.is_json
            or request.path.startswith("/api/")
            or request.path.startswith("/admin/api/")
        )

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        if is_api_request():
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Solicitud no autorizada. Verifica el token CSRF.",
                        "code": "csrf_invalid",
                    }
                ),
                400,
            )

        return render_template("500.html"), 400

    @app.errorhandler(400)
    def bad_request(error):
        if is_api_request():
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Solicitud inválida.",
                        "code": "bad_request",
                    }
                ),
                400,
            )

        return render_template("500.html"), 400

    @app.errorhandler(404)
    def not_found(error):
        if is_api_request():
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Recurso no encontrado.",
                        "code": "not_found",
                    }
                ),
                404,
            )

        return render_template("404.html"), 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        if is_api_request():
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Método HTTP no permitido.",
                        "code": "method_not_allowed",
                    }
                ),
                405,
            )

        return render_template("500.html"), 405

    @app.errorhandler(413)
    def payload_too_large(error):
        if is_api_request():
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "El archivo o contenido supera el tamaño permitido.",
                        "code": "payload_too_large",
                    }
                ),
                413,
            )

        return render_template("500.html"), 413

    @app.errorhandler(500)
    def internal_error(error):
        logger.error(
            "Error interno de SmartResto. request_id=%s",
            getattr(request, "request_id", "unknown"),
            exc_info=(
                error.original_exception
                if hasattr(error, "original_exception")
                else error
            ),
        )

        if is_api_request():
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Error interno del servidor.",
                        "code": "internal_error",
                        "request_id": getattr(request, "request_id", None),
                    }
                ),
                500,
            )

        return render_template("500.html"), 500

    return app


if __name__ == "__main__":
    app = create_app()

    app.run(host="127.0.0.1", port=5000, debug=app.config["DEBUG"])
