"""Security audit logging — structured log events for security-relevant actions."""

from __future__ import annotations

import logging
from enum import Enum

logger = logging.getLogger("security.audit")


class SecurityEvent(str, Enum):
    RATE_LIMITED = "rate_limited"
    PROMPT_BLOCKED = "prompt_blocked"
    PROMPT_SUSPICIOUS = "prompt_suspicious"
    GUARDRAIL_BLOCKED_INPUT = "guardrail_blocked_input"
    GUARDRAIL_BLOCKED_OUTPUT = "guardrail_blocked_output"


def log_security_event(event: SecurityEvent, **kwargs) -> None:
    """Log a security event with structured context."""
    logger.warning(
        "Security event: %s | %s",
        event.value,
        " | ".join(f"{k}={v}" for k, v in kwargs.items()),
    )
