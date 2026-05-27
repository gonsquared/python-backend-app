import uuid
from pathlib import Path
from typing import Protocol

from fastapi import UploadFile

STORAGE_DIR = Path("storage/images")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


class StorageBackend(Protocol):
    async def save(self, filename_hint: str, content: bytes) -> str: ...
    def delete(self, path: str) -> None: ...


class LocalStorageBackend:
    def __init__(self, directory: Path = STORAGE_DIR):
        self.directory = directory
        self.directory.mkdir(parents=True, exist_ok=True)

    async def save(self, filename_hint: str, content: bytes) -> str:
        ext = Path(filename_hint).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            ext = ".bin"
        filename = f"{uuid.uuid4()}{ext}"
        (self.directory / filename).write_bytes(content)
        return filename

    def delete(self, path: str) -> None:
        target = self.directory / path
        if target.exists():
            target.unlink()


def get_storage() -> LocalStorageBackend:
    return LocalStorageBackend()
