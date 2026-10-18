"""The nomenclature of the thesis (T3): ``10_report/Nomenklatur.tex`` from the quantity
registry (``quantities.yaml``) and the selection in ``10_report/nomenklatur.yaml``; afterwards
the ``.tex`` files are scanned for symbols the tables do not carry.

    uv run --all-extras python scripts/build_nomenclature.py [--check]

Symbols are written the way the registry spells them (``m_n``, ``alpha_n``, ``rho_aP0``,
``sigma_V_Mises``, ``a_B_V``, ``E_W*``, ``sigma'_W``): the letter italic, Greek letters by name,
every subscript upright and several subscripts joined by a comma, a trailing ``*`` as a
superscript. The scan is a heuristic over the mathematics of the chapters (``$...$``,
``\\(...\\)``, ``equation``, ``align``): it reports every token of the form letter with an
optional subscript that no table row renders, so that the writer adds the entry or corrects the
text; it never edits a file. ``--check`` scans without writing.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gearcore.errors import InputRangeError  # noqa: E402

REPO = Path(__file__).resolve().parents[3]
REGISTRY = Path(__file__).resolve().parents[1] / "src" / "gearcore" / "data" / "quantities.yaml"
REPORT = REPO / "10_report"
SELECTION = REPORT / "nomenklatur.yaml"
TARGET = REPORT / "Nomenklatur.tex"
GREEK = {
    "alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta", "kappa", "lambda",
    "mu", "nu", "xi", "pi", "rho", "sigma", "tau", "phi", "chi", "psi", "omega", "vartheta",
    "Gamma", "Delta", "Theta", "Lambda", "Xi", "Pi", "Sigma", "Phi", "Psi", "Omega",
}  # fmt: skip
WORDS = {"inv", "pr", "Mises", "NH", "Hill", "stat", "zul", "max", "min", "el"}
"""Subscripts and symbols that are words, set upright."""
MATH_SPANS = re.compile(
    r"\$(?!\$)(.+?)\$|\\\((.+?)\\\)|\\begin\{(equation|align|gather)\*?\}(.+?)\\end\{\3\*?\}",
    re.DOTALL,
)
TOKEN = re.compile(
    r"(?<![A-Za-z\\])(\\[A-Za-z]+|[A-Za-z])('?)(?:\^\{?\*\}?)?"
    r"(?:_(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}|\\[A-Za-z]+|[A-Za-z0-9]))?"
)
IGNORED_COMMANDS = {
    "frac", "dfrac", "cdot", "times", "left", "right", "mathrm", "text", "textrm", "sqrt",
    "sum", "int", "ln", "log", "exp", "sin", "cos", "tan", "arctan", "arcsin", "arccos",
    "le", "ge", "leq", "geq", "approx", "pm", "mp", "infty", "quad", "qquad", "label", "ref",
    "eqref", "dots", "ldots", "cdots", "partial", "Delta", "nabla", "prime", "overline", "hat",
    "bar", "vec", "mathit", "operatorname", "begin", "end", "displaystyle", "limits", "to",
    "rightarrow", "leftarrow", "nonumber", "notag", "hspace", "vspace", "si", "SI", "num",
    "unit", "percent", "degree", "ohm", "mathcal", "mathbf", "boldsymbol", "tfrac",
}  # fmt: skip


@dataclass(frozen=True)
class Row:
    symbol: str
    latex: str
    unit: str
    description: str
    origin: str


# --- rendering ---------------------------------------------------------------------------------------


GREEK_TEX = {name: "\\" + name for name in GREEK} | {"epsilon": "\\varepsilon", "phi": "\\varphi"}
"""Greek letters as the German texts print them (ε and φ in their cursive forms)."""
VARIANT_GREEK = {"varepsilon": "epsilon", "varphi": "phi"}
"""The cursive forms read back to the registry name in the scan (``Y_{\\varepsilon}`` is the
row ``Y_epsilon``)."""


def _letter(text: str) -> str:
    """A base letter or a Greek name as LaTeX (``alpha`` → ``\\alpha``)."""
    if text in GREEK:
        return GREEK_TEX[text]
    if text in WORDS:
        return "\\mathrm{" + text + "}"
    return text


def _subscript(parts: Sequence[str]) -> str:
    """Subscript parts: Greek letters by name, everything else upright in one ``\\mathrm``;
    parts are separated by a comma unless a Greek letter is among them (``f_H_alpha`` →
    ``Hα`` as ISO 1328-1 prints it, ``a_B_V`` → ``B,V`` and ``sigma_V_Mises`` → ``V,Mises`` as
    Stommel et al. print them)."""
    greek_among = any(p in GREEK for p in parts)
    rendered: list[str] = []
    upright: list[str] = []

    def flush() -> None:
        if upright:
            rendered.append("\\mathrm{" + ("" if greek_among else ",").join(upright) + "}")
            upright.clear()

    for part in parts:
        if part in GREEK:
            flush()
            rendered.append(GREEK_TEX[part])
        else:
            upright.append(part)
    flush()
    return "".join(rendered)


def symbol_to_latex(symbol: str) -> str:
    """The registry spelling of a symbol as LaTeX mathematics (without the dollars)."""
    if not symbol or not symbol.strip():
        raise InputRangeError("empty symbol")
    if "/" in symbol and " " not in symbol:
        return "/".join(symbol_to_latex(part) for part in symbol.split("/"))
    if " " in symbol:  # 'Sigma x'
        return " ".join(symbol_to_latex(part) for part in symbol.split())
    star = symbol.endswith("*")
    if star:
        symbol = symbol[:-1]
    base, _, rest = symbol.partition("_")
    prime = base.endswith("'")
    if prime:
        base = base[:-1]
    out = _letter(base) + ("'" if prime else "")
    if rest:
        out += "_{" + _subscript(rest.split("_")) + "}"
    if star:
        out += "^{*}"
    return out


def _unit(unit: str) -> str:
    text = unit.strip()
    if text in ("-", "–", ""):
        return "--"
    if text == "deg":
        text = "°"
    text = text.replace("%", "\\%")
    return text.replace("µ", "\\textmu ").replace("°", "\\textdegree ")


def _tex(text: str) -> str:
    """A designation as text: powers of ten set as mathematics, the specials escaped."""
    text = text.replace("&", "\\&").replace("%", "\\%").replace("_", "\\_")
    text = re.sub(r"(\d+)\^(\d+)", r"$\1^{\2}$", text)
    return re.sub(r"\^(?!\{)", "\\\\textasciicircum{}", text)


def _sort_key(row: Row) -> tuple[int, str, str]:
    base = row.symbol.split("_")[0].rstrip("'*")
    greek = base in GREEK
    return (1 if greek else 0, base.lower(), row.symbol)


# --- the selection ---------------------------------------------------------------------------------


def read_registry(path: Path) -> dict[str, dict[str, Any]]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    quantities = loaded.get("quantities") if isinstance(loaded, dict) else None
    if not isinstance(quantities, dict):
        raise InputRangeError(f"{path}: expected a mapping 'quantities'")
    return {str(k): v for k, v in quantities.items() if isinstance(v, dict)}


def read_selection(path: Path) -> dict[str, Any]:
    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) if path.is_file() else None
    if not isinstance(loaded, dict):
        raise InputRangeError(f"{path}: expected a mapping")
    for key, kind in (
        ("registry", list),
        ("extra", list),
        ("indices", list),
        ("abkuerzungen", list),
    ):
        if not isinstance(loaded.get(key), kind):
            raise InputRangeError(f"{path}: '{key}' must be a list")
    if not isinstance(loaded.get("benennung", {}), dict):
        raise InputRangeError(f"{path}: 'benennung' must be a mapping key → German designation")
    return loaded


def rows_of(selection: Mapping[str, Any], registry: Mapping[str, Mapping[str, Any]]) -> list[Row]:
    rows: list[Row] = []
    seen: set[str] = set()
    # German designations where the registry carries the English wording of an ISO document
    # or no designation (the registry stays verbatim, the thesis reads German)
    overrides = {str(k): str(v) for k, v in selection.get("benennung", {}).items()}
    for name in overrides:
        if name not in registry:
            raise InputRangeError(f"nomenklatur.yaml: benennung names {name!r}, no registry key")
    for key in selection["registry"]:
        entry = registry.get(str(key))
        if entry is None:
            raise InputRangeError(f"nomenklatur.yaml: {key!r} is not a key of quantities.yaml")
        symbol = entry.get("symbol")
        if not isinstance(symbol, str):
            raise InputRangeError(f"nomenklatur.yaml: {key!r} has no symbol in the registry")
        description = overrides.get(str(key)) or entry.get("description")
        if not isinstance(description, str) or not description.strip():
            raise InputRangeError(
                f"nomenklatur.yaml: {key!r} has no designation; add one under 'benennung'"
            )
        if str(key) in seen:
            raise InputRangeError(f"nomenklatur.yaml: the key {key!r} is listed twice")
        seen.add(str(key))
        # the same letter for two quantities (k: teeth spanned, Wöhler exponent) is allowed
        # and listed twice; `clashes` names them for the writer
        rows.append(
            Row(
                symbol=symbol,
                latex=symbol_to_latex(symbol),
                unit=str(entry.get("unit", "")),
                description=description,
                origin=str(entry.get("source", "")),
            )
        )
    for i, extra in enumerate(selection["extra"]):
        if not isinstance(extra, dict):
            raise InputRangeError(f"nomenklatur.yaml: extra {i} is not a mapping")
        for field in ("symbol", "unit", "description", "source"):
            if not extra.get(field):
                raise InputRangeError(f"nomenklatur.yaml: extra {i} without '{field}'")
        symbol = str(extra["symbol"])
        if symbol in seen:
            raise InputRangeError(f"nomenklatur.yaml: the symbol {symbol!r} appears twice (extra)")
        seen.add(symbol)
        rows.append(
            Row(
                symbol,
                symbol_to_latex(symbol),
                str(extra["unit"]),
                str(extra["description"]),
                str(extra["source"]),
            )
        )
    return sorted(rows, key=_sort_key)


def render(rows: Sequence[Row], selection: Mapping[str, Any]) -> str:
    lines = [
        "% Erzeugt von scripts/build_nomenclature.py aus quantities.yaml und nomenklatur.yaml;",
        "% nicht von Hand ändern. Zeichen kursiv, Indizes und Einheiten aufrecht (DIN 1338).",
        "\\begin{longtable}{llL{0.66\\textwidth}}",
        "    \\textbf{Zeichen} & \\textbf{Einheit} & \\textbf{Benennung} \\\\",
        "    \\endhead",
    ]
    for row in rows:
        lines.append(f"    ${row.latex}$ & {_unit(row.unit)} & {_tex(row.description)} \\\\")
    lines.append("\\end{longtable}")
    lines.append("")
    lines.append("\\vspace{1em}")
    lines.append(
        "\\begin{longtable}{L{0.1\\textwidth}L{0.34\\textwidth}L{0.1\\textwidth}L{0.34\\textwidth}}"
    )
    lines.append("    \\multicolumn{4}{l}{\\textbf{Indizes}} \\\\")
    lines.append("    \\endhead")
    lines.extend(
        _two_columns(
            [
                (f"$\\mathrm{{{_tex(str(i['index']))}}}$", _tex(str(i["description"])))
                for i in selection["indices"]
            ]
        )
    )
    lines.append("\\end{longtable}")
    lines.append("")
    lines.append("\\vspace{1em}")
    lines.append(
        "\\begin{longtable}{L{0.1\\textwidth}L{0.34\\textwidth}L{0.1\\textwidth}L{0.34\\textwidth}}"
    )
    lines.append("    \\multicolumn{4}{l}{\\textbf{Abkürzungen}} \\\\")
    lines.append("    \\endhead")
    lines.extend(
        _two_columns(
            [(_tex(str(a["kurz"])), _tex(str(a["lang"]))) for a in selection["abkuerzungen"]]
        )
    )
    lines.append("\\end{longtable}")
    lines.append("")
    return "\n".join(lines)


def _two_columns(items: Sequence[tuple[str, str]]) -> list[str]:
    out: list[str] = []
    for i in range(0, len(items), 2):
        left = items[i]
        right = items[i + 1] if i + 1 < len(items) else ("", "")
        out.append(f"    {left[0]} & {left[1]} & {right[0]} & {right[1]} \\\\")
    return out


# --- the scan --------------------------------------------------------------------------------------


def canonical(base: str, prime: str, subscript: str | None) -> str:
    """A token of the text in the registry spelling (``\\sigma_{\\mathrm{V,Mises}}`` →
    ``sigma_V_Mises``), so that it compares with the selection."""
    letter = VARIANT_GREEK.get(base.lstrip("\\"), base.lstrip("\\"))
    out = letter + prime
    if subscript:
        inner = (
            subscript[1:-1] if subscript.startswith("{") and subscript.endswith("}") else subscript
        )
        inner = re.sub(r"\\mathrm\{([^}]*)\}", r"\1", inner)
        for variant, name in VARIANT_GREEK.items():
            inner = inner.replace("\\" + variant, "\\" + name)
        inner = inner.replace("\\", "").replace(",", "_").replace(" ", "")
        if inner:
            out += "_" + inner
    return out


def tokens_of_text(text: str) -> set[str]:
    found: set[str] = set()
    for match in MATH_SPANS.finditer(text):
        body = match.group(1) or match.group(2) or match.group(4) or ""
        body = re.sub(r"\\(label|ref|eqref|tag)\{[^{}]*\}", " ", body)
        # units and words set upright are no symbols; a \mathrm inside a subscript stays
        body = re.sub(r"(?<![_^{])\\(mathrm|text|textrm|si|SI|unit|num)\{[^{}]*\}", " ", body)
        for token in TOKEN.finditer(body):
            base, prime, subscript = token.groups()
            if base.startswith("\\") and base[1:] in IGNORED_COMMANDS:
                continue
            if base.startswith("\\") and VARIANT_GREEK.get(base[1:], base[1:]) not in GREEK:
                continue
            found.add(canonical(base, prime, subscript))
    return found


def scan(tex_files: Iterable[Path], known: set[str]) -> dict[str, list[str]]:
    """symbol → files that use it, for every symbol the tables do not carry."""
    missing: dict[str, list[str]] = {}
    for path in tex_files:
        text = re.sub(r"(?<!\\)%.*", "", path.read_text(encoding="utf-8"))
        for token in sorted(tokens_of_text(text)):
            generic = _generic(token)
            # a listed symbol with a running index (a_sigma,i for a_sigma) counts as known
            stripped = re.sub(r"_(i|ij)$", "", generic)
            if token in known or generic in known or stripped in known:
                continue
            missing.setdefault(token, []).append(path.name)
    return missing


def clashes(rows: Sequence[Row]) -> dict[str, list[str]]:
    """symbol → designations, for every symbol that stands for more than one quantity."""
    by_symbol: dict[str, list[str]] = {}
    for row in rows:
        by_symbol.setdefault(row.symbol, []).append(row.description)
    return {s: d for s, d in by_symbol.items() if len(d) > 1}


def known_symbols(rows: Sequence[Row], indices: Iterable[str] = ()) -> set[str]:
    """Every spelling the scan may meet for a listed symbol: the registry spelling, its
    subscript parts joined (``f_Halpha`` for ``f_H_alpha``), the bare letter, the letter with
    the gear index 1 or 2, and the listed indices as bare tokens (``i``)."""
    out: set[str] = set(indices)
    for row in rows:
        symbol = row.symbol.rstrip("*")
        for part in symbol.split("/"):
            out.add(part)
            base, _, rest = part.partition("_")
            base = base.rstrip("'")
            out.add(base)  # the bare letter counts as known
            out.update({f"{base}_1", f"{base}_2"})  # the gear index of the index table
            if rest:
                out.add(base + "_" + "".join(rest.split("_")))
    return out


def _generic(token: str) -> str:
    """A token with digit subscripts in the registry's generic spelling (``sigma_11`` →
    ``sigma_ij``, ``a_sigma_1`` → ``a_sigma_i``)."""
    base, _, rest = token.partition("_")
    if not rest:
        return token
    parts = []
    for part in rest.split("_"):
        if part.isdigit() and len(part) == 1:
            parts.append("i")
        elif part.isdigit() and len(part) == 2:
            parts.append("ij")
        else:
            parts.append(part)
    return base + "_" + "_".join(parts)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--selection", type=Path, default=SELECTION)
    parser.add_argument("--registry", type=Path, default=REGISTRY)
    parser.add_argument("--out", type=Path, default=TARGET)
    parser.add_argument("--chapters", type=Path, default=REPORT / "Kapitel")
    parser.add_argument("--check", action="store_true", help="scan only, write nothing")
    args = parser.parse_args(argv)
    selection = read_selection(args.selection)
    rows = rows_of(selection, read_registry(args.registry))
    if not args.check:
        args.out.write_text(render(rows, selection), encoding="utf-8")
        print(
            f"{args.out}: {len(rows)} Formelzeichen, {len(selection['indices'])} Indizes, "
            f"{len(selection['abkuerzungen'])} Abkürzungen"
        )
    for symbol, descriptions in clashes(rows).items():
        print(f"Hinweis: {symbol} steht für {' und '.join(descriptions)}")
    index_tokens = [str(i["index"]) for i in selection["indices"] if isinstance(i, dict)]
    missing = scan(sorted(args.chapters.glob("**/*.tex")), known_symbols(rows, index_tokens))
    if missing:
        print("Formelzeichen im Text ohne Eintrag (prüfen, dann in nomenklatur.yaml eintragen):")
        for symbol, files in missing.items():
            print(f"  {symbol}: {', '.join(sorted(set(files)))}")
    else:
        print("kein Formelzeichen im Text ohne Eintrag")
    return 0


if __name__ == "__main__":
    sys.exit(main())
