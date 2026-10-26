"""Tables of the appendix of the thesis, generated from the data files of the chain (T6).

    uv run --all-extras python scripts/thesis_appendix_tables.py [--out DIR]

Every table body is written as a ``.tex`` file into ``10_report/Kapitel/generiert/`` (default)
and included by the appendix files with ``\\input{Kapitel/generiert/<name>.tex}``. No number is
typed here: the script reads the data files at run time and formats them in the style of the
thesis (``10_report/00_schreibregeln.md``: every value of a quantity in math mode with ``{,}``
as the decimal comma, counts in the text face, symbols from the quantity registry).

Appendix A.2 (``sec:anhang_b``)
    ``anhang_b_normzuordnung``      the mapping of the STplus norms to the current norms, the
                                    first table of ``00_development_documentation/norm_map.md``
                                    (the cells shortened by the rules below, every norm
                                    designation checked against the source cell)
    ``anhang_b_normabweichungen``   the documented deviations and the quantities left out of the
                                    comparison, ``data/stplus/expected_differences.yaml``
    ``anhang_b_geometrie_kste``     the geometry of the gears of the STplus case kst-E and its
                                    inspection dimensions, computed with the package
                                    (``gearcore.parity`` on the packaged case ``kst_e_rerun``)
    ``anhang_b_radpaar_kste``       the pair quantities of the same case

Appendix A.4 (``sec:anhang_d``)
    ``anhang_d_kennwerte_karten``   the characteristic values of the Matscape cards QS, DY1 and
                                    DY2 at 23 and 80 degC (``data/fatigue/stommel_materials.yaml``,
                                    the Matscape CSV curves, the CONVERSE cards)
    ``anhang_d_hill_zustaende``     the Hill ratios of selected orientation states of the three
                                    CONVERSE cards at 80 degC and the mean over the nodes of the
                                    mapping of the pocket body (``stommel_hill_W3_QS``)
    ``anhang_d_klassen_festigkeit`` the class table of the check after Stommel et al.: f_tau, q,
                                    A_W and k per class
    ``anhang_d_klassen_abminderung`` the reduction factors A per class and load case

Appendix A.5 (``sec:anhang_e``)
    ``anhang_e_netzleiter_cpe4``     the refinement series of the plane sector with the
                                     formulation of CPE4 (``80_output/fe/kst_e/convergence``)
    ``anhang_e_netzleiter_cpe4i``    the same with incompatible modes
                                     (``convergence_incompatible_modes``)
    ``anhang_e_extrapolation_cpe4``  the Richardson extrapolation of every series and quantity,
    ``anhang_e_extrapolation_cpe4i`` recomputed with ``gearcore.fe.convergence.richardson``
    ``anhang_e_elementtypen``        the plane decks of the full licence per element type against
                                     the own solver (``full_licence_result/comparison.md``)
    ``anhang_e_elementtypen_grenzwerte`` limit and order of the series over the tooth thickness
                                     per element type from the Abaqus values
    ``anhang_e_volumen_schichten``   the solid decks with 20, 40 and 80 layers
    ``anhang_e_elementtest``         the element test of the Learning Edition
                                     (``le_tests/element_nlgeom/ELEMENT_TEST.md``)
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from gearcore.data import data_path, load_stommel_materials  # noqa: E402
from gearcore.errors import InputRangeError, ParseError  # noqa: E402
from gearcore.fatigue import materials as mt  # noqa: E402
from gearcore.fe import convergence as cv  # noqa: E402
from gearcore.io.converse_card import ConverseCard  # noqa: E402
from gearcore.parity import (  # noqa: E402
    compute_generation_from_data,
    compute_inspection_from_data,
    generation_data,
)
from gearcore.quantities import latex as symbol_latex  # noqa: E402
from gearcore.quantities import quantity  # noqa: E402
from gearcore.trace import load_sources  # noqa: E402

REPO = Path(__file__).resolve().parents[3]
OUT = REPO / "10_report" / "Kapitel" / "generiert"
NORM_MAP = REPO / "20_code" / "00_development_documentation" / "norm_map.md"
FE = REPO / "80_output" / "fe" / "kst_e"
CONVERGENCE = FE / "convergence"
CONVERGENCE_INCOMPATIBLE = FE / "convergence_incompatible_modes"
COMPARISON = FE / "full_licence_result" / "comparison.md"
ELEMENT_TEST = FE / "le_tests" / "element_nlgeom" / "ELEMENT_TEST.md"
ANISOTROPY_NODES = (
    FE / "tasche_serie_w1w4_qs_gerechnet" / "stommel_hill_W3_QS" / "anisotropie_knoten.csv"
)
CASE = "kst_e_rerun"
"""The packaged STplus case of the test gears kst-E (re-run with STplus 11.1F)."""
CASE_NAMES = {"kst_e_rerun": "kst-E", "kst_b_rerun": "kst-B", "kst_c_rerun": "kst-C"}
GEAR_NAMES = {"pinion": "Ritzel", "wheel": "Rad"}
STOMMEL_KEY = "Sto18"
"""Bibliography key of Stommel, Stojek, Korte 2018 in ``10_report/litbib.bib``."""
STOMMEL_PAGES = {"Tabelle 6.1": 323, "Bild 6.18": 346, "Bild 6.26": 362, "Tabelle 6.3": 371}
"""Printed pages of the class tables (header of ``stommel_materials.yaml``)."""
HEADER = (
    "% erzeugt von 20_code/10_gearcore/scripts/thesis_appendix_tables.py, nicht von Hand ändern"
)
RULE_COLOUR = "black!30"
"""Colour of the rule between two body rows (``\\arrayrulecolor`` of colortbl); the rule under
the header stays black. The rows of the wide appendix tables with wrapped cells were hard to tell
apart without them (user, 2026-10-26)."""


# --- formatting -------------------------------------------------------------------------------------


def num(value: float, digits: int) -> str:
    """A value in math mode with the decimal comma (``$-15{,}38$``); a negative zero is zero."""
    rounded = round(float(value), digits)
    if rounded == 0.0:
        rounded = 0.0
    text = f"{rounded:.{digits}f}"
    return "$" + text.replace(".", "{,}") + "$"


def count(value: int) -> str:
    """A count in the text face with a thin space as the thousands separator (``55\\,193``)."""
    return f"{int(value):,}".replace(",", "\\,")


def tex(text: str) -> str:
    """Plain text with the specials of LaTeX escaped."""
    return (
        text.replace("\\", "\\textbackslash{}")
        .replace("&", "\\&")
        .replace("%", "\\%")
        .replace("_", "\\_")
        .replace("#", "\\#")
    )


def sym(name: str) -> str:
    """The symbol of a registry quantity as inline mathematics."""
    symbol = quantity(name).symbol
    if symbol is None:
        raise InputRangeError(f"{name}: the registry has no symbol")
    return "$" + symbol_latex(symbol) + "$"


def unit_text(unit: str) -> str:
    """The unit of a registry quantity as the unit column prints it."""
    return {"-": "", "deg": "°", "rad": "rad"}.get(unit, unit)


Row = Sequence[str]
"""A table row; a row with one cell is a group header spanning every column."""


def table(
    caption: str,
    label: str,
    columns: str,
    header: Sequence[Sequence[str]],
    rows: Sequence[Row],
    *,
    tabcolsep: str = "4pt",
) -> str:
    """A ``table`` environment in the pattern of the thesis: caption above, ``\\footnotesize``,
    the header rows, a rule, the body with a light rule between its rows. ``header`` holds one or
    two header rows."""
    width = len(re.findall(r"[lcr]|L\{[^}]*\}", columns))
    lines = [
        HEADER,
        "\\begin{table}[htbp]",
        f"    \\caption{{{caption}}}",
        f"    \\label{{{label}}}",
        "    \\centering",
        "    \\footnotesize",
        f"    \\setlength{{\\tabcolsep}}{{{tabcolsep}}}",
        f"    \\begin{{tabular}}{{{columns}}}",
    ]
    for head in header:
        if len(head) != width:
            raise InputRangeError(f"{label}: header with {len(head)} cells for {width} columns")
        lines.append("        " + " & ".join(head) + " \\\\")
    lines.append("        \\hline")
    lines.append(f"        \\arrayrulecolor{{{RULE_COLOUR}}}")
    for row in rows:
        if len(row) == 1:
            lines.append(f"        \\multicolumn{{{width}}}{{l}}{{{row[0]}}} \\\\")
        elif sum(_span(cell) for cell in row) == width:
            lines.append("        " + " & ".join(row) + " \\\\")
        else:
            raise InputRangeError(f"{label}: row with {len(row)} cells for {width} columns: {row}")
        lines.append("        \\hline")
    lines.extend(["        \\arrayrulecolor{black}", "    \\end{tabular}", "\\end{table}", ""])
    return "\n".join(lines)


def _span(cell: str) -> int:
    """The number of columns a cell covers (``\\multicolumn{3}{l}{...}`` covers three)."""
    match = re.match(r"\\multicolumn\{(\d+)\}", cell)
    return int(match.group(1)) if match else 1


def spanning(cells: int, text: str) -> str:
    return f"\\multicolumn{{{cells}}}{{l}}{{{text}}}"


def body_rows(text: str) -> int:
    """The number of body rows of a generated table (the row lines after the header rule, group
    headers included, the rules between the rows not)."""
    lines = text.splitlines()
    start = lines.index("        \\hline") + 1
    end = lines.index("    \\end{tabular}")
    return sum(1 for line in lines[start:end] if line.endswith("\\\\"))


# --- markdown of the chain -----------------------------------------------------------------------------


def markdown_cells(text: str, heading: str) -> tuple[list[str], list[list[str]]]:
    """(header cells, body rows as cell lists) of the first pipe table at or after the line that
    starts with ``heading``; a cell is the stripped text between the pipes. Cells are read by
    position because a header may repeat (``eigener Löser`` twice in ``comparison.md``)."""
    lines = text.splitlines()
    starts = [i for i, line in enumerate(lines) if line.startswith(heading)]
    if not starts:
        raise ParseError(f"heading {heading!r} not found")
    i = starts[0]
    while i < len(lines) and not lines[i].startswith("|"):
        i += 1
    block: list[str] = []
    while i < len(lines) and lines[i].startswith("|"):
        block.append(lines[i])
        i += 1
    if len(block) < 3:
        raise ParseError(f"no table after {heading!r}")
    head = [cell.strip() for cell in block[0].strip().strip("|").split("|")]
    rows: list[list[str]] = []
    for line in block[2:]:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) < len(head):
            raise ParseError(f"short row under {heading!r}: {line}")
        rows.append(cells[: len(head)])
    return head, rows


def md_number(text: str) -> float:
    """A number as the markdown of the chain prints it (decimal comma, a minus sign)."""
    cleaned = text.replace("−", "-").replace(",", ".").replace(" ", "")
    try:
        return float(cleaned)
    except ValueError as error:
        raise ParseError(f"not a number: {text!r}") from error


# --- A.2 the norms ---------------------------------------------------------------------------------------

Pieces = tuple[tuple[str, str], ...]
"""(text that must stand in the source cell, text printed for it)."""


def _same(*items: str) -> Pieces:
    return tuple((item, item) for item in items)


NORM_ROWS: dict[str, tuple[Pieces, Pieces]] = {
    "Begriffe/Geometrie": (
        _same("DIN 3960:1987-03"),
        (
            ("DIN ISO 21771:2014-08", "DIN ISO 21771:2014-08"),
            ("(ISO 21771:2007)", "(ISO 21771:2007)"),
            ("Anhang NB", "mit Anhang NB"),
        ),
    ),
    "Abweichungsdefinitionen": (
        (("DIN 3960 §6–8", "DIN 3960, Abschnitte 6 bis 8"),),
        (
            ("DIN ISO 1328-1:2018-03", "DIN ISO 1328-1:2018-03"),
            ("DIN 21772:2012-07", "(zuvor DIN 21772:2012-07)"),
        ),
    ),
    "Prüfmaße": ((("DIN 3960 §3.8", "DIN 3960, Abschnitt 3.8"),), _same("DIN 21773:2014-08")),
    "Bezugsprofil / Werkzeug": (
        (("Werkzeugfaktoren", "Werkzeugfaktoren des Bezugsprofils"),),
        (
            ("DIN 867:1986-02", "DIN 867:1986-02"),
            ("ISO 53:1998", "ISO 53:1998"),
            ("DIN 3972:1952-02", "DIN 3972:1952-02 (Profile I bis IV)"),
            ("ISO 54:1996", "Modulreihe ISO 54:1996"),
        ),
    ),
    "Zahndickenabmaße / Flankenspiel": (_same("DIN 3967:1978-08"), _same("DIN 3967:1978-08")),
    "Achsabstandsabmaße": (_same("DIN 3964:1980-11"), _same("DIN 3964:1980-11")),
    "Verzahnungsqualität": (
        _same("DIN 3961/62/63:1978"),
        _same("DIN ISO 1328-1:2018-03", "DIN ISO 1328-2:2021-09"),
    ),
    "Tragfähigkeit Flanke/Fuß": (
        (("DIN 3990-1…-5:1987", "DIN 3990-1 bis -5:1987"),),
        (
            ("ISO 6336-1/-2/-3/-6:2019", "ISO 6336-1/-2/-3/-6:2019"),
            ("-5:2016", "ISO 6336-5:2016"),
            ("ISO/TS 6336-4:2019", "ISO/TS 6336-4:2019"),
        ),
    ),
    "Fressen": (_same("DIN 3990-4:1987", "ISO/TR 13989:2000"), _same("ISO/TS 6336-20/-21:2022")),
    "Graufleckigkeit": (_same("ISO/TR 15144-1:2010"), _same("ISO/TS 6336-22:2018-08")),
    "Kunststoff": (
        _same("nicht in STplus"),
        (("VDI 2736 Bl. 1–4 (2014/2016)", "VDI 2736 Blatt 1 bis 4 (2014/2016)"),),
    ),
    "Ohne aktuelle Norm": (
        _same("Lewis-Parabel", "K*/U-Faktor", "FVA-166-Verluste", "CCS 1996"),
        (("bewusst weggelassen", "nicht übernommen"),),
    ),
}
"""How the cells of ``norm_map.md`` are shortened for the thesis: every left text must stand in
the source cell (the norm designations are kept exactly), the right text is printed."""


def norm_map_rows() -> list[dict[str, str]]:
    """The rows of the first table of ``norm_map.md`` (Thema, STplus, Status, Basis)."""
    _head, rows = markdown_cells(NORM_MAP.read_text(encoding="utf-8"), "## Zuordnung STplus")
    out: list[dict[str, str]] = []
    for cells in rows:
        out.append(
            {
                "thema": cells[0].replace("**", ""),
                "stplus": cells[1].replace("**", ""),
                "status": cells[2].replace("**", ""),
                "basis": cells[3].replace("**", ""),
            }
        )
    return out


def _shortened(cell: str, pieces: Pieces, thema: str) -> str:
    out = ""
    for needle, printed in pieces:
        if needle not in cell:
            raise ParseError(f"norm_map.md, row {thema!r}: {needle!r} not in {cell!r}")
        if not out:
            out = printed
        elif printed.startswith("("):
            out += " " + printed
        else:
            out += ", " + printed
    return out


def table_norm_mapping() -> str:
    rows = norm_map_rows()
    themes = [row["thema"] for row in rows]
    if set(themes) != set(NORM_ROWS) or len(themes) != len(NORM_ROWS):
        raise ParseError(
            f"norm_map.md rows {themes} differ from the rules {sorted(NORM_ROWS)}; update NORM_ROWS"
        )
    body: list[Row] = []
    for row in rows:
        stplus_pieces, basis_pieces = NORM_ROWS[row["thema"]]
        stplus = _shortened(row["stplus"], stplus_pieces, row["thema"])
        if row["status"].startswith("zurückgezogen"):
            stplus += " (zurückgezogen)"
        basis = _shortened(row["basis"], basis_pieces, row["thema"])
        if "(Etappe 2)" in row["basis"]:
            basis += " (vorgesehen)"
        body.append([tex(row["thema"]), tex(stplus), tex(basis)])
    caption = (
        "Zuordnung der Normen, nach denen STplus 11.1F rechnet, zu den aktuellen Normen der "
        "Geometriekette. Zurückgezogene Normen sind gekennzeichnet, mit vorgesehen markierte "
        "Normen der Tragfähigkeit sind in der Kette noch nicht gerechnet."
    )
    return table(
        caption,
        "tab:anhang_normzuordnung",
        "L{3.7cm}L{4.5cm}L{6.0cm}",
        [["Thema", "STplus", "aktuelle Norm in der Kette"]],
        body,
    )


def norm_designation(source_key: str) -> str:
    """The designation of a norm of ``sources.yaml`` (``DIN 21773:2014-08``) from its title."""
    entry = load_sources().get(source_key)
    if entry is None:
        raise InputRangeError(f"unknown source {source_key!r}")
    title = str(entry["title"])
    match = re.match(r"^((?:DIN ISO|DIN|ISO)\s\d+(?:-\d+)?:\d{4}(?:-\d{2})?)", title)
    if match is None:
        raise ParseError(f"{source_key}: no norm designation at the start of {title!r}")
    return match.group(1)


_IDENTIFIER = re.compile(r"[A-Za-z]+(?:_[A-Za-z0-9]+)?")


def formula_tex(text: str) -> str:
    """A formula of the data file (``h_w = (d_Fa1 + d_Fa2) / 2 - a_w``) as inline
    mathematics: every identifier set as a symbol (base italic, index upright)."""

    def render(match: re.Match[str]) -> str:
        token = match.group(0)
        if token in ("min", "max"):
            return "\\" + token
        if token.isupper() and "_" not in token:
            return "\\mathrm{" + token + "}"
        base, _, index = token.partition("_")
        return base + ("_{\\mathrm{" + index + "}}" if index else "")

    return "$" + _IDENTIFIER.sub(render, text) + "$"


@dataclass(frozen=True)
class RuleWording:
    """German wording of a documented difference (the data file writes English prose)."""

    norm: str
    stplus: str
    example_fallback: str = ""


RULE_WORDING: dict[str, RuleWording] = {
    "diametral_ball_dimension_allowance_factor": RuleWording(
        norm="Ableitung des Zweikugelmaßes $M_{\\mathrm{dK}}$ nach der Zahndicke",
        stplus="Verhältnis der oberen Abmaße $A_{\\mathrm{Mde}} / A_{\\mathrm{sne}}$",
    ),
    "chordal_tooth_thickness_allowance": RuleWording(
        norm="Grenzmaße der Sehne aus ihrem Abmaßfaktor",
        stplus="druckt die Zahndickenabmaße $A_{\\mathrm{sne}}$ und $A_{\\mathrm{sni}}$ selbst",
        example_fallback="kein Zahlenbeispiel, verglichen werden Nennmaß und Höhe der Sehne",
    ),
    "number_of_teeth_spanned": RuleWording(
        norm="Berührung nahe dem V-Zylinder, Bereich nach Gl. (12) und (13)",
        stplus=formula_tex("k = min(INT((k_min + k_max) / 2) + 1, k_max)"),
        example_fallback="der Vergleich rechnet $k$ nach der Regel von STplus",
    ),
    "measuring_ball_diameter": RuleWording(
        norm="nächstgrößerer Tabellenwert über der idealen Kugel nach DIN 21773, Gl. (26) und (27)",
        stplus=(
            "Tabelle des Programms, größte Kugel über dem Kopfkreis, zwei Werte darunter für die "
            "Mitte der Formkreise"
        ),
        example_fallback="der Vergleich rechnet $D_{\\mathrm{M}}$ nach der Regel von STplus",
    ),
}
"""The not-compared quantities of ``expected_differences.yaml`` in the words of the thesis; a
deviation from the norm carries its formulas in the data file and needs no wording."""


def expected_differences() -> dict[str, Any]:
    path = data_path("stplus", "expected_differences.yaml")
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ParseError("expected_differences.yaml: a mapping is expected")
    if loaded.get("differences"):
        raise ParseError(
            "expected_differences.yaml: 'differences' is not empty, the sentence of the appendix "
            "that says so must change"
        )
    return loaded


def _quantity_cell(field: str) -> str:
    name = re.sub(r"_(mm|um|deg)$", "", field)
    entry = quantity(name)
    description = entry.description or name
    return f"{sym(name)}, {tex(description)}"


def _example_cell(example: Mapping[str, Any] | None, fallback: str) -> str:
    if example is None:
        return fallback
    case = CASE_NAMES.get(str(example["case"]), str(example["case"]))
    if "norm_value" in example:
        unit = "\\," + tex(str(example["unit"])) if example.get("unit") else ""
        return (
            f"{case}: Norm {num(float(example['norm_value']), 3)}{unit}, "
            f"Kette {num(float(example['gearcore_value']), 3)}{unit}, "
            f"STplus {num(float(example['stplus_value']), 3)}{unit}"
        )
    gear = GEAR_NAMES.get(str(example.get("gear", "")), "")
    where = f"{case}, {gear}" if gear else case
    return (
        f"{where}: Kette {num(float(example['gearcore_value']), 4)}, "
        f"STplus {num(float(example['stplus_value']), 3)}"
    )


def _norm_cell(new: Mapping[str, Any]) -> str:
    equation = str(new["eq"]).replace(" to ", " bis ")
    where = equation if equation.startswith("Tabelle") else f"Gl. {equation}"
    return (
        f"{norm_designation(str(new['source']))}, {tex(where)}, "
        f"Abschnitt {tex(str(new['section']))}, S.~{int(new['page'])}"
    )


def table_norm_deviations() -> str:
    loaded = expected_differences()
    body: list[Row] = []
    body.append(["Aus dem Vergleich ausgenommen"])
    for key, entry in loaded["not_compared"].items():
        wording = RULE_WORDING.get(key)
        if wording is None:
            raise InputRangeError(f"expected_differences.yaml: no wording for {key!r}")
        body.append(
            [
                _quantity_cell(str(entry["field"])),
                _norm_cell(entry["new"]) + ", " + wording.norm,
                wording.stplus,
                _example_cell(entry.get("example"), wording.example_fallback),
            ]
        )
    body.append(["Bewusste Abweichung der Kette von der Norm"])
    for entry in loaded["deviations_from_the_norm"].values():
        norm = entry["norm"]
        old = entry["old_norm"]
        norm_cell = (
            f"{_norm_cell(norm)}, {formula_tex(str(norm['formula']))}, ebenso "
            f"{norm_designation(str(old['source']))}, Gl. {tex(str(old['eq']))}, "
            f"S.~{int(old['page'])}"
        )
        chain = formula_tex(str(entry["gearcore"]["formula"]))
        stplus = formula_tex(str(entry["stplus"]["formula"]))
        body.append(
            [
                _quantity_cell(str(entry["field"])),
                norm_cell,
                f"Kette {chain}, STplus {stplus}",
                _example_cell(entry.get("example"), ""),
            ]
        )
    caption = (
        "Dokumentierte Unterschiede zwischen der Geometriekette und STplus: Größen, die STplus "
        "unter dem Namen der Norm anders definiert und die der Vergleich deshalb nach der "
        "Programmregel rechnet oder ausnimmt, sowie die bewusste Abweichung der Kette von "
        "der Norm. Werte in mm, Faktoren ohne Einheit."
    )
    return table(
        caption,
        "tab:anhang_normabweichungen",
        "L{3.1cm}L{4.5cm}L{3.6cm}L{3.0cm}",
        [["Größe", "Norm (Gleichung, Abschnitt, Seite) und Regel", "Regel von STplus", "Beispiel"]],
        body,
    )


# --- A.2 the geometry of kst-E -----------------------------------------------------------------------


def kst_e_results() -> tuple[Any, Any]:
    """(generation, inspection) of the packaged case, as the comparison with STplus computes
    them (k and D_M by the rule of STplus)."""
    data = generation_data(CASE)
    generation = compute_generation_from_data(data, data.values)
    inspection = compute_inspection_from_data(data, data.values)
    return generation, inspection


Getter = Callable[[Any, Any, str], Any]


@dataclass(frozen=True)
class GeometryRow:
    name: str
    """Registry name of the quantity."""
    getter: Getter
    digits: int
    note: str = ""
    """Appended to the symbol (``Nennmaß``)."""


def _gear(attribute: str) -> Getter:
    return lambda g, _i, role: getattr(getattr(g.gears, role), attribute)


def _pair_gear(attribute: str) -> Getter:
    return lambda g, _i, role: getattr(getattr(g.pair_geometry.gears, role), attribute)


def _pair_value(attribute: str) -> Getter:
    return lambda g, _i, role: getattr(getattr(g.pair_geometry, attribute), role)


def _result_value(attribute: str) -> Getter:
    return lambda g, _i, role: getattr(getattr(g, attribute), role)


def _inspection(attribute: str, part: str | None = None) -> Getter:
    def get(_g: Any, i: Any, role: str) -> Any:
        value = getattr(getattr(i.gears, role), attribute)
        if value is None or part is None:
            return value
        return getattr(value, part)

    return get


GEAR_ROWS: tuple[GeometryRow, ...] = (
    GeometryRow("number_of_teeth", _gear("number_of_teeth"), 0),
    GeometryRow("normal_module", lambda g, _i, _r: g.inputs.normal_module_mm, 4),
    GeometryRow("normal_pressure_angle", lambda g, _i, _r: g.inputs.normal_pressure_angle_deg, 3),
    GeometryRow("helix_angle", lambda g, _i, _r: g.inputs.helix_angle_deg, 3),
    GeometryRow("face_width", lambda g, _i, r: getattr(g.inputs.gears, r).face_width_mm, 4),
    GeometryRow("profile_shift_coefficient", _pair_value("profile_shift_coefficient"), 4),
    GeometryRow("tooth_thickness_allowance", _gear("tooth_thickness_allowance_um"), 2),
    GeometryRow(
        "generating_profile_shift_coefficient", _gear("generating_profile_shift_coefficient"), 4
    ),
    GeometryRow("tool_addendum", _gear("tool_addendum_mm"), 4),
    GeometryRow("tool_tip_radius", _gear("tool_tip_radius_mm"), 4),
    GeometryRow("tool_root_form_height", _gear("tool_root_form_height_mm"), 4),
    GeometryRow("tool_edge_break_angle", _gear("tool_edge_break_angle_deg"), 3),
    GeometryRow("reference_diameter", _pair_gear("reference_diameter_mm"), 4),
    GeometryRow("base_diameter", _pair_gear("base_diameter_mm"), 4),
    GeometryRow("working_pitch_diameter", _pair_value("working_pitch_diameter_mm"), 4),
    GeometryRow("tip_diameter", _gear("tip_diameter_mm"), 4),
    GeometryRow("tip_form_diameter", _gear("tip_form_diameter_mm"), 4),
    GeometryRow("sap_diameter", _pair_value("sap_diameter_mm"), 4),
    GeometryRow("root_form_diameter", _gear("root_form_diameter_mm"), 4),
    GeometryRow("generated_root_diameter", _gear("generated_root_diameter_mm"), 4),
    GeometryRow("tooth_depth", _gear("tooth_depth_mm"), 4),
    GeometryRow("addendum", _gear("addendum_mm"), 4),
    GeometryRow("dedendum", _gear("dedendum_mm"), 4),
    GeometryRow("tip_chamfer_radial", _gear("tip_chamfer_radial_mm"), 4),
    GeometryRow("transverse_tooth_thickness", _pair_gear("transverse_tooth_thickness_mm"), 4),
    GeometryRow("transverse_space_width", _pair_gear("transverse_space_width_mm"), 4),
    GeometryRow("transverse_tip_tooth_thickness", _gear("transverse_tip_tooth_thickness_mm"), 4),
    GeometryRow("residual_tip_thickness", _gear("residual_tip_thickness_mm"), 4),
    GeometryRow("tip_clearance", _result_value("tip_clearance_mm"), 4),
    GeometryRow("form_over_dimension", _result_value("form_over_dimension_mm"), 4),
)

INSPECTION_ROWS: tuple[GeometryRow, ...] = (
    GeometryRow("number_of_teeth_spanned", _inspection("number_of_teeth_spanned"), 0),
    GeometryRow("span_measurement", _inspection("span_measurement_mm", "nominal"), 4, "Nennmaß"),
    GeometryRow(
        "span_measurement", _inspection("span_measurement_mm", "upper"), 4, "oberes Grenzmaß"
    ),
    GeometryRow(
        "span_measurement", _inspection("span_measurement_mm", "lower"), 4, "unteres Grenzmaß"
    ),
    GeometryRow(
        "span_measuring_circle_diameter", _inspection("span_measuring_circle_diameter_mm"), 4
    ),
    GeometryRow("measuring_ball_diameter", _inspection("measuring_ball_diameter_mm"), 4),
    GeometryRow(
        "diametral_two_ball_dimension",
        _inspection("diametral_two_ball_dimension_mm", "nominal"),
        4,
        "Nennmaß",
    ),
    GeometryRow(
        "diametral_two_ball_dimension",
        _inspection("diametral_two_ball_dimension_mm", "upper"),
        4,
        "oberes Grenzmaß",
    ),
    GeometryRow(
        "diametral_two_ball_dimension",
        _inspection("diametral_two_ball_dimension_mm", "lower"),
        4,
        "unteres Grenzmaß",
    ),
    GeometryRow("ball_centre_circle_diameter", _inspection("ball_centre_circle_diameter_mm"), 4),
    GeometryRow(
        "chordal_tooth_thickness",
        _inspection("chordal_tooth_thickness_mm", "nominal"),
        4,
        "Nennmaß",
    ),
    GeometryRow("height_above_chord", _inspection("height_above_chord_mm"), 4),
)

PAIR_ROWS: tuple[tuple[str, str, int], ...] = (
    ("centre_distance", "centre_distance_mm", 4),
    ("transverse_working_pressure_angle", "transverse_working_pressure_angle_deg", 3),
    ("sum_of_profile_shift_coefficients", "sum_of_profile_shift_coefficients", 4),
    ("gear_ratio", "gear_ratio", 4),
    ("transverse_pitch", "transverse_pitch_mm", 4),
    ("transverse_base_pitch", "transverse_base_pitch_mm", 4),
    ("length_of_path_of_contact", "length_of_path_of_contact_mm", 4),
    ("transverse_contact_ratio", "transverse_contact_ratio", 4),
    ("overlap_ratio", "overlap_ratio", 4),
    ("total_contact_ratio", "total_contact_ratio", 4),
    ("common_tooth_depth", "common_tooth_depth_mm", 4),
    ("contact_face_width", "contact_face_width_mm", 4),
)
"""(registry name, attribute of ``pair_geometry``, decimals) of the pair quantities."""


def _value_cell(value: Any, digits: int) -> str:
    if value is None:
        return ""
    if isinstance(value, tuple):
        return " / ".join(num(float(v), digits) for v in value)
    if digits == 0:
        return str(int(value))
    return num(float(value), digits)


def _geometry_body(generation: Any, inspection: Any, rows: Iterable[GeometryRow]) -> list[Row]:
    body: list[Row] = []
    for row in rows:
        entry = quantity(row.name)
        symbol = sym(row.name) + (f" ({row.note})" if row.note else "")
        body.append(
            [
                symbol,
                unit_text(entry.unit),
                _value_cell(row.getter(generation, inspection, "pinion"), row.digits),
                _value_cell(row.getter(generation, inspection, "wheel"), row.digits),
            ]
        )
    return body


def table_geometry() -> str:
    generation, inspection = kst_e_results()
    body: list[Row] = _geometry_body(generation, inspection, GEAR_ROWS)
    body.append(["Prüfmaße nach DIN 21773 mit $k$ und $D_{\\mathrm{M}}$ nach der Regel von STplus"])
    body.extend(_geometry_body(generation, inspection, INSPECTION_ROWS))
    caption = (
        "Geometrie der Prüfverzahnung kst-E, mit der Geometriekette aus der STplus-Eingabedatei "
        "des Falls gerechnet: Einzelräder, Werkzeuge, erzeugte Verzahnung und Prüfmaße. "
        "Die Zahndickenabmaße sind oberes und unteres Grenzabmaß, die Zahndicke und die "
        "Lückenweite gelten für die Nennverzahnung mit $x$, die Erzeugung für "
        "$x_{\\mathrm{E}}$. Ein leeres Feld bedeutet, dass das Rad die Größe nicht hat."
    )
    return table(
        caption,
        "tab:anhang_geometrie_kste",
        "L{6.2cm}lll",
        [["Größe", "Einheit", "Ritzel", "Rad"]],
        body,
    )


def table_pair() -> str:
    generation, _inspection = kst_e_results()
    body: list[Row] = []
    for name, attribute, digits in PAIR_ROWS:
        entry = quantity(name)
        value = getattr(generation.pair_geometry, attribute)
        body.append([sym(name), unit_text(entry.unit), num(float(value), digits)])
    caption = (
        "Radpaar der Prüfverzahnung kst-E nach DIN ISO 21771, mit der Geometriekette gerechnet. "
        "Die gemeinsame Zahnhöhe folgt der Regel der Kette mit den Kopf-Formkreisen "
        "(\\tabref{tab:anhang_normabweichungen})."
    )
    return table(
        caption,
        "tab:anhang_radpaar_kste",
        "L{6.2cm}ll",
        [["Größe", "Einheit", "Wert"]],
        body,
    )


# --- A.4 the material cards and the classes -------------------------------------------------------------

CARDS: tuple[tuple[str, str], ...] = (
    ("pa46_gf30_qs", "QS"),
    ("pa46_gf30_dy1", "DY1"),
    ("pa46_gf30_dy2", "DY2"),
)
TEMPERATURES: tuple[int, ...] = (23, 80)
ISOTROPIC = (1.0 / 3.0, 1.0 / 3.0)
ALIGNED = (1.0, 0.0)
HILL_STATES: tuple[tuple[float, float], ...] = (
    ISOTROPIC,
    (0.5, 0.25),
    (0.5, 0.0),
    (0.58333, 0.08333),
    (0.625, 0.0),
    (0.75, 0.0),
    (0.875, 0.0),
    ALIGNED,
)
"""Lattice states of the cards shown in the appendix: the isotropic state, states with a_22 of
a quarter and a twelfth (the state nearest to the mean of the root fillets of the mapping), the
row a_22 = 0 up to the aligned state."""


def _curve_at(material: mt.StommelMaterial, temperature_c: float, direction_deg: int) -> Any:
    for reference, curve in material.curves_at(temperature_c):
        if reference.direction_deg == direction_deg:
            return curve
    raise InputRangeError(f"{material.name}: no {direction_deg} deg curve at {temperature_c} degC")


def _elastic_row(card: ConverseCard, temperature_c: float, state: tuple[float, float]) -> Any:
    row = card.elastic_at(temperature_c, *state)
    if abs(row.a11 - state[0]) > 1.0e-3 or abs(row.a22 - state[1]) > 1.0e-3:
        raise InputRangeError(f"{card.name}: state {state} is not on the lattice of the card")
    return row


def table_material_cards() -> str:
    materials = [(mt.load_material(name), label) for name, label in CARDS]
    cards = [(mt.converse_card(material), label) for material, label in materials]
    columns = [f"{label} ${t}$\\,\\textdegree C" for _m, label in materials for t in TEMPERATURES]

    def per_column(value: Callable[[int, int], str]) -> list[str]:
        return [value(k, t) for k in range(len(materials)) for t in TEMPERATURES]

    def check_maximum(material: mt.StommelMaterial, t: int, direction: int, key: str) -> float:
        peak, _strain = _curve_at(material, t, direction).maximum
        printed = mt.model_property(material.name, t, key)
        if abs(peak - printed) > 0.05:
            raise ParseError(
                f"{material.name} {t} degC {direction} deg: curve maximum {peak} differs from the "
                f"model property {key} = {printed}"
            )
        return float(peak)

    body: list[Row] = [
        ["Matscape, Modelleigenschaften"],
        [
            "$E_{\\mathrm{0}}$ in Fließrichtung",
            "MPa",
            *per_column(lambda k, t: num(mt.model_property(materials[k][0].name, t, "E_0_mpa"), 2)),
        ],
        [
            "$E_{\\mathrm{90}}$ quer zur Fließrichtung",
            "MPa",
            *per_column(
                lambda k, t: num(mt.model_property(materials[k][0].name, t, "E_90_mpa"), 2)
            ),
        ],
        [
            "wirksame Orientierung $a_{\\mathrm{1}}$ / $a_{\\mathrm{2}}$ des Stabs",
            "",
            *per_column(
                lambda k, _t: " / ".join(
                    num(v, 3) for v in _effective_orientation(materials[k][0].name)
                )
            ),
        ],
        ["Matscape, Kurven des Zugstabs in Fließrichtung ($0$°) und quer dazu ($90$°)"],
        [
            "Streckgrenze $\\sigma_{\\mathrm{Y}}$, Maximum der Kurve unter $0$°",
            "MPa",
            *per_column(lambda k, t: num(check_maximum(materials[k][0], t, 0, "sigma_b_0_mpa"), 2)),
        ],
        [
            "Dehnung bei $\\sigma_{\\mathrm{Y}}$, Ende der Kurve",
            "\\%",
            *per_column(lambda k, t: num(_curve_at(materials[k][0], t, 0).maximum[1], 2)),
        ],
        [
            "Maximum der Kurve unter $90$°",
            "MPa",
            *per_column(
                lambda k, t: num(check_maximum(materials[k][0], t, 90, "sigma_b_90_mpa"), 2)
            ),
        ],
        [
            "Dehnung beim Maximum unter $90$°",
            "\\%",
            *per_column(lambda k, t: num(_curve_at(materials[k][0], t, 90).maximum[1], 2)),
        ],
        ["CONVERSE-Karte, isotrope Zeile $a_{11} = a_{22} = 1/3$"],
        [
            "$E$",
            "MPa",
            *per_column(lambda k, t: num(_elastic_row(cards[k][0], t, ISOTROPIC).E1_mpa, 2)),
        ],
        [
            "$\\nu$",
            "",
            *per_column(lambda k, t: num(_elastic_row(cards[k][0], t, ISOTROPIC).nu12, 4)),
        ],
        ["CONVERSE-Karte, ausgerichteter Zustand $a_{11} = 1$"],
        [
            "$E_{\\mathrm{1}}$",
            "MPa",
            *per_column(lambda k, t: num(_elastic_row(cards[k][0], t, ALIGNED).E1_mpa, 2)),
        ],
        [
            "$E_{\\mathrm{2}}$",
            "MPa",
            *per_column(lambda k, t: num(_elastic_row(cards[k][0], t, ALIGNED).E2_mpa, 2)),
        ],
        [
            "$G_{\\mathrm{12}}$",
            "MPa",
            *per_column(lambda k, t: num(_elastic_row(cards[k][0], t, ALIGNED).G12_mpa, 2)),
        ],
    ]
    caption = (
        "Kennwerte der Werkstoffkarten von PA46-GF30 (Stanyl TW200F6, konditioniert) für die "
        "quasistatische Prüfgeschwindigkeit QS und die Dehnraten DY1 ($3$\\,1/s) und DY2 "
        "($60$\\,1/s) bei $23$ und $80$\\,\\textdegree C: die Modelleigenschaften und die "
        "Kurven des Zugstabs aus Matscape sowie die isotrope Zeile und der ausgerichtete Zustand "
        "der CONVERSE-Karte. Die Streckgrenze ist das Maximum der Kurve in Fließrichtung, der "
        "Kennwert $K$ des Nachweises nach Stommel et al."
    )
    return table(
        caption,
        "tab:anhang_kennwerte_karten",
        "L{2.9cm}l" + "l" * len(columns),
        [["Größe", "Einheit", *columns]],
        body,
        tabcolsep="3pt",
    )


def _effective_orientation(name: str) -> tuple[float, float]:
    """(a_1, a_2) of the bar as the data file records them from Matscape."""
    entry = load_stommel_materials()["materials"][name]
    values = entry["model_properties"]["effective_orientation"]
    return float(values[0]), float(values[1])


RATIOS: tuple[str, ...] = ("R11", "R22", "R33", "R12", "R13", "R23")


def anisotropy_mean() -> dict[str, float]:
    """Mean of a_11, a_22 and the six Hill ratios over the nodes of ``anisotropie_knoten.csv``."""
    keys = ("a11", "a22", *RATIOS)
    sums = dict.fromkeys(keys, 0.0)
    n = 0
    with ANISOTROPY_NODES.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            for key in keys:
                sums[key] += float(row[key])
            n += 1
    if n == 0:
        raise ParseError(f"{ANISOTROPY_NODES}: no rows")
    return {key: value / n for key, value in sums.items()} | {"n": float(n)}


def table_hill_states() -> str:
    body: list[Row] = []
    for name, label in CARDS:
        card = mt.converse_card(mt.load_material(name))
        body.append([f"Karte {label} ({tex(card.name)})"])
        for state in HILL_STATES:
            rows = [
                row
                for row in card.hill
                if abs(row.temperature_c - 80.0) < 1.0e-6
                and abs(row.a11 - state[0]) < 1.0e-4
                and abs(row.a22 - state[1]) < 1.0e-4
            ]
            if len(rows) != 1:
                raise InputRangeError(f"{card.name}: state {state} not on the lattice at 80 degC")
            row = rows[0]
            body.append(
                [
                    num(row.a11, 3),
                    num(row.a22, 3),
                    *(num(getattr(row, key), 4) for key in RATIOS),
                ]
            )
    mean = anisotropy_mean()
    body.append(
        [
            f"Mittel über die {count(int(mean['n']))} Knoten des Taschenkörpers, Zuordnung der "
            "Karte QS (W3)"
        ]
    )
    body.append([num(mean["a11"], 3), num(mean["a22"], 3), *(num(mean[key], 4) for key in RATIOS)])
    caption = (
        "Hill-Verhältnisse $R_{11}$ bis $R_{23}$ der CONVERSE-Karten bei $80$\\,\\textdegree C "
        "für ausgewählte Orientierungszustände $(a_{11}, a_{22})$ des Gitters der Karte, vom "
        "isotropen Zustand bis zum ausgerichteten, sowie das Mittel der an den Knoten "
        "interpolierten Verhältnisse der Zuordnung auf den Taschenkörper. Die Verhältnisse "
        "skalieren die Fließfläche gegen die Bezugskurve des Zugstabs \\cite{AbaqusHill25}."
    )
    return table(
        caption,
        "tab:anhang_hill_zustaende",
        "llllllll",
        [
            [
                "$a_{11}$",
                "$a_{22}$",
                "$R_{11}$",
                "$R_{22}$",
                "$R_{33}$",
                "$R_{12}$",
                "$R_{13}$",
                "$R_{23}$",
            ]
        ],
        body,
    )


def _range(bounds: mt.Range, digits: int) -> str:
    if bounds.minimum == bounds.maximum:
        return num(bounds.minimum, digits)
    return f"{num(bounds.minimum, digits)} bis {num(bounds.maximum, digits)}"


def _classes() -> list[mt.MaterialClass]:
    return list(mt.material_classes().values())


def table_classes_strength() -> str:
    body: list[Row] = []
    for cls in _classes():
        body.append(
            [
                tex(cls.designation),
                tex(cls.behaviour),
                num(cls.f_tau, 2),
                num(cls.q, 2),
                _range(cls.cyclic_reduction_factor, 2),
                _range(cls.slope_exponent, 2),
            ]
        )
    pages = STOMMEL_PAGES
    caption = (
        "Werkstoffklassen des vereinfachten Festigkeitsnachweises nach Stommel et al.: "
        "Schubfestigkeitsfaktor $f_{\\tau}$ und Steuergröße $q$ "
        f"\\cite[Tabelle 6.1, S.~{pages['Tabelle 6.1']}]{{{STOMMEL_KEY}}}, "
        "Abminderungsfaktor $A_{\\mathrm{W}}$ der Wechselfestigkeit bei $N = 10^{7}$ "
        f"\\cite[Bild 6.26, S.~{pages['Bild 6.26']}]{{{STOMMEL_KEY}}} und Neigungsexponent "
        f"$k$ der synthetischen Wöhlerlinie \\cite[Tabelle 6.3, S.~{pages['Tabelle 6.3']}]"
        f"{{{STOMMEL_KEY}}}. Die Klasse amorph (verstärkt) trägt für $f_{{\\tau}}$ und $q$ die "
        "Werte der spröden Spalte, weil das Buch keine eigene Spalte dafür führt."
    )
    return table(
        caption,
        "tab:anhang_klassen_festigkeit",
        "L{3.6cm}L{1.9cm}llL{2.4cm}L{2.6cm}",
        [["Klasse", "Verhalten", "$f_{\\tau}$", "$q$", "$A_{\\mathrm{W}}$", "$k$"]],
        body,
    )


def table_classes_reduction() -> str:
    body: list[Row] = []
    for cls in _classes():
        body.append(
            [tex(cls.designation)] + [_range(cls.a_range(case), 2) for case in mt.LOAD_CASES]
        )
    caption = (
        "Abminderungsfaktoren $A$ des statischen Nachweises nach Stommel et al. je Werkstoffklasse "
        "und Belastungsfall, kleinster und größter Wert "
        f"\\cite[Bild 6.18, S.~{STOMMEL_PAGES['Bild 6.18']}]{{{STOMMEL_KEY}}}."
    )
    return table(
        caption,
        "tab:anhang_klassen_abminderung",
        "L{3.6cm}L{2.4cm}L{2.4cm}L{2.4cm}L{2.4cm}",
        [["Klasse", "einmalig", "mehrmalig", "langzeitig", "wechselnd"]],
        body,
    )


# --- A.5 the convergence study ------------------------------------------------------------------------

SERIES: tuple[str, ...] = ("gleichmäßig", "Zahnhöhe", "Zahnfuß", "Zahndicke")
SENSITIVITY = "Empfindlichkeit"
SENSITIVITY_LABELS = {
    "b_H × 0,5": "Lastbreite $0{,}5\\,b_{\\mathrm{H}}$",
    "b_H × 2": "Lastbreite $2\\,b_{\\mathrm{H}}$",
    "Punkt D": "Stellung D",
}
QUANTITIES: tuple[tuple[str, str, int], ...] = (
    ("root_sigma1_max_mpa", "$\\sigma_{\\mathrm{1,max}}$ Fuß in MPa", 2),
    ("tip_centre_um", "$u$ Kopfmitte in \\textmu m", 2),
    ("tip_corner_um", "$u$ Kopfecke in \\textmu m", 2),
    ("strain_energy_nmm", "$U$ in N\\,mm/mm", 4),
)
FORMULATIONS: tuple[tuple[Path, str, str], ...] = (
    (CONVERGENCE, "cpe4", "Formulierung von CPE4 und C3D8 (selektiv reduzierte Integration)"),
    (CONVERGENCE_INCOMPATIBLE, "cpe4i", "Formulierung mit inkompatiblen Moden (CPE4I und C3D8I)"),
)


def read_ladder(folder: Path) -> list[dict[str, str]]:
    path = folder / "convergence.csv"
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ParseError(f"{path}: no rows")
    return rows


def series_rows(rows: Sequence[Mapping[str, str]], series: str) -> list[Mapping[str, str]]:
    """The base mesh and the levels of one series, in the order of the levels."""
    base = [r for r in rows if r["label"] == "base"]
    if len(base) != 1:
        raise ParseError("convergence.csv: exactly one base row is expected")
    own = [r for r in rows if r["series"] == series and r["label"] != "base"]
    return base + sorted(own, key=lambda r: int(r["level"]))


def table_ladder(folder: Path, suffix: str, formulation: str) -> str:
    rows = read_ladder(folder)
    body: list[Row] = []
    for row in rows:
        if row["series"] == SENSITIVITY:
            series = SENSITIVITY_LABELS.get(row["label"])
            if series is None:
                raise ParseError(f"convergence.csv: unknown sensitivity row {row['label']!r}")
        elif row["series"] in SERIES:
            series = row["series"]
        else:
            raise ParseError(f"convergence.csv: unknown series {row['series']!r}")
        body.append(
            [
                series,
                row["level"],
                count(int(row["nodes"])),
                count(int(row["elements"])),
                row["over_tooth_height"],
                row["at_tooth_root"],
                row["over_tooth_thickness"],
                num(float(row["root_sigma1_max_mpa"]), 2),
                num(float(row["tip_centre_um"]), 2),
                num(float(row["tip_corner_um"]), 2),
                num(float(row["strain_energy_nmm"]), 4),
            ]
        )
    caption = (
        f"Verfeinerungsreihen des ebenen Radsektors, {formulation}: Knoten und Elemente je "
        "Stufe, Elemente über der Zahnhöhe, je Zahnlücke am Fuß und über der Zahndicke, größte "
        "Hauptspannung an der Fußoberfläche, Verschiebung der Kopfmitte und der belasteten "
        "Kopfecke und Formänderungsenergie des Sektors. Die Stufe 1 ist das Ausgangsnetz jeder "
        "Reihe, die letzten Zeilen prüfen das Ausgangsnetz gegen die Lastbreite und die Stellung."
    )
    return table(
        caption,
        f"tab:anhang_netzleiter_{suffix}",
        "L{2.1cm}llllllllll",
        [
            [
                "Reihe",
                "Stufe",
                "Knoten",
                "Elemente",
                "Höhe",
                "Fuß",
                "Dicke",
                "$\\sigma_{\\mathrm{1,max}}$",
                "$u$ Mitte",
                "$u$ Ecke",
                "$U$",
            ],
            ["", "", "", "", "", "", "", "MPa", "\\textmu m", "\\textmu m", "N\\,mm/mm"],
        ],
        body,
        tabcolsep="3pt",
    )


def richardson_of(rows: Sequence[Mapping[str, str]], key: str) -> cv.Richardson:
    """The extrapolation of one quantity over the levels of a series (h = 1 / level)."""
    h = [1.0 / float(r["level"]) for r in rows]
    values = [float(r[key]) for r in rows]
    return cv.richardson(h, values)


def table_richardson(folder: Path, suffix: str, formulation: str) -> str:
    rows = read_ladder(folder)
    body: list[Row] = []
    for series in SERIES:
        levels = series_rows(rows, series)
        body.append([f"Reihe {series}, Stufen " + ", ".join(r["level"] for r in levels)])
        for key, name, digits in QUANTITIES:
            result = richardson_of(levels, key)
            values = " / ".join(num(v, digits) for v in result.values)
            if result.order is None or result.limit is None or result.relative_error is None:
                body.append(
                    [name, values, spanning(3, "keine monotone Konvergenz, keine Extrapolation")]
                )
                continue
            body.append(
                [
                    name,
                    values,
                    num(result.order, 2),
                    num(result.limit, digits),
                    " / ".join(num(100.0 * e, 2) for e in result.relative_error),
                ]
            )
    caption = (
        f"Extrapolation nach Richardson für den ebenen Radsektor, {formulation}: Werte je Stufe, "
        "Ordnung $p$ und Grenzwert aus den letzten drei Stufen nach \\eqref{eq:richardson} und "
        "Fehler jeder Stufe gegen den Grenzwert. Ohne monotonen Verlauf über die letzten drei "
        "Stufen wird nicht extrapoliert."
    )
    return table(
        caption,
        f"tab:anhang_extrapolation_{suffix}",
        "L{2.5cm}L{4.6cm}lL{1.5cm}L{4.0cm}",
        [["Größe", "Werte je Stufe", "$p$", "Grenzwert", "Fehler je Stufe in \\%"]],
        body,
        tabcolsep="3pt",
    )


PLANE_ELEMENTS = ("CPE4R", "CPE4", "CPE4I")


def plane_cells() -> list[list[str]]:
    """The rows of the plane decks of ``comparison.md`` as cell lists: Stufe, Element, Knoten,
    u Abaqus, u own solver, σ1 Abaqus, σ1 own solver, ALLAE (two columns share a header)."""
    header, rows = markdown_cells(COMPARISON.read_text(encoding="utf-8"), "## Ebene Decks")
    if len(header) != 8 or not header[3].startswith("u Kopfmitte Abaqus"):
        raise ParseError(f"comparison.md: unexpected columns of the plane decks {header}")
    return rows


def solid_cells() -> list[list[str]]:
    """The rows of the solid decks of ``comparison.md``: Schichten, Element, Knoten, u centre,
    u face, σ1 centre, σ1 largest layer, σ1 face, ALLSE, ALLAE."""
    header, rows = markdown_cells(COMPARISON.read_text(encoding="utf-8"), "## Volumendecks")
    if len(header) != 10 or header[0] != "Schichten":
        raise ParseError(f"comparison.md: unexpected columns of the solid decks {header}")
    return rows


def table_plane_elements() -> str:
    body: list[Row] = []
    # the markdown table carries two columns named "eigener Löser": the cells are read by position
    for cells in plane_cells():
        body.append(
            [
                "Ausgangsnetz" if cells[0] == "base" else tex(cells[0]),
                tex(cells[1]),
                count(int(cells[2])),
                num(md_number(cells[3]), 3),
                num(md_number(cells[4]), 3),
                num(md_number(cells[5]), 2),
                num(md_number(cells[6]), 2),
                num(md_number(cells[7]), 6),
            ]
        )
    caption = (
        "Ebene Decks der Konvergenzstudie auf der Abaqus-Vollversion je Elementtyp gegen den "
        "eigenen ebenen Löser in der Formulierung des Elements: Verschiebung der Kopfmitte, "
        "größte Hauptspannung an der Fußoberfläche (Knotenmittel) und künstliche Energie "
        "ALLAE der Hourglass-Kontrolle. Die Stufen t2 bis t4 verfeinern die Zahndicke auf das "
        "Zwei-, Drei- und Vierfache, u2 verfeinert gleichmäßig auf das Doppelte."
    )
    return table(
        caption,
        "tab:anhang_elementtypen",
        "llllllll",
        [
            [
                "Stufe",
                "Element",
                "Knoten",
                "$u$ Abaqus",
                "$u$ eigener Löser",
                "$\\sigma_{\\mathrm{1,max}}$ Abaqus",
                "$\\sigma_{\\mathrm{1,max}}$ eigener Löser",
                "ALLAE",
            ],
            ["", "", "", "\\textmu m", "\\textmu m", "MPa", "MPa", "N\\,mm"],
        ],
        body,
        tabcolsep="3pt",
    )


_LIMIT_LINE = re.compile(
    r"^Reihe Zahndicke mit (?P<element>\S+): σ1 = (?P<values>[^;]+) MPa; "
    r"Grenzwert (?P<limit>[-\d,]+) MPa, Ordnung (?P<order>[-\d,]+)\.$"
)


def plane_limits() -> list[tuple[str, list[float], float, float]]:
    """(element, σ1 per level in MPa, limit in MPa, order) of the series over the tooth
    thickness, as the comparison of the chain prints them from the Abaqus results (the
    extrapolation runs on the unrounded values of the ``.dat`` files, so it is not refitted
    here from the printed ones)."""
    out: list[tuple[str, list[float], float, float]] = []
    for line in COMPARISON.read_text(encoding="utf-8").splitlines():
        match = _LIMIT_LINE.match(line.strip())
        if match is None:
            continue
        values = [md_number(v) for v in match.group("values").split(", ")]
        out.append(
            (
                match.group("element"),
                values,
                md_number(match.group("limit")),
                md_number(match.group("order")),
            )
        )
    if [element for element, *_rest in out] != list(PLANE_ELEMENTS):
        raise ParseError(f"comparison.md: limit lines for {[e for e, *_r in out]} found")
    return out


def table_plane_limits() -> str:
    body: list[Row] = []
    for element, values, limit, order in plane_limits():
        body.append([element, " / ".join(num(v, 2) for v in values), num(order, 2), num(limit, 2)])
    caption = (
        "Reihe über der Zahndicke auf der Abaqus-Vollversion je Elementtyp, Stufen 1 bis 4: "
        "größte Hauptspannung an der Fußoberfläche je Stufe mit Ordnung $p$ und Grenzwert nach "
        "\\eqref{eq:richardson} aus den letzten drei Stufen."
    )
    return table(
        caption,
        "tab:anhang_elementtypen_grenzwerte",
        "lL{6.0cm}ll",
        [["Element", "$\\sigma_{\\mathrm{1,max}}$ in MPa je Stufe", "$p$", "Grenzwert in MPa"]],
        body,
    )


def table_solid_layers() -> str:
    body: list[Row] = []
    for cells in solid_cells():
        layers = cells[0].replace(" layers", "")
        body.append(
            [
                layers,
                tex(cells[1]),
                count(int(cells[2])),
                num(md_number(cells[3]), 3),
                num(md_number(cells[4]), 3),
                num(md_number(cells[5]), 2),
                num(md_number(cells[6]), 2),
                num(md_number(cells[7]), 2),
                num(md_number(cells[8]), 4),
                num(md_number(cells[9]), 6),
            ]
        )
    caption = (
        "Volumendecks des Radsektors mit 20, 40 und 80 Schichten über der Zahnbreite auf der "
        "Abaqus-Vollversion, Elemente C3D8R und C3D8I: Verschiebung der Kopfmitte in der "
        "Radmitte und an der Stirnfläche, größte Hauptspannung an der Fußoberfläche in der "
        "Radmitte, in der Schicht mit dem größten Wert und an der Stirnfläche, "
        "Formänderungsenergie ALLSE und künstliche Energie ALLAE."
    )
    return table(
        caption,
        "tab:anhang_volumen_schichten",
        "llllllllll",
        [
            [
                "Schichten",
                "Element",
                "Knoten",
                "$u$ Mitte",
                "$u$ Stirn",
                "$\\sigma_{\\mathrm{1}}$ Mitte",
                "$\\sigma_{\\mathrm{1}}$ max.",
                "$\\sigma_{\\mathrm{1}}$ Stirn",
                "ALLSE",
                "ALLAE",
            ],
            ["", "", "", "\\textmu m", "\\textmu m", "MPa", "MPa", "MPa", "N\\,mm", "N\\,mm"],
        ],
        body,
        tabcolsep="3pt",
    )


def _math_units(text: str) -> str:
    """Values with a unit in a text cell of the markdown set in math mode (``8 Nm`` to
    ``$8$\\,Nm``)."""

    def render(match: re.Match[str]) -> str:
        value = match.group(1).replace(",", "{,}")
        return f"${value}$\\,{match.group(2)}"

    return re.sub(r"(?<![\w,])(\d+(?:,\d+)?) (Nm|s|mm|MPa)\b", render, text)


def table_element_test() -> str:
    header, rows = markdown_cells(ELEMENT_TEST.read_text(encoding="utf-8"), "| Element | Variante")
    if len(header) != 6:
        raise ParseError(f"ELEMENT_TEST.md: unexpected columns {header}")
    body: list[Row] = []
    for cells in rows:
        # the variant is ``n2s`` or ``nlgeom_n2s``, the first two rows spell the switch out
        variant = cells[1]
        nlgeom = (
            "ja" if variant.lower().startswith("nlgeom") and "NLGEOM=NO" not in variant else "nein"
        )
        body.append(
            [
                tex(cells[0]),
                nlgeom,
                tex(cells[2]),
                tex(cells[3]),
                _math_units(tex(cells[4])),
                _math_units(tex(cells[5])),
            ]
        )
    caption = (
        "Elementtest in der Abaqus Learning Edition am Grobmodell mit einem Zahn und zwei "
        "Schichten, Werkstoffstufe W1, Stellung C, Momente $8$, $12$ und $16$\\,Nm am Rad: "
        "Status, letzter Schritt und Inkrement, Warnungen negativer Eigenwerte der Systemmatrix "
        "und Rechenzeit je Elementtyp mit und ohne geometrische Nichtlinearität."
    )
    return table(
        caption,
        "tab:anhang_elementtest",
        "llL{2.2cm}L{1.8cm}L{5.2cm}l",
        [
            [
                "Element",
                "NLGEOM",
                "Status",
                "Schritt / Inkrement",
                "negative Eigenwerte",
                "Zeit",
            ]
        ],
        body,
    )


# --- main ------------------------------------------------------------------------------------------------

TABLES: tuple[tuple[str, Callable[[], str]], ...] = (
    ("anhang_b_normzuordnung", table_norm_mapping),
    ("anhang_b_normabweichungen", table_norm_deviations),
    ("anhang_b_geometrie_kste", table_geometry),
    ("anhang_b_radpaar_kste", table_pair),
    ("anhang_d_kennwerte_karten", table_material_cards),
    ("anhang_d_hill_zustaende", table_hill_states),
    ("anhang_d_klassen_festigkeit", table_classes_strength),
    ("anhang_d_klassen_abminderung", table_classes_reduction),
    ("anhang_e_netzleiter_cpe4", lambda: table_ladder(*FORMULATIONS[0])),
    ("anhang_e_netzleiter_cpe4i", lambda: table_ladder(*FORMULATIONS[1])),
    ("anhang_e_extrapolation_cpe4", lambda: table_richardson(*FORMULATIONS[0])),
    ("anhang_e_extrapolation_cpe4i", lambda: table_richardson(*FORMULATIONS[1])),
    ("anhang_e_elementtypen", table_plane_elements),
    ("anhang_e_elementtypen_grenzwerte", table_plane_limits),
    ("anhang_e_volumen_schichten", table_solid_layers),
    ("anhang_e_elementtest", table_element_test),
)


def build(out: Path) -> dict[str, int]:
    """Write every table into ``out``; returns the number of body rows per file."""
    out.mkdir(parents=True, exist_ok=True)
    counts: dict[str, int] = {}
    for name, builder in TABLES:
        text = builder()
        (out / f"{name}.tex").write_text(text, encoding="utf-8", newline="\n")
        counts[name] = body_rows(text)
    return counts


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--out", type=Path, default=OUT, help="target folder of the .tex files")
    args = parser.parse_args(argv)
    counts = build(args.out)
    for name, rows in counts.items():
        print(f"{args.out / (name + '.tex')}: {rows} Zeilen")
    return 0


if __name__ == "__main__":
    sys.exit(main())
