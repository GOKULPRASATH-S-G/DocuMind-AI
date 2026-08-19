import uuid
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from app.core.config import settings

logger = logging.getLogger(__name__)


class DocumentChunkData(BaseModel):
    chunk_id: str
    document_id: str
    page_number: int
    chunk_index: int
    text: str
    source_type: str  # TEXT, OCR, TABLE
    metadata: Dict[str, Any]


def chunk_document_pages(
    normalized_data: Dict[str, Any],
    chunk_size: int = settings.RAG_CHUNK_SIZE,
    chunk_overlap: int = settings.RAG_CHUNK_OVERLAP,
    filename: Optional[str] = None,
    document_id: Optional[str] = None
) -> List[DocumentChunkData]:
    """
    Page-aware Document & Table Chunker.
    Chunks text by page boundaries and converts tables into atomic structured chunks without splitting table rows.
    """
    doc_id = document_id or normalized_data.get("document_id") or str(uuid.uuid4())
    filename = filename or normalized_data.get("filename", "document.pdf")
    chunks: List[DocumentChunkData] = []
    global_chunk_idx = 0

    # 1. Process Pages (Text / OCR)
    pages = normalized_data.get("pages", [])
    for pg in pages:
        page_num = pg.get("page_number", 1)
        source = pg.get("source", "TEXT")
        text_content = pg.get("text", "").strip()

        if not text_content:
            continue

        # Split text content into overlapping windows if length exceeds chunk_size
        if len(text_content) <= chunk_size:
            text_splits = [text_content]
        else:
            text_splits = _split_text_with_overlap(text_content, chunk_size, chunk_overlap)

        for split_text in text_splits:
            chunk_id = f"{doc_id}_p{page_num}_c{global_chunk_idx}"
            chunks.append(
                DocumentChunkData(
                    chunk_id=chunk_id,
                    document_id=doc_id,
                    page_number=page_num,
                    chunk_index=global_chunk_idx,
                    text=split_text,
                    source_type=source,
                    metadata={
                        "filename": filename,
                        "document_id": doc_id,
                        "page_number": page_num,
                        "chunk_index": global_chunk_idx,
                        "source_type": source
                    }
                )
            )
            global_chunk_idx += 1

    # 2. Process Tables (Atomic structured chunks)
    tables = normalized_data.get("tables", [])
    for idx, tb in enumerate(tables):
        page_num = tb.get("page_number", 1)
        headers = tb.get("headers", [])
        rows = tb.get("rows", [])

        table_lines = [f"--- TABLE {idx + 1} (PAGE {page_num}) ---\nSOURCE: TABLE\n"]
        if headers:
            table_lines.append(" | ".join(headers))
            table_lines.append("-" * 35)
        for r in rows:
            table_lines.append(" | ".join(r))

        table_text = "\n".join(table_lines)
        chunk_id = f"{doc_id}_p{page_num}_tbl{idx}_c{global_chunk_idx}"

        chunks.append(
            DocumentChunkData(
                chunk_id=chunk_id,
                document_id=doc_id,
                page_number=page_num,
                chunk_index=global_chunk_idx,
                text=table_text,
                source_type="TABLE",
                metadata={
                    "filename": filename,
                    "document_id": doc_id,
                    "page_number": page_num,
                    "chunk_index": global_chunk_idx,
                    "source_type": "TABLE",
                    "table_index": idx
                }
            )
        )
        global_chunk_idx += 1

    # 3. Process Visual Artifacts (Searchable visual evidence representation)
    visual_artifacts = normalized_data.get("visual_artifacts", [])
    for idx, vis in enumerate(visual_artifacts):
        page_num = vis.get("page_number", 1)
        image_id = vis.get("image_id", f"img_p{page_num}_{idx}")
        v_type = vis.get("visual_type", "UNKNOWN_VISUAL")
        desc = vis.get("description", "Visual document artifact.")
        kv_pairs = vis.get("key_values", [])

        kv_lines = []
        if isinstance(kv_pairs, list):
            for kv in kv_pairs:
                if isinstance(kv, dict):
                    kv_lines.append(f"{kv.get('label', '')}: {kv.get('value', '')}")
        
        vis_text = (
            f"VISUAL DOCUMENT EVIDENCE\n"
            f"Document: {filename}\n"
            f"Page: {page_num}\n"
            f"Visual Type: {v_type}\n"
            f"Image ID: {image_id}\n\n"
            f"Description:\n{desc}"
        )
        if kv_lines:
            vis_text += f"\n\nKey Values:\n" + "\n".join(kv_lines)

        chunk_id = f"{doc_id}_p{page_num}_vis{idx}_c{global_chunk_idx}"
        chunks.append(
            DocumentChunkData(
                chunk_id=chunk_id,
                document_id=doc_id,
                page_number=page_num,
                chunk_index=global_chunk_idx,
                text=vis_text,
                source_type="VISUAL",
                metadata={
                    "filename": filename,
                    "document_id": doc_id,
                    "page_number": page_num,
                    "chunk_index": global_chunk_idx,
                    "source_type": "VISUAL",
                    "visual_type": v_type,
                    "image_id": image_id,
                    "storage_reference": vis.get("storage_reference", "")
                }
            )
        )
        global_chunk_idx += 1

    # 4. Fallback: If pages, tables, and visual artifacts are empty
    if not chunks and isinstance(normalized_data, dict):

        lines = []
        for k, v in normalized_data.items():
            if k in ["document_id", "filename"]:
                continue
            lines.append(f"{k}: {v}")
        fallback_text = "\n".join(lines).strip()
        if fallback_text:
            text_splits = _split_text_with_overlap(fallback_text, chunk_size, chunk_overlap)
            for split_text in text_splits:
                chunk_id = f"{doc_id}_p1_c{global_chunk_idx}"
                chunks.append(
                    DocumentChunkData(
                        chunk_id=chunk_id,
                        document_id=doc_id,
                        page_number=1,
                        chunk_index=global_chunk_idx,
                        text=split_text,
                        source_type="TEXT",
                        metadata={
                            "filename": filename,
                            "document_id": doc_id,
                            "page_number": 1,
                            "chunk_index": global_chunk_idx,
                            "source_type": "TEXT"
                        }
                    )
                )
                global_chunk_idx += 1

    logger.info(f"Chunked document {doc_id} into {len(chunks)} chunks (size={chunk_size}, overlap={chunk_overlap}).")
    return chunks


def _split_text_with_overlap(text: str, chunk_size: int, chunk_overlap: int) -> List[str]:
    """Helper to split text into overlapping character slices at word boundaries."""
    splits = []
    start = 0
    text_len = len(text)

    while start < text_len:
        end = min(start + chunk_size, text_len)
        if end < text_len:
            # Adjust end to nearest space to prevent splitting words
            space_idx = text.rfind(" ", start, end)
            if space_idx > start:
                end = space_idx

        splits.append(text[start:end].strip())
        start = max(end - chunk_overlap, end) if end < text_len else text_len

    return [s for s in splits if s]
