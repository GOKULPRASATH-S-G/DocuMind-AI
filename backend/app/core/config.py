import os
import logging
from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "MultiModal Document Intelligence & RAG"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "development-secret-key-change-in-production"
    
    # JWT Authentication Config
    JWT_SECRET: str = "documind_prod_jwt_secret_9823479823749823749823749823749283749823749823"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440 # 24 Hours

    # Server & Environment Config
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    ALLOWED_ORIGINS: str = "*"

    # Database Configuration
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "doc_rag_db"
    POSTGRES_PORT: int = 5432
    DATABASE_URL: Optional[str] = None

    # External AI & Vector DB Providers Config
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.5-flash-lite"
    GEMINI_VISION_MODEL: str = "gemini-3.5-flash-lite"
    GEMINI_EMBEDDING_MODEL: str = "models/gemini-embedding-001"
    
    ENABLE_VISUAL_ANALYSIS: bool = True
    RAG_CHUNK_SIZE: int = 800
    RAG_CHUNK_OVERLAP: int = 120
    AUTO_APPROVE_THRESHOLD: float = 0.85
    CHROMA_PERSIST_DIR: str = "./chroma_data"
    STORAGE_LOCAL_DIR: str = "./uploaded_files"
    MAX_UPLOAD_SIZE_MB: int = 50

    TESSERACT_CMD: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def get_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    def parse_allowed_origins(self) -> List[str]:
        if not self.ALLOWED_ORIGINS:
            return ["*"]
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    def validate_production_secrets(self):
        if not self.GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY is not configured. Set GEMINI_API_KEY in environment variables.")

settings = Settings()
settings.validate_production_secrets()
