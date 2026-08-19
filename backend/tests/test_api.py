from fastapi.testclient import TestClient

from app.main import app


def test_health_check() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "aws_region": "eu-west-1"}


def test_chat_ok() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/chat",
        json={"message": "hola", "session_id": "sess-1"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["reply"] == "[simulado] Recibi: hola"
    assert payload["session_id"] == "sess-1"
    assert payload["provider"] == "simulated"


def test_chat_invalid_request() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/chat",
        json={"message": ""},
    )

    assert response.status_code == 422


def test_chat_provider_error(monkeypatch) -> None:
    client = TestClient(app)

    def raise_error(_: str):
        raise RuntimeError("boom")

    monkeypatch.setattr("app.main.chat_provider.generate_reply", raise_error)

    response = client.post(
        "/api/v1/chat",
        json={"message": "hola"},
    )

    assert response.status_code == 502
    assert response.json() == {"detail": "Provider error"}


def test_orchestrator_routes_to_general_without_relevant_sources(monkeypatch) -> None:
    client = TestClient(app)

    monkeypatch.setattr(
        "app.main.orchestrator.rag_service.retrieve",
        lambda query, limit=3: [],
    )

    response = client.post(
        "/api/v1/chat",
        json={"message": "hola"},
    )

    assert response.status_code == 200
    assert response.json()["route"] == "general"
    assert response.json()["sources"] == []
