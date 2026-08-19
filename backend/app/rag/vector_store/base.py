from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional


class BaseVectorStoreProvider(ABC):
    @abstractmethod
    def add_chunks(
        self,
        chunk_ids: List[str],
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]]
    ) -> int:
        """Stores chunk text, embedding vectors, and metadata in the vector database."""
        pass

    @abstractmethod
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        document_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Performs vector similarity search."""
        pass

    @abstractmethod
    def delete_document_chunks(self, document_id: str) -> int:
        """Deletes all vector chunks associated with a document_id."""
        pass
