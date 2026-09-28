"""Packaged reference data: source registry, worked examples, STplus oracle fixtures.

The data ships inside the wheel so tests and notebooks read the same files
(``importlib.resources``); nothing here is read from the repository layout at run time.
"""

from importlib.resources import files
from pathlib import Path


def data_path(*parts: str) -> Path:
    """Absolute path of a file below ``gearcore/data`` (must exist as a regular file or dir)."""
    root = files("gearcore.data")
    target = root.joinpath(*parts)
    return Path(str(target))


def stplus_case_dirs() -> list[Path]:
    """All STplus fixture case directories (those containing a ``meta.json``), sorted by name."""
    base = data_path("stplus")
    if not base.is_dir():
        return []
    return sorted(p for p in base.iterdir() if p.is_dir() and (p / "meta.json").is_file())
