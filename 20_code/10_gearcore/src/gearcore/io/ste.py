"""STplus ``.ste`` input files (FVA STplus 11.1F manual §3.2, §4).

Grammar (manual §3.2, Bild 3.1): the file runs from ``$ Anfang`` to ``$ Ende``; ``$ NAME`` opens a
block; a line is ``KEY = v1 v2 ...`` (gear 1 first, gear 2 second); ``%`` is the placeholder for
"not given"; ``#`` starts a comment; keys are case-insensitive and only their first 24 characters
count; several ``KEY = value`` pairs may share one line (load spectra, written as ``KEY = v KEY = v``).
Tool, material and lubricant blocks are named after the entry that references them
(``WERKZEUG_VORVERZ.``, ``WERKSTOFF``, ``SCHMIERSTOFF``). ``$ Neu`` / ``$ Variante`` start further
datasets (not supported here).

Single-value semantics (manual §3.2 p. 11): on per-gear keys a lone value belongs to gear 1 and
gear 2 counts as "not given"; only the pair keys (``NORMALMODUL``, ``ACHSABSTAND``,
``EINGRIFFSWINKEL``, ``SCHRAEGUNGSWINKEL``) take one value for the pair. Numbers use the STplus
grammar (optional sign, digits, decimal point, ``E``/``D`` exponent) — anything else is a
``ParseError``, never a silently absent value.

The raw layer (``SteFile``) keeps every token; the typed layer maps the geometry, tool and
material blocks onto gearcore contracts and reports explicitly what it could not map.
"""

import math
import re
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from gearcore.errors import NotSupportedError, ParseError
from gearcore.models.common import FrozenModel, Pair
from gearcore.models.inputs import (
    GearInput,
    GearKind,
    MaterialKind,
    MaterialRef,
    PairInput,
    QualitySystem,
    SpanMeasurement,
    ToolKind,
    ToolProfile,
)
from gearcore.models.materials import GearStrength, MaterialRecord, Provenance, SteelData

PLACEHOLDER = "%"
KEY_LENGTH = 24
_FIRST_KEY = re.compile(r"^([^\s=]+)\s*=")
# further pairs on the same line: whitespace, KEY, whitespace, '=', whitespace (load spectra)
_MORE_KEYS = re.compile(r"\s([^\s=]+)\s+=(?=\s)")
_NUMBER = re.compile(r"^[-+]?(\d+\.?\d*|\.\d+)([eEdD][-+]?\d+)?$")
_LINE_BREAK = re.compile(r"\r?\n")


class SteEntry(FrozenModel):
    key: str
    """Upper-cased key, truncated to 24 characters as STplus does."""
    values: tuple[str, ...]
    """Raw tokens; ``%`` placeholders are kept so positions stay meaningful."""
    line: int

    def number(self, index: int) -> float | None:
        """Numeric value at ``index``; ``None`` for a placeholder or a missing position.

        A token that is neither a placeholder nor an STplus number is a ``ParseError`` (a German
        decimal comma, ``nan``, ``1_0`` ... must never be reported as "absent").
        """
        if index >= len(self.values):
            return None
        token = self.values[index]
        if token == PLACEHOLDER:
            return None
        if not _NUMBER.match(token):
            raise ParseError(
                f"line {self.line}: {self.key} value {index + 1}: non-numeric token {token!r}"
            )
        value = float(token.replace("d", "e").replace("D", "E"))
        if not math.isfinite(value):
            raise ParseError(
                f"line {self.line}: {self.key} value {index + 1}: {token!r} exceeds the number range"
            )
        return value

    def numbers(self) -> tuple[float | None, ...]:
        return tuple(self.number(i) for i in range(len(self.values)))


