import os
import uuid
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    import fitz  # PyMuPDF
except ImportError:
    import pymupdf as fitz

from PIL import Image
import io

from app.core.config import settings

logger = logging.getLogger(__name__)


def extract_document_visual_artifacts(
    file_path: str,
    document_id: str,
    mime_type: str = "application/pdf"
) -> List[Dict[str, Any]]:
    """
    Extracts embedded images and scanned page renderings from PDF or image files.
    Saves image artifacts to local storage directory and returns metadata list.
    """
    if not os.path.exists(file_path):
        logger.error(f"Image extraction failed: file '{file_path}' does not exist.")
        return []

    base_storage_dir = Path(settings.STORAGE_LOCAL_DIR) / "documents" / document_id
    images_dir = base_storage_dir / "images"
    pages_dir = base_storage_dir / "pages"
    images_dir.mkdir(parents=True, exist_ok=True)
    pages_dir.mkdir(parents=True, exist_ok=True)

    extracted_artifacts = []

    # Handle image file upload directly
    if mime_type.startswith("image/"):
        try:
            with open(file_path, "rb") as f:
                img_bytes = f.read()

            with Image.open(io.BytesIO(img_bytes)) as img:
                width, height = img.size
                format_ext = (img.format or "png").lower()

            image_id = f"img_{document_id}_p1_0"
            rel_path = f"documents/{document_id}/pages/page_1.{format_ext}"
            abs_path = base_storage_dir / "pages" / f"page_1.{format_ext}"

            with open(abs_path, "wb") as f:
                f.write(img_bytes)

            extracted_artifacts.append({
                "image_id": image_id,
                "document_id": document_id,
                "page_number": 1,
                "image_index": 0,
                "storage_reference": rel_path,
                "absolute_path": str(abs_path),
                "mime_type": f"image/{format_ext}",
                "width": width,
                "height": height,
                "source": "SCANNED_PAGE",
                "visual_type": "SCANNED_PAGE"
            })
            return extracted_artifacts
        except Exception as img_err:
            logger.error(f"Failed to extract uploaded image artifact: {img_err}")
            return []

    # PDF Processing via PyMuPDF
    try:
        doc = fitz.open(file_path)
        for page_index in range(len(doc)):
            page_num = page_index + 1
            page = doc[page_index]
            text = page.get_text().strip()
            image_list = page.get_images(full=True)

            # 1. Extract embedded raster images
            for img_idx, img_info in enumerate(image_list):
                xref = img_info[0]
                try:
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]
                    width = base_image.get("width", 0)
                    height = base_image.get("height", 0)

                    # Ignore tiny icons/decorations smaller than 50x50
                    if width > 0 and height > 0 and (width < 50 or height < 50):
                        continue

                    image_id = f"img_{document_id}_p{page_num}_{img_idx}"
                    filename = f"img_p{page_num}_{img_idx}.{image_ext}"
                    rel_path = f"documents/{document_id}/images/{filename}"
                    abs_path = images_dir / filename

                    with open(abs_path, "wb") as f:
                        f.write(image_bytes)

                    extracted_artifacts.append({
                        "image_id": image_id,
                        "document_id": document_id,
                        "page_number": page_num,
                        "image_index": img_idx,
                        "storage_reference": rel_path,
                        "absolute_path": str(abs_path),
                        "mime_type": f"image/{image_ext}",
                        "width": width,
                        "height": height,
                        "source": "PDF_IMAGE",
                        "visual_type": "UNKNOWN_VISUAL"
                    })
                except Exception as extract_err:
                    logger.warning(f"Error extracting image xref {xref} on page {page_num}: {extract_err}")

            # 2. Render page image for scanned/image-heavy pages
            if len(text) < 50 or len(image_list) == 0:
                try:
                    pix = page.get_pixmap(dpi=150)
                    page_img_bytes = pix.tobytes("png")
                    image_id = f"scanned_p{page_num}_{document_id}"
                    filename = f"page_{page_num}.png"
                    rel_path = f"documents/{document_id}/pages/{filename}"
                    abs_path = pages_dir / filename

                    with open(abs_path, "wb") as f:
                        f.write(page_img_bytes)

                    extracted_artifacts.append({
                        "image_id": image_id,
                        "document_id": document_id,
                        "page_number": page_num,
                        "image_index": 0,
                        "storage_reference": rel_path,
                        "absolute_path": str(abs_path),
                        "mime_type": "image/png",
                        "width": pix.width,
                        "height": pix.height,
                        "source": "SCANNED_PAGE",
                        "visual_type": "SCANNED_PAGE"
                    })
                except Exception as render_err:
                    logger.warning(f"Error rendering scanned page image for page {page_num}: {render_err}")

        doc.close()
    except Exception as e:
        logger.error(f"Error extracting visual artifacts from '{file_path}': {e}")

    logger.info(f"Extracted {len(extracted_artifacts)} visual artifacts for document '{document_id}'.")
    return extracted_artifacts
