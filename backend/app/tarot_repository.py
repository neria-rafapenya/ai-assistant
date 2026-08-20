import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import boto3
from boto3.dynamodb.conditions import Key


class SQLiteTarotReadingRepository:
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
                CREATE TABLE IF NOT EXISTS tarot_readings (
                    user_id TEXT NOT NULL,
                    reading_id TEXT NOT NULL,
                    question TEXT NOT NULL,
                    spread TEXT NOT NULL,
                    style TEXT NOT NULL,
                    cards_json TEXT NOT NULL,
                    reading TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, reading_id)
                )
                """
            )

    def save(self, user_id: str, reading: dict[str, Any]) -> dict[str, Any]:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO tarot_readings
                    (user_id, reading_id, question, spread, style, cards_json,
                     reading, provider, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    reading["reading_id"],
                    reading["question"],
                    reading["spread"],
                    reading["style"],
                    json.dumps(reading["cards"], ensure_ascii=False),
                    reading["reading"],
                    reading["provider"],
                    reading["created_at"],
                ),
            )
        return reading

    def list_for_user(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT reading_id, question, spread, style, cards_json,
                       reading, provider, created_at
                FROM tarot_readings
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        return [
            {
                "reading_id": row["reading_id"],
                "question": row["question"],
                "spread": row["spread"],
                "style": row["style"],
                "cards": json.loads(row["cards_json"]),
                "reading": row["reading"],
                "provider": row["provider"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]


class DynamoDBTarotReadingRepository:
    def __init__(self, table_name: str, region: str) -> None:
        self.table = boto3.resource("dynamodb", region_name=region).Table(table_name)

    def save(self, user_id: str, reading: dict[str, Any]) -> dict[str, Any]:
        self.table.put_item(Item={"user_id": user_id, **reading})
        return reading

    def list_for_user(self, user_id: str, limit: int = 20) -> list[dict[str, Any]]:
        response = self.table.query(
            KeyConditionExpression=Key("user_id").eq(user_id),
            ScanIndexForward=False,
            Limit=limit,
        )
        return [
            {key: value for key, value in item.items() if key != "user_id"}
            for item in response.get("Items", [])
        ]


def create_reading_record(
    question: str,
    spread: str,
    style: str,
    cards: list[dict[str, str]],
    reading: str,
    provider: str,
) -> dict[str, Any]:
    return {
        "reading_id": str(uuid4()),
        "question": question,
        "spread": spread,
        "style": style,
        "cards": cards,
        "reading": reading,
        "provider": provider,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
