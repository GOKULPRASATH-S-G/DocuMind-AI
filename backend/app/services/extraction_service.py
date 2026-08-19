import time
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import LLMExtractionError, DocumentProcessingError
from app.models.document import Document
from app.models.extracted_data import ExtractedData
from app.pipeline.prompt_builder import format_normalized_document_for_llm, get_general_document_extraction_prompt
from app.pipeline.validation_engine import DocumentValidationEngine
from app.pipeline.confidence_engine import ConfidenceEngine
from app.schemas.extraction import (
    GeneralDocumentExtraction,
    StructuredExtractionResponse,
    FieldConfidenceDetailSchema
)
from app.services.llm.base import BaseLLMProvider
from app.services.llm.gemini import GeminiLLMProvider

logger = logging.getLogger(__name__)


class ExtractionService:
    def __init__(
        self,
        llm_provider: Optional[BaseLLMProvider] = None,
        confidence_engine: Optional[ConfidenceEngine] = None
    ):
        self.llm_provider = llm_provider or GeminiLLMProvider()
        self.confidence_engine = confidence_engine or ConfidenceEngine()
        self.validation_engine = DocumentValidationEngine()

    def run_invoice_extraction(self, document_id: str, db: Session) -> StructuredExtractionResponse:
        return self.run_document_extraction(document_id, db)

    def run_document_extraction(self, document_id: str, db: Session) -> StructuredExtractionResponse:
        """
        Orchestrates Universal Document LLM extraction & auto-approval for vector indexing:
        1. Fetch document record & normalized Phase 2 content.
        2. Format source-aware prompt & execute Gemini LLM call using GeneralDocumentExtraction schema.
        3. Evaluate confidence & mark APPROVED.
        4. Auto-index into ChromaDB vector store.
        """
        start_time = time.time()
        logger.info(f"Initiating universal document intelligence & summary extraction for document_id: {document_id}")

        doc_record = db.query(Document).filter(Document.id == document_id).first()
        if not doc_record:
            raise DocumentProcessingError(f"Document ID '{document_id}' not found.")

        if doc_record.processing_status == "UPLOADED":
            raise DocumentProcessingError(
                f"Document '{document_id}' has not been processed yet. Run document processing before triggering extraction."
            )

        ext_record = db.query(ExtractedData).filter(ExtractedData.document_id == document_id).first()
        if not ext_record or not ext_record.raw_llm_json:
            raise DocumentProcessingError(f"Normalized extraction data for document '{document_id}' is missing.")

        normalized_data = ext_record.raw_llm_json

        pages = normalized_data.get("pages", [])
        primary_source = "TEXT"
        ocr_confidence_sum = 0.0
        ocr_page_count = 0

        for pg in pages:
            if pg.get("source") == "OCR":
                primary_source = "OCR"
                ocr_page_count += 1
                ocr_confidence_sum += pg.get("confidence", 0.9)

        avg_ocr_conf = (ocr_confidence_sum / ocr_page_count) if ocr_page_count > 0 else None

        formatted_content = format_normalized_document_for_llm(normalized_data)
        if not formatted_content.strip():
            raise LLMExtractionError(f"Document '{document_id}' contains no text content to extract.")

        # Gemini LLM Extraction
        schema_dict = GeneralDocumentExtraction.model_json_schema()
        prompt = get_general_document_extraction_prompt(schema_dict)

        raw_json = {}
        has_ocr_error = "Tesseract binary not found" in formatted_content or "missing OCR" in formatted_content or "Scanned page detected" in formatted_content
        is_image_file = doc_record.mime_type and doc_record.mime_type.startswith("image/")

        # If it's an image file or scanned page without local Tesseract OCR, use Gemini Multimodal Vision directly!
        if (has_ocr_error or is_image_file or doc_record.is_scanned) and hasattr(self.llm_provider, "analyze_image"):
            try:
                logger.info(f"Using Gemini Multimodal Vision directly for file {doc_record.filename} (mime={doc_record.mime_type})...")
                img_input = doc_record.file_path
                mime_t = doc_record.mime_type or "image/png"

                if not is_image_file and doc_record.file_path.lower().endswith(".pdf"):
                    from app.pipeline.pdf_to_image import convert_pdf_page_to_image_bytes
                    img_input = convert_pdf_page_to_image_bytes(doc_record.file_path, 1)
                    mime_t = "image/png"

                raw_json = self.llm_provider.analyze_image(
                    image_input=img_input,
                    prompt=f"{prompt}\nAnalyze this image/scanned document visually and output strict JSON matching the schema.",
                    mime_type=mime_t
                )
            except Exception as vis_err:
                logger.warning(f"Gemini Multimodal Vision direct extraction fallback: {vis_err}")

        if not raw_json or not isinstance(raw_json, dict) or not raw_json.get("summary"):
            try:
                raw_json = self.llm_provider.extract_structured_json(
                    prompt=prompt,
                    content=formatted_content,
                    schema=schema_dict
                )
            except Exception as llm_err:
                logger.warning(f"Structured LLM extraction failed for document {document_id}: {llm_err}. Using fallback summary.")
                first_page_text = pages[0].get("text", "") if pages else formatted_content[:500]
                raw_json = {
                    "document_title": doc_record.filename,
                    "document_type": "General Document",
                    "summary": first_page_text[:300] or "Document text ingested successfully.",
                    "key_topics": ["General"],
                    "key_entities": []
                }

        try:
            validated_model = GeneralDocumentExtraction.model_validate(raw_json)
        except Exception as val_err:
            logger.warning(f"GeneralDocumentExtraction validation fallback: {val_err}")
            validated_model = GeneralDocumentExtraction(
                document_title=raw_json.get("document_title") or doc_record.filename,
                document_type=raw_json.get("document_type") or "General Document",
                summary=raw_json.get("summary") or "Document processed.",
                key_topics=raw_json.get("key_topics") if isinstance(raw_json.get("key_topics"), list) else [],
                key_entities=raw_json.get("key_entities") if isinstance(raw_json.get("key_entities"), list) else []
            )

        validated_json = validated_model.model_dump()

        validation_result = self.validation_engine.validate_document(validated_model)

        confidence_result = self.confidence_engine.evaluate_document_confidence(
            extraction=validated_model,
            source=primary_source,
            ocr_confidence=avg_ocr_conf,
            validation_result=validation_result
        )

        model_name = getattr(self.llm_provider, "model_name", settings.GEMINI_MODEL)
        
        # Always set status to APPROVED for instant vector Q&A indexing
        doc_record.processing_status = "APPROVED"
        doc_record.overall_confidence = confidence_result.overall_confidence
        doc_record.error_message = None

        if not (ext_record.raw_llm_json and isinstance(ext_record.raw_llm_json, dict) and "pages" in ext_record.raw_llm_json):
            ext_record.raw_llm_json = raw_json
        ext_record.validated_json = validated_json
        ext_record.extraction_type = "general_document"
        ext_record.model_name = model_name
        ext_record.overall_confidence = confidence_result.overall_confidence
        ext_record.field_confidence_scores = {
            f_name: f_res.model_dump() for f_name, f_res in confidence_result.fields.items()
        }
        ext_record.validation_errors = []

        db.commit()
        db.refresh(doc_record)
        db.refresh(ext_record)

        # Auto-index into ChromaDB vector store for instant Q&A
        try:
            from app.rag.indexer import DocumentIndexer
            indexer = DocumentIndexer()
            indexer.index_document(document_id, db)
            logger.info(f"Auto-indexed document {document_id} into ChromaDB vector store.")
        except Exception as auto_idx_err:
            logger.warning(f"Auto-indexing notice for document {document_id}: {auto_idx_err}")

        duration = round(time.time() - start_time, 3)
        logger.info(f"Extraction & Indexing complete for {document_id}: duration={duration}s")

        response_fields = {
            f_name: FieldConfidenceDetailSchema(
                field_name=f_res.field_name,
                value=f_res.value,
                confidence_score=f_res.confidence_score,
                is_valid=f_res.is_valid,
                validation_error=f_res.validation_error,
                validation_warning=f_res.validation_warning,
                source=f_res.source,
                c_source=f_res.c_source,
                c_validation=f_res.c_validation,
                c_format=f_res.c_format,
                c_llm=f_res.c_llm
            ) for f_name, f_res in confidence_result.fields.items()
        }

        return StructuredExtractionResponse(
            document_id=document_id,
            status="APPROVED",
            extraction_type="general_document",
            model=model_name,
            overall_confidence=confidence_result.overall_confidence,
            requires_human_review=False,
            data=validated_model,
            fields=response_fields,
            hard_errors=[],
            warnings=confidence_result.warnings
        )
