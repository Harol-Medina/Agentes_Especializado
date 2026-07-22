"""Dependency injection container for FastAPI route handlers.

Each ``Depends(...)`` call resolves a concrete adapter implementation
bound to the configured ports.  Placeholder implementations are used
in tasks 4.1–4.2; real adapters are wired in later tasks.
"""

from functools import lru_cache

from fastapi import Depends

from src.config import Settings, get_settings


def get_config(settings: Settings = Depends(get_settings)) -> Settings:
    """Expose settings as a FastAPI dependency."""
    return settings


# ---------------------------------------------------------------------------
# Storage / DB dependency (placeholder — wired in task 7.1)
# ---------------------------------------------------------------------------

# from src.adapters.postgres_adapter import PostgresAdapter
#
# @lru_cache(maxsize=1)
# def get_storage() -> PostgresAdapter:
#     settings = get_settings()
#     return PostgresAdapter(dsn=settings.database_url)


# ---------------------------------------------------------------------------
# Bedrock / LLM dependency (placeholder — wired in task 6.1)
# ---------------------------------------------------------------------------

# from src.adapters.bedrock_adapter import BedrockAdapter
#
# @lru_cache(maxsize=1)
# def get_llm() -> BedrockAdapter:
#     settings = get_settings()
#     return BedrockAdapter(settings=settings)
