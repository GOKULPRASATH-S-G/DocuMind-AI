# DocuMind AI — 2-Minute Portfolio Demo Script

## Overview
This script provides a concise 2-minute walkthrough of **DocuMind AI** for technical screeners, recruiters, and hiring managers.

---

## Timeline & Step-by-Step Walkthrough

### 0:00 – 0:15 | Introduction & Dashboard
- **Presenter Action**: Open the application at `http://localhost:3000`.
- **Narration**: *"Welcome to DocuMind AI, a multimodal enterprise document intelligence platform. Enterprise PDFs are rarely clean markdown — they contain scanned images, embedded tables, and inconsistent layouts. DocuMind AI ingests native and scanned documents, runs OCR and Gemini structured extraction, enforces validation rules with human-in-the-loop review, and powers grounded RAG with page-level citations."*

---

### 0:15 – 0:45 | Native Document Processing Pipeline
- **Presenter Action**:
  1. Select `enterprise_sample_document.pdf` in the upload dropzone and click **Upload Document**.
  2. Click **Phase 2: Page Ingestion**. Highlight the breakdown (`4 Native Text Pages`, `2 Tables Found`).
  3. Click **Phase 4: Extract, Validate & Score Confidence**.
- **Narration**: *"For native PDFs, DocuMind AI extracts vector text and structural tables instantly. Gemini extracts key fields, and our validation engine checks mathematical accuracy and business rules. Here, overall confidence is 96%, auto-approving the document for indexing."*

---

### 0:45 – 1:15 | Scanned PDF & OCR Fallback Processing
- **Presenter Action**:
  1. Select `batch1-0001 (1).pdf` (scanned invoice) and click **Upload Document**.
  2. Click **Phase 2: Page Ingestion**. Highlight the badge: `SCANNED DOCUMENT DETECTED — Tesseract OCR Active`.
  3. Click **Phase 4: Extract, Validate & Score Confidence**. Show extracted invoice metadata (`Invoice #51109338`, `Gross Worth $6,204.19`).
- **Narration**: *"When a scanned invoice with no text layer is uploaded, DocuMind AI automatically detects the missing text layer and routes the document to Tesseract OCR and Gemini Vision. It extracts line items, net worth, VAT, and gross worth accurately."*

---

### 1:15 – 1:45 | Grounded Q&A with Provenance Citations
- **Presenter Action**:
  1. Navigate to the **Grounded Q&A** tab.
  2. Type: `"Who is the project manager?"` $\rightarrow$ Highlight Answer (`Priya Raman`) and Citation (`enterprise_sample_document.pdf — Page 3`).
  3. Type: `"What is the invoice number and gross total?"` $\rightarrow$ Highlight Answer (`Invoice 51109338`, `$6,204.19`) and Citation (`batch1-0001 (1).pdf — Page 1`).
  4. Type: `"What is the employee's passport number?"` $\rightarrow$ Highlight the Amber **Insufficient Evidence** warning card.
- **Narration**: *"Our RAG engine retrieves relevant vector chunks from ChromaDB and synthesizes answers strictly grounded in retrieved evidence, attaching clickable page-level citations. Notice that when asked an unsupported question like passport number, it explicitly refuses to hallucinate."*

---

### 1:45 – 2:00 | Evaluation & System Observability
- **Presenter Action**: Navigate to **Evaluation & Observability** tab. Point out Accuracy, Grounding Rate, Citation Accuracy, and System Health.
- **Narration**: *"Finally, our evaluation dashboard tracks accuracy, recall@5, grounding, and latency across automated benchmarks, ensuring reproducible production quality."*
