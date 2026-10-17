"""Numbers of quantities in math mode (rule 4.5 of ``10_report/00_schreibregeln.md``, user
2026-10-17): in the prose, the tables and the captions of the chapters every value of a
quantity is set in math mode with ``{,}`` as the decimal comma and the unit upright after a
thin space (``$52$\\,mm``, ``$0{,}2034$``, ``$21{,}463$°``, ``$1{,}25\\,m_{\\mathrm{n}}$``);
counts, part numbers, dates, norm numbers and material designations stay in the text face.

    uv run --all-extras python scripts/thesis_numbers.py [--fix] [FILE ...]

Without ``--fix`` every number the rules would change is listed with file and line; with
``--fix`` the files are rewritten. What is recognised: a number with a decimal comma, a number
followed by a unit (mm, µm, MPa, Nm, N/mm, kN, N, °C, °, %, HV, h, min, s and their LaTeX
spellings) and a number followed by an inline formula that starts with a symbol (``1,25
$m_{\\mathrm{n}}$``). Left alone: mathematics, comments, equation environments, the arguments
of ``\\Note``, ``\\cite``, ``\\ref``, ``\\label``, ``\\includegraphics`` and the like, bare
integers without a unit (a count or a geometry value in a table is set by hand).
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CHAPTERS = REPO / "10_report" / "Kapitel"

UNITS = (
    r"\textmu{}m",
    r"\textmu m",
    r"\textdegree{}C",
    r"\textdegree C",
    r"\textdegree",
    "N/mm",
    "Nmm",
    "MPa",
    "GPa",
    "°C",
    "min",
    "mm",
    "µm",
    "Nm",
    "kN",
    "HV",
    "Hz",
    r"\%",
    "°",
    "N",
    "h",
    "s",
)
"""Units a number may carry, longest first so that ``Nmm`` wins over ``Nm`` over ``N``."""
NO_SPACE_UNITS = ("°", r"\textdegree")
"""Units set directly after the number (the degree sign of an angle)."""

NUMBER = r"-?(?:\d{1,3}(?:\\,\d{3})+|\d+)(?:,\d+)?"
"""A number with an optional thin-space thousands separator and a decimal comma."""
BEFORE = r"(?<![\w{.\-])(?<![^\\],)"
"""A number starts after a non-word character: not inside a word, a date, a key or a brace, and
not after a comma unless that comma is the thin space ``\\,`` (``R\\,0,5``)."""
UNIT_PATTERN = re.compile(
    BEFORE
    + "("
    + NUMBER
    + r")(?:\s|\\,|~)*("
    + "|".join(re.escape(u) for u in UNITS)
    + r")(?![A-Za-zäöüÄÖÜß{])"
)
DECIMAL_PATTERN = re.compile(BEFORE + r"(-?(?:\d{1,3}(?:\\,\d{3})+|\d+),\d+)(?!\d|,\d)")
SYMBOL_PATTERN = re.compile(
    BEFORE
    + "("
    + NUMBER
    + r")\s+\$((?:[A-Za-z]|\\(?!times|cdot|pm|le|ge|approx|ldots|dots)[A-Za-z])[^$]*)\$"
)
"""A number before an inline formula that starts with a symbol (``1,25 $m_{\\mathrm{n}}$``), not
before an operator (``2 $\\times$ 15`` stays a count)."""
AFTER_MATH_PATTERN = re.compile(
    r"(?<=\$)\s+(" + "|".join(re.escape(u) for u in UNITS) + r")(?![A-Za-zäöüÄÖÜß{])"
)
"""A unit after a closing ``$`` with a plain space (``$+20$ µm``): the thin space instead."""
PROTECTED = re.compile(
    r"\$[^$]*\$"
    r"|\\(?:Note|sNote|Explain|Reminder|cite|ref|label|figref|tabref|secref|eqref|includegraphics"
    r"|input|begin|end|usepackage|newcolumntype|hypersetup|graphicspath)\*?(?:\[[^\]]*\])?\{[^{}]*\}"
)
COMMENT = re.compile(r"(?<!\\)%.*")
EQUATION_START = re.compile(r"\\begin\{(equation|align|gather|eqnarray)\*?\}")
EQUATION_END = re.compile(r"\\end\{(equation|align|gather|eqnarray)\*?\}")


@dataclass(frozen=True)
class Change:
    file: str
    line: int
    old: str
    new: str


class _Collector:
    """The replacements of one line, so that the report names each one on its own."""

    def __init__(self) -> None:
        self.pairs: list[tuple[str, str]] = []

    def __call__(self, new: str, match: re.Match[str]) -> str:
        self.pairs.append((match.group(0), new))
        return new


def math_number(number: str) -> str:
    """``-0,203`` → ``-0{,}203`` inside ``$...$``; the thin space ``\\,`` of a thousands
    separator (``15\\,692``) stays."""
    return re.sub(r"(?<!\\),", "{,}", number)


def convert_text(text: str, collect: _Collector) -> str:
    """The rules on one stretch of prose that holds no protected span."""

    def unit(match: re.Match[str]) -> str:
        number, unit = match.group(1), match.group(2)
        gap = "" if unit in NO_SPACE_UNITS else r"\,"
        return collect(f"${math_number(number)}${gap}{unit}", match)

    def decimal(match: re.Match[str]) -> str:
        return collect(f"${math_number(match.group(1))}$", match)

    text = UNIT_PATTERN.sub(unit, text)
    return DECIMAL_PATTERN.sub(decimal, text)


def convert_line(line: str) -> tuple[str, list[tuple[str, str]]]:
    """One source line and its replacements: the comment kept, the number-before-symbol rule
    first (it joins a number to an inline formula), then the rules on every stretch outside the
    protected spans, last the thin space between a formula and its unit."""
    collect = _Collector()
    comment = COMMENT.search(line)
    code, tail = (line[: comment.start()], line[comment.start() :]) if comment else (line, "")

    def symbol(match: re.Match[str]) -> str:
        return collect(f"${math_number(match.group(1))}\\,{match.group(2)}$", match)

    def after_math(match: re.Match[str]) -> str:
        return collect(f"\\,{match.group(1)}", match)

    code = SYMBOL_PATTERN.sub(symbol, code)
    pieces: list[str] = []
    position = 0
    for span in PROTECTED.finditer(code):
        pieces.append(convert_text(code[position : span.start()], collect))
        pieces.append(span.group(0))
        position = span.end()
    pieces.append(convert_text(code[position:], collect))
    code = AFTER_MATH_PATTERN.sub(after_math, "".join(pieces))
    return code + tail, collect.pairs


def convert(text: str, name: str) -> tuple[str, list[Change]]:
    """The converted file and what changed, one entry per replacement; equation environments
    untouched."""
    out: list[str] = []
    changes: list[Change] = []
    inside_equation = False
    for number, line in enumerate(text.splitlines(keepends=True), start=1):
        if EQUATION_START.search(line):
            inside_equation = True
        if inside_equation:
            out.append(line)
            if EQUATION_END.search(line):
                inside_equation = False
            continue
        new, pairs = convert_line(line)
        changes.extend(Change(name, number, old, fresh) for old, fresh in pairs)
        out.append(new)
    return "".join(out), changes


def run(paths: Sequence[Path], fix: bool) -> list[str]:
    lines: list[str] = []
    for path in paths:
        text = path.read_text(encoding="utf-8")
        new, changes = convert(text, path.name)
        if not changes:
            continue
        lines.append(f"{path.name}: {len(changes)} Ersetzung(en)")
        for change in changes:
            lines.append(f"  {change.line}: {change.old} → {change.new}")
        if fix and new != text:
            path.write_text(new, encoding="utf-8")
    return lines


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("files", nargs="*", type=Path)
    parser.add_argument("--fix", action="store_true", help="rewrite the files")
    args = parser.parse_args(argv)
    paths = args.files or sorted(CHAPTERS.glob("**/*.tex"))
    for line in run(paths, args.fix):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
