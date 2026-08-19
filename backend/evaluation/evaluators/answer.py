import re
from typing import List, Dict, Any

def normalize_text(text: str) -> str:
    """Standardizes string for flexible matching (removes punctuation, lowercases, strips spaces)."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    return " ".join(text.split())

def evaluate_answer(
    actual_answer: str,
    expected_answer: str,
    acceptable_variants: List[str],
    required_facts: List[str],
    insufficient_expected: bool,
    insufficient_actual: bool
) -> Dict[str, Any]:
    """
    Evaluates whether the actual model answer satisfies the expected answer criteria.
    Supports variant matching, required facts presence check, and refusal for negative questions.
    """
    if insufficient_expected:
        # Refusal expected for unsupported question
        is_correct = insufficient_actual or ("couldn't find" in actual_answer.lower() or "insufficient" in actual_answer.lower())
        return {
            "is_correct": is_correct,
            "reason": "Correct refusal" if is_correct else "Failed to refuse unsupported question",
            "matched_facts": [],
            "missing_facts": []
        }

    if insufficient_actual and not insufficient_expected:
        return {
            "is_correct": False,
            "reason": "Model returned insufficient evidence when answer exists in document",
            "matched_facts": [],
            "missing_facts": required_facts
        }

    norm_actual = normalize_text(actual_answer)
    norm_expected = normalize_text(expected_answer)

    # 1. Exact or Variant Match
    for variant in [expected_answer] + acceptable_variants:
        norm_var = normalize_text(variant)
        if norm_var and norm_var in norm_actual:
            return {
                "is_correct": True,
                "reason": f"Matched variant: '{variant}'",
                "matched_facts": required_facts,
                "missing_facts": []
            }

    # 2. Required Facts Match (e.g. for multi-item list questions like Laptop, Mouse, etc.)
    matched_facts = []
    missing_facts = []

    for fact in required_facts:
        norm_fact = normalize_text(fact)
        if norm_fact in norm_actual:
            matched_facts.append(fact)
        else:
            missing_facts.append(fact)

    if required_facts and len(matched_facts) == len(required_facts):
        return {
            "is_correct": True,
            "reason": "All required facts present in answer",
            "matched_facts": matched_facts,
            "missing_facts": []
        }

    if required_facts and len(matched_facts) > 0 and len(matched_facts) >= (len(required_facts) * 0.75):
        return {
            "is_correct": True,
            "reason": f"Majority of required facts present ({len(matched_facts)}/{len(required_facts)})",
            "matched_facts": matched_facts,
            "missing_facts": missing_facts
        }

    return {
        "is_correct": False,
        "reason": f"Missing required facts: {missing_facts}",
        "matched_facts": matched_facts,
        "missing_facts": missing_facts
    }
