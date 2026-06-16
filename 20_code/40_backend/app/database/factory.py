"""
@module: app.database.factory
@context: Database abstraction layer.
@role: Returns the DatabaseBackend selected by .env (DATABASE_BACKEND). Only
       "none" is implemented so far; the other backends are documented
       extension points (see README.md).
"""

from functools import lru_cache

from app.config import Settings, get_settings
from app.database.base import DatabaseBackend
from app.database.null import NullDatabaseBackend


def build_database(settings: Settings) -> DatabaseBackend:
    """Construct the configured database backend."""
    if settings.database_backend == "none":
        return NullDatabaseBackend()
    raise NotImplementedError(
        f"DATABASE_BACKEND={settings.database_backend!r} is a documented "
        "extension point but not implemented yet. See app/database/README.md."
    )


@lru_cache
def get_database() -> DatabaseBackend:
    """Return the cached, configured database backend."""
    return build_database(get_settings())
