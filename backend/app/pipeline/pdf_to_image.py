import fitz  # PyMuPDF
import logging
from app.core.exceptions import DocumentProcessingError

logger = logging.getLogger(__name__)


def convert_pdf_page_to_image_bytes(file_path: str, page_number: int, dpi: int = 300) -> bytes:
    """
    Converts a specific PDF page (1-indexed) to PNG image bytes suitable for Tesseract OCR.
    Isolated from the OCR provider layer.
    """
    logger.info(f"Converting PDF page {page_number} to image bytes at {dpi} DPI for file {file_path}")
    try:
        doc = fitz.open(file_path)
        if page_number < 1 or page_number > len(doc):
            doc.close()
            raise DocumentProcessingError(f"Page number {page_number} out of range (total pages: {len(doc)}).")

        page = doc[page_number - 1]
        zoom = dpi / 72  # 72 points per inch standard PDF resolution
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        image_bytes = pix.tobytes("png")
        doc.close()

        logger.info(f"Successfully converted page {page_number} to PNG image bytes ({len(image_bytes)} bytes)")
        return image_bytes

    except Exception as e:
        logger.error(f"Failed to convert PDF page {page_number} to image in {file_path}: {e}")
        raise DocumentProcessingError(f"PDF page to image conversion failed for page {page_number}: {str(e)}")
