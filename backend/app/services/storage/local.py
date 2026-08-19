import os
import uuid
import shutil
from pathlib import Path
from app.services.storage.base import BaseStorageProvider
from app.core.config import settings


class LocalStorageProvider(BaseStorageProvider):
    def __init__(self, base_dir: str = settings.STORAGE_LOCAL_DIR):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_file(self, filename: str, content: bytes) -> str:
        unique_name = f"{uuid.uuid4().hex}_{filename}"
        file_path = self.base_dir / unique_name
        with open(file_path, "wb") as f:
            f.write(content)
        return str(file_path)

    def get_file(self, file_path: str) -> bytes:
        p = Path(file_path)
        if not p.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        with open(p, "rb") as f:
            return f.read()

    def delete_file(self, file_path: str) -> bool:
        p = Path(file_path)
        if p.exists():
            p.unlink()
            return True
        return False
