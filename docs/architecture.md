# DocuMind AI — System Architecture & Workflow

## High-Level Architecture Diagram

```mermaid
flowchart TD
    User["👤 Enterprise User / Client"]
    Frontend["🎨 Vite + React SPA Frontend"]
    API["⚡ FastAPI REST Gateway"]

    subgraph Storage ["💾 Persistence Layer"]
        DB[("🗄️ PostgreSQL / SQLite DB")]
        Disk[("📁 Local Disk Storage")]
        VectorStore[("⚡ ChromaDB Vector Store")]
    end

    subgraph Processing ["⚙️ Ingestion & Extraction Engine"]
        Ingestion["📄 Page Ingestion Engine (PyMuPDF / pdf2image)"]
        OCR["🔍 OCR Engine (Tesseract OCR)"]
        GeminiExt["🧠 Multimodal Gemini Extraction Engine"]
        Validation["🛡️ Deterministic Validation Engine (Pydantic / Rules)"]
        Confidence["📊 Confidence Scoring & Routing Engine"]
    end

    subgraph HITL ["👥 Human-in-the-Loop"]
        ReviewQueue["📥 Human Review Queue"]
        ReviewAction["✏️ Interactive Field Correction & Approval"]
    end

    subgraph RAGEngine ["🔍 Multimodal RAG Engine"]
        Embedder["🔤 Google Gemini / SentenceTransformers Embeddings"]
        Retriever["🎯 Vector Similarity & Page Retriever"]
        Synthesis["💡 Grounded QA Generator (Gemini 2.5 Flash)"]
        CitationEngine["📌 Provenance & Page Citation Engine"]
    end

    User -->|Upload PDF/Images & Query| Frontend
    Frontend -->|JWT Authenticated REST| API

    API -->|Store File & Metadata| DB
    API -->|Save Raw Files| Disk

    API --> Ingestion
    Ingestion -->|Extract Pages & Tables| OCR
    OCR -->|Pass Clean Text + Page Images| GeminiExt
    GeminiExt --> Validation
    Validation --> Confidence

    Confidence -->|Overall Confidence < 85% or Hard Errors| ReviewQueue
    Confidence -->|Overall Confidence >= 85% Approved| Embedder

    ReviewQueue --> ReviewAction
    ReviewAction -->|Approved Correction| Embedder

    Embedder -->|Upsert Chunks & Metadata| VectorStore
    
    API -->|Vector Query| Retriever
    Retriever -->|Top-K Context Chunks| VectorStore
    Retriever --> Synthesis
    Synthesis --> CitationEngine
    CitationEngine -->|Response + Provenance Badges| Frontend
```

---

## Component Breakdown

### 1. API & Gateway Layer (`backend/app/api/v1/`)
- **FastAPI**: Serves RESTful API endpoints for user authentication, document uploads, asynchronous processing, human-in-the-loop review, semantic search, grounded QA, and production observability.
- **JWT Security & Auth**: Password hashing (`passlib`/`bcrypt`), JWT token generation, role-based access control (`ADMIN`, `REVIEWER`, `USER`), and path-traversal file download protection.

### 2. Document Processing Pipeline (`backend/app/services/`)
- **Page Ingestion**: Converts multi-page native and scanned PDFs into structured page models, extracting text layers and native PDF tables via PyMuPDF.
- **OCR Engine (`TesseractOCRProvider`)**: Fallback pipeline for scanned or image-only documents. Runs layout-aware OCR with bounding box word extraction.
- **Gemini Structured Extraction (`GeminiLLMProvider`)**: Uses `gemini-2.5-flash` with Pydantic JSON schemas to extract key fields (invoice numbers, dates, line items, monetary values, project names).
- **Deterministic Validation**: Runs business logic rules (mathematical total checks, date formats, string patterns, mandatory field verification).
- **Confidence Scoring & Routing**: Computes field-level and overall confidence scores. If confidence $< 85\%$ or validation fails, routes document to `NEEDS_REVIEW`.

### 3. Human-in-the-Loop Review Queue (`backend/app/api/v1/endpoints/reviews.py`)
- **Interactive Review Dashboard**: Displays side-by-side original document viewer and field extraction editor.
- **Human Corrections**: Reviewers can edit fields, resolve validation warnings, and explicitly approve or reject document extractions before vector store indexing.
- **Audit Logging**: Every field change and approval action is persisted with user timestamp attribution.

### 4. Vector Search & Grounded RAG (`backend/app/rag/`)
- **ChromaDB Vector Store**: Persists document chunk embeddings enriched with metadata (`document_id`, `page_number`, `source_type`).
- **Grounded QA Generator**: Synthesizes answers strictly using retrieved document context. Refuses unsupported queries cleanly without hallucinations.
- **Page-Level Citations**: Attaches exact document filename, page number, and source type (`TEXT`, `OCR`, `TABLE`, `VISUAL`) to every response.
