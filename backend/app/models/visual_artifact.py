import uuid
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import String, Integer, DateTime, Text, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


class VisualArtifact(Base):
    __tablename__ = "visual_artifacts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    image_id: Mapped[str] = mapped_column(String(100), nullable=False)
    storage_reference: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), default="image/png")
    width: Mapped[int] = mapped_column(Integer, default=0)
    height: Mapped[int] = mapped_column(Integer, default=0)
    
    visual_type: Mapped[str] = mapped_column(String(50), default="UNKNOWN_VISUAL")  # IMAGE, CHART, DIAGRAM, UNKNOWN_VISUAL, SCANNED_PAGE
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    key_values: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    extraction_status: Mapped[str] = mapped_column(String(50), default="EXTRACTED")  # EXTRACTED, ANALYZED, FAILED
    source: Mapped[str] = mapped_column(String(50), default="PDF_IMAGE")  # PDF_IMAGE, SCANNED_PAGE

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    document = relationship("Document", back_populates="visual_artifacts")
