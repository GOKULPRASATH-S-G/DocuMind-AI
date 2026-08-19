from abc import ABC, abstractmethod


class BaseStorageProvider(ABC):
    @abstractmethod
    def save_file(self, filename: str, content: bytes) -> str:
        """Save file bytes to storage medium and return access path/URI."""
        pass

    @abstractmethod
    def get_file(self, file_path: str) -> bytes:
        """Retrieve file bytes from storage medium by path/URI."""
        pass

    @abstractmethod
    def delete_file(self, file_path: str) -> bool:
        """Delete file from storage medium."""
        pass
