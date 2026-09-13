"""Retriever & Generation Agent node in the LangGraph workflow."""
from __future__ import annotations

import re
from typing import Optional

from src.schemas.response_schema import ResponseSchema
from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger("retriever_agent")

_query_agent = None

def _get_query_agent():
    global _query_agent
    if _query_agent is None:
        from src.agents.query_agent import create_query_agent
        _query_agent = create_query_agent(api_key=settings.GOOGLE_API_KEY)
    return _query_agent

def clean_llm_response(raw_text: str) -> str:
    """Extracts cleanly formatted text from raw LLM output or ValidationOutcome wrappers."""
    if not raw_text:
        return ""

    if "ValidationOutcome" in raw_text:
        # Extract validated_output if wrapped by Guardrails
        match = re.search(r'validated_output="((?:[^"\\]|\\.)*)"', raw_text)
        if match:
            return match.group(1).replace('\\n', '\n').replace('\\"', '"').strip()
        fallback_match = re.search(r"validated_output='([^']*)'[, ]", raw_text)
        if fallback_match:
            return fallback_match.group(1).replace('\\n', '\n').replace('\\"', '"').replace("\\'", "'").strip()

    return raw_text.strip()

def retriver_agent(state: ResponseSchema) -> ResponseSchema:
    user_query = state.get("user_query", "")
    instruction = state.get("instruction", "")
    current_retries = state.get("retry_count", 0)
    user_id = state.get("user_id")
    kb_id = state.get("knowledge_base_id")

    logger.info(f"Retriever node executing (Query: '{user_query[:50]}...', User: {user_id}, Retry: {current_retries})")

    modified_input = f"{user_query}\n\nSystem Directive:\n{instruction}" if instruction else user_query

    try:
        agent = _get_query_agent()
        result = agent.invoke({
            "input": modified_input,
            "user_id": user_id,
            "knowledge_base_id": kb_id
        })
        raw_output = result.get("output", "")
        response_str = clean_llm_response(raw_output)
        citations = result.get("citations", [])
    except Exception as e:
        logger.error(f"Error during query agent invocation: {e}", exc_info=True)
        response_str = f"Error processing query: {str(e)}"
        citations = []

    return {
        "user_query": user_query,
        "query_response": response_str,
        "evaluation_state": "",
        "retry_count": current_retries + 1,
        "instruction": instruction,
        "citations": citations,
        "user_id": user_id,
        "knowledge_base_id": kb_id,
    }
