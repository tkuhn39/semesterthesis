"""
@module: tests.test_database
@context: Database abstraction tests.
@role: Verifies the default (none) backend is healthy and that a configured but
       unimplemented backend fails loudly instead of silently falling back.
"""

import pytest

from app.config import Settings
from app.database import build_database
from app.database.null import NullDatabaseBackend


def test_default_backend_is_null_and_healthy() -> None:
    """DATABASE_BACKEND=none yields a healthy NullDatabaseBackend."""
    backend = build_database(Settings(database_backend="none"))
    assert isinstance(backend, NullDatabaseBackend)
    assert backend.health_check() is True


def test_unimplemented_backend_raises() -> None:
    """A configured-but-unimplemented backend raises (no silent fallback)."""
    with pytest.raises(NotImplementedError):
        build_database(Settings(database_backend="sqlite"))
