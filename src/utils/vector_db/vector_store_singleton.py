"""Singleton manager for the vector store index.

Ensures that the document loader, embeddings model, and vector store
are initialized cleanly once and reused across agent invocations without
hardcoded paths or redundant re-initializations.
"""
from __future__ import annotations

import threading
from pathlib import Path
from typing import Optional, Any

from src.core.config import settings
from src.core.logging import get_logger
from src.utils.vector_db.loader_strategies.base import DocumentLoaderStrategy
from src.utils.vector_db.index_strategies.base import VectorIndexStrategy

logger = get_logger("vector_store_singleton")

class VectorStoreSingleton:
    _instance: Optional[VectorStoreSingleton] = None
    _lock = threading.Lock()

    def __new__(cls, *args: Any, **kwargs: Any) -> VectorStoreSingleton:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(VectorStoreSingleton, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        embeddings_model: Any,
        document_loader_strategy: DocumentLoaderStrategy,
        vector_index_strategy: VectorIndexStrategy
    ) -> None:
        # Initialize only once per instance lifecycle
        if getattr(self, "_initialized", False):
            return

        with self._lock:
            if getattr(self, "_initialized", False):
                return
            self.embeddings_model = embeddings_model
            self.document_loader_strategy = document_loader_strategy
            self.vector_index_strategy = vector_index_strategy
            self.vector_store = None

            try:
                from langchain_experimental.text_splitter import SemanticChunker
                self.text_splitter = SemanticChunker(embeddings_model, breakpoint_threshold_type="percentile")
                def semantic_chunker(markdown_text: str):
                    return self.text_splitter.create_documents([markdown_text])
                self.chunker = semantic_chunker
            except Exception as e:
                logger.warning(f"SemanticChunker unavailable, falling back to simple chunker: {e}")
                def simple_chunker(markdown_text: str):
                    from langchain_core.documents import Document
                    return [Document(page_content=markdown_text[i:i+1000]) for i in range(0, len(markdown_text), 800)]
                self.chunker = simple_chunker

            self._initialized = True

    def _resolve_document_path(self, target_path: Optional[str | Path] = None) -> Path:
        """Resolve document path dynamically from settings or explicit parameter."""
        if target_path:
            p = Path(target_path)
            if p.exists():
                return p

        # Check default documents folder
        doc_dir = Path(settings.DOCUMENTS_DIR)
        if doc_dir.exists():
            default_pdf = doc_dir / "MIREMS.pdf"
            if default_pdf.exists():
                return default_pdf
            # Fallback to first pdf found in documents directory
            pdf_files = list(doc_dir.glob("*.pdf"))
            if pdf_files:
                return pdf_files[0]

        # Return whatever is available or fall back to MIREMS.pdf relative path
        return settings.BASE_DIR / "documents" / "MIREMS.pdf"

    def _build_vectorstore(self, document_path: Optional[str | Path] = None) -> Any:
        """Orchestrates document loading, conversion, and vector indexing."""
        if self.vector_store is None:
            resolved_path = self._resolve_document_path(document_path)
            logger.info(f"Building vector store using document at: {resolved_path}")

            if not resolved_path.exists():
                logger.warning(f"Document file not found at {resolved_path}. Skipping initial upsert.")
                return None

            try:
                documents_markdown = self.document_loader_strategy.load_documents(path=str(resolved_path))
                self.vector_store = self.vector_index_strategy.create_or_load_vector_index(
                    documents_markdown,
                    chunker=self.chunker
                )
                logger.info("Vector store built and loaded successfully")
            except Exception as e:
                logger.error(f"Failed to build vector store: {e}", exc_info=True)
                raise
        return self.vector_store

    def query(self, query_text: str, user_id: Optional[str] = None) -> str:
        """Embeds query text and executes semantic retrieval across the vector index with tenant isolation."""
        try:
            query_embedding = self.embeddings_model.embed_query(query_text)
        except Exception as e:
            logger.error(f"Error generating query embedding: {e}")
            return "Error: Unable to generate query embeddings."

        if self.vector_store is None:
            try:
                self._build_vectorstore()
            except Exception as e:
                logger.warning(f"Vector store build deferred or failed: {e}")

        try:
            results = self.vector_index_strategy.semantic_search(
                embeded_query=query_embedding,
                user_id=user_id
            )
            return results
        except Exception as e:
            logger.error(f"Error querying vector index: {e}", exc_info=True)
            return f"Error executing semantic search: {str(e)}"
