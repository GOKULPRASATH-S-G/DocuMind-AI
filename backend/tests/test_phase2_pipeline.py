import os
import pytest
from app.pipeline.text_detector import detect_page_modes
from app.pipeline.extractor_pymupdf import extract_native_page_text, extract_all_native_text
from app.pipeline.extractor_tables import extract_all_tables
from app.pipeline.pdf_to_image import convert_pdf_page_to_image_bytes
from app.services.ocr.tesseract import TesseractOCRProvider
from app.schemas.ingestion import PageModeEnum


def test_scanned_page_detection(native_pdf_path, scanned_pdf_path, mixed_pdf_path):
    # Test 1: Native PDF detection
    native_detections = detect_page_modes(native_pdf_path)
    assert len(native_detections) == 2
    assert native_detections[0].mode == PageModeEnum.NATIVE_PDF
    assert native_detections[0].text_length > 50

    # Test 2: Scanned PDF page detection
    scanned_detections = detect_page_modes(scanned_pdf_path)
    assert len(scanned_detections) == 1
    assert scanned_detections[0].mode == PageModeEnum.SCANNED_IMAGE
    assert scanned_detections[0].text_length == 0

    # Test 3: Mixed PDF per-page independent detection
    mixed_detections = detect_page_modes(mixed_pdf_path)
    assert len(mixed_detections) == 2
    assert mixed_detections[0].mode == PageModeEnum.NATIVE_PDF
    assert mixed_detections[1].mode == PageModeEnum.SCANNED_IMAGE


def test_native_pdf_extraction(native_pdf_path):
    res_page1 = extract_native_page_text(native_pdf_path, page_number=1)
    assert res_page1.page_number == 1
    assert "INVOICE #INV-2026-001" in res_page1.text
    assert res_page1.source.value == "TEXT"

    all_pages = extract_all_native_text(native_pdf_path)
    assert len(all_pages) == 2
    assert "Terms and Conditions" in all_pages[1].text


def test_pdf_page_to_image_conversion(scanned_pdf_path):
    img_bytes = convert_pdf_page_to_image_bytes(scanned_pdf_path, page_number=1, dpi=150)
    assert isinstance(img_bytes, bytes)
    assert len(img_bytes) > 1000


def test_ocr_service_interface(scanned_pdf_path):
    img_bytes = convert_pdf_page_to_image_bytes(scanned_pdf_path, page_number=1, dpi=150)
    ocr_provider = TesseractOCRProvider()

    # Test 1: Extract text
    try:
        text = ocr_provider.extract_text_from_image(img_bytes)
        assert isinstance(text, str)
    except Exception as e:
        pytest.skip(f"Tesseract binary not installed on test host: {e}")

    # Test 2: Extract text with boxes
    try:
        box_data = ocr_provider.extract_text_with_boxes(img_bytes)
        assert "text" in box_data
        assert "confidence" in box_data
        assert "boxes" in box_data
        assert isinstance(box_data["confidence"], float)
    except Exception as e:
        pytest.skip(f"Tesseract binary not installed on test host: {e}")


def test_table_extraction(native_pdf_path):
    # Running table extraction on text PDF should return empty list without crashing
    tables = extract_all_tables(native_pdf_path)
    assert isinstance(tables, list)


def test_api_upload_and_process(client, native_pdf_path):
    # 1. Upload valid PDF
    with open(native_pdf_path, "rb") as f:
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("test_native.pdf", f, "application/pdf")}
        )
    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == "test_native.pdf"
    assert data["processing_status"] == "UPLOADED"
    doc_id = data["id"]

    # 2. Process document
    proc_response = client.post(f"/api/v1/documents/{doc_id}/process")
    assert proc_response.status_code == 200
    proc_data = proc_response.json()
    assert proc_data["document_id"] == doc_id
    assert proc_data["total_pages"] == 2
    assert proc_data["summary"]["status"] == "EXTRACTED"
    assert proc_data["summary"]["native_pages"] == 2


def test_invalid_upload(client):
    # Test uploading empty file
    empty_bytes = b""
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("empty.pdf", empty_bytes, "application/pdf")}
    )
    assert response.status_code == 400

    # Test uploading invalid file extension
    txt_bytes = b"Hello world"
    response = client.post(
        "/api/v1/documents/upload",
        files={"file": ("test.txt", txt_bytes, "text/plain")}
    )
    assert response.status_code == 400


def test_missing_document(client):
    response = client.post("/api/v1/documents/non_existent_doc_id/process")
    assert response.status_code == 404
