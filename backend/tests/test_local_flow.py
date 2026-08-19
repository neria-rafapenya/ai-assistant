from io import BytesIO

from fastapi.testclient import TestClient

from app.main import app, rag_service
from app.vector_index import LocalVectorIndex


class FakeS3Client:
    def __init__(self) -> None:
        self.saved_objects: dict[str, bytes] = {}

    def get_object(self, Bucket: str, Key: str):
        return {"Body": BytesIO(b"fake pdf bytes")}

    def put_object(self, Bucket: str, Key: str, Body: bytes, ContentType: str):
        self.saved_objects[Key] = Body


def test_local_document_to_rag_chat_flow(monkeypatch, tmp_path) -> None:
    client = TestClient(app)
    fake_s3 = FakeS3Client()
    local_index = LocalVectorIndex(tmp_path / "vector_index.json", dimensions=64)

    monkeypatch.setattr("app.main.s3_client", fake_s3)
    monkeypatch.setattr("app.main.vector_index", local_index)
    monkeypatch.setattr(rag_service, "vector_store", local_index)
    monkeypatch.setattr("app.main.settings.s3_bucket_name", "test-bucket")
    monkeypatch.setattr(
        "app.main.extract_chunks",
        lambda _: [
            {
                "chunk_id": 0,
                "page": 1,
                "text": "Los ingresos económicos aumentaron durante el ejercicio.",
            }
        ],
    )

    process_response = client.post(
        "/api/v1/documents/process",
        json={"key": "incoming/demo.pdf"},
    )

    assert process_response.status_code == 200
    assert process_response.json()["status"] == "processed"
    assert process_response.json()["indexed_chunks"] == 1
    assert "processed/demo.json" in fake_s3.saved_objects

    search_response = client.get(
        "/api/v1/rag/search",
        params={"query": "ingresos económicos", "limit": 5},
    )

    assert search_response.status_code == 200
    assert search_response.json()["results"][0]["source_key"] == "incoming/demo.pdf"

    chat_response = client.post(
        "/api/v1/chat",
        json={"message": "ingresos económicos"},
    )

    assert chat_response.status_code == 200
    assert chat_response.json()["route"] == "rag"
    assert chat_response.json()["sources"] == ["incoming/demo.pdf"]
