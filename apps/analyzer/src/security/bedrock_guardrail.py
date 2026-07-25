"""AWS Bedrock Guardrail integration for content filtering.

Uses the Bedrock ApplyGuardrail API to validate both input prompts
and model outputs against the configured guardrail (ArchaeologistContentFilter).

The guardrail filters:
- Sexual, violent, hate, misconduct content
- Prompt injection attacks (PROMPT_ATTACK filter)
- Denied topics: weapons, malware, illegal activity, personal data
- PII: anonymizes emails/phones/names, blocks SSN/credit cards/AWS keys
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from src.config import get_settings

logger = logging.getLogger(__name__)

# Guardrail configuration
GUARDRAIL_ID = "dmqbd98c0qg6"
GUARDRAIL_VERSION = "1"


class GuardrailAction(str, Enum):
    """Possible guardrail outcomes."""

    ALLOWED = "NONE"
    BLOCKED = "GUARDRAIL_INTERVENED"


@dataclass
class GuardrailResult:
    """Result of applying a Bedrock guardrail."""

    action: GuardrailAction
    blocked: bool
    output_text: str = ""
    assessments: list[dict] = field(default_factory=list)
    reason: str = ""


class BedrockGuardrail:
    """Applies AWS Bedrock Guardrail to validate content.

    Validates user input before sending to Claude and optionally
    validates model output before returning to user.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._client = boto3.client(
            "bedrock-runtime",
            region_name=settings.aws_region,
            aws_access_key_id=settings.aws_access_key_id or None,
            aws_secret_access_key=settings.aws_secret_access_key or None,
        )
        self._guardrail_id = GUARDRAIL_ID
        self._guardrail_version = GUARDRAIL_VERSION

    async def validate_input(self, text: str) -> GuardrailResult:
        """Validate user input against the guardrail.

        Args:
            text: The user's raw input text.

        Returns:
            GuardrailResult indicating if the input is allowed or blocked.
        """
        return await self._apply_guardrail(text, source="INPUT")

    async def validate_output(self, text: str) -> GuardrailResult:
        """Validate model output before returning to user.

        Args:
            text: The model's generated response.

        Returns:
            GuardrailResult indicating if the output is safe to return.
        """
        return await self._apply_guardrail(text, source="OUTPUT")

    async def _apply_guardrail(self, text: str, source: str) -> GuardrailResult:
        """Call the Bedrock ApplyGuardrail API.

        Args:
            text: Content to validate.
            source: "INPUT" or "OUTPUT".

        Returns:
            GuardrailResult with the guardrail's decision.
        """
        try:
            response = await asyncio.to_thread(
                self._client.apply_guardrail,
                guardrailIdentifier=self._guardrail_id,
                guardrailVersion=self._guardrail_version,
                source=source,
                content=[{"text": {"text": text}}],
            )

            action_str = response.get("action", "NONE")
            action = GuardrailAction(action_str)
            blocked = action == GuardrailAction.BLOCKED

            # Extract output text (original or replacement)
            outputs = response.get("outputs", [])
            output_text = text
            if blocked and outputs:
                output_text = outputs[0].get("text", "")

            # Extract assessment details for logging
            assessments = response.get("assessments", [])

            reason = ""
            if blocked:
                reason = self._extract_block_reason(assessments)
                logger.warning(
                    "Bedrock guardrail BLOCKED content — source=%s, reason=%s",
                    source,
                    reason,
                )

            return GuardrailResult(
                action=action,
                blocked=blocked,
                output_text=output_text,
                assessments=assessments,
                reason=reason,
            )

        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "")
            logger.error(
                "Bedrock guardrail API error — code=%s, error=%s",
                error_code,
                str(exc),
            )
            # Fail open for API errors (don't block legitimate requests
            # due to guardrail service issues) but log for investigation
            return GuardrailResult(
                action=GuardrailAction.ALLOWED,
                blocked=False,
                output_text=text,
                reason=f"Guardrail API error: {error_code} (fail-open)",
            )

        except Exception as exc:
            logger.error("Unexpected guardrail error: %s", str(exc))
            return GuardrailResult(
                action=GuardrailAction.ALLOWED,
                blocked=False,
                output_text=text,
                reason=f"Unexpected error: {str(exc)} (fail-open)",
            )

    def _extract_block_reason(self, assessments: list[dict]) -> str:
        """Extract a human-readable reason from guardrail assessments."""
        reasons: list[str] = []

        for assessment in assessments:
            # Topic policy
            topic_policy = assessment.get("topicPolicy", {})
            for topic in topic_policy.get("topics", []):
                if topic.get("action") == "BLOCKED":
                    reasons.append(f"topic:{topic.get('name', 'unknown')}")

            # Content policy
            content_policy = assessment.get("contentPolicy", {})
            for filter_result in content_policy.get("filters", []):
                if filter_result.get("action") == "BLOCKED":
                    reasons.append(
                        f"content:{filter_result.get('type', 'unknown')}"
                    )

            # Sensitive info policy
            sensitive_policy = assessment.get("sensitiveInformationPolicy", {})
            for pii in sensitive_policy.get("piiEntities", []):
                if pii.get("action") == "BLOCKED":
                    reasons.append(f"pii:{pii.get('type', 'unknown')}")

        return "; ".join(reasons) if reasons else "content_policy_violation"