class SteSection(FrozenModel):
    name: str
    """Block name as written (case preserved) — tool/material names are case-sensitive labels."""
    entries: tuple[SteEntry, ...] = ()

    def get(self, key: str) -> SteEntry | None:
        """The single entry with ``key``; a repeated key (load spectra) is ambiguous → ``ParseError``."""
        found = self.get_all(key)
        if len(found) > 1:
            lines = ", ".join(str(e.line) for e in found)
            raise ParseError(
                f"block '$ {self.name}': key {found[0].key} appears {len(found)} times "
                f"(lines {lines}); use get_all for repeated keys"
            )
        return found[0] if found else None

    def get_all(self, key: str) -> tuple[SteEntry, ...]:
        wanted = _normalise_key(key)
        return tuple(entry for entry in self.entries if entry.key == wanted)


class SteFile(FrozenModel):
    sections: tuple[SteSection, ...] = ()
    path: str | None = None

    def section(self, name: str) -> SteSection | None:
        wanted = name.strip().upper()
        for section in self.sections:
            if section.name.upper() == wanted:
                return section
        return None

    def find(self, key: str) -> SteEntry | None:
        for section in self.sections:
            entry = section.get(key)
            if entry is not None:
                return entry
        return None

    def keys(self) -> set[str]:
        return {entry.key for section in self.sections for entry in section.entries}


def is_number(token: str) -> bool:
    """True if ``token`` is an STplus number (sign, digits, decimal point, E/D exponent)."""
    return bool(_NUMBER.match(token))


def _normalise_key(key: str) -> str:
    return key.strip().upper()[:KEY_LENGTH]


def parse_ste(text: str, *, path: str | None = None) -> SteFile:
    """Parse ``.ste`` text. Raises ``ParseError`` on structural problems, never guesses."""
    sections: list[SteSection] = []
    seen_names: set[str] = set()
    current_name: str | None = None
    current_entries: list[SteEntry] = []
    saw_start = False

    def flush() -> None:
        nonlocal current_entries
        if current_name is not None:
            sections.append(SteSection(name=current_name, entries=tuple(current_entries)))
        current_entries = []

    for number, raw in enumerate(_LINE_BREAK.split(text), start=1):
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("$"):
            flush()
            current_name = line[1:].strip()
            if not current_name:
                raise ParseError(f"line {number}: empty block name")
            upper = current_name.upper()
            if upper in seen_names:
                raise ParseError(f"line {number}: block '$ {current_name}' appears twice")
            seen_names.add(upper)
            if upper == "ANFANG":
                saw_start = True
            continue
        if "=" not in line:
            raise ParseError(f"line {number}: expected 'KEY = value' or '$ BLOCK', got {line!r}")
        if current_name is None:
            raise ParseError(f"line {number}: entry before the first '$' block")
        for key, values in _split_pairs(line, number):
            current_entries.append(
                SteEntry(key=_normalise_key(key), values=tuple(values), line=number)
            )
    flush()
    if not saw_start:
        raise ParseError("missing '$ Anfang'")
    if "ENDE" not in seen_names:
        raise ParseError("missing '$ Ende'")
    return SteFile(sections=tuple(sections), path=path)


def _split_pairs(line: str, number: int) -> list[tuple[str, list[str]]]:
    """Split ``K1 = a b K2 = c`` into ``[(K1, [a, b]), (K2, [c])]``; ``Fall=Test`` stays a value."""
    first = _FIRST_KEY.match(line)
    if not first:
        raise ParseError(f"line {number}: cannot read key in {line!r}")
    starts: list[tuple[str, int, int]] = [(first.group(1), first.start(1), first.end())]
    for match in _MORE_KEYS.finditer(line, first.end()):
        starts.append((match.group(1), match.start(1), match.end()))
    pairs: list[tuple[str, list[str]]] = []
    for index, (key, _key_start, value_start) in enumerate(starts):
        value_end = starts[index + 1][1] if index + 1 < len(starts) else len(line)
        pairs.append((key, line[value_start:value_end].split()))
    return pairs


def load_ste(path: Path) -> SteFile:
    """Read a ``.ste`` file (Latin-1, as written by STplus/Windows editors)."""
    return parse_ste(path.read_text(encoding="latin-1"), path=str(path))


# --- typed extraction -----------------------------------------------------------------------

