import logging
from typing import List, Optional
from app.rag.embeddings.base import BaseEmbeddingProvider
from app.core.config import settings
from app.core.exceptions import LLMExtractionError

logger = logging.getLogger(__name__)


class GeminiEmbeddingProvider(BaseEmbeddingProvider):
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        self.model_name = model_name if model_name is not None else settings.GEMINI_EMBEDDING_MODEL
        self._genai_client = None
        self._legacy_genai = None

        if self.api_key:
            try:
                from google import genai
                self._genai_client = genai.Client(api_key=self.api_key)
                logger.info(f"Initialized Gemini Embedding Provider (google.genai) with model: {self.model_name}")
            except Exception as e:
                logger.info(f"google.genai client fallback for embeddings: {e}")
                try:
                    import google.generativeai as legacy_genai
                    legacy_genai.configure(api_key=self.api_key)
                    self._legacy_genai = legacy_genai
                    logger.info(f"Initialized legacy GenerativeAI Embeddings with model: {self.model_name}")
                except Exception as legacy_err:
                    logger.error(f"Failed to configure Gemini Embedding SDK: {legacy_err}")

    def embed_text(self, text: str) -> List[float]:
        if not text or not text.strip():
            raise LLMExtractionError("Cannot generate embedding for empty text.")
        res = self.embed_texts([text])
        return res[0]

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        if not texts:
            return []

        if not self.api_key:
            raise LLMExtractionError("GEMINI_API_KEY is not configured in .env for generating embeddings.")

        cleaned_texts = [t.strip() for t in texts if t and t.strip()]
        if not cleaned_texts:
            raise LLMExtractionError("All texts provided for embedding generation are empty.")

        target_model = self.model_name.replace("models/", "")
        logger.info(f"Generating embeddings for {len(cleaned_texts)} chunks using model {target_model}...")

        try:
            embeddings_list: List[List[float]] = []

            if self._genai_client:
                # Use official google.genai Client
                for txt in cleaned_texts:
                    resp = self._genai_client.models.embed_content(
                        model=self.model_name,
                        contents=txt
                    )
                    if hasattr(resp, "embeddings") and resp.embeddings:
                        embeddings_list.append(list(resp.embeddings[0].values))
                    elif hasattr(resp, "embedding") and hasattr(resp.embedding, "values"):
                        embeddings_list.append(list(resp.embedding.values))
                    elif isinstance(resp, dict) and "embedding" in resp:
                        embeddings_list.append(resp["embedding"]["values"])
                    else:
                        raise LLMExtractionError("Invalid embedding output structure from Gemini API.")
                return embeddings_list

            elif self._legacy_genai:
                for txt in cleaned_texts:
                    res = self._legacy_genai.embed_content(
                        model=self.model_name,
                        content=txt
                    )
                    embeddings_list.append(res["embedding"])
                return embeddings_list

            else:
                raise LLMExtractionError(f"Embedding provider '{self.model_name}' is not properly initialized.")

        except Exception as e:
            logger.error(f"Gemini embedding API call failed: {e}")
            raise LLMExtractionError(f"Gemini embedding API call failed: {str(e)}")
