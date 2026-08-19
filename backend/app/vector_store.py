from pathlib import Path
from typing import Any, Protocol

from app.vector_index import LocalVectorIndex


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
) -> VectorStore:
    if backend == "local":
        return LocalVectorIndex(local_index_path, dimensions)

    if backend == "opensearch":
        raise RuntimeError(
            "OpenSearch backend is not implemented yet; keep VECTOR_STORE_BACKEND=local"
        )

    raise ValueError(f"Unknown vector store backend: {backend}")
