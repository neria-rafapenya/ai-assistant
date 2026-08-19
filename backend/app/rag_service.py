import re
from typing import Any


class RAGService:
    def __init__(self, embedding_provider: Any, vector_store: Any, min_score: float = 0.0) -> None:
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store
        self.min_score = min_score

    def retrieve(self, query: str, limit: int = 3) -> list[dict[str, Any]]:
        query_terms = self._terms(query)
        candidates = self.vector_store.search(
            self.embedding_provider.embed(query),
            limit=limit,
        )
        return [
            candidate
            for candidate in candidates
            if candidate.get("score", 0) > self.min_score
            and query_terms.intersection(self._terms(candidate.get("text", "")))
        ]

    @staticmethod
    def _terms(text: str) -> set[str]:
        stop_words = {
            "a",
            "al",
            "con",
            "como",
            "de",
            "del",
            "el",
            "en",
            "es",
            "la",
            "las",
            "los",
            "me",
            "para",
            "por",
            "que",
            "qué",
            "se",
            "un",
            "una",
            "y",
        }
        return {
            term
            for term in re.findall(r"[\wáéíóúüñ]+", text.lower())
            if term not in stop_words and len(term) > 2
        }
