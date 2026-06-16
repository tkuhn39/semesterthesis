"""
@module: app.storage
@context: Storage abstraction layer.
@role: Public entry point. Use get_storage() to obtain the configured backend
       and the StorageBackend type for annotations.
"""

from app.storage.base import StorageBackend
from app.storage.factory import build_storage, get_storage

__all__ = ["StorageBackend", "build_storage", "get_storage"]
