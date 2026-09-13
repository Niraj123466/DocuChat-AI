"""Output Guardrail: PII Scrubbing, Grounding Verification, and Safety Gate."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple, Any

from src.core.logging import get_logger

logger = get_logger("output_guard")

@dataclass
class OutputSafetyResult:
    """Outcome of validating and sanitizing LLM output."""
    is_safe: bool
    sanitized_output: str
    pii_redacted: bool = False
    grounding_score: float = 1.0
    critique: Optional[str] = None


class OutputGuard:
    """Evaluates model outputs for sensitive information disclosure and factual grounding."""

    # PII Regular Expressions
    EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
    PHONE_PATTERN = re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b")
    SSN_PATTERN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
    CREDIT_CARD_PATTERN = re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b")

    @classmethod
    def scrub_pii(cls, text: str) -> Tuple[str, bool]:
        """Detects and masks personally identifiable information (PII) from generated responses."""
        if not text:
            return "", False

        pii_found = False
        scrubbed = text

        if cls.EMAIL_PATTERN.search(scrubbed):
            scrubbed = cls.EMAIL_PATTERN.sub("[REDACTED_EMAIL]", scrubbed)
            pii_found = True

        if cls.PHONE_PATTERN.search(scrubbed):
            scrubbed = cls.PHONE_PATTERN.sub("[REDACTED_PHONE]", scrubbed)
            pii_found = True

        if cls.SSN_PATTERN.search(scrubbed):
            scrubbed = cls.SSN_PATTERN.sub("[REDACTED_SSN]", scrubbed)
            pii_found = True

        if cls.CREDIT_CARD_PATTERN.search(scrubbed):
            scrubbed = cls.CREDIT_CARD_PATTERN.sub("[REDACTED_CREDIT_CARD]", scrubbed)
            pii_found = True

        if pii_found:
            logger.warning("Sensitive PII detected and redacted from LLM response.")

        return scrubbed, pii_found

    @classmethod
    def verify_grounding(cls, answer: str, context: str) -> float:
        """Estimates factual grounding score based on content token coverage."""
        if not answer or not answer.strip():
            return 0.0

        if not context or "No relevant context" in context:
            # If no context exists and answer states limitation, grounding is valid
            if any(phrase in answer.lower() for phrase in ["cannot find", "not able to help", "apologize", "no verified"]):
                return 1.0
            return 0.5  # Unverified generation without context

        # Extract meaningful alphanumeric tokens
        ans_tokens = set(re.findall(r"\b[a-zA-Z]{3,}\b", answer.lower()))
        ctx_tokens = set(re.findall(r"\b[a-zA-Z]{3,}\b", context.lower()))

        if not ans_tokens:
            return 1.0

        supported = ans_tokens.intersection(ctx_tokens)
        score = len(supported) / len(ans_tokens)
        return min(1.0, float(score))

    @classmethod
    def process(cls, output_text: str, context_text: Optional[str] = None) -> OutputSafetyResult:
        """Runs full output safety pipeline: PII scrubbing + grounding assessment."""
        if not output_text:
            return OutputSafetyResult(is_safe=True, sanitized_output="")

        # 1. Scrub PII
        scrubbed, pii_found = cls.scrub_pii(output_text)

        # 2. Check grounding if context is provided
        grounding = 1.0
        if context_text:
            grounding = cls.verify_grounding(scrubbed, context_text)

        is_safe = True
        critique = None
        if grounding < 0.20 and len(scrubbed) > 100:
            logger.warning(f"Low grounding score detected: {grounding:.2f}")
            critique = "Potential hallucination: low vocabulary overlap with retrieved document chunks."

        return OutputSafetyResult(
            is_safe=is_safe,
            sanitized_output=scrubbed,
            pii_redacted=pii_found,
            grounding_score=round(grounding, 3),
            critique=critique
        )