TOOL_KEYS: dict[str, str] = {
    "KOPFHOEHENFAKTOR": "addendum_factor",
    "FUSSHOEHENFAKTOR": "dedendum_factor",
    "FUSSFORMHOEHENFAKTOR": "root_form_height_factor",
    "KOPFABRUNDUNGSFAKTOR": "tip_radius_factor",
    "WKZ_NORMALMODUL": "normal_module_mm",
    "WKZ_EINGRIFFSWINKEL": "profile_angle_deg",
    "KANTENBRECHWINKEL": "edge_break_angle_deg",
    "PROTUBERANZBETRAG": "protuberance_mm",
    "PROTUBERANZWINKEL": "protuberance_angle_deg",
    "BEARB_ZUGABE_WKZ": "machining_allowance_mm",
}
"""Rack-type tool keys (manual §4.16.2.1) → ``ToolProfile`` fields."""

SHAPER_PREFIX = "SR_"
PROFILE_PREFIX = "PW_"

GEOMETRY_KEYS_MAPPED = {
    "ZAEHNEZAHL",
    "NORMALMODUL",
    "ACHSABSTAND",
    "EINGRIFFSWINKEL",
    "SCHRAEGUNGSWINKEL",
    "PROFILVERSCHIEBUNG_N",
    "AUFTEILUNG_X1X2",
    "ZAHNBREITE",
    "KOPFKREISDM",
    "MESSZAEHNEZAHL_K",
    "MESSZAEHNEZAHL",
    "ZAHNWEITE",
    "OBERES_ZAHNW_ABMASS",
    "UNTERES_ZAHNW_ABMASS",
    "ABMASS_TOL_REIHE",
    "DIN_QUALITAET",
    "ISO_QUALITAET",
    "KOPFKANTENBRUCH",
    "WERKZEUG_VORVERZ.",
    "WERKZEUG_FERTIGVERZ.",
}


class SteImport(FrozenModel):
    """Result of the typed extraction: the contracts plus everything that was not mapped."""

    pair: PairInput
    materials: tuple[MaterialRecord, ...] = ()
    unmapped_keys: tuple[str, ...] = ()
    """Keys present in the geometry block that the typed layer ignores (kept visible, never silent)."""
    notes: tuple[str, ...] = ()


def _not_valid(error: ValidationError, what: str) -> ParseError:
    """Reading an input file is not mathematics: the verdict of a contract is a parse error."""
    reasons = "; ".join(
        ".".join(str(part) for part in item["loc"]) + ": " + str(item["msg"])
        for item in error.errors()
    )
    return ParseError(f"{what} is no valid input: {reasons}")


ABSENT_MEANS_NONE: dict[str, str] = {
    "PROTUBERANZBETRAG": "no protuberance",
    "BEARB_ZUGABE_WKZ": "no machining allowance of the tool",
}
"""Tool keys whose absence in a ``.ste`` block means that the feature is absent. The contract
requires the value, so the importer states the zero and says so in its notes (user decision
2026-09-30: a blanket zero only together with a note)."""


def tool_from_section(section: SteSection, notes: list[str] | None = None) -> ToolProfile:
    """Build a ``ToolProfile`` from a ``$ WKZ_...`` block; shaper/profile tools are flagged, not guessed.

    A block without ``PROTUBERANZBETRAG`` or ``BEARB_ZUGABE_WKZ`` yields a tool with the value
    zero; each such zero is appended to ``notes`` (when a list is passed) as a note.
    """
    keys = {entry.key for entry in section.entries}
    if any(k.startswith(SHAPER_PREFIX) for k in keys):
        raise NotSupportedError(
            f"tool {section.name!r}: shaper cutter (SR_*) tools are an extension point"
        )
    if any(k.startswith(PROFILE_PREFIX) for k in keys):
        raise NotSupportedError(
            f"tool {section.name!r}: profile/form (PW_*) tools are an extension point"
        )
    fields: dict[str, Any] = {"kind": ToolKind.RACK, "name": section.name}
    for key, field in TOOL_KEYS.items():
        entry = section.get(key)
        if entry is None:
            continue
        value = entry.number(0)
        if value is None:
            raise ParseError(f"tool {section.name!r}: {key} has no value (line {entry.line})")
        fields[field] = value
    if "addendum_factor" not in fields or "tip_radius_factor" not in fields:
        raise ParseError(
            f"tool {section.name!r}: KOPFHOEHENFAKTOR and KOPFABRUNDUNGSFAKTOR are required "
            "(STplus would default them; gearcore does not guess)"
        )
    for key, meaning in ABSENT_MEANS_NONE.items():
        if TOOL_KEYS[key] not in fields:
            fields[TOOL_KEYS[key]] = 0.0
            if notes is not None:
                notes.append(f"tool {section.name!r}: {key} not given → 0 ({meaning})")
    try:
        return ToolProfile(**fields)
    except ValidationError as error:
        raise _not_valid(error, f"tool {section.name!r}") from error


