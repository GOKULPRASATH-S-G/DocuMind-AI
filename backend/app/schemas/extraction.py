from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class LineItem(BaseModel):
    description: Optional[str] = None
    quantity: Optional[float] = None
    unit_price: Optional[float] = None
    amount: Optional[float] = None


class InvoiceExtraction(BaseModel):
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    vendor_name: Optional[str] = None
    customer_name: Optional[str] = None
    currency: Optional[str] = None
    line_items: List[LineItem] = Field(default_factory=list)
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total_amount: Optional[float] = None
    due_date: Optional[str] = None


class GeneralDocumentExtraction(BaseModel):
    document_title: Optional[str] = Field(default=None, description="Title or header of the document")
    document_type: Optional[str] = Field(default="General Document", description="Category e.g. Patent, Report, Manual, Invoice, Contract")
    author_or_organization: Optional[str] = Field(default=None, description="Author, organization, applicant, or publisher")
    date: Optional[str] = Field(default=None, description="Document date if mentioned")
    summary: Optional[str] = Field(default=None, description="Concise multi-sentence summary of document contents")
    key_topics: List[str] = Field(default_factory=list, description="Primary topics or subjects discussed")
    key_entities: List[str] = Field(default_factory=list, description="Key names, organizations, or identifiers")
    key_value_metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional key metadata extracted from document")


class FieldConfidenceDetailSchema(BaseModel):
    field_name: str
    value: Any
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    is_valid: bool
    validation_error: Optional[str] = None
    validation_warning: Optional[str] = None
    source: str = "TEXT"
    c_source: float = 1.0
    c_validation: float = 1.0
    c_format: float = 1.0
    c_llm: float = 0.8


class StructuredExtractionResponse(BaseModel):
    document_id: str
    status: str  # "APPROVED" or "NEEDS_REVIEW"
    extraction_type: str = "general_document"
    model: str
    overall_confidence: float
    requires_human_review: bool
    data: Any  # GeneralDocumentExtraction or InvoiceExtraction
    fields: Dict[str, FieldConfidenceDetailSchema]
    hard_errors: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[Dict[str, Any]] = Field(default_factory=list)


class ExtractionResultSchema(BaseModel):
    document_id: str
    overall_confidence: float
    requires_human_review: bool
    fields: Dict[str, FieldConfidenceDetailSchema]
    extracted_tables: List[Dict[str, Any]] = []
    validation_errors: List[Dict[str, Any]] = []
