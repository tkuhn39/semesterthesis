"""Figures of the state of the art taken from sources (T5): a region of a page of a PDF under
``00_literatur`` is cut out as a vector PDF for ``10_report/bilder`` ("nach [..]" in the caption).
The list ``10_report/bilder/quellbilder.yaml`` names every cut:

    quellbilder:
      - name: fva856_bild16          # file name below 80_output/thesis/quellen/<name>.pdf
        pdf: 07_themis/KST_856_I_AB_1491_unlocked.pdf   # below 00_literatur
        page: 57                     # PDF page (1-based), not the printed number
        box: [70, 400, 540, 700]     # x1 y1 x2 y2 in bp, origin bottom left (graphicx viewport)
        raster: 600                  # optional: a PNG twin in dpi for a scanned page (stencil mask)

``build`` writes every cut through a small pdflatex document (``graphicx`` with ``page``,
``viewport`` and ``clip``, ``preview`` with ``tightpage``), so the result stays a vector
graphic with the fonts of the source; ``build_thesis_figures.py`` then copies it like any
other PDF of ``80_output``. ``find`` helps to choose a box: it lists the text blocks of a page
with their coordinates (``pdftotext -bbox-layout``) and, for a caption text such as
``"Bild 16"``, the gap above that caption, which usually is the figure.

    uv run --all-extras python scripts/thesis_source_figures.py find PDF PAGE [--caption "Bild 16"]
    uv run --all-extras python scripts/thesis_source_figures.py preview PDF PAGE [--box x1 y1 x2 y2]
    uv run --all-extras python scripts/thesis_source_figures.py build [NAME ...]

``preview`` renders the page (or the box) at 72 dpi as PNG into the scratch folder given by
``--out`` (default ``80_output/thesis/quellen/preview``), so one pixel is one bp and a box can be
read off the image. Coordinates of ``pdftotext`` have their origin at the top left; the script
converts them to the bottom-left origin of the viewport with the page height.
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gearcore.errors import InputRangeError  # noqa: E402

REPO = Path(__file__).resolve().parents[3]
LITERATUR = REPO / "00_literatur"
LISTING = REPO / "10_report" / "bilder" / "quellbilder.yaml"
OUTPUT = REPO / "80_output" / "thesis" / "quellen"

WRAPPER = r"""\documentclass{article}
\usepackage{graphicx}
\usepackage[active,tightpage]{preview}
\setlength{\PreviewBorder}{0pt}
\begin{document}
\begin{preview}
\includegraphics[page=%(page)d,viewport=%(x1)g %(y1)g %(x2)g %(y2)g,clip]{%(pdf)s}
\end{preview}
\end{document}
"""


@dataclass(frozen=True)
class Cut:
    name: str
    pdf: Path
    page: int
    box: tuple[float, float, float, float]
    raster: int | None = None
    """Resolution in dpi of an additional PNG twin (``raster:`` in the listing); for a scanned
    source whose page is a CCITT stencil mask, which the pdf.js viewer of the editor leaves
    blank (seen 2026-10-21 with Fig. 2 of DE 10 2008 045 318 B3). The vector cut is still
    written; the thesis takes the PNG through ``bilder.yaml`` (``format: png``)."""


def read_listing(path: Path = LISTING) -> list[Cut]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    cuts: list[Cut] = []
    names: set[str] = set()
    for i, entry in enumerate(data.get("quellbilder") or []):
        where = f"{path.name} Eintrag {i + 1}"
        name = str(entry.get("name") or "")
        if not re.fullmatch(r"[A-Za-z0-9_\-]+", name):
            raise InputRangeError(f"{where}: name {name!r} must be a plain file name")
        if name in names:
            raise InputRangeError(f"{where}: name {name!r} repeats")
        names.add(name)
        pdf = LITERATUR / str(entry["pdf"])
        if not pdf.is_file():
            raise InputRangeError(f"{where}: {pdf} is not a file")
        page = int(entry["page"])
        values = [float(v) for v in entry["box"]]
        if len(values) != 4 or values[0] >= values[2] or values[1] >= values[3]:
            raise InputRangeError(f"{where}: box must be x1 y1 x2 y2 with x1 < x2 and y1 < y2")
        raster = entry.get("raster")
        if raster is not None and not (isinstance(raster, int) and 72 <= raster <= 1200):
            raise InputRangeError(f"{where}: raster must be a resolution in dpi between 72 and 1200")
        cuts.append(Cut(name=name, pdf=pdf, page=page, box=(values[0], values[1], values[2], values[3]),
                        raster=raster))
    return cuts


def page_size(pdf: Path, page: int) -> tuple[float, float]:
    """Width and height of the page in bp from ``pdfinfo``."""
    out = subprocess.run(
        ["pdfinfo", "-f", str(page), "-l", str(page), str(pdf)],
        capture_output=True, text=True, check=True, encoding="utf-8", errors="replace",
    ).stdout
    match = re.search(rf"Page\s+{page}\s+size:\s+([\d.]+)\s+x\s+([\d.]+)", out)
    if match is None:
        match = re.search(r"Page size:\s+([\d.]+)\s+x\s+([\d.]+)", out)
    if match is None:
        raise InputRangeError(f"pdfinfo gives no page size for {pdf.name} page {page}")
    return float(match.group(1)), float(match.group(2))


def text_blocks(pdf: Path, page: int) -> list[tuple[float, float, float, float, str]]:
    """(x_min, y_min, x_max, y_max, text) of every text block, top-left origin as pdftotext."""
    out = subprocess.run(
        ["pdftotext", "-f", str(page), "-l", str(page), "-bbox-layout", str(pdf), "-"],
        capture_output=True, check=True,
    ).stdout.decode("utf-8", errors="replace")
    root = ET.fromstring(out)
    ns = {"h": "http://www.w3.org/1999/xhtml"}
    blocks: list[tuple[float, float, float, float, str]] = []
    for block in root.iter("{http://www.w3.org/1999/xhtml}block"):
        words = [w.text or "" for w in block.iter("{http://www.w3.org/1999/xhtml}word")]
        corners = []
        for name in ("xMin", "yMin", "xMax", "yMax"):
            value = block.get(name)
            if value is None:
                raise InputRangeError(f"pdftotext block without {name} on page {page} of {pdf.name}")
            corners.append(float(value))
        blocks.append((corners[0], corners[1], corners[2], corners[3], " ".join(words)))
    del ns
    return sorted(blocks, key=lambda b: (b[1], b[0]))


def find(pdf: Path, page: int, caption: str | None) -> None:
    width, height = page_size(pdf, page)
    blocks = text_blocks(pdf, page)
    print(f"{pdf.name} Seite {page}: {width:.0f} x {height:.0f} bp, {len(blocks)} Textblöcke")
    for x1, y1, x2, y2, text in blocks:
        print(f"  x {x1:6.1f}..{x2:6.1f}  y(oben) {y1:6.1f}..{y2:6.1f}  {text[:70]}")
    if caption is None:
        return
    hits = [b for b in blocks if caption.lower() in b[4].lower()]
    if not hits:
        print(f"Bildunterschrift {caption!r} nicht gefunden")
        return
    for cap in hits:
        above = [b for b in blocks if b[3] <= cap[1] + 1.0 and b is not cap]
        top = max((b[3] for b in above), default=0.0)
        y_top_bp = height - cap[1]          # bottom of the figure in viewport coordinates
        y_bottom_bp = height - top          # top of the figure in viewport coordinates
        print(
            f"Lücke über {caption!r}: viewport {cap[0]:.0f} {y_top_bp:.0f} {max(cap[2], width - cap[0]):.0f} "
            f"{y_bottom_bp:.0f}  (Textspalte x {cap[0]:.0f}..{cap[2]:.0f}; prüfen mit preview)"
        )


def preview(pdf: Path, page: int, box: Sequence[float] | None, out: Path) -> Path:
    out.mkdir(parents=True, exist_ok=True)
    stem = out / f"{pdf.stem}_s{page}"
    args = ["pdftoppm", "-f", str(page), "-l", str(page), "-r", "72", "-png"]
    if box is not None:
        width, height = page_size(pdf, page)
        x1, y1, x2, y2 = box
        args += ["-x", str(int(x1)), "-y", str(int(height - y2)),
                 "-W", str(int(x2 - x1)), "-H", str(int(y2 - y1))]
        stem = out / f"{pdf.stem}_s{page}_box"
    subprocess.run(args + [str(pdf), str(stem)], check=True)
    files = sorted(out.glob(f"{stem.name}*.png"))
    if not files:
        raise InputRangeError("pdftoppm wrote no file")
    return files[-1]


def build(cuts: Sequence[Cut], output: Path = OUTPUT) -> list[Path]:
    output.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for cut in cuts:
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp)
            # a copy without spaces or umlauts, so the file name needs no quoting in TeX
            source = work / "quelle.pdf"
            shutil.copyfile(cut.pdf, source)
            x1, y1, x2, y2 = cut.box
            (work / "cut.tex").write_text(
                WRAPPER % {"page": cut.page, "x1": x1, "y1": y1, "x2": x2, "y2": y2, "pdf": "quelle.pdf"},
                encoding="utf-8",
            )
            result = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "cut.tex"],
                cwd=work, capture_output=True, text=True, encoding="utf-8", errors="replace",
            )
            if result.returncode != 0 or not (work / "cut.pdf").is_file():
                log = (work / "cut.log").read_text(encoding="utf-8", errors="replace") if (work / "cut.log").is_file() else result.stdout
                raise InputRangeError(f"{cut.name}: pdflatex failed:\n{log[-1500:]}")
            target = output / f"{cut.name}.pdf"
            shutil.copyfile(work / "cut.pdf", target)
            written.append(target)
            print(f"{cut.name}: {cut.pdf.name} Seite {cut.page} -> {target.relative_to(REPO)}")
            if cut.raster is not None:
                subprocess.run(
                    ["pdftoppm", "-r", str(cut.raster), "-gray", "-png", "-singlefile",
                     str(work / "cut.pdf"), str(output / cut.name)],
                    check=True,
                )
                twin = output / f"{cut.name}.png"
                written.append(twin)
                print(f"{cut.name}: Rasterzwilling {cut.raster} dpi -> {twin.relative_to(REPO)}")
    return written


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    p_find = commands.add_parser("find", help="text blocks of a page and the gap above a caption")
    p_find.add_argument("pdf", type=Path)
    p_find.add_argument("page", type=int)
    p_find.add_argument("--caption")
    p_prev = commands.add_parser("preview", help="render a page or a box at 72 dpi")
    p_prev.add_argument("pdf", type=Path)
    p_prev.add_argument("page", type=int)
    p_prev.add_argument("--box", type=float, nargs=4, metavar=("X1", "Y1", "X2", "Y2"))
    p_prev.add_argument("--out", type=Path, default=OUTPUT / "preview")
    p_build = commands.add_parser("build", help="cut every listed figure (or the named ones)")
    p_build.add_argument("names", nargs="*")
    p_build.add_argument("--listing", type=Path, default=LISTING)
    args = parser.parse_args(argv)
    if args.command == "find":
        find(args.pdf if args.pdf.is_absolute() else LITERATUR / args.pdf, args.page, args.caption)
        return 0
    if args.command == "preview":
        pdf = args.pdf if args.pdf.is_absolute() else LITERATUR / args.pdf
        print(preview(pdf, args.page, args.box, args.out))
        return 0
    cuts = read_listing(args.listing)
    if args.names:
        unknown = set(args.names) - {c.name for c in cuts}
        if unknown:
            raise InputRangeError(f"not listed: {', '.join(sorted(unknown))}")
        cuts = [c for c in cuts if c.name in args.names]
    build(cuts)
    return 0


if __name__ == "__main__":
    sys.exit(main())
