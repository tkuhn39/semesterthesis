"""
@module: app.storage.base
@context: Storage abstraction layer.
@role: Backend-agnostic interface for object/file persistence. Application code
       depends only on this ABC; concrete backends (local, S3-compatible) are
       chosen at runtime by app.storage.factory from .env. Keys are POSIX-style
       relative paths (e.g. "results/run1/stress.csv") so they are identical
       across backends and HA nodes.
"""

from abc import ABC, abstractmethod


class StorageBackend(ABC):
    """Interface every storage backend implements."""

    @abstractmethod
    def save_bytes(self, key: str, data: bytes) -> None:
        """Store ``data`` under ``key``, overwriting any existing object."""

    @abstractmethod
    def load_bytes(self, key: str) -> bytes:
        """Return the bytes stored under ``key``. Raises ``KeyError`` if absent."""

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Return whether an object exists under ``key``."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """Remove ``key``. No-op if it does not exist."""

    @abstractmethod
    def list_keys(self, prefix: str = "") -> list[str]:
        """Return all keys, optionally filtered by ``prefix``."""


def normalize_key(key: str) -> str:
    """Validate and normalize a storage key to a safe POSIX-style relative path.

    Rejects absolute paths and parent-directory traversal so that no backend can
    be tricked into writing outside its root.
    """
    stripped = key.strip()
    if stripped.startswith("/"):
        raise ValueError(f"Invalid storage key (absolute path): {key!r}")
    parts = [segment for segment in stripped.split("/") if segment not in ("", ".")]
    if not parts or any(segment == ".." for segment in parts):
        raise ValueError(f"Invalid storage key: {key!r}")
    return "/".join(parts)
