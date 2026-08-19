# DocuMind AI — Resume & Portfolio Descriptions

## Project Descriptions

### Short Version (1-liner)
"Engineered a multimodal document intelligence platform using Python, FastAPI, Tesseract OCR, Gemini 2.5 Flash, ChromaDB, and React to extract structured data from native/scanned enterprise PDFs with confidence validation and grounded RAG citations."

### Long Version (Paragraph)
"Engineered a multimodal document RAG platform that processes native and scanned enterprise PDFs using OCR, table/visual extraction, Gemini-based structured extraction, confidence validation, and a human review queue. Indexed validated content into ChromaDB vector storage and implemented grounded question answering with page-level source citations and reproducible evaluation benchmarks."

---

## Targeted Resume Bullets

• **Multimodal Ingestion Pipeline**: Built and shipped an enterprise document ingestion pipeline in Python and FastAPI that extracted structured data from native and scanned PDFs using layout-aware Tesseract OCR, PyMuPDF table extraction, and Gemini 2.5 Flash.

• **Validation & Human-in-the-Loop Queue**: Implemented deterministic business rule validation and field confidence scoring to route low-confidence document extractions ($< 85\%$) to a React human review dashboard before indexing.

• **Grounded RAG & Citations**: Developed a grounded document Q&A engine using ChromaDB vector search and page-level source attribution (`TEXT`, `OCR`, `TABLE`, `VISUAL`), guaranteeing factual answers while rejecting unsupported queries.
