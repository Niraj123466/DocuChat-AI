"""Base abstractions for document rerankers."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class RankedChunk:
    """Represents a chunk of retrieved text with score and metadata."""
    content: str
    source: str = "document"
    chunk_id: Any = 0
    score: float = 0.0
    original_rank: int = 0
    page_number: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class BaseReranker(ABC):
    """Abstract base class for all context rerankers."""

    @abstractmethod
    def rerank(
        self,
        query: str,
        chunks: List[RankedChunk],
        top_n: int = 4
    ) -> List[RankedChunk]:
        """Reranks a list of candidate chunks for a specific query."""
        pass
