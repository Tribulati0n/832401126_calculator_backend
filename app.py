"""Flask application entry point.

Run locally with::

    python app.py

The app is built by the :func:`create_app` factory, which also wires up
the database, the services and CORS — the same factory is used by tests
and by production WSGI servers (gunicorn, waitress).
"""

from __future__ import annotations

import os

from flask import Flask, jsonify
from flask_cors import CORS

from src.config import Config
from src.controller.calculator_controller import calculator_bp
from src.model.database import Database
from src.service.calculator_service import CalculatorService
from src.service.history_service import HistoryService


def create_app(config: type[Config] = Config) -> Flask:
    """Application factory: builds and configures the Flask app."""
    app = Flask(__name__)
    app.config.from_object(config)

    # The front end runs on a different origin in this separation
    # architecture, so the API must explicitly allow cross-origin calls.
    CORS(app, resources={r"/api/*": {"origins": config.CORS_ORIGINS}})

    database = Database(config.DATABASE_PATH)
    app.extensions["calculator_service"] = CalculatorService(database)
    app.extensions["history_service"] = HistoryService(database)

    app.register_blueprint(calculator_bp)

    @app.errorhandler(404)
    def not_found(_error):  # pragma: no cover - trivial handler
        return jsonify({"success": False, "message": "Resource not found"}), 404

    @app.errorhandler(405)
    def method_not_allowed(_error):  # pragma: no cover - trivial handler
        return jsonify({"success": False, "message": "Method not allowed"}), 405

    @app.errorhandler(500)
    def server_error(_error):  # pragma: no cover - trivial handler
        return jsonify({"success": False, "message": "Internal server error"}), 500

    return app


app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", Config.PORT))
    app.run(host="0.0.0.0", port=port, debug=False)
