"""Business logic for reading and deleting calculation history."""

from __future__ import annotations

from ..model.database import Database
from ..model.history_model import HistoryRecord


class HistoryService:
    """CRUD operations on the calculation-history table."""

    def __init__(self, database: Database) -> None:
        self._database = database

    def list_history(self, limit: int = 50, offset: int = 0,
                     query: str = "") -> tuple[list[dict], int]:
        """Return (records, total_count) filtered by an optional search.

        ``query`` performs a substring match against the expression, which
        powers the history-search extension.  ``limit``/``offset`` provide
        simple pagination.
        """
        limit = max(0, min(limit, 200))
        offset = max(0, offset)

        where = ""
        params: list = []
        if query:
            where = "WHERE expression LIKE ?"
            params.append(f"%{query}%")

        total_row = self._database.query_one(
            f"SELECT COUNT(*) AS total FROM calculation_history {where}",
            tuple(params),
        )
        total = int(total_row["total"]) if total_row else 0

        rows = self._database.query(
            f"SELECT id, expression, result, created_at "
            f"FROM calculation_history {where} "
            f"ORDER BY id DESC LIMIT ? OFFSET ?",
            tuple(params + [limit, offset]),
        )
        records = [HistoryRecord.from_row(row).to_dict() for row in rows]
        return records, total

    def delete_history(self, history_id: int) -> bool:
        """Delete one record; return True if a row was actually removed."""
        cursor = self._database.execute_write(
            "DELETE FROM calculation_history WHERE id = ?", (history_id,)
        )
        return cursor.rowcount > 0

    def clear_history(self) -> int:
        """Delete every record and return how many rows were removed."""
        cursor = self._database.execute_write("DELETE FROM calculation_history")
        return cursor.rowcount
