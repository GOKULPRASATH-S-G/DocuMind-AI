from typing import List, Optional
from pydantic import BaseModel


class RAGQueryRequest(BaseModel):
    question: str
    document_ids: Optional[List[str]] = None
    top_k: int = 5


class RAGCitation(BaseModel):
    document_id: str
    document_name: str
    page_number: int
    chunk_snippet: str
    similarity_score: float


class RAGQueryResponse(BaseModel):
    answer: str
    citations: List[RAGCitation]
