import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, JSON, Text
from app.db.session import Base

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), index=True, nullable=True)
    action = Column(String(100), index=True, nullable=False) # e.g. DOCUMENT_UPLOADED, DOCUMENT_APPROVED, RAG_QUERY
    document_id = Column(String(36), index=True, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    metadata_json = Column(JSON, nullable=True)
