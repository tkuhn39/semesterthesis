"""Contour scans of the Klingelnberg P40 (``.DAT``): the transverse section of a few teeth.

Grammar (79 files of 2023 to 2026 read): a block tag ``[A]`` (``[B]`` to ``[D]`` for repeats) on a line of its own,
then one point per line ``index; x; y; z;`` in millimetres, the index counting from 1 without
gaps. A file may hold a second block (a repeated scan): every block is one ``ContourScan``.
``x`` and ``y`` lie in the transverse section with the gear axis near the origin (the mounting is
eccentric by about 0,1 mm, which the evaluation fits), ``z`` is the axial position of the section
in machine coordinates and must be the same for every point of a block. The scan runs from +x to
-x over about three teeth. Nothing is interpreted here; the fits live in
``gearcore.measurement.contour_scan``.
"""

import math
import re
from pathlib import Path
from typing import Literal

import numpy as np
from numpy.typing import NDArray

from gearcore.errors import ParseError
from gearcore.models.common import FrozenModel

Array = NDArray[np.float64]
MIN_POINTS = 10
_TAG = re.compile(r"^\[([A-Z])\]\s*$")
_ROW = re.compile(r"^\s*(\d+)\s*;\s*([-+.\d]+)\s*;\s*([-+.\d]+)\s*;\s*([-+.\d]+)\s*;?\s*$")
_NUMBER = re.compile(r"^[-+]?(\d+\.?\d*|\.\d+)$")


class ContourScan(FrozenModel):
    """One block of a contour file."""

    name: str
    """File stem, with the block letter appended when the file holds several blocks."""
    block: Literal["A", "B", "C", "D"]
    z_mm: float
    points_mm: tuple[tuple[float, float], ...]

    def as_array(self) -> Array:
        return np.asarray(self.points_mm, dtype=np.float64)


def _number(token: str, where: str) -> float:
    if not _NUMBER.match(token):
        raise ParseError(f"{where}: non-numeric token {token!r}")
    value = float(token)
    if not math.isfinite(value):
        raise ParseError(f"{where}: {token!r} exceeds the number range")
    return value


def parse_contour_scans(
    text: str, *, name: str, path: str | None = None
) -> tuple[ContourScan, ...]:
    """Every block of a contour file as a scan; ``name`` is the file stem."""
    where = path or name
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    blocks: list[tuple[str, list[tuple[float, float]], set[float]]] = []
    expected_index = 1
    for number, raw in enumerate(lines, start=1):
        stripped = raw.strip()
        if not stripped:
            continue
        if (tag := _TAG.match(stripped)) is not None:
            if tag.group(1) not in ("A", "B", "C", "D"):
                raise ParseError(f"{where}: line {number}: unknown block tag {stripped!r}")
            blocks.append((tag.group(1), [], set()))
            expected_index = 1
            continue
        row = _ROW.match(stripped)
        if row is None:
            raise ParseError(f"{where}: line {number}: not a point line: {stripped!r}")
        if not blocks:
            raise ParseError(f"{where}: line {number}: a point before the first block tag")
        index = int(row.group(1))
        if index != expected_index:
            raise ParseError(f"{where}: line {number}: index {index}, expected {expected_index}")
        expected_index += 1
        x = _number(row.group(2), f"{where}: line {number}")
        y = _number(row.group(3), f"{where}: line {number}")
        z = _number(row.group(4), f"{where}: line {number}")
        blocks[-1][1].append((x, y))
        blocks[-1][2].add(z)
    if not blocks:
        raise ParseError(f"{where}: no block tag '[A]'")
    scans: list[ContourScan] = []
    for letter, points, heights in blocks:
        if len(points) < MIN_POINTS:
            raise ParseError(f"{where}: block [{letter}] has only {len(points)} points")
        if len(heights) != 1:
            raise ParseError(
                f"{where}: block [{letter}] is not a plane section, z = {sorted(heights)}"
            )
        scan_name = name if len(blocks) == 1 else f"{name}[{letter}]"
        scans.append(
            ContourScan(
                name=scan_name,
                block=letter,
                z_mm=heights.pop(),
                points_mm=tuple(points),
            )
        )
    return tuple(scans)


def load_contour_scans(path: Path) -> tuple[ContourScan, ...]:
    file = Path(path)
    try:
        text = file.read_bytes().decode("ascii")
    except UnicodeDecodeError as error:
        raise ParseError(f"{file}: not ASCII at byte {error.start}") from None
    return parse_contour_scans(text, name=file.stem, path=str(file))


__all__ = ["MIN_POINTS", "ContourScan", "load_contour_scans", "parse_contour_scans"]
