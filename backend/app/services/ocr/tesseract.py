import io
import os
import shutil
import logging
from typing import Dict, Any, List
from PIL import Image
import pytesseract
from app.services.ocr.base import BaseOCRProvider
from app.core.config import settings

logger = logging.getLogger(__name__)


def _configure_tesseract_path() -> tuple[bool, str]:
    """
    Locates Tesseract-OCR executable, configures TESSDATA_PREFIX to local workspace or Tesseract folder,
    and checks if eng.traineddata exists.
    """
    cmd_path = None
    if settings.TESSERACT_CMD and os.path.exists(settings.TESSERACT_CMD):
        cmd_path = settings.TESSERACT_CMD
    elif shutil.which("tesseract"):
        cmd_path = shutil.which("tesseract")
    else:
        possible_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe")
        ]
        for p in possible_paths:
            if os.path.exists(p):
                cmd_path = p
                break

    if not cmd_path:
        return False, "Tesseract binary not found on host machine."

    pytesseract.pytesseract.tesseract_cmd = cmd_path
    
    # 1. Check local project backend/tessdata directory
    project_backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    local_tessdata = os.path.join(project_backend_dir, "tessdata")
    local_eng = os.path.join(local_tessdata, "eng.traineddata")

    # 2. Check installation tessdata directory
    system_tessdata = os.path.join(os.path.dirname(cmd_path), "tessdata")
    system_eng = os.path.join(system_tessdata, "eng.traineddata")

    # Check if we can copy local eng.traineddata to system tessdata if system tessdata exists
    if os.path.exists(local_eng):
        if os.path.exists(system_tessdata) and not os.path.exists(system_eng):
            try:
                shutil.copy2(local_eng, system_eng)
                logger.info(f"Copied eng.traineddata from local workspace to: {system_eng}")
            except Exception as e:
                logger.warning(f"Could not copy eng.traineddata to system directory ({e}). Using local tessdata.")

    if os.path.exists(system_eng):
        os.environ["TESSDATA_PREFIX"] = system_tessdata
        logger.info(f"Configured TESSDATA_PREFIX to system path: {system_tessdata}")
        return True, "Tesseract OCR engine ready (system tessdata)."
    elif os.path.exists(local_eng):
        os.environ["TESSDATA_PREFIX"] = local_tessdata
        logger.info(f"Configured TESSDATA_PREFIX to project path: {local_tessdata}")
        return True, "Tesseract OCR engine ready (project tessdata)."

    return False, f"Language file 'eng.traineddata' missing in {system_tessdata} and {local_tessdata}."


class TesseractOCRProvider(BaseOCRProvider):
    def __init__(self):
        self.is_available, self.status_message = _configure_tesseract_path()

    def extract_text_from_image(self, image_bytes: bytes) -> str:
        if not self.is_available:
            logger.warning(f"Tesseract unavailable: {self.status_message}")
            return f"[Scanned page detected. {self.status_message}]"

        try:
            image = Image.open(io.BytesIO(image_bytes))
            text = pytesseract.image_to_string(image)
            return text.strip()
        except Exception as e:
            logger.error(f"Tesseract OCR image_to_string failed: {e}")
            return f"[OCR execution error: {str(e)}]"

    def extract_text_with_boxes(self, image_bytes: bytes) -> Dict[str, Any]:
        if not self.is_available:
            logger.warning(f"Tesseract unavailable: {self.status_message}")
            return {
                "text": f"[Scanned page detected. {self.status_message}]",
                "confidence": 0.0,
                "boxes": [],
                "word_count": 0,
                "error": self.status_message
            }

        try:
            image = Image.open(io.BytesIO(image_bytes))
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

            text_words: List[str] = []
            valid_confidences: List[float] = []
            boxes: List[Dict[str, Any]] = []

            for i in range(len(data['text'])):
                word = str(data['text'][i]).strip()
                raw_conf = data['conf'][i]

                if word and raw_conf != -1:
                    conf = float(raw_conf) / 100.0
                    conf = max(0.0, min(1.0, conf))
                    text_words.append(word)
                    valid_confidences.append(conf)

                    boxes.append({
                        "x": int(data['left'][i]),
                        "y": int(data['top'][i]),
                        "width": int(data['width'][i]),
                        "height": int(data['height'][i]),
                        "text": word,
                        "confidence": round(conf, 4)
                    })

            full_text = " ".join(text_words)
            avg_confidence = round(sum(valid_confidences) / len(valid_confidences), 4) if valid_confidences else 0.0

            return {
                "text": full_text,
                "confidence": avg_confidence,
                "boxes": boxes,
                "word_count": len(text_words)
            }
        except Exception as e:
            logger.error(f"Tesseract OCR box/confidence extraction failed: {e}")
            return {
                "text": f"[OCR error: {str(e)}]",
                "confidence": 0.0,
                "boxes": [],
                "word_count": 0,
                "error": str(e)
            }

    def extract_text_with_layout(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Provides detailed OCR result dictionary with full_text, words list with bounding boxes,
        and average confidence for layout analysis and hybrid text extraction.
        """
        res = self.extract_text_with_boxes(image_bytes)
        return {
            "full_text": res.get("text", ""),
            "text": res.get("text", ""),
            "confidence": res.get("confidence", 0.0),
            "words": [
                {
                    "x": b["x"],
                    "y": b["y"],
                    "w": b["width"],
                    "h": b["height"],
                    "text": b["text"],
                    "confidence": b["confidence"]
                }
                for b in res.get("boxes", [])
            ],
            "boxes": res.get("boxes", []),
            "word_count": res.get("word_count", 0)
        }

