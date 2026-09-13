"""Deterministic Source Citation Engine for Grounded RAG.

Injects numbered document citation tags into context prompts, extracts
inline citations from LLM output, and produces verified citation objects.
"""
from __future__ import annotations

import re
from typing import List, Dict, Any, Optional
from src.rag.rerankers.base import RankedChunk

class CitationItem:
    """Represents a validated citation mapped to source document chunk."""

    def __init__(
        self,
        doc_index: int,
        source: str,
        chunk_id: Any,
        relevance_score: float,
        text_snippet: str,
        page_number: Optional[int] = None
    ) -> None:
        self.doc_index = doc_index
        self.source = source
        self.chunk_id = chunk_id
        self.relevance_score = round(relevance_score, 3)
        self.text_snippet = text_snippet
        self.page_number = page_number

    def to_dict(self) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "doc_index": self.doc_index,
            "source": self.source,
            "chunk_id": str(self.chunk_id),
            "relevance_score": self.relevance_score,
            "text_snippet": self.text_snippet,
        }
        if self.page_number is not None:
            data["page_number"] = self.page_number
        return data


class CitationEngine:
    """Formats context with citation markers and extracts cited sources from LLM text."""

    @staticmethod
    def format_context_for_prompt(chunks: List[RankedChunk]) -> str:
        """Formats a list of RankedChunks into numbered citation blocks for prompt injection."""
        if not chunks:
            return "No relevant context found in documents."

        blocks: List[str] = []
        for i, chunk in enumerate(chunks, 1):
            page_info = f" | Page {chunk.page_number}" if chunk.page_number else ""
            header = f"[Doc {i}: {chunk.source}{page_info}]"
            blocks.append(f"{header}\n{chunk.content.strip()}")

        return "\n\n".join(blocks)

    @staticmethod
    def extract_citations(
        llm_answer: str,
        chunks: List[RankedChunk],
        snippet_length: int = 160
    ) -> List[Dict[str, Any]]:
        """Parses inline citation tags like [Doc 1] or [1] from LLM output and correlates with chunks."""
        if not llm_answer or not chunks:
            return []

        # Find all citation references: [Doc 1], [Doc 2], [Doc 1, 2], [1], etc.
        pattern = r"\[(?:Doc\s*)?(\d+)\]"
        matches = re.findall(pattern, llm_answer, re.IGNORECASE)

        cited_indices = set()
        for m in matches:
            try:
                idx = int(m)
                if 1 <= idx <= len(chunks):
                    cited_indices.add(idx)
            except ValueError:
                continue

        # If no explicit [Doc X] tag found, but chunks exist, include top 1 or 2 as background context citations
        if not cited_indices and chunks:
            # Fallback to top-ranked chunks if score is high
            for i, chunk in enumerate(chunks[:2], 1):
                if chunk.score >= 0.3:
                    cited_indices.add(i)

        citations: List[Dict[str, Any]] = []
        for idx in sorted(cited_indices):
            chunk = chunks[idx - 1]
            raw_text = chunk.content.strip()
            snippet = raw_text[:snippet_length] + ("..." if len(raw_text) > snippet_length else "")

            item = CitationItem(
                doc_index=idx,
                source=chunk.source,
                chunk_id=chunk.chunk_id,
                relevance_score=chunk.score,
                text_snippet=snippet,
                page_number=chunk.page_number
            )
            citations.append(item.to_dict())

        return citations
