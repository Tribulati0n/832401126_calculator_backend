"""SQLite database access layer.

A new connection is opened per operation, which keeps things safe in a
multi-threaded WSGI server without shared connection state.  WAL mode
allows concurrent readers while a single writer holds a short lock.
"""

from __future__ import annotations

import os
import sqlite3
import threading
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS calculation_history (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    expression  TEXT    NOT NULL,
    result      TEXT    NOT NULL,
    created_at  TEXT    NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_history_created_at
    ON calculation_history (created_at DESC);
"""


class Database:
    """Thin wrapper around a SQLite database file."""

    def __init__(self, path: str) -> None:
        self.path = str(path)
        # Writes are serialized with a lock so concurrent requests never
        # trip over SQLite's "database is locked" error.
        self._write_lock = threading.Lock()
        self._ensure_directory()
        self.init_schema()

    def _ensure_directory(self) -> None:
        directory = os.path.dirname(self.path)
        if directory:
            Path(directory).mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        """Open a new connection with row access by column name."""
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def init_schema(self) -> None:
        """Create the ``calculation_history`` table if it does not exist."""
        with self._write_lock:
            connection = self.connect()
            try:
                connection.executescript(_SCHEMA)
                connection.commit()
            finally:
                connection.close()

    def execute_write(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        """Run an INSERT/UPDATE/DELETE inside the serialized writer."""
        with self._write_lock:
            connection = self.connect()
            try:
                cursor = connection.execute(sql, params)
                connection.commit()
                return cursor
            finally:
                connection.close()

    def query(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        """Run a SELECT and return all rows."""
        connection = self.connect()
        try:
            return connection.execute(sql, params).fetchall()
        finally:
            connection.close()

    def query_one(self, sql: str, params: tuple = ()) -> sqlite3.Row | None:
        """Run a SELECT and return the first row, if any."""
        rows = self.query(sql, params)
        return rows[0] if rows else None