def _values(section: SteSection, key: str) -> tuple[float | None, float | None]:
    """(gear 1, gear 2) numbers of ``key``; missing positions are ``None``."""
    entry = section.get(key)
    if entry is None:
        return (None, None)
    if len(entry.values) > 2:
        raise ParseError(
            f"line {entry.line}: {key} has {len(entry.values)} values; a pair has two gears"
        )
    return (entry.number(0), entry.number(1) if len(entry.values) > 1 else None)


def _pair_key(section: SteSection, key: str) -> float | None:
    """A pair key (one value for both gears); two values are accepted only when equal."""
    first, second = _values(section, key)
    if second is not None and first is not None and second != first:
        raise NotSupportedError(
            f"{key}: different values per gear ({first}, {second}) are not supported"
        )
    if first is None and second is not None:
        raise ParseError(f"{key}: value for gear 1 is a placeholder but gear 2 has {second}")
    return first


def _integer(value: float | None, key: str, gear: int, *, unsupported: bool = False) -> int | None:
    if value is None:
        return None
    if value != int(value):
        message = f"{key} for gear {gear}: {value} is not an integer"
        if unsupported:
            raise NotSupportedError(
                message + " (fractional tooth numbers / virtual gears are not supported)"
            )
        raise ParseError(message)
    return int(value)


def material_from_section(section: SteSection, kind: MaterialKind) -> MaterialRecord:
    """Material block (manual §4.16.3) → ``MaterialRecord``; the kind must be given by the caller.

    STplus files carry no explicit steel/plastic flag for user-defined blocks (``WERKSTOFFART`` only
    knows metals), so the caller states the kind — rule 9 forbids inferring it from E-modulus.
    """
    try:
        return _material_from_section(section, kind)
    except ValidationError as error:
        raise _not_valid(error, f"material {section.name!r}") from error


def _material_from_section(section: SteSection, kind: MaterialKind) -> MaterialRecord:
    prov = Provenance(source=f"STplus:{section.name}", location="$ " + section.name)

    def num(key: str) -> float | None:
        entry = section.get(key)
        return None if entry is None else entry.number(0)

    strength = GearStrength(
        sigma_Hlim_MPa=num("DIN3990/87_SIGMA_HLIM"),
        sigma_FE_MPa=num("DIN3990/87_SIGMA_FE"),
        sigma_Flim_MPa=num("DIN3990/87_SIGMA_FLIM"),
        n_ref_H=num("DIN3990/87_NL_REF_H"),
        n_ref_F=num("DIN3990/87_NL_REF_F"),
        provenance=prov,
    )
    modulus = num("ELASTIZITAETSMODUL")
    poisson = num("QUERKONTRAKTIONSZAHL")
    if kind is MaterialKind.STEEL:
        if modulus is None or poisson is None:
            raise ParseError(
                f"material {section.name!r}: ELASTIZITAETSMODUL and QUERKONTRAKTIONSZAHL required"
            )
        heat = section.get("WAERMEBEHANDLUNG")
        density = num("DICHTE_RADKRANZMATERIAL")
        steel = SteelData(
            youngs_modulus_MPa=modulus,
            poisson_ratio=poisson,
            density_kg_m3=None if density is None else density * 1e9,  # STplus: kg/mm3
            heat_treatment=None if heat is None else " ".join(heat.values),
            surface_hardness_HV=num("OBERFLAECHENHAERTE"),
            core_hardness_HV=num("KERNHAERTE_ZAHN"),
            yield_strength_MPa=num("STRECKGRENZE_SIGMA02"),
            tensile_strength_MPa=num("BRUCHGRENZE"),
            provenance=prov,
        )
        return MaterialRecord(kind=kind, name=section.name, steel=steel, strength=strength)
    # plastic: STplus has no polymer datasheet keys; E and nu stay in the provenance note (stage 2: typed)
    note = f"E={modulus} MPa, nu={poisson} from the .ste block (no ISO 10350 datasheet layer)"
    strength = strength.model_copy(update={"provenance": prov.model_copy(update={"note": note})})
    return MaterialRecord(kind=kind, name=section.name, strength=strength)


