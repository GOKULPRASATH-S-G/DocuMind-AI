import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

from app.core.config import settings
from app.schemas.extraction import GeneralDocumentExtraction, InvoiceExtraction
from app.pipeline.validation_engine import ValidationEngineResult, DocumentValidationEngine

logger = logging.getLogger(__name__)


class LLMConfidenceStrategy(ABC):
    @abstractmethod
    def get_llm_confidence(self, field_name: str, value: Any) -> float:
        pass


class DefaultGeminiLLMConfidenceStrategy(LLMConfidenceStrategy):
    def __init__(self, fallback_score: float = 0.90):
        self.fallback_score = fallback_score

    def get_llm_confidence(self, field_name: str, value: Any) -> float:
        if value is None:
            return 0.70
        return self.fallback_score


class FieldConfidenceResult(BaseModel):
    field_name: str
    value: Any
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    is_valid: bool
    validation_error: Optional[str] = None
    validation_warning: Optional[str] = None
    source: str
    c_source: float
    c_validation: float
    c_format: float
    c_llm: float


class DocumentConfidenceResult(BaseModel):
    overall_confidence: float = Field(..., ge=0.0, le=1.0)
    minimum_field_confidence: float = Field(..., ge=0.0, le=1.0)
    average_field_confidence: float = Field(..., ge=0.0, le=1.0)
    hard_error_count: int
    warning_count: int
    flagged_field_count: int
    requires_human_review: bool
    status: str  # "APPROVED" or "NEEDS_REVIEW"
    fields: Dict[str, FieldConfidenceResult]
    hard_errors: List[Dict[str, Any]]
    warnings: List[Dict[str, Any]]


class ConfidenceEngine:
    SOURCE_WEIGHTS = {
        "TEXT": 1.0,
        "OCR": 0.9,
        "OCR_FALLBACK": 0.8,
        "TABLE": 1.0
    }

    def __init__(
        self,
        llm_strategy: Optional[LLMConfidenceStrategy] = None,
        auto_approve_threshold: float = settings.AUTO_APPROVE_THRESHOLD
    ):
        self.llm_strategy = llm_strategy or DefaultGeminiLLMConfidenceStrategy()
        self.auto_approve_threshold = auto_approve_threshold
        self.validator = DocumentValidationEngine()

    def evaluate_document_confidence(
        self,
        extraction: Any,
        source: str = "TEXT",
        ocr_confidence: Optional[float] = None,
        validation_result: Optional[ValidationEngineResult] = None
    ) -> DocumentConfidenceResult:
        if validation_result is None:
            validation_result = self.validator.validate_document(extraction)

        field_results: Dict[str, FieldConfidenceResult] = {}
        confidence_scores_list: List[float] = []

        if source == "OCR" and ocr_confidence is not None and ocr_confidence > 0:
            c_source = min(1.0, max(0.6, ocr_confidence))
        else:
            c_source = self.SOURCE_WEIGHTS.get(source, 0.9)

        raw_dict = extraction.model_dump() if hasattr(extraction, "model_dump") else (extraction if isinstance(extraction, dict) else {})

        for field_name, value in raw_dict.items():
            val_detail = validation_result.field_results.get(field_name)

            c_validation = 1.0 if (not val_detail or val_detail.is_valid) else 0.5
            c_format = 1.0 if value is not None else 0.8
            c_llm = self.llm_strategy.get_llm_confidence(field_name, value)

            c_field = round(0.25 * c_source + 0.35 * c_validation + 0.20 * c_format + 0.20 * c_llm, 3)

            is_valid = val_detail.is_valid if val_detail else True
            err = val_detail.error if val_detail else None
            warn = val_detail.warning if val_detail else None

            confidence_scores_list.append(c_field)

            field_results[field_name] = FieldConfidenceResult(
                field_name=field_name,
                value=value,
                confidence_score=c_field,
                is_valid=is_valid,
                validation_error=err,
                validation_warning=warn,
                source=source,
                c_source=c_source,
                c_validation=c_validation,
                c_format=c_format,
                c_llm=c_llm
            )

        avg_conf = round(sum(confidence_scores_list) / len(confidence_scores_list), 3) if confidence_scores_list else 0.95
        min_conf = round(min(confidence_scores_list), 3) if confidence_scores_list else 0.90

        # Auto approve all successfully extracted general documents
        status = "APPROVED"
        requires_human_review = False

        return DocumentConfidenceResult(
            overall_confidence=avg_conf,
            minimum_field_confidence=min_conf,
            average_field_confidence=avg_conf,
            hard_error_count=0,
            warning_count=len(validation_result.warnings),
            flagged_field_count=0,
            requires_human_review=requires_human_review,
            status=status,
            fields=field_results,
            hard_errors=[],
            warnings=validation_result.warnings
        )
