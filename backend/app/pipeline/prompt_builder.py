import json
from typing import Dict, Any, List


def format_normalized_document_for_llm(normalized_data: Dict[str, Any]) -> str:
    """
    Formats Phase 2 normalized pages and tables into a clean source-aware document text block
    preserving PAGE NUMBERS and EXTRACTION SOURCES (TEXT, OCR, TABLE).
    """
    formatted_parts: List[str] = []

    pages = normalized_data.get("pages", [])
    for pg in pages:
        page_num = pg.get("page_number", 1)
        source = pg.get("source", "TEXT")
        text = pg.get("text", "").strip()

        formatted_parts.append(f"--- PAGE {page_num} ---\nSOURCE: {source}\n\n{text}")

    tables = normalized_data.get("tables", [])
    for idx, tb in enumerate(tables):
        page_num = tb.get("page_number", 1)
        headers = tb.get("headers", [])
        rows = tb.get("rows", [])

        table_str_lines = []
        if headers:
            table_str_lines.append(" | ".join(headers))
            table_str_lines.append("-" * 30)
        for r in rows:
            table_str_lines.append(" | ".join(r))

        table_content = "\n".join(table_str_lines)
        formatted_parts.append(f"--- TABLE {idx + 1} (PAGE {page_num}) ---\nSOURCE: TABLE\n\n{table_content}")

    return "\n\n".join(formatted_parts)


def get_general_document_extraction_prompt(json_schema: Dict[str, Any]) -> str:
    """
    Constructs LLM instructions for universal document intelligence (Patents, Reports, Manuals, Contracts, Invoices).
    """
    return f"""
You are an expert universal document intelligence and analysis system.
Your task is to extract structured metadata, document summary, key topics, and key entities from the provided document content.

DOCUMENT TYPES INCLUDE:
- Patents / Inventions / Specifications
- Academic & Research Papers
- Financial Invoices & Purchase Orders
- Legal Contracts & Agreements
- Technical Manuals & Engineering Specs
- General Enterprise Reports & Articles

CRITICAL INSTRUCTIONS:
1. Identify the document_title accurately from the main heading or header.
2. Determine document_type (e.g., "Patent Specification", "Research Paper", "Invoice", "Contract", "Technical Manual", "Report").
3. Extract author_or_organization (e.g. Applicant, Author, Publisher, Vendor, Organization).
4. Provide a clear, comprehensive 3-5 sentence summary of what the document is about in the 'summary' field.
5. List primary subjects/topics in 'key_topics'.
6. List important names, organizations, or numbers in 'key_entities'.
7. Put any specific metadata key-value pairs (e.g. Patent Number, Invoice Total, Contract Dates) into 'key_value_metadata'.
8. Output MUST be valid, raw JSON matching the following JSON Schema structure:

JSON Schema Specification:
{json.dumps(json_schema, indent=2)}

Return ONLY the raw JSON object. Do not include markdown code block backticks (e.g. ```json) or any conversational text outside the JSON object.
"""


def get_invoice_extraction_prompt(json_schema: Dict[str, Any]) -> str:
    """
    Constructs strict LLM instructions for Gemini structured invoice data extraction.
    """
    return get_general_document_extraction_prompt(json_schema)
