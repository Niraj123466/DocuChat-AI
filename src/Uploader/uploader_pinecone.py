"""Document Uploader service for chunking and upserting into Pinecone.

Decoupled into callable classes without top-level execution side-effects.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, List, Dict, Any

try:
    from pinecone import Pinecone
except ImportError:
    Pinecone = None
from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger("uploader_pinecone")

class DocumentUploader:
    """Manages document chunking, embedding generation, and Pinecone vector upserts."""

    def __init__(self, index_name: Optional[str] = None) -> None:
        self.index_name = index_name or settings.PINECONE_INDEX_NAME
        if not settings.PINECONE_API_KEY:
            logger.warning("PINECONE_API_KEY not configured.")
            self.client = None
        else:
            self.client = Pinecone(api_key=settings.PINECONE_API_KEY)

    def _get_index(self):
        if not self.client:
            if not settings.PINECONE_API_KEY:
                raise ValueError("PINECONE_API_KEY is not set.")
            self.client = Pinecone(api_key=settings.PINECONE_API_KEY)
        return self.client.Index(self.index_name)

    def upload_documents(
        self,
        file_path: Optional[str | Path] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Loads target document, chunks it, embeds it, and upserts vectors to Pinecone with tenant isolation."""
        target = Path(file_path) if file_path else (settings.DOCUMENTS_DIR / "MIREMS.pdf")
        if not target.exists():
            raise FileNotFoundError(f"Document to upload does not exist at: {target}")

        logger.info(f"Starting ingestion for: {target} (Tenant: {user_id})")

        # 1. Convert document using LocalLoader or fallback
        from src.utils.vector_db.loader_strategies.local_loader import LocalLoader
        loader = LocalLoader()
        markdown_text = loader.load_documents(target)

        # 2. Embeddings model
        from langchain_huggingface import HuggingFaceEmbeddings
        embeddings_model = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_kwargs={"device": "cpu"}
        )

        # 3. Chunking with fallback strategy
        chunk_texts = []
        try:
            from langchain_experimental.text_splitter import SemanticChunker
            chunker = SemanticChunker(embeddings_model, breakpoint_threshold_type="percentile")
            docs = chunker.create_documents([markdown_text])
            chunk_texts = [d.page_content for d in docs] if docs else [markdown_text]
        except Exception:
            try:
                from langchain_text_splitters import RecursiveCharacterTextSplitter
                splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
                chunk_texts = splitter.split_text(markdown_text) or [markdown_text]
            except Exception:
                chunk_texts = [markdown_text[i:i+1000] for i in range(0, len(markdown_text), 800)] or [markdown_text]

        logger.info(f"Generated {len(chunk_texts)} chunks for {target.name}")

        # 4. Generate Embeddings
        vectors = embeddings_model.embed_documents(chunk_texts)

        # 5. Build Pinecone vectors with dimension alignment and tenant tagging
        index = self._get_index()
        target_dim = None
        try:
            stats = index.describe_index_stats()
            target_dim = getattr(stats, "dimension", None)
            logger.info(f"Target Pinecone index dimension: {target_dim}")
        except Exception as e:
            logger.warning(f"Could not retrieve Pinecone index dimension: {e}")

        def _align(vec: List[float]) -> List[float]:
            if not target_dim or len(vec) == target_dim:
                return vec
            if len(vec) < target_dim:
                return list(vec) + [0.0] * (target_dim - len(vec))
            return list(vec[:target_dim])

        pinecone_vectors: List[Dict[str, Any]] = []
        id_prefix = f"usr_{user_id}_{target.stem}" if user_id else f"{target.stem}"

        for i, (vec, chunk_text) in enumerate(zip(vectors, chunk_texts)):
            meta = {
                "chunk_text": chunk_text,
                "chunk_id": i,
                "source": target.name,
            }
            if user_id:
                meta["user_id"] = user_id

            pinecone_vectors.append({
                "id": f"{id_prefix}_chunk_{i}",
                "values": _align(vec),
                "metadata": meta
            })

        # 6. Upsert in batches of 100 with namespace partitioning
        batch_size = 100
        namespace = f"user_{user_id}" if user_id else None

        for i in range(0, len(pinecone_vectors), batch_size):
            batch = pinecone_vectors[i:i + batch_size]
            if namespace:
                index.upsert(vectors=batch, namespace=namespace)
            index.upsert(vectors=batch)  # Also in default namespace with user_id metadata

        logger.info(f"Successfully uploaded {len(pinecone_vectors)} chunks to Pinecone index '{self.index_name}' (Namespace: {namespace})")
        return {
            "status": "success",
            "document": target.name,
            "chunks_uploaded": len(pinecone_vectors),
            "index": self.index_name,
            "user_id": user_id,
            "namespace": namespace or "default"
        }

# Backward compatibility alias
MyDocumentUploader = DocumentUploader

if __name__ == "__main__":
    uploader = DocumentUploader()
    try:
        result = uploader.upload_documents()
        print(f"Upload result: {result}")
    except Exception as err:
        print(f"Upload failed: {err}")
