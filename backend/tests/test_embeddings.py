import json

from app.embeddings import BedrockEmbeddingProvider


class FakeEmbeddingBody:
    def read(self):
        return json.dumps({"embedding": [0.1, 0.2, 0.3, 0.4]}).encode()


class FakeEmbeddingClient:
    def __init__(self):
        self.calls = []

    def invoke_model(self, **kwargs):
        self.calls.append(kwargs)
        return {"body": FakeEmbeddingBody()}


def test_bedrock_embedding_provider_uses_titan_v2() -> None:
    client = FakeEmbeddingClient()
    provider = BedrockEmbeddingProvider(
        region="eu-west-1",
        model_id="amazon.titan-embed-text-v2:0",
        dimensions=4,
        client=client,
    )

    embedding = provider.embed("texto de prueba")

    assert embedding == [0.1, 0.2, 0.3, 0.4]
    assert client.calls[0]["modelId"] == "amazon.titan-embed-text-v2:0"
    assert json.loads(client.calls[0]["body"]) == {
        "inputText": "texto de prueba",
        "dimensions": 4,
        "normalize": True,
    }
