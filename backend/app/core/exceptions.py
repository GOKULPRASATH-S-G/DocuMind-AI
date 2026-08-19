class DocumentIntelligenceException(Exception):
    """Base exception for MultiModal Document Intelligence system."""
    pass

class DocumentProcessingError(DocumentIntelligenceException):
    """Raised when document processing fails."""
    pass

class OCRError(DocumentIntelligenceException):
    """Raised when OCR extraction fails."""
    pass

class LLMExtractionError(DocumentIntelligenceException):
    """Raised when LLM structured extraction fails."""
    pass

class ValidationError(DocumentIntelligenceException):
    """Raised when validation rules fail."""
    pass

class VectorStoreError(DocumentIntelligenceException):
    """Raised when vector database operations fail."""
    pass
