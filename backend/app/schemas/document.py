from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict


class DocumentBase(BaseModel):
    filename: str
    mime_type: str
    file_size: int


class DocumentCreate(DocumentBase):
    file_path: str


class DocumentResponse(DocumentBase):
    id: str
    is_scanned: bool
    processing_status: str
    overall_confidence: float
    error_message: Optional[str] = None
    uploaded_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentDetailResponse(DocumentResponse):
    extracted_data: Optional[Dict[str, Any]] = None
    validation_errors: Optional[List[Dict[str, Any]]] = None
    field_confidence_scores: Optional[Dict[str, Any]] = None
