"""Worker service configuration."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_env_file() -> str:
    if Path(".env").exists():
        return ".env"
    for path in [Path("../../.env"), Path("../../../.env")]:
        if path.exists():
            return str(path)
    return ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_find_env_file(),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    service_name: str = "docuai-worker"
    log_level: str = "INFO"

    # Persistence (worker uses sync psycopg2 for Dramatiq actor bodies)
    database_url: str = "postgresql://docuai:docuai@localhost:5432/docuai"

    # Queue
    redis_url: str = "redis://localhost:6379/0"

    # Search
    opensearch_host: str = "localhost"
    opensearch_port: int = 9200
    opensearch_index: str = "documents"

    # Vision-LLM ingestion
    openrouter_api_key: str = ""
    openrouter_model: str = "qwen/qwen2.5-vl-72b-instruct"

    # Concurrency cap (matches dramatiq actor `max_concurrency`)
    max_concurrency: int = 2


settings = Settings()
