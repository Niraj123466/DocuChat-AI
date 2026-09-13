"""Query Agent responsible for RAG retrieval, cross-encoder reranking, and generation."""
from __future__ import annotations

from typing import Optional, List, Dict, Any

from src.core.config import settings
from src.core.logging import get_logger
from src.core.llm import GoogleGeminiProvider, MockLLMProvider, FallbackLLMProvider, TokenBudgetManager
from src.rag.rerankers.base import RankedChunk
from src.rag.rerankers.cross_encoder import CrossEncoderReranker
from src.rag.citation import CitationEngine
from src.utils.prompt_manager import prompt_manager

logger = get_logger("query_agent")

def _parse_chunks_from_context_text(raw_context: str) -> List[RankedChunk]:
    """Parses raw context text blocks into individual RankedChunk objects."""
    if not raw_context or "No relevant context" in raw_context:
        return []

    # If context is divided by headers like '--- Source [Doc Chunk X (source)] (Relevance: 0.85) ---'
    blocks = raw_context.split("--- Source ")
    chunks: List[RankedChunk] = []

    for idx, block in enumerate(blocks):
        block = block.strip()
        if not block:
            continue

        # Extract content after the header
        lines = block.split("\n", 1)
        header = lines[0] if lines else ""
        content = lines[1].strip() if len(lines) > 1 else block

        source = "document"
        chunk_id = idx
        score = 0.5

        if "[" in header and "]" in header:
            header_inner = header[header.find("[") + 1 : header.find("]")]
            parts = header_inner.split()
            if len(parts) >= 3 and "Chunk" in parts:
                try:
                    chunk_id = parts[parts.index("Chunk") + 1]
                except (ValueError, IndexError):
                    pass
            source = header_inner

        chunks.append(
            RankedChunk(
                content=content,
                source=source,
                chunk_id=chunk_id,
                score=score,
                original_rank=idx
            )
        )

    if not chunks and raw_context.strip():
        # Fallback single chunk
        chunks.append(RankedChunk(content=raw_context.strip(), source="document", chunk_id=0, score=0.5))

    return chunks


def create_query_agent(
    model: str = "gemini-3.6-flash",
    temperature: float = 0.1,
    api_key: Optional[str] = None,
    prompt_path: Optional[str] = None
):
    """Creates a query execution agent configured with Reranker and Citation engine."""
    effective_key = api_key or settings.GOOGLE_API_KEY
    if effective_key:
        primary = GoogleGeminiProvider(api_key=effective_key, model_name=model)
        fallback = MockLLMProvider(predefined_response="[Fallback] I could not reach the primary LLM model.")
        llm = FallbackLLMProvider(primary=primary, fallback=fallback)
    else:
        logger.warning("GOOGLE_API_KEY not configured. Using MockLLMProvider.")
        llm = MockLLMProvider()

    system_text = prompt_manager.get_prompt(
        "query_agent_prompt",
        organization_name=settings.ORGANIZATION_NAME or "DocuChat"
    )
    reranker = CrossEncoderReranker(min_score=settings.SCORE_THRESHOLD)

    class RAGExecutor:
        def __init__(self, llm_provider, system_prompt, reranker_instance):
            self.llm = llm_provider
            self.system_prompt = system_prompt
            self.reranker = reranker_instance

        def invoke(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
            user_input = inputs.get("input", "").strip()
            user_id = inputs.get("user_id")
            from src.tools.query_tool import retrieve_context

            # 1. Retrieve initial candidate chunks with tenant isolation
            try:
                raw_context = retrieve_context(user_input, user_id=user_id)
            except Exception as e:
                logger.error(f"Error during context retrieval: {e}")
                raw_context = ""

            # 2. Parse candidate chunks
            candidate_chunks = _parse_chunks_from_context_text(raw_context)

            # 3. Cross-Encoder Reranking
            if candidate_chunks:
                reranked_chunks = self.reranker.rerank(
                    query=user_input,
                    chunks=candidate_chunks,
                    top_n=settings.TOP_K
                )
            else:
                reranked_chunks = []

            # 4. Format context with numbered citation tags
            formatted_context = CitationEngine.format_context_for_prompt(reranked_chunks)

            # 5. Enforce Token Budget
            budgeted_context = TokenBudgetManager.truncate_to_budget(formatted_context, max_tokens=3000)

            # 6. Build prompt messages
            messages = [
                ("system", self.system_prompt),
                ("human", f"Question:\n{user_input}\n\nContext:\n{budgeted_context}")
            ]

            # 7. Generate response
            raw_response = self.llm.generate(messages=messages, temperature=0.1)

            # 8. Extract citations from answer
            citations = CitationEngine.extract_citations(raw_response, reranked_chunks)

            return {
                "output": raw_response,
                "citations": citations,
                "chunks_retrieved": len(candidate_chunks),
                "chunks_used": len(reranked_chunks)
            }

    return RAGExecutor(llm, system_text, reranker)
