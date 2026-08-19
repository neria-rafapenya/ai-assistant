import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import boto3
from boto3.dynamodb.conditions import Key


class SQLiteChatRepository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
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
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    provider TEXT,
                    route TEXT,
                    sources_json TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL
                )
                """
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_chat_messages_session
                ON chat_messages (session_id, id)
                """
            )

    def save_message(
        self,
        session_id: str,
        role: str,
        content: str,
        provider: str | None = None,
        route: str | None = None,
        sources: list[str] | None = None,
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO chat_messages
                    (session_id, role, content, provider, route, sources_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    role,
                    content,
                    provider,
                    route,
                    json.dumps(sources or [], ensure_ascii=False),
                    datetime.now(timezone.utc).isoformat(),
                ),
            )

    def list_messages(self, session_id: str) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT id, session_id, role, content, provider, route,
                       sources_json, created_at
                FROM chat_messages
                WHERE session_id = ?
                ORDER BY id ASC
                """,
                (session_id,),
            ).fetchall()

        return [
            {
                "id": str(row["id"]),
                "session_id": row["session_id"],
                "role": row["role"],
                "content": row["content"],
                "provider": row["provider"],
                "route": row["route"],
                "sources": json.loads(row["sources_json"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]


class DynamoDBChatRepository:
    def __init__(self, table_name: str, region: str) -> None:
        self.table = boto3.resource("dynamodb", region_name=region).Table(table_name)

    def save_message(self, session_id: str, role: str, content: str,
                     provider: str | None = None, route: str | None = None,
                     sources: list[str] | None = None) -> None:
        item: dict[str, Any] = {
            "session_id": session_id,
            "message_id": str(uuid4()),
            "role": role,
            "content": content,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "sources": sources or [],
        }
        if provider is not None:
            item["provider"] = provider
        if route is not None:
            item["route"] = route
        self.table.put_item(Item=item)

    def list_messages(self, session_id: str) -> list[dict[str, Any]]:
        response = self.table.query(
            KeyConditionExpression=Key("session_id").eq(session_id),
            ScanIndexForward=True,
        )
        return [
            {
                "id": item["message_id"],
                "session_id": item["session_id"],
                "role": item["role"],
                "content": item["content"],
                "provider": item.get("provider"),
                "route": item.get("route"),
                "sources": item.get("sources", []),
                "created_at": item["created_at"],
            }
            for item in response.get("Items", [])
        ]
