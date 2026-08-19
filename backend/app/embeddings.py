import hashlib
import json
import math
import re
from typing import Any

import boto3
from botocore.config import Config


class SimulatedEmbeddingProvider:
    """Deterministic local embeddings used until Bedrock is connected."""

    def __init__(self, dimensions: int = 64) -> None:
        self.dimensions = dimensions

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = re.findall(r"[\wáéíóúüñ]+", text.lower())

        for token in tokens:
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]


class BedrockEmbeddingProvider:
    """Generates semantic vectors with Amazon Titan Text Embeddings V2."""

    def __init__(self, region: str, model_id: str, dimensions: int = 512, client: Any | None = None) -> None:
        self.model_id = model_id
        self.dimensions = dimensions
        self.client = client or boto3.client(
            "bedrock-runtime",
            region_name=region,
            config=Config(read_timeout=60, retries={"max_attempts": 2}),
        )

    def embed(self, text: str) -> list[float]:
        if not text.strip():
            raise ValueError("Embedding input text cannot be empty")

        response = self.client.invoke_model(
            modelId=self.model_id,
            body=json.dumps({
                "inputText": text,
                "dimensions": self.dimensions,
                "normalize": True,
            }),
            contentType="application/json",
            accept="application/json",
        )
        payload = json.loads(response["body"].read())
        embedding = payload.get("embedding")
        if not embedding:
            raise RuntimeError("Bedrock returned an empty embedding")
        if len(embedding) != self.dimensions:
            raise RuntimeError(
                f"Expected {self.dimensions} embedding values, got {len(embedding)}"
            )
        return embedding
