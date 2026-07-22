"""Abstract embedding generation port."""

from abc import ABC, abstractmethod


class EmbeddingPort(ABC):
    """Defines the contract for generating vector embeddings from text."""

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """
        Generate an embedding vector for *text*.

        Returns:
            A list of floats representing the embedding (1024 dimensions
            for Titan Embeddings V2).
        """
        ...

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embedding vectors for a batch of texts.

        Returns:
            A list of embedding vectors in the same order as *texts*.
        """
        ...
