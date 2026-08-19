import os
import pytest
from unittest.mock import MagicMock, patch
from app.pipeline.visual_detector import detect_page_visual_content
from app.pipeline.image_extractor import extract_document_visual_artifacts
from app.models.visual_artifact import VisualArtifact
from app.models.document import Document
from app.rag.chunker import chunk_document_pages
from app.rag.evidence_builder import build_multimodal_context
from app.rag.qa_service import GroundedQAService
from app.schemas.qa import RAGAnswer, Citation
from app.core.exceptions import LLMExtractionError
from tests.conftest import TestingSessionLocal, client


def test_1_embedded_image_detection(native_pdf_path):
    """Test 1: Detects embedded images or pages in native PDF files."""
    detections = detect_page_visual_content(native_pdf_path)
    assert len(detections) >= 1
    assert "has_visual_content" in detections[0]
    assert "visual_type" in detections[0]


def test_2_scanned_page_visual_artifact():
    """Test 2: Classifies image MIME types as scanned page visual artifacts."""
    detections = detect_page_visual_content("dummy_path.png", mime_type="image/png")
    assert len(detections) == 1
    assert detections[0]["has_visual_content"] is True
    assert detections[0]["visual_type"] == "IMAGE"
    assert detections[0]["source"] == "SCANNED_PAGE"


def test_3_image_extraction(native_pdf_path, tmp_path):
    """Test 3: Extracts images/page renderings and saves artifacts to storage."""
    artifacts = extract_document_visual_artifacts(
        file_path=native_pdf_path,
        document_id="doc_multimodal_test",
        mime_type="application/pdf"
    )
    assert isinstance(artifacts, list)
    for art in artifacts:
        assert "image_id" in art
        assert "storage_reference" in art
        assert "absolute_path" in art


def test_4_visual_metadata():
    """Test 4: Creates valid VisualArtifact DB model record with metadata."""
    va = VisualArtifact(
        document_id="doc_123",
        page_number=4,
        image_id="img_123",
        storage_reference="documents/doc_123/images/img_4_0.png",
        mime_type="image/png",
        width=800,
        height=600,
        visual_type="CHART",
        description="Bar chart showing monthly sales.",
        key_values=[{"label": "January", "value": 120}],
        source="PDF_IMAGE"
    )
    assert va.page_number == 4
    assert va.visual_type == "CHART"
    assert va.key_values[0]["label"] == "January"


def test_5_visual_description_generation_mocked():
    """Test 5: Gemini Vision analysis returns structured JSON with visual type and description."""
    mock_llm = MagicMock()
    mock_llm.analyze_image.return_value = {
        "visual_type": "CHART",
        "description": "Bar chart showing Q1 monthly revenue.",
        "key_values": [{"label": "Jan", "value": "₹100,000"}]
    }

    res = mock_llm.analyze_image("dummy.png", "prompt")
    assert res["visual_type"] == "CHART"
    assert "Q1 monthly revenue" in res["description"]


def test_6_visual_chunk_creation():
    """Test 6: Converts visual artifacts into searchable vector chunks with source_type=VISUAL."""
    normalized_data = {
        "document_id": "doc_vis_chunk",
        "filename": "sales_report.pdf",
        "pages": [],
        "tables": [],
        "visual_artifacts": [
            {
                "image_id": "img_p4_0",
                "page_number": 4,
                "visual_type": "CHART",
                "description": "Bar chart of sales data.",
                "key_values": [{"label": "Jan", "value": 120}],
                "storage_reference": "documents/doc_vis_chunk/images/img_4_0.png"
            }
        ]
    }
    chunks = chunk_document_pages(normalized_data)
    assert len(chunks) == 1
    assert chunks[0].source_type == "VISUAL"
    assert "VISUAL DOCUMENT EVIDENCE" in chunks[0].text
    assert "Bar chart of sales data." in chunks[0].text
    assert chunks[0].metadata["image_id"] == "img_p4_0"


