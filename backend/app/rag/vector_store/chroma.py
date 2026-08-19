import os
import logging
from typing import Dict, Any, List, Optional
import chromadb

from app.rag.vector_store.base import BaseVectorStoreProvider
from app.core.config import settings

logger = logging.getLogger(__name__)


class ChromaVectorStoreProvider(BaseVectorStoreProvider):
    COLLECTION_NAME = "document_chunks"

    def __init__(self, persist_dir: Optional[str] = None):
        self.persist_dir = persist_dir or settings.CHROMA_PERSIST_DIR
        os.makedirs(self.persist_dir, exist_ok=True)
        self.client = chromadb.PersistentClient(path=self.persist_dir)
        self._get_collection()

    def _get_collection(self):
        try:
            self.collection = self.client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={"description": "MultiModal Document Intelligence Vector Store"}
            )
        except Exception as e:
            logger.warning(f"ChromaDB get_or_create_collection reset recovery: {e}")
            self.collection = self.client.create_collection(
                name=self.COLLECTION_NAME,
                metadata={"description": "MultiModal Document Intelligence Vector Store"}
            )
        return self.collection

    def add_chunks(
        self,
        chunk_ids: List[str],
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]]
    ) -> int:
        if not chunk_ids or not texts or not embeddings:
            return 0

        clean_metadatas = []
        for m in metadatas:
            clean_m = {}
            for k, v in m.items():
                if v is None:
                    clean_m[k] = ""
                elif isinstance(v, (str, int, float, bool)):
                    clean_m[k] = v
                else:
                    clean_m[k] = str(v)
            clean_metadatas.append(clean_m)

        try:
            self._get_collection().add(
                ids=chunk_ids,
                documents=texts,
                embeddings=embeddings,
                metadatas=clean_metadatas
            )
        except Exception as err:
            logger.warning(f"ChromaDB add error ({err}). Retrying after refreshing collection handle...")
            try:
                self.client.delete_collection(name=self.COLLECTION_NAME)
            except Exception:
                pass
            self.collection = self.client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={"description": "MultiModal Document Intelligence Vector Store"}
            )
            self.collection.add(
                ids=chunk_ids,
                documents=texts,
                embeddings=embeddings,
                metadatas=clean_metadatas
            )

        logger.info(f"Added {len(chunk_ids)} vector chunks to ChromaDB collection '{self.COLLECTION_NAME}'.")
        return len(chunk_ids)

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        document_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        where_clause = {"document_id": document_id} if document_id else None

        try:
            results = self._get_collection().query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_clause
            )
        except Exception as query_err:
            logger.warning(f"ChromaDB query warning ({query_err}). Re-fetching collection handle...")
            results = self.client.get_or_create_collection(name=self.COLLECTION_NAME).query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where_clause
            )

        formatted_results: List[Dict[str, Any]] = []

        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for idx in range(len(ids)):
            dist = distances[idx] if idx < len(distances) else 0.5
            score = round(max(0.0, 1.0 - (dist / 2.0)), 4)
            meta = metadatas[idx] if idx < len(metadatas) else {}

            formatted_results.append({
                "chunk_id": ids[idx],
                "text": documents[idx] if idx < len(documents) else "",
                "score": score,
                "distance": dist,
                "document_id": meta.get("document_id", ""),
                "page_number": meta.get("page_number", 1),
                "filename": meta.get("filename", "document.pdf"),
                "source_type": meta.get("source_type", "TEXT"),
                "chunk_index": meta.get("chunk_index", 0),
                "metadata": meta
            })

        return formatted_results

    def delete_document_chunks(self, document_id: str) -> int:
        if not document_id:
            return 0
        try:
            col = self._get_collection()
            existing = col.get(where={"document_id": document_id})
            existing_ids = existing.get("ids", [])
            if existing_ids:
                col.delete(ids=existing_ids)
                logger.info(f"Deleted {len(existing_ids)} existing chunks for document '{document_id}' from ChromaDB.")
                return len(existing_ids)
        except Exception as e:
            logger.warning(f"Error checking/deleting chunks for document {document_id}: {e}")
        return 0
