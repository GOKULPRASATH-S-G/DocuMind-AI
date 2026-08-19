import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.visual_artifact import VisualArtifact

logger = logging.getLogger(__name__)


def build_multimodal_context(
    retrieved_chunks: List[Dict[str, Any]],
    db: Optional[Session] = None
) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Combines text, table, OCR, and visual vector chunks into a structured evidence context block.
    Extracts associated visual image file references when visual chunks are retrieved.

    Returns:
    - context_text (str): Formatted evidence string for LLM prompt
    - visual_image_inputs (List[Dict]): List of image dicts containing image_id, page_number, file_path, mime_type
    """
    if not retrieved_chunks:
        return "NO EVIDENCE AVAILABLE.", []

    context_lines = []
    visual_image_inputs = []

    for idx, chunk in enumerate(retrieved_chunks, start=1):
        doc_id = chunk.get("document_id", "unknown_doc")
        filename = chunk.get("filename", "unknown_file")
        page_num = chunk.get("page_number", 1)
        chunk_id = chunk.get("chunk_id", f"chunk_{idx}")
        source_type = chunk.get("source_type", "TEXT")
        text = chunk.get("text", "").strip()
        meta = chunk.get("metadata", {})

        image_id = meta.get("image_id") or chunk.get("image_id")
        storage_ref = meta.get("storage_reference") or chunk.get("storage_reference")

        block = (
            f"SOURCE {idx}\n"
            f"Document ID: {doc_id}\n"
            f"Document: {filename}\n"
            f"Page: {page_num}\n"
            f"Chunk ID: {chunk_id}\n"
            f"Source Type: {source_type}\n"
        )

        if image_id:
            block += f"Image ID: {image_id}\n"

        block += f"Content:\n\"{text}\""
        context_lines.append(block)

        # Check if visual chunk points to an available image file on disk
        if source_type == "VISUAL" or image_id:
            resolved_file_path = None

            if storage_ref:
                potential_path = Path(settings.STORAGE_LOCAL_DIR) / storage_ref
                if potential_path.exists():
                    resolved_file_path = str(potential_path)

            if not resolved_file_path and db and image_id:
                va = db.query(VisualArtifact).filter(VisualArtifact.image_id == image_id).first()
                if va and va.storage_reference:
                    potential_path = Path(settings.STORAGE_LOCAL_DIR) / va.storage_reference
                    if potential_path.exists():
                        resolved_file_path = str(potential_path)

            if resolved_file_path:
                visual_image_inputs.append({
                    "image_id": image_id or f"img_{doc_id}_p{page_num}",
                    "document_id": doc_id,
                    "filename": filename,
                    "page_number": page_num,
                    "file_path": resolved_file_path,
                    "mime_type": "image/png" if resolved_file_path.endswith(".png") else "image/jpeg"
                })

    formatted_context_text = "\n\n".join(context_lines)
    return formatted_context_text, visual_image_inputs
