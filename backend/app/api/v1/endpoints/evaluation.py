import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.evaluation import EvaluationRun, EvaluationResult
from app.schemas.evaluation import (
    EvaluationRunRequest,
    EvaluationRunResponse,
    EvaluationRunDetailResponse
)
from evaluation.runner import EvaluationRunner

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/run", response_model=EvaluationRunResponse, status_code=status.HTTP_201_CREATED)
def trigger_evaluation_run(
    payload: EvaluationRunRequest,
    db: Session = Depends(get_db)
):
    """
    Triggers a new evaluation run over a specified benchmark dataset.
    Computes retrieval, answer, citation, grounding, hallucination, modality, and latency metrics.
    """
    logger.info(f"Triggering Phase 9 evaluation run for dataset: {payload.dataset}")
    try:
        runner = EvaluationRunner(dataset_name=payload.dataset)
        summary = runner.run_evaluation(db_session=db)
        
        run_record = db.query(EvaluationRun).filter(EvaluationRun.id == summary["run_id"]).first()
        if not run_record:
            return summary
            
        return run_record
    except FileNotFoundError as fnf:
        raise HTTPException(status_code=404, detail=str(fnf))
    except Exception as err:
        logger.error(f"Evaluation run failed: {err}")
        raise HTTPException(status_code=500, detail=f"Evaluation execution failed: {str(err)}")


@router.get("/runs", response_model=List[EvaluationRunResponse])
def list_evaluation_runs(
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    Retrieves historical evaluation runs ordered by most recent first.
    """
    runs = db.query(EvaluationRun).order_by(EvaluationRun.started_at.desc()).limit(limit).all()
    return runs


@router.get("/runs/{run_id}", response_model=EvaluationRunDetailResponse)
def get_evaluation_run_detail(
    run_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieves detailed results and question-by-question breakdown for a specific evaluation run.
    """
    run_record = db.query(EvaluationRun).filter(EvaluationRun.id == run_id).first()
    if not run_record:
        raise HTTPException(status_code=404, detail=f"Evaluation run '{run_id}' not found.")
    
    return run_record
