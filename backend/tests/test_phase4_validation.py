import pytest
from app.pipeline.validation_engine import DocumentValidationEngine
from app.pipeline.confidence_engine import ConfidenceEngine
from app.schemas.extraction import GeneralDocumentExtraction, InvoiceExtraction, LineItem


@pytest.fixture
def valid_doc_data():
    return GeneralDocumentExtraction(
        document_title="AI Medical Diagnosis Patent",
        document_type="Patent Specification",
        author_or_organization="Bannari Amman Institute of Technology",
        date="2026-08-17",
        summary="An AI-based system for medical image analysis and early disease detection.",
        key_topics=["Medical Imaging", "AI", "Disease Detection"],
        key_entities=["Patent Form 2", "India"]
    )


def test_valid_document_auto_approval(valid_doc_data):
    engine = ConfidenceEngine()
    result = engine.evaluate_document_confidence(valid_doc_data, source="TEXT")

    assert result.status == "APPROVED"
    assert result.requires_human_review is False
    assert result.overall_confidence >= 0.85
    assert result.hard_error_count == 0


def test_universal_document_validation(valid_doc_data):
    validator = DocumentValidationEngine()
    result = validator.validate_document(valid_doc_data)

    assert result.is_valid is True
    assert len(result.hard_errors) == 0


def test_source_confidence_weights(valid_doc_data):
    engine = ConfidenceEngine()

    res_native = engine.evaluate_document_confidence(valid_doc_data, source="TEXT")
    res_ocr = engine.evaluate_document_confidence(valid_doc_data, source="OCR", ocr_confidence=0.80)

    assert res_native.fields["document_title"].c_source == 1.0
    assert res_ocr.fields["document_title"].c_source == 0.80
    assert res_native.overall_confidence > res_ocr.overall_confidence
