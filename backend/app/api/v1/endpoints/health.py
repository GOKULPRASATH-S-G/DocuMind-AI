import os
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.session import get_db
from app.core.config import settings
from app.rag.vector_store.chroma import ChromaVectorStoreProvider

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("", status_code=status.HTTP_200_OK)
def get_health_status():
    """Basic health check endpoint returning overall application status."""
    return {"status": "ok", "environment": settings.ENVIRONMENT}

@router.get("/ready", status_code=status.HTTP_200_OK)
def get_readiness_status(db: Session = Depends(get_db)):
    """
    Readiness probe verifying database, ChromaDB vector store, and document storage accessibility.
    """
    health_details = {
        "status": "ready",
        "database": "ok",
        "vector_store": "ok",
        "storage": "ok"
    }

    # 1. Database Check
    try:
        db.execute(text("SELECT 1"))
    except Exception as ex:
        logger.error(f"Readiness check failed - Database error: {ex}")
        health_details["database"] = f"failed: {str(ex)}"
        health_details["status"] = "not_ready"

    # 2. ChromaDB Vector Store Check
    try:
        chroma_store = ChromaVectorStoreProvider()
        count = chroma_store.collection.count()
        health_details["vector_store_chunks"] = count
    except Exception as ex:
        logger.error(f"Readiness check failed - ChromaDB error: {ex}")
        health_details["vector_store"] = f"failed: {str(ex)}"
        health_details["status"] = "not_ready"

    # 3. Storage Local Directory Check
    try:
        storage_dir = settings.STORAGE_LOCAL_DIR
        if not os.path.exists(storage_dir):
            os.makedirs(storage_dir, exist_ok=True)
    except Exception as ex:
        logger.error(f"Readiness check failed - Storage error: {ex}")
        health_details["storage"] = f"failed: {str(ex)}"
        health_details["status"] = "not_ready"

    if health_details["status"] != "ready":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=health_details
        )

    return health_details
