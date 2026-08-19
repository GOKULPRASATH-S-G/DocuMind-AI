import time
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import LLMExtractionError, DocumentProcessingError
from app.models.document import Document
from app.models.extracted_data import ExtractedData
from app.models.document_index import DocumentIndex
from app.rag.chunker import chunk_document_pages
from app.rag.embeddings.base import BaseEmbeddingProvider
from app.rag.embeddings.gemini import GeminiEmbeddingProvider
from app.rag.vector_store.base import BaseVectorStoreProvider
from app.rag.vector_store.chroma import ChromaVectorStoreProvider

logger = logging.getLogger(__name__)


class DocumentIndexer:
    """
    RAG Document Indexer.
    Indexes documents into the ChromaDB vector store.
    """

    def __init__(
        self,
        embedding_provider: Optional[BaseEmbeddingProvider] = None,
        vector_store: Optional[BaseVectorStoreProvider] = None
    ):
        self.embedding_provider = embedding_provider or GeminiEmbeddingProvider()
        self.vector_store = vector_store or ChromaVectorStoreProvider()

    def index_document(self, document_id: str, db: Session) -> Dict[str, Any]:
        start_time = time.time()
        logger.info(f"Initiating vector indexing for document_id: {document_id}")

        doc_record = db.query(Document).filter(Document.id == document_id).first()
        if not doc_record:
            raise DocumentProcessingError(f"Document ID '{document_id}' not found.")

        ext_record = db.query(ExtractedData).filter(ExtractedData.document_id == document_id).first()
        if not ext_record or not ext_record.raw_llm_json:
            raise DocumentProcessingError(f"Extraction data for document '{document_id}' is missing.")

        normalized_data = dict(ext_record.raw_llm_json or {})

        if "visual_artifacts" not in normalized_data and hasattr(doc_record, "visual_artifacts") and doc_record.visual_artifacts:
            normalized_data["visual_artifacts"] = [
                {
                    "image_id": v.image_id,
                    "page_number": v.page_number,
                    "visual_type": v.visual_type,
                    "description": v.description or "",
                    "key_values": v.key_values or [],
                    "storage_reference": v.storage_reference
                } for v in doc_record.visual_artifacts
            ]

        self.vector_store.delete_document_chunks(document_id)

        chunks = chunk_document_pages(normalized_data, filename=doc_record.filename, document_id=doc_record.id)

        if not chunks:
            logger.warning(f"Document '{document_id}' produced zero text chunks for indexing.")
            return {"document_id": document_id, "status": doc_record.processing_status, "chunks_indexed": 0}

        texts = [c.text for c in chunks]
        embeddings = self.embedding_provider.embed_texts(texts)

        if len(embeddings) != len(chunks):
            raise LLMExtractionError("Mismatch between generated embeddings count and chunks count.")

        chunk_ids = [c.chunk_id for c in chunks]
        metadatas = [c.metadata for c in chunks]

        added_count = self.vector_store.add_chunks(
            chunk_ids=chunk_ids,
            texts=texts,
            embeddings=embeddings,
            metadatas=metadatas
        )

        doc_record.processing_status = "INDEXED"

        idx_record = db.query(DocumentIndex).filter(DocumentIndex.document_id == document_id).first()
        if not idx_record:
            idx_record = DocumentIndex(
                document_id=document_id,
                collection_name=getattr(self.vector_store, "COLLECTION_NAME", "document_chunks"),
                chunk_count=added_count,
                embedding_model=getattr(self.embedding_provider, "model_name", settings.GEMINI_EMBEDDING_MODEL)
            )
            db.add(idx_record)
        else:
            idx_record.chunk_count = added_count
            idx_record.embedding_model = getattr(self.embedding_provider, "model_name", settings.GEMINI_EMBEDDING_MODEL)

        db.commit()

        duration = round(time.time() - start_time, 3)
        logger.info(f"Indexing complete for document {document_id}: status=INDEXED, chunks={added_count}, duration={duration}s")

        return {
            "document_id": document_id,
            "status": "INDEXED",
            "chunks_indexed": added_count
        }
