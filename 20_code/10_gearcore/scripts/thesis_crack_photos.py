"""The crack-growth photos of the running test with the wheel 97364 (8 Nm): the user's nine
rig photos of the marked teeth, one per stop (file name = load cycles), cut to one window of the
same pixel size around the marked teeth so that the thesis shows the same teeth at the same
scale at every stop (user, 2026-10-25: zoom uniformly on the teeth and the cracks).

    uv run --all-extras python scripts/thesis_crack_photos.py [--input DIR] [--out DIR]
        [--width PX] [--height PX] [--check]

The wheel is found in every photo by its colour (the yellow plastic against the steel of the
rig); the window spans the full wheel width and ``--height`` pixels, centred on the green marks
of the marked teeth where they are visible, else on the offset ``MARK_OFFSET`` the user or the
author set by looking at the photo (fraction of the wheel height from its top). The crops go to
``80_output/thesis/risswachstum_97364/risswachstum_97364_<cycles>.png`` and are listed in
``10_report/bilder/bilder.yaml`` by hand. ``--check`` prints the windows and writes nothing.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gearcore.errors import InputRangeError  # noqa: E402

REPO = Path(__file__).resolve().parents[3]
INPUT = REPO / "70_input" / "72_Kleingetriebepruefstand_KV3" / "Risswachstum_8-Nm_97364"
OUTPUT = REPO / "80_output" / "thesis" / "risswachstum_97364"
ME = "97364"
MARK_OFFSET: dict[int, float] = {}
"""Load cycles -> centre of the window as a fraction of the wheel height, for photos without a
visible green mark (filled from the detected marks of the neighbouring stops when empty)."""
WINDOW_TOP: dict[int, int] = {40000000: 260}
"""Load cycles -> top row of the window in pixels, set by hand where the colour mask takes the
steel pinion above the wheel for wheel (the photo of the last stop; the user wants only plastic in
every window, 2026-10-25)."""


@dataclass(frozen=True)
class Window:
    cycles: int
    source: Path
    wheel_box: tuple[int, int, int, int]
    """left, top, right, bottom of the wheel in the photo (pixels)."""
    mark_centre: float | None
    """Row of the green marks (pixels), None when no mark was found."""
    box: tuple[int, int, int, int]
    """The crop window (left, top, right, bottom)."""


def _masks(image: Image.Image) -> tuple[np.ndarray, np.ndarray]:
    a = np.asarray(image.convert("RGB")).astype(int)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    yellow = (r > 120) & (g > 100) & (b < 140) & (r - b > 40)
    green = (g > r + 15) & (g > b + 15) & (g > 70)
    return yellow, green


def wheel_box(yellow: np.ndarray, share: float = 0.3) -> tuple[int, int, int, int]:
    """Bounding box of the rows and columns where at least ``share`` of the pixels are wheel."""
    rows = np.where(yellow.mean(axis=1) > share)[0]
    cols = np.where(yellow.mean(axis=0) > share)[0]
    if rows.size == 0 or cols.size == 0:
        raise InputRangeError("no wheel found in the photo (yellow mask empty)")
    return int(cols.min()), int(rows.min()), int(cols.max()) + 1, int(rows.max()) + 1


def mark_row(green: np.ndarray, box: tuple[int, int, int, int], minimum: int = 25) -> float | None:
    """Mean row of the green marks inside the wheel box, None below ``minimum`` pixels."""
    left, top, right, bottom = box
    inside = green[top:bottom, left:right]
    rows = np.where(inside.any(axis=1))[0]
    if rows.size < 3 or int(inside.sum()) < minimum:
        return None
    weights = inside.sum(axis=1).astype(float)
    return float(top + np.average(np.arange(inside.shape[0]), weights=weights))


def windows(
    folder: Path, width: int | None, height: int, offsets: dict[int, float]
) -> list[Window]:
    """One window per photo ``<ME>_<cycles>.JPEG`` of the folder, sorted by cycles."""
    photos = sorted(folder.glob(f"{ME}_*.JPEG"), key=lambda p: int(p.stem.split("_")[1]))
    if not photos:
        raise InputRangeError(f"no photos {ME}_<cycles>.JPEG in {folder}")
    found: list[tuple[int, Path, tuple[int, int, int, int], float | None]] = []
    for photo in photos:
        cycles = int(photo.stem.split("_")[1])
        yellow, green = _masks(Image.open(photo))
        box = wheel_box(yellow)
        found.append((cycles, photo, box, mark_row(green, box)))
    # the window height is the same everywhere; the width is the smallest wheel width unless given
    common_width = width or min(right - left for _, _, (left, _, right, _), _ in found)
    fractions = [
        (centre - top) / (bottom - top)
        for _, _, (_, top, _, bottom), centre in found
        if centre is not None
    ]
    default_fraction = float(np.median(fractions)) if fractions else 0.35
    out: list[Window] = []
    for cycles, photo, (left, top, right, bottom), centre in found:
        fraction = offsets.get(cycles)
        if centre is None or fraction is not None:
            centre = top + (fraction if fraction is not None else default_fraction) * (bottom - top)
        x0 = left + (right - left - common_width) // 2
        y0 = int(round(centre - height / 2))
        y0 = max(top, min(y0, bottom - height))
        if cycles in WINDOW_TOP:
            y0 = WINDOW_TOP[cycles]
        if bottom - top < height:
            raise InputRangeError(f"{photo.name}: the wheel is only {bottom - top} px high")
        out.append(
            Window(
                cycles,
                photo,
                (left, top, right, bottom),
                centre,
                (x0, y0, x0 + common_width, y0 + height),
            )
        )
    return out


def write_crops(items: list[Window], out: Path) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for item in items:
        crop = Image.open(item.source).convert("RGB").crop(item.box)
        target = out / f"risswachstum_{ME}_{item.cycles}.png"
        crop.save(target, optimize=True)
        written.append(target)
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--input", type=Path, default=INPUT)
    parser.add_argument("--out", type=Path, default=OUTPUT)
    parser.add_argument(
        "--width", type=int, default=None, help="window width in px (default: wheel)"
    )
    parser.add_argument("--height", type=int, default=560, help="window height in px")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    items = windows(args.input, args.width, args.height, MARK_OFFSET)
    for item in items:
        mark = "–" if item.mark_centre is None else f"{item.mark_centre:.0f}"
        print(f"{item.cycles:>9}: wheel {item.wheel_box}, mark row {mark}, window {item.box}")
    if args.check:
        return 0
    for path in write_crops(items, args.out):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
