from pathlib import Path
from typing import Any, Protocol

from app.vector_index import LocalVectorIndex
from app.opensearch_store import OpenSearchVectorStore


class VectorStore(Protocol):
    def upsert(self, records: list[dict[str, Any]]) -> None:
        ...

    def search(
        self,
        vector: list[float],
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        ...


def create_vector_store(
    backend: str,
    local_index_path: Path,
    dimensions: int,
    opensearch_endpoint: str = "",
    opensearch_index: str = "ai-assistant-documents",
    aws_region: str = "eu-west-1",
    opensearch_service: str = "aoss",
) -> VectorStore:
    if backend == "local":
        return LocalVectorIndex(local_index_path, dimensions)

    if backend == "opensearch":
        return OpenSearchVectorStore(
            endpoint=opensearch_endpoint,
            index_name=opensearch_index,
            dimensions=dimensions,
            region=aws_region,
            service=opensearch_service,
        )

    raise ValueError(f"Unknown vector store backend: {backend}")
