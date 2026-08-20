from fastapi.testclient import TestClient
from types import SimpleNamespace

from app.main import app


def test_health_check() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "aws_region": "eu-west-1"}


def test_chat_requires_authentication() -> None:
    app.dependency_overrides.clear()
    client = TestClient(app)

    response = client.post("/api/v1/chat", json={"message": "hola"})

    assert response.status_code == 401


def test_profile_requires_explicit_health_consent(monkeypatch) -> None:
    class InMemoryProfiles:
        def __init__(self):
            self.items = {}

        def get(self, user_id):
            return self.items.get(user_id)

        def save(self, user_id, profile):
            self.items[user_id] = profile
            return profile

    repository = InMemoryProfiles()
    monkeypatch.setattr("app.main.profile_repository", repository)
    client = TestClient(app)

    response = client.put(
        "/api/v1/profile",
        json={"health_conditions": "dato sensible"},
    )
    assert response.status_code == 422

    response = client.put(
        "/api/v1/profile",
        json={
            "date_of_birth": "1990-04-15",
            "profession": "Diseñador",
            "goals": ["crecimiento personal"],
            "health_conditions": "dato sensible",
            "health_data_consent": True,
        },
    )
    assert response.status_code == 200
    assert response.json()["zodiac_sign"] == "Aries"
    assert response.json()["age"] is not None


def test_tarot_read_builds_guided_interpretation(monkeypatch) -> None:
    client = TestClient(app)
    captured = {}

    def fake_generate(prompt, provider_name=None):
        captured["prompt"] = prompt
        return SimpleNamespace(reply="Lectura general\nUna perspectiva útil.", provider="simulated")

    monkeypatch.setattr("app.main.provider_manager.generate_reply", fake_generate)

    response = client.post(
        "/api/v1/tarot/read",
        json={
            "question": "¿Qué debería tener en cuenta en mi proyecto?",
            "spread": "three",
            "style": "reflexivo",
            "cards": [
                {"position": "situación", "name": "El Mago"},
                {"position": "perspectiva", "name": "La Luna"},
                {"position": "consejo", "name": "La Fuerza"},
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["provider"] == "simulated"
    assert "Cómo se relacionan" in captured["prompt"]


def test_tarot_read_rejects_wrong_spread_size() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/tarot/read",
        json={
            "question": "¿Qué debería observar?",
            "spread": "three",
            "cards": [{"position": "situación", "name": "El Mago"}],
        },
    )

    assert response.status_code == 422


def test_chat_ok(monkeypatch) -> None:
    client = TestClient(app)

    monkeypatch.setattr(
        "app.main.orchestrator.rag_service.retrieve",
        lambda query, limit=3: [],
    )

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


def test_chat_can_select_provider_for_single_request(monkeypatch) -> None:
    client = TestClient(app)

    monkeypatch.setattr(
        "app.main.orchestrator.handle",
        lambda message, provider_name=None: SimpleNamespace(
            reply=f"respuesta con {provider_name}",
            provider=provider_name,
            route="general",
            sources=[],
        ),
    )

    response = client.post(
        "/api/v1/chat",
        json={"message": "prueba controlada", "provider": "bedrock"},
    )

    assert response.status_code == 200
    assert response.json()["provider"] == "bedrock"


def test_chat_provider_error(monkeypatch) -> None:
    client = TestClient(app)

    monkeypatch.setattr(
        "app.main.orchestrator.rag_service.retrieve",
        lambda query, limit=3: [],
    )

    def raise_error(_: str):
        raise RuntimeError("boom")

    monkeypatch.setattr("app.main.chat_provider.generate_reply", raise_error)

    response = client.post(
        "/api/v1/chat",
        json={"message": "hola"},
    )

    assert response.status_code == 502
    assert response.json() == {"detail": "Provider error: boom"}


def test_chat_delegates_to_orchestrator(monkeypatch) -> None:
    client = TestClient(app)

    def fake_handle(message: str, provider_name=None):
        assert message == "consulta sobre documentos"
        assert provider_name is None
        return SimpleNamespace(
            reply="respuesta del orchestrator",
            provider="simulated",
            route="rag",
            sources=["incoming/documento.pdf"],
        )

    monkeypatch.setattr("app.main.orchestrator.handle", fake_handle)

    response = client.post(
        "/api/v1/chat",
        json={"message": "consulta sobre documentos"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["reply"] == "respuesta del orchestrator"
    assert payload["session_id"]
    assert payload["provider"] == "simulated"
    assert payload["route"] == "rag"
    assert payload["sources"] == ["incoming/documento.pdf"]


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
