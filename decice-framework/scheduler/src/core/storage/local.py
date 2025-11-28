import os
import shutil
from pathlib import Path
from typing import BinaryIO, List

from .interface import IStorageProvider


class LocalStorageProvider(IStorageProvider):
    def __init__(self, root_dir: Path):
        self.root_dir = root_dir
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def save_file(self, relative_path: str, file_obj: BinaryIO) -> str:
        # relative_path e.g. "dataset_A/file1.json"
        full_path = self.root_dir / relative_path
        full_path.parent.mkdir(parents=True, exist_ok=True)

        with open(full_path, "wb+") as buffer:
            shutil.copyfileobj(file_obj, buffer)

        return str(full_path)

    def delete_folder(self, relative_path: str) -> bool:
        full_path = self.root_dir / relative_path
        if full_path.exists():
            shutil.rmtree(full_path)
            return True
        return False

    def list_files(self, relative_path: str) -> List[str]:
        full_path = self.root_dir / relative_path
        if not full_path.exists():
            return []
        return [str(p) for p in full_path.glob("*.json")]
