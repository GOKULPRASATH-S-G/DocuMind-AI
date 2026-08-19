import os
import uuid
import logging
from typing import List, Dict, Any
from app.services.vector_store.base import BaseVectorStoreProvider
from app.core.config import settings
from app.core.exceptions import VectorStoreError

logger = logging.getLogger(__name__)


class ChromaVectorStoreProvider(BaseVectorStoreProvider):
    def __init__(self, persist_dir: str = settings.CHROMA_PERSIST_DIR, collection_name: str = "document_chunks"):
        self.persist_dir = persist_dir
        self.collection_name = collection_name
        self.collection = None
        self._init_chroma()

    def _init_chroma(self):
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            os.makedirs(self.persist_dir, exist_ok=True)
            self.client = chromadb.PersistentClient(path=self.persist_dir)
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
        except Exception as e:
            logger.error(f"ChromaDB initialization failed: {e}")
            self.collection = None

    def add_chunks(self, chunks: List[Dict[str, Any]]) -> List[str]:
        if not self.collection:
            logger.warning("ChromaDB collection unavailable. Skipping persistent vector store insertion.")
            return [c.get("id", str(uuid.uuid4())) for c in chunks]

        ids = []
        documents = []
        metadatas = []

        for chunk in chunks:
            chunk_id = chunk.get("id", str(uuid.uuid4()))
            text = chunk.get("chunk_text", "")
            metadata = {
                "document_id": str(chunk.get("document_id", "")),
                "document_name": str(chunk.get("document_name", "")),
                "page_number": int(chunk.get("page_number", 1)),
                "chunk_index": int(chunk.get("chunk_index", 0))
            }
            ids.append(chunk_id)
            documents.append(text)
            metadatas.append(metadata)

        try:
            self.collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas
            )
            return ids
        except Exception as e:
            logger.error(f"Failed to insert chunks into ChromaDB: {e}")
            raise VectorStoreError(f"ChromaDB add failed: {str(e)}")

    def search_similar(self, query: str, top_k: int = 5, document_ids: List[str] = None) -> List[Dict[str, Any]]:
        if not self.collection:
            logger.warning("ChromaDB unavailable. Returning empty search results.")
            return []

        where_clause = None
        if document_ids:
            if len(document_ids) == 1:
                where_clause = {"document_id": document_ids[0]}
            else:
                where_clause = {"$or": [{"document_id": doc_id} for doc_id in document_ids]}

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k,
                where=where_clause
            )

            retrieved = []
            if results and results.get("documents") and len(results["documents"]) > 0:
                docs = results["documents"][0]
                metas = results["metadatas"][0] if results.get("metadatas") else []
                distances = results["distances"][0] if results.get("distances") else []
                ids = results["ids"][0] if results.get("ids") else []

                for i in range(len(docs)):
                    sim_score = (1.0 - distances[i]) if i < len(distances) else 0.8
                    meta = metas[i] if i < len(metas) else {}
                    retrieved.append({
                        "id": ids[i] if i < len(ids) else str(uuid.uuid4()),
                        "chunk_text": docs[i],
                        "document_id": meta.get("document_id", ""),
                        "document_name": meta.get("document_name", "Document"),
                        "page_number": meta.get("page_number", 1),
                        "similarity_score": round(max(0.0, min(1.0, sim_score)), 4)
                    })
            return retrieved
        except Exception as e:
            logger.error(f"ChromaDB search failed: {e}")
            return []
