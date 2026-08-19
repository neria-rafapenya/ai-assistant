from dataclasses import dataclass
from typing import Any


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
        provider_manager: Any,
        rag_service: Any,
        prompt_builder: Any,
    ) -> None:
        self.provider_manager = provider_manager
        self.rag_service = rag_service
        self.prompt_builder = prompt_builder

    def handle(
        self,
        message: str,
        provider_name: str | None = None,
    ) -> OrchestratorResult:
        query = message.strip()
        relevant = self.rag_service.retrieve(query, limit=3)
        route = "rag" if relevant else "general"
        sources = list(dict.fromkeys(candidate["source_key"] for candidate in relevant))

        prompt = self.prompt_builder.build(query, relevant)
        provider_result = self.provider_manager.generate_reply(
            prompt,
            provider_name=provider_name,
        )
        return OrchestratorResult(
            reply=provider_result.reply,
            provider=provider_result.provider,
            route=route,
            sources=sources,
        )
