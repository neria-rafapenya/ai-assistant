from app.providers.bedrock import BedrockChatProvider


class FakeBedrockClient:
    def __init__(self) -> None:
        self.calls = []

    def converse(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "output": {
                "message": {
                    "content": [{"text": "  respuesta de Bedrock  "}],
                }
            }
        }


def test_bedrock_provider_uses_converse_without_aws_call() -> None:
    client = FakeBedrockClient()
    provider = BedrockChatProvider(
        region="eu-west-1",
        model_id="amazon.nova-lite-v1:0",
        max_tokens=128,
        temperature=0.1,
        client=client,
    )

    result = provider.generate_reply("hola")

    assert result.reply == "respuesta de Bedrock"
    assert result.provider == "bedrock"
    assert client.calls == [
        {
            "modelId": "amazon.nova-lite-v1:0",
            "messages": [
                {"role": "user", "content": [{"text": "hola"}]},
            ],
            "inferenceConfig": {"maxTokens": 128, "temperature": 0.1},
        }
    ]
