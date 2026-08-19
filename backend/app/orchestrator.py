from dataclasses import dataclass
from typing import Any, Protocol


class ChatProvider(Protocol):
    provider_name: str

    def generate_reply(self, message: str) -> Any:
        """Generate a response for the user message."""


class EmbeddingProvider(Protocol):
    def embed(self, text: str) -> list[float]:
        """Create an embedding for a text query."""


class VectorStore(Protocol):
    def search(self, vector: list[float], limit: int = 5) -> list[dict[str, Any]]:
        """Return the most relevant indexed chunks."""


@dataclass
class OrchestratorResult:
    reply: str
    provider: str
    route: str
    sources: list[str]


class Orchestrator:
    """Coordinates the chat request without coupling it to AWS services."""

    def __init__(
        self,
        chat_provider: ChatProvider,
        embedding_provider: EmbeddingProvider,
        vector_store: VectorStore,
    ) -> None:
        self.chat_provider = chat_provider
        self.embedding_provider = embedding_provider
        self.vector_store = vector_store

    def handle(self, message: str) -> OrchestratorResult:
        query = message.strip()
        candidates = self.vector_store.search(
            self.embedding_provider.embed(query),
            limit=3,
        )
        relevant = [candidate for candidate in candidates if candidate.get("score", 0) > 0]
        route = "rag" if relevant else "general"
        sources = list(dict.fromkeys(candidate["source_key"] for candidate in relevant))

        provider_result = self.chat_provider.generate_reply(query)
        return OrchestratorResult(
            reply=provider_result.reply,
            provider=provider_result.provider,
            route=route,
            sources=sources,
        )
