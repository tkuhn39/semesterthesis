"""Thermal-camera screenshots of the running-in matrix (kst-E_63, wheel 97351) cut for the thesis
(user, 2026-10-18): only the image and the temperature legend on its right remain, set side by
side on white; one example goes into 4.5, every image into appendix H.

The six screenshots under ``70_input/72_Kleingetriebepruefstand_KV3/Bilder/
Waermebildaufnahme_Kunststoffraeder`` (``<torque>_<speed>.png``, torque at the wheel in Nm,
speed at the wheel in 1/min) are 2940 × 1912 pixel captures of the camera software with the same
layout; the boxes below are pixel coordinates of that layout and are checked against the image
size. Output: ``80_output/thesis/waermebild/waermebild_<torque>nm_<speed>.png`` (raster, the
only non-vector figures of the thesis, because the source is a raster image).

    uv run --all-extras python scripts/thesis_thermal_images.py
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Sequence
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gearcore.errors import InputRangeError  # noqa: E402

REPO = Path(__file__).resolve().parents[3]
INPUT = REPO / "70_input" / "72_Kleingetriebepruefstand_KV3" / "Bilder" / "Waermebildaufnahme_Kunststoffraeder"
OUTPUT = REPO / "80_output" / "thesis" / "waermebild"
EXPECTED_SIZE = (2940, 1912)
IMAGE_BOX = (722, 390, 2161, 1470)
"""(left, upper, right, lower) of the thermal image in the capture."""
LEGEND_BOX = (2749, 397, 2940, 1463)
"""The colour bar with its labels and the two boxes of the range."""
GAP = 40
NAME = re.compile(r"^(\d+)_(\d+)\.png$")


def cut(source: Path, target: Path) -> Path:
    with Image.open(source) as capture:
        if capture.size != EXPECTED_SIZE:
            raise InputRangeError(f"{source.name}: size {capture.size}, expected {EXPECTED_SIZE}")
        image = capture.crop(IMAGE_BOX)
        legend = capture.crop(LEGEND_BOX)
    width = image.width + GAP + legend.width
    height = max(image.height, legend.height)
    sheet = Image.new("RGB", (width, height), "white")
    sheet.paste(image, (0, 0))
    sheet.paste(legend, (image.width + GAP, LEGEND_BOX[1] - IMAGE_BOX[1]))
    target.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(target, format="PNG", optimize=True)
    return target


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--input", type=Path, default=INPUT)
    parser.add_argument("--out", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    sources = sorted(args.input.glob("*.png"))
    if not sources:
        raise InputRangeError(f"no PNG under {args.input}")
    for source in sources:
        match = NAME.match(source.name)
        if match is None:
            print(f"{source.name}: name not <torque>_<speed>.png, skipped")
            continue
        torque, speed = match.groups()
        target = cut(source, args.out / f"waermebild_{torque}nm_{speed}.png")
        print(f"{source.name} -> {target.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
