from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    frontend_origin: str = "http://localhost:5173"
    s3_bucket_name: str = ""
    aws_region: str = "eu-west-1"
    embedding_dimensions: int = 64
    local_index_path: Path = ROOT_DIR / "backend" / "data" / "vector_index.json"

    model_config = SettingsConfigDict(
        env_file=ROOT_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
