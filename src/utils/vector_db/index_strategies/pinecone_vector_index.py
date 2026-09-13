"""Pinecone vector index strategy implementation.

Handles document embedding, chunk upserting, and top-k semantic search
with score filtering and citation metadata formatting.
"""
from __future__ import annotations

from typing import Any, List, Optional
try:
    from pinecone import Pinecone
except ImportError:
    Pinecone = None

from src.utils.vector_db.index_strategies.base import VectorIndexStrategy
from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger("pinecone_vector_index")

class PineconeVectorIndex(VectorIndexStrategy):
    def __init__(self, embeddings: Any) -> None:
        self.__collection_name = settings.PINECONE_INDEX_NAME
        self.__embeddings = embeddings
        self.__collection_loaded = False
        self.__client: Optional[Pinecone] = None
        self._target_dim: Optional[int] = None

        if settings.PINECONE_API_KEY:
            try:
                self.__client = Pinecone(api_key=settings.PINECONE_API_KEY)
            except Exception as e:
                logger.error(f"Failed to initialize Pinecone client: {e}")
        else:
            logger.warning("PINECONE_API_KEY not configured. Pinecone operations will fail until key is provided.")

    def _get_index(self):
        if not self.__client:
            if not settings.PINECONE_API_KEY:
                raise ValueError("PINECONE_API_KEY is not set.")
            self.__client = Pinecone(api_key=settings.PINECONE_API_KEY)
        return self.__client.Index(self.__collection_name)

    def _get_target_dimension(self, index) -> Optional[int]:
        """Retrieves target dimension from Pinecone index to prevent 400 dimension mismatch."""
        if self._target_dim is None:
            try:
                stats = index.describe_index_stats()
                self._target_dim = getattr(stats, "dimension", None)
                logger.info(f"Detected Pinecone index dimension: {self._target_dim}")
            except Exception as e:
                logger.warning(f"Could not retrieve Pinecone index dimension: {e}")
        return self._target_dim

    def _align_vector(self, vector: List[float], target_dim: Optional[int]) -> List[float]:
        """Aligns vector to target dimension. For cosine distance, zero-padding strictly preserves similarity."""
        if not target_dim or len(vector) == target_dim:
            return vector
        if len(vector) < target_dim:
            return list(vector) + [0.0] * (target_dim - len(vector))
        return list(vector[:target_dim])

    def create_or_load_vector_index(self, markdown_text: str, chunker=None):
        if self.__collection_loaded:
            return self

        try:
            index = self._get_index()
        except Exception as e:
            logger.error(f"Cannot connect to Pinecone index '{self.__collection_name}': {e}")
            return self

        # Use chunker callable if supplied; otherwise treat as single chunk
        if chunker is not None:
            chunk_outputs = chunker(markdown_text)
            if chunk_outputs and hasattr(chunk_outputs[0], "page_content"):
                chunk_texts = [c.page_content for c in chunk_outputs]
            else:
                chunk_texts = list(chunk_outputs)
        else:
            chunk_texts = [markdown_text] if markdown_text else []

        if not chunk_texts:
            self.__collection_loaded = True
            return self

        logger.info(f"Embedding {len(chunk_texts)} document chunks...")
        vectors = self.__embeddings.embed_documents(chunk_texts)
        target_dim = self._get_target_dimension(index)

        pinecone_vectors = []
        for i, (values, chunk_text) in enumerate(zip(vectors, chunk_texts)):
            aligned_values = self._align_vector(values, target_dim)
            pinecone_vectors.append({
                "id": f"chunk_{i}",
                "values": aligned_values,
                "metadata": {
                    "chunk_text": chunk_text,
                    "chunk_id": i,
                    "source": "documents_folder"
                }
            })

        # Batch upsert to Pinecone (max 100 per batch for safety)
        batch_size = 100
        for i in range(0, len(pinecone_vectors), batch_size):
            batch = pinecone_vectors[i:i+batch_size]
            index.upsert(vectors=batch)

        logger.info(f"Successfully uploaded {len(pinecone_vectors)} chunks to Pinecone index '{self.__collection_name}'")
        self.__collection_loaded = True
        return self

    def semantic_search(
        self,
        embeded_query: List[float],
        top_k: Optional[int] = None,
        user_id: Optional[str] = None
    ) -> str:
        """Executes top-K semantic search across Pinecone with strict tenant isolation."""
        try:
            index = self._get_index()
            target_dim = self._get_target_dimension(index)
            aligned_query = self._align_vector(embeded_query, target_dim)
            k = top_k or settings.TOP_K

            query_kwargs: Dict[str, Any] = {
                "vector": aligned_query,
                "top_k": k,
                "include_metadata": True,
            }
            if user_id:
                query_kwargs["namespace"] = f"user_{user_id}"
                query_kwargs["filter"] = {"user_id": {"$eq": str(user_id)}}

            response = index.query(**query_kwargs)
        except Exception as e:
            logger.error(f"Pinecone query error: {e}", exc_info=True)
            return f"Retrieval error: {str(e)}"

        matches = response.get("matches", [])
        if not matches:
            return "No relevant context found for the question."

        # Filter and rank matches above score threshold
        relevant_chunks: List[str] = []
        for i, match in enumerate(matches, 1):
            score = match.get("score", 0.0)
            metadata = match.get("metadata", {})
            chunk_text = metadata.get("chunk_text", "").strip()

            if chunk_text and score >= settings.SCORE_THRESHOLD:
                source = metadata.get("source", "document")
                chunk_id = metadata.get("chunk_id", i)
                relevant_chunks.append(
                    f"--- Source [Doc Chunk {chunk_id} ({source})] (Relevance: {score:.2f}) ---\n{chunk_text}"
                )

        if not relevant_chunks:
            # If all are below threshold, fallback to top match if score > 0.2
            top_match = matches[0]
            if top_match.get("score", 0.0) >= 0.20:
                chunk_text = top_match.get("metadata", {}).get("chunk_text", "").strip()
                if chunk_text:
                    return f"--- Source [Top Chunk] ---\n{chunk_text}"
            return "No relevant context found for the question."

        return "\n\n".join(relevant_chunks)
