"""
@module: app.storage.factory
@context: Storage abstraction layer.
@role: Returns the StorageBackend selected by .env (STORAGE_BACKEND). This is
       the only place backends are instantiated; application code calls
       get_storage() and depends solely on the StorageBackend interface.
"""

from functools import lru_cache

from app.config import Settings, get_settings
from app.storage.base import StorageBackend
from app.storage.local import LocalStorageBackend


def build_storage(settings: Settings) -> StorageBackend:
    """Construct the configured storage backend."""
    if settings.storage_backend == "local":
        return LocalStorageBackend(settings.storage_local_base_path)
    if settings.storage_backend == "s3":
        # Imported lazily so boto3 is only required when S3 is actually used.
        from app.storage.s3 import S3StorageBackend

        return S3StorageBackend(settings)
    raise ValueError(f"Unknown STORAGE_BACKEND: {settings.storage_backend!r}")


@lru_cache
def get_storage() -> StorageBackend:
    """Return the cached, configured storage backend."""
    return build_storage(get_settings())
