from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseOCRProvider(ABC):
    @abstractmethod
    def extract_text_from_image(self, image_bytes: bytes) -> str:
        """Extract plain text string from raw image bytes."""
        pass

    @abstractmethod
    def extract_text_with_boxes(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Extract text along with real OCR word confidence scores and bounding boxes.
        Should return a dictionary containing:
        - text: str
        - confidence: float (0.0 to 1.0)
        - boxes: List[Dict[str, Any]] containing x, y, width, height, text, confidence
        """
        pass

    @abstractmethod
    def extract_text_with_layout(self, image_bytes: bytes) -> Dict[str, Any]:
        """
        Extract text with full_text and words list layout for hybrid / scanned document ingestion.
        """
        pass