def test_7_visual_embedding_indexing(tmp_path):
    """Test 7: Indexes visual chunks into ChromaDB and retrieves them."""
    from app.rag.vector_store.chroma import ChromaVectorStoreProvider
    from tests.test_phase6_rag import DummyMockEmbeddingProvider

    store = ChromaVectorStoreProvider(persist_dir=str(tmp_path / "chroma_vis_test"))
    embed = DummyMockEmbeddingProvider()

    chunk_ids = ["chunk_vis_1"]
    texts = ["VISUAL DOCUMENT EVIDENCE\nDescription: Sales chart"]
    embeddings = [embed.embed_text(texts[0])]
    metadatas = [{
        "document_id": "doc_v1",
        "page_number": 4,
        "filename": "chart.pdf",
        "source_type": "VISUAL",
        "image_id": "img_v1"
    }]

    added = store.add_chunks(chunk_ids, texts, embeddings, metadatas)
    assert added == 1

    hits = store.search(query_embedding=embeddings[0], top_k=1, document_id="doc_v1")
    assert len(hits) == 1
    assert hits[0]["source_type"] == "VISUAL"


def test_8_multimodal_retrieval():
    """Test 8: Heterogeneous retrieval returns TEXT, TABLE, and VISUAL evidence together."""
    mock_retriever = MagicMock()
    mock_retriever.search.return_value = [
        {"chunk_id": "c1", "source_type": "TEXT", "score": 0.95, "text": "Report text"},
        {"chunk_id": "c2", "source_type": "TABLE", "score": 0.90, "text": "Table row data"},
        {"chunk_id": "c3", "source_type": "VISUAL", "score": 0.88, "text": "Sales bar chart", "metadata": {"image_id": "img_1"}}
    ]

    context_text, visual_inputs = build_multimodal_context(mock_retriever.search.return_value)
    assert "SOURCE 1" in context_text
    assert "Source Type: TEXT" in context_text
    assert "Source Type: TABLE" in context_text
    assert "Source Type: VISUAL" in context_text


def test_9_visual_citation_structure():
    """Test 9: Citation schema supports image_id and source_type fields."""
    cit = Citation(
        document_id="doc_v_cit",
        filename="sales_report.pdf",
        page_number=4,
        chunk_id="chunk_vis_1",
        image_id="img_p4_0",
        source_type="VISUAL",
        quoted_evidence="Bar chart showing monthly sales"
    )
    assert cit.source_type == "VISUAL"
    assert cit.image_id == "img_p4_0"


def test_10_approved_document_rule_for_visual(client):
    """Test 10: Unapproved document with visual artifacts cannot be queried via QA."""
    db = TestingSessionLocal()

    try:
        doc = Document(
            filename="unapproved_visual.pdf",
            file_path="/tmp/unapproved.pdf",
            mime_type="application/pdf",
            file_size=1024,
            processing_status="NEEDS_REVIEW"
        )
        db.add(doc)
        db.commit()

        qa_service = GroundedQAService()
        with pytest.raises(LLMExtractionError) as exc_info:
            qa_service.answer_question("What does the chart show?", document_id=doc.id, db=db)
        assert "not approved for QA retrieval" in str(exc_info.value)
    finally:
        db.close()


def test_11_missing_image_handling():
    """Test 11: Missing image file returns text description gracefully without crash."""
    chunks = [
        {
            "chunk_id": "c_missing",
            "document_id": "doc_m",
            "filename": "missing.pdf",
            "page_number": 1,
            "source_type": "VISUAL",
            "text": "Visual chart text",
            "metadata": {"image_id": "non_existent_img", "storage_reference": "documents/non_existent.png"}
        }
    ]
    context_text, visual_inputs = build_multimodal_context(chunks)
    assert "Visual chart text" in context_text
    assert len(visual_inputs) == 0  # Missing image on disk filtered gracefully


def test_12_gemini_vision_failure_fallback():
    """Test 12: Gemini Vision API failure falls back gracefully to default visual description."""
    mock_llm = MagicMock()
    mock_llm.analyze_image.side_effect = Exception("API Timeout")

    from app.services.llm.gemini import GeminiLLMProvider
    provider = GeminiLLMProvider(api_key="")
    res = provider.analyze_image("invalid_path.png", "prompt")
    assert res["visual_type"] == "UNKNOWN_VISUAL"
    assert "Visual document artifact" in res["description"]


def test_13_duplicate_image_handling():
    """Test 13: Identical image extractions generate distinct chunk IDs."""
    normalized_data = {
        "document_id": "doc_dup",
        "filename": "duplicate_img.pdf",
        "visual_artifacts": [
            {"image_id": "img_1", "page_number": 1, "visual_type": "IMAGE", "description": "Logo"},
            {"image_id": "img_2", "page_number": 2, "visual_type": "IMAGE", "description": "Logo"}
        ]
    }
    chunks = chunk_document_pages(normalized_data)
    assert len(chunks) == 2
    assert chunks[0].chunk_id != chunks[1].chunk_id
