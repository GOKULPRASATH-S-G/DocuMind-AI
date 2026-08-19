import pytest
from unittest.mock import MagicMock
from app.rag.qa_service import GroundedQAService
from app.schemas.qa import RAGAnswer, Citation, QAQuery
from app.core.exceptions import LLMExtractionError
from app.models.document import Document
from tests.conftest import TestingSessionLocal


@pytest.fixture
def mock_retriever():
    retriever = MagicMock()
    retriever.search.return_value = [
        {
            "chunk_id": "chunk_101",
            "document_id": "doc_native_001",
            "filename": "01_native_text_invoice.pdf",
            "page_number": 1,
            "score": 0.95,
            "source_type": "TEXT",
            "text": "Invoice Number: INV-2026-001\nVendor: ABC Technologies Pvt Ltd\nTotal Amount: ₹123,900"
        },
        {
            "chunk_id": "chunk_102",
            "document_id": "doc_native_001",
            "filename": "01_native_text_invoice.pdf",
            "page_number": 1,
            "score": 0.88,
            "source_type": "TEXT",
            "text": "Subtotal: ₹105,000\nGST (18%): ₹18,900"
        }
    ]
    return retriever


@pytest.fixture
def mock_llm_provider():
    llm = MagicMock()
    llm.model_name = "gemini-3.6-flash"
    llm.extract_structured_json.return_value = {
        "answer": "The total amount is ₹123,900.",
        "confidence": 0.95,
        "citations": [
            {
                "document_id": "doc_native_001",
                "filename": "01_native_text_invoice.pdf",
                "page_number": 1,
                "chunk_id": "chunk_101",
                "quoted_evidence": "Total Amount: ₹123,900"
            }
        ],
        "insufficient_evidence": False
    }
    return llm


def test_1_correct_answer_from_evidence(mock_retriever, mock_llm_provider):
    """Test 1: Synthesizes correct grounded answer & citations when valid evidence exists."""
    qa_service = GroundedQAService(retriever=mock_retriever, llm_provider=mock_llm_provider)
    result = qa_service.answer_question("What is the total amount?")

    assert isinstance(result, RAGAnswer)
    assert result.answer == "The total amount is ₹123,900."
    assert not result.insufficient_evidence
    assert len(result.citations) == 1
    assert result.citations[0].filename == "01_native_text_invoice.pdf"
    assert result.citations[0].quoted_evidence == "Total Amount: ₹123,900"


def test_2_no_evidence():
    """Test 2: Returns insufficient evidence refusal when vector store returns 0 chunks."""
    retriever = MagicMock()
    retriever.search.return_value = []
    llm = MagicMock()

    qa_service = GroundedQAService(retriever=retriever, llm_provider=llm)
    result = qa_service.answer_question("What is the total amount?")

    assert result.insufficient_evidence is True
    assert result.answer == "I couldn't find this information in the provided documents."
    assert len(result.citations) == 0
    # LLM should not be invoked when 0 chunks are found
    assert llm.extract_structured_json.call_count == 0


def test_3_weak_evidence():
    """Test 3: Filters weak evidence below similarity threshold (<0.25) and returns refusal."""
    retriever = MagicMock()
    retriever.search.return_value = [
        {
            "chunk_id": "chunk_weak",
            "document_id": "doc_weak",
            "filename": "irrelevant.pdf",
            "page_number": 1,
            "score": 0.10,  # Below threshold 0.25
            "text": "Weather report for Tuesday: Sunny 25 C."
        }
    ]
    llm = MagicMock()

    qa_service = GroundedQAService(retriever=retriever, llm_provider=llm)
    result = qa_service.answer_question("What is the invoice total?")

    assert result.insufficient_evidence is True
    assert result.answer == "I couldn't find this information in the provided documents."
    assert len(result.citations) == 0
    assert llm.extract_structured_json.call_count == 0


def test_4_conflicting_evidence(mock_retriever):
    """Test 4: Reports conflicting values explicitly across pages and cites both sources."""
    conflicting_retriever = MagicMock()
    conflicting_retriever.search.return_value = [
        {
            "chunk_id": "chunk_p1",
            "document_id": "doc_conflict",
            "filename": "conflict_inv.pdf",
            "page_number": 1,
            "score": 0.92,
            "text": "Total Amount: ₹100,000"
        },
        {
            "chunk_id": "chunk_p3",
            "document_id": "doc_conflict",
            "filename": "conflict_inv.pdf",
            "page_number": 3,
            "score": 0.90,
            "text": "Total Amount: ₹120,000"
        }
    ]

    llm = MagicMock()
    llm.extract_structured_json.return_value = {
        "answer": "The documents contain conflicting total amounts: ₹100,000 on page 1 and ₹120,000 on page 3.",
        "confidence": 0.91,
        "citations": [
            {
                "document_id": "doc_conflict",
                "filename": "conflict_inv.pdf",
                "page_number": 1,
                "chunk_id": "chunk_p1",
                "quoted_evidence": "Total Amount: ₹100,000"
            },
            {
                "document_id": "doc_conflict",
                "filename": "conflict_inv.pdf",
                "page_number": 3,
                "chunk_id": "chunk_p3",
                "quoted_evidence": "Total Amount: ₹120,000"
            }
        ],
        "insufficient_evidence": False
    }

    qa_service = GroundedQAService(retriever=conflicting_retriever, llm_provider=llm)
    result = qa_service.answer_question("What is the total amount?")

    assert not result.insufficient_evidence
    assert "conflicting total amounts" in result.answer
    assert len(result.citations) == 2
    assert result.citations[0].page_number == 1
    assert result.citations[1].page_number == 3


