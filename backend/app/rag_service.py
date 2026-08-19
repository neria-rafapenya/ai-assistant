from typing import Any


class RAGService:
    def __init__(self, embedding_provider: Any, vector_store: Any, min_score: float = 0.0) -> None:
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store
        self.min_score = min_score

    def retrieve(self, query: str, limit: int = 3) -> list[dict[str, Any]]:
        candidates = self.vector_store.search(
            self.embedding_provider.embed(query),
            limit=limit,
        )
        return [
            candidate
            for candidate in candidates
            if candidate.get("score", 0) > self.min_score
        ]
