from typing import Any


class OpenSearchVectorStore:
    def __init__(
        self,
        endpoint: str,
        index_name: str,
        dimensions: int,
        region: str,
        service: str = "aoss",
        client: Any | None = None,
    ) -> None:
        if not endpoint:
            raise RuntimeError("OPENSEARCH_ENDPOINT is required")

        self.index_name = index_name
        self.dimensions = dimensions

        if client is not None:
            self.client = client
            return

        from boto3 import Session
        from opensearchpy import AWSV4SignerAuth, OpenSearch

        credentials = Session().get_credentials()
        auth = AWSV4SignerAuth(credentials, region, service)
        self.client = OpenSearch(
            hosts=[{"host": endpoint.removeprefix("https://"), "port": 443}],
            http_auth=auth,
            use_ssl=True,
            verify_certs=True,
        )

    def create_index(self) -> None:
        if self.client.indices.exists(index=self.index_name):
            return

        self.client.indices.create(
            index=self.index_name,
            body={
                "settings": {"index": {"knn": True}},
                "mappings": {
                    "properties": {
                        "source_key": {"type": "keyword"},
                        "page": {"type": "integer"},
                        "text": {"type": "text"},
                        "embedding": {
                            "type": "knn_vector",
                            "dimension": self.dimensions,
                            "method": {
                                "name": "hnsw",
                                "engine": "nmslib",
                                "space_type": "cosinesimil",
                            },
                        },
                    }
                },
            },
        )

    def upsert(self, records: list[dict[str, Any]]) -> None:
        if not records:
            return

        operations: list[dict[str, Any]] = []
        for record in records:
            operations.extend(
                [
                    {"index": {"_index": self.index_name, "_id": record["id"]}},
                    record,
                ]
            )

        response = self.client.bulk(body=operations, refresh="wait_for")
        if response.get("errors"):
            raise RuntimeError("OpenSearch bulk upsert failed")

    def search(self, vector: list[float], limit: int = 5) -> list[dict[str, Any]]:
        response = self.client.search(
            index=self.index_name,
            body={
                "size": limit,
                "query": {
                    "knn": {
                        "embedding": {
                            "vector": vector,
                            "k": limit,
                        }
                    }
                },
            },
        )
        return [
            {
                **hit.get("_source", {}),
                "id": hit.get("_id"),
                "score": round(hit.get("_score", 0.0), 6),
            }
            for hit in response.get("hits", {}).get("hits", [])
        ]
