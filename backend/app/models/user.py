import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, String, DateTime, Enum
from sqlalchemy.orm import relationship
from app.db.session import Base

class UserRole(str, PyEnum):
    ADMIN = "ADMIN"
    REVIEWER = "REVIEWER"
    USER = "USER"

class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
    workspace_id = Column(String(36), default=lambda: str(uuid.uuid4()), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    documents = relationship("Document", back_populates="owner", cascade="all, delete-orphan")
