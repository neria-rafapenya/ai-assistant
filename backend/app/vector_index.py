import json
from pathlib import Path
from typing import Any


class LocalVectorIndex:
    def __init__(self, path: Path, dimensions: int) -> None:
        self.path = path
        self.dimensions = dimensions
        self.records: list[dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        data = json.loads(self.path.read_text(encoding="utf-8"))
        self.records = data.get("records", [])

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(
                {"dimensions": self.dimensions, "records": self.records},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

    def upsert(self, records: list[dict[str, Any]]) -> None:
        ids = {record["id"] for record in records}
        self.records = [record for record in self.records if record["id"] not in ids]
        self.records.extend(records)
        self._save()

    def search(self, vector: list[float], limit: int = 5) -> list[dict[str, Any]]:
        scored: list[dict[str, Any]] = []
        for record in self.records:
            candidate = record["embedding"]
            score = sum(left * right for left, right in zip(vector, candidate, strict=True))
            scored.append({**record, "score": round(score, 6)})
        return sorted(scored, key=lambda item: item["score"], reverse=True)[:limit]
