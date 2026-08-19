from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict

class EvaluationRunRequest(BaseModel):
    dataset: str = Field(default="phase9_questions", description="Dataset file name without .json extension")

class EvaluationResultSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    question_id: str
    question: str
    expected_answer: str
    actual_answer: Optional[str] = None
    retrieval_hit: bool
    answer_correct: bool
    citation_correct: bool
    grounded: bool
    insufficient_evidence: bool
    source_type: Optional[str] = None
    latency_ms: float
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class EvaluationRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    run_id: str
    dataset_name: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    total_questions: int
    passed_count: int
    failed_count: int
    accuracy: float
    recall_at_1: float
    recall_at_3: float
    recall_at_5: float
    citation_accuracy: float
    grounding_rate: float
    hallucination_rate: float
    text_accuracy: float
    table_accuracy: float
    ocr_accuracy: float
    visual_accuracy: float
    avg_latency_ms: float

class EvaluationRunDetailResponse(EvaluationRunResponse):
    results: List[EvaluationResultSchema] = []

