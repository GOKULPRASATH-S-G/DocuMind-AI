import logging
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1.router import api_router
from app.api.v1.endpoints.health import get_health_status, get_readiness_status
from app.db.session import engine, Base, get_db
import app.models # Ensure models are imported for metadata reflection

logging.basicConfig(level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO), format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Create database tables automatically on startup
try:
    Base.metadata.create_all(bind=engine)
    from sqlalchemy import text
    with engine.connect() as conn:
        for sql_cmd in [
            "ALTER TABLE extracted_data ADD COLUMN extraction_type VARCHAR(50) DEFAULT 'invoice'",
            "ALTER TABLE extracted_data ADD COLUMN model_name VARCHAR(100) DEFAULT 'gemini-3.5-flash-lite'",
            "ALTER TABLE extracted_data ADD COLUMN overall_confidence FLOAT DEFAULT 0.0",
            "ALTER TABLE documents ADD COLUMN owner_id VARCHAR(36)",
            "ALTER TABLE documents ADD COLUMN workspace_id VARCHAR(36)",
            "ALTER TABLE documents ADD COLUMN failure_stage VARCHAR(100)",
            "ALTER TABLE documents ADD COLUMN failure_reason TEXT",
            "ALTER TABLE documents ADD COLUMN failed_at TIMESTAMP",
            "ALTER TABLE documents ADD COLUMN retry_count INTEGER DEFAULT 0"
        ]:
            try:
                conn.execute(text(sql_cmd))
                conn.commit()
            except Exception:
                pass
    logger.info("Database tables and migration columns verified successfully.")
except Exception as e:
    logger.warning(f"Database table initialization warning: {e}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs"
)

# Security Headers Middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# Configured CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.parse_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health", tags=["Health & Readiness"])
def root_health():
    return get_health_status()

@app.get("/health/ready", tags=["Health & Readiness"])
def root_ready(db=Depends(get_db)):
    return get_readiness_status(db=db)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.BACKEND_HOST, port=settings.BACKEND_PORT, reload=True)
