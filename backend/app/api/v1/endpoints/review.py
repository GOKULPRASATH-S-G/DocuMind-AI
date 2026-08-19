from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.document import Document
from app.models.extracted_data import ExtractedData
from app.models.human_review import HumanReview
from app.models.chunk import DocumentChunk
from app.schemas.review import ReviewQueueResponse, ReviewQueueItem, HumanReviewSubmit
from app.schemas.document import DocumentDetailResponse
from app.pipeline.extractor_pymupdf import extract_native_text
from app.services.vector_store.chroma import ChromaVectorStoreProvider
from app.rag.chunker import chunk_document_pages

router = APIRouter()
vector_store = ChromaVectorStoreProvider()


@router.get("/queue", response_model=ReviewQueueResponse)
def get_review_queue(
    page: int = 1,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    query = db.query(Document).filter(Document.processing_status == "NEEDS_REVIEW")
    total = query.count()
    items = query.order_by(Document.uploaded_at.desc()).offset((page - 1) * limit).limit(limit).all()

    queue_items = []
    for doc in items:
        ext = db.query(ExtractedData).filter(ExtractedData.document_id == doc.id).first()
        err_count = len(ext.validation_errors) if ext and ext.validation_errors else 0
        queue_items.append(
            ReviewQueueItem(
                document_id=doc.id,
                filename=doc.filename,
                file_size=doc.file_size,
                processing_status=doc.processing_status,
                overall_confidence=doc.overall_confidence,
                flagged_fields_count=err_count,
                uploaded_at=doc.uploaded_at
            )
        )

    return ReviewQueueResponse(total=total, items=queue_items)


@router.post("/{document_id}/approve", response_model=DocumentDetailResponse)
def submit_human_review(
    document_id: str,
    payload: HumanReviewSubmit,
    db: Session = Depends(get_db)
):
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    ext = db.query(ExtractedData).filter(ExtractedData.document_id == document_id).first()
    original_fields = ext.validated_json if ext else {}

    # Save human review log
    review_entry = HumanReview(
        document_id=doc.id,
        reviewer_id="human_operator",
        original_fields=original_fields,
        corrected_fields=payload.corrected_fields,
        review_action=payload.action,
        notes=payload.reviewer_notes
    )
    db.add(review_entry)

    # Update extracted data with human corrections
    if ext:
        ext.validated_json = payload.corrected_fields
        ext.validation_errors = []
        # Human review sets all scores to 1.0
        if ext.field_confidence_scores:
            for k in ext.field_confidence_scores:
                ext.field_confidence_scores[k]["confidence_score"] = 1.0
                ext.field_confidence_scores[k]["is_valid"] = True
                ext.field_confidence_scores[k]["validation_error"] = None

    doc.processing_status = "APPROVED" if payload.action == "APPROVED" else "REJECTED"
    doc.overall_confidence = 1.0 if payload.action == "APPROVED" else doc.overall_confidence

    # Index into vector database if approved
    if payload.action == "APPROVED":
        pages_text = extract_native_text(doc.file_path)
        if not pages_text:
            pages_text = [{"page_number": 1, "text": str(payload.corrected_fields)}]

        chunks = chunk_document_pages(
            document_id=doc.id,
            document_name=doc.filename,
            pages_text=pages_text
        )
        vector_store.add_chunks(chunks)

        for c in chunks:
            chunk_obj = DocumentChunk(
                document_id=doc.id,
                page_number=c["page_number"],
                chunk_index=c["chunk_index"],
                chunk_text=c["chunk_text"],
                vector_id=c["id"]
            )
            db.add(chunk_obj)

    db.commit()
    db.refresh(doc)

    return DocumentDetailResponse(
        id=doc.id,
        filename=doc.filename,
        mime_type=doc.mime_type,
        file_size=doc.file_size,
        is_scanned=doc.is_scanned,
        processing_status=doc.processing_status,
        overall_confidence=doc.overall_confidence,
        uploaded_at=doc.uploaded_at,
        updated_at=doc.updated_at,
        extracted_data=ext.validated_json if ext else payload.corrected_fields,
        validation_errors=[],
        field_confidence_scores=ext.field_confidence_scores if ext else None
    )
