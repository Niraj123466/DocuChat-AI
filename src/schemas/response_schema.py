"""TypedDict schema for LangGraph workflow state."""
from __future__ import annotations

from typing import TypedDict, Literal, Optional, List, Dict, Any

class ResponseSchema(TypedDict, total=False):
    user_query: str
    query_response: str
    evaluation_state: Literal["True", "False", ""]
    retry_count: int
    instruction: str
    citations: List[Dict[str, Any]]
    user_id: Optional[str]
    knowledge_base_id: Optional[str]