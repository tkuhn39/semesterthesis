"""Quantity registry: the single source of truth for names, symbols and designations (ADR-108).

``data/quantities.yaml`` names every physical quantity once: program name, symbol and designation
of the governing norm with its location, the English designation of an ISO document, what other
current documents print, what STplus prints and what the replaced norms printed. Contracts take
their metadata from the registry through ``Q``; fixtures, the comparison with STplus and the
notebooks refer to it by name. Nothing else defines a symbol (project rule 3b).

Naming rule: the program name renders the designation of the governing norm in English, using the
wording of an ISO document in the repository where one exists for that designation. A contract
field is the program name without the context prefix of its model, plus ``_factor`` for a module
factor, plus the unit suffix. Arguments of single-equation functions are the symbol plus the unit
suffix (``m_n_mm``, ``alpha_n_rad``).

Typography: the symbol itself is set in italics, every subscript upright, whether it is a letter
or a digit (``latex`` renders the symbols of the registry that way).
"""

import re
from functools import lru_cache
from types import MappingProxyType
from typing import Any, Literal, Self

import yaml
from pydantic import Field, model_validator

from gearcore.data import data_path
from gearcore.errors import InputRangeError
from gearcore.models.common import FrozenModel

Unit = Literal["mm", "deg", "µm", "rad", "m/s", "1/min", "-"]
UNIT_SUFFIX: MappingProxyType[str, str] = MappingProxyType(
    {
        "mm": "_mm",
        "deg": "_deg",
        "µm": "_um",
        "rad": "_rad",
        "m/s": "_m_s",
        "1/min": "_per_min",
        "-": "",
    }
)
FACTOR_SUFFIX = "_factor"
FACTOR_MARK = "*"
"""DIN ISO 21771:2014-08, Anhang NB (p. 6): ``*`` marks a module factor."""

GREEK = MappingProxyType(
    {
        "alpha": r"\alpha",
        "beta": r"\beta",
        "gamma": r"\gamma",
        "epsilon": r"\varepsilon",
        "eta": r"\eta",
        "xi": r"\xi",
        "psi": r"\psi",
        "rho": r"\rho",
    }
)


class Designation(FrozenModel):
    """A designation as a document prints it."""

    text: str = Field(min_length=1)
    source: str = Field(min_length=1)
    location: str = Field(min_length=1)


class PrintedSymbol(FrozenModel):
    """Symbol and designation of one document for a quantity."""

    symbol: str | None
    description: str = Field(min_length=1)
    source: str = Field(min_length=1)
    location: str = Field(min_length=1)


class StplusNames(FrozenModel):
    """What STplus 11.1F prints: listing symbol and label, input key, interface key."""

    symbol: str | None = None
    label: str | None = None
    input_key: str | None = None
    interface_key: str | None = None


class Quantity(FrozenModel):
    """One entry of the registry."""

    name: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    symbol: str | None
    unit: Unit
    description: str | None
    source: str | None
    location: str | None
    english: Designation | None
    also: tuple[PrintedSymbol, ...]
    stplus: StplusNames | None
    replaced: tuple[PrintedSymbol, ...]
    note: str | None
    since: int = Field(ge=0)
    status: Literal["verified", "pending"]

    @model_validator(mode="after")
    def _verified_entries_are_complete(self) -> Self:
        if self.status == "verified" and not (self.description and self.source and self.location):
            raise ValueError(
                f"{self.name}: a verified quantity needs description, source, location"
            )
        if self.status == "pending" and (self.description or self.source or self.location):
            raise ValueError(f"{self.name}: a pending quantity carries no unverified designation")
        return self

    def field_name(self, *, prefix: str = "", factor: bool = False) -> str:
        """Name of the contract field that holds this quantity (or its module factor)."""
        base = self.name.removeprefix(prefix)
        return base + FACTOR_SUFFIX if factor else base + UNIT_SUFFIX[self.unit]

    def field_symbol(self, *, factor: bool = False) -> str | None:
        if self.symbol is None:
            return None
        return self.symbol + FACTOR_MARK if factor else self.symbol

    def field_unit(self, *, factor: bool = False) -> str:
        return "-" if factor else self.unit

    def printed_symbols(self, source: str | None = None) -> set[str]:
        """The symbol of the governing norm and those other current documents print."""
        symbols = {self.symbol} if self.symbol is not None else set()
        for printed in self.also:
            if printed.symbol is not None and source in (None, printed.source):
                symbols.add(printed.symbol)
        return symbols


