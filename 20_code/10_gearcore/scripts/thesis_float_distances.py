"""Distance between every figure or table of the built thesis and its first mention in the text
(user, 2026-10-25: floats close to where the text names them).

    uv run --all-extras python scripts/thesis_float_distances.py --build DIR [--max-pages N]

``DIR`` holds the ``SA_16_03738470.pdf`` and its ``.aux`` of one build (latexmk output folder).
The ``.aux`` gives every label its number and page (``\\newlabel{fig:x}{{5.3}{42}...}``); the PDF
text per page (``pdftotext -layout -f n -l n``) gives the page of the first mention "Bild 5.3" or
"Tabelle 5.3" that is not the caption itself (a caption starts its line with the number). Prints
one line per float with the pages and the distance, the floats farther than ``--max-pages`` first,
and exits 1 when any float lies before its first mention or farther than ``--max-pages`` after it.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

LABEL = re.compile(r"\\newlabel\{((?:fig|tab):[^}]*)\}\{\{([\d.]+)\}\{(\d+)\}")
MAIN = "SA_16_03738470"


@dataclass(frozen=True)
class Float:
    label: str
    number: str
    page: int
    kind: str  # Bild or Tabelle


def floats_of(aux: Path) -> list[Float]:
    out = []
    for found in LABEL.finditer(aux.read_text(encoding="utf-8", errors="replace")):
        label, number, page = found.groups()
        out.append(
            Float(label, number, int(page), "Bild" if label.startswith("fig:") else "Tabelle")
        )
    return out


def page_texts(pdf: Path, pages: int) -> list[str]:
    texts = []
    for n in range(1, pages + 1):
        done = subprocess.run(
            ["pdftotext", "-layout", "-f", str(n), "-l", str(n), str(pdf), "-"],
            capture_output=True,
            check=True,
        )
        texts.append(done.stdout.decode("utf-8", errors="replace"))
    return texts


def number_of_pages(pdf: Path) -> int:
    done = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, check=True)
    for line in done.stdout.decode("utf-8", errors="replace").splitlines():
        if line.startswith("Pages:"):
            return int(line.split()[1])
    raise RuntimeError("pdfinfo prints no page count")


def all_mentions(texts: list[str], kind: str, number: str, arabic_offset: int) -> list[int]:
    """Arabic pages of every mention outside a caption, in order; empty when never mentioned.
    ``arabic_offset`` is the number of PDF pages before arabic page 1. A mention may break
    across two lines of the extracted text ("Bild" at the end of one line, "2.9" at the start of
    the next); a caption is a mention that starts its line and continues with a colon."""
    pattern = re.compile(
        rf"(?<![\w.]){re.escape(kind)}\s+{re.escape(number)}(?!\d)(?!\.\d)", re.MULTILINE
    )
    pages = []
    for i, text in enumerate(texts[arabic_offset:]):
        for found in pattern.finditer(text):
            line_start = text.rfind("\n", 0, found.start()) + 1
            before = text[line_start : found.start()].strip()
            after = text[found.end() : found.end() + 1]
            if before == "" and after == ":":
                continue
            pages.append(i + 1)
            break
    return pages


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--build", type=Path, required=True)
    parser.add_argument("--max-pages", type=int, default=1)
    args = parser.parse_args(argv)
    pdf = args.build / f"{MAIN}.pdf"
    aux = args.build / f"{MAIN}.aux"
    floats = floats_of(aux)
    texts = page_texts(pdf, number_of_pages(pdf))
    # the first arabic page: the PDF page that carries the heading of chapter 1 as a line of its
    # own (the table of contents prints the same words with dots and a page number behind them)
    offset = 0
    heading = re.compile(r"^\s*1\s+Einleitung\s*$", re.MULTILINE)
    for i, text in enumerate(texts):
        if heading.search(text):
            offset = i  # PDF page i + 1 is arabic page 1
            break
    rows = []
    for item in floats:
        mentions = all_mentions(texts, item.kind, item.number, offset)
        mention = mentions[0] if mentions else None
        nearest = min(mentions, key=lambda m: abs(item.page - m)) if mentions else None
        distance = None if nearest is None else item.page - nearest
        rows.append((item, mention, distance))

    def outside(mention: int | None, distance: int | None) -> bool:
        return mention is None or distance is None or distance < 0 or distance > args.max_pages

    bad = [r for r in rows if outside(r[1], r[2])]
    rows.sort(key=lambda r: (r[2] is None, -(abs(r[2]) if r[2] is not None else 0)))
    print(f"{len(floats)} Floats, Offset der arabischen Seiten {offset}, {len(bad)} außerhalb")
    for item, mention, distance in rows:
        flag = "!!" if outside(mention, distance) else "  "
        print(
            f"{flag} {item.kind} {item.number:<6} Seite {item.page:>3}  erste Nennung "
            f"{mention!s:>4}  Abstand zur nächsten {distance!s:>4}  {item.label}"
        )
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
