"""Data model for a single calculation-history record."""

from __future__ import annotations

from dataclasses import dataclass

import sqlite3


@dataclass
class HistoryRecord:
    """One row of the ``calculation_history`` table."""

    id: int
    expression: str
    result: str
    created_at: str

    def to_dict(self) -> dict:
        """JSON-serializable representation used by the API."""
        return {
            "id": self.id,
            "expression": self.expression,
            "result": self.result,
            "created_at": self.created_at,
        }

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "HistoryRecord":
        return cls(
            id=row["id"],
            expression=row["expression"],
            result=row["result"],
            created_at=row["created_at"],
        )
