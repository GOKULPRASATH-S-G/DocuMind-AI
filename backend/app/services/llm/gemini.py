import os
import json
import logging
from typing import Dict, Any, List, Optional
from app.services.llm.base import BaseLLMProvider
from app.core.config import settings
from app.core.exceptions import LLMExtractionError


logger = logging.getLogger(__name__)


class GeminiLLMProvider(BaseLLMProvider):
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        self.model_name = model_name if model_name is not None else settings.GEMINI_MODEL
        self._genai_client = None
        self._legacy_model = None

        if self.api_key:
            try:
                # Primary SDK: google.genai
                from google import genai
                self._genai_client = genai.Client(api_key=self.api_key)
                logger.info(f"Initialized google.genai Client with model: {self.model_name}")
            except Exception as e:
                logger.info(f"google.genai client initialization fallback: {e}")
                try:
                    import google.generativeai as legacy_genai
                    legacy_genai.configure(api_key=self.api_key)
                    self._legacy_model = legacy_genai.GenerativeModel(self.model_name)
                    logger.info(f"Initialized legacy GenerativeModel with model: {self.model_name}")
                except Exception as legacy_err:
                    logger.error(f"Failed to configure Gemini SDK: {legacy_err}")

    def extract_structured_json(self, prompt: str, content: str, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes structured extraction via Gemini API using official SDK.
        """
        if not self.api_key:
            logger.error("Structured extraction attempted without GEMINI_API_KEY configured.")
            raise LLMExtractionError(
                "GEMINI_API_KEY is not configured in .env. Please set a valid Gemini API key to run structured extraction."
            )

        if not self._genai_client and not self._legacy_model:
            raise LLMExtractionError(f"Gemini LLM model '{self.model_name}' is not properly initialized.")

        if not content or not content.strip():
            logger.error("Structured extraction attempted with empty document content.")
            raise LLMExtractionError("Document content is empty. Cannot perform structured extraction.")

        full_prompt = f"{prompt}\n\nDOCUMENT CONTENT TO EXTRACT:\n{content}"
        logger.info(f"Sending extraction prompt to Gemini API (model={self.model_name}, content_length={len(content)})...")

        candidate_models = [self.model_name, "gemini-3.5-flash-lite", "gemini-3.6-flash", "gemini-3.1-flash-lite", "gemini-2.5-flash"]
        # Remove duplicates while preserving order
        candidate_models = list(dict.fromkeys([m for m in candidate_models if m]))

        last_error = None
        for m_name in candidate_models:
            try:
                raw_text = ""
                if self._genai_client:
                    config = {"response_mime_type": "application/json"}
                    response = self._genai_client.models.generate_content(
                        model=m_name,
                        contents=full_prompt,
                        config=config
                    )
                    raw_text = response.text.strip() if response and response.text else ""
                elif self._legacy_model:
                    generation_config = {"response_mime_type": "application/json"}
                    response = self._legacy_model.generate_content(
                        full_prompt,
                        generation_config=generation_config
                    )
                    raw_text = response.text.strip() if response and response.text else ""

                if not raw_text:
                    continue

                clean_text = raw_text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

                try:
                    parsed_json = json.loads(clean_text)
                    if not isinstance(parsed_json, dict):
                        raise LLMExtractionError(f"Expected JSON dictionary from Gemini, received {type(parsed_json).__name__}")
                    return parsed_json
                except json.JSONDecodeError as json_err:
                    logger.error(f"Failed to parse Gemini JSON output: {json_err}. Raw text: {raw_text[:500]}")
                    raise LLMExtractionError(f"Gemini output is not valid JSON: {str(json_err)}")

            except Exception as e:
                last_error = e
                logger.warning(f"Gemini model {m_name} failed: {e}. Trying fallback models if available...")

        raise LLMExtractionError(f"Gemini API call failed across models: {str(last_error)}")


    def extract_structured_data(self, document_content: str, target_schema_prompt: str) -> Dict[str, Any]:
        return self.extract_structured_json(target_schema_prompt, document_content, {})

    def generate_rag_answer(self, question: str, context_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not self.api_key:
            raise LLMExtractionError("GEMINI_API_KEY is not configured for RAG answer generation.")

        formatted_context = ""
        for i, chunk in enumerate(context_chunks):
            doc_name = chunk.get("document_name", "Unknown Document")
            page_num = chunk.get("page_number", 1)
            text = chunk.get("chunk_text", "")
            formatted_context += f"\n[Source {i+1}: {doc_name} (Page {page_num})]\n{text}\n"

        prompt = f"""
        Answer the following question strictly using the provided document context.
        Question: {question}

        Context:
        {formatted_context}
        """

        try:
            raw_answer = ""
            if self._genai_client:
                resp = self._genai_client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                raw_answer = resp.text.strip() if resp and resp.text else ""
            elif self._legacy_model:
                resp = self._legacy_model.generate_content(prompt)
                raw_answer = resp.text.strip() if resp and resp.text else ""

            citations = [
                {
                    "document_id": c.get("document_id", "doc_id"),
                    "document_name": c.get("document_name", "Document"),
                    "page_number": c.get("page_number", 1),
                    "chunk_snippet": c.get("chunk_text", "")[:150],
                    "similarity_score": c.get("similarity_score", 0.85)
                } for c in context_chunks
            ]
            return {
                "answer": raw_answer or "No response generated.",
                "citations": citations
            }
        except Exception as e:
            logger.error(f"Gemini RAG synthesis failed: {e}")
            raise LLMExtractionError(f"RAG response generation failed: {str(e)}")

    def analyze_image(self, image_input: Any, prompt: str, mime_type: str = "image/png") -> Dict[str, Any]:
        """
        Analyzes an image input (file path, bytes, or PIL Image) using Gemini Vision model.
        Returns structured JSON dict.
        """
        if not self.api_key:
            logger.warning("analyze_image called without GEMINI_API_KEY configured. Returning default description.")
            return {
                "visual_type": "UNKNOWN_VISUAL",
                "description": "Visual document artifact extracted from page.",
                "key_values": []
            }

        vision_model = getattr(settings, "GEMINI_VISION_MODEL", self.model_name)

        try:
            image_bytes = None
            if isinstance(image_input, (str, os.PathLike)) and os.path.exists(image_input):
                with open(image_input, "rb") as f:
                    image_bytes = f.read()
            elif isinstance(image_input, bytes):
                image_bytes = image_input

            raw_text = ""
            if self._genai_client and image_bytes:
                from google.genai import types
                part = types.Part.from_bytes(data=image_bytes, mime_type=mime_type)
                config = {"response_mime_type": "application/json"}
                response = self._genai_client.models.generate_content(
                    model=vision_model,
                    contents=[part, prompt],
                    config=config
                )
                raw_text = response.text.strip() if response and response.text else ""
            elif self._legacy_model and image_bytes:
                from PIL import Image
                import io
                pil_img = Image.open(io.BytesIO(image_bytes))
                generation_config = {"response_mime_type": "application/json"}
                response = self._legacy_model.generate_content(
                    [prompt, pil_img],
                    generation_config=generation_config
                )
                raw_text = response.text.strip() if response and response.text else ""

            if not raw_text:
                return {
                    "visual_type": "UNKNOWN_VISUAL",
                    "description": "Visual document artifact extracted from document page.",
                    "key_values": []
                }

            clean_text = raw_text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            parsed_json = json.loads(clean_text)
            if isinstance(parsed_json, dict):
                return parsed_json
        except Exception as err:
            logger.warning(f"Gemini Vision image analysis failed or API unavailable: {err}")

        return {
            "visual_type": "UNKNOWN_VISUAL",
            "description": "Visual document artifact extracted from document page.",
            "key_values": []
        }

