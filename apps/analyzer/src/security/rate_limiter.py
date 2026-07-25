"""In-memory rate limiter for the RAG query endpoint.

Limits requests per IP/session to prevent abuse and cost overruns.
Uses a sliding window approach with configurable window size and max requests.
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""

    allowed: bool
    remaining: int
    reset_in_seconds: float
    reason: str = ""


class RateLimiter:
    """Sliding window rate limiter.

    Tracks request timestamps per key (IP or session) and rejects
    requests that exceed the configured limit within the window.
    """

    def __init__(
        self,
        max_requests: int = 20,
        window_seconds: float = 60.0,
    ) -> None:
        """
        Args:
            max_requests: Maximum requests allowed per window.
            window_seconds: Size of the sliding window in seconds.
        """
        self._max_requests = max_requests
        self._window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def check(self, key: str) -> RateLimitResult:
        """Check if a request from the given key is allowed.

        Args:
            key: Unique identifier (IP address, session ID, etc.)

        Returns:
            RateLimitResult indicating if the request is allowed.
        """
        now = time.time()
        window_start = now - self._window_seconds

        # Clean old entries
        self._requests[key] = [
            ts for ts in self._requests[key] if ts > window_start
        ]

        current_count = len(self._requests[key])

        if current_count >= self._max_requests:
            # Calculate when the oldest request in window expires
            oldest = self._requests[key][0] if self._requests[key] else now
            reset_in = (oldest + self._window_seconds) - now

            logger.warning(
                "Rate limit exceeded — key=%s, count=%d, max=%d",
                key[:20],
                current_count,
                self._max_requests,
            )

            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_in_seconds=max(0, reset_in),
                reason=f"Rate limit exceeded: {self._max_requests} requests per {self._window_seconds}s",
            )

        # Record this request
        self._requests[key].append(now)

        return RateLimitResult(
            allowed=True,
            remaining=self._max_requests - current_count - 1,
            reset_in_seconds=self._window_seconds,
        )

    def cleanup(self) -> None:
        """Remove expired entries to prevent memory growth."""
        now = time.time()
        window_start = now - self._window_seconds
        expired_keys = []

        for key, timestamps in self._requests.items():
            self._requests[key] = [ts for ts in timestamps if ts > window_start]
            if not self._requests[key]:
                expired_keys.append(key)

        for key in expired_keys:
            del self._requests[key]


# Singleton instances for different endpoints
query_rate_limiter = RateLimiter(max_requests=20, window_seconds=60.0)
analyze_rate_limiter = RateLimiter(max_requests=3, window_seconds=300.0)
