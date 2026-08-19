# Phase 9: Multimodal Document RAG Evaluation & Observability Framework

This framework provides deterministic, reproducible benchmarking and evaluation for the Multimodal RAG System.

---

## 1. Evaluation Dataset (`datasets/phase9_questions.json`)
The evaluation dataset consists of manually defined ground-truth test cases derived from actual document contents (e.g. `multimodal_rag_test.pdf`).

Each test case contains:
- `id`: Unique identifier (e.g., `q001`).
- `question`: Natural language question.
- `expected_answer`: Manually defined target answer string.
- `acceptable_variants`: List of allowed regex/phrase variants (e.g. `["149,270", "₹149,270"]`).
- `required_facts`: Sub-strings or facts required for complex multi-item questions.
- `expected_pages`: List of 1-indexed document page numbers containing evidence.
- `expected_source_types`: `TEXT`, `TABLE`, `OCR`, `VISUAL`, `CROSS_SOURCE`, or `NEGATIVE`.
- `insufficient_evidence_expected`: Boolean indicating whether the engine is expected to refuse to answer due to missing facts.

---

## 2. Metrics & Definitions

### A. Retrieval Metrics
- **Recall@K**: Proportion of expected evidence pages present in top-K retrieved vector chunks.
- **Hit Rate@K**: Binary flag indicating whether at least one expected page was retrieved in top-K.

### B. Answer Accuracy
- Calculated via deterministic fact and variant matching without forcing exact string equality.
- Evaluates whether expected key facts or acceptable variants are present in the response.

### C. Citation Correctness
- **Citation Presence Rate**: % of answered queries returning citations.
- **Citation Accuracy**: Verifies that cited page numbers and source types match actual ground-truth evidence pages.

### D. Grounding & Hallucination Definitions
- **Grounded**: `true` if all facts in the generated answer appear in the retrieved evidence snippets, or if the model correctly refuses an unanswerable question (`insufficient_evidence: true`).
- **Hallucination Rate**:
  $$\text{Hallucination Rate} = \frac{\text{Number of unsupported answers}}{\text{Total evaluation questions}}$$
  *Note*: Refusal to answer an unanswerable question (e.g. `q011` passport number) counts as **grounded** and **non-hallucinated**.

### E. Modality Performance Breakdown
Performance is tracked separately across document modalities:
- **TEXT**: Native PDF text sections.
- **TABLE**: Extracted structured financial/itemized tables.
- **OCR**: Embedded scanned images, delivery slips, and forms.
- **VISUAL**: Rendered charts, graphs, and visual layouts.

---

## 3. Running Evaluation Benchmarks

### Command Line Interface
```bash
cd backend
python -m evaluation.runner
```

### REST API Endpoints
- `POST /api/v1/evaluation/run` - Trigger a new evaluation benchmark run.
- `GET /api/v1/evaluation/runs` - List past evaluation run history.
- `GET /api/v1/evaluation/runs/{run_id}` - Retrieve detailed question-by-question breakdown.

### Frontend Dashboard
Access the **Evaluation & Observability** tab in the web application (`http://localhost:5173`) to view interactive metric cards, modality charts, latency stats, and failed question analysis.

---

## 4. Regression Testing
Run `pytest tests/test_phase9_evaluation.py` to verify evaluator logic and API endpoints in isolation using mock data. Run `pytest tests/` for full end-to-end integration testing.
