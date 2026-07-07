"""Abaqus-Python postprocessing companion for the rolling deck.

The script itself (``abaqus_fem_postprocessing.py``) runs in the Abaqus interpreter and
must never be imported by the backend (it needs ``odbAccess``). This package only exposes
its TEXT so the deck builders can ship it alongside the .inp files.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

SCRIPT_NAME = "abaqus_fem_postprocessing.py"


@lru_cache(maxsize=1)
def postprocessing_script_text() -> str:
    """The Abaqus-Python postprocessing script as text (for bundling into the deck download)."""
    return (Path(__file__).parent / SCRIPT_NAME).read_text(encoding="utf-8")
