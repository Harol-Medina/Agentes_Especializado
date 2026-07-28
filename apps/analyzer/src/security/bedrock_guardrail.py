"""Bedrock Guardrail integration — content filtering stub.

In production, this would call the Bedrock ApplyGuardrail API.
For MVP, we pass through all content (guardrail validation is optional).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class GuardrailResult:
    blocked: bool = False
    reason: str | None = None
    output_text: str = ""


class BedrockGuardrail:
    """Validates input/output via AWS Bedrock Guardrails.

    MVP implementation: passthrough (no blocking).
    To enable real guardrails, configure BEDROCK_GUARDRAIL_ID in .env.
    """

    async def validate_input(self, text: str) -> GuardrailResult:
        """Validate user input. Returns passthrough for MVP."""
        return GuardrailResult(blocked=False, output_text=text)

    async def validate_output(self, text: str) -> GuardrailResult:
        """Validate generated output. Returns passthrough for MVP."""
        return GuardrailResult(blocked=False, output_text=text)
