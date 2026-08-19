import os
import logging
from typing import List, Dict, Any, Optional

try:
    import fitz  # PyMuPDF
except ImportError:
    import pymupdf as fitz

logger = logging.getLogger(__name__)


def detect_page_visual_content(file_path: str, mime_type: str = "application/pdf") -> List[Dict[str, Any]]:
    """
    Analyzes document per page for visual content:
    - Embedded raster images (photos, charts, diagrams)
    - Rendered scanned pages
    - Image-heavy layouts
    Returns structured visual detection metadata per page.
    """
    # Handle image uploads first
    if mime_type and mime_type.startswith("image/"):
        return [{
            "page_number": 1,
            "has_visual_content": True,
            "embedded_images_count": 1,
            "visual_type": "IMAGE",
            "source": "SCANNED_PAGE"
        }]

    if not os.path.exists(file_path):
        logger.error(f"Visual detection failed: File not found at '{file_path}'")
        return []

    results = []


    try:
        doc = fitz.open(file_path)
        for page_num in range(len(doc)):
            page = doc[page_num]
            image_list = page.get_images(full=True)
            text = page.get_text().strip()

            has_visual = len(image_list) > 0 or len(text) < 50
            source_type = "PDF_IMAGE" if len(image_list) > 0 else ("SCANNED_PAGE" if len(text) < 50 else "NONE")
            visual_type = "IMAGE" if len(image_list) > 0 else ("SCANNED_PAGE" if len(text) < 50 else "NONE")

            if len(image_list) == 0 and len(text) >= 50:
                visual_type = "NONE"
                has_visual = False

            results.append({
                "page_number": page_num + 1,
                "has_visual_content": has_visual,
                "embedded_images_count": len(image_list),
                "visual_type": visual_type,
                "source": source_type
            })

        doc.close()
    except Exception as e:
        logger.error(f"Error executing visual content detection on '{file_path}': {e}")
        # Fallback single page
        results.append({
            "page_number": 1,
            "has_visual_content": True,
            "embedded_images_count": 0,
            "visual_type": "UNKNOWN_VISUAL",
            "source": "PDF_IMAGE"
        })

    return results
