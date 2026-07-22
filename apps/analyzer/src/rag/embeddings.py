"""Titan Embeddings V2 client.

Generates 1024-dimensional embedding vectors via Amazon Bedrock's
Titan Embed Text V2 model. Implements the EmbeddingPort interface.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import boto3
from botocore.exceptions import ClientError

from src.config import get_settings
from src.domain.ports.embedding_port import EmbeddingPort

logger = logging.getLogger(__name__)

# Retry configuration
_MAX_RETRIES = 3
_BASE_DELAY = 1.0  # seconds


class TitanEmbeddingsClient(EmbeddingPort):
    """Amazon Titan Embeddings V2 client using boto3 bedrock-runtime.

    Produces 1024-dimensional vectors suitable for pgvector indexing.
    Uses asyncio.to_thread to avoid blocking the event loop with sync boto3 calls.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._model_id = settings.bedrock_titan_model_id
        self._client = boto3.client(
            "bedrock-runtime",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id or None,
            aws_secret_access_key=settings.aws_secret_access_key or None,
        )

    # ------------------------------------------------------------------ public API

    async def embed(self, text: str) -> list[float]:
        """Generate a single embedding vector for the given text.

        Implements EmbeddingPort.embed.

        Args:
            text: The input text to embed.

        Returns:
            A 1024-dimensional float vector.
        """
        return await self.generate_embedding(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a batch of texts.

        Implements EmbeddingPort.embed_batch.

        Args:
            texts: List of input texts to embed.

        Returns:
            List of 1024-dimensional float vectors (same order as input).
        """
        return await self.generate_batch(texts)

    async def generate_embedding(self, text: str) -> list[float]:
        """Generate a single 1024-dimensional embedding vector.

        Retries up to 3 times with exponential backoff on transient errors.

        Args:
            text: The input text to embed.

        Returns:
            A list of 1024 floats.

        Raises:
            RuntimeError: If all retry attempts are exhausted.
        """
        last_error: Exception | None = None

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                result = await asyncio.to_thread(self._invoke_model, text)
                return result
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "")
                last_error = e

                if error_code in ("ThrottlingException", "ServiceUnavailableException"):
                    delay = _BASE_DELAY * (2 ** (attempt - 1))
                    logger.warning(
                        "Bedrock throttle/unavailable (attempt %d/%d), "
                        "retrying in %.1fs: %s",
                        attempt,
                        _MAX_RETRIES,
                        delay,
                        error_code,
                    )
                    await asyncio.sleep(delay)
                else:
                    # Non-retryable error
                    raise RuntimeError(
                        f"Bedrock embedding failed: {e}"
                    ) from e
            except Exception as e:
                last_error = e
                delay = _BASE_DELAY * (2 ** (attempt - 1))
                logger.warning(
                    "Embedding generation error (attempt %d/%d), "
                    "retrying in %.1fs: %s",
                    attempt,
                    _MAX_RETRIES,
                    delay,
                    str(e),
                )
                await asyncio.sleep(delay)

        raise RuntimeError(
            f"Embedding generation failed after {_MAX_RETRIES} retries: {last_error}"
        )

    async def generate_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for multiple texts sequentially.

        Titan Embeddings V2 doesn't support batch requests natively,
        so we invoke the model sequentially for each text.

        Args:
            texts: List of texts to embed.

        Returns:
            List of embedding vectors in the same order as input.
        """
        embeddings: list[list[float]] = []
        for text in texts:
            embedding = await self.generate_embedding(text)
            embeddings.append(embedding)
        return embeddings

    # ------------------------------------------------------------------ internals

    def _invoke_model(self, text: str) -> list[float]:
        """Synchronous Bedrock model invocation (runs in thread).

        Args:
            text: Input text to embed.

        Returns:
            1024-dimensional embedding vector.
        """
        body = json.dumps({
            "inputText": text,
            "dimensions": 1024,
            "normalize": True,
        })

        response = self._client.invoke_model(
            modelId=self._model_id,
            contentType="application/json",
            accept="application/json",
            body=body,
        )

        response_body = json.loads(response["body"].read())
        embedding: list[float] = response_body["embedding"]
        return embedding
