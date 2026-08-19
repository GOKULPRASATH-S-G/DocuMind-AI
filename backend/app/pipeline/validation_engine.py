import re
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
from app.schemas.extraction import GeneralDocumentExtraction, InvoiceExtraction

logger = logging.getLogger(__name__)


class FieldValidationDetail(BaseModel):
    is_valid: bool
    error: Optional[str] = None
    warning: Optional[str] = None
    rule_id: Optional[str] = None


class ValidationEngineResult(BaseModel):
    is_valid: bool
    hard_errors: List[Dict[str, Any]]
    warnings: List[Dict[str, Any]]
    field_results: Dict[str, FieldValidationDetail]


class DocumentValidationEngine:
    """
    Universal Document Validation Engine.
    Validates general document fields (Title, Type, Summary, Topics) smoothly for all PDF types.
    Does NOT throw hard errors for missing invoice fields.
    """

    def validate_document(self, extraction: Any) -> ValidationEngineResult:
        hard_errors: List[Dict[str, Any]] = []
        warnings: List[Dict[str, Any]] = []
        field_results: Dict[str, FieldValidationDetail] = {}

        if isinstance(extraction, GeneralDocumentExtraction):
            for field_name in GeneralDocumentExtraction.model_fields.keys():
                field_results[field_name] = FieldValidationDetail(is_valid=True)

            if not extraction.document_title:
                warnings.append({"field": "document_title", "message": "Document title not explicitly detected.", "rule": "TITLE_MISSING"})

            if not extraction.summary:
                warnings.append({"field": "summary", "message": "Summary is empty.", "rule": "SUMMARY_MISSING"})

        elif isinstance(extraction, InvoiceExtraction):
            for field_name in InvoiceExtraction.model_fields.keys():
                field_results[field_name] = FieldValidationDetail(is_valid=True)
            # Legacy invoice schema without hard error blocking
            if not extraction.invoice_number:
                warnings.append({"field": "invoice_number", "message": "Invoice number missing.", "rule": "OPTIONAL_MISSING"})
        else:
            # Flexible dict or object
            fields = getattr(extraction, "model_fields", {}).keys() if hasattr(extraction, "model_fields") else extraction.keys() if isinstance(extraction, dict) else []
            for f in fields:
                field_results[f] = FieldValidationDetail(is_valid=True)

        return ValidationEngineResult(
            is_valid=True,
            hard_errors=hard_errors,
            warnings=warnings,
            field_results=field_results
        )


class InvoiceValidationEngine(DocumentValidationEngine):
    """
    Backwards-compatible Validation Engine.
    """
    def validate_invoice(self, extraction: Any) -> ValidationEngineResult:
        return self.validate_document(extraction)
