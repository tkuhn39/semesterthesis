"""The check list of the writing rules (``10_report/00_schreibregeln.md``, section 6) on the
chapters of the thesis: sentences over 30 words, dashes, colon chains, three-part enumerations
as a rhythm, repeated sentence starts, forbidden words, the count of placeholders and of the
mentions of AI-assisted programming.

    uv run --all-extras python scripts/check_thesis_text.py [FILE ...]

Without files every ``.tex`` below ``10_report/Kapitel`` is checked. The
checks are heuristics on the prose (comments, mathematics, figure and table environments and
commands are removed first); every hit names file and line, nothing is edited.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
CHAPTERS = REPO / "10_report" / "Kapitel"
MAX_WORDS = 30
FORBIDDEN = ("Agent", "Gate", "Review", "Registry", "Pipeline", "Orakel")
AI_WORDS = ("Claude", "KI-gestützt", "Fable")
DASHES = ("—", "–", " - ")
SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-ZÄÖÜ\\$])")
ENUMERATION = re.compile(r"\b\w+, \w+ und \w+\b")
"""Three items joined as ``a, b und c``: a rhythm the rules forbid when it recurs."""
NUMBER_IN_TEXT = re.compile(
    r"(?<![\w.{])(?:-?\d+,\d+|\d+\s*(?:mm|µm|MPa|GPa|Nm|N/mm|kN|°|%|HV|Hz)(?![A-Za-zäöü]))"
)
"""A value of a quantity set in the text face (rule 4.5: it belongs in math mode);
``scripts/thesis_numbers.py --fix`` converts it."""


@dataclass(frozen=True)
class Hit:
    file: str
    line: int
    rule: str
    text: str


def prose_lines(text: str) -> list[tuple[int, str]]:
    """(line number, prose) of a chapter: comments, environments that hold no prose, and
    commands with their arguments removed; mathematics kept as a placeholder word."""
    out: list[tuple[int, str]] = []
    skip = 0
    for number, raw in enumerate(text.splitlines(), start=1):
        line = re.sub(r"(?<!\\)%.*", "", raw).strip()
        if re.match(
            r"\\begin\{(figure|table|tabular|equation|align|longtable|itemize|enumerate)", line
        ):
            skip += 1
        if skip:
            if re.match(
                r"\\end\{(figure|table|tabular|equation|align|longtable|itemize|enumerate)", line
            ):
                skip -= 1
            continue
        line = re.sub(r"\$[^$]*\$", "FORMEL", line)
        line = re.sub(r"\\(?:Note|sNote|Explain|Reminder)\{[^{}]*\}", "", line)
        line = re.sub(r"\\[A-Za-z]+\*?(?:\[[^\]]*\])?(?:\{[^{}]*\})*", "", line)
        line = line.replace("~", " ").strip()
        if line:
            out.append((number, line))
    return out


def sentences(lines: Sequence[tuple[int, str]]) -> list[tuple[int, str]]:
    """Sentences with the line they start on (paragraph text joined, split at the ends)."""
    out: list[tuple[int, str]] = []
    paragraph: list[tuple[int, str]] = []

    def flush() -> None:
        if not paragraph:
            return
        start = paragraph[0][0]
        text = " ".join(t for _n, t in paragraph)
        for sentence in SENTENCE_END.split(text):
            sentence = sentence.strip()
            if sentence:
                out.append((start, sentence))
        paragraph.clear()

    previous = None
    for number, text in lines:
        if previous is not None and number > previous + 1:
            flush()
        paragraph.append((number, text))
        previous = number
    flush()
    return out


def check(path: Path) -> tuple[list[Hit], dict[str, int]]:
    text = path.read_text(encoding="utf-8")
    name = path.name
    hits: list[Hit] = []
    lines = prose_lines(text)
    for number, line in lines:
        for dash in DASHES:
            if dash in line:
                hits.append(Hit(name, number, "Gedankenstrich", line[:90]))
                break
        for word in FORBIDDEN:
            if re.search(rf"\b{word}\b", line):
                hits.append(Hit(name, number, f"Wort '{word}'", line[:90]))
        if line.count(":") >= 2:
            hits.append(Hit(name, number, "Doppelpunkt-Kette", line[:90]))
        if ENUMERATION.search(line):
            hits.append(Hit(name, number, "Dreier-Aufzählung", line[:90]))
        found = NUMBER_IN_TEXT.search(line)
        if found:
            hits.append(Hit(name, number, f"Zahl '{found.group(0)}' in Textschrift", line[:90]))
    starts: list[str] = []
    for number, sentence in sentences(lines):
        words = sentence.split()
        if len(words) > MAX_WORDS:
            hits.append(Hit(name, number, f"Satz mit {len(words)} Wörtern", sentence[:90]))
        first = words[0].lower() if words else ""
        if starts and first and first == starts[-1]:
            hits.append(Hit(name, number, f"gleicher Satzanfang '{words[0]}'", sentence[:90]))
        starts.append(first)
    counts = {
        "Platzhalter": len(re.findall(r"\\Note\{PH:", text)),
        "KI-Nennung": sum(text.count(w) for w in AI_WORDS),
        "Sätze": len(sentences(lines)),
    }
    return hits, counts


def report(paths: Iterable[Path]) -> list[str]:
    out: list[str] = []
    for path in paths:
        hits, counts = check(path)
        out.append(
            f"{path.name}: {counts['Sätze']} Sätze, {counts['Platzhalter']} Platzhalter, "
            f"{counts['KI-Nennung']} KI-Nennung(en), {len(hits)} Hinweise"
        )
        for hit in hits:
            out.append(f"  {hit.line}: {hit.rule}: {hit.text}")
    return out


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("files", nargs="*", type=Path)
    args = parser.parse_args(argv)
    paths = args.files or sorted(CHAPTERS.glob("**/*.tex"))
    for line in report(paths):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
