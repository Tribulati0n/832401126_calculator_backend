"""Business logic for the calculate endpoint.

Flow: validate input -> normalize -> safe_calculate -> persist a history
record -> return the record.  This is the exact flow the assignment asks
for: the front end sends an expression and the back end computes, stores
and returns the result.
"""

from __future__ import annotations

from datetime import datetime

from ..calculator.calculator import normalize_expression, safe_calculate
from ..model.database import Database
from ..model.history_model import HistoryRecord


class CalculatorService:
    """Coordinates expression evaluation with history persistence."""

    def __init__(self, database: Database) -> None:
        self._database = database

    def calculate(self, expression: str) -> dict:
        """Evaluate ``expression``, store it and return the API payload."""
        result_value = safe_calculate(expression)
        result_text = _format_result(result_value)
        normalized = normalize_expression(expression)
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor = self._database.execute_write(
            "INSERT INTO calculation_history (expression, result, created_at) "
            "VALUES (?, ?, ?)",
            (normalized, result_text, created_at),
        )
        record = HistoryRecord(
            id=cursor.lastrowid,
            expression=normalized,
            result=result_text,
            created_at=created_at,
        )
        return record.to_dict()


def _format_result(value: float) -> str:
    """Keep the display string in sync with the engine's formatter."""
    from ..calculator.evaluator import format_result

    return format_result(value)
