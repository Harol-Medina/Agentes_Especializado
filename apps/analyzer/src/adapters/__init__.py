"""Adapters package — external service integrations."""

from src.adapters.bedrock_adapter import BedrockAdapter
from src.adapters.git_adapter import GitAdapter
from src.adapters.postgres_adapter import PostgresAdapter

__all__ = [
    "BedrockAdapter",
    "GitAdapter",
    "PostgresAdapter",
]
