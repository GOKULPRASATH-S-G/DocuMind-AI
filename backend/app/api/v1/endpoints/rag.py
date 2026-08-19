from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.rate_limiter import rag_rate_limiter
from app.models.document import Document
from app.models.user import User, UserRole
from app.models.audit import AuditLog
from app.api.v1.endpoints.auth import get_current_user
from app.rag.retriever import DocumentRetriever
from app.core.exceptions import LLMExtractionError

router = APIRouter()
retriever = DocumentRetriever()

class SearchRequest(BaseModel):
    query: str
    top_k: int = Field(5, ge=1, le=50)
    document_id: Optional[str] = None

class SearchResultItem(BaseModel):
    chunk_id: str
    document_id: str
    filename: str
    page_number: int
    score: float
    source_type: str
    text: str

class SearchResponse(BaseModel):
    query: str
    results: List[SearchResultItem]

@router.post("/search", response_model=SearchResponse)
def search_vector_store(
    request: Request,
    payload: SearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Phase 6 & 10 SECURE SEMANTIC SEARCH ENDPOINT:
    - Enforces ownership: only searches over authorized approved documents owned by current_user.
    - Applies rate limiting.
    - Logs audit event.
    """
    rag_rate_limiter.check_rate_limit(request.client.host if request.client else "127.0.0.1")

    if not payload.query or not payload.query.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty.")

    # Ownership Security Check
    if payload.document_id:
        doc = db.query(Document).filter(Document.id == payload.document_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail=f"Document '{payload.document_id}' not found.")
        if current_user.role == UserRole.USER and doc.owner_id and doc.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied. You do not own this document.")

    try:
        raw_results = retriever.search(
            query=payload.query,
            top_k=payload.top_k,
            document_id=payload.document_id
        )

        # Filter out any chunks belonging to documents not owned by current_user
        if current_user.role == UserRole.USER:
            user_doc_ids = set(
                d.id for d in db.query(Document.id).filter(
                    Document.owner_id == current_user.id
                ).all()
            )
            raw_results = [r for r in raw_results if not r.get("document_id") or r.get("document_id") in user_doc_ids]

        results = [
            SearchResultItem(
                chunk_id=r["chunk_id"],
                document_id=r["document_id"],
                filename=r["filename"],
                page_number=r["page_number"],
                score=r["score"],
                source_type=r["source_type"],
                text=r["text"]
            ) for r in raw_results
        ]

        # Log Audit Event
        audit = AuditLog(
            user_id=current_user.id,
            action="RAG_SEARCH",
            document_id=payload.document_id,
            metadata_json={"top_k": payload.top_k, "result_count": len(results)}
        )
        db.add(audit)
        db.commit()

        return SearchResponse(query=payload.query, results=results)

    except LLMExtractionError as err:
        raise HTTPException(status_code=400, detail=str(err))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Semantic search failed: {str(e)}")