@lru_cache(maxsize=1)
def quantities() -> MappingProxyType[str, Quantity]:
    """The registry, in the order of the file."""
    loaded = yaml.safe_load(data_path("quantities.yaml").read_text(encoding="utf-8"))
    entries = {name: Quantity(name=name, **entry) for name, entry in loaded["quantities"].items()}
    return MappingProxyType(entries)


def quantity(name: str) -> Quantity:
    """The registry entry ``name``; an unknown name is an ``InputRangeError``."""
    registry = quantities()
    if not isinstance(name, str) or name not in registry:
        raise InputRangeError(f"unknown quantity {name!r}; add it to data/quantities.yaml first")
    return registry[name]


def quantity_of_field(field_name: str, *, prefix: str = "") -> tuple[Quantity, bool]:
    """The quantity a contract field or fixture key holds, and whether it is its module factor."""
    registry = quantities().values()
    own = [entry for entry in registry if prefix and entry.name.startswith(prefix)]
    for entry in (*own, *registry):
        for factor in (False, True):
            used = prefix if entry.name.startswith(prefix) else ""
            if field_name == entry.field_name(prefix=used, factor=factor):
                return entry, factor
    raise InputRangeError(f"no quantity of the registry is named like the field {field_name!r}")


def Q(name: str, *, factor: bool = False, equation: str | None = None, **constraints: Any) -> Any:
    """``pydantic.Field`` of the quantity ``name`` with the metadata of the registry.

    ``factor=True`` declares the module factor of the quantity (symbol with ``*``, no unit).
    ``equation`` names the equation a result field is computed by (``'ISO21771:2014 (19)'``).
    """
    entry = quantity(name)
    extra: dict[str, Any] = {
        "quantity": name,
        "factor": factor,
        "symbol": entry.field_symbol(factor=factor),
        "unit": entry.field_unit(factor=factor),
        "designation": entry.description,
        "designation_en": entry.english.text if entry.english is not None else None,
        "source": entry.source,
        "location": entry.location,
        "status": entry.status,
    }
    if equation is not None:
        extra["equation"] = equation
    if entry.stplus is not None and entry.stplus.input_key is not None:
        extra["stplus_key"] = entry.stplus.input_key
    shown = extra["designation_en"] or entry.description or name.replace("_", " ")
    description = f"{shown} (module factor)" if factor else shown
    return Field(description=description, json_schema_extra=extra, **constraints)


def _latex_part(part: str) -> str:
    """One symbol: base in italics, subscript upright (Greek letters stay Greek)."""
    star = part.endswith(FACTOR_MARK)
    body = part.removesuffix(FACTOR_MARK)
    base, _, subscript = body.partition("_")
    rendered = GREEK.get(base, base)
    if subscript:
        pieces = [GREEK.get(p, rf"\mathrm{{{p}}}") for p in subscript.split("_")]
        rendered += "_{" + "".join(pieces) + "}"
    return rendered + ("^{*}" if star else "")


def latex(symbol: str) -> str:
    """LaTeX of a registry symbol: ``'rho_aP0*'`` gives ``\\rho_{\\mathrm{aP0}}^{*}``.

    ``'inv alpha_n'`` names the involute function of an angle, ``'E_sns/E_sni'`` a pair.
    """
    if not isinstance(symbol, str) or not re.fullmatch(r"[A-Za-z0-9_*/ ]+", symbol):
        raise InputRangeError(f"not a symbol of the registry: {symbol!r}")
    parts = []
    for part in symbol.split("/"):
        words = part.split(" ")
        if words[0] == "inv":
            argument = r"\," + _latex_part(words[1]) if len(words) > 1 else ""
            parts.append(r"\operatorname{inv}" + argument)
        else:
            parts.append(" ".join(_latex_part(word) for word in words))
    return " / ".join(parts)


STPLUS_SPELLING: MappingProxyType[str, str] = MappingProxyType({"alfa": "alpha", "eps": "epsilon"})
"""How the STplus listing spells Greek letters that the registry writes out in full."""

STPLUS = "STplus 11.1F"


class SymbolDifference(FrozenModel):
    """A symbol that another document prints for a quantity and that differs from the registry."""

    quantity: str
    symbol: str | None
    other: str
    kind: Literal["replaced", "also", "stplus"]
    description: str | None
    source: str
    location: str | None
    spelling_only: bool = False
    status: Literal["verified", "pending"]


class DesignationDifference(FrozenModel):
    """An older norm prints the same symbol with another designation."""

    quantity: str
    symbol: str
    description: str
    other: str
    source: str
    location: str


