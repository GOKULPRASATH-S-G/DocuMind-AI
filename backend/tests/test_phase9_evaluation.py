import pytest
from unittest.mock import patch, MagicMock
from evaluation.evaluators.retrieval import evaluate_retrieval
from evaluation.evaluators.answer import evaluate_answer
from evaluation.evaluators.citation import evaluate_citations
from evaluation.evaluators.grounding import evaluate_grounding
from evaluation.runner import EvaluationRunner
from app.models.evaluation import EvaluationRun, EvaluationResult

def test_dataset_loading():
    runner = EvaluationRunner("phase9_questions")
    dataset = runner.load_dataset()
    assert len(dataset) >= 12
    assert dataset[0]["id"] == "q001"
    assert "question" in dataset[0]
    assert "expected_answer" in dataset[0]

def test_retrieval_evaluator():
    retrieved = [{"page_number": 2}, {"page_number": 1}, {"page_number": 4}]
    res = evaluate_retrieval(retrieved, [2])
    assert res["hit_at_1"] is True
    assert res["recall_at_1"] == 1.0
    assert res["recall_at_5"] == 1.0

def test_answer_evaluator_exact_and_facts():
    # Variant match
    res1 = evaluate_answer("Total amount is 149,270", "149270", ["149,270"], ["149270"], False, False)
    assert res1["is_correct"] is True

    # Multi-fact match
    res2 = evaluate_answer(
        "Purchased items: Laptop, Wireless Mouse, Keyboard, Monitor",
        "Laptop, Mouse",
        [],
        ["Laptop", "Wireless Mouse", "Keyboard", "Monitor"],
        False,
        False
    )
    assert res2["is_correct"] is True

    # Refusal match for unsupported question
    res3 = evaluate_answer(
        "I couldn't find this information in the provided documents.",
        "Refusal expected",
        [],
        [],
        True,
        True
    )
    assert res3["is_correct"] is True

def test_citation_evaluator():
    citations = [{"page_number": 4, "source_type": "OCR"}]
    res = evaluate_citations(citations, [4], ["OCR"], False)
    assert res["is_correct"] is True
    assert res["page_match"] is True

def test_grounding_evaluator():
    chunks = [{"text": "Delivery ID: DEL-88421 Received By: Arun Kumar"}]
    res = evaluate_grounding("Arun Kumar received the delivery", chunks, ["Arun Kumar"], False, False)
    assert res["grounded"] is True
    assert res["hallucination"] is False

def test_evaluation_api_endpoints(client, db_session):
    # Seed dummy run into DB
    run_rec = EvaluationRun(
        id="test-run-123",
        dataset_name="phase9_questions",
        total_questions=12,
        passed_count=12,
        accuracy=1.0
    )
    db_session.add(run_rec)
    db_session.commit()

    mock_summary = {
        "run_id": "test-run-123",
        "dataset_name": "phase9_questions",
        "started_at": "2026-08-18T11:00:00",
        "completed_at": "2026-08-18T11:00:05",
        "total_questions": 12,
        "passed_count": 12,
        "failed_count": 0,
        "accuracy": 1.0,
        "recall_at_1": 1.0,
        "recall_at_3": 1.0,
        "recall_at_5": 1.0,
        "citation_accuracy": 1.0,
        "grounding_rate": 1.0,
        "hallucination_rate": 0.0,
        "text_accuracy": 1.0,
        "table_accuracy": 1.0,
        "ocr_accuracy": 1.0,
        "visual_accuracy": 1.0,
        "avg_latency_ms": 150.0
    }

    with patch.object(EvaluationRunner, "run_evaluation", return_value=mock_summary):
        # 1. Trigger run
        post_res = client.post("/api/v1/evaluation/run", json={"dataset": "phase9_questions"})
        assert post_res.status_code == 201
        run_data = post_res.json()
        assert run_data["dataset_name"] == "phase9_questions"

        # 2. List runs
        list_res = client.get("/api/v1/evaluation/runs")
        assert list_res.status_code == 200
        assert len(list_res.json()) >= 1

        # 3. Get run detail
        run_id = list_res.json()[0]["run_id"]
        detail_res = client.get(f"/api/v1/evaluation/runs/{run_id}")
        assert detail_res.status_code == 200
        assert detail_res.json()["run_id"] == run_id

