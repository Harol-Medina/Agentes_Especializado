"""RAG retriever — semantic search via pgvector cosine similarity.

Retrieves relevant code chunks from the code_embeddings table using
the cosine distance operator (<=>). Similarity is computed as 1 - distance.
Chunks below a minimum threshold are discarded.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from uuid import UUID

import numpy as np

from src.adapters.postgres_adapter import PostgresAdapter
from src.rag.embeddings import TitanEmbeddingsClient

logger = logging.getLogger(__name__)

# Minimum similarity score to consider a chunk relevant
_SIMILARITY_THRESHOLD = 0.05


@dataclass
class RetrievedChunk:
    """A code chunk retrieved via semantic search with its similarity score."""

    chunk_text: str
    chunk_type: str
    file_path: str
    module_name: str | None
    function_name: str | None
    similarity: float
    metadata: dict = field(default_factory=dict)


class RAGRetriever:
    """Retrieves relevant code chunks via pgvector cosine similarity.

    Uses Titan Embeddings V2 to embed the user question, then performs
    a nearest-neighbor query against the code_embeddings table.
    """

    def __init__(
        self,
        postgres: PostgresAdapter,
        embeddings: TitanEmbeddingsClient,
    ) -> None:
        """Initialize with database and embedding clients.

        Args:
            postgres: Connected PostgresAdapter for vector search queries.
            embeddings: TitanEmbeddingsClient for generating question embeddings.
        """
        self._postgres = postgres
        self._embeddings = embeddings

    async def retrieve(
        self,
        project_id: UUID,
        question: str,
        max_chunks: int = 10,
    ) -> list[RetrievedChunk]:
        """Retrieve relevant code chunks for a given question.

        1. Generate embedding for the question using TitanEmbeddingsClient.
        2. Query pgvector for nearest neighbors using cosine distance.
        3. Filter by minimum similarity threshold (0.3).
        4. Return RetrievedChunk objects with text, similarity, and metadata.

        Args:
            project_id: The project to search within.
            question: Natural language question to find relevant code for.
            max_chunks: Maximum number of chunks to return.

        Returns:
            List of RetrievedChunk objects sorted by similarity (descending).
        """
        # 1. Generate embedding for the question
        query_embedding = await self._embeddings.generate_embedding(question)

        # 2. Query pgvector — cosine distance operator <=> (lower = more similar)
        #    Similarity = 1 - cosine_distance
        query = """
            SELECT
                chunk_text,
                chunk_type,
                file_path,
                module_name,
                function_name,
                metadata,
                1 - (embedding <=> $1::vector) AS similarity
            FROM code_embeddings
            WHERE project_id = $2
            ORDER BY embedding <=> $1::vector
            LIMIT $3
        """

        query_vec = np.array(query_embedding)
        rows = await self._postgres.fetch(query, query_vec, project_id, max_chunks)

        # 3. Filter by minimum similarity threshold
        chunks: list[RetrievedChunk] = []
        for row in rows:
            similarity = float(row["similarity"])
            if similarity < _SIMILARITY_THRESHOLD:
                continue

            # Parse metadata — may be a dict already or a JSON string
            metadata = row["metadata"]
            if isinstance(metadata, str):
                import json
                metadata = json.loads(metadata)

            chunks.append(
                RetrievedChunk(
                    chunk_text=row["chunk_text"],
                    chunk_type=row["chunk_type"],
                    file_path=row["file_path"] or "",
                    module_name=row["module_name"],
                    function_name=row["function_name"],
                    similarity=similarity,
                    metadata=metadata if metadata else {},
                )
            )

        logger.info(
            "Retrieved %d chunks (of %d candidates) for project %s, question='%s...'",
            len(chunks),
            len(rows),
            project_id,
            question[:50],
        )

        return chunks
