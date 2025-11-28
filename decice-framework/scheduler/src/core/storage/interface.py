from abc import ABC, abstractmethod
from typing import BinaryIO, List


class IStorageProvider(ABC):
    @abstractmethod
    def save_file(self, path: str, file_obj: BinaryIO) -> str:
        """Saves a file-like object to the path. Returns the stored path/URI."""
        pass

    @abstractmethod
    def delete_folder(self, path: str) -> bool:
        """Recursively deletes a folder/prefix."""
        pass

    @abstractmethod
    def list_files(self, path: str) -> List[str]:
        """Lists files in a directory/prefix."""
        pass
