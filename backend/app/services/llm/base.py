from abc import ABC, abstractmethod
from typing import Dict, Any, List


class BaseLLMProvider(ABC):
    @abstractmethod
    def extract_structured_json(self, prompt: str, content: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sends formatted document content and prompt to the LLM and returns raw extracted dictionary.
        Raises LLMExtractionError on failure, missing API keys, or malformed JSON responses.
        """
        pass

    @abstractmethod
    def generate_rag_answer(self, question: str, context_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate answer with citations based on retrieved context chunks."""
        pass

    @abstractmethod
    def analyze_image(self, image_input: Any, prompt: str, mime_type: str = "image/png") -> Dict[str, Any]:
        """Analyzes image input using Gemini Vision multimodal capability and returns structured JSON analysis."""
        pass

