from app.opensearch_store import OpenSearchVectorStore


class FakeIndices:
    def __init__(self) -> None:
        self.created = None

    def exists(self, index: str) -> bool:
        return False

    def create(self, index: str, body: dict) -> None:
        self.created = {"index": index, "body": body}


class FakeOpenSearchClient:
    def __init__(self) -> None:
        self.indices = FakeIndices()
        self.bulk_call = None
        self.search_call = None

    def bulk(self, **kwargs):
        self.bulk_call = kwargs
        return {"errors": False}

    def search(self, **kwargs):
        self.search_call = kwargs
        return {
            "hits": {
                "hits": [
                    {
                        "_id": "doc#0",
                        "_score": 0.91,
                        "_source": {
                            "source_key": "incoming/doc.pdf",
                            "page": 1,
                            "text": "contenido",
                        },
                    }
                ]
            }
        }


def test_opensearch_store_creates_mapping_and_searches() -> None:
    client = FakeOpenSearchClient()
    store = OpenSearchVectorStore(
        endpoint="https://example.aoss.amazonaws.com",
        index_name="documents",
        dimensions=4,
        region="eu-west-1",
        client=client,
    )

    store.create_index()
    store.upsert(
        [
            {
                "id": "doc#0",
                "source_key": "incoming/doc.pdf",
                "page": 1,
                "text": "contenido",
                "embedding": [0.1, 0.2, 0.3, 0.4],
            }
        ]
    )
    results = store.search([0.1, 0.2, 0.3, 0.4], limit=3)

    assert client.indices.created["index"] == "documents"
    embedding_mapping = client.indices.created["body"]["mappings"]["properties"]["embedding"]
    assert embedding_mapping["dimension"] == 4
    assert "engine" not in embedding_mapping
    assert client.bulk_call["refresh"] == "wait_for"
    assert client.search_call["body"]["size"] == 3
    assert results[0]["source_key"] == "incoming/doc.pdf"