def test_5_document_specific_search(mock_retriever, mock_llm_provider):
    """Test 5: Passes document_id filter to retriever when specified."""
    qa_service = GroundedQAService(retriever=mock_retriever, llm_provider=mock_llm_provider)
    qa_service.answer_question("What is the total?", document_id="doc_native_001")

    mock_retriever.search.assert_called_once_with(
        query="What is the total?",
        top_k=5,
        document_id="doc_native_001"
    )


def test_6_cross_document_search(mock_retriever, mock_llm_provider):
    """Test 6: Cross-document search passes document_id=None to retriever."""
    qa_service = GroundedQAService(retriever=mock_retriever, llm_provider=mock_llm_provider)
    qa_service.answer_question("What is the total?", document_id=None)

    mock_retriever.search.assert_called_once_with(
        query="What is the total?",
        top_k=5,
        document_id=None
    )


def test_7_citation_generation(mock_retriever, mock_llm_provider):
    """Test 7: Citation contains complete required fields."""
    qa_service = GroundedQAService(retriever=mock_retriever, llm_provider=mock_llm_provider)
    result = qa_service.answer_question("What is the total?")

    cit = result.citations[0]
    assert cit.document_id == "doc_native_001"
    assert cit.filename == "01_native_text_invoice.pdf"
    assert cit.page_number == 1
    assert cit.chunk_id == "chunk_101"
    assert cit.quoted_evidence == "Total Amount: ₹123,900"


def test_8_multiple_citations(mock_retriever):
    """Test 8: Synthesizes multi-item answer with multiple citations."""
    llm = MagicMock()
    llm.extract_structured_json.return_value = {
        "answer": "Purchased items: Laptop (₹100,000) and Wireless Mouse (₹5,000).",
        "confidence": 0.90,
        "citations": [
            {
                "document_id": "doc_native_001",
                "filename": "01_native_text_invoice.pdf",
                "page_number": 1,
                "chunk_id": "chunk_101",
                "quoted_evidence": "Laptop: ₹100,000"
            },
            {
                "document_id": "doc_native_001",
                "filename": "01_native_text_invoice.pdf",
                "page_number": 1,
                "chunk_id": "chunk_102",
                "quoted_evidence": "Wireless Mouse: ₹5,000"
            }
        ],
        "insufficient_evidence": False
    }

    qa_service = GroundedQAService(retriever=mock_retriever, llm_provider=llm)
    result = qa_service.answer_question("What items were purchased?")

    assert len(result.citations) == 2
    assert "Laptop" in result.answer
    assert "Wireless Mouse" in result.answer


def test_9_approved_document_retrieval(client):
    """Test 9: Approved document query via POST /api/v1/qa endpoint succeeds."""
    db = TestingSessionLocal()
    try:
        # Create an APPROVED document record in test DB
        doc = Document(
            filename="approved_doc.pdf",
            file_path="/tmp/approved_doc.pdf",
            mime_type="application/pdf",
            file_size=1024,
            processing_status="APPROVED"
        )

        db.add(doc)
        db.commit()
        db.refresh(doc)
        approved_doc_id = doc.id
    finally:
        db.close()

    payload = {
        "query": "What is the total amount?",
        "top_k": 5,
        "document_id": approved_doc_id
    }
    response = client.post("/api/v1/qa", json=payload)
    assert response.status_code == 200
    res_data = response.json()
    assert "answer" in res_data
    assert "citations" in res_data
    assert "insufficient_evidence" in res_data


def test_10_unapproved_document_exclusion(client):
    """Test 10: Querying an UNAPPROVED (e.g. NEEDS_REVIEW or UPLOADED) document fails."""
    db = TestingSessionLocal()
    try:
        unapproved_doc = Document(
            filename="unapproved_doc.pdf",
            file_path="/tmp/unapproved_doc.pdf",
            mime_type="application/pdf",
            file_size=1024,
            processing_status="NEEDS_REVIEW"
        )

        db.add(unapproved_doc)
        db.commit()
        db.refresh(unapproved_doc)
        unapproved_id = unapproved_doc.id
    finally:
        db.close()

    payload = {
        "query": "What is the total amount?",
        "top_k": 5,
        "document_id": unapproved_id
    }
    response = client.post("/api/v1/qa", json=payload)
    assert response.status_code == 400
    assert "not approved for QA retrieval" in response.json()["detail"]


def test_11_gemini_failure_fallback(mock_retriever):
    """Test 11: Gemini API failure raises LLMExtractionError."""
    failing_llm = MagicMock()
    failing_llm.extract_structured_json.side_effect = LLMExtractionError("Gemini API Connection Timeout")

    qa_service = GroundedQAService(retriever=mock_retriever, llm_provider=failing_llm)
    with pytest.raises(LLMExtractionError) as exc_info:
        qa_service.answer_question("What is the total?")
    assert "Gemini API Connection Timeout" in str(exc_info.value)


def test_12_malformed_gemini_output(mock_retriever):
    """Test 12: Malformed LLM output invalid for Pydantic schema raises LLMExtractionError."""
    malformed_llm = MagicMock()
    # Missing required field 'answer'
    malformed_llm.extract_structured_json.return_value = {
        "confidence": "INVALID_FLOAT",
        "insufficient_evidence": "NOT_A_BOOL"
    }

    qa_service = GroundedQAService(retriever=mock_retriever, llm_provider=malformed_llm)
    with pytest.raises(LLMExtractionError) as exc_info:
        qa_service.answer_question("What is the total?")
    assert "Malformed LLM answer response" in str(exc_info.value)


def test_13_empty_query_validation(client):
    """Test 13: Empty or whitespace query returns HTTP 400 error."""
    response = client.post("/api/v1/qa", json={"query": "   ", "top_k": 5})
    assert response.status_code == 400
    assert "query cannot be empty" in response.json()["detail"].lower()
