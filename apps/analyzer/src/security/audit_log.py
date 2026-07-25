"""Security audit logging for flagged or blocked requests.

Logs all security-relevant events (blocked prompts, rate limit hits,
guardrail interventions) to a structured format for investigation.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger("security.audit")


class SecurityEvent(str, Enum):
    """Types of security events to audit."""

    PROMPT_BLOCKED = "prompt_blocked"
    PROMPT_SUSPICIOUS = "prompt_suspicious"
    RATE_LIMITED = "rate_limited"
    GUARDRAIL_BLOCKED_INPUT = "guardrail_blocked_input"
    GUARDRAIL_BLOCKED_OUTPUT = "guardrail_blocked_output"
    PII_DETECTED = "pii_detected"
    CREDENTIAL_LEAK_PREVENTED = "credential_leak_prevented"


def log_security_event(
    event: SecurityEvent,
    *,
    client_ip: str = "unknown",
    prompt_preview: str = "",
    matched_patterns: list[str] | None = None,
    threat_level: str = "",
    guardrail_reason: str = "",
    additional_context: dict | None = None,
) -> None:
    """Log a security event in structured JSON format.

    Args:
        event: The type of security event.
        client_ip: Source IP address (first 3 octets only for privacy).
        prompt_preview: First 100 chars of the prompt (truncated for privacy).
        matched_patterns: List of pattern names that triggered the event.
        threat_level: Severity level from PromptGuard.
        guardrail_reason: Reason from Bedrock Guardrail if applicable.
        additional_context: Extra metadata.
    """
    # Privacy: mask last octet of IP
    masked_ip = _mask_ip(client_ip)

    # Privacy: truncate prompt to first 100 chars
    safe_preview = prompt_preview[:100] + "..." if len(prompt_preview) > 100 else prompt_preview

    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event.value,
        "client_ip": masked_ip,
        "prompt_preview": safe_preview,
        "matched_patterns": matched_patterns or [],
        "threat_level": threat_level,
        "guardrail_reason": guardrail_reason,
        **(additional_context or {}),
    }

    # Use WARNING for suspicious, ERROR for blocked
    if event in (
        SecurityEvent.PROMPT_BLOCKED,
        SecurityEvent.GUARDRAIL_BLOCKED_INPUT,
        SecurityEvent.GUARDRAIL_BLOCKED_OUTPUT,
        SecurityEvent.CREDENTIAL_LEAK_PREVENTED,
    ):
        logger.error("SECURITY_EVENT: %s", json.dumps(log_entry))
    else:
        logger.warning("SECURITY_EVENT: %s", json.dumps(log_entry))


def _mask_ip(ip: str) -> str:
    """Mask the last octet of an IPv4 address for privacy."""
    parts = ip.split(".")
    if len(parts) == 4:
        return f"{parts[0]}.{parts[1]}.{parts[2]}.***"
    return ip[:10] + "***"
