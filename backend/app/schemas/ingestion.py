from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class PageModeEnum(str, Enum):
    NATIVE_PDF = "NATIVE_PDF"
    SCANNED_IMAGE = "SCANNED_IMAGE"


class ExtractionSourceEnum(str, Enum):
    TEXT = "TEXT"
    OCR = "OCR"
    TABLE = "TABLE"


class OCRBoundingBox(BaseModel):
    x: int
    y: int
    width: int
    height: int
    text: str
    confidence: float


class PageDetectionResult(BaseModel):
    page_number: int
    mode: PageModeEnum
    text_length: int


class PageExtractionResult(BaseModel):
    page_number: int
    text: str
    source: ExtractionSourceEnum
    confidence: Optional[float] = None
    boxes: Optional[List[OCRBoundingBox]] = None
    error: Optional[str] = None


class TableExtractionResult(BaseModel):
    page_number: int
    table_index: int
    headers: List[str]
    rows: List[List[str]]
    source: str = "TABLE"


class ExtractionSummary(BaseModel):
    document_id: str
    status: str
    total_pages: int
    native_pages: int
    ocr_pages: int
    tables_found: int


class NormalizedExtractionResult(BaseModel):
    document_id: str
    filename: str
    file_type: str
    total_pages: int
    pages: List[PageExtractionResult]
    tables: List[TableExtractionResult]
    summary: ExtractionSummary

    @property
    def combined_full_text(self) -> str:
        return "\n\n".join([f"--- PAGE {p.page_number} ---\n{p.text}" for p in self.pages])

