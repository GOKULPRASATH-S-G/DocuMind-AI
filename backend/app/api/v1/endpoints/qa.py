from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.rate_limiter import rag_rate_limiter
from app.models.document import Document
from app.models.user import User, UserRole
from app.models.audit import AuditLog
from app.api.v1.endpoints.auth import get_current_user
from app.schemas.qa import QAQuery, RAGAnswer
from app.rag.qa_service import answer_question
from app.core.exceptions import LLMExtractionError, DocumentProcessingError

router = APIRouter()

@router.post("", response_model=RAGAnswer)
@router.post("/", response_model=RAGAnswer)
def ask_rag_question(
    request: Request,
    payload: QAQuery,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Phase 7 & 10 SECURE GROUNDED RAG QA ENDPOINT:
    - Enforces document ownership authorization.
    - Applies rate limiting.
    - Synthesizes grounded answers strictly from authorized evidence chunks with page citations.
    - Logs audit event.
    """
    rag_rate_limiter.check_rate_limit(request.client.host if request.client else "127.0.0.1")

    if not payload.query or not payload.query.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query cannot be empty."
        )

    # Ownership Security Verification
    if payload.document_id:
        doc = db.query(Document).filter(Document.id == payload.document_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail=f"Document '{payload.document_id}' not found.")
        if current_user.role == UserRole.USER and doc.owner_id and doc.owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Access denied. You do not own this document.")

    try:
        result = answer_question(
            query=payload.query,
            top_k=payload.top_k,
            document_id=payload.document_id,
            db=db
        )

        # Filter out citations from documents not owned by current_user
        if current_user.role == UserRole.USER:
            user_doc_ids = set(
                d.id for d in db.query(Document.id).filter(
                    Document.owner_id == current_user.id
                ).all()
            )
            result.citations = [c for c in result.citations if not c.document_id or c.document_id in user_doc_ids]

        # Log Audit Event
        audit = AuditLog(
            user_id=current_user.id,
            action="RAG_QUERY",
            document_id=payload.document_id,
            metadata_json={"top_k": payload.top_k, "citations_count": len(result.citations)}
        )
        db.add(audit)
        db.commit()

        return result

    except LLMExtractionError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(err)
        )
    except DocumentProcessingError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(err)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Grounded RAG synthesis failed: {str(e)}"
        )
