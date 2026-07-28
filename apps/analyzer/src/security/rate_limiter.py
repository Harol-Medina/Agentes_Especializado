"""Simple in-memory rate limiter for the query endpoint."""

from __future__ import annotations

import time
from dataclasses import dataclass


@dataclass
class RateResult:
    allowed: bool
    reset_in_seconds: float = 0.0
    remaining: int = 20


class RateLimiter:
    """Token-bucket rate limiter per client IP."""

    def __init__(self, max_requests: int = 20, window_seconds: int = 60) -> None:
        self._max = max_requests
        self._window = window_seconds
        self._requests: dict[str, list[float]] = {}

    def check(self, client_ip: str) -> RateResult:
        now = time.time()
        cutoff = now - self._window

        history = self._requests.get(client_ip, [])
        history = [t for t in history if t > cutoff]
        self._requests[client_ip] = history

        if len(history) >= self._max:
            oldest = history[0]
            return RateResult(
                allowed=False,
                reset_in_seconds=oldest + self._window - now,
                remaining=0,
            )

        history.append(now)
        return RateResult(allowed=True, remaining=self._max - len(history))


query_rate_limiter = RateLimiter(max_requests=20, window_seconds=60)
