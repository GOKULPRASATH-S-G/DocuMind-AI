import pytest
from unittest.mock import MagicMock
from app.services.extraction_service import ExtractionService
from app.services.llm.base import BaseLLMProvider


@pytest.fixture
def sample_review_document(client, native_pdf_path, db_session):
    """Creates a processed document in NEEDS_REVIEW status with a hard total mismatch error."""
    with open(native_pdf_path, "rb") as f:
        up_res = client.post("/api/v1/documents/upload", files={"file": ("review_test.pdf", f, "application/pdf")})
    doc_id = up_res.json()["id"]
    client.post(f"/api/v1/documents/{doc_id}/process")

    # Mock invalid extraction (subtotal 100 + tax 10 != total 999)
    mock_llm = MagicMock(spec=BaseLLMProvider)
    mock_llm.model_name = "gemini-3.6-flash-mock"
    mock_llm.extract_structured_json.return_value = {
        "invoice_number": "INV-TEST-55",
        "invoice_date": "2026-08-17",
        "vendor_name": "Review Test Vendor Inc",
        "customer_name": "Test Customer",
        "currency": "USD",
        "line_items": [{"description": "Item A", "quantity": 2.0, "unit_price": 50.0, "amount": 100.0}],
        "subtotal": 100.0,
        "tax": 10.0,
        "total_amount": 999.0,  # Invalid total mismatch
        "due_date": "2026-09-17"
    }

    service = ExtractionService(llm_provider=mock_llm)
    service.run_invoice_extraction(doc_id, db_session)
    return doc_id


def test_review_queue_retrieval(client, sample_review_document):
    """Test 1: GET /api/v1/reviews queue retrieval with status filter & pagination."""
    res = client.get("/api/v1/reviews?status=NEEDS_REVIEW&page=1&page_size=10")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    assert any(item["document_id"] == sample_review_document for item in data["items"])


def test_review_detail_retrieval(client, sample_review_document):
    """Test 2: GET /api/v1/reviews/{id} review detail retrieval."""
    res = client.get(f"/api/v1/reviews/{sample_review_document}")
    assert res.status_code == 200
    data = res.json()
    assert data["document_id"] == sample_review_document
    assert data["status"] == "NEEDS_REVIEW"
    assert len(data["hard_errors"]) > 0


def test_invalid_field_edit(client, sample_review_document):
    """Test 3: PATCH /api/v1/reviews/{id}/fields fails when field name is invalid."""
    res = client.patch(
        f"/api/v1/reviews/{sample_review_document}/fields",
        json={"field": "invalid_non_existent_field", "value": 123}
    )
    assert res.status_code == 400
    assert "not a valid schema field" in res.json()["detail"]


def test_approval_blocked_by_hard_errors(client, sample_review_document):
    """Test 4: POST /api/v1/reviews/{id}/approve is BLOCKED when hard validation errors exist."""
    res = client.post(f"/api/v1/reviews/{sample_review_document}/approve")
    assert res.status_code == 400
    assert "blocking validation errors" in res.json()["detail"].lower()


def test_field_edit_and_successful_approval(client, sample_review_document):
    """Test 5 & 6: Field edit fixes total_amount (subtotal 100 + tax 10 = 110) and permits approval."""
    # 1. Edit total_amount to 110.0
    edit_res = client.patch(
        f"/api/v1/reviews/{sample_review_document}/fields",
        json={"field": "total_amount", "value": 110.0}
    )
    assert edit_res.status_code == 200
    assert edit_res.json()["data"]["total_amount"] == 110.0
    assert len(edit_res.json()["hard_errors"]) == 0

    # 2. Approve Document
    appr_res = client.post(f"/api/v1/reviews/{sample_review_document}/approve")
    assert appr_res.status_code == 200
    assert appr_res.json()["status"] in ["APPROVED", "INDEXED"]
    assert appr_res.json()["requires_human_review"] is False

    # 3. Verify Review History Audit Trail
    detail = client.get(f"/api/v1/reviews/{sample_review_document}").json()
    actions = [h["action"] for h in detail["history"]]
    assert "FIELD_EDITED" in actions
    assert "APPROVED" in actions


def test_review_rejection(client, sample_review_document):
    """Test 7: POST /api/v1/reviews/{id}/reject rejects document and records reason."""
    res = client.post(
        f"/api/v1/reviews/{sample_review_document}/reject",
        json={"reason": "Unreadable blurred invoice document"}
    )
    assert res.status_code == 200
    assert res.json()["status"] == "REJECTED"

    # Verify history
    detail = client.get(f"/api/v1/reviews/{sample_review_document}").json()
    assert detail["history"][0]["action"] == "REJECTED"
    assert "Unreadable blurred" in detail["history"][0]["reason"]
