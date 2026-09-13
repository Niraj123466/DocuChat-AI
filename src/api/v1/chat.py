"""Chat API endpoints for RAG-augmented query processing with guardrails, caching, and citations."""
from __future__ import annotations

import time
from typing import Optional, Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.Workflow.workflow import workflow
from src.agents.retriver_agent import clean_llm_response
from src.guardrails.input_guard import InputGuard
from src.api.dependencies import check_rate_limit, get_current_user
from src.cache.cache_manager import cache_manager
from src.core.telemetry import metrics, trace_span
from src.core.logging import get_logger
from src.db.session import get_db
from src.services.chat_service import ChatService

logger = get_logger("chat_api")

router = APIRouter(prefix="/chat", tags=["Chat"])

class ChatRequest(BaseModel):
    user_message: Optional[str] = Field(None, description="User query text")
    message: Optional[str] = Field(None, description="Alternative user query field")
    conversation_id: Optional[str] = Field(None, description="Optional conversation thread ID to append turns to")

    def get_query(self) -> str:
        q = (self.user_message or self.message or "").strip()
        if not q:
            raise ValueError("Query message cannot be empty.")
        return q

class CitationItem(BaseModel):
    doc_index: int = Field(..., description="Document marker index [Doc X]")
    source: str = Field(..., description="Source document name")
    chunk_id: str = Field(..., description="Chunk identifier")
    relevance_score: float = Field(..., description="Semantic cross-encoder relevance score")
    text_snippet: str = Field(..., description="Snippet of the referenced context")
    page_number: Optional[int] = Field(None, description="Document page number if available")

class ChatResponse(BaseModel):
    response: str
    retry_count: int = 0
    evaluation_passed: bool = True
    citations: List[CitationItem] = Field(default_factory=list, description="Grounding source citations")
    conversation_id: Optional[str] = Field(None, description="Thread ID if persisted")
    metadata: Dict[str, Any] = Field(default_factory=dict)

async def _persist_turns_if_needed(
    db: AsyncSession,
    conversation_id: Optional[str],
    user_id: str,
    query: str,
    response: str,
    citations: List[Dict[str, Any]],
    metadata: Dict[str, Any]
) -> Optional[str]:
    try:
        if not conversation_id:
            conv = await ChatService.create_conversation(db, title=query[:50], user_id=user_id)
            conversation_id = conv.id
        else:
            conv = await ChatService.get_conversation(db, conversation_id, user_id=user_id)
            if not conv:
                conv = await ChatService.create_conversation(db, title=query[:50], user_id=user_id)
                conversation_id = conv.id

        await ChatService.record_message(db, conversation_id=conversation_id, sender="user", content=query, user_id=user_id)
        await ChatService.record_message(
            db,
            conversation_id=conversation_id,
            sender="assistant",
            content=response,
            citations=citations,
            metadata=metadata,
            user_id=user_id
        )
        return conversation_id
    except Exception as e:
        logger.warning(f"Could not persist conversation thread [{conversation_id}]: {e}")
        return conversation_id

