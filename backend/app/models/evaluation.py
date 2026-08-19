import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, JSON, Text
from sqlalchemy.orm import relationship
from app.db.session import Base

class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dataset_name = Column(String(100), nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    
    total_questions = Column(Integer, default=0)
    passed_count = Column(Integer, default=0)
    failed_count = Column(Integer, default=0)
    accuracy = Column(Float, default=0.0)
    
    recall_at_1 = Column(Float, default=0.0)
    recall_at_3 = Column(Float, default=0.0)
    recall_at_5 = Column(Float, default=0.0)
    citation_accuracy = Column(Float, default=0.0)
    grounding_rate = Column(Float, default=0.0)
    hallucination_rate = Column(Float, default=0.0)
    
    text_accuracy = Column(Float, default=0.0)
    table_accuracy = Column(Float, default=0.0)
    ocr_accuracy = Column(Float, default=0.0)
    visual_accuracy = Column(Float, default=0.0)
    
    avg_latency_ms = Column(Float, default=0.0)
    run_metadata = Column(JSON, nullable=True)

    @property
    def run_id(self) -> str:
        return self.id

    results = relationship("EvaluationResult", back_populates="run", cascade="all, delete-orphan")


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String(36), ForeignKey("evaluation_runs.id"), nullable=False)
    
    question_id = Column(String(50), nullable=False)
    question = Column(Text, nullable=False)
    expected_answer = Column(Text, nullable=False)
    actual_answer = Column(Text, nullable=True)
    
    retrieval_hit = Column(Boolean, default=False)
    answer_correct = Column(Boolean, default=False)
    citation_correct = Column(Boolean, default=False)
    grounded = Column(Boolean, default=False)
    insufficient_evidence = Column(Boolean, default=False)
    
    source_type = Column(String(50), nullable=True)
    latency_ms = Column(Float, default=0.0)
    error = Column(Text, nullable=True)
    details = Column(JSON, nullable=True)

    run = relationship("EvaluationRun", back_populates="results")
