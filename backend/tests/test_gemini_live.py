import os
import pytest
from app.core.config import settings
from app.schemas.extraction import InvoiceExtraction
from app.services.llm.gemini import GeminiLLMProvider
from app.pipeline.prompt_builder import get_invoice_extraction_prompt


@pytest.mark.skipif(
    not settings.GEMINI_API_KEY or settings.GEMINI_API_KEY == "your-gemini-api-key-here",
    reason="GEMINI_API_KEY is not configured in .env. Skipping live Gemini API test."
)
def test_live_gemini_extraction():
    """Requirement 12: Manual/Integration test executing live Gemini API call when API key is provided."""
    provider = GeminiLLMProvider()
    schema_dict = InvoiceExtraction.model_json_schema()
    prompt = get_invoice_extraction_prompt(schema_dict)

    sample_doc_content = """
    --- PAGE 1 ---
    SOURCE: TEXT

    ACME TECHNOLOGIES INC.
    123 Tech Way, Silicon Valley, CA
    INVOICE #: INV-2026-995
    Date: 2026-08-15
    Customer: Enterprise Solutions LLC

    --- TABLE 1 (PAGE 1) ---
    SOURCE: TABLE

    Description | Quantity | Unit Price | Amount
    Cloud AI Integration | 1 | 5000.00 | 5000.00
    OCR License | 2 | 250.00 | 500.00

    Subtotal: $5500.00
    Tax (10%): $550.00
    Total Amount Due: $6050.00
    Due Date: 2026-09-15
    """

    raw_json = provider.extract_structured_json(prompt, sample_doc_content, schema_dict)
    assert isinstance(raw_json, dict)

    validated = InvoiceExtraction.model_validate(raw_json)
    assert validated.invoice_number == "INV-2026-995"
    assert validated.vendor_name is not None
    assert validated.total_amount == 6050.00
    assert len(validated.line_items) == 2
