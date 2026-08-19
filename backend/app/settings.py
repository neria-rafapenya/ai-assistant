from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    frontend_origin: str = "http://localhost:5173"
    s3_bucket_name: str = ""
    aws_region: str = "eu-west-1"
    ai_provider: str = "simulated"
    bedrock_model_id: str = ""
    bedrock_max_tokens: int = 512
    bedrock_temperature: float = 0.2
    vector_store_backend: str = "local"
    opensearch_endpoint: str = ""
    opensearch_index: str = "ai-assistant-documents"
    opensearch_service: str = "aoss"
    embedding_dimensions: int = 64
    local_index_path: Path = ROOT_DIR / "backend" / "data" / "vector_index.json"
    chat_database_path: Path = ROOT_DIR / "backend" / "data" / "chat.db"

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
