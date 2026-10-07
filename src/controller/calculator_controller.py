"""HTTP API controller.

Exposes the calculator over clean REST endpoints and translates every
engine exception into a standardized JSON error response.

Endpoints
---------
POST   /api/calculate          Evaluate an expression and store it
GET    /api/history            List history (search + pagination)
DELETE /api/history/{id}       Delete one history record
DELETE /api/history            Clear all history (extension)
GET    /api/health             Liveness check for deployment probes
"""

from __future__ import annotations

from datetime import datetime

from flask import Blueprint, current_app, jsonify, request

from ..calculator.exceptions import CalculatorError
from ..service.calculator_service import CalculatorService
from ..service.history_service import HistoryService

calculator_bp = Blueprint("calculator", __name__, url_prefix="/api")


def _get_services() -> tuple[CalculatorService, HistoryService]:
    """Pull the shared service instances off the Flask app object."""
    app = current_app
    return app.extensions["calculator_service"], app.extensions["history_service"]


@calculator_bp.post("/calculate")
def calculate():
    """Evaluate ``{"expression": "..."}`` and persist the result."""
    calculator_service, _ = _get_services()

    payload = request.get_json(silent=True)
    if payload is None:
        return _error("Request body must be valid JSON"), 400
    if "expression" not in payload:
        return _error("Missing required field 'expression'"), 400
    if not isinstance(payload["expression"], str):
        return _error("Field 'expression' must be a string"), 400

    try:
        record = calculator_service.calculate(payload["expression"])
    except CalculatorError as exc:
        # Expected, user-caused failures: invalid expression, division by
        # zero, out-of-domain math, overflow, ...
        return _error(str(exc)), 400

    return jsonify({
        "success": True,
        "id": record["id"],
        "expression": record["expression"],
        "result": record["result"],
        "created_at": record["created_at"],
    }), 200


@calculator_bp.get("/history")
def history():
    """List history records with optional ``q`` / ``limit`` / ``offset``."""
    _, history_service = _get_services()

    raw_limit = request.args.get("limit", "50")
    raw_offset = request.args.get("offset", "0")
    query = request.args.get("q", "").strip()

    try:
        limit = int(raw_limit)
        offset = int(raw_offset)
    except ValueError:
        return _error("'limit' and 'offset' must be integers"), 400

    records, total = history_service.list_history(limit, offset, query)
    return jsonify({
        "success": True,
        "data": records,
        "total": total,
        "limit": limit,
        "offset": offset,
    }), 200


@calculator_bp.delete("/history/<int:history_id>")
def delete_history(history_id: int):
    """Delete a single history record identified by its id."""
    _, history_service = _get_services()

    deleted = history_service.delete_history(history_id)
    if not deleted:
        return _error(f"History record {history_id} does not exist"), 404

    return jsonify({"success": True, "deleted": True, "id": history_id}), 200


@calculator_bp.delete("/history")
def clear_history():
    """Delete all history records (optional extension)."""
    _, history_service = _get_services()

    count = history_service.clear_history()
    return jsonify({"success": True, "deleted": count}), 200


@calculator_bp.get("/health")
def health():
    """Return liveness information used by deployment health checks."""
    return jsonify({
        "status": "ok",
        "service": "832401126_calculator_backend",
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }), 200


def _error(message: str) -> dict:
    """Standardized error payload."""
    return {"success": False, "message": message}
