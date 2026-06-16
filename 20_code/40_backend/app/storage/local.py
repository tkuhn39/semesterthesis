"""
@module: app.storage.local
@context: Storage abstraction layer.
@role: Filesystem-backed StorageBackend. Single-node / development use only;
       a local path is not shared across HA nodes (project_rules.md §18).
       The base directory comes from .env (STORAGE_LOCAL_BASE_PATH).
"""

from pathlib import Path

from app.storage.base import StorageBackend, normalize_key


class LocalStorageBackend(StorageBackend):
    """Stores objects as files under a base directory."""

    def __init__(self, base_path: Path) -> None:
        self._base_path = Path(base_path)
        self._base_path.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        return self._base_path / normalize_key(key)

    def save_bytes(self, key: str, data: bytes) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def load_bytes(self, key: str) -> bytes:
        path = self._path(key)
        if not path.is_file():
            raise KeyError(key)
        return path.read_bytes()

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)

    def list_keys(self, prefix: str = "") -> list[str]:
        keys = [
            file.relative_to(self._base_path).as_posix()
            for file in self._base_path.rglob("*")
            if file.is_file()
        ]
        if prefix:
            keys = [key for key in keys if key.startswith(prefix)]
        return sorted(keys)
