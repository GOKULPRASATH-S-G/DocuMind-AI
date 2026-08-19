import pdfplumber
import logging
from typing import List, Dict, Any
from app.schemas.ingestion import TableExtractionResult

logger = logging.getLogger(__name__)


def extract_page_tables(file_path: str, page_number: int) -> List[TableExtractionResult]:
    """
    Extracts tables from a specific 1-indexed PDF page using pdfplumber.
    A failure here is caught and logged, returning an empty list so pipeline execution continues.
    """
    logger.info(f"Attempting table extraction on page {page_number} of {file_path}")
    page_tables: List[TableExtractionResult] = []
    try:
        with pdfplumber.open(file_path) as pdf:
            if page_number < 1 or page_number > len(pdf.pages):
                logger.warning(f"Table extraction page {page_number} out of range (total pages {len(pdf.pages)}).")
                return []

            page = pdf.pages[page_number - 1]
            tables = page.extract_tables()

            for idx, table in enumerate(tables):
                if not table or len(table) < 1:
                    continue

                headers = [str(col).strip() if col is not None else f"col_{j}" for j, col in enumerate(table[0])]
                rows = []
                for row in table[1:]:
                    row_values = [str(cell).strip() if cell is not None else "" for cell in row]
                    rows.append(row_values)

                logger.info(f"Found table #{idx} on page {page_number}: headers={headers}, rows={len(rows)}")
                page_tables.append(
                    TableExtractionResult(
                        page_number=page_number,
                        table_index=idx,
                        headers=headers,
                        rows=rows,
                        source="TABLE"
                    )
                )
    except Exception as e:
        logger.error(f"pdfplumber table extraction failed on page {page_number} of {file_path}: {e}")
        # Table extraction failure MUST NOT crash the document processing pipeline
        return []

    return page_tables


def extract_all_tables(file_path: str) -> List[TableExtractionResult]:
    """
    Attempts table extraction for every page in the document.
    """
    all_tables: List[TableExtractionResult] = []
    try:
        with pdfplumber.open(file_path) as pdf:
            total_pages = len(pdf.pages)
        
        for p in range(1, total_pages + 1):
            page_tables = extract_page_tables(file_path, p)
            all_tables.extend(page_tables)
    except Exception as e:
        logger.error(f"pdfplumber total table extraction error on {file_path}: {e}")

    return all_tables
