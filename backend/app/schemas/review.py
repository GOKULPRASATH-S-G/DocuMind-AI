from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field
from app.schemas.extraction import FieldConfidenceDetailSchema, InvoiceExtraction


class ReviewQueueItemSchema(BaseModel):
    review_id: str
    document_id: str
    filename: str
    status: str
    overall_confidence: float
    flagged_fields: int
    created_at: datetime


class ReviewQueuePaginatedResponse(BaseModel):
    items: List[ReviewQueueItemSchema]
    total: int
    page: int
    page_size: int


class ReviewHistoryItemSchema(BaseModel):
    id: str
    action: str
    field_name: Optional[str] = None
    old_value: Optional[Any] = None
    new_value: Optional[Any] = None
    reviewer_id: str
    reason: Optional[str] = None
    reviewed_at: datetime


class ReviewDetailResponse(BaseModel):
    review_id: str
    document_id: str
    filename: str
    mime_type: str
    status: str
    overall_confidence: float
    requires_human_review: bool
    data: InvoiceExtraction
    fields: Dict[str, FieldConfidenceDetailSchema]
    hard_errors: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[Dict[str, Any]] = Field(default_factory=list)
    history: List[ReviewHistoryItemSchema] = Field(default_factory=list)


class FieldEditRequest(BaseModel):
    field: str
    value: Any


class ReviewRejectRequest(BaseModel):
    reason: str


# Legacy Schema Aliases for backward compatibility
class ReviewQueueItem(BaseModel):
    document_id: str
    filename: str
    overall_confidence: float
    flagged_fields_count: int
    uploaded_at: datetime


class ReviewQueueResponse(BaseModel):
    items: List[ReviewQueueItem]


class HumanReviewSubmit(BaseModel):
    corrected_fields: Dict[str, Any]
    reviewer_notes: Optional[str] = None
    action: str = "APPROVED"
