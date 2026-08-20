import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import boto3
from botocore.exceptions import ClientError


class UsageLimitExceeded(Exception):
    """Raised when a user has exhausted a daily product quota."""


def period_key(now: datetime | None = None) -> str:
    current = now or datetime.now(timezone.utc)
    return current.strftime("%Y-%m-%d")


class SQLiteUsageRepository:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS usage_counters (
                    user_id TEXT NOT NULL,
                    period_key TEXT NOT NULL,
                    tarot_count INTEGER NOT NULL DEFAULT 0,
                    chat_count INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, period_key)
                )
                """
            )

    def consume(self, user_id: str, kind: str, limit: int) -> int:
        if kind not in {"tarot", "chat"}:
            raise ValueError(f"Unknown usage kind: {kind}")
        column = f"{kind}_count"
        current_period = period_key()
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.database_path) as connection:
            connection.execute(
                """
                INSERT INTO usage_counters
                    (user_id, period_key, tarot_count, chat_count, updated_at)
                VALUES (?, ?, 0, 0, ?)
                ON CONFLICT(user_id, period_key) DO NOTHING
                """,
                (user_id, current_period, now),
            )
            row = connection.execute(
                f"SELECT {column} FROM usage_counters WHERE user_id = ? AND period_key = ?",
                (user_id, current_period),
            ).fetchone()
            current_count = int(row[0]) if row else 0
            if current_count >= limit:
                raise UsageLimitExceeded
            next_count = current_count + 1
            connection.execute(
                f"UPDATE usage_counters SET {column} = ?, updated_at = ? "
                "WHERE user_id = ? AND period_key = ?",
                (next_count, now, user_id, current_period),
            )
            return next_count


class DynamoDBUsageRepository:
    def __init__(self, table_name: str, region: str) -> None:
        self.table = boto3.resource("dynamodb", region_name=region).Table(table_name)

    def consume(self, user_id: str, kind: str, limit: int) -> int:
        if kind not in {"tarot", "chat"}:
            raise ValueError(f"Unknown usage kind: {kind}")
        column = f"{kind}_count"
        try:
            response = self.table.update_item(
                Key={"user_id": user_id, "period_key": period_key()},
                UpdateExpression=(
                    "SET #counter = if_not_exists(#counter, :zero) + :one, "
                    "updated_at = :updated_at"
                ),
                ConditionExpression=(
                    "attribute_not_exists(#counter) OR #counter < :limit"
                ),
                ExpressionAttributeNames={"#counter": column},
                ExpressionAttributeValues={
                    ":zero": 0,
                    ":one": 1,
                    ":limit": limit,
                    ":updated_at": datetime.now(timezone.utc).isoformat(),
                },
                ReturnValues="UPDATED_NEW",
            )
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") == "ConditionalCheckFailedException":
                raise UsageLimitExceeded from exc
            raise
        return int(response["Attributes"][column])


def usage_snapshot(user_id: str, sandbox: bool, tarot_limit: int, chat_limit: int) -> dict[str, Any]:
    return {
        "period": period_key(),
        "tarot_limit": None if sandbox else tarot_limit,
        "chat_limit": None if sandbox else chat_limit,
        "sandbox": sandbox,
    }
