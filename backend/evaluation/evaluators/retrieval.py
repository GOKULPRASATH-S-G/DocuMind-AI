from typing import List, Dict, Any

def evaluate_retrieval(retrieved_chunks: List[Dict[str, Any]], expected_pages: List[int]) -> Dict[str, Any]:
    """
    Evaluates vector retrieval performance against expected ground truth page numbers.
    Computes Recall@1, Recall@3, Recall@5, Precision@K, and Hit Rate@K.
    """
    if not expected_pages:
        # Negative / hallucination case where no evidence page is expected
        return {
            "hit_at_1": True,
            "hit_at_3": True,
            "hit_at_5": True,
            "recall_at_1": 1.0,
            "recall_at_3": 1.0,
            "recall_at_5": 1.0,
            "precision_at_5": 1.0,
            "retrieved_pages": []
        }

    retrieved_pages = [chunk.get("page_number") for chunk in retrieved_chunks if chunk.get("page_number") is not None]
    
    top_1 = set(retrieved_pages[:1])
    top_3 = set(retrieved_pages[:3])
    top_5 = set(retrieved_pages[:5])
    expected_set = set(expected_pages)

    hit_1 = len(top_1.intersection(expected_set)) > 0
    hit_3 = len(top_3.intersection(expected_set)) > 0
    hit_5 = len(top_5.intersection(expected_set)) > 0

    recall_1 = len(top_1.intersection(expected_set)) / len(expected_set)
    recall_3 = len(top_3.intersection(expected_set)) / len(expected_set)
    recall_5 = len(top_5.intersection(expected_set)) / len(expected_set)

    precision_5 = len(top_5.intersection(expected_set)) / min(5, len(retrieved_pages)) if retrieved_pages else 0.0

    return {
        "hit_at_1": hit_1,
        "hit_at_3": hit_3,
        "hit_at_5": hit_5,
        "recall_at_1": round(recall_1, 4),
        "recall_at_3": round(recall_3, 4),
        "recall_at_5": round(recall_5, 4),
        "precision_at_5": round(precision_5, 4),
        "retrieved_pages": retrieved_pages
    }
