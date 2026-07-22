"""Adapters package — external service integrations."""

from src.adapters.bedrock_adapter import BedrockAdapter
from src.adapters.postgres_adapter import PostgresAdapter

__all__ = [
    "BedrockAdapter",
    "PostgresAdapter",
]
