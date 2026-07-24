"""Application configuration via pydantic-settings.

All values can be overridden by environment variables (case-insensitive).
The .data/.env file is the canonical source of truth; Docker Compose injects
it at container startup via ``env_file: .data/.env``.
"""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration for the Analyzer service."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ----------------------------------------------------------------- database
    database_url: str  # asyncpg connection string, e.g. postgresql+asyncpg://...

    # ----------------------------------------------------------------- services
    backend_url: str = "http://backend:8080"

    # ----------------------------------------------------------------- security
    webhook_secret: str  # HMAC-SHA256 signing secret shared with Backend

    # ----------------------------------------------------------------- AWS
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"

    # ----------------------------------------------------------------- Bedrock
    bedrock_claude_model_id: str = Field(
        default="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
        validation_alias="bedrock_model_id",
    )
    bedrock_titan_model_id: str = Field(
        default="amazon.titan-embed-text-v2:0",
        validation_alias="bedrock_embedding_model_id",
    )

    # ----------------------------------------------------------------- limits
    max_repo_size_bytes: int = 524_288_000  # 500 MB
    max_file_count: int = 50_000

    # ----------------------------------------------------------------- storage
    temp_repo_dir: str = "/tmp/repos"

    # ----------------------------------------------------------------- logging
    log_level: str = "INFO"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the (cached) singleton Settings instance."""
    return Settings()
