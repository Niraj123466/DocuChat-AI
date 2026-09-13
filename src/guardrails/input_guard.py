"""Input Guardrail: Prompt Injection & Adversarial Attack Detector."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, List, Pattern

from src.core.logging import get_logger

logger = get_logger("input_guard")

@dataclass
class InjectionScanResult:
    """Outcome of scanning user input for prompt injection and adversarial patterns."""
    is_safe: bool
    sanitized_text: str
    risk_score: float = 0.0
    violation_reason: Optional[str] = None


class InputGuard:
    """Proactive input sanitization and prompt injection defense."""

    MAX_INPUT_LENGTH = 4000  # Guard against token exhaustion DoS

    # Adversarial patterns & jailbreaks compiled for speed
    INJECTION_PATTERNS: List[Pattern] = [
        re.compile(r"ignore\s+(all\s+)?(previous|above|prior)\s+(instructions|directives|rules)", re.IGNORECASE),
        re.compile(r"disregard\s+(all\s+)?(previous|above|prior)\s+(instructions|directives)", re.IGNORECASE),
        re.compile(r"(system\s+prompt|system\s+instructions?)\s*(reveal|show|print|display|leak|output)", re.IGNORECASE),
        re.compile(r"(reveal|show|print|display|leak|dump)\s+(your\s+)?(system\s+prompt|instructions|directives)", re.IGNORECASE),
        re.compile(r"you\s+are\s+now\s+(in\s+)?(dan\s+mode|developer\s+mode|jailbroken|unrestricted)", re.IGNORECASE),
        re.compile(r"(act|roleplay)\s+as\s+(an?\s+)?(unrestricted|evil|unfiltered|jailbroken)\s+(ai|assistant)", re.IGNORECASE),
        re.compile(r"<\s*\|\s*im_start\s*\|\s*>|\[\s*system\s*\]|---\s*begin\s+system", re.IGNORECASE),
        re.compile(r"(bypass|override)\s+(all\s+)?(safety|content|ethical)\s+(filters?|guidelines?|rules?)", re.IGNORECASE),
        re.compile(r"repeat\s+everything\s+(above|before)", re.IGNORECASE),
    ]

    @classmethod
    def sanitize(cls, text: str) -> str:
        """Removes null bytes and control characters while normalizing whitespace."""
        if not text:
            return ""
        # Remove null characters and non-printable control chars (except standard \n, \t, \r)
        cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
        return cleaned.strip()

    @classmethod
    def scan(cls, user_text: str) -> InjectionScanResult:
        """Evaluates text against length limits and prompt injection attack patterns."""
        if not user_text or not user_text.strip():
            return InjectionScanResult(
                is_safe=False,
                sanitized_text="",
                risk_score=1.0,
                violation_reason="Input query cannot be empty."
            )

        sanitized = cls.sanitize(user_text)

        # 1. Length validation (DoS protection)
        if len(sanitized) > cls.MAX_INPUT_LENGTH:
            logger.warning(f"Input exceeds maximum length: {len(sanitized)} > {cls.MAX_INPUT_LENGTH}")
            return InjectionScanResult(
                is_safe=False,
                sanitized_text=sanitized[:cls.MAX_INPUT_LENGTH],
                risk_score=0.8,
                violation_reason=f"Input length exceeds safe threshold of {cls.MAX_INPUT_LENGTH} characters."
            )

        # 2. Prompt injection pattern scanning
        for pattern in cls.INJECTION_PATTERNS:
            match = pattern.search(sanitized)
            if match:
                matched_phrase = match.group(0)
                logger.warning(f"Prompt injection pattern detected: '{matched_phrase}'")
                return InjectionScanResult(
                    is_safe=False,
                    sanitized_text=sanitized,
                    risk_score=0.95,
                    violation_reason=f"Query violates AI safety policies (Adversarial pattern: '{matched_phrase}')."
                )

        # Input is verified safe
        return InjectionScanResult(
            is_safe=True,
            sanitized_text=sanitized,
            risk_score=0.0,
            violation_reason=None
        )
