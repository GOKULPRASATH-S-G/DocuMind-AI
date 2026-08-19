from typing import Dict, Any

def generate_terminal_report(run_data: Dict[str, Any]) -> str:
    """Generates a clean, professional terminal summary table for evaluation runs."""
    total = run_data.get("total_questions", 0)
    passed = run_data.get("passed_count", 0)
    failed = run_data.get("failed_count", 0)
    accuracy = run_data.get("accuracy", 0.0) * 100
    
    r1 = run_data.get("recall_at_1", 0.0) * 100
    r3 = run_data.get("recall_at_3", 0.0) * 100
    r5 = run_data.get("recall_at_5", 0.0) * 100
    
    citation_acc = run_data.get("citation_accuracy", 0.0) * 100
    grounding = run_data.get("grounding_rate", 0.0) * 100
    hallucination = run_data.get("hallucination_rate", 0.0) * 100
    
    txt_acc = run_data.get("text_accuracy", 0.0) * 100
    tbl_acc = run_data.get("table_accuracy", 0.0) * 100
    ocr_acc = run_data.get("ocr_accuracy", 0.0) * 100
    vis_acc = run_data.get("visual_accuracy", 0.0) * 100
    
    latency = run_data.get("avg_latency_ms", 0.0)

    lines = [
        "========================================",
        "MULTIMODAL RAG EVALUATION BENCHMARK",
        "========================================",
        f"Dataset: {run_data.get('dataset_name', 'phase9_questions')}",
        f"Questions Evaluated: {total} (Passed: {passed}, Failed: {failed})",
        "----------------------------------------",
        f"Answer Accuracy:    {accuracy:.2f}%",
        f"Recall@1:           {r1:.2f}%",
        f"Recall@3:           {r3:.2f}%",
        f"Recall@5:           {r5:.2f}%",
        f"Citation Accuracy:  {citation_acc:.2f}%",
        f"Grounding Rate:     {grounding:.2f}%",
        f"Hallucination Rate: {hallucination:.2f}%",
        "----------------------------------------",
        "MODALITY ACCURACY BREAKDOWN:",
        f"  TEXT:    {txt_acc:.2f}%",
        f"  TABLE:   {tbl_acc:.2f}%",
        f"  OCR:     {ocr_acc:.2f}%",
        f"  VISUAL:  {vis_acc:.2f}%",
        "----------------------------------------",
        f"Average QA Latency: {latency:.1f} ms",
        "========================================"
    ]
    return "\n".join(lines)
