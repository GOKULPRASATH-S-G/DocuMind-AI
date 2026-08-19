import fitz  # PyMuPDF
import logging
from typing import List, Dict, Any
from app.schemas.ingestion import PageModeEnum, PageDetectionResult
from app.core.exceptions import DocumentProcessingError

logger = logging.getLogger(__name__)

# Minimum character count on a page to be classified as NATIVE_PDF
MIN_TEXT_LENGTH_THRESHOLD = 50


def detect_page_modes(file_path: str, mime_type: str = "application/pdf") -> List[PageDetectionResult]:
    """
    Analyzes each PDF/Image page independently to detect whether useful text exists or if OCR is required.
    Does NOT classify an entire multi-page document as scanned if only one page requires OCR.
    """
    logger.info(f"Starting page-by-page text vs scanned detection for file: {file_path}")

    # Handle image formats (PNG, JPG, JPEG, TIFF)
    if mime_type and mime_type.startswith("image/"):
        logger.info(f"File {file_path} is an image file ({mime_type}). Treating as single SCANNED_IMAGE page.")
        return [
            PageDetectionResult(
                page_number=1,
                mode=PageModeEnum.SCANNED_IMAGE,
                text_length=0
            )
        ]

    results: List[PageDetectionResult] = []

    try:
        doc = fitz.open(file_path)
        if len(doc) == 0:
            logger.error(f"PDF document is empty (0 pages): {file_path}")
            raise DocumentProcessingError("PDF document contains 0 pages.")

        for i, page in enumerate(doc):
            page_num = i + 1
            extracted_text = page.get_text().strip()
            text_len = len(extracted_text)

            if text_len >= MIN_TEXT_LENGTH_THRESHOLD:
                mode = PageModeEnum.NATIVE_PDF
            else:
                mode = PageModeEnum.SCANNED_IMAGE

            logger.info(f"Page {page_num}/{len(doc)} detection result: mode={mode.value}, text_length={text_len}")
            results.append(
                PageDetectionResult(
                    page_number=page_num,
                    mode=mode,
                    text_length=text_len
                )
            )

        doc.close()
        return results

    except fitz.FileDataError as e:
        logger.error(f"Corrupted or invalid PDF file {file_path}: {e}")
        raise DocumentProcessingError(f"Corrupted or invalid PDF file: {str(e)}")
    except Exception as e:
        if isinstance(e, DocumentProcessingError):
            raise e
        logger.error(f"Error during page detection for {file_path}: {e}")
        raise DocumentProcessingError(f"Page detection failed: {str(e)}")
