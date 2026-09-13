"""Cross-Encoder reranker using sentence-transformers with fallback heuristic."""
from __future__ import annotations

import re
import math
from typing import List, Optional
from src.rag.rerankers.base import BaseReranker, RankedChunk
from src.core.logging import get_logger

logger = get_logger("cross_encoder_reranker")

class CrossEncoderReranker(BaseReranker):
    """Reranks candidate chunks using a deep cross-encoder model or semantic fallback."""

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        min_score: float = 0.05
    ) -> None:
        self.model_name = model_name
        self.min_score = min_score
        self._model = None
        self._load_attempted = False

    def _get_model(self):
        if self._model is None and not self._load_attempted:
            self._load_attempted = True
            try:
                from sentence_transformers import CrossEncoder
                logger.info(f"Loading CrossEncoder model: {self.model_name}")
                self._model = CrossEncoder(self.model_name, device="cpu")
                logger.info("CrossEncoder model loaded successfully")
            except Exception as e:
                logger.warning(f"Could not load CrossEncoder ({e}). Using semantic overlap fallback.")
                self._model = None
        return self._model

    def _fallback_score(self, query: str, text: str) -> float:
        """Fast lexical and token-overlap scoring when neural cross-encoder is unavailable."""
        q_tokens = set(re.findall(r"\w+", query.lower()))
        if not q_tokens:
            return 0.0
        t_tokens = re.findall(r"\w+", text.lower())
        if not t_tokens:
            return 0.0

        t_set = set(t_tokens)
        overlap = len(q_tokens.intersection(t_set))
        jaccard = overlap / len(q_tokens.union(t_set))

        # Term frequency weighting for rare/key query words
        tf = sum(1 for t in t_tokens if t in q_tokens)
        normalized_tf = tf / math.sqrt(len(t_tokens) + 1)

        score = (jaccard * 0.4) + (min(normalized_tf, 1.0) * 0.6)
        return float(score)

    def rerank(
        self,
        query: str,
        chunks: List[RankedChunk],
        top_n: int = 4
    ) -> List[RankedChunk]:
        """Reranks candidate chunks in descending order of query relevance."""
        if not chunks:
            return []

        model = self._get_model()

        if model is not None:
            try:
                pairs = [(query, chunk.content) for chunk in chunks]
                scores = model.predict(pairs)
                for chunk, s in zip(chunks, scores):
                    chunk.score = float(s)
            except Exception as e:
                logger.error(f"Error during CrossEncoder inference: {e}", exc_info=True)
                for chunk in chunks:
                    chunk.score = self._fallback_score(query, chunk.content)
        else:
            for chunk in chunks:
                chunk.score = self._fallback_score(query, chunk.content)

        # Sort descending by score
        sorted_chunks = sorted(chunks, key=lambda c: c.score, reverse=True)

        # Filter chunks by minimum threshold
        filtered = [c for c in sorted_chunks if c.score >= self.min_score]
        result = filtered[:top_n] if filtered else sorted_chunks[:top_n]

        logger.info(f"Reranked {len(chunks)} chunks down to top-{len(result)} (Best score: {result[0].score:.3f} if result else 0)")
        return result
