"""Query tool for RAG context retrieval from the vector store."""
from __future__ import annotations

from typing import Optional
from langchain.tools import tool
from src.core.logging import get_logger

logger = get_logger("query_tool")

_vector_store = None

def _get_or_create_vector_store():
    global _vector_store
    if _vector_store is None:
        from langchain_huggingface import HuggingFaceEmbeddings
        from src.utils.vector_db.vector_store_singleton import VectorStoreSingleton
        from src.utils.vector_db.loader_strategies.local_loader import LocalLoader
        from src.utils.vector_db.index_strategies.pinecone_vector_index import PineconeVectorIndex

        logger.info("Initializing vector store instance for query tool")
        embeddings_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2", model_kwargs={"device": "cpu"})
        loader_strat = LocalLoader()
        index_strat = PineconeVectorIndex(embeddings=embeddings_model)

        _vector_store = VectorStoreSingleton(
            embeddings_model=embeddings_model,
            document_loader_strategy=loader_strat,
            vector_index_strategy=index_strat,
        )
    return _vector_store

def retrieve_context(query_text: str, user_id: Optional[str] = None) -> str:
    """Retrieves relevant document context for a given query string and tenant user_id."""
    try:
        store = _get_or_create_vector_store()
        result = store.query(query_text=query_text, user_id=user_id)
        return result or "No relevant context found."
    except Exception as e:
        logger.error(f"Failed to retrieve context for query: {e}", exc_info=True)
        return "No relevant context found due to retrieval error."

@tool
def get_context(query_text: str) -> str:
    """Retrieves relevant document context for a given user query string."""
    return retrieve_context(query_text=query_text)

if __name__ == "__main__":
    print(get_context.run("What initiative did the federal government announce regarding AI?"))