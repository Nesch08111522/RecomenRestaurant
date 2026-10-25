import logging
import os
import uuid

from flask import Flask, jsonify, render_template, request
from flask_wtf.csrf import CSRFError

# Load local secrets before importing configuration and route modules. Existing
# process environment variables take precedence over values in the local file.
try:
    from dotenv import load_dotenv
except ImportError:  # The app still runs with process-level environment variables.
    load_dotenv = None
if load_dotenv:
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"), override=False)

from config import Config
from context_processors import inject_globals
from utils.security import csrf
from views.admin import admin_bp
from views.auth import auth_bp
from views.main import main_bp
from views.owner import owner_bp

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

    @app.context_processor
    def inject():
        return inject_globals()

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "geolocation=(self)")
        response.headers.setdefault("X-Request-ID", request.headers.get("X-Request-ID", str(uuid.uuid4())))
        return response

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        if request.is_json or request.path.startswith("/api/"):
            return jsonify({"error": "Solicitud no autorizada", "code": "csrf_invalid"}), 400
        return render_template("500.html"), 400

    @app.errorhandler(404)
    def not_found(error):
        if request.is_json or request.path.startswith("/api/"):
            return jsonify({"error": "Recurso no encontrado"}), 404
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        logger.exception("Error interno request_id=%s", request.headers.get("X-Request-ID"))
        if request.is_json or request.path.startswith("/api/"):
            return jsonify({"error": "Error interno del servidor"}), 500
        return render_template("500.html"), 500

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=app.config["DEBUG"])
