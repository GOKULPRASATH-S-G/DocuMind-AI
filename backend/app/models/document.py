import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime, Text, JSON, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base

class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)

    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    workspace_id: Mapped[str] = mapped_column(String(36), nullable=True, index=True)

    is_scanned: Mapped[bool] = mapped_column(default=False)
    processing_status: Mapped[str] = mapped_column(String(50), default="UPLOADED", index=True) # UPLOADED, QUEUED, PROCESSING, EXTRACTED, VALIDATING, NEEDS_REVIEW, APPROVED, INDEXING, INDEXED, REJECTED, FAILED
    overall_confidence: Mapped[float] = mapped_column(Float, default=0.0)

    failure_stage: Mapped[str] = mapped_column(String(100), nullable=True)
    failure_reason: Mapped[str] = mapped_column(Text, nullable=True)
    failed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    error_message: Mapped[str] = mapped_column(Text, nullable=True)

    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="documents")
    extracted_data = relationship("ExtractedData", back_populates="document", cascade="all, delete-orphan", uselist=False)
    human_reviews = relationship("HumanReview", back_populates="document", cascade="all, delete-orphan")
    index_meta = relationship("DocumentIndex", back_populates="document", cascade="all, delete-orphan", uselist=False)
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    visual_artifacts = relationship("VisualArtifact", back_populates="document", cascade="all, delete-orphan")