def pair_input_from_ste(
    ste: SteFile,
    *,
    material_kinds: dict[str, MaterialKind] | None = None,
) -> SteImport:
    """Map the first dataset of a ``.ste`` onto ``PairInput`` (+ materials, + unmapped keys).

    ``material_kinds`` names the kind of every referenced material block (``{"WST_PA66":
    MaterialKind.PLASTIC}``); blocks without a stated kind are reported in ``notes`` and skipped.

    Whatever a contract rejects while the file is read (``ToolProfile``, ``SpanMeasurement``,
    ``GearInput``, ``MaterialRecord``, ``PairInput``) leaves this function as a ``ParseError``.
    """
    try:
        return _pair_input_from_ste(ste, material_kinds)
    except ValidationError as error:
        raise _not_valid(error, "the file") from error


def _pair_input_from_ste(ste: SteFile, material_kinds: dict[str, MaterialKind] | None) -> SteImport:
    names = [s.name.upper() for s in ste.sections]
    if "NEU" in names or "VARIANTE" in names:
        raise NotSupportedError("multi-dataset .ste files ($ Neu / $ Variante) are not supported")
    geo = ste.section("Geometriedaten")
    if geo is None:
        raise ParseError("no '$ Geometriedaten' block")
    notes: list[str] = []

    teeth_raw = _values(geo, "ZAEHNEZAHL")
    if teeth_raw[0] is None or teeth_raw[1] is None:
        raise NotSupportedError(
            "ZAEHNEZAHL must give both gears (single gear / ZAEHNEZAHLVERHAELTNIS not supported)"
        )
    teeth: list[int] = []
    for gear, z in enumerate(teeth_raw, start=1):
        z_int = _integer(z, "ZAEHNEZAHL", gear, unsupported=True)
        if z_int is None:
            raise ParseError(f"gear {gear}: ZAEHNEZAHL has no value")
        if z_int < 0:
            raise NotSupportedError("internal gear (ZAEHNEZAHL < 0) is an extension point")
        teeth.append(z_int)

    module = _pair_key(geo, "NORMALMODUL")
    if module is None:
        raise ParseError("NORMALMODUL missing")
    alpha = _pair_key(geo, "EINGRIFFSWINKEL")
    if alpha is None:
        # the default of 20 degrees belongs to the user interface of STplus; the program itself
        # rejects such a batch input (probe data/stplus_program/probes/no_pressure_angle)
        raise ParseError("EINGRIFFSWINKEL missing (STplus rejects a batch input without it)")
    beta = _pair_key(geo, "SCHRAEGUNGSWINKEL")
    if beta is None:
        beta = 0.0
        notes.append("SCHRAEGUNGSWINKEL not given → 0 (spur gears)")

    split = _values(geo, "AUFTEILUNG_X1X2")[0]
    if split not in (None, 0.0):
        raise NotSupportedError(
            f"AUFTEILUNG_X1X2 = {split:g} (manual Bild 4.12: DIN 3992 / equal sliding / equal root "
            "stress / ... distribution of the profile-shift sum) is not supported; only 0 = x1 given"
        )
    if geo.get("PR.VERSCH.SUMME") is not None:
        raise NotSupportedError("PR.VERSCH.SUMME (profile-shift sum input) is not supported")

    a = _pair_key(geo, "ACHSABSTAND")
    x = _values(geo, "PROFILVERSCHIEBUNG_N")
    x_in_file = x
    if a is not None and x[0] is not None and x[1] is not None:
        # STplus keeps x_1 and derives x_2 from the centre distance without saying so; gearcore
        # admits only two of a_w, x_1, x_2 (ADR-107), so the translation is made explicit here
        notes.append(
            f"ACHSABSTAND and PROFILVERSCHIEBUNG_N of both gears given: x_2 = {x[1]:g} of the "
            "file is not passed on (STplus derives x_2 from the centre distance; gearcore admits "
            "only two of a_w, x_1, x_2)"
        )
        x = (x[0], None)
    span_w = _values(geo, "ZAHNWEITE")
    span_k = _values(geo, "MESSZAEHNEZAHL")
    span_k_check = _values(geo, "MESSZAEHNEZAHL_K")
    width = _values(geo, "ZAHNBREITE")
    tip = _values(geo, "KOPFKREISDM")
    chamfer = _values(geo, "KOPFKANTENBRUCH")
    a_we = _values(geo, "OBERES_ZAHNW_ABMASS")
    a_wi = _values(geo, "UNTERES_ZAHNW_ABMASS")
    series_entry = geo.get("ABMASS_TOL_REIHE")
    din_q = _values(geo, "DIN_QUALITAET")
    iso_q = _values(geo, "ISO_QUALITAET")
    has_din = any(v is not None for v in din_q)
    has_iso = any(v is not None for v in iso_q)
    if has_din and has_iso:
        raise ParseError(
            "DIN_QUALITAET and ISO_QUALITAET both given: the tolerance system is ambiguous"
        )
    quality = iso_q if has_iso else din_q
    quality_system = QualitySystem.ISO1328 if has_iso else QualitySystem.DIN3962

    tools_entry = geo.get("WERKZEUG_VORVERZ.")
    tools: list[ToolProfile] = []
    if tools_entry is None or len(tools_entry.values) < 2:
        raise ParseError(
            "WERKZEUG_VORVERZ. must name a tool block for both gears (STplus would use a default "
            "hob; gearcore requires the tool explicitly)"
        )
    for entry_of_names in (tools_entry, series_entry):
        if entry_of_names is not None and len(entry_of_names.values) > 2:
            raise ParseError(
                f"line {entry_of_names.line}: {entry_of_names.key} has "
                f"{len(entry_of_names.values)} values; a pair has two gears"
            )
    for name in tools_entry.values[:2]:
        section = ste.section(name)
        if section is None:
            raise ParseError(f"tool block '$ {name}' referenced by WERKZEUG_VORVERZ. not found")
        tools.append(tool_from_section(section, notes))
    if geo.get("WERKZEUG_FERTIGVERZ.") is not None:
        raise NotSupportedError("WERKZEUG_FERTIGVERZ. (second tool) is an extension point")

    materials: list[MaterialRecord] = []
    refs: list[MaterialRef | None] = [None, None]
    load = ste.section("Tragfaehigkeit_Allgem")
    entry = None if load is None else load.get("WERKSTOFF")
    if entry is not None:
        if len(entry.values) > 2:
            raise ParseError(
                f"line {entry.line}: WERKSTOFF has {len(entry.values)} values; a pair has two gears"
            )
        for index, name in enumerate(entry.values):
            section = ste.section(name)
            kind = (material_kinds or {}).get(name)
            if section is None:
                notes.append(
                    f"material block '$ {name}' not in file (database material) — not imported"
                )
                continue
            if kind is None:
                notes.append(
                    f"material '{name}': kind (steel/plastic) not stated by caller — not imported"
                )
                continue
            materials.append(material_from_section(section, kind))
            refs[index] = MaterialRef(kind=kind, name=name)

    gears: list[GearInput] = []
    for i in range(2):
        gear_no = i + 1
        span = None
        w = span_w[i]
        if w is not None and x_in_file[i] is None:
            # STplus takes ZAHNWEITE with MESSZAEHNEZAHL in place of x (manual Bild 4.12). For
            # gearcore the span is an inspection dimension that is passed on as such (ADR-107).
            # MESSZAEHNEZAHL_K is the check-dimension tooth count and must NOT stand in for
            # MESSZAEHNEZAHL (gate ADV0-11)
            k = _integer(span_k[i], "MESSZAEHNEZAHL", gear_no)
            if k is None:
                raise ParseError(f"gear {gear_no}: ZAHNWEITE given without MESSZAEHNEZAHL")
            span = SpanMeasurement(span_measurement_mm=w, number_of_teeth_spanned=k)
        elif w is not None:
            notes.append(
                f"gear {gear_no}: ZAHNWEITE {w} is not used for x (PROFILVERSCHIEBUNG_N is in "
                "the file); it is an inspection dimension"
            )
        b = width[i]
        if b is None:
            raise ParseError(
                f"gear {gear_no}: ZAHNBREITE missing (a lone value belongs to gear 1 only)"
            )
        h_k = chamfer[i]
        if h_k is None:
            # the contract requires the value; a file without it has no tip chamfer
            h_k = 0.0
            notes.append(f"gear {gear_no}: KOPFKANTENBRUCH not given → 0 (no tip chamfer)")
        allowance = None
        if a_we[i] is not None or a_wi[i] is not None:
            upper, lower = a_we[i], a_wi[i]
            if upper is None or lower is None:
                raise ParseError(
                    f"gear {gear_no}: OBERES_ and UNTERES_ZAHNW_ABMASS must be given together"
                )
            allowance = (upper, lower)
        q = _integer(quality[i], "QUALITAET", gear_no)
        gears.append(
            GearInput(
                kind=GearKind.EXTERNAL,
                number_of_teeth=teeth[i],
                profile_shift_coefficient=x[i],
                span=span,
                face_width_mm=b,
                tip_diameter_mm=tip[i],
                tip_chamfer_radial_mm=h_k,
                tool=tools[i],
                material=refs[i],
                number_of_teeth_spanned=_integer(span_k_check[i], "MESSZAEHNEZAHL_K", gear_no),
                span_allowance_um=allowance,
                allowance_series=(
                    None
                    if series_entry is None or i >= len(series_entry.values)
                    else series_entry.values[i]
                ),
                quality_grade=q,
                quality_system=None if q is None else quality_system,
            )
        )

    config = ste.section("Konfigurationsdaten")
    c_min = None if config is None else _values(config, "MINDESTKOPFSPIEL")[0]

    determined = [g.profile_shift_coefficient is not None or g.span is not None for g in gears]
    if a is not None and not any(determined):
        raise NotSupportedError(
            "ACHSABSTAND without PROFILVERSCHIEBUNG_N and without ZAHNWEITE: the distribution of "
            "the sum of the profile shift coefficients (AUFTEILUNG_X1X2) is an extension point"
        )
    if a is None and not all(determined):
        raise ParseError(
            "without ACHSABSTAND both gears need PROFILVERSCHIEBUNG_N (a gear with ZAHNWEITE "
            "and MESSZAEHNEZAHL instead is imported, but its nominal x stays open)"
        )
    pair = PairInput(
        normal_module_mm=module,
        normal_pressure_angle_deg=alpha,
        helix_angle_deg=beta,
        centre_distance_mm=a,
        gears=Pair(pinion=gears[0], wheel=gears[1]),
        min_tip_clearance_factor=c_min,
    )
    unmapped = sorted(k for k in {e.key for e in geo.entries} if k not in GEOMETRY_KEYS_MAPPED)
    return SteImport(
        pair=pair, materials=tuple(materials), unmapped_keys=tuple(unmapped), notes=tuple(notes)
    )


def known_keys_from_sty(path: Path) -> set[str]:
    """Key register from STplus ``bin/DEFAULT.STY`` (INI-style ``[KEY]`` headers), upper-cased."""
    keys: set[str] = set()
    for raw in path.read_text(encoding="latin-1").splitlines():
        line = raw.strip()
        if line.startswith("[") and line.endswith("]"):
            keys.add(_normalise_key(line[1:-1]))
    return keys
