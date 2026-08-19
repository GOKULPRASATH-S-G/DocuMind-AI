import fitz  # PyMuPDF
import logging
from typing import List, Dict, Any, Optional
from app.schemas.ingestion import PageExtractionResult, ExtractionSourceEnum
from app.core.exceptions import DocumentProcessingError

logger = logging.getLogger(__name__)


def extract_native_page_text(file_path: str, page_number: int) -> PageExtractionResult:
    """
    Extracts native text from a specific 1-indexed page number using PyMuPDF.
    Preserves page boundaries and metadata.
    """
    logger.info(f"Extracting native PDF text for page {page_number} from {file_path}")
    try:
        doc = fitz.open(file_path)
        if page_number < 1 or page_number > len(doc):
            doc.close()
            raise DocumentProcessingError(f"Page number {page_number} out of range (total pages: {len(doc)}).")

        page = doc[page_number - 1]
        text = page.get_text().strip()
        doc.close()

        return PageExtractionResult(
            page_number=page_number,
            text=text,
            source=ExtractionSourceEnum.TEXT,
            confidence=1.0
        )
    except Exception as e:
        logger.error(f"PyMuPDF text extraction failed for page {page_number} in {file_path}: {e}")
        return PageExtractionResult(
            page_number=page_number,
            text="",
            source=ExtractionSourceEnum.TEXT,
            error=str(e)
        )


def extract_all_native_text(file_path: str) -> List[PageExtractionResult]:
    """
    Extracts native text from all pages in a document using PyMuPDF.
    """
    results = []
    try:
        doc = fitz.open(file_path)
        for i, page in enumerate(doc):
            page_num = i + 1
            text = page.get_text().strip()
            results.append(
                PageExtractionResult(
                    page_number=page_num,
                    text=text,
                    source=ExtractionSourceEnum.TEXT,
                    confidence=1.0
                )
            )
        doc.close()
    except Exception as e:
        logger.error(f"PyMuPDF native extraction error on {file_path}: {e}")
        raise DocumentProcessingError(f"Failed native PDF text extraction: {str(e)}")
    return results


def extract_native_text(file_path: str) -> List[Dict[str, Any]]:
    """
    Returns list of dicts with page_number and text for backward compatibility.
    """
    pages = extract_all_native_text(file_path)
    return [{"page_number": p.page_number, "text": p.text} for p in pages]
