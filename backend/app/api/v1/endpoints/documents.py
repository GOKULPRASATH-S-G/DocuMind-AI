import os
import shutil
import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Request, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.config import settings
from app.core.rate_limiter import upload_rate_limiter
from app.models.document import Document
from app.models.extracted_data import ExtractedData
from app.models.user import User, UserRole
from app.models.audit import AuditLog
from app.models.human_review import HumanReview
from app.models.visual_artifact import VisualArtifact
from app.api.v1.endpoints.auth import get_current_user
from app.schemas.document import DocumentResponse, DocumentDetailResponse
from app.schemas.extraction import StructuredExtractionResponse
from app.schemas.ingestion import (
    NormalizedExtractionResult,
    ExtractionSummary,
    PageExtractionResult,
    ExtractionSourceEnum,
    PageModeEnum,
    OCRBoundingBox
)
from app.services.storage.local import LocalStorageProvider
from app.services.ocr.tesseract import TesseractOCRProvider
from app.pipeline.text_detector import detect_page_modes
from app.pipeline.extractor_pymupdf import extract_native_page_text
from app.pipeline.pdf_to_image import convert_pdf_page_to_image_bytes
from app.pipeline.extractor_tables import extract_page_tables
from app.core.exceptions import DocumentProcessingError, OCRError, LLMExtractionError

logger = logging.getLogger(__name__)

router = APIRouter()
storage_provider = LocalStorageProvider()
ocr_provider = TesseractOCRProvider()

