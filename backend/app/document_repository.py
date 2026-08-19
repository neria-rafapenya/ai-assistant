import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import boto3


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


class DynamoDBDocumentRepository:
    def __init__(self, table_name: str, region: str, max_attempts: int = 3) -> None:
        self.max_attempts = max_attempts
        self.table = boto3.resource("dynamodb", region_name=region).Table(table_name)

    def start_processing(self, source_key: str) -> bool:
        existing = self.get(source_key)
        if existing and int(existing.get("attempts", 0)) >= self.max_attempts:
            return False
        now = datetime.now(timezone.utc).isoformat()
        if existing:
            self.table.update_item(
                Key={"source_key": source_key},
                UpdateExpression=(
                    "SET #status = :processing, #attempts = #attempts + :one, "
                    "#updated_at = :now REMOVE #last_error"
                ),
                ExpressionAttributeNames={
                    "#status": "status", "#attempts": "attempts",
                    "#updated_at": "updated_at", "#last_error": "last_error",
                },
                ExpressionAttributeValues={
                    ":processing": "processing", ":one": 1, ":now": now,
                },
            )
        else:
            self.table.put_item(Item={
                "source_key": source_key, "status": "processing",
                "attempts": 1, "created_at": now, "updated_at": now,
            })
        return True

    def mark_completed(self, source_key: str, processed_key: str, chunks: int) -> None:
        self.table.update_item(
            Key={"source_key": source_key},
            UpdateExpression=(
                "SET #status = :processed, #processed_key = :processed_key, "
                "#chunks = :chunks, #updated_at = :now REMOVE #last_error"
            ),
            ExpressionAttributeNames={
                "#status": "status", "#processed_key": "processed_key",
                "#chunks": "chunks", "#updated_at": "updated_at",
                "#last_error": "last_error",
            },
            ExpressionAttributeValues={
                ":processed": "processed", ":processed_key": processed_key,
                ":chunks": chunks, ":now": datetime.now(timezone.utc).isoformat(),
            },
        )

    def mark_failed(self, source_key: str, error: str) -> None:
        self.table.update_item(
            Key={"source_key": source_key},
            UpdateExpression="SET #status = :failed, #last_error = :error, #updated_at = :now",
            ExpressionAttributeNames={
                "#status": "status", "#last_error": "last_error", "#updated_at": "updated_at",
            },
            ExpressionAttributeValues={
                ":failed": "failed", ":error": error[:2000],
                ":now": datetime.now(timezone.utc).isoformat(),
            },
        )

    def get(self, source_key: str) -> dict[str, Any] | None:
        response = self.table.get_item(Key={"source_key": source_key})
        return response.get("Item")
