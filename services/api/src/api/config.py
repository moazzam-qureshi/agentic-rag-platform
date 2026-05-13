"""API service configuration loaded from environment variables."""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_env_file() -> str:
    """Find .env file, preferring project root over service dir."""
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

    # === Service ===
    service_name: str = "docuai-api"
    log_level: str = "INFO"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000

    # === Persistence ===
    database_url: str = "postgresql+asyncpg://docuai:docuai@localhost:5432/docuai"

    # === Queue / cache ===
    redis_url: str = "redis://localhost:6379/0"

    # === Hybrid search ===
    opensearch_host: str = "localhost"
    opensearch_port: int = 9200
    opensearch_index: str = "documents"

    # === LLMs ===
    # OpenAI for chat/translation
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"

    # OpenRouter for vision-LLM page extraction
    openrouter_api_key: str = ""
    openrouter_model: str = "qwen/qwen2.5-vl-72b-instruct"

    # === Guardrails ===
    # Trusted reverse-proxy networks (Coolify/Traefik). Comma-separated CIDRs.
    # Without this, X-Forwarded-For is ignored (anti-spoof default).
    trusted_proxies: str = "127.0.0.1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"

    # Per-IP rate limits (chat endpoints).
    rate_limit_per_hour: int = 30
    rate_limit_per_day: int = 100

    # Per-IP daily upload ceiling.
    upload_max_per_ip_per_day: int = 3
    upload_max_pages_per_doc: int = 20

    # Worker concurrency cap (max simultaneous VLM jobs across the cluster).
    worker_max_concurrency: int = 2

    # Cloudflare Turnstile (required on /upload).
    turnstile_secret: str = ""
    turnstile_sitekey: str = ""

    # Auto-delete uploaded docs older than N hours.
    document_ttl_hours: int = 24

    # LLM call cap (tokens) — hard ceiling on max_tokens unless overridden.
    llm_max_tokens_default: int = 1024


settings = Settings()
