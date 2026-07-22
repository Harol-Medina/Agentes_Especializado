"""pgvector embedding indexer.

Handles bulk insertion of code chunk embeddings into the code_embeddings
table via asyncpg and pgvector.
"""

from __future__ import annotations

import json
import logging
from uuid import UUID, uuid4

import numpy as np

from src.adapters.postgres_adapter import PostgresAdapter
from src.parsing.chunker import CodeChunk

logger = logging.getLogger(__name__)


class EmbeddingIndexer:
    """Indexes code chunk embeddings into PostgreSQL using pgvector.

    Bulk inserts chunks and their corresponding embedding vectors into
    the code_embeddings table for later semantic retrieval.
    """

    def __init__(self, postgres: PostgresAdapter) -> None:
        """Initialize with a PostgresAdapter instance.

        Args:
            postgres: A connected PostgresAdapter for database operations.
        """
        self._postgres = postgres

    async def index_chunks(
        self,
        project_id: UUID,
        chunks: list[CodeChunk],
        embeddings: list[list[float]],
    ) -> int:
        """Bulk INSERT code chunks with their embeddings into code_embeddings.

        Args:
            project_id: The project these chunks belong to.
            chunks: List of CodeChunk objects to index.
            embeddings: List of embedding vectors (1024-dim), same order as chunks.

        Returns:
            Number of rows inserted.

        Raises:
            ValueError: If chunks and embeddings have different lengths.
            RuntimeError: If the database insert fails.
        """
        if len(chunks) != len(embeddings):
            raise ValueError(
                f"Mismatch: {len(chunks)} chunks vs {len(embeddings)} embeddings"
            )

        if not chunks:
            logger.info("No chunks to index for project %s", project_id)
            return 0

        # Prepare rows for bulk insert
        rows = []
        for chunk, embedding in zip(chunks, embeddings):
            row = (
                uuid4(),                        # id
                project_id,                     # project_id
                chunk.text,                     # chunk_text
                chunk.chunk_type,               # chunk_type
                chunk.file_path,                # file_path
                chunk.module_name,              # module_name
                chunk.function_name,            # function_name
                np.array(embedding),            # embedding vector(1024)
                json.dumps(chunk.metadata),     # metadata jsonb
            )
            rows.append(row)

        # Bulk INSERT statement
        query = """
            INSERT INTO code_embeddings (
                id, project_id, chunk_text, chunk_type,
                file_path, module_name, function_name,
                embedding, metadata
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb)
        """

        try:
            await self._postgres.execute_many(query, rows)
            logger.info(
                "Indexed %d chunks for project %s", len(rows), project_id
            )
            return len(rows)
        except Exception as e:
            logger.error(
                "Failed to index chunks for project %s: %s", project_id, e
            )
            raise RuntimeError(
                f"Embedding indexing failed for project {project_id}: {e}"
            ) from e
