from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseVectorStoreProvider(ABC):
    @abstractmethod
    def add_chunks(self, chunks: List[Dict[str, Any]]) -> List[str]:
        """Add text chunks with embeddings and metadata to vector database."""
        pass

    @abstractmethod
    def search_similar(self, query: str, top_k: int = 5, document_ids: List[str] = None) -> List[Dict[str, Any]]:
        """Search for top_k most similar chunks matching query string."""
        pass
