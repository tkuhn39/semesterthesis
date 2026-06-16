"""
@module: tests.test_storage_local
@context: Storage abstraction tests.
@role: Round-trips the LocalStorageBackend and checks key-safety validation.
"""

from pathlib import Path

import pytest

from app.storage.base import normalize_key
from app.storage.local import LocalStorageBackend


def test_local_backend_round_trip(tmp_path: Path) -> None:
    """save -> exists -> load -> list -> delete behaves consistently."""
    storage = LocalStorageBackend(tmp_path)
    key = "results/run1/stress.csv"
    payload = b"x,y\n1,2\n"

    assert storage.exists(key) is False
    storage.save_bytes(key, payload)
    assert storage.exists(key) is True
    assert storage.load_bytes(key) == payload
    assert storage.list_keys(prefix="results/") == [key]

    storage.delete(key)
    assert storage.exists(key) is False


def test_local_backend_missing_key_raises(tmp_path: Path) -> None:
    """Loading an absent key raises KeyError."""
    storage = LocalStorageBackend(tmp_path)
    with pytest.raises(KeyError):
        storage.load_bytes("does/not/exist.bin")


def test_normalize_key_rejects_traversal() -> None:
    """Keys escaping the root are rejected."""
    for bad in ["../secret", "results/../../etc/passwd", "/abs", "", "."]:
        with pytest.raises(ValueError):
            normalize_key(bad)