@router.post("", response_model=ChatResponse, dependencies=[Depends(check_rate_limit)])
@router.post("/", response_model=ChatResponse, dependencies=[Depends(check_rate_limit)])
async def chat_endpoint(
    request: ChatRequest,
    current_user: Dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Processes user query through AI guardrails, cache layer, and LangGraph workflow with strict tenant isolation."""
    try:
        query_text = request.get_query()
    except ValueError as val_err:
        raise HTTPException(status_code=422, detail=str(val_err))

    user_id = current_user["id"]
    user_label = current_user["email"]

    # Strict ownership check: prevent IDOR access to conversations
    if request.conversation_id:
        existing_conv = await ChatService.get_conversation(db, request.conversation_id, user_id=user_id)
        if not existing_conv:
            raise HTTPException(status_code=404, detail="Conversation not found")

    # 1. Input Guardrail: Prompt Injection & Adversarial Attack Defense
    scan_result = InputGuard.scan(query_text)
    if not scan_result.is_safe:
        logger.warning(f"Blocked malicious or invalid query: {scan_result.violation_reason}")
        raise HTTPException(
            status_code=400,
            detail={
                "error": "AI Safety Policy Violation",
                "reason": scan_result.violation_reason,
                "risk_score": scan_result.risk_score
            }
        )

    clean_query = scan_result.sanitized_text

    # 2. Performance Cache: Exact Query Match Check (scoped to tenant)
    tenant_cache_key = f"usr_{user_id}:{clean_query}"
    cached_data = cache_manager.get_query(tenant_cache_key)
    if cached_data:
        metrics.inc_counter("docuchat_cache_hits_total")
        logger.info(f"Returning cached answer for user [{user_label}] query: '{clean_query[:50]}...'")
        cached_citations = [CitationItem(**c) for c in cached_data.get("citations", [])]
        saved_conv_id = await _persist_turns_if_needed(
            db=db,
            conversation_id=request.conversation_id,
            user_id=user_id,
            query=clean_query,
            response=cached_data["response"],
            citations=cached_data.get("citations", []),
            metadata={"cache_hit": True}
        )
        return ChatResponse(
            response=cached_data["response"],
            retry_count=cached_data.get("retry_count", 0),
            evaluation_passed=cached_data.get("evaluation_passed", True),
            citations=cached_citations,
            conversation_id=saved_conv_id,
            metadata={
                "cache_hit": True,
                "cached_at": cached_data.get("timestamp"),
                "user": user_label,
            }
        )

    metrics.inc_counter("docuchat_cache_misses_total")
    logger.info(f"Incoming chat request from user [{user_label}]: '{clean_query[:60]}...'")

    initial_state = {
        "user_query": clean_query,
        "query_response": "",
        "evaluation_state": "",
        "retry_count": 0,
        "instruction": "",
        "user_id": user_id,
    }

    start_llm_time = time.perf_counter()
    with trace_span("LangGraph RAG Workflow", attributes={"user.id": user_label, "query.length": len(clean_query)}):
        try:
            final_state = workflow.invoke(initial_state)
        except Exception as e:
            logger.error(f"Error executing LangGraph workflow: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Inference execution failed: {str(e)}")

    llm_duration = time.perf_counter() - start_llm_time
    metrics.observe_histogram("docuchat_llm_latency_seconds", llm_duration)

    raw_response = final_state.get("query_response", "No response could be generated.")
    clean_response = clean_llm_response(raw_response)
    evaluation_state = final_state.get("evaluation_state") == "True"
    retries = final_state.get("retry_count", 0)
    raw_citations = final_state.get("citations", [])

    # Validate citations into Pydantic models
    citations_list: List[CitationItem] = []
    for c in raw_citations:
        try:
            citations_list.append(CitationItem(**c))
        except Exception as ce:
            logger.warning(f"Could not parse citation item {c}: {ce}")

    # Track estimated token usage
    tokens_in = max(1, len(clean_query) // 4)
    tokens_out = max(1, len(clean_response) // 4)
    metrics.inc_counter("docuchat_tokens_total", tokens_in, labels={"type": "input"})
    metrics.inc_counter("docuchat_tokens_total", tokens_out, labels={"type": "output"})

    # 3. Store into Cache (1 hour TTL, tenant-scoped)
    cache_payload = {
        "response": clean_response,
        "retry_count": retries,
        "evaluation_passed": evaluation_state,
        "citations": [c.model_dump() for c in citations_list],
        "timestamp": time.time(),
    }
    cache_manager.set_query(tenant_cache_key, cache_payload, ttl_seconds=3600)

    # 4. Optional Database persistence for multi-turn thread history
    saved_conv_id = await _persist_turns_if_needed(
        db=db,
        conversation_id=request.conversation_id,
        user_id=user_id,
        query=clean_query,
        response=clean_response,
        citations=[c.model_dump() for c in citations_list],
        metadata={"retries": retries, "eval_passed": evaluation_state}
    )

    logger.info(f"Chat completed for user [{user_label}] (Retries: {retries}, Eval Passed: {evaluation_state}, Citations: {len(citations_list)})")

    return ChatResponse(
        response=clean_response,
        retry_count=retries,
        evaluation_passed=evaluation_state,
        citations=citations_list,
        conversation_id=saved_conv_id,
        metadata={
            "cache_hit": False,
            "llm_latency_ms": round(llm_duration * 1000, 2),
            "tokens_estimated": {"input": tokens_in, "output": tokens_out},
            "user": user_label
        }
    )
