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

from gearcore._safe import finite_input, positive_input
from gearcore.errors import InputRangeError, NotSupportedError, ParseError
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
    "PR.VERSCH.SUMME",
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


TIP_CIRCLE_KEYS: tuple[str, ...] = (
    "BEZ_KOPFDICKE",
    "DA_DURCH_WKZ",
    "DA_NACH_DIN3960",
    "KOPFSPIELFAKTOR",
    "K_HOEHENF_VERZ_BEZ_PR",
)
"""Keys that define the tip circle of a gear in place of ``KOPFKREISDM`` (manual Bild 4.6, p. 18,
and Bild 4.12, p. 25: "entweder d_a oder s_na/m_n oder d_a durch Wkz oder d_a nach DIN 3960 oder
c* oder h_ap*"). The importer does not translate them: a file that sets one for a gear without
``KOPFKREISDM`` is not imported (probes ``tip_circle_from_reference_profile_addendum``,
``tip_circle_per_din3960``)."""

CONFIGURATION_KEYS_EVALUATED: tuple[str, ...] = (
    "MINDESTKOPFSPIEL",
    "MAX_KOPFKANTENBRUCH",
    "TANG_BETRAG_ZU_H_KGF",
    "ABSCHALTEN_KORRGLIED",
    "VB_FUSSFORMHOEHE_HFF0*",
    "VB_FUSSHOEHE_HF0*",
    "MIN_WKZ_ZAHNKOPFDICKE*",
    "MIN_LUECKENWEITE_EFF0*",
    "MIN_LUECKENWEITE_EF0*",
)
"""Keys of ``$ KONFIGURATIONSDATEN`` the importer reads; every other key of the block is named
in a note."""


class SteImport(FrozenModel):
    """Result of the typed extraction: the contracts plus everything that was not mapped."""

    pair: PairInput
    materials: tuple[MaterialRecord, ...] = ()
    unmapped_keys: tuple[str, ...] = ()
    """Keys present in the geometry block that the typed layer ignores (kept visible, never silent)."""
    notes: tuple[str, ...] = ()
    preset_tip_diameters: tuple[bool, bool] = (False, False)
    """True for a gear whose file gives no ``KOPFKREISDM``: its tip diameter is the default of
    STplus, d + 2 m_n (1 + x), which STplus may shorten afterwards (tip tooth thickness,
    interference, tool); of these gearcore models the cut by the tool only (GEN-16)."""


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


TOOL_ABSOLUTE_KEYS: dict[str, str] = {
    "KOPFHOEHE": "KOPFHOEHENFAKTOR",
    "KOPFABRUNDUNGSRADIUS": "KOPFABRUNDUNGSFAKTOR",
    "FUSSFORMHOEHE": "FUSSFORMHOEHENFAKTOR",
    "FUSSHOEHE": "FUSSHOEHENFAKTOR",
}
"""Absolute tool dimension in mm -> its module factor (manual Bild 4.174, p. 185)."""

TOOL_KEYS_NOT_SUPPORTED: tuple[str, ...] = (
    "ABST_WKZ_KOPFLINIE/D_W0",
    "PROTUBERANZBETRAG_FAKTOR",
    "PROT_HOEHENFAKTOR",
    "PROTUBERANZHOEHE",
    "ABST_PBML_FAKTOR",
    "ABST_PROFILBEZUGSL/MESSL",
    "MASS_BZ0_FAKTOR",
    "MASS_BZ0",
    "ZAHNDICKE_S_0_FAKTOR",
    "ZAHNDICKE_S_0",
    "BEARB_ZUGABE_WKZ_FAKTOR",
    "WKZ_NDPITCH",
    "SCHLEIFSCHEIBENDM_MIN",
)
"""Keys of a rack tool block (manual Bild 4.176, p. 188, and Bild 4.183, p. 195) that change the
tool and that the importer does not translate: a block that carries one is not imported."""


