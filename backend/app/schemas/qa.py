from typing import List, Optional
from pydantic import BaseModel, Field


class Citation(BaseModel):
    document_id: str = Field(..., description="ID of the document containing the cited evidence")
    filename: str = Field(..., description="Filename of the cited document")
    page_number: int = Field(..., description="Page number of the cited evidence")
    chunk_id: str = Field(..., description="Unique chunk ID for the cited evidence")
    image_id: Optional[str] = Field(default=None, description="ID of the visual image artifact if source_type is VISUAL")
    source_type: str = Field(default="TEXT", description="Evidence type: TEXT, OCR, TABLE, or VISUAL")
    quoted_evidence: str = Field(..., description="Exact quoted text or snippet from the evidence")



class RAGAnswer(BaseModel):
    answer: str = Field(..., description="Grounded answer synthesized exclusively from document evidence")
    confidence: Optional[float] = Field(
        default=None,
        description="Answer grounding confidence score based on evidence coverage/retrieval (NOT model probability)"
    )
    citations: List[Citation] = Field(default_factory=list, description="List of source citations backing the claims in the answer")
    insufficient_evidence: bool = Field(default=False, description="True if evidence was missing or insufficient to answer the query")


class QAQuery(BaseModel):
    query: str = Field(..., description="User question or query string")
    top_k: int = Field(default=5, ge=1, le=50, description="Number of evidence chunks to retrieve")
    document_id: Optional[str] = Field(default=None, description="Optional document ID to restrict search to a single document")
