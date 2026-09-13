"""Prompt Manager for loading and formatting prompt templates."""
from __future__ import annotations

from pathlib import Path
from typing import Dict, Any, Optional
import yaml

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger("prompt_manager")

DEFAULT_PROMPTS = {
    "query_agent_prompt": (
        "IDENTITY: You are a professional AI research assistant powered by {organization_name}.\n\n"
        "GROUNDING & CITATION RULES:\n"
        "1. Base your answers strictly and exclusively on the provided Context documents.\n"
        "2. For every factual claim, include an inline citation tag matching the source document, e.g. [Doc 1], [Doc 2].\n"
        "3. If the Context does not contain the answer, reply: 'I cannot find verified information regarding this in the uploaded documents.'\n"
        "4. Never hallucinate facts or extrapolate beyond what is stated in the documents.\n\n"
        "FEW-SHOT EXAMPLES:\n"
        "Example 1:\n"
        "Context: [Doc 1: Policy.pdf] Employees receive 20 days of paid annual leave.\n"
        "Question: How many vacation days do employees get?\n"
        "Answer: Employees are entitled to 20 days of paid annual leave [Doc 1].\n\n"
        "Example 2:\n"
        "Context: [Doc 1: Financials.pdf] Total revenue in Q3 reached $4.2M, driven by 30% growth in enterprise subscriptions.\n"
        "Question: What was the Q3 revenue?\n"
        "Answer: Q3 total revenue was $4.2M, propelled by a 30% increase in enterprise subscriptions [Doc 1].\n"
    ),
    "evaluator_agent_prompt": (
        "You are an AI Safety & Grounding Auditor.\n"
        "Assess whether the Answer is fully supported by the provided Context.\n"
        "Check for: 1. Hallucinations, 2. Missing citations, 3. Inaccuracies.\n"
    )
}

class PromptManager:
    """Manages prompt loading, templating, and versioning."""

    def __init__(self, prompt_file: Optional[Path] = None) -> None:
        self.prompt_file = prompt_file or (settings.BASE_DIR / "src" / "utils" / "prompts.yml")
        self._prompts: Dict[str, str] = {}
        self._load_prompts()

    def _load_prompts(self) -> None:
        if self.prompt_file.exists():
            try:
                with open(self.prompt_file, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if isinstance(data, dict):
                        self._prompts = data
                        logger.info(f"Loaded {len(self._prompts)} prompts from {self.prompt_file.name}")
                        return
            except Exception as e:
                logger.warning(f"Failed to parse {self.prompt_file}: {e}. Using default prompts.")

        self._prompts = DEFAULT_PROMPTS.copy()

    def get_prompt(self, prompt_name: str, **kwargs: Any) -> str:
        """Retrieves and formats a named prompt template."""
        template = self._prompts.get(prompt_name) or DEFAULT_PROMPTS.get(prompt_name, "")
        if not template:
            raise KeyError(f"Prompt '{prompt_name}' not found.")
        try:
            return template.format(**kwargs)
        except KeyError as ke:
            logger.warning(f"Missing parameter {ke} when formatting prompt '{prompt_name}'")
            return template

# Global singleton
prompt_manager = PromptManager()
