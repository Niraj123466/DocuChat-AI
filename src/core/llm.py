"""LLM Provider abstraction layer, fallback cascade, and token budgeting."""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import List, Tuple, Optional, Any

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger("llm_provider")

class TokenBudgetManager:
    """Manages token budgeting and truncates context to avoid context window overflows."""

    CHARS_PER_TOKEN = 4  # Standard empirical ratio for English text

    @classmethod
    def estimate_tokens(cls, text: str) -> int:
        """Estimates token count from character length."""
        return max(1, len(text) // cls.CHARS_PER_TOKEN)

    @classmethod
    def truncate_to_budget(cls, text: str, max_tokens: int = 3000) -> str:
        """Trims text to fit within max token budget, breaking at sentence/paragraph boundaries."""
        max_chars = max_tokens * cls.CHARS_PER_TOKEN
        if len(text) <= max_chars:
            return text

        logger.warning(f"Context exceeds {max_tokens} tokens ({len(text)} chars). Truncating context.")
        trimmed = text[:max_chars]
        last_break = max(trimmed.rfind("\n\n"), trimmed.rfind(". "), trimmed.rfind("\n"))
        if last_break > max_chars * 0.7:
            trimmed = trimmed[:last_break]
        return trimmed + "\n... [Context truncated for token budget]"


class BaseLLMProvider(ABC):
    """Abstract interface for LLM model providers."""

    @abstractmethod
    def generate(
        self,
        messages: List[Tuple[str, str]],
        temperature: float = 0.1,
        max_tokens: Optional[int] = None
    ) -> str:
        """Generates a text completion from a list of (role, content) tuples."""
        pass


class GoogleGeminiProvider(BaseLLMProvider):
    """Google Gemini LLM provider with fallback models and retry handling."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "gemini-2.5-flash-lite",
        fallback_model: str = "gemini-flash-lite-latest",
        max_retries: int = 2
    ) -> None:
        self.api_key = api_key or settings.GOOGLE_API_KEY
        self.model_name = model_name
        self.fallback_model = fallback_model
        self.max_retries = max_retries
        self._llm = None

    def _init_llm(self, model: str):
        from langchain_google_genai import ChatGoogleGenerativeAI
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY is not configured.")
        return ChatGoogleGenerativeAI(
            model=model,
            temperature=0.1,
            google_api_key=self.api_key,
            max_retries=0,
        )

    def generate(
        self,
        messages: List[Tuple[str, str]],
        temperature: float = 0.1,
        max_tokens: Optional[int] = None
    ) -> str:
        models_to_try = [
            self.model_name,
            self.fallback_model,
            "gemini-2.5-flash-lite",
            "gemini-flash-lite-latest",
            "gemini-3.6-flash",
            "gemini-flash-latest",
            "gemini-3-flash-preview",
            "gemini-3.1-flash-lite-preview",
        ]
        # Deduplicate while preserving order
        unique_models = []
        for m in models_to_try:
            if m and m not in unique_models:
                unique_models.append(m)

        for model in unique_models:
            for attempt in range(self.max_retries + 1):
                try:
                    logger.info(f"Invoking {model} (Attempt {attempt + 1})")
                    llm = self._init_llm(model)
                    response = llm.invoke(messages)
                    raw_content = getattr(response, "content", response)
                    if isinstance(raw_content, list):
                        text = "".join(
                            part.get("text", str(part)) if isinstance(part, dict) else getattr(part, "text", str(part))
                            for part in raw_content
                        )
                    else:
                        text = str(raw_content)
                    return text.strip()
                except Exception as e:
                    err_msg = str(e)
                    logger.warning(f"Error calling {model} on attempt {attempt + 1}: {err_msg}")
                    # If 429 quota exhausted or rate-limited, immediately failover to next model
                    if "429" in err_msg or "RESOURCE_EXHAUSTED" in err_msg or "quota" in err_msg.lower():
                        logger.info(f"Rate limit / quota reached for {model}. Immediately failing over to next model.")
                        break
                    if attempt < self.max_retries:
                        time.sleep(1.0 * (2 ** attempt))  # Exponential backoff
                    else:
                        logger.error(f"Exhausted retries for {model}. Failing over to next provider.")
                        break

        raise RuntimeError(f"All Google Gemini models failed after retries.")


class MockLLMProvider(BaseLLMProvider):
    """Mock LLM provider for unit tests, offline execution, and regression benchmarks."""

    def __init__(self, predefined_response: Optional[str] = None) -> None:
        self.predefined_response = predefined_response

    def generate(
        self,
        messages: List[Tuple[str, str]],
        temperature: float = 0.1,
        max_tokens: Optional[int] = None
    ) -> str:
        if self.predefined_response:
            return self.predefined_response

        # Extract human question from messages
        human_msg = ""
        for role, content in messages:
            if role == "human":
                human_msg = content
                break

        return f"Based on the provided documents [Doc 1], here is the verified answer regarding: {human_msg[:40]}."


class FallbackLLMProvider(BaseLLMProvider):
    """Composite provider that tries primary provider and falls back gracefully to secondary."""

    def __init__(self, primary: BaseLLMProvider, fallback: BaseLLMProvider) -> None:
        self.primary = primary
        self.fallback = fallback

    def generate(
        self,
        messages: List[Tuple[str, str]],
        temperature: float = 0.1,
        max_tokens: Optional[int] = None
    ) -> str:
        try:
            return self.primary.generate(messages, temperature, max_tokens)
        except Exception as e:
            logger.warning(f"Primary LLM provider failed: {e}. Executing fallback provider.")
            return self.fallback.generate(messages, temperature, max_tokens)
