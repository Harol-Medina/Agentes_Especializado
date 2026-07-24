"""HTTP webhook sender adapter — HMAC-SHA256 signed POST to Backend.

Notifies the Backend when the analysis pipeline completes (fully or partially).
Implements:
- HMAC-SHA256 signature in X-Webhook-Signature header.
- Retry 3× with exponential backoff (1s, 2s, 4s) on failure.
- Non-fatal: logs error if all retries fail (the job is still recorded as complete).

Implements task 4.8 webhook requirements.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Retry configuration
MAX_RETRIES: int = 3
RETRY_DELAYS: tuple[float, ...] = (1.0, 2.0, 4.0)  # seconds between attempts
REQUEST_TIMEOUT_SECONDS: float = 10.0


class WebhookAdapter:
    """Sends HMAC-signed webhook notifications to the Backend service."""

    def __init__(self, webhook_url: str, webhook_secret: str) -> None:
        """
        Args:
            webhook_url: Full URL of the Backend webhook endpoint.
            webhook_secret: Shared secret for HMAC-SHA256 signing.
        """
        self._webhook_url = webhook_url
        self._webhook_secret = webhook_secret

    def _sign_payload(self, payload_bytes: bytes) -> str:
        """Compute HMAC-SHA256 hex digest for the given payload bytes.

        Uses hmac.new(key, msg, digestmod) from the standard library.
        The signature is sent as ``sha256={hex_digest}`` in X-Webhook-Signature.
        """
        return hmac.HMAC(
            key=self._webhook_secret.encode("utf-8"),
            msg=payload_bytes,
            digestmod=hashlib.sha256,
        ).hexdigest()

    async def notify_completion(self, payload: dict[str, Any]) -> None:
        """Send the completion webhook to the Backend.

        Signs the JSON payload with HMAC-SHA256 and POSTs to the configured
        webhook URL. Retries up to 3 times with exponential backoff (1s, 2s, 4s).

        Args:
            payload: Dict with keys jobId, status, projectId, agentsStatus.

        Non-fatal: If all retries fail, logs error but does NOT raise.
        """
        payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        signature = self._sign_payload(payload_bytes)

        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": f"sha256={signature}",
        }

        for attempt in range(MAX_RETRIES):
            try:
                async with httpx.AsyncClient(
                    timeout=REQUEST_TIMEOUT_SECONDS
                ) as client:
                    response = await client.post(
                        self._webhook_url,
                        content=payload_bytes,
                        headers=headers,
                    )
                    response.raise_for_status()

                logger.info(
                    "Webhook delivered — url=%s, status_code=%d, attempt=%d/%d",
                    self._webhook_url,
                    response.status_code,
                    attempt + 1,
                    MAX_RETRIES,
                )
                return

            except (httpx.HTTPStatusError, httpx.RequestError) as exc:
                logger.warning(
                    "Webhook attempt %d/%d failed — url=%s, error=%s",
                    attempt + 1,
                    MAX_RETRIES,
                    self._webhook_url,
                    str(exc),
                )

                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAYS[attempt])

        # All retries exhausted — non-fatal, log and return
        logger.error(
            "Webhook delivery failed after %d attempts — url=%s, payload_job_id=%s. "
            "The job is still recorded as complete; Backend will pick up status via polling.",
            MAX_RETRIES,
            self._webhook_url,
            payload.get("jobId"),
        )
