import os
import json
import time
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

from app.db.session import SessionLocal
from app.models.document import Document
from app.models.evaluation import EvaluationRun, EvaluationResult
from app.rag.retriever import DocumentRetriever
from app.rag.qa_service import answer_question

from evaluation.evaluators.retrieval import evaluate_retrieval
from evaluation.evaluators.answer import evaluate_answer
from evaluation.evaluators.citation import evaluate_citations
from evaluation.evaluators.grounding import evaluate_grounding
from evaluation.report import generate_terminal_report

logger = logging.getLogger(__name__)

DATASETS_DIR = os.path.join(os.path.dirname(__file__), "datasets")

class EvaluationRunner:
    def __init__(self, dataset_name: str = "phase9_questions"):
        self.dataset_name = dataset_name
        self.dataset_path = os.path.join(DATASETS_DIR, f"{dataset_name}.json")
        self.retriever = DocumentRetriever()

    def load_dataset(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.dataset_path):
            raise FileNotFoundError(f"Evaluation dataset file not found: {self.dataset_path}")
        with open(self.dataset_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def run_evaluation(self, db_session=None) -> Dict[str, Any]:
        close_session = False
        if db_session is None:
            db_session = SessionLocal()
            close_session = True

        dataset = self.load_dataset()
        started_at = datetime.utcnow()

        # Find target approved test document ID
        target_doc = db_session.query(Document).filter(
            Document.filename.like("%multimodal_rag_test%")
        ).first()

        doc_id = target_doc.id if target_doc else None

        run_record = EvaluationRun(
            dataset_name=self.dataset_name,
            started_at=started_at,
            total_questions=len(dataset)
        )
        db_session.add(run_record)
        db_session.commit()

        results_list = []
        passed_count = 0
        failed_count = 0

        r1_list, r3_list, r5_list = [], [], []
        citation_correct_list = []
        grounding_list = []
        hallucination_list = []
        latencies = []

        modality_totals = {"TEXT": 0, "TABLE": 0, "OCR": 0, "VISUAL": 0, "CROSS_SOURCE": 0, "NEGATIVE": 0}
        modality_correct = {"TEXT": 0, "TABLE": 0, "OCR": 0, "VISUAL": 0, "CROSS_SOURCE": 0, "NEGATIVE": 0}

        for q_item in dataset:
            q_id = q_item["id"]
            question = q_item["question"]
            expected_answer = q_item["expected_answer"]
            acceptable_variants = q_item.get("acceptable_variants", [])
            required_facts = q_item.get("required_facts", [])
            expected_pages = q_item.get("expected_pages", [])
            expected_source_types = q_item.get("expected_source_types", [])
            insufficient_expected = q_item.get("insufficient_evidence_expected", False)
            modality = q_item.get("modality", "TEXT")

            start_t = time.time()
            error_msg = None
            retrieved_chunks = []
            qa_res = None

            try:
                # 1. Vector Retrieval
                retrieved_chunks = self.retriever.search(
                    query=question,
                    top_k=5,
                    document_id=doc_id
                )

                # 2. Grounded QA Engine Answer
                qa_res = answer_question(
                    query=question,
                    top_k=5,
                    document_id=doc_id,
                    db=db_session
                )
            except Exception as ex:
                error_msg = str(ex)
                logger.error(f"Error evaluating question {q_id}: {ex}")

            end_t = time.time()
            latency_ms = round((end_t - start_t) * 1000, 2)
            latencies.append(latency_ms)

            actual_answer = qa_res.answer if qa_res else "Error processing request"
            insufficient_actual = qa_res.insufficient_evidence if qa_res else True
            citations = [c.model_dump() for c in qa_res.citations] if qa_res else []

            # 3. Evaluators
            ret_eval = evaluate_retrieval(retrieved_chunks, expected_pages)
            ans_eval = evaluate_answer(
                actual_answer, expected_answer, acceptable_variants, required_facts,
                insufficient_expected, insufficient_actual
            )
            cit_eval = evaluate_citations(citations, expected_pages, expected_source_types, insufficient_expected)
            grd_eval = evaluate_grounding(actual_answer, retrieved_chunks, required_facts, insufficient_expected, insufficient_actual)

            is_passed = ans_eval["is_correct"]
            if is_passed:
                passed_count += 1
            else:
                failed_count += 1

            r1_list.append(ret_eval["recall_at_1"])
            r3_list.append(ret_eval["recall_at_3"])
            r5_list.append(ret_eval["recall_at_5"])
            citation_correct_list.append(1.0 if cit_eval["is_correct"] else 0.0)
            grounding_list.append(1.0 if grd_eval["grounded"] else 0.0)
            hallucination_list.append(1.0 if grd_eval["hallucination"] else 0.0)

            modality_totals[modality] = modality_totals.get(modality, 0) + 1
            if is_passed:
                modality_correct[modality] = modality_correct.get(modality, 0) + 1

            res_record = EvaluationResult(
                run_id=run_record.id,
                question_id=q_id,
                question=question,
                expected_answer=expected_answer,
                actual_answer=actual_answer,
                retrieval_hit=ret_eval["hit_at_5"],
                answer_correct=ans_eval["is_correct"],
                citation_correct=cit_eval["is_correct"],
                grounded=grd_eval["grounded"],
                insufficient_evidence=insufficient_actual,
                source_type=modality,
                latency_ms=latency_ms,
                error=error_msg,
                details={
                    "retrieval": ret_eval,
                    "answer_eval": ans_eval,
                    "citation_eval": cit_eval,
                    "grounding_eval": grd_eval
                }
            )
            db_session.add(res_record)
            results_list.append(res_record)

        completed_at = datetime.utcnow()
        total_q = len(dataset)

        run_record.completed_at = completed_at
        run_record.passed_count = passed_count
        run_record.failed_count = failed_count
        run_record.accuracy = round(passed_count / total_q, 4) if total_q else 0.0
        
        run_record.recall_at_1 = round(sum(r1_list) / len(r1_list), 4) if r1_list else 0.0
        run_record.recall_at_3 = round(sum(r3_list) / len(r3_list), 4) if r3_list else 0.0
        run_record.recall_at_5 = round(sum(r5_list) / len(r5_list), 4) if r5_list else 0.0
        
        run_record.citation_accuracy = round(sum(citation_correct_list) / len(citation_correct_list), 4) if citation_correct_list else 0.0
        run_record.grounding_rate = round(sum(grounding_list) / len(grounding_list), 4) if grounding_list else 0.0
        run_record.hallucination_rate = round(sum(hallucination_list) / len(hallucination_list), 4) if hallucination_list else 0.0

        run_record.text_accuracy = round(modality_correct["TEXT"] / modality_totals["TEXT"], 4) if modality_totals.get("TEXT") else 1.0
        run_record.table_accuracy = round(modality_correct["TABLE"] / modality_totals["TABLE"], 4) if modality_totals.get("TABLE") else 1.0
        run_record.ocr_accuracy = round(modality_correct["OCR"] / modality_totals["OCR"], 4) if modality_totals.get("OCR") else 1.0
        run_record.visual_accuracy = round(modality_correct["VISUAL"] / modality_totals["VISUAL"], 4) if modality_totals.get("VISUAL") else 1.0

        run_record.avg_latency_ms = round(sum(latencies) / len(latencies), 2) if latencies else 0.0
        
        db_session.commit()

        summary_dict = {
            "run_id": run_record.id,
            "dataset_name": self.dataset_name,
            "total_questions": total_q,
            "passed_count": passed_count,
            "failed_count": failed_count,
            "accuracy": run_record.accuracy,
            "recall_at_1": run_record.recall_at_1,
            "recall_at_3": run_record.recall_at_3,
            "recall_at_5": run_record.recall_at_5,
            "citation_accuracy": run_record.citation_accuracy,
            "grounding_rate": run_record.grounding_rate,
            "hallucination_rate": run_record.hallucination_rate,
            "text_accuracy": run_record.text_accuracy,
            "table_accuracy": run_record.table_accuracy,
            "ocr_accuracy": run_record.ocr_accuracy,
            "visual_accuracy": run_record.visual_accuracy,
            "avg_latency_ms": run_record.avg_latency_ms
        }

        if close_session:
            db_session.close()

        return summary_dict


if __name__ == "__main__":
    runner = EvaluationRunner("phase9_questions")
    res = runner.run_evaluation()
    print(generate_terminal_report(res))