STRUCTURAL_BLOCKS: tuple[str, ...] = (
    "ANFANG",
    "ENDE",
    "GEOMETRIEDATEN",
    "KONFIGURATIONSDATEN",
    "PLOTSTEUERUNG",
)
"""Blocks of a ``.ste`` file that are no tool: a tool name that points to one is an input error."""


def _given(section: SteSection, key: str) -> bool:
    """A key is given where it carries a value other than the placeholder ``%`` (manual §3.2:
    the placeholder stands for "not given"; the templates of the manual list every key with it)."""
    entry = section.get(key)
    return entry is not None and any(value != PLACEHOLDER for value in entry.values)


def tool_from_section(
    section: SteSection | None,
    notes: list[str],
    *,
    name: str | None = None,
    normal_module_mm: float | None = None,
    normal_pressure_angle_deg: float | None = None,
    limit_controls: dict[str, float] | None = None,
) -> ToolProfile:
    """Build a ``ToolProfile`` from a ``$ WKZ_...`` block as STplus 11.1F computes with it.

    STplus completes an incomplete block and corrects a contradicting one; the importer does the
    same and appends every such step to ``notes`` (user decision 2026-10-03, ADR-114; the rules
    are ``stplus_program.stplus_tool_factors``): missing addendum, tip rounding, root form
    height and dedendum get the presets of the program, the factor wins over a contradicting
    absolute value, a tip rounding beyond the full radius and heights beyond their limits are
    reduced, a dedendum below the root form height is set equal to it, and the flank between
    root form height and dedendum gets the edge break angle alpha_n0 + 10 degrees where none is
    given. ``section`` = ``None`` is the hob STplus uses where no tool is named.

    A block without ``PROTUBERANZBETRAG`` or ``BEARB_ZUGABE_WKZ`` yields the value zero with a
    note. ``normal_module_mm`` and ``normal_pressure_angle_deg`` are those of the gear; they are
    used where the block gives none (absolute values, limits). Shaper and profile tools and keys
    the importer does not translate are ``NotSupportedError``. The list is required: a default
    is never applied without a record of it (ADR-109). ``limit_controls`` carries the controls
    of the tool limits a file sets (keyword arguments ``min_..._factor`` of
    ``stplus_tool_factors``).
    """
    from gearcore.stplus_program import stplus_tool_factors

    if section is not None and not isinstance(section, SteSection):
        raise InputRangeError(
            f"a section of a parsed .ste file is required, got {type(section).__name__}"
        )
    if not isinstance(notes, list):
        raise InputRangeError(
            f"notes must be a list that takes the records of the defaults, got {type(notes).__name__}"
        )
    label = name if section is None else section.name
    fields: dict[str, Any] = {"kind": ToolKind.RACK, "name": label}
    given: dict[str, float] = {}
    if section is None:
        notes.append(
            f"tool {label!r}: no tool block named → the hob STplus uses where none is given"
        )
    else:
        keys = {entry.key for entry in section.entries if _given(section, entry.key)}
        if any(k.startswith(SHAPER_PREFIX) for k in keys):
            raise NotSupportedError(
                f"tool {label!r}: shaper cutter (SR_*) tools are an extension point"
            )
        if any(k.startswith(PROFILE_PREFIX) for k in keys):
            raise NotSupportedError(
                f"tool {label!r}: profile/form (PW_*) tools are an extension point"
            )
        unsupported = sorted(k for k in keys if k in TOOL_KEYS_NOT_SUPPORTED)
        if unsupported:
            raise NotSupportedError(
                f"tool {label!r}: {', '.join(unsupported)} is not translated (tools dimensioned "
                "from a measuring line, protuberance heights and a machining allowance given "
                "as a factor are extension points)"
            )
        if section.entries and not keys & {*TOOL_KEYS, *TOOL_ABSOLUTE_KEYS}:
            raise ParseError(
                f"block '$ {label}' is no tool block: it carries none of the keys of a rack tool"
            )
        for key in (*TOOL_KEYS, *TOOL_ABSOLUTE_KEYS):
            entry = section.get(key)
            if entry is None or key not in keys:
                continue  # not given, or given as the placeholder
            numbers = entry.numbers()
            if numbers[0] is None:
                continue  # the first position holds the value; the placeholder is "not given"
            given[key] = numbers[0]
            extra = sum(number is not None for number in numbers[1:])
            if extra:
                notes.append(
                    f"tool {label!r}: {key} has {extra + 1} values; the first is used (a tool "
                    "block describes one tool)"
                )
        unread = sorted(keys - {*TOOL_KEYS, *TOOL_ABSOLUTE_KEYS})
        if unread:
            notes.append(f"tool {label!r}: keys not read by the importer: {', '.join(unread)}")
    for key, field in TOOL_KEYS.items():
        if key in given and key not in TOOL_ABSOLUTE_KEYS.values():
            fields[field] = given[key]
    if normal_module_mm is not None:
        positive_input(normal_module_mm, "normal module of the gear")
    if normal_pressure_angle_deg is not None:
        finite_input(normal_pressure_angle_deg, "normal pressure angle of the gear")
    module = given.get("WKZ_NORMALMODUL", normal_module_mm)
    alpha = given.get("WKZ_EINGRIFFSWINKEL", normal_pressure_angle_deg)
    if module is not None and module <= 0.0:
        raise ParseError(f"tool {label!r}: WKZ_NORMALMODUL = {module:g} is no module")
    if alpha is not None and not 0.0 < alpha < 90.0:
        # (a flank without inclination is the grinding wheel of the manual's example 1, p. 256)
        raise ParseError(
            f"tool {label!r}: a profile angle of {alpha:g} deg is no rack tool the importer "
            "translates (0 < alpha < 90)"
        )
    factors: dict[str, float | None] = {}
    for absolute_key, factor_key in TOOL_ABSOLUTE_KEYS.items():
        factor = given.get(factor_key)
        if absolute_key in given:
            if module is None:
                raise ParseError(
                    f"tool {label!r}: {absolute_key} in mm needs the module of the tool or of "
                    "the gear"
                )
            from_absolute = given[absolute_key] / module
            if factor is None:
                factor = from_absolute
                notes.append(
                    f"tool {label!r}: {absolute_key} = {given[absolute_key]!r} mm → {factor_key} = "
                    f"{factor!r} with the module {module!r}"
                )
            elif abs(factor - from_absolute) * module > 1.0e-3:
                notes.append(
                    f"tool {label!r}: {absolute_key} = {given[absolute_key]!r} mm contradicts "
                    f"{factor_key} = {factor!r} ({factor * module!r} mm); STplus computes with "
                    "the factor"
                )
        factors[factor_key] = factor
    fields.update(
        stplus_tool_factors(
            str(label),
            addendum=factors["KOPFHOEHENFAKTOR"],
            tip_radius=factors["KOPFABRUNDUNGSFAKTOR"],
            root_form_height=factors["FUSSFORMHOEHENFAKTOR"],
            dedendum=factors["FUSSHOEHENFAKTOR"],
            edge_break_angle_deg=given.get("KANTENBRECHWINKEL"),
            alpha_n_deg=alpha,
            notes=notes,
            **(limit_controls or {}),
        )
    )
    for key, meaning in ABSENT_MEANS_NONE.items():
        if TOOL_KEYS[key] not in fields:
            fields[TOOL_KEYS[key]] = 0.0
            notes.append(f"tool {label!r}: {key} not given → 0 ({meaning})")
    try:
        return ToolProfile(**fields)
    except ValidationError as error:
        raise _not_valid(error, f"tool {label!r}") from error


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
    if module <= 0.0:
        raise ParseError(f"NORMALMODUL = {module:g} is no module")
    if not 0.0 < alpha < 90.0:
        raise ParseError(f"EINGRIFFSWINKEL = {alpha:g} is no pressure angle (0 < alpha < 90)")
    beta = _pair_key(geo, "SCHRAEGUNGSWINKEL")

    split = _values(geo, "AUFTEILUNG_X1X2")[0]
    if split not in (None, 0.0):
        raise NotSupportedError(
            f"AUFTEILUNG_X1X2 = {split:g} (manual Bild 4.12: DIN 3992 / equal sliding / equal root "
            "stress / ... distribution of the profile-shift sum) is not supported; only 0 = x1 given"
        )

    a = _pair_key(geo, "ACHSABSTAND")
    x = _values(geo, "PROFILVERSCHIEBUNG_N")
    total = _pair_key(geo, "PR.VERSCH.SUMME")
    from_sum: int | None = None
    if total is not None:
        # manual Bild 4.12: the sum of the profile shift coefficients with the coefficient of one
        # gear gives the other (probe profile_shift_sum)
        if (x[0] is None) == (x[1] is None):
            raise NotSupportedError(
                "PR.VERSCH.SUMME needs PROFILVERSCHIEBUNG_N of exactly one gear; the distribution "
                "of the sum (AUFTEILUNG_X1X2) is an extension point"
            )
        if a is not None and beta is not None:
            # centre distance and helix angle fix the sum: STplus keeps x_1 and derives x_2 from
            # the centre distance, whatever the sum says (probe
            # profile_shift_sum_with_centre_distance: sum 0,6, x_1 0,4, a 61 -> x_2 0,1298)
            if x[0] is None:
                raise NotSupportedError(
                    "PR.VERSCH.SUMME with ACHSABSTAND, SCHRAEGUNGSWINKEL and the profile shift "
                    "coefficient of gear 2 only is not probed"
                )
            notes.append(
                f"PR.VERSCH.SUMME = {total:g} is not used: with ACHSABSTAND and SCHRAEGUNGSWINKEL "
                "given STplus derives x_2 from the centre distance"
            )
        else:
            from_sum = 2 if x[1] is None else 1
            known = x[0] if from_sum == 2 else x[1]
            assert known is not None
            x = (known, total - known) if from_sum == 2 else (total - known, known)
            notes.append(
                f"PR.VERSCH.SUMME = {total:g}: PROFILVERSCHIEBUNG_N of gear {from_sum} follows as "
                f"{x[from_sum - 1]!r} (sum minus the coefficient given)"
            )
    if beta is None:
        # STplus computes the helix angle from the centre distance and the sum of the profile
        # shift coefficients (manual p. 16, subroutine GE12; probe
        # helix_angle_from_centre_distance); without them it rejects the input (probe
        # no_helix_angle_no_centre_distance)
        if a is None or x[0] is None or x[1] is None:
            raise ParseError(
                "SCHRAEGUNGSWINKEL missing: STplus computes it from ACHSABSTAND and the sum of the "
                "profile shift coefficients and rejects an input that lacks them"
            )
        from gearcore.stplus_program import stplus_helix_angle_deg

        beta = stplus_helix_angle_deg(a, module, alpha, teeth[0], teeth[1], x[0] + x[1])
        notes.append(
            f"SCHRAEGUNGSWINKEL not given → beta = {beta!r} deg from ACHSABSTAND = {a:g} and the "
            f"sum of the profile shift coefficients {x[0] + x[1]!r}, the solution of the equation "
            "STplus iterates (STplus ends its iteration when the centre distance is met within "
            "about 0,5 um, lists a slightly smaller angle and adds the remainder to x_2)"
        )
    x_in_file = x
    if a is not None and x[0] is not None and x[1] is not None:
        # STplus keeps x_1 and derives x_2 from the centre distance without saying so; gearcore
        # admits only two of a_w, x_1, x_2 (ADR-107), so the translation is made explicit here
        if from_sum is None:
            notes.append(
                f"ACHSABSTAND and PROFILVERSCHIEBUNG_N of both gears given: x_2 = {x[1]:g} of the "
                "file is not passed on (STplus derives x_2 from the centre distance; gearcore "
                "admits only two of a_w, x_1, x_2)"
            )
        elif from_sum == 2:
            notes.append(
                f"ACHSABSTAND given: x_2 = {x[1]!r} of PR.VERSCH.SUMME is not passed on (it "
                "follows from the centre distance; gearcore admits only two of a_w, x_1, x_2)"
            )
        else:
            raise NotSupportedError(
                "PR.VERSCH.SUMME with ACHSABSTAND and the profile shift coefficient of gear 2 "
                "only (no SCHRAEGUNGSWINKEL) is not probed"
            )
        x = (x[0], None)
    span_w = _values(geo, "ZAHNWEITE")
    span_k = _values(geo, "MESSZAEHNEZAHL")
    span_k_check = _values(geo, "MESSZAEHNEZAHL_K")
    width = _values(geo, "ZAHNBREITE")
    tip = _values(geo, "KOPFKREISDM")
    active = sorted(
        key
        for key in TIP_CIRCLE_KEYS
        if (entry_of_key := geo.get(key)) is not None
        and any(v != PLACEHOLDER and v.lower() != "nein" for v in entry_of_key.values)
    )
    if active and (tip[0] is None or tip[1] is None):
        raise NotSupportedError(
            f"{', '.join(active)} defines the tip circle of a gear without KOPFKREISDM "
            "(tip tooth thickness, tip circle by the tool, tip alteration per DIN 3960, tip "
            "clearance factor, addendum factor of the reference profile): extension points; "
            "give KOPFKREISDM"
        )
    if active:
        # probe tip_circle_given_with_other_definitions: the listing equals that of the file
        # without these keys (tip circles, tool factors, tip clearance)
        notes.append(
            f"{', '.join(active)}: no effect in STplus where KOPFKREISDM is given for both gears"
        )
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

    config = ste.section("Konfigurationsdaten")
    limit_controls = {
        argument: value
        for argument, (key, bounds) in TOOL_LIMIT_CONTROLS.items()
        if (value := _control(config, key, bounds, notes)) is not None
    }
    tools_entry = geo.get("WERKZEUG_VORVERZ.")
    tools: list[ToolProfile] = []
    for entry_of_names in (tools_entry, series_entry):
        if entry_of_names is not None and len(entry_of_names.values) > 2:
            raise ParseError(
                f"line {entry_of_names.line}: {entry_of_names.key} has "
                f"{len(entry_of_names.values)} values; a pair has two gears"
            )
    tool_names = [] if tools_entry is None else list(tools_entry.values[:2])
    for index in range(2):
        # a gear without a tool name (no entry, one name only, or the placeholder %) is cut by
        # the hob STplus presets (manual p. 22; probes defaults_minimal, tool_for_one_gear_only)
        name = tool_names[index] if index < len(tool_names) else PLACEHOLDER
        section = None
        if name != PLACEHOLDER:
            if name.upper() in STRUCTURAL_BLOCKS:
                raise ParseError(
                    f"WERKZEUG_VORVERZ. names '{name}', which is a block of the file structure "
                    "and no tool"
                )
            section = ste.section(name)
            if section is None:
                raise ParseError(f"tool block '$ {name}' referenced by WERKZEUG_VORVERZ. not found")
        tools.append(
            tool_from_section(
                section,
                notes,
                name=f"STplus default hob of gear {index + 1}",
                normal_module_mm=module,
                normal_pressure_angle_deg=alpha,
                limit_controls=limit_controls,
            )
        )
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
                f"gear {gear_no}: ZAHNWEITE {w} is not used for x (the file gives x by "
                "PROFILVERSCHIEBUNG_N or PR.VERSCH.SUMME); it is an inspection dimension"
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
            if upper is None:
                raise ParseError(
                    f"gear {gear_no}: UNTERES_ZAHNW_ABMASS given without OBERES_ZAHNW_ABMASS"
                )
            if lower is None:
                # manual p. 20; probe upper_span_allowance_only
                lower = upper
                notes.append(
                    f"gear {gear_no}: UNTERES_ZAHNW_ABMASS not given → equal to the upper span "
                    f"allowance {upper:g} as STplus sets it"
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

    c_min = _control(config, "MINDESTKOPFSPIEL", MIN_TIP_CLEARANCE_RANGE, notes)

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
    preset_tips = (gears[0].tip_diameter_mm is None, gears[1].tip_diameter_mm is None)
    pair = _completed_like_stplus(pair, config, notes)
    unmapped = sorted(k for k in {e.key for e in geo.entries} if k not in GEOMETRY_KEYS_MAPPED)
    return SteImport(
        pair=pair,
        materials=tuple(materials),
        unmapped_keys=tuple(unmapped),
        notes=tuple(notes),
        preset_tip_diameters=preset_tips,
    )


TOOL_LIMIT_CONTROLS: dict[str, tuple[str, tuple[float, float]]] = {
    "min_tip_land_factor": ("MIN_WKZ_ZAHNKOPFDICKE*", (0.1, 1.0)),
    "min_space_factor": ("MIN_LUECKENWEITE_EFF0*", (0.1, 0.6)),
    "min_root_space_factor": ("MIN_LUECKENWEITE_EF0*", (0.1, 0.6)),
}
"""Controls of ``$ KONFIGURATIONSDATEN`` (manual §4.17.2) that move the limits of the tool:
argument of ``stplus_program.stplus_tool_factors`` -> key and the values STplus accepts (the
ranges of ``stplus_program.MIN_TOOL_*_RANGE``; probes ``tool_tip_land_control``,
``tool_space_control``, ``tool_root_space_control``)."""


MIN_TIP_CLEARANCE_RANGE = (0.001, 0.99)
"""Range of the control MINDESTKOPFSPIEL (manual Bild 4.231, p. 229: ``# 0.13 0.001... 0.99``)."""


def _control(
    config: SteSection | None, key: str, bounds: tuple[float, float], notes: list[str]
) -> float | None:
    """The value of a control of ``$ KONFIGURATIONSDATEN``, ``None`` where the preset holds.

    The controls the importer reads are printed as ``KEY = % (%)`` in the manual (Bild 4.231,
    p. 229): one value for the stage, the second column being a third gear. The first value
    holds for both gears, whatever a second one says (probes
    ``tip_chamfer_tangential_two_values``, ``tip_chamfer_limit_lowered``,
    ``controls_first_value_holds``). STplus accepts the values between the ends of the range,
    not the ends themselves; any other value leaves the preset in place (manual p. 223; probes
    ``control_outside_its_range``, ``controls_at_the_ends_of_their_ranges``).
    The placeholder ``%`` is "not given". The use of a control, a value that is not accepted
    and a value that is not used are recorded."""
    entry = None if config is None else config.get(key)
    if entry is None:
        return None
    numbers = entry.numbers()  # (every token is a number or the placeholder, else ParseError)
    value = numbers[0] if numbers else None
    if value is None:
        return None
    if len(entry.values) > 1:
        notes.append(
            f"$ KONFIGURATIONSDATEN: {key} has {len(entry.values)} values; the first holds for "
            "both gears, as in STplus (a second one belongs to a third gear)"
        )
    if not bounds[0] < value < bounds[1]:
        notes.append(
            f"$ KONFIGURATIONSDATEN: {key} = {value:g} does not lie between {bounds[0]:g} and "
            f"{bounds[1]:g}: STplus does not accept it and keeps the preset"
        )
        return None
    notes.append(f"$ KONFIGURATIONSDATEN: {key} = {value:g} is used in place of the preset")
    return value


def _completed_like_stplus(
    pair: PairInput, config: SteSection | None, notes: list[str]
) -> PairInput:
    """Tip diameters, chamfer heights and residual tip thicknesses as STplus presets them
    (user decision 2026-10-03, ADR-114; every step is appended to ``notes``).

    - A tip chamfer given as an input is limited to 0,20 m_n (control MAX_KOPFKANTENBRUCH).
    - A gear without ``KOPFKREISDM`` gets d_a = d + 2 m_n (h_aP* + x) with h_aP* = 1 and no tip
      alteration (manual p. 19), where its profile shift coefficient follows from the file.
    - A chamfer given by h_K gets the residual tip thickness of the STplus rule: the tangential
      amount 0,7 h_K (control TANG_BETRAG_ZU_H_KGF), at least 0,2 s_an, in the normal section.
      It needs the tip tooth thickness of the generated gear; where the generation is not
      available, the residual thickness stays open and a note says why.

    The tooth thickness allowances of the DIN 3967 series STplus presets (c25) come with
    increment 5; until then the tip tooth thickness is that of the gear without allowance.
    """
    from gearcore import generation as gn
    from gearcore import pair as pr
    from gearcore.errors import GearCoreError
    from gearcore.stplus_program import (
        MAX_TIP_CHAMFER_RANGE,
        TANGENTIAL_AMOUNT_RANGE,
        stplus_default,
        stplus_residual_tip_thickness,
        stplus_tip_chamfer_height,
        stplus_transverse_residual_tip_thickness,
    )

    if config is not None:
        presets = sorted(k for k in {e.key for e in config.entries} if k.startswith("VB_FUSS"))
        if presets:
            notes.append(
                f"$ KONFIGURATIONSDATEN: {', '.join(presets)} has no effect in STplus 11.1F (probe "
                "tool_root_presets_of_the_configuration): the tool root keeps the presets 1,3 / 1,3"
            )
        flag = config.get("ABSCHALTEN_KORRGLIED")
        switches = () if flag is None else flag.numbers()
        circle = switches[0] if switches else None
        if len(switches) > 1:
            notes.append(
                f"$ KONFIGURATIONSDATEN: ABSCHALTEN_KORRGLIED has {len(switches)} values; the "
                "first holds for both gears, as in STplus (a second one belongs to a third gear)"
            )
        if circle not in (None, 0.0):
            # manual p. 227/228: STplus then takes the tool tip rounding as a circle in the
            # transverse section; gearcore rolls the ellipse (ADR-113)
            raise NotSupportedError(
                f"$ KONFIGURATIONSDATEN: ABSCHALTEN_KORRGLIED = {circle:g} (circular in place of "
                "the elliptic tool tip rounding in the transverse section) is not supported"
            )
        ignored = sorted(
            k for k in {e.key for e in config.entries} if k not in CONFIGURATION_KEYS_EVALUATED
        )
        if ignored:
            notes.append(
                f"$ KONFIGURATIONSDATEN: {', '.join(ignored)} not evaluated by the importer"
            )
    limit = _control(config, "MAX_KOPFKANTENBRUCH", MAX_TIP_CHAMFER_RANGE, notes)
    tangential = _control(config, "TANG_BETRAG_ZU_H_KGF", TANGENTIAL_AMOUNT_RANGE, notes)
    m_n = pair.normal_module_mm
    gears = list(pair.gears.as_tuple())
    for index, gear in enumerate(gears):
        h_K = gear.tip_chamfer_radial_mm
        limited = stplus_tip_chamfer_height(h_K, m_n, max_factor=limit)
        if limited < h_K:
            notes.append(
                f"gear {index + 1}: KOPFKANTENBRUCH = {h_K:g} limited to {limited!r} mm as STplus "
                f"does ({limited / m_n:g} m_n)"
            )
            gears[index] = gear.model_copy(update={"tip_chamfer_radial_mm": limited})
    pair = pair.model_copy(update={"gears": Pair(pinion=gears[0], wheel=gears[1])})

    shifts = [gear.profile_shift_coefficient for gear in gears]
    follows = (
        all(x is not None for x in shifts)
        if pair.centre_distance_mm is None
        else any(x is not None for x in shifts)
    )
    without_tip = [i for i, gear in enumerate(gears) if gear.tip_diameter_mm is None]
    if without_tip and follows:
        h_aP_factor = stplus_default("reference_profile_addendum").value
        assert isinstance(h_aP_factor, float)
        pair = pr.with_nominal_tip_diameters(pair, h_aP_mm=h_aP_factor * m_n)
        gears = list(pair.gears.as_tuple())
        for index in without_tip:
            notes.append(
                f"gear {index + 1}: KOPFKREISDM not given → d_a = {gears[index].tip_diameter_mm!r} mm "
                "= d + 2 m_n (1 + x), the default of STplus without tip alteration (STplus "
                "shortens it afterwards where the tool, the tip tooth thickness or the mating "
                "gear require it; gearcore applies the cut by the tool only)"
            )
    elif without_tip:
        for index in without_tip:
            notes.append(
                f"gear {index + 1}: KOPFKREISDM not given; the default of STplus needs the profile "
                "shift coefficient, which a span measurement determines (increments 4 and 5)"
            )

    open_chamfers = [
        i
        for i, gear in enumerate(gears)
        if gear.tip_chamfer_radial_mm > 0.0 and gear.residual_tip_thickness_mm is None
    ]
    if not open_chamfers:
        return pair
    if not follows or any(gear.tip_diameter_mm is None for gear in gears):
        for index in open_chamfers:
            notes.append(
                f"gear {index + 1}: residual tip thickness of the chamfer not determined (the tip "
                "tooth thickness needs the profile shift coefficient and the tip diameter)"
            )
        return pair
    try:
        generated = gn.compute_generation(pair).gears.as_tuple()
    except GearCoreError as error:
        # reading a file is not mathematics: a pair gearcore cannot generate is still imported
        for index in open_chamfers:
            notes.append(
                f"gear {index + 1}: residual tip thickness of the chamfer not determined, the "
                f"generation is not available ({type(error).__name__}: {error})"
            )
        return pair
    for index in open_chamfers:
        gear, result = gears[index], generated[index]
        s_an = result.normal_tip_tooth_thickness_mm
        residual = stplus_residual_tip_thickness(
            s_an, gear.tip_chamfer_radial_mm, tangential_factor=tangential
        )
        # the contract carries the transverse arc on the tip circle, STplus the normal thickness
        transverse = stplus_transverse_residual_tip_thickness(
            result.transverse_tip_tooth_thickness_mm,
            s_an,
            gear.tip_chamfer_radial_mm,
            tangential_factor=tangential,
        )
        amount = (
            stplus_default("tip_chamfer_tangential").value if tangential is None else tangential
        )
        notes.append(
            f"gear {index + 1}: residual tip thickness of the chamfer → s_aK = {residual!r} mm in "
            f"the normal section ({transverse!r} mm transverse) by the STplus rule s_an - 2 "
            f"({amount:g} h_K), at least 0,2 s_an, with s_an = {s_an!r} mm of the gear without "
            "tooth thickness allowance (STplus presets the series c25, increment 5)"
        )
        gears[index] = gear.model_copy(update={"residual_tip_thickness_mm": transverse})
    return pair.model_copy(update={"gears": Pair(pinion=gears[0], wheel=gears[1])})


def known_keys_from_sty(path: Path) -> set[str]:
    """Key register from STplus ``bin/DEFAULT.STY`` (INI-style ``[KEY]`` headers), upper-cased."""
    keys: set[str] = set()
    for raw in path.read_text(encoding="latin-1").splitlines():
        line = raw.strip()
        if line.startswith("[") and line.endswith("]"):
            keys.add(_normalise_key(line[1:-1]))
    return keys
