import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import boto3


class SQLiteProfileRepository:
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
                CREATE TABLE IF NOT EXISTS user_profiles (
                    user_id TEXT PRIMARY KEY,
                    profile_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def get(self, user_id: str) -> dict[str, Any] | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT profile_json FROM user_profiles WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        return json.loads(row["profile_json"]) if row else None

    def save(self, user_id: str, profile: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT created_at FROM user_profiles WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            created_at = existing["created_at"] if existing else now
            connection.execute(
                """
                INSERT INTO user_profiles (user_id, profile_json, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    profile_json = excluded.profile_json,
                    updated_at = excluded.updated_at
                """,
                (user_id, json.dumps(profile, ensure_ascii=False), created_at, now),
            )
        return profile


class DynamoDBProfileRepository:
    def __init__(self, table_name: str, region: str) -> None:
        self.table = boto3.resource("dynamodb", region_name=region).Table(table_name)

    def get(self, user_id: str) -> dict[str, Any] | None:
        response = self.table.get_item(Key={"user_id": user_id})
        item = response.get("Item")
        if not item:
            return None
        return {key: value for key, value in item.items() if key not in {"user_id", "created_at", "updated_at"}}

    def save(self, user_id: str, profile: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        self.table.put_item(
            Item={
                "user_id": user_id,
                **profile,
                "updated_at": now,
            }
        )
        return profile
