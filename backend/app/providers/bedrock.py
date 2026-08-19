from typing import Any

import boto3
from botocore.config import Config
from pydantic import BaseModel


class BedrockChatResponse(BaseModel):
    reply: str
    provider: str = "bedrock"


class BedrockChatProvider:
    provider_name = "bedrock"

    def __init__(
        self,
        region: str,
        model_id: str,
        max_tokens: int = 512,
        temperature: float = 0.2,
        client: Any | None = None,
    ) -> None:
        self.model_id = model_id
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.client = client or boto3.client(
            "bedrock-runtime",
            region_name=region,
            config=Config(
                read_timeout=120,
                retries={"max_attempts": 2},
            ),
        )

    def generate_reply(self, message: str) -> BedrockChatResponse:
        if not self.model_id:
            raise RuntimeError("BEDROCK_MODEL_ID is not configured")

        response = self.client.converse(
            modelId=self.model_id,
            messages=[
                {
                    "role": "user",
                    "content": [{"text": message}],
                }
            ],
            inferenceConfig={
                "maxTokens": self.max_tokens,
                "temperature": self.temperature,
            },
        )

        content = response.get("output", {}).get("message", {}).get("content", [])
        reply = next(
            (block["text"] for block in content if block.get("text")),
            None,
        )
        if not reply:
            raise RuntimeError("Bedrock returned an empty response")

        return BedrockChatResponse(reply=reply.strip())
