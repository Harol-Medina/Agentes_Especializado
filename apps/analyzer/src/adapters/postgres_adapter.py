"""asyncpg + pgvector PostgreSQL adapter.

Provides connection pooling and bulk operations for the Analyzer service.
Uses pgvector extension for vector similarity search.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Sequence

import asyncpg
from pgvector.asyncpg import register_vector

from src.config import get_settings

logger = logging.getLogger(__name__)


class PostgresAdapter:
    """Async PostgreSQL adapter with pgvector support via asyncpg."""

    def __init__(self, database_url: str | None = None) -> None:
        """Initialize adapter with optional database_url override.

        If not provided, reads from application settings.
        """
        self._database_url = database_url or get_settings().database_url
        self._pool: asyncpg.Pool | None = None

    # ------------------------------------------------------------------ lifecycle

    async def connect(self) -> None:
        """Create the connection pool and register pgvector codec.

        Must be called before any database operations.
        """
        # asyncpg expects a plain postgresql:// DSN (not postgresql+asyncpg://)
        dsn = self._database_url.replace("postgresql+asyncpg://", "postgresql://")

        self._pool = await asyncpg.create_pool(
            dsn=dsn,
            min_size=2,
            max_size=10,
            command_timeout=60,
            init=self._init_connection,
        )
        logger.info("PostgresAdapter: connection pool created (min=2, max=10)")

    async def close(self) -> None:
        """Gracefully close the connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            logger.info("PostgresAdapter: connection pool closed")

    # ------------------------------------------------------------------ queries

    async def fetch(self, query: str, *args: Any) -> list[asyncpg.Record]:
        """Execute a query and return all rows.

        Args:
            query: SQL query with $1, $2, ... placeholders.
            *args: Positional parameters for the query.

        Returns:
            List of asyncpg.Record objects.
        """
        self._ensure_connected()
        async with self._pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def fetch_one(self, query: str, *args: Any) -> asyncpg.Record | None:
        """Execute a query and return a single row or None.

        Args:
            query: SQL query with $1, $2, ... placeholders.
            *args: Positional parameters for the query.

        Returns:
            A single asyncpg.Record or None.
        """
        self._ensure_connected()
        async with self._pool.acquire() as conn:
            return await conn.fetchrow(query, *args)

    async def execute(self, query: str, *args: Any) -> str:
        """Execute a single statement (INSERT, UPDATE, DELETE).

        Args:
            query: SQL statement with $1, $2, ... placeholders.
            *args: Positional parameters for the statement.

        Returns:
            Command tag string (e.g. 'INSERT 0 1').
        """
        self._ensure_connected()
        async with self._pool.acquire() as conn:
            return await conn.execute(query, *args)

    async def execute_many(self, query: str, args: Sequence[tuple]) -> None:
        """Execute a statement against a sequence of parameter tuples (bulk INSERT).

        Uses asyncpg's executemany for efficient batch operations.

        Args:
            query: SQL statement with $1, $2, ... placeholders.
            args: Sequence of tuples, each containing parameters for one execution.
        """
        self._ensure_connected()
        async with self._pool.acquire() as conn:
            await conn.executemany(query, args)

    # ------------------------------------------------------------------ internals

    @staticmethod
    async def _init_connection(conn: asyncpg.Connection) -> None:
        """Initialize each connection with pgvector codec."""
        await register_vector(conn)

    def _ensure_connected(self) -> None:
        """Raise if pool is not initialized."""
        if self._pool is None:
            raise RuntimeError(
                "PostgresAdapter is not connected. Call connect() first."
            )
