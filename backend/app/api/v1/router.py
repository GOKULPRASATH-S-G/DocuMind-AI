from fastapi import APIRouter
from app.api.v1.endpoints import documents, review, reviews, rag, qa, evaluation, auth, health, metrics

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication & Profile"])
api_router.include_router(health.router, prefix="/health", tags=["Health & Readiness"])
api_router.include_router(metrics.router, prefix="/metrics", tags=["Production Metrics"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
api_router.include_router(reviews.router, prefix="/reviews", tags=["Human Review Queue"])
api_router.include_router(review.router, prefix="/review", tags=["Human Review Legacy"])
api_router.include_router(rag.router, tags=["RAG & Search"])
api_router.include_router(rag.router, prefix="/rag", tags=["RAG Intelligence Legacy"])
api_router.include_router(qa.router, prefix="/qa", tags=["Grounded QA Engine"])
api_router.include_router(evaluation.router, prefix="/evaluation", tags=["Evaluation & Observability"])



