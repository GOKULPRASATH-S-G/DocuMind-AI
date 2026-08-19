from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.models.document import Document
from app.models.audit import AuditLog
from app.models.evaluation import EvaluationRun

router = APIRouter()

@router.get("", status_code=200)
def get_production_metrics(db: Session = Depends(get_db)):
    """
    Returns aggregated real-time production metrics for the application dashboard.
    """
    total_docs = db.query(Document).count()
    indexed_docs = db.query(Document).filter(Document.processing_status == "INDEXED").count()
    review_docs = db.query(Document).filter(Document.processing_status == "NEEDS_REVIEW").count()
    failed_docs = db.query(Document).filter(Document.processing_status == "FAILED").count()

    total_queries = db.query(AuditLog).filter(AuditLog.action == "RAG_QUERY").count()
    
    last_eval = db.query(EvaluationRun).order_by(EvaluationRun.started_at.desc()).first()

    return {
        "documents": {
            "total": total_docs,
            "indexed": indexed_docs,
            "review": review_docs,
            "failed": failed_docs
        },
        "rag": {
            "queries_total": total_queries,
            "avg_latency_ms": last_eval.avg_latency_ms if last_eval else 0.0
        },
        "evaluation": {
            "accuracy": round(last_eval.accuracy * 100, 1) if last_eval else 100.0,
            "grounding": round(last_eval.grounding_rate * 100, 1) if last_eval else 100.0,
            "hallucination": round(last_eval.hallucination_rate * 100, 1) if last_eval else 0.0
        }
    }