def stplus_symbol_in_registry_notation(symbol: str) -> str:
    """STplus listing symbol with Greek letters as the registry spells them, without ``*``."""
    parts = symbol.removesuffix(FACTOR_MARK).split("_")
    return "_".join(STPLUS_SPELLING.get(part, part) for part in parts)


def symbol_differences() -> tuple[SymbolDifference, ...]:
    """Every symbol of an older norm, of STplus or of another current document that is not the
    symbol of the registry. For STplus a mere spelling (``alfa_n``) is marked ``spelling_only``;
    the factor mark ``*`` is no difference, nor is a function applied to an argument
    (``inv alpha_n`` for ``inv``)."""
    found: list[SymbolDifference] = []
    for entry in quantities().values():
        for kind in ("replaced", "also"):
            for printed in getattr(entry, kind):
                if printed.symbol is None or printed.symbol == entry.symbol:
                    continue
                if not printed.symbol.startswith(f"{entry.symbol} "):
                    found.append(
                        SymbolDifference(
                            quantity=entry.name,
                            symbol=entry.symbol,
                            other=printed.symbol,
                            kind=kind,
                            description=printed.description,
                            source=printed.source,
                            location=printed.location,
                            status=entry.status,
                        )
                    )
        names = entry.stplus
        if names is None or names.symbol is None or entry.symbol is None:
            continue
        if names.symbol.removesuffix(FACTOR_MARK) != entry.symbol:
            found.append(
                SymbolDifference(
                    quantity=entry.name,
                    symbol=entry.symbol,
                    other=names.symbol,
                    kind="stplus",
                    description=names.label,
                    source=STPLUS,
                    location=None,
                    spelling_only=stplus_symbol_in_registry_notation(names.symbol) == entry.symbol,
                    status=entry.status,
                )
            )
    return tuple(found)


def _wording(text: str) -> str:
    """Designation without the differences of the spelling reform (Meßzähne, Messzähne)."""
    return text.replace("ß", "ss").casefold()


def designation_differences() -> tuple[DesignationDifference, ...]:
    """Older norms that print the symbol of the registry with another designation (verified
    quantities; remarks in parentheses are no designations)."""
    found: list[DesignationDifference] = []
    for entry in quantities().values():
        if entry.status != "verified" or entry.symbol is None or entry.description is None:
            continue
        for printed in entry.replaced:
            if printed.symbol != entry.symbol or printed.description.startswith("("):
                continue
            if _wording(printed.description) != _wording(entry.description):
                found.append(
                    DesignationDifference(
                        quantity=entry.name,
                        symbol=entry.symbol,
                        description=entry.description,
                        other=printed.description,
                        source=printed.source,
                        location=printed.location,
                    )
                )
    return tuple(found)


def _cell(text: str | None) -> str:
    return "–" if text in (None, "") else str(text).replace("|", "\\|")


def _render_differences() -> list[str]:
    """Section of the table that shows only what differs from the current norm."""
    differences = symbol_differences()
    verified = [d for d in differences if d.status == "verified"]
    lines = [
        "## Was sich gegenüber der aktuellen Norm unterscheidet",
        "",
        "Nur die Abweichungen; alle Zuordnungen stehen in den Abschnitten weiter unten. Wo ein",
        "Zeichen hier nicht auftaucht, schreiben die ersetzte Norm und STplus dasselbe Zeichen wie",
        "die aktuelle Norm.",
        "",
        "### Geänderte Formelzeichen: ersetzte und ältere Normen",
        "",
        "| Programmname | aktuell | früher | Benennung dort | Quelle |",
        "|---|---|---|---|---|",
    ]
    lines += [
        f"| `{d.quantity}` | {_cell(d.symbol)} | {d.other} | {_cell(d.description)} "
        f"| {d.source}, {d.location} |"
        for d in verified
        if d.kind == "replaced"
    ]
    lines += [
        "",
        f"### Abweichende Formelzeichen in {STPLUS}",
        "",
        "Der Stern am Zeichen (Modulfaktor) ist keine Abweichung.",
        "",
        "| Programmname | aktuell | STplus | Beschriftung im Listing |",
        "|---|---|---|---|",
    ]
    lines += [
        f"| `{d.quantity}` | {_cell(d.symbol)} | {d.other} | {_cell(d.description)} |"
        for d in verified
        if d.kind == "stplus" and not d.spelling_only
    ]
    spelled = [
        f"{d.other} = {d.symbol}" for d in verified if d.kind == "stplus" and d.spelling_only
    ]
    lines += ["", "Nur andere Schreibweise griechischer Buchstaben: " + ", ".join(spelled) + "."]
    lines += [
        "",
        "### Abweichende Formelzeichen in anderen aktuellen Dokumenten",
        "",
        "| Programmname | maßgebend | dort | Benennung dort | Quelle |",
        "|---|---|---|---|---|",
    ]
    lines += [
        f"| `{d.quantity}` | {_cell(d.symbol)} | {d.other} | {_cell(d.description)} "
        f"| {d.source}, {d.location} |"
        for d in verified
        if d.kind == "also"
    ]
    lines += [
        "",
        "### Gleiches Formelzeichen, andere Benennung in der ersetzten Norm",
        "",
        "| Programmname | Zeichen | Benennung aktuell | Benennung früher | Quelle |",
        "|---|---|---|---|---|",
    ]
    lines += [
        f"| `{d.quantity}` | {d.symbol} | {_cell(d.description)} | {_cell(d.other)} "
        f"| {d.source}, {d.location} |"
        for d in designation_differences()
    ]
    pending = [
        f"`{d.quantity}`: {d.other} ({d.source}) statt {_cell(d.symbol)}"
        for d in differences
        if d.status == "pending"
    ]
    lines += [
        "",
        "Noch nicht an der Normseite geprüft (`pending`), daher oben nicht aufgeführt: "
        + "; ".join(pending)
        + ".",
        "",
    ]
    return lines


