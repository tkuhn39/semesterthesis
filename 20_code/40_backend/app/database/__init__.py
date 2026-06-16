"""
@module: app.database
@context: Database abstraction layer (extension point).
@role: Public entry point. Use get_database() to obtain the configured backend
       and the DatabaseBackend type for annotations.
"""

from app.database.base import DatabaseBackend
from app.database.factory import build_database, get_database

__all__ = ["DatabaseBackend", "build_database", "get_database"]
