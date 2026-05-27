import asyncio
import uuid
from pathlib import Path
from typing import Protocol


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
            raise ValueError(
                f"Unsupported file extension '{ext}'. "
                f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
            )
        filename = f"{uuid.uuid4()}{ext}"
        dest = self.directory / filename
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, dest.write_bytes, content)
        return filename

    def delete(self, path: str) -> None:
        target = (self.directory / path).resolve()
        if not str(target).startswith(str(self.directory.resolve())):
            raise ValueError(f"Refusing to delete path outside storage directory: {path}")
        if target.exists():
            target.unlink()


_storage = LocalStorageBackend()


def get_storage() -> LocalStorageBackend:
    return _storage
