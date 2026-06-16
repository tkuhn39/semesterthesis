"""
@module: app.database.null
@context: Database abstraction layer.
@role: No-op backend used when DATABASE_BACKEND=none. The application runs
       without a database (e.g. relying on object storage only).
"""

from app.database.base import DatabaseBackend


class NullDatabaseBackend(DatabaseBackend):
    """A database backend that does nothing; no database is configured."""

    def health_check(self) -> bool:
        return True
