"""The figures of the thesis: copy the files listed in ``10_report/bilder/bilder.yaml`` from
``80_output`` into ``10_report/bilder/<kapitel>/``. Every figure goes in as a vector PDF
(user's wish of 2026-10-17: no loss of resolution anywhere). An SVG source is taken as the
``.pdf`` twin that ``plot_style.save`` writes beside it from the same figure (same renderer,
fonts embedded); only an SVG without a twin, or whose twin is older than the SVG (a hand-edited
drawing), is converted by Inkscape, which substitutes the symbol face and the mathtext glyphs
and is therefore the second choice. ``format: png`` takes the 300 dpi twin instead. Files below
``bilder/kap*`` that the listing no longer names are removed, so that graphicx never picks a
stale twin.

    uv run --all-extras python scripts/build_thesis_figures.py [--check]

``bilder.yaml``::

    bilder:
      - name: netz_sektor          # file name in the thesis (without extension)
        kapitel: 3                 # target folder bilder/kap3
        quelle: fe/kst_e/bilder_V2/frozen_mesh_sector.svg   # below 80_output
        format: pdf                # pdf (default for svg: the twin, else Inkscape) or png
        unterschrift: ...          # the caption, for the writer of the chapter (not used here)

A missing source is refused by name; ``--check`` only lists what would be written.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gearcore.errors import InputRangeError  # noqa: E402

REPO = Path(__file__).resolve().parents[3]
OUTPUT = REPO / "80_output"
REPORT = REPO / "10_report"
LISTING = REPORT / "bilder" / "bilder.yaml"


@dataclass(frozen=True)
class Figure:
    name: str
    chapter: int
    source: Path
    fmt: str
    caption: str
    action: str = "copy"
    """``copy`` (a png, or the pdf twin of an svg), ``inkscape`` (an svg without a current twin)."""

    @property
    def target(self) -> Path:
        return REPORT / "bilder" / f"kap{self.chapter}" / f"{self.name}.{self.fmt}"


def read_listing(path: Path) -> tuple[Figure, ...]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) if path.is_file() else None
    if not isinstance(loaded, dict) or not isinstance(loaded.get("bilder"), list):
        raise InputRangeError(f"{path}: expected a mapping with a list 'bilder'")
    figures: list[Figure] = []
    names: set[str] = set()
    for i, entry in enumerate(loaded["bilder"]):
        if not isinstance(entry, dict):
            raise InputRangeError(f"{path}: entry {i} is not a mapping")
        figure = _figure(entry, f"{path}: entry {i}")
        if figure.name in names:
            raise InputRangeError(f"{path}: the name {figure.name!r} repeats")
        names.add(figure.name)
        figures.append(figure)
    return tuple(figures)


def _figure(entry: dict[str, Any], where: str) -> Figure:
    for key in ("name", "kapitel", "quelle"):
        if key not in entry:
            raise InputRangeError(f"{where}: '{key}' missing")
    source = OUTPUT / str(entry["quelle"])
    if not source.is_file():
        raise InputRangeError(f"{where}: source {source} does not exist")
    suffix = source.suffix.lower().lstrip(".")
    fmt = str(entry.get("format") or ("pdf" if suffix == "svg" else suffix))
    action = "copy"
    if suffix == "svg" and fmt not in ("pdf", "svg", "png"):
        raise InputRangeError(f"{where}: an svg source gives pdf, svg or png, not {fmt!r}")
    if suffix == "svg" and fmt == "png":
        # the 300 dpi twin that plot_style.save writes beside every svg (raster, only on request)
        source = source.with_suffix(".png")
        if not source.is_file():
            raise InputRangeError(f"{where}: no png twin {source} beside the svg")
        suffix = "png"
    elif suffix == "svg" and fmt == "pdf":
        # the vector twin of the same figure; an older twin belongs to an earlier drawing
        twin = source.with_suffix(".pdf")
        if twin.is_file() and twin.stat().st_mtime >= source.stat().st_mtime - 1.0:
            source = twin
            suffix = "pdf"
        else:
            action = "inkscape"
    if suffix != "svg" and fmt != suffix:
        raise InputRangeError(f"{where}: a {suffix} source is copied as {suffix}, not {fmt!r}")
    chapter = entry["kapitel"]
    if not isinstance(chapter, int) or chapter < 1:
        raise InputRangeError(f"{where}: 'kapitel' must be a chapter number")
    return Figure(
        name=str(entry["name"]),
        chapter=chapter,
        source=source,
        fmt=fmt,
        caption=str(entry.get("unterschrift") or ""),
        action=action,
    )


INKSCAPE_CANDIDATES = (
    Path(os.environ.get("INKSCAPE", "")),
    Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inkscape" / "bin" / "inkscape.com",
    Path("C:/Program Files/Inkscape/bin/inkscape.com"),
)
"""Where Inkscape is looked for: the environment variable INKSCAPE, the user's program folder
(the MSI of 1.4.4 unpacked there with ``msiexec /a`` on 2026-10-17, no administrator rights),
the machine-wide installation."""


def inkscape() -> Path:
    for candidate in INKSCAPE_CANDIDATES:
        if str(candidate) and candidate.is_file():
            return candidate
    found = shutil.which("inkscape")
    if found:
        return Path(found)
    raise InputRangeError(
        "Inkscape not found (INKSCAPE, %LOCALAPPDATA%\\Programs\\Inkscape, C:\\Program Files\\"
        "Inkscape, PATH); the thesis takes vector figures, no PNG fallback"
    )


def svg_to_pdf(source: Path, target: Path) -> None:
    """Vector PDF of the SVG by Inkscape, for a drawing that has no twin of ``plot_style.save``
    (text stays text; the TUM face is installed for the user, TeX Gyre Heros was copied into
    Inkscape's font folder on 2026-10-17; the glyphs of mathtext still come out substituted)."""
    command = [
        str(inkscape()),
        "--export-type=pdf",
        f"--export-filename={target}",
        "--export-area-page",
        str(source),
    ]
    done = subprocess.run(command, capture_output=True, text=True, timeout=300)
    if done.returncode != 0 or not target.is_file():
        raise InputRangeError(
            f"Inkscape failed on {source.name}: {done.stderr.strip() or done.stdout.strip()}"
        )


def build(figures: Sequence[Figure], check: bool = False) -> list[str]:
    lines: list[str] = []
    for figure in figures:
        what = "copy" if figure.action == "copy" else "svg → pdf (Inkscape, no current twin)"
        lines.append(
            f"{figure.target.relative_to(REPORT)} ← {figure.source.relative_to(OUTPUT)} ({what})"
        )
        if check:
            continue
        figure.target.parent.mkdir(parents=True, exist_ok=True)
        if figure.action == "copy":
            shutil.copyfile(figure.source, figure.target)
        else:
            svg_to_pdf(figure.source, figure.target)
    if not check:
        # a figure that left the listing or changed its format must not linger: graphicx
        # would pick a stale pdf before the png of the same name
        wanted = {f.target.resolve() for f in figures}
        for stale in (REPORT / "bilder").glob("kap*/*"):
            if stale.is_file() and stale.resolve() not in wanted:
                stale.unlink()
                lines.append(f"{stale.relative_to(REPORT)} entfernt (nicht mehr gelistet)")
    return lines


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--listing", type=Path, default=LISTING)
    parser.add_argument("--check", action="store_true", help="list only, write nothing")
    args = parser.parse_args(argv)
    for line in build(read_listing(args.listing), check=args.check):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
