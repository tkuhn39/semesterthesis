"""STplus transverse contour export ``zahnkonXwzY.txt`` (manual §6.4.2).

The manual does not document the column layout ("unkommentierte Listendateien"). Grammar confirmed
on the first oracle run (STplus 11.1F, 2026-09-28, FZG-C): one point per line, ``x ; y`` in mm
(Fortran scientific notation, e.g. ``-5.549498E+00 ;  2.993630E+01``), transverse section, one tooth
centred on the +y axis running from the root circle on the left flank over the tip to the root
circle on the right flank (fzg_c: r_min = d_f/2 = 30.446, r_max = d_a/2 = 41.225). ``X`` = number
of tools, ``Y`` = gear. Any other layout raises ``ParseError`` so the assumption cannot silently
degrade into a wrong contour.
"""

import re
from pathlib import Path

import numpy as np
from numpy.typing import NDArray

from gearcore.errors import ParseError

_SEPARATORS = re.compile(r"[;,]\s*|\s+")


def parse_contour(text: str, *, path: str | None = None) -> NDArray[np.float64]:
    """Return an ``(N, 2)`` array of x/y in mm. Non-numeric lines are a grammar error."""
    rows: list[tuple[float, float]] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        tokens = [t for t in _SEPARATORS.split(line) if t]
        if len(tokens) != 2:
            raise ParseError(
                f"{path or 'contour'} line {number}: expected exactly two numeric columns, got {line!r}"
            )
        try:
            x, y = float(tokens[0].replace("D", "E")), float(tokens[1].replace("D", "E"))
        except ValueError as exc:
            raise ParseError(
                f"{path or 'contour'} line {number}: non-numeric token in {line!r}"
            ) from exc
        rows.append((x, y))
    if len(rows) < 3:
        raise ParseError(f"{path or 'contour'}: fewer than three points")
    return np.asarray(rows, dtype=np.float64)


def load_contour(path: Path) -> NDArray[np.float64]:
    return parse_contour(path.read_text(encoding="latin-1"), path=str(path))
