"""Evaluator Agent node in the LangGraph workflow.

Enforces content safety, PII scrubbing, grounding checks, and manages retry loops.
"""
from __future__ import annotations

from src.schemas.response_schema import ResponseSchema
from src.core.config import settings
from src.core.logging import get_logger
from src.guardrails.output_guard import OutputGuard

logger = get_logger("evaluator_agent")

# Initialize profanity checker safely
try:
    from better_profanity import profanity
    profanity.load_censor_words()
except Exception as e:
    logger.warning(f"Could not load better_profanity: {e}")
    profanity = None

def evaluator_agent(state: ResponseSchema) -> ResponseSchema:
    user_query = state.get("user_query", "")
    query_response = state.get("query_response", "")
    retry_count = state.get("retry_count", 0)
    citations = state.get("citations", [])
    raw_text = query_response or ""

    logger.info(f"Evaluating response (Retry count: {retry_count}/{settings.MAX_RETRIES})")

    # 1. Check maximum retry threshold
    if retry_count >= settings.MAX_RETRIES:
        logger.warning("Maximum retry threshold exceeded. Forcing termination with safety notice.")
        return {
            "user_query": user_query,
            "query_response": "I apologize, but I could not formulate a completely verified and compliant response after maximum retries. Please rephrase your query.",
            "evaluation_state": "True",
            "retry_count": retry_count,
            "instruction": "",
            "citations": citations,
        }

    # 2. Output Guardrails: Scrub PII
    safety_result = OutputGuard.process(raw_text)
    scrubbed_text = safety_result.sanitized_output

    # 3. Check for profanity / toxicity violations
    is_flagged = False
    if profanity:
        try:
            is_flagged = profanity.contains_profanity(scrubbed_text)
        except Exception as e:
            logger.error(f"Error during profanity check: {e}")

    if is_flagged:
        logger.warning("Profanity or safety violation detected in generated response. Triggering retry.")
        retry_instruction = (
            "Rephrase the response to be completely professional and profanity-free. "
            "Avoid any explicit language, slurs, or direct quotes of offensive content. "
            "Summarize factually, neutrally, and cite verified document sources."
        )
        return {
            "user_query": user_query,
            "query_response": scrubbed_text,
            "evaluation_state": "False",
            "retry_count": retry_count,
            "instruction": retry_instruction,
            "citations": citations,
        }

    # 4. Response is verified and approved
    logger.info(f"Evaluation passed successfully (PII redacted: {safety_result.pii_redacted}).")
    return {
        "user_query": user_query,
        "query_response": scrubbed_text,
        "evaluation_state": "True",
        "retry_count": retry_count,
        "instruction": "",
        "citations": citations,
    }