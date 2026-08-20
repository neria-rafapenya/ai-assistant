from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    frontend_origin: str = "http://localhost:5173"
    cognito_issuer: str = (
        "https://cognito-idp.eu-west-1.amazonaws.com/eu-west-1_5fX8JYeKk"
    )
    cognito_client_id: str = "4086ign9h6tpj0r5o1mhhab74n"
    s3_bucket_name: str = ""
    aws_region: str = "eu-west-1"
    ai_provider: str = "simulated"
    bedrock_model_id: str = ""
    bedrock_max_tokens: int = 512
    bedrock_temperature: float = 0.2
    embedding_provider: str = "simulated"
    bedrock_embedding_model_id: str = "amazon.titan-embed-text-v2:0"
    vector_store_backend: str = "local"
    opensearch_endpoint: str = ""
    opensearch_index: str = "ai-assistant-documents"
    opensearch_service: str = "aoss"
    embedding_dimensions: int = 64
    persistence_backend: str = "sqlite"
    dynamodb_documents_table_name: str = "ai-assistant-documents-dev"
    dynamodb_conversations_table_name: str = "ai-assistant-conversations-dev"
    dynamodb_profiles_table_name: str = "ai-assistant-profiles-dev"
    local_index_path: Path = ROOT_DIR / "backend" / "data" / "vector_index.json"
    chat_database_path: Path = ROOT_DIR / "backend" / "data" / "chat.db"

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