def render_markdown() -> str:
    """The registry as a table for the documentation (German, generated, never edited by hand)."""
    lines = [
        "# Größen, Formelzeichen und Benennungen",
        "",
        "Erzeugt aus `20_code/10_gearcore/src/gearcore/data/quantities.yaml` mit",
        "`scripts/build_quantities.py`; nicht von Hand ändern. Die Datei ist die einzige Quelle für",
        "Programmnamen, Formelzeichen und Benennungen (Projektregel 3b, ADR-108).",
        "",
        "Schreibweise: Indizes nach einem Unterstrich, griechische Buchstaben ausgeschrieben. Im",
        "Formelsatz steht das Formelzeichen kursiv, jeder Index aufrecht.",
        "Status `pending`: Die Größe steht im Datenvertrag, ihre Benennung ist noch nicht an der",
        "Normseite geprüft; sie darf in keiner Rechnung verwendet werden.",
        "",
        *_render_differences(),
        "## Aktuelle Norm",
        "",
        "| Programmname | Zeichen | Einheit | Benennung der Norm | Quelle | Englische Benennung "
        "| seit | Status |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for entry in quantities().values():
        source = f"{entry.source}, {entry.location}" if entry.source else None
        english = (
            f"{entry.english.text} ({entry.english.source}, {entry.english.location})"
            if entry.english is not None
            else None
        )
        lines.append(
            f"| `{entry.name}` | {_cell(entry.symbol)} | {entry.unit} | {_cell(entry.description)} "
            f"| {_cell(source)} | {_cell(english)} | Inkrement {entry.since} | {entry.status} |"
        )
    lines += [
        "",
        "## STplus 11.1F",
        "",
        "| Programmname | Zeichen der Norm | Zeichen im Listing | Beschriftung im Listing "
        "| Eingabe (.ste) | Schnittstelle (.sts) |",
        "|---|---|---|---|---|---|",
    ]
    for entry in quantities().values():
        names = entry.stplus
        if names is None:
            continue
        lines.append(
            f"| `{entry.name}` | {_cell(entry.symbol)} | {_cell(names.symbol)} | {_cell(names.label)} "
            f"| {_cell(names.input_key)} | {_cell(names.interface_key)} |"
        )
    for title, attribute in (
        ("Ersetzte und ältere Normen", "replaced"),
        ("Andere aktuelle Dokumente", "also"),
    ):
        lines += [
            "",
            f"## {title}",
            "",
            "| Programmname | Zeichen der Norm | Zeichen dort | Benennung dort | Quelle |",
            "|---|---|---|---|---|",
        ]
        for entry in quantities().values():
            for printed in getattr(entry, attribute):
                lines.append(
                    f"| `{entry.name}` | {_cell(entry.symbol)} | {_cell(printed.symbol)} "
                    f"| {_cell(printed.description)} | {printed.source}, {printed.location} |"
                )
    lines += ["", "## Hinweise", ""]
    for entry in quantities().values():
        if entry.note:
            lines.append(f"- `{entry.name}` ({_cell(entry.symbol)}): {entry.note}")
    return "\n".join(lines) + "\n"
