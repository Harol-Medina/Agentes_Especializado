"""AWS Bedrock client adapter — Claude Sonnet invocation with retry + exponential backoff.

Implements requirement 6.1: LLM access for analysis agents via Amazon Bedrock.
Uses boto3 bedrock-runtime client with asyncio.to_thread for async compatibility.
Includes connect/read timeouts and asyncio.wait_for as safety net to prevent hangs.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional

import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError, ConnectTimeoutError, ReadTimeoutError

from src.config import get_settings

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES = 3
INITIAL_BACKOFF_SECONDS = 1.0


class BedrockInvocationError(Exception):
    """Raised when Bedrock invocation fails after all retries."""

    def __init__(self, message: str, original_error: Optional[Exception] = None) -> None:
        self.message = message
        self.original_error = original_error
        super().__init__(message)


class BedrockAdapter:
    """AWS Bedrock client for Claude Sonnet and Titan Embeddings invocations.

    Features:
    - Synchronous boto3 calls wrapped with asyncio.to_thread for async usage.
    - Retry with exponential backoff (1s, 2s, 4s) on throttling/transient errors.
    - Configurable model IDs via application settings.
    - Connect/read timeouts to fail fast on bad credentials or network issues.
    - asyncio.wait_for as final safety net against indefinite hangs.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._timeout_seconds = settings.bedrock_timeout_seconds
        boto_config = BotoConfig(
            connect_timeout=settings.bedrock_connect_timeout_seconds,
            read_timeout=settings.bedrock_timeout_seconds,
            retries={"max_attempts": 0},  # We handle retries ourselves
        )
        self._client = boto3.client(
            "bedrock-runtime",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id or None,
            aws_secret_access_key=settings.aws_secret_access_key or None,
            config=boto_config,
        )
        self._claude_model_id = settings.bedrock_claude_model_id
        self._titan_model_id = settings.bedrock_titan_model_id

    async def invoke_claude(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 4096,
    ) -> str:
        """Invoke Claude Sonnet via Bedrock with retry and exponential backoff.

        Args:
            system_prompt: System-level instructions for Claude.
            user_prompt: User message containing the analysis request.
            max_tokens: Maximum tokens in the response.

        Returns:
            The text content of Claude's response.

        Raises:
            BedrockInvocationError: If invocation fails after MAX_RETRIES attempts.
        """
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_prompt},
            ],
        })

        last_error: Optional[Exception] = None

        for attempt in range(MAX_RETRIES):
            try:
                response = await asyncio.wait_for(
                    asyncio.to_thread(
                        self._client.invoke_model,
                        modelId=self._claude_model_id,
                        contentType="application/json",
                        accept="application/json",
                        body=body,
                    ),
                    timeout=self._timeout_seconds,
                )

                response_body = json.loads(response["body"].read())
                # Extract text from Claude's response format
                content_blocks = response_body.get("content", [])
                text_parts = [
                    block["text"]
                    for block in content_blocks
                    if block.get("type") == "text"
                ]
                return "".join(text_parts)

            except asyncio.TimeoutError:
                last_error = TimeoutError(
                    f"Bedrock call timed out after {self._timeout_seconds}s"
                )
                logger.error(
                    "Bedrock call timed out (attempt %d/%d) — timeout=%ds",
                    attempt + 1,
                    MAX_RETRIES,
                    self._timeout_seconds,
                )
                # Timeout is not retryable — fail immediately
                raise BedrockInvocationError(
                    f"Bedrock call timed out after {self._timeout_seconds}s. "
                    "Check AWS credentials and network connectivity.",
                    original_error=last_error,
                ) from last_error

            except (ConnectTimeoutError, ReadTimeoutError) as exc:
                last_error = exc
                logger.error(
                    "Bedrock connection/read timeout (attempt %d/%d): %s",
                    attempt + 1,
                    MAX_RETRIES,
                    str(exc),
                )
                # Connection timeouts usually mean bad credentials or no network
                raise BedrockInvocationError(
                    f"Bedrock connection failed: {exc}. "
                    "Check AWS credentials and network connectivity.",
                    original_error=exc,
                ) from exc

            except ClientError as exc:
                error_code = exc.response.get("Error", {}).get("Code", "")
                last_error = exc

                # Retry on throttling and transient errors
                if error_code in (
                    "ThrottlingException",
                    "ServiceUnavailableException",
                    "ModelTimeoutException",
                ):
                    backoff = INITIAL_BACKOFF_SECONDS * (2**attempt)
                    logger.warning(
                        "Bedrock throttled/transient error (attempt %d/%d) — "
                        "retrying in %.1fs. error_code=%s",
                        attempt + 1,
                        MAX_RETRIES,
                        backoff,
                        error_code,
                    )
                    await asyncio.sleep(backoff)
                    continue

                # Non-retryable error
                raise BedrockInvocationError(
                    f"Bedrock invocation failed: {error_code} — {exc}",
                    original_error=exc,
                ) from exc

            except Exception as exc:
                last_error = exc
                backoff = INITIAL_BACKOFF_SECONDS * (2**attempt)
                logger.warning(
                    "Unexpected error invoking Bedrock (attempt %d/%d) — "
                    "retrying in %.1fs. error=%s",
                    attempt + 1,
                    MAX_RETRIES,
                    backoff,
                    str(exc),
                )
                await asyncio.sleep(backoff)

        raise BedrockInvocationError(
            f"Bedrock invocation failed after {MAX_RETRIES} retries",
            original_error=last_error,
        )
