from typing import List, Dict, Any

def evaluate_citations(
    citations: List[Dict[str, Any]],
    expected_pages: List[int],
    expected_sources: List[str],
    insufficient_expected: bool
) -> Dict[str, Any]:
    """
    Verifies citation accuracy:
    - Presence of citations
    - Page number correctness
    - Source type correctness
    """
    if insufficient_expected:
        # Negative questions should have no citations
        return {
            "has_citation": len(citations) > 0,
            "page_match": True,
            "source_type_match": True,
            "is_correct": len(citations) == 0,
            "reason": "No citation provided for unsupported question as expected" if len(citations) == 0 else "Unexpected citation for negative question"
        }

    if not citations:
        return {
            "has_citation": False,
            "page_match": False,
            "source_type_match": False,
            "is_correct": False,
            "reason": "No citation returned for supported question"
        }

    cited_pages = [c.get("page_number") for c in citations if c.get("page_number") is not None]
    cited_sources = [c.get("source_type") for c in citations if c.get("source_type")]

    expected_pages_set = set(expected_pages)
    expected_sources_set = set(expected_sources)

    page_match = any(p in expected_pages_set for p in cited_pages)
    source_match = not expected_sources_set or any(s in expected_sources_set for s in cited_sources)

    is_correct = page_match and source_match

    return {
        "has_citation": True,
        "page_match": page_match,
        "source_type_match": source_match,
        "is_correct": is_correct,
        "reason": "Citation matches expected page & source type" if is_correct else "Citation page or source type mismatch",
        "cited_pages": cited_pages,
        "cited_sources": cited_sources
    }
