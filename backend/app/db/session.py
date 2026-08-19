import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.core.config import settings

logger = logging.getLogger(__name__)

def create_resilient_engine():
    db_url = settings.get_database_url()
    if "postgresql" in db_url:
        try:
            eng = create_engine(db_url, pool_pre_ping=True, pool_size=10, max_overflow=20)
            with eng.connect() as conn:
                pass
            logger.info("Connected to PostgreSQL successfully.")
            return eng
        except Exception as e:
            logger.warning(f"PostgreSQL connection failed ({e}). Falling back to local SQLite database.")
            return create_engine("sqlite:///./doc_rag.db", connect_args={"check_same_thread": False})
    else:
        return create_engine(db_url, connect_args={"check_same_thread": False})

engine = create_resilient_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
