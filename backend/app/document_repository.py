import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class SQLiteDocumentRepository:
    def __init__(self, database_path: Path, max_attempts: int = 3) -> None:
        self.database_path = database_path
        self.max_attempts = max_attempts
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._create_schema()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _create_schema(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    source_key TEXT PRIMARY KEY, status TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0, processed_key TEXT,
                    chunks INTEGER, last_error TEXT, created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def start_processing(self, source_key: str) -> bool:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT attempts FROM documents WHERE source_key = ?", (source_key,)
            ).fetchone()
            if row and row["attempts"] >= self.max_attempts:
                return False
            if row:
                connection.execute(
                    """
                    UPDATE documents SET status='processing', attempts=attempts+1,
                    last_error=NULL, updated_at=? WHERE source_key=?
                    """,
                    (now, source_key),
                )
            else:
                connection.execute(
                    """
                    INSERT INTO documents
                    (source_key,status,attempts,created_at,updated_at)
                    VALUES (?, 'processing', 1, ?, ?)
                    """,
                    (source_key, now, now),
                )
        return True

    def mark_completed(self, source_key: str, processed_key: str, chunks: int) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE documents SET status='processed', processed_key=?, chunks=?,
                last_error=NULL, updated_at=? WHERE source_key=?
                """,
                (processed_key, chunks, datetime.now(timezone.utc).isoformat(), source_key),
            )

    def mark_failed(self, source_key: str, error: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE documents SET status='failed', last_error=?, updated_at=?
                WHERE source_key=?
                """,
                (error[:2000], datetime.now(timezone.utc).isoformat(), source_key),
            )

    def get(self, source_key: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM documents WHERE source_key = ?", (source_key,)
            ).fetchone()
        return dict(row) if row else None