ALLOWED_MIME_TYPES = {
    "application/pdf": ".pdf",
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/tiff": ".tiff"
}

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tiff"}


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def upload_document(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    SECURE DOCUMENT UPLOAD ENDPOINT:
    - Rate limits uploads per client IP.
    - Validates file extension, magic bytes (%PDF-), and max file size.
    - Assigns owner_id and workspace_id.
    - Stores file securely using UUID directory path.
    - Queues document for processing.
    """
    upload_rate_limiter.check_rate_limit(request.client.host if request.client else "127.0.0.1")

    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename cannot be empty.")

    ext = os.path.splitext(file.filename)[1].lower()
    mime_type = file.content_type or ""

    if ext not in ALLOWED_EXTENSIONS:
        logger.warning(f"Upload rejected: Unsupported file extension {ext}")
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file extension '{ext}'. Allowed extensions: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
        )

    content = file.file.read()
    if len(content) == 0:
        logger.warning(f"Upload rejected: File {file.filename} is empty (0 bytes)")
        raise HTTPException(status_code=400, detail="Uploaded file is empty (0 bytes).")

    # Max File Size Security Check
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds maximum allowed limit of {settings.MAX_UPLOAD_SIZE_MB}MB."
        )

    # Magic Bytes Validation for PDF
    if ext == ".pdf" and not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="Invalid PDF file. Header signature missing %PDF-.")

    saved_path = storage_provider.save_file(file.filename, content)
    logger.info(f"File uploaded securely: {file.filename} saved to {saved_path} ({len(content)} bytes)")

    doc_record = Document(
        filename=file.filename,
        file_path=saved_path,
        mime_type=mime_type or ("application/pdf" if ext == ".pdf" else f"image/{ext.strip('.')}"),
        file_size=len(content),
        owner_id=current_user.id,
        workspace_id=current_user.workspace_id,
        processing_status="UPLOADED"
    )

    db.add(doc_record)
    db.commit()
    db.refresh(doc_record)

    # Log Audit Event
    audit = AuditLog(
        user_id=current_user.id,
        action="DOCUMENT_UPLOADED",
        document_id=doc_record.id,
        metadata_json={"filename": file.filename, "size": len(content)}
    )
    db.add(audit)
    db.commit()

    return doc_record


@router.get("", response_model=List[DocumentResponse])
def get_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    STRICT OWNERSHIP-ENFORCED DOCUMENT LISTING:
    - Every signed-in user can ONLY see their own uploaded documents.
    - Unauthenticated guest sessions can ONLY see guest uploaded documents.
    """
    return db.query(Document).filter(Document.owner_id == current_user.id).order_by(Document.uploaded_at.desc()).all()


@router.get("/{document_id}", response_model=DocumentDetailResponse)
def get_document_detail(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    OWNERSHIP-ENFORCED DOCUMENT DETAIL ENDPOINT.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found.")

    if current_user.role == UserRole.USER and doc.owner_id and doc.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied. You do not own this document.")

    return doc


@router.get("/{document_id}/file")
def download_document_file(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    SECURE PATH-TRAVERSAL PROTECTED FILE DOWNLOAD ENDPOINT.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found.")

    if current_user.role == UserRole.USER and doc.owner_id and doc.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied. You do not own this document.")

    if not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="File missing on server disk storage.")

    return FileResponse(
        path=doc.file_path,
        media_type=doc.mime_type or "application/pdf",
        filename=os.path.basename(doc.filename)
    )


@router.post("/{document_id}/process", response_model=NormalizedExtractionResult)
def process_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Phase 2 PROCESS ENDPOINT (Hybrid Native + OCR Page Ingestion):
    Performs per-page detection, native text, Tesseract OCR, visual artifact detection, and table extraction.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found.")

    if current_user.role == UserRole.USER and doc.owner_id and doc.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied.")

    doc.processing_status = "PROCESSING"
    db.commit()

    try:
        page_mode_results = detect_page_modes(doc.file_path)
        total_pages = len(page_mode_results)
        is_scanned_doc = all(p.mode == PageModeEnum.SCANNED_IMAGE for p in page_mode_results)
        doc.is_scanned = is_scanned_doc

        page_results = []
        full_text_list = []
        all_extracted_tables = []
        has_any_visual = False

        for page_det in page_mode_results:
            page_num = page_det.page_number
            mode = page_det.mode
            page_text = ""
            source_enum = ExtractionSourceEnum.TEXT
            ocr_boxes = []

            if mode == PageModeEnum.NATIVE_PDF:
                native_res = extract_native_page_text(doc.file_path, page_num)
                page_text = native_res.text if hasattr(native_res, 'text') else str(native_res)
                source_enum = ExtractionSourceEnum.TEXT
                
                # Hybrid pass ONLY if native page text is sparse/empty
                if len(page_text.strip()) < 30:
                    try:
                        img_bytes = convert_pdf_page_to_image_bytes(doc.file_path, page_num)
                        ocr_res = ocr_provider.extract_text_with_layout(img_bytes)
                        ocr_text = ocr_res.get("full_text", "").strip()
                        if ocr_text:
                            page_text = ocr_text
                            source_enum = ExtractionSourceEnum.OCR
                    except Exception as hy_err:
                        logger.debug(f"Hybrid OCR pass skipped on page {page_num}: {hy_err}")

            else:
                img_bytes = convert_pdf_page_to_image_bytes(doc.file_path, page_num)
                ocr_res = ocr_provider.extract_text_with_layout(img_bytes)
                page_text = ocr_res.get("full_text", "")
                source_enum = ExtractionSourceEnum.OCR

                for word in ocr_res.get("words", []):
                    ocr_boxes.append(OCRBoundingBox(
                        x=word.get("x", 0),
                        y=word.get("y", 0),
                        width=word.get("w", 0),
                        height=word.get("h", 0),
                        text=word.get("text", ""),
                        confidence=word.get("confidence", 1.0)
                    ))

            # Table extraction pass
            if mode == PageModeEnum.NATIVE_PDF:
                try:
                    page_tables = extract_page_tables(doc.file_path, page_num)
                    all_extracted_tables.extend(page_tables)
                except Exception as tbl_err:
                    logger.warning(f"Table extraction pass warning on page {page_num}: {tbl_err}")

            page_results.append(PageExtractionResult(
                page_number=page_num,
                text=page_text,
                source=source_enum,
                confidence=1.0 if mode == PageModeEnum.NATIVE_PDF else 0.85,
                boxes=ocr_boxes
            ))
            full_text_list.append(f"--- PAGE {page_num} ({mode.value}) ---\n{page_text}")

        summary = ExtractionSummary(
            document_id=doc.id,
            status="EXTRACTED",
            total_pages=total_pages,
            native_pages=sum(1 for p in page_mode_results if p.mode == PageModeEnum.NATIVE_PDF),
            ocr_pages=sum(1 for p in page_mode_results if p.mode == PageModeEnum.SCANNED_IMAGE),
            tables_found=len(all_extracted_tables)
        )

        # Persist normalized extracted text into ExtractedData for downstream Phase 3 LLM extraction
        ext_record = db.query(ExtractedData).filter(ExtractedData.document_id == doc.id).first()
        normalized_data_dump = {
            "document_id": doc.id,
            "filename": doc.filename,
            "pages": [p.model_dump() for p in page_results],
            "tables": [t.model_dump() for t in all_extracted_tables],
            "combined_full_text": "\n\n".join(full_text_list)
        }
        if not ext_record:
            ext_record = ExtractedData(
                document_id=doc.id,
                extraction_type="invoice",
                raw_llm_json=normalized_data_dump
            )
            db.add(ext_record)
        else:
            ext_record.raw_llm_json = normalized_data_dump

        doc.processing_status = "EXTRACTED"
        db.commit()

        return NormalizedExtractionResult(
            document_id=doc.id,
            filename=doc.filename,
            file_type=doc.mime_type,
            total_pages=total_pages,
            pages=page_results,
            tables=all_extracted_tables,
            summary=summary
        )
    except Exception as e:
        doc.processing_status = "FAILED"
        doc.failure_stage = "PROCESSING"
        doc.failure_reason = str(e)
        doc.failed_at = datetime.utcnow()
        db.commit()
        logger.error(f"Error processing document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Document processing failed: {str(e)}")


@router.post("/{document_id}/extract", response_model=StructuredExtractionResponse)
def extract_structured_data_endpoint(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Phase 3 & 4 GEMINI EXTRACTION & VALIDATION ENDPOINT.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found.")

    if current_user.role == UserRole.USER and doc.owner_id and doc.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied.")

    try:
        # Ensure Phase 2 process_document has run
        ext_record = db.query(ExtractedData).filter(ExtractedData.document_id == document_id).first()
        if doc.processing_status == "UPLOADED" or not ext_record or not ext_record.raw_llm_json:
            process_document(document_id, db, current_user)

        from app.services.extraction_service import ExtractionService
        service = ExtractionService()
        return service.run_invoice_extraction(document_id, db)
    except Exception as e:
        doc.processing_status = "FAILED"
        doc.failure_stage = "EXTRACTION"
        doc.failure_reason = str(e)
        doc.failed_at = datetime.utcnow()
        db.commit()
        logger.error(f"Error during structured extraction for doc {document_id}: {e}")
        error_detail = {
            "stage": "structured_extraction",
            "status": "failed",
            "error_code": type(e).__name__,
            "message": str(e)
        }
        raise HTTPException(status_code=500, detail=error_detail)


@router.post("/{document_id}/index")
def index_document_endpoint(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Phase 6 DOCUMENT INDEXING ENDPOINT:
    - IDEMPOTENT: Removes existing vector chunks for document_id before inserting new vectors.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found.")

    if current_user.role == UserRole.USER and doc.owner_id and doc.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied.")

    from app.rag.indexer import DocumentIndexer
    indexer = DocumentIndexer()

    try:
        res = indexer.index_document(document_id, db)
        return res
    except (ValueError, DocumentProcessingError, LLMExtractionError) as ve:
        logger.warning(f"Indexing validation rejected for document {document_id}: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error indexing document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Document indexing failed: {str(e)}")


@router.get("/{document_id}/images/{image_id}")
def stream_visual_artifact_image(
    document_id: str,
    image_id: str,
    db: Session = Depends(get_db)
):
    """
    Streams visual artifact image file.
    """
    from pathlib import Path
    va = db.query(VisualArtifact).filter(
        VisualArtifact.document_id == document_id,
        VisualArtifact.image_id == image_id
    ).first()

    if not va or not va.storage_reference:
        raise HTTPException(status_code=404, detail=f"Visual artifact '{image_id}' not found.")

    file_path = Path(settings.STORAGE_LOCAL_DIR) / va.storage_reference
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Visual artifact image file missing.")

    return FileResponse(path=str(file_path), media_type=va.mime_type or "image/png", filename=f"{image_id}.png")


@router.delete("/{document_id}", status_code=status.HTTP_200_OK)
def delete_single_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    SECURE CASCADE DOCUMENT DELETION ENDPOINT:
    - Enforces ownership (USER can delete own documents, ADMIN can delete any).
    - Deletes database records (HumanReview, VisualArtifact, ExtractedData, DocumentChunk, DocumentIndex, Document).
    - Deletes ChromaDB vector chunks.
    - Deletes stored PDF and visual artifact image files.
    - Creates AUDIT LOG event DOCUMENT_DELETED.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found.")

    if current_user.role == UserRole.USER and doc.owner_id and doc.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied. You do not own this document.")

    try:
        # Delete DB records
        db.query(HumanReview).filter(HumanReview.document_id == document_id).delete()
        db.query(VisualArtifact).filter(VisualArtifact.document_id == document_id).delete()
        db.query(ExtractedData).filter(ExtractedData.document_id == document_id).delete()
        db.delete(doc)
        db.commit()

        # Delete ChromaDB chunks for document
        try:
            from app.rag.vector_store.chroma import ChromaVectorStoreProvider
            vector_store = ChromaVectorStoreProvider()
            vector_store.delete_document_chunks(document_id)
        except Exception as c_err:
            logger.warning(f"ChromaDB deletion warning for document {document_id}: {c_err}")

        # Delete document storage directory
        doc_storage_dir = os.path.join(settings.STORAGE_LOCAL_DIR, "documents", document_id)
        if os.path.exists(doc_storage_dir):
            try:
                shutil.rmtree(doc_storage_dir)
            except Exception as d_err:
                logger.warning(f"Failed to delete storage directory for doc {document_id}: {d_err}")

        # Log Audit Event
        audit = AuditLog(
            user_id=current_user.id,
            action="DOCUMENT_DELETED",
            document_id=document_id,
            metadata_json={"filename": doc.filename}
        )
        db.add(audit)
        db.commit()

        return {"message": f"Document '{document_id}' and all associated artifacts deleted successfully."}
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting document {document_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")
