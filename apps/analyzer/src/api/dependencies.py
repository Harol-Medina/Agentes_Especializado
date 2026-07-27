"""Dependency injection container for FastAPI route handlers.

Provides singleton instances of adapters (PostgresAdapter, BedrockAdapter)
via FastAPI's Depends() mechanism. Adapters are lazily initialized and
cached for the lifetime of the application.
"""

from __future__ import annotations

from functools import lru_cache
from typing import AsyncGenerator

from fastapi import Depends

from src.adapters.bedrock_adapter import BedrockAdapter
from src.adapters.postgres_adapter import PostgresAdapter
from src.config import Settings, get_settings


def get_config(settings: Settings = Depends(get_settings)) -> Settings:
    """Expose settings as a FastAPI dependency."""
    return settings


# ---------------------------------------------------------------------------
# Storage / DB dependency
# ---------------------------------------------------------------------------

_postgres: PostgresAdapter | None = None


async def get_postgres() -> AsyncGenerator[PostgresAdapter, None]:
    """Provide a connected PostgresAdapter instance.

    Lazily initializes and connects on first use. The pool is shared
    across all requests for the lifetime of the process.
    """
    global _postgres
    if _postgres is None:
        _postgres = PostgresAdapter()
        await _postgres.connect()
    yield _postgres


# ---------------------------------------------------------------------------
# Bedrock / LLM dependency
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_bedrock() -> BedrockAdapter:
    """Provide a singleton BedrockAdapter instance.

    The adapter is stateless (boto3 client is thread-safe) so a single
    instance is reused across all requests.
    """
    return BedrockAdapter()
