import logging
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc

from app.db.session import get_db
from app.models.document import Document
from app.models.extracted_data import ExtractedData
from app.models.human_review import HumanReview
from app.models.user import User, UserRole
from app.models.audit import AuditLog
from app.api.v1.endpoints.auth import get_current_user
from app.pipeline.validation_engine import InvoiceValidationEngine
from app.pipeline.confidence_engine import ConfidenceEngine
from app.schemas.extraction import InvoiceExtraction, FieldConfidenceDetailSchema
from app.schemas.review import (
    ReviewQueuePaginatedResponse,
    ReviewQueueItemSchema,
    ReviewDetailResponse,
    ReviewHistoryItemSchema,
    FieldEditRequest,
    ReviewRejectRequest
)

logger = logging.getLogger(__name__)
router = APIRouter()

validation_engine = InvoiceValidationEngine()
confidence_engine = ConfidenceEngine()


@router.get("", response_model=ReviewQueuePaginatedResponse)
def get_review_queue(
    status: Optional[str] = Query(None, description="Status filter: NEEDS_REVIEW, APPROVED, REJECTED, or ALL"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: Optional[str] = Query("date_desc", description="Sorting: confidence_asc, confidence_desc, date_desc, date_asc"),
    db: Session = Depends(get_db)
):
    """
    1. REVIEW QUEUE ENDPOINT:
    Returns paginated list of documents requiring human review or filtered by status.
    """
    query = db.query(Document)

    if status and status.upper() != "ALL":
        query = query.filter(Document.processing_status == status.upper())

    # Apply sorting
    if sort_by == "confidence_asc":
        query = query.order_by(asc(Document.overall_confidence))
    elif sort_by == "confidence_desc":
        query = query.order_by(desc(Document.overall_confidence))
    elif sort_by == "date_asc":
        query = query.order_by(asc(Document.uploaded_at))
    else:
        query = query.order_by(desc(Document.uploaded_at))

    total = query.count()
    offset = (page - 1) * page_size
    documents = query.offset(offset).limit(page_size).all()

    items: List[ReviewQueueItemSchema] = []
    for doc in documents:
        ext_record = db.query(ExtractedData).filter(ExtractedData.document_id == doc.id).first()
        flagged_count = 0
        if ext_record and ext_record.field_confidence_scores:
            for _, f_data in ext_record.field_confidence_scores.items():
                if isinstance(f_data, dict) and (f_data.get("confidence_score", 1.0) < 0.85 or not f_data.get("is_valid", True)):
                    flagged_count += 1

        items.append(
            ReviewQueueItemSchema(
                review_id=doc.id,
                document_id=doc.id,
                filename=doc.filename,
                status=doc.processing_status,
                overall_confidence=doc.overall_confidence or 0.0,
                flagged_fields=flagged_count,
                created_at=doc.uploaded_at
            )
        )

    return ReviewQueuePaginatedResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/{review_id}", response_model=ReviewDetailResponse)
def get_review_detail(review_id: str, db: Session = Depends(get_db)):
    """
    2. REVIEW DETAIL ENDPOINT:
    Returns complete document review state, extracted fields, confidence scores, and audit history.
    """
    doc = db.query(Document).filter(Document.id == review_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Review/Document ID '{review_id}' not found.")

    ext_record = db.query(ExtractedData).filter(ExtractedData.document_id == doc.id).first()
    if not ext_record or not ext_record.validated_json:
        raise HTTPException(status_code=400, detail=f"Extracted data for document '{review_id}' is missing.")

    # Parse Pydantic extraction
    validated_model = InvoiceExtraction.model_validate(ext_record.validated_json)

    # Recalculate or load validation and confidence
    val_res = validation_engine.validate_invoice(validated_model)
    conf_res = confidence_engine.evaluate_document_confidence(validated_model, validation_result=val_res)

    # Load review history
    history_records = db.query(HumanReview).filter(HumanReview.document_id == doc.id).order_by(desc(HumanReview.reviewed_at)).all()
    history_items = [
        ReviewHistoryItemSchema(
            id=h.id,
            action=h.action or h.review_action,
            field_name=h.field_name,
            old_value=h.old_value,
            new_value=h.new_value,
            reviewer_id=h.reviewer_id,
            reason=h.reason or h.notes,
            reviewed_at=h.reviewed_at
        ) for h in history_records
    ]

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
        ) for f_name, f_res in conf_res.fields.items()
    }

    return ReviewDetailResponse(
        review_id=doc.id,
        document_id=doc.id,
        filename=doc.filename,
        mime_type=doc.mime_type,
        status=doc.processing_status,
        overall_confidence=conf_res.overall_confidence,
        requires_human_review=conf_res.requires_human_review,
        data=validated_model,
        fields=response_fields,
        hard_errors=conf_res.hard_errors,
        warnings=conf_res.warnings,
        history=history_items
    )


