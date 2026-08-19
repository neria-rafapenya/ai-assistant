from app.rag_service import RAGService


class FakeEmbeddingProvider:
    def embed(self, text: str) -> list[float]:
        return [1.0]


class FakeVectorStore:
    def search(self, vector: list[float], limit: int = 5):
        return [
            {
                "id": "document#1",
                "source_key": "incoming/document.pdf",
                "text": "Experiencia profesional con React y TypeScript.",
                "score": 0.9,
            }
        ]


def test_rag_ignores_high_scoring_unrelated_context() -> None:
    service = RAGService(FakeEmbeddingProvider(), FakeVectorStore())

    results = service.retrieve("qué tiempo hace hoy")

    assert results == []


def test_rag_keeps_context_with_shared_relevant_term() -> None:
    service = RAGService(FakeEmbeddingProvider(), FakeVectorStore())

    results = service.retrieve("experiencia con React")

    assert len(results) == 1
    assert results[0]["source_key"] == "incoming/document.pdf"
