import time
import logging
from typing import Dict, Any, List, Optional

from app.core.exceptions import LLMExtractionError
from app.rag.embeddings.base import BaseEmbeddingProvider
from app.rag.embeddings.gemini import GeminiEmbeddingProvider
from app.rag.vector_store.base import BaseVectorStoreProvider
from app.rag.vector_store.chroma import ChromaVectorStoreProvider

logger = logging.getLogger(__name__)


class DocumentRetriever:
    """
    RAG Document Retriever.
    Generates query vector embeddings and performs semantic similarity retrieval against ChromaDB.
    """

    def __init__(
        self,
        embedding_provider: Optional[BaseEmbeddingProvider] = None,
        vector_store: Optional[BaseVectorStoreProvider] = None
    ):
        self.embedding_provider = embedding_provider or GeminiEmbeddingProvider()
        self.vector_store = vector_store or ChromaVectorStoreProvider()

    def search(
        self,
        query: str,
        top_k: int = 5,
        document_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Executes semantic search against the production vector index.
        """
        start_time = time.time()
        if not query or not query.strip():
            raise LLMExtractionError("Search query cannot be empty.")

        logger.info(f"Executing semantic vector search: query='{query}', top_k={top_k}, document_id={document_id}")

        # 1. Embed query
        query_embedding = self.embedding_provider.embed_text(query)

        # 2. Vector Store Similarity Search
        results = self.vector_store.search(
            query_embedding=query_embedding,
            top_k=top_k,
            document_id=document_id
        )

        duration = round(time.time() - start_time, 3)
        logger.info(f"Vector search returned {len(results)} matches in {duration}s.")

        return results
