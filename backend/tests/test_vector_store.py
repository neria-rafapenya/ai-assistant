import pytest

from app.vector_index import LocalVectorIndex
from app.vector_store import create_vector_store


def test_vector_store_factory_uses_local_backend(tmp_path) -> None:
    store = create_vector_store(
        backend="local",
        local_index_path=tmp_path / "vector_index.json",
        dimensions=4,
    )

    assert isinstance(store, LocalVectorIndex)


def test_vector_store_factory_rejects_unimplemented_opensearch(tmp_path) -> None:
    with pytest.raises(RuntimeError, match="OpenSearch backend is not implemented"):
        create_vector_store(
            backend="opensearch",
            local_index_path=tmp_path / "vector_index.json",
            dimensions=4,
        )
