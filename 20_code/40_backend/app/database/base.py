"""
@module: app.database.base
@context: Database abstraction layer (extension point).
@role: Backend-agnostic interface for database access. Application code depends
       only on this ABC; concrete backends (SQLite/Postgres/D1) are chosen at
       runtime by app.database.factory from .env. Kept minimal on purpose — no
       ORM is committed to until a data model exists (project_rules.md §20).
"""

from abc import ABC, abstractmethod


class DatabaseBackend(ABC):
    """Interface every database backend implements."""

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the database is reachable and usable."""
