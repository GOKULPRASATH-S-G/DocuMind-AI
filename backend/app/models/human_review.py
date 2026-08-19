import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, JSON, Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base


class HumanReview(Base):
    __tablename__ = "human_reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)

    reviewer_id: Mapped[str] = mapped_column(String(100), default="human_operator")
    action: Mapped[str] = mapped_column(String(50), default="APPROVED")  # FIELD_EDITED, APPROVED, REJECTED
    
    field_name: Mapped[str] = mapped_column(String(100), nullable=True)
    old_value: Mapped[dict] = mapped_column(JSON, nullable=True)
    new_value: Mapped[dict] = mapped_column(JSON, nullable=True)
    
    original_fields: Mapped[dict] = mapped_column(JSON, nullable=True)
    corrected_fields: Mapped[dict] = mapped_column(JSON, nullable=True)
    
    review_action: Mapped[str] = mapped_column(String(50), default="APPROVED")
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=True)

    reviewed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    document = relationship("Document", back_populates="human_reviews")
