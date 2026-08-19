import os
import tempfile
import pytest
import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont
import io
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.session import Base, get_db
from app.models import Document, ExtractedData

# Setup temporary SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_phase2.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="module")
def db_session():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
        if os.path.exists("./test_phase2.db"):
            try:
                os.remove("./test_phase2.db")
            except OSError:
                pass


@pytest.fixture(scope="module")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def native_pdf_path(tmp_path):
    """Creates a sample 2-page native PDF file with text."""
    pdf_file = tmp_path / "native_sample.pdf"
    doc = fitz.open()

    page1 = doc.new_page()
    page1.insert_text((50, 100), "INVOICE #INV-2026-001\nDate: 2026-08-17\nVendor: ACME Corporation\nTotal Due: $1450.50", fontsize=12)

    page2 = doc.new_page()
    page2.insert_text((50, 100), "Page 2 Terms and Conditions:\nAll payments due within 30 days of receipt of invoice.", fontsize=12)

    doc.save(str(pdf_file))
    doc.close()
    return str(pdf_file)


@pytest.fixture
def scanned_pdf_path(tmp_path):
    """Creates a scanned PDF page containing an image without extractable native text."""
    pdf_file = tmp_path / "scanned_sample.pdf"
    img = Image.new("RGB", (600, 400), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((50, 50), "Scanned Text Image Invoice Total $500", fill=(0, 0, 0))

    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_bytes = img_byte_arr.getvalue()

    doc = fitz.open()
    page = doc.new_page(width=600, height=400)
    page.insert_image(page.rect, stream=img_bytes)

    doc.save(str(pdf_file))
    doc.close()
    return str(pdf_file)


@pytest.fixture
def mixed_pdf_path(tmp_path):
    """Creates a 2-page mixed PDF: Page 1 native text, Page 2 scanned image."""
    pdf_file = tmp_path / "mixed_sample.pdf"
    doc = fitz.open()

    # Page 1: Native text
    page1 = doc.new_page(width=600, height=400)
    page1.insert_text((50, 100), "This is native extractable PDF text content for Page 1 of the document.", fontsize=12)

    # Page 2: Image
    img = Image.new("RGB", (600, 400), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((50, 50), "Scanned Image Page 2", fill=(0, 0, 0))
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    img_bytes = img_byte_arr.getvalue()

    page2 = doc.new_page(width=600, height=400)
    page2.insert_image(page2.rect, stream=img_bytes)

    doc.save(str(pdf_file))
    doc.close()
    return str(pdf_file)
