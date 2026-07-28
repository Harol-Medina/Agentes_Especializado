"""Local prompt injection detection using regex patterns."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class ThreatLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class PromptAssessment:
    level: ThreatLevel = ThreatLevel.NONE
    blocked: bool = False
    matched_patterns: list[str] = field(default_factory=list)
    sanitized_input: str | None = None


# Patterns that indicate prompt injection attempts
_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"disregard\s+(all\s+)?above",
    r"you\s+are\s+now\s+a",
    r"act\s+as\s+if",
    r"system\s*:\s*",
    r"<\|?(system|im_start|im_end)\|?>",
]


class PromptGuard:
    """Detects prompt injection patterns in user input."""

    def __init__(
        self,
        max_prompt_length: int = 5000,
        block_on_level: ThreatLevel = ThreatLevel.HIGH,
    ) -> None:
        self._max_length = max_prompt_length
        self._block_level = block_on_level
        self._patterns = [re.compile(p, re.IGNORECASE) for p in _INJECTION_PATTERNS]

    def analyze(self, text: str) -> PromptAssessment:
        # Truncate if too long
        sanitized = text[: self._max_length]

        matched: list[str] = []
        for pattern in self._patterns:
            if pattern.search(sanitized):
                matched.append(pattern.pattern)

        if len(matched) >= 3:
            level = ThreatLevel.HIGH
        elif len(matched) >= 1:
            level = ThreatLevel.MEDIUM
        else:
            level = ThreatLevel.NONE

        blocked = level.value >= self._block_level.value and level != ThreatLevel.NONE

        return PromptAssessment(
            level=level,
            blocked=blocked,
            matched_patterns=matched,
            sanitized_input=sanitized,
        )
