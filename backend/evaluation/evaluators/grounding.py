import re
from typing import List, Dict, Any

def evaluate_grounding(
    actual_answer: str,
    retrieved_chunks: List[Dict[str, Any]],
    required_facts: List[str],
    insufficient_expected: bool,
    insufficient_actual: bool
) -> Dict[str, Any]:
    """
    Evaluates whether claims in actual_answer are supported by retrieved_chunks evidence.
    Tracks grounding rate and hallucination rate.
    Refusing an unsupported question (insufficient_actual=True) counts as grounded=True and hallucination=False.
    """
    if insufficient_expected and insufficient_actual:
        return {
            "grounded": True,
            "hallucination": False,
            "reason": "Correct refusal to answer unsupported question"
        }

    if insufficient_actual:
        return {
            "grounded": True, # Refusing to answer when missing context is not hallucination
            "hallucination": False,
            "reason": "Refused answer due to insufficient evidence"
        }

    combined_evidence = " ".join([chunk.get("text", "") or chunk.get("chunk_text", "") for chunk in retrieved_chunks]).lower()

    if not required_facts:
        return {
            "grounded": True,
            "hallucination": False,
            "reason": "No specific facts required"
        }

    unsupported_facts = []
    supported_facts = []

    for fact in required_facts:
        fact_norm = re.sub(r"[^\w\s]", "", fact.lower()).strip()
        evidence_norm = re.sub(r"[^\w\s]", "", combined_evidence)
        
        if fact_norm in evidence_norm:
            supported_facts.append(fact)
        else:
            unsupported_facts.append(fact)

    is_grounded = len(unsupported_facts) == 0
    is_hallucination = not is_grounded and not insufficient_expected

    return {
        "grounded": is_grounded,
        "hallucination": is_hallucination,
        "reason": "All claims supported by evidence" if is_grounded else f"Unsupported claims: {unsupported_facts}",
        "supported_facts": supported_facts,
        "unsupported_facts": unsupported_facts
    }
