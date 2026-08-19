import pytest
from unittest.mock import MagicMock
from app.rag.chunker import chunk_document_pages
from app.rag.embeddings.base import BaseEmbeddingProvider
from app.rag.vector_store.chroma import ChromaVectorStoreProvider
from app.rag.indexer import DocumentIndexer
from app.rag.retriever import DocumentRetriever
from app.core.exceptions import LLMExtractionError


# Mock Embedding Provider for isolated deterministic testing
class DummyMockEmbeddingProvider(BaseEmbeddingProvider):
    def embed_text(self, text: str):
        if not text or not text.strip():
            raise LLMExtractionError("Cannot embed empty text.")
        # Return deterministic dummy 768-dim vector
        val = float(len(text) % 10) / 10.0
        return [val] * 768

    def embed_texts(self, texts):
        if not texts:
            return []
        return [self.embed_text(t) for t in texts]


def test_chunking_normal_text():
    """Test 1: Chunking normal page text preserves page metadata and splits cleanly."""
    normalized_data = {
        "document_id": "doc-test-100",
        "filename": "sample_invoice.pdf",
        "pages": [
            {"page_number": 1, "source": "TEXT", "text": "Page 1 Invoice Header Vendor Corp"},
            {"page_number": 2, "source": "TEXT", "text": "Page 2 Payment Terms Net 30"}
        ],
        "tables": []
    }
    chunks = chunk_document_pages(normalized_data, chunk_size=50, chunk_overlap=10)
    assert len(chunks) == 2
    assert chunks[0].page_number == 1
    assert chunks[0].source_type == "TEXT"
    assert chunks[1].page_number == 2


def test_table_chunking():
    """Test 2: Tables are converted into readable matrix text chunks preserving page number."""
    normalized_data = {
        "document_id": "doc-test-table",
        "filename": "table_doc.pdf",
        "pages": [],
        "tables": [
            {
                "page_number": 1,
                "headers": ["Item", "Qty", "Price", "Amount"],
                "rows": [["Laptop", "2", "50000", "100000"], ["Mouse", "2", "1000", "2000"]]
            }
        ]
    }
    chunks = chunk_document_pages(normalized_data)
    assert len(chunks) == 1
    assert chunks[0].source_type == "TABLE"
    assert "Item | Qty | Price | Amount" in chunks[0].text
    assert "Laptop | 2 | 50000 | 100000" in chunks[0].text


def test_chroma_vector_store_operations(tmp_path):
    """Test 3: ChromaDB add, search, and delete_document_chunks."""
    store = ChromaVectorStoreProvider(persist_dir=str(tmp_path / "chroma_test"))

    chunk_ids = ["chunk_1", "chunk_2"]
    texts = ["Invoice total amount is 1100.00 USD", "Payment terms net 30 days"]
    embeddings = [[0.1] * 768, [0.9] * 768]
    metadatas = [
        {"document_id": "doc-99", "page_number": 1, "filename": "inv.pdf", "source_type": "TEXT"},
        {"document_id": "doc-99", "page_number": 2, "filename": "inv.pdf", "source_type": "TEXT"}
    ]

    added = store.add_chunks(chunk_ids, texts, embeddings, metadatas)
    assert added == 2

    # Search
    results = store.search(query_embedding=[0.1] * 768, top_k=1, document_id="doc-99")
    assert len(results) == 1
    assert results[0]["chunk_id"] == "chunk_1"

    # Delete
    deleted = store.delete_document_chunks("doc-99")
    assert deleted == 2


def test_indexing_unapproved_document_fails(client, native_pdf_path):
    """Test 4: HARD RULE - Indexing document with status NEEDS_REVIEW fails!"""
    with open(native_pdf_path, "rb") as f:
        up_res = client.post("/api/v1/documents/upload", files={"file": ("unapproved.pdf", f, "application/pdf")})
    doc_id = up_res.json()["id"]
    client.post(f"/api/v1/documents/{doc_id}/process")

    # Document status is EXTRACTED, not APPROVED
    idx_res = client.post(f"/api/v1/documents/{doc_id}/index")
    assert idx_res.status_code == 400
    assert "Only APPROVED documents can be indexed" in idx_res.json()["detail"]


def test_indexing_approved_document_succeeds(client, native_pdf_path, tmp_path, db_session):
    """Test 5 & 6: Approved document indexing succeeds and re-indexing is idempotent."""
    # 1. Upload & Process
    with open(native_pdf_path, "rb") as f:
        up_res = client.post("/api/v1/documents/upload", files={"file": ("approved_test.pdf", f, "application/pdf")})
    doc_id = up_res.json()["id"]
    client.post(f"/api/v1/documents/{doc_id}/process")

    # Mock structured extraction
    mock_llm = MagicMock()
    mock_llm.model_name = "gemini-3.6-flash"
    mock_llm.extract_structured_json.return_value = {
        "invoice_number": "INV-APPROVED-100",
        "invoice_date": "2026-08-17",
        "vendor_name": "Approved Vendor Inc",
        "customer_name": "Acme Corp",
        "currency": "USD",
        "line_items": [{"description": "Service A", "quantity": 1.0, "unit_price": 100.0, "amount": 100.0}],
        "subtotal": 100.0,
        "tax": 10.0,
        "total_amount": 110.0,
        "due_date": "2026-09-17"
    }

    from app.services.extraction_service import ExtractionService
    ext_service = ExtractionService(llm_provider=mock_llm)
    ext_res = ext_service.run_invoice_extraction(doc_id, db_session)
    assert ext_res.status in ["APPROVED", "INDEXED"]

    # 2. Index Document with Mock Embeddings & Vector Store
    mock_embed = DummyMockEmbeddingProvider()
    test_store = ChromaVectorStoreProvider(persist_dir=str(tmp_path / "chroma_approved_test"))
    indexer = DocumentIndexer(embedding_provider=mock_embed, vector_store=test_store)

    index_res = indexer.index_document(doc_id, db_session)
    assert index_res["status"] == "INDEXED"
    assert index_res["chunks_indexed"] >= 1

    # Re-indexing safety (idempotent check - no duplicates)
    reindex_res = indexer.index_document(doc_id, db_session)
    assert reindex_res["chunks_indexed"] == index_res["chunks_indexed"]

    # Search test
    retriever = DocumentRetriever(embedding_provider=mock_embed, vector_store=test_store)
    hits = retriever.search("What is the invoice number?", top_k=3, document_id=doc_id)
    assert len(hits) >= 1
    assert hits[0]["document_id"] == doc_id
    assert hits[0]["filename"] == "approved_test.pdf"