@router.patch("/{review_id}/fields", response_model=ReviewDetailResponse)
def update_review_field(
    review_id: str,
    payload: FieldEditRequest,
    db: Session = Depends(get_db)
):
    """
    3. FIELD EDIT ENDPOINT:
    Modifies an extracted field value, preserves audit history log, and re-evaluates validation rules.
    """
    doc = db.query(Document).filter(Document.id == review_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Review ID '{review_id}' not found.")

    ext_record = db.query(ExtractedData).filter(ExtractedData.document_id == doc.id).first()
    if not ext_record or not ext_record.validated_json:
        raise HTTPException(status_code=400, detail="Extracted data is missing.")

    # Validate field name exists in InvoiceExtraction schema
    if payload.field not in InvoiceExtraction.model_fields:
        raise HTTPException(
            status_code=400,
            detail=f"Field '{payload.field}' is not a valid schema field. Allowed fields: {', '.join(InvoiceExtraction.model_fields.keys())}"
        )

    current_data = dict(ext_record.validated_json)
    old_val = current_data.get(payload.field)
    new_val = payload.value

    # Update field value in dictionary
    current_data[payload.field] = new_val

    # Validate updated dictionary via Pydantic
    try:
        updated_model = InvoiceExtraction.model_validate(current_data)
    except Exception as err:
        raise HTTPException(status_code=400, detail=f"Invalid field value for '{payload.field}': {str(err)}")

    # Log audit history in HumanReview table
    history_record = HumanReview(
        document_id=doc.id,
        reviewer_id="human_operator",
        action="FIELD_EDITED",
        review_action="MODIFIED",
        field_name=payload.field,
        old_value={"val": old_val},
        new_value={"val": new_val},
        original_fields=ext_record.raw_llm_json or {},
        corrected_fields=current_data,
        notes=f"Updated field '{payload.field}' from {old_val} to {new_val}"
    )
    db.add(history_record)

    # Re-run deterministic validation & confidence calculation
    val_res = validation_engine.validate_invoice(updated_model)
    conf_res = confidence_engine.evaluate_document_confidence(updated_model, validation_result=val_res)

    # Update ext_record
    ext_record.validated_json = updated_model.model_dump()
    ext_record.overall_confidence = conf_res.overall_confidence
    ext_record.field_confidence_scores = {
        f_name: f_res.model_dump() for f_name, f_res in conf_res.fields.items()
    }
    ext_record.validation_errors = conf_res.hard_errors

    # If all hard errors are cleared and score >= 0.85, status updates to APPROVED automatically or stays in review until explicit approval
    doc.overall_confidence = conf_res.overall_confidence
    if conf_res.hard_error_count == 0 and conf_res.overall_confidence >= 0.85 and doc.processing_status == "NEEDS_REVIEW":
        doc.error_message = None

    db.commit()
    db.refresh(doc)
    db.refresh(ext_record)

    logger.info(f"Field '{payload.field}' updated for document {review_id} by human_operator.")
    return get_review_detail(review_id, db)


@router.post("/{review_id}/approve", response_model=ReviewDetailResponse)
def approve_review(
    review_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    4. REVIEW APPROVAL ENDPOINT:
    Requires REVIEWER or ADMIN role.
    Validates rules, checks for blocking hard errors, transitions document to APPROVED, and auto-indexes into ChromaDB.
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.REVIEWER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only REVIEWER and ADMIN users can approve documents."
        )

    doc = db.query(Document).filter(Document.id == review_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Review ID '{review_id}' not found.")

    ext_record = db.query(ExtractedData).filter(ExtractedData.document_id == doc.id).first()
    if not ext_record or not ext_record.validated_json:
        raise HTTPException(status_code=400, detail="Extracted data is missing.")

    validated_model = InvoiceExtraction.model_validate(ext_record.validated_json)
    val_res = validation_engine.validate_invoice(validated_model)

    if len(val_res.hard_errors) > 0:
        hard_msgs = [e.get("message", "Validation error") if isinstance(e, dict) else str(e) for e in val_res.hard_errors]
        raise HTTPException(
            status_code=400,
            detail=f"Cannot approve document with blocking validation errors: {'; '.join(hard_msgs)}"
        )

    # Log audit history
    history_record = HumanReview(
        document_id=doc.id,
        reviewer_id=current_user.id,
        action="APPROVED",
        review_action="APPROVED",
        original_fields=ext_record.raw_llm_json or {},
        corrected_fields=ext_record.validated_json or {},
        notes=f"Document approved by {current_user.email}"
    )
    db.add(history_record)

    ext_record.needs_review = False
    doc.processing_status = "APPROVED"
    doc.error_message = None
    db.commit()

    # Log Audit Event
    audit = AuditLog(
        user_id=current_user.id,
        action="DOCUMENT_APPROVED",
        document_id=doc.id,
        metadata_json={"reviewer": current_user.email}
    )
    db.add(audit)
    db.commit()

    # Auto-index into ChromaDB
    try:
        from app.rag.indexer import DocumentIndexer
        indexer = DocumentIndexer()
        indexer.index_document(doc.id, db)
        doc.processing_status = "INDEXED"
        db.commit()
    except Exception as idx_err:
        logger.warning(f"Auto-indexing warning during approval for document {doc.id}: {idx_err}")

    db.refresh(doc)
    logger.info(f"Document {review_id} approved and indexed successfully by {current_user.email}.")
    return get_review_detail(review_id, db)


@router.post("/{review_id}/reject", response_model=ReviewDetailResponse)
def reject_review(
    review_id: str,
    payload: ReviewRejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    5. REVIEW REJECTION ENDPOINT:
    Requires REVIEWER or ADMIN role. Transitions status to REJECTED.
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.REVIEWER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. Only REVIEWER and ADMIN users can reject documents."
        )

    doc = db.query(Document).filter(Document.id == review_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail=f"Review ID '{review_id}' not found.")

    ext_record = db.query(ExtractedData).filter(ExtractedData.document_id == doc.id).first()

    # Log audit history
    history_record = HumanReview(
        document_id=doc.id,
        reviewer_id=current_user.id,
        action="REJECTED",
        review_action="REJECTED",
        original_fields=ext_record.raw_llm_json if ext_record else {},
        corrected_fields=ext_record.validated_json if ext_record else {},
        notes=f"Rejection reason: {payload.reason}"
    )
    db.add(history_record)

    doc.processing_status = "REJECTED"
    doc.error_message = f"Rejection reason: {payload.reason}"
    if ext_record:
        ext_record.needs_review = False

    db.commit()

    # Log Audit Event
    audit = AuditLog(
        user_id=current_user.id,
        action="DOCUMENT_REJECTED",
        document_id=doc.id,
        metadata_json={"reason": payload.reason, "reviewer": current_user.email}
    )
    db.add(audit)
    db.commit()

    db.refresh(doc)
    logger.info(f"Document {review_id} rejected by {current_user.email}. Reason: {payload.reason}")
    return get_review_detail(review_id, db)
