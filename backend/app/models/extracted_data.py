import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


class ExtractedData(Base):
    __tablename__ = "extracted_data"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, unique=True)

    raw_llm_json: Mapped[dict] = mapped_column(JSON, nullable=True)
    validated_json: Mapped[dict] = mapped_column(JSON, nullable=True)
    extraction_type: Mapped[str] = mapped_column(String(50), default="invoice")
    model_name: Mapped[str] = mapped_column(String(100), default="gemini-1.5-flash")
    field_confidence_scores: Mapped[dict] = mapped_column(JSON, nullable=True)
    validation_errors: Mapped[list] = mapped_column(JSON, nullable=True)
    overall_confidence: Mapped[float] = mapped_column(JSON, default=0.0, nullable=True)

    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    document = relationship("Document", back_populates="extracted_data")
