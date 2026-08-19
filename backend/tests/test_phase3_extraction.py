import pytest
from unittest.mock import MagicMock
from app.core.exceptions import LLMExtractionError, DocumentProcessingError
from app.pipeline.prompt_builder import format_normalized_document_for_llm, get_invoice_extraction_prompt
from app.schemas.extraction import InvoiceExtraction
from app.services.extraction_service import ExtractionService
from app.services.llm.base import BaseLLMProvider


def test_prompt_builder_metadata_preservation():
    """Requirement 7 & 8: Verify page/source metadata and table information formatting."""
    normalized_data = {
        "pages": [
            {"page_number": 1, "text": "Invoice #: INV-100\nVendor: ACME", "source": "TEXT"},
            {"page_number": 2, "text": "Scanned Image Text Total $500", "source": "OCR"}
        ],
        "tables": [
            {
                "page_number": 1,
                "table_index": 0,
                "headers": ["Item", "Qty", "Price", "Amount"],
                "rows": [["Widget A", "2", "50", "100"], ["Widget B", "1", "400", "400"]]
            }
        ]
    }

    formatted = format_normalized_document_for_llm(normalized_data)

    assert "--- PAGE 1 ---" in formatted
    assert "SOURCE: TEXT" in formatted
    assert "Invoice #: INV-100" in formatted
    assert "--- PAGE 2 ---" in formatted
    assert "SOURCE: OCR" in formatted
    assert "--- TABLE 1 (PAGE 1) ---" in formatted
    assert "Item | Qty | Price | Amount" in formatted
    assert "Widget A | 2 | 50 | 100" in formatted


def test_successful_mock_extraction(client, native_pdf_path, db_session):
    """Requirement 1: Test successful structured extraction using mocked LLM provider."""
    # 1. Upload and process native PDF
    with open(native_pdf_path, "rb") as f:
        up_res = client.post("/api/v1/documents/upload", files={"file": ("invoice_test.pdf", f, "application/pdf")})
    doc_id = up_res.json()["id"]
    client.post(f"/api/v1/documents/{doc_id}/process")

    # 2. Mock LLM Provider
    mock_llm = MagicMock(spec=BaseLLMProvider)
    mock_llm.model_name = "gemini-1.5-flash-mock"
    mock_llm.extract_structured_json.return_value = {
        "invoice_number": "INV-2026-001",
        "invoice_date": "2026-08-17",
        "vendor_name": "ACME Corporation",
        "customer_name": None,
        "currency": "USD",
        "line_items": [
            {"description": "Cloud Service", "quantity": 1.0, "unit_price": 1450.50, "amount": 1450.50}
        ],
        "subtotal": 1450.50,
        "tax": None,
        "total_amount": 1450.50,
        "due_date": None
    }

    service = ExtractionService(llm_provider=mock_llm)
    response = service.run_invoice_extraction(doc_id, db_session)
    assert response.document_id == doc_id
    assert response.extraction_type == "general_document"


def test_missing_fields_null():
    """Requirement 2: Verify missing fields remain null and do not fabricate data."""
    mock_llm = MagicMock(spec=BaseLLMProvider)
    mock_llm.model_name = "gemini-1.5-flash-mock"
    mock_llm.extract_structured_json.return_value = {
        "invoice_number": "INV-99",
        "total_amount": 100.0
    }

    # Verify Pydantic parses missing fields as None
    data = InvoiceExtraction.model_validate(mock_llm.extract_structured_json.return_value)
    assert data.invoice_number == "INV-99"
    assert data.vendor_name is None
    assert data.due_date is None
    assert data.line_items == []


def test_invalid_json_handling():
    """Requirement 3: Test invalid JSON handling by LLM provider."""
    from app.services.llm.gemini import GeminiLLMProvider
    provider = GeminiLLMProvider(api_key="mock_key")

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "This is malformed non-JSON output from LLM."
    mock_client.models.generate_content.return_value = mock_response
    provider._genai_client = mock_client
    provider._legacy_model = None

    with pytest.raises(LLMExtractionError) as exc_info:
        provider.extract_structured_json("prompt", "content", {})

    assert "not valid JSON" in str(exc_info.value)


def test_schema_validation_failure(client, native_pdf_path, db_session):
    """Requirement 4: Test schema validation failure when LLM returns incompatible data type."""
    with open(native_pdf_path, "rb") as f:
        up_res = client.post("/api/v1/documents/upload", files={"file": ("invoice_test.pdf", f, "application/pdf")})
    doc_id = up_res.json()["id"]
    client.post(f"/api/v1/documents/{doc_id}/process")

    mock_llm = MagicMock(spec=BaseLLMProvider)
    mock_llm.model_name = "gemini-1.5-flash-mock"
    # total_amount expecting float but passed invalid dictionary
    mock_llm.extract_structured_json.return_value = {
        "invoice_number": "INV-100",
        "total_amount": {"invalid_nested": "dict"}
    }

    service = ExtractionService(llm_provider=mock_llm)
    with pytest.raises(LLMExtractionError) as exc:
        service.run_invoice_extraction(doc_id, db_session)
    assert "validation failed" in str(exc.value).lower()


def test_gemini_api_failure():
    """Requirement 5: Test Gemini API error handling when API call fails."""
    from app.services.llm.gemini import GeminiLLMProvider
    provider = GeminiLLMProvider(api_key="mock_key")

    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("Gemini 503 Service Unavailable")
    provider._genai_client = mock_client
    provider._legacy_model = None

    with pytest.raises(LLMExtractionError) as exc_info:
        provider.extract_structured_json("prompt", "content", {})

    assert "Gemini API call failed" in str(exc_info.value)


def test_empty_document_error():
    """Requirement 6: Test extraction error on empty document content."""
    from app.services.llm.gemini import GeminiLLMProvider
    provider = GeminiLLMProvider(api_key="mock_key")

    with pytest.raises(LLMExtractionError) as exc_info:
        provider.extract_structured_json("prompt", "   ", {})

    assert "content is empty" in str(exc_info.value)
