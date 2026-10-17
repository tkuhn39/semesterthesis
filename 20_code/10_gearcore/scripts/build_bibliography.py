"""The bibliography of the thesis (T2): ``10_report/litbib.bib`` is the thesis' own list, every
entry transcribed from the title page of a source in ``00_literatur``. This script checks the
list against the chapters and, on request, copies older entries from the Citavi export of the
Bachelor thesis, which serves as a template only.

    uv run --all-extras python scripts/build_bibliography.py check
    uv run --all-extras python scripts/build_bibliography.py take Ehr07 Erh08

``check``: every ``\\cite`` key of the chapters has an entry (missing keys are listed and fail
the check), entries nobody cites are listed, duplicate keys are refused, a norm (``@manual``
with ``keywords = {norm}``) needs an author (DIN, ISO, VDI), a title that carries the
designation and a date with the month, every entry needs a year or date. ``take``: the named
entries of the Citavi export appended to ``litbib.bib`` with the key rules of the thesis
(umlauts rewritten, ``@misc`` with a
number → ``@manual`` with ``keywords = {norm}``, ``@misc`` with a url → ``@online``, Citavi's
``price`` and a DOI that is no DOI dropped) and a comment that the title page is still to be
checked; a key that exists is refused.
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gearcore.errors import InputRangeError  # noqa: E402

REPO = Path(__file__).resolve().parents[3]
REPORT = REPO / "10_report"
LITBIB = REPORT / "litbib.bib"
CITAVI = REPO / "00_literatur" / "Literaturverzeichnis_BA-Kuhn_Tim_2024-04-28_23-54-47.bib"
CITE = re.compile(r"\\(?:paren|text|foot|auto|smart)?cite[a-z]*\*?(?:\[[^\]]*\]){0,2}\{([^}]*)\}")
ENTRY_HEAD = re.compile(r"@(\w+)\s*\{\s*([^,\s]+)\s*,", re.MULTILINE)
DROPPED_FIELDS = {"price"}
UMLAUTS = {"ä": "ae", "ö": "oe", "ü": "ue", "Ä": "Ae", "Ö": "Oe", "Ü": "Ue", "ß": "ss"}
NORM_AUTHORS = ("DIN", "ISO", "VDI", "IEC", "JIS", "SAE", "AGMA")
DESIGNATION = re.compile(r"\b(DIN|ISO|VDI|IEC|JIS|SAE|AGMA)\b.*\d")


@dataclass
class Entry:
    key: str
    kind: str
    fields: dict[str, str] = field(default_factory=dict)

    def render(self) -> str:
        lines = [f"@{self.kind}{{{self.key},"]
        for name, value in self.fields.items():
            lines.append(f"  {name} = {{{value}}},")
        lines.append("}")
        return "\n".join(lines)


# --- BibTeX reading --------------------------------------------------------------------------------


def _braced_value(text: str, start: int) -> tuple[str, int]:
    """The value starting at ``text[start]`` (a ``{`` or a ``"``), and the index after it."""
    if text[start] == "{":
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    return text[start + 1 : i], i + 1
        raise InputRangeError("unbalanced braces in the bib file")
    if text[start] == '"':
        end = text.index('"', start + 1)
        return text[start + 1 : end], end + 1
    match = re.match(r"[^,}]*", text[start:])
    value = match.group(0) if match else ""
    return value.strip(), start + len(value)


def parse_bib(text: str) -> list[Entry]:
    """Every ``@type{key, field = value, ...}`` of a BibTeX file (comments between entries are
    skipped); a repeated key is refused."""
    entries: list[Entry] = []
    seen: set[str] = set()
    for head in ENTRY_HEAD.finditer(text):
        kind, key = head.group(1).lower(), head.group(2)
        if kind in ("comment", "preamble", "string"):
            continue
        if key in seen:
            raise InputRangeError(f"the bib file repeats the key {key!r}")
        seen.add(key)
        i = head.end()
        fields: dict[str, str] = {}
        while True:
            m = re.compile(r"\s*(\w+)\s*=\s*").match(text, i)
            if m is None:
                break
            name = m.group(1).lower()
            value, i = _braced_value(text, m.end())
            fields[name] = " ".join(value.split())
            m2 = re.compile(r"\s*,?\s*").match(text, i)
            i = m2.end() if m2 else i
            if i < len(text) and text[i] == "}":
                break
        entries.append(Entry(key=key, kind=kind, fields=fields))
    return entries


def ascii_key(key: str) -> str:
    """A citation key pdflatex accepts: umlauts transcribed, other marks stripped."""
    out = "".join(UMLAUTS.get(ch, ch) for ch in key)
    out = unicodedata.normalize("NFKD", out).encode("ascii", "ignore").decode("ascii")
    if not out:
        raise InputRangeError(f"the key {key!r} has no ASCII letters")
    return out


def classify(entry: Entry) -> Entry:
    """The entry type the FZG style groups by: norms as ``@manual`` (keyword ``norm``, the
    author stays and makes the label [DIN14]), web pages as ``@online`` (the type alone puts
    them under the web pages; the keyword ``web`` is for other types that belong there);
    Citavi's ``price`` and a DOI that is no DOI dropped."""
    fields = {k: v for k, v in entry.fields.items() if k not in DROPPED_FIELDS}
    if "doi" in fields and not fields["doi"].startswith("10."):
        fields.pop("doi")
    kind = entry.kind
    if kind == "misc" and "number" in fields:
        kind = "manual"
        fields.setdefault("keywords", "norm")
    elif kind == "misc" and ("url" in fields or "howpublished" in fields):
        kind = "online"
    return Entry(key=entry.key, kind=kind, fields=fields)


# --- the check -------------------------------------------------------------------------------------


def cited_keys(tex_files: Iterable[Path]) -> set[str]:
    keys: set[str] = set()
    for path in tex_files:
        text = re.sub(r"(?<!\\)%.*", "", path.read_text(encoding="utf-8"))
        for match in CITE.finditer(text):
            keys.update(k.strip() for k in match.group(1).split(",") if k.strip())
    return keys


def entry_problems(entry: Entry) -> list[str]:
    """What the FZG citation rules miss in one entry."""
    problems: list[str] = []
    f = entry.fields
    if "year" not in f and "date" not in f:
        problems.append("ohne year oder date")
    if entry.kind == "manual" and "norm" in f.get("keywords", ""):
        if f.get("author", "").split()[:1] not in ([a] for a in NORM_AUTHORS):
            problems.append("Norm ohne Herausgeber als author (DIN, ISO, VDI, ...)")
        if not DESIGNATION.search(f.get("title", "")):
            problems.append("Norm ohne Bezeichnung mit Nummer im title")
        if not re.fullmatch(r"\d{4}-\d{2}(-\d{2})?", f.get("date", "")):
            problems.append("Norm ohne date mit Monat (JJJJ-MM)")
    elif "author" not in f and "editor" not in f:
        problems.append("ohne author oder editor")
    if "title" not in f:
        problems.append("ohne title")
    return problems


def check(litbib: Path, chapters: Path) -> tuple[list[str], list[str], dict[str, list[str]]]:
    """(cited keys without entry, entries nobody cites, problems per entry)."""
    entries = parse_bib(litbib.read_text(encoding="utf-8"))
    keys = {e.key for e in entries}
    cited = cited_keys(sorted(chapters.glob("**/*.tex")))
    missing = sorted(k for k in cited if k not in keys)
    unused = sorted(k for k in keys if k not in cited)
    problems = {e.key: p for e in entries if (p := entry_problems(e))}
    return missing, unused, problems


# --- take from the Citavi export -----------------------------------------------------------------------


def take(keys: Sequence[str], citavi: Path, litbib: Path) -> list[Entry]:
    """Append the named Citavi entries to ``litbib.bib`` under the key rules of the thesis."""
    export = {e.key: e for e in parse_bib(citavi.read_text(encoding="utf-8"))}
    present = {e.key for e in parse_bib(litbib.read_text(encoding="utf-8"))}
    taken: list[Entry] = []
    for key in keys:
        source = export.get(key)
        if source is None:
            raise InputRangeError(f"{key!r} is not in the Citavi export {citavi.name}")
        new_key = ascii_key(key)
        if new_key in present:
            raise InputRangeError(f"{new_key!r} is already in {litbib.name}")
        taken.append(classify(Entry(key=new_key, kind=source.kind, fields=source.fields)))
        present.add(new_key)
    with litbib.open("a", encoding="utf-8") as handle:
        for entry in taken:
            handle.write(
                f"\n% Herkunft: Citavi-Export der BA ({citavi.name}), Titelseite noch zu prüfen\n"
            )
            handle.write(entry.render() + "\n")
    return taken


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--litbib", type=Path, default=LITBIB)
    parser.add_argument("--chapters", type=Path, default=REPORT / "Kapitel")
    parser.add_argument("--citavi", type=Path, default=CITAVI)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="cited keys, unused entries, rule violations")
    take_parser = commands.add_parser("take", help="copy entries of the Citavi export")
    take_parser.add_argument("keys", nargs="+")
    args = parser.parse_args(argv)
    if args.command == "take":
        for entry in take(args.keys, args.citavi, args.litbib):
            print(f"{entry.key}: @{entry.kind} übernommen, Titelseite prüfen")
        return 0
    missing, unused, problems = check(args.litbib, args.chapters)
    entries = len(parse_bib(args.litbib.read_text(encoding="utf-8")))
    print(f"{args.litbib.name}: {entries} Einträge, {entries - len(unused)} zitiert")
    if missing:
        print("zitiert ohne Eintrag: " + ", ".join(missing))
    if unused:
        print("Einträge ohne Zitat: " + ", ".join(unused))
    for key, items in problems.items():
        print(f"{key}: " + "; ".join(items))
    return 1 if missing or problems else 0


if __name__ == "__main__":
    sys.exit(main())
