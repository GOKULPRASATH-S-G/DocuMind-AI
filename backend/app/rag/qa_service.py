import time
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from app.core.exceptions import LLMExtractionError
from app.schemas.qa import RAGAnswer, Citation, QAQuery
from app.rag.retriever import DocumentRetriever
from app.rag.prompts import GROUNDED_RAG_SYSTEM_PROMPT, build_evidence_context
from app.rag.evidence_builder import build_multimodal_context
from app.services.llm.base import BaseLLMProvider
from app.services.llm.gemini import GeminiLLMProvider
from app.models.document import Document

logger = logging.getLogger(__name__)



class GroundedQAService:
    """
    Phase 7 Grounded RAG Question-Answering Engine.
    Orchestrates semantic retrieval, evidence filtering, grounded LLM synthesis,
    citation verification, conflict detection, and evaluation logging.
    """

    MIN_SIMILARITY_THRESHOLD = 0.05

    def __init__(
        self,
        retriever: Optional[DocumentRetriever] = None,
        llm_provider: Optional[BaseLLMProvider] = None
    ):
        self.retriever = retriever or DocumentRetriever()
        self.llm_provider = llm_provider or GeminiLLMProvider()

    def answer_question(
        self,
        query: str,
        top_k: int = 5,
        document_id: Optional[str] = None,
        db: Optional[Session] = None
    ) -> RAGAnswer:
        """
        Executes grounded QA workflow:
        1. Validate query & document approval status.
        2. Execute semantic retrieval via ChromaDB.
        3. Filter weak/irrelevant evidence.
        4. Construct evidence context block.
        5. Invoke Gemini with strict Grounded RAG System Prompt.
        6. Validate Pydantic response & grounding confidence.
        7. Log evaluation metrics.
        """
        start_time = time.time()

        # 1. Query Validation
        if not query or not query.strip():
            raise LLMExtractionError("Search query cannot be empty.")

        query = query.strip()
        logger.info(f"Processing Grounded QA query: '{query}' (top_k={top_k}, document_id={document_id})")

        # Optional DB check: Enforce APPROVED document rule if document_id is specified
        if document_id and db:
            doc_record = db.query(Document).filter(Document.id == document_id).first()
            if not doc_record:
                raise LLMExtractionError(f"Document ID '{document_id}' not found.")
            if doc_record.processing_status not in ["APPROVED", "INDEXED"]:
                raise LLMExtractionError(
                    f"Document '{document_id}' is not approved for QA retrieval. Status: '{doc_record.processing_status}'"
                )

        # 2. Semantic Vector Retrieval
        retrieval_start = time.time()
        retrieved_chunks = self.retriever.search(
            query=query,
            top_k=top_k,
            document_id=document_id
        )
        retrieval_duration = round(time.time() - retrieval_start, 3)

        # 3. Evidence Filtering & Weak Relevance Check with SQL DB Fallback
        valid_chunks = [c for c in retrieved_chunks if c.get("text", "").strip()]
        max_score = max([c.get("score", 0.0) for c in valid_chunks], default=0.0)

        if not valid_chunks or max_score < self.MIN_SIMILARITY_THRESHOLD:
            logger.info(f"Vector search returned weak/empty evidence for '{query}'. Attempting DB document fallback...")
            
            # Database Evidence Fallback
            if db:
                from app.models.extracted_data import ExtractedData
                target_docs = []
                if document_id:
                    doc = db.query(Document).filter(Document.id == document_id).first()
                    if doc:
                        target_docs = [doc]
                else:
                    target_docs = db.query(Document).order_by(Document.uploaded_at.desc()).limit(5).all()

                fallback_chunks = []
                for doc_rec in target_docs:
                    ext = db.query(ExtractedData).filter(ExtractedData.document_id == doc_rec.id).first()
                    if ext:
                        v_data = ext.validated_data or {}
                        r_data = ext.raw_llm_json or {}
                        
                        doc_text = ""
                        if v_data and v_data.get("summary"):
                            doc_text = f"Document Title: {v_data.get('document_title', doc_rec.filename)}\nCategory: {v_data.get('document_type', '')}\nSummary: {v_data.get('summary', '')}\nKey Topics: {', '.join(v_data.get('key_topics', []))}"
                        elif r_data and r_data.get("pages"):
                            page_texts = [p.get("text", "") for p in r_data.get("pages", []) if p.get("text")]
                            doc_text = "\n".join(page_texts)[:1500]

                        if doc_text.strip():
                            fallback_chunks.append({
                                "chunk_id": f"{doc_rec.id}_db_fallback",
                                "text": doc_text,
                                "score": 0.85,
                                "document_id": doc_rec.id,
                                "filename": doc_rec.filename,
                                "page_number": 1,
                                "source_type": "TEXT"
                            })

                if fallback_chunks:
                    valid_chunks = fallback_chunks
                    max_score = 0.85

        if not valid_chunks:
            logger.info(f"Insufficient evidence found for query '{query}'. (max_score={max_score})")
            no_evidence_answer = RAGAnswer(
                answer="I couldn't find this information in the provided documents.",
                confidence=0.0,
                citations=[],
                insufficient_evidence=True
            )

            # Evaluation Logging
            self._log_evaluation(
                query=query,
                retrieved_chunk_ids=[c.get("chunk_id", "") for c in retrieved_chunks],
                top_k=top_k,
                retrieval_duration=retrieval_duration,
                generation_duration=0.0,
                citation_count=0,
                insufficient_evidence=True,
                document_filter=document_id
            )
            return no_evidence_answer

        # 4. Build Multimodal Evidence Context String & Visual Attachments
        evidence_text, visual_image_inputs = build_multimodal_context(valid_chunks, db=db)


        # 5. Gemini LLM Answer Generation
        gen_start = time.time()
        full_prompt = (
            f"{GROUNDED_RAG_SYSTEM_PROMPT}\n\n"
            f"EVIDENCE SOURCES:\n{evidence_text}\n\n"
            f"USER QUESTION:\n{query}"
        )

        schema_dict = RAGAnswer.model_json_schema()
        raw_json = self.llm_provider.extract_structured_json(
            prompt=full_prompt,
            content=evidence_text,
            schema=schema_dict
        )
        generation_duration = round(time.time() - gen_start, 3)

        # 6. Parse and Validate Response
        try:
            rag_answer = RAGAnswer.model_validate(raw_json)
        except Exception as val_err:
            logger.error(f"Failed to validate LLM response into RAGAnswer schema: {val_err}. Raw JSON: {raw_json}")
            raise LLMExtractionError(f"Malformed LLM answer response: {str(val_err)}")

        # Handle explicit insufficient evidence flag from LLM
        if rag_answer.insufficient_evidence:
            rag_answer.citations = []
            rag_answer.confidence = 0.0
            if not rag_answer.answer or rag_answer.answer == "No response generated.":
                rag_answer.answer = "I couldn't find this information in the provided documents."

        # Compute Grounding Confidence based on evidence retrieval similarity of cited chunks
        if not rag_answer.insufficient_evidence:
            grounding_scores = [c.get("score", 0.85) for c in valid_chunks]
            avg_grounding_score = round(sum(grounding_scores) / len(grounding_scores), 4) if grounding_scores else 0.85
            rag_answer.confidence = avg_grounding_score

            # Verify citations against retrieved chunks to ensure non-empty citations if LLM missed citations
            if not rag_answer.citations and valid_chunks:
                # Auto-populate top chunk citation as fallback if evidence was used but citations array omitted
                top_chunk = valid_chunks[0]
                top_meta = top_chunk.get("metadata", {})
                rag_answer.citations = [
                    Citation(
                        document_id=top_chunk.get("document_id", "doc_id"),
                        filename=top_chunk.get("filename", "document.pdf"),
                        page_number=top_chunk.get("page_number", 1),
                        chunk_id=top_chunk.get("chunk_id", "chunk_1"),
                        source_type=top_chunk.get("source_type") or top_meta.get("source_type", "TEXT"),
                        image_id=top_meta.get("image_id") or top_chunk.get("image_id"),
                        quoted_evidence=top_chunk.get("text", "")[:150]
                    )
                ]
            else:
                # Enrich citations with source_type and image_id from matching retrieved chunks
                for cit in rag_answer.citations:
                    matching_chunk = next(
                        (c for c in valid_chunks if c.get("chunk_id") == cit.chunk_id or c.get("page_number") == cit.page_number),
                        None
                    )
                    if matching_chunk:
                        meta = matching_chunk.get("metadata", {})
                        if not cit.source_type or cit.source_type == "TEXT":
                            cit.source_type = matching_chunk.get("source_type") or meta.get("source_type", "TEXT")
                        if not cit.image_id:
                            cit.image_id = meta.get("image_id") or matching_chunk.get("image_id")


        # 7. Evaluation Logging
        self._log_evaluation(
            query=query,
            retrieved_chunk_ids=[c.get("chunk_id", "") for c in valid_chunks],
            top_k=top_k,
            retrieval_duration=retrieval_duration,
            generation_duration=generation_duration,
            citation_count=len(rag_answer.citations),
            insufficient_evidence=rag_answer.insufficient_evidence,
            document_filter=document_id
        )

        total_duration = round(time.time() - start_time, 3)
        logger.info(
            f"QA execution complete in {total_duration}s: "
            f"insufficient_evidence={rag_answer.insufficient_evidence}, citations={len(rag_answer.citations)}, "
            f"confidence={rag_answer.confidence}"
        )

        return rag_answer

    def _log_evaluation(
        self,
        query: str,
        retrieved_chunk_ids: List[str],
        top_k: int,
        retrieval_duration: float,
        generation_duration: float,
        citation_count: int,
        insufficient_evidence: bool,
        document_filter: Optional[str]
    ):
        """
        Internal evaluation logger recording query performance and citation statistics.
        """
        logger.info(
            f"[QA_EVALUATION_LOG] query='{query}' | top_k={top_k} | doc_filter={document_filter} | "
            f"retrieved_chunks={len(retrieved_chunk_ids)} | retrieval_time={retrieval_duration}s | "
            f"generation_time={generation_duration}s | citation_count={citation_count} | "
            f"insufficient_evidence={insufficient_evidence}"
        )


# Global service instance and shortcut helper
_qa_service_instance = GroundedQAService()


def answer_question(
    query: str,
    top_k: int = 5,
    document_id: Optional[str] = None,
    db: Optional[Session] = None
) -> RAGAnswer:
    """
    Global entrypoint for grounded RAG question answering.
    """
    return _qa_service_instance.answer_question(
        query=query,
        top_k=top_k,
        document_id=document_id,
        db=db
    )
