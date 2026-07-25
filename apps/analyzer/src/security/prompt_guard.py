"""Prompt injection detection and input sanitization.

Detects common prompt injection patterns including:
- Instruction override attempts ("ignore previous instructions")
- Role manipulation ("you are now a...")
- System prompt extraction ("repeat your system prompt")
- Encoding obfuscation (base64, hex, unicode tricks)
- Delimiter injection (closing/opening XML, markdown fences)
- Jailbreak patterns (DAN, developer mode, etc.)

Returns a threat assessment with severity and matched patterns.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class ThreatLevel(str, Enum):
    """Severity of detected prompt injection attempt."""

    NONE = "none"
    LOW = "low"          # Suspicious but possibly benign
    MEDIUM = "medium"    # Likely injection attempt
    HIGH = "high"        # Definite injection / policy violation
    CRITICAL = "critical"  # Attempting to extract secrets or bypass safety


@dataclass
class ThreatAssessment:
    """Result of prompt injection analysis."""

    level: ThreatLevel
    blocked: bool
    matched_patterns: list[str] = field(default_factory=list)
    sanitized_input: str = ""
    reason: str = ""


# ──────────────────────────────────────────────────────────────────────────────
# Pattern definitions (compiled for performance)
# ──────────────────────────────────────────────────────────────────────────────

_CRITICAL_PATTERNS: list[tuple[re.Pattern, str]] = [
    # System prompt extraction
    (re.compile(r"(repeat|show|print|display|reveal|output)\s*(your|the|my)?\s*(system|initial|original|hidden)\s*(prompt|instructions|message|context)", re.IGNORECASE), "system_prompt_extraction"),
    # Secret/credential extraction
    (re.compile(r"(show|reveal|print|output|give)\s*(me)?\s*(the|your)?\s*(api|aws|secret|access)\s*(key|token|credential|password)", re.IGNORECASE), "credential_extraction"),
    # Direct policy bypass
    (re.compile(r"(ignore|disregard|forget|override|bypass)\s*(all|any|previous|prior|above|the)?\s*(instructions|rules|constraints|guidelines|safety|filters|restrictions)", re.IGNORECASE), "instruction_override"),
]

_HIGH_PATTERNS: list[tuple[re.Pattern, str]] = [
    # Jailbreak personas
    (re.compile(r"\b(DAN|Do Anything Now|Developer Mode|STAN|DUDE|AIM)\b", re.IGNORECASE), "jailbreak_persona"),
    # Role reassignment
    (re.compile(r"(you are now|act as|pretend to be|roleplay as|simulate being)\s*(a|an)?\s*(unrestricted|unfiltered|evil|malicious|hacker)", re.IGNORECASE), "malicious_role_assignment"),
    # Harmful content generation
    (re.compile(r"(write|generate|create|produce|give me)\s*(a|an|the)?\s*(malware|exploit|virus|ransomware|trojan|keylogger|backdoor|phishing)", re.IGNORECASE), "malware_generation"),
    # Weapons / harmful substances
    (re.compile(r"(how to|instructions for|steps to|guide to)\s*(make|build|create|synthesize|produce)\s*(a|an)?\s*(bomb|weapon|explosive|poison|drug|meth)", re.IGNORECASE), "weapons_instructions"),
    # CSAM-related
    (re.compile(r"(child|minor|underage|young)\s*(porn|sexual|nude|naked|explicit)", re.IGNORECASE), "csam_attempt"),
    # Encoding evasion with harmful intent
    (re.compile(r"(decode|execute|eval|run)\s*(this|the following)?\s*(base64|hex|rot13|unicode)", re.IGNORECASE), "encoding_evasion"),
]

_MEDIUM_PATTERNS: list[tuple[re.Pattern, str]] = [
    # Generic instruction manipulation
    (re.compile(r"(new instructions|from now on|starting now|henceforth)\s*:?\s*(you|I|we)", re.IGNORECASE), "instruction_manipulation"),
    # Delimiter injection
    (re.compile(r"(</?(system|user|assistant|instructions|context|prompt)>)", re.IGNORECASE), "delimiter_injection"),
    # Hypothetical framing for bypass
    (re.compile(r"(hypothetically|in theory|for (educational|research|academic) purposes|if you were not restricted)", re.IGNORECASE), "hypothetical_bypass"),
    # Multi-step manipulation
    (re.compile(r"(step 1|first|before answering).*?(ignore|forget|disregard)", re.IGNORECASE | re.DOTALL), "multi_step_manipulation"),
    # Token smuggling
    (re.compile(r"[\u200b\u200c\u200d\u2060\ufeff]", re.UNICODE), "invisible_characters"),
]

_LOW_PATTERNS: list[tuple[re.Pattern, str]] = [
    # Curiosity about system internals (not necessarily malicious)
    (re.compile(r"(what|which)\s*(model|AI|LLM|system)\s*(are you|is this|am I talking to)", re.IGNORECASE), "system_identification"),
    # Excessive repetition (potential token flooding)
    (re.compile(r"(.{5,})\1{10,}", re.DOTALL), "repetition_flooding"),
]

# Topics explicitly out of scope for a code analysis tool
_OFF_TOPIC_HARMFUL: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\b(suicide|self.?harm|kill\s*(my|your)self)\b", re.IGNORECASE), "self_harm_content"),
    (re.compile(r"\b(hack|ddos|dos\s*attack|brute.?force)\s*(this|that|a|their|the)\s*(server|website|account|system)\b", re.IGNORECASE), "attack_planning"),
]


class PromptGuard:
    """Analyzes user prompts for injection attempts and policy violations.

    Usage:
        guard = PromptGuard()
        assessment = guard.analyze("user input here")
        if assessment.blocked:
            # reject the request
    """

    def __init__(
        self,
        max_prompt_length: int = 5000,
        block_on_level: ThreatLevel = ThreatLevel.HIGH,
    ) -> None:
        """
        Args:
            max_prompt_length: Maximum allowed characters in a prompt.
            block_on_level: Minimum threat level that triggers blocking.
        """
        self._max_length = max_prompt_length
        self._block_threshold = block_on_level
        self._severity_order = [
            ThreatLevel.NONE,
            ThreatLevel.LOW,
            ThreatLevel.MEDIUM,
            ThreatLevel.HIGH,
            ThreatLevel.CRITICAL,
        ]

    def analyze(self, prompt: str) -> ThreatAssessment:
        """Analyze a prompt for injection patterns and policy violations.

        Args:
            prompt: The raw user input to analyze.

        Returns:
            ThreatAssessment with severity level, matched patterns, and block decision.
        """
        if not prompt or not prompt.strip():
            return ThreatAssessment(
                level=ThreatLevel.NONE,
                blocked=False,
                sanitized_input="",
                reason="Empty input",
            )

        matched: list[str] = []
        max_level = ThreatLevel.NONE

        # Length check
        if len(prompt) > self._max_length:
            matched.append("exceeds_max_length")
            max_level = self._max_level(max_level, ThreatLevel.MEDIUM)

        # Check patterns in severity order (most severe first)
        for pattern, name in _CRITICAL_PATTERNS:
            if pattern.search(prompt):
                matched.append(name)
                max_level = self._max_level(max_level, ThreatLevel.CRITICAL)

        for pattern, name in _HIGH_PATTERNS:
            if pattern.search(prompt):
                matched.append(name)
                max_level = self._max_level(max_level, ThreatLevel.HIGH)

        for pattern, name in _MEDIUM_PATTERNS:
            if pattern.search(prompt):
                matched.append(name)
                max_level = self._max_level(max_level, ThreatLevel.MEDIUM)

        for pattern, name in _LOW_PATTERNS:
            if pattern.search(prompt):
                matched.append(name)
                max_level = self._max_level(max_level, ThreatLevel.LOW)

        # Off-topic harmful content
        for pattern, name in _OFF_TOPIC_HARMFUL:
            if pattern.search(prompt):
                matched.append(name)
                max_level = self._max_level(max_level, ThreatLevel.HIGH)

        # Determine if blocked
        blocked = self._severity_order.index(max_level) >= self._severity_order.index(self._block_threshold)

        # Sanitize: truncate to max length, strip invisible characters
        sanitized = self._sanitize(prompt)

        reason = ""
        if blocked:
            reason = f"Blocked: detected {', '.join(matched[:3])}"
        elif matched:
            reason = f"Suspicious patterns detected but below blocking threshold: {', '.join(matched[:3])}"

        return ThreatAssessment(
            level=max_level,
            blocked=blocked,
            matched_patterns=matched,
            sanitized_input=sanitized,
            reason=reason,
        )

    def _sanitize(self, prompt: str) -> str:
        """Remove invisible characters and truncate to max length."""
        # Remove zero-width characters and other invisible unicode
        cleaned = re.sub(r"[\u200b\u200c\u200d\u2060\ufeff]", "", prompt)
        # Normalize whitespace
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        # Truncate
        if len(cleaned) > self._max_length:
            cleaned = cleaned[: self._max_length]
        return cleaned

    def _max_level(self, current: ThreatLevel, new: ThreatLevel) -> ThreatLevel:
        """Return the higher severity level."""
        if self._severity_order.index(new) > self._severity_order.index(current):
            return new
        return current
