import os
import shutil
import logging
from sqlalchemy import text
from app.db.session import engine, SessionLocal
from app.rag.vector_store.chroma import ChromaVectorStoreProvider

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reset_all_test_data():
    logger.info("Resetting all test data and clearing database...")

    # 1. Clear SQL Database tables
    db = SessionLocal()
    try:
        tables = ["human_reviews", "visual_artifacts", "audit_logs", "document_indexes", "extracted_data", "documents", "users"]
        for tbl in tables:
            try:
                db.execute(text(f"DELETE FROM {tbl};"))
                db.commit()
                logger.info(f"Cleared table: {tbl}")
            except Exception as e:
                db.rollback()
                logger.warning(f"Notice clearing table {tbl}: {e}")
    finally:
        db.close()

    # 2. Clear uploaded files directory
    project_backend = os.path.dirname(os.path.abspath(__file__))
    uploaded_dir = os.path.join(project_backend, "uploaded_files")
    if os.path.exists(uploaded_dir):
        for f in os.listdir(uploaded_dir):
            file_p = os.path.join(uploaded_dir, f)
            try:
                if os.path.isfile(file_p) or os.path.islink(file_p):
                    os.unlink(file_p)
                elif os.path.isdir(file_p):
                    shutil.rmtree(file_p)
            except Exception as err:
                logger.warning(f"Could not delete uploaded file {file_p}: {err}")
        logger.info(f"Cleared uploaded_files directory: {uploaded_dir}")

    # 3. Clear ChromaDB vector store collection
    try:
        store = ChromaVectorStoreProvider()
        store.client.delete_collection(name=store.COLLECTION_NAME)
        store.client.get_or_create_collection(name=store.COLLECTION_NAME)
        logger.info("ChromaDB vector store collection reset cleanly.")
    except Exception as chroma_err:
        logger.warning(f"Notice resetting ChromaDB collection: {chroma_err}")

    # 4. Remove extra test database files
    for db_name in ["test_phase2.db", "sql_app.db"]:
        db_path = os.path.join(project_backend, db_name)
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
                logger.info(f"Removed extra test db: {db_name}")
            except Exception as e:
                logger.warning(f"Could not remove {db_name}: {e}")

    logger.info("SUCCESS: All test documents, vector chunks, users, and data cleared cleanly!")

if __name__ == "__main__":
    reset_all_test_data()
