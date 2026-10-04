"""What STplus itself ships and presets: tool databases and defaults, kept with their provenance.

User decision 2026-09-30 (ADR-109): nothing STplus offered may get lost. The tool databases of the
installation are packaged verbatim (``data/stplus_program/tool_database_*.txt``), the defaults of
the program are transcribed from the manual and from probe runs (``defaults.yaml``), and every
record says which program version it comes from (``provenance.yaml``).

None of this is a norm. gearcore applies no STplus default silently: a caller asks for a record
or a default by name and gets it labelled with program and version.

Tool records. A record keeps every entry of the database as written. Its ``profile`` is the
``ToolProfile`` STplus computes with (user decision 2026-10-03, ADR-114): the factor keys win
over contradicting absolute values (probe ``tool_contradicting_record``), missing factors get
the presets of the program, and heights beyond the limits of the program are reduced; ``notes``
record each step. A record has no profile where the completed tool lies beyond the bounds of the
contract, where the record names no profile angle (the limits of STplus need it:
``stplus_tool`` takes the pressure angle of the gear) and for a shaper or profile tool; ``issues``
say why. Absolute values that contradict the factors are reported as issues. ``WERKZEUGTYP`` is
kept as written; the manual does not explain the key.
"""

import json
import math
import sys
from functools import lru_cache
from types import MappingProxyType
from typing import Any, Literal

import yaml
from pydantic import Field, ValidationError
from scipy.optimize import brentq

from gearcore import inspection as ins
from gearcore import involute as iv
from gearcore import pair as pr
from gearcore._guards import HALF_PI, helix, pressure_angle, teeth
from gearcore._safe import EPS, finite_input, finite_result, integer_input, positive_input
from gearcore.data import data_path
from gearcore.errors import (
    GeometryInfeasibleError,
    InputRangeError,
    NotSupportedError,
    ParseError,
)
from gearcore.io.ste import SteSection, parse_ste, tool_from_section
from gearcore.models.common import HELIX_ANGLE_RANGE_DEG, FrozenModel, Pair
from gearcore.models.inputs import ToolProfile
from gearcore.models.results import GenerationResult

DIRECTORY = "stplus_program"
ABSOLUTE_VALUES: MappingProxyType[str, str] = MappingProxyType(
    {
        "KOPFHOEHE": "KOPFHOEHENFAKTOR",
        "FUSSHOEHE": "FUSSHOEHENFAKTOR",
        "FUSSFORMHOEHE": "FUSSFORMHOEHENFAKTOR",
        "KOPFABRUNDUNGSRADIUS": "KOPFABRUNDUNGSFAKTOR",
    }
)
"""Absolute tool dimension in mm -> its module factor (manual Bild 4.174, p. 185)."""

CONTRADICTION_MM = 1.0e-3
"""Absolute value and factor times module agree within the digits the database prints."""


class ProgramFile(FrozenModel):
    """One file of the installation that is packaged."""

    stored: str
    original: str
    role: str
    bytes: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    stored_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    line_endings: str
    encoding: str
    modified: str


class ProgramProvenance(FrozenModel):
    """Program, version and release the packaged STplus data comes from."""

    program: str
    version: str
    release: str
    publisher: str
    evidence: str
    installation: str
    manual: dict[str, str]
    imported: str
    note: str
    files: tuple[ProgramFile, ...]

    @property
    def label(self) -> str:
        """``'STplus 11.1F (Freigabe 01.12.2025)'``: the label every record carries."""
        return f"{self.program} {self.version} (Freigabe {self.release})"


class StplusToolRecord(FrozenModel):
    """A tool of an STplus tool database, as written, with its provenance."""

    name: str
    database: Literal["local", "global"]
    origin: str
    """Program, version, release and file the record comes from."""
    entries: tuple[tuple[str, str], ...]
    """Every ``KEY = value`` of the record in the order of the file."""
    profile: ToolProfile | None
    """The contract of the factor keys; ``None`` where ``issues`` say why there is none."""
    issues: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    """Zeros the contract states for keys the record does not carry (no protuberance, no
    machining allowance)."""


class ManualPassage(FrozenModel):
    page: int = Field(ge=1)
    text: str = Field(min_length=1)


class StplusDefault(FrozenModel):
    """A default of STplus with its evidence."""

    name: str
    origin: str
    quantity: str | None
    input_key: str | None
    value: float | str | None
    unit: str
    rule: str | None
    applies_to: Literal["user interface", "batch input", "both"]
    manual: ManualPassage | None
    probe: str | None
    status: Literal["verified", "located"]
    note: str | None
    tool: dict[str, float] | None = None
    file: str | None = None
    """Packaged file of the installation that is the evidence (``input_key_register.txt``)."""


def _load_yaml(name: str) -> dict[str, Any]:
    loaded: dict[str, Any] = yaml.safe_load(data_path(DIRECTORY, name).read_text(encoding="utf-8"))
    return loaded


@lru_cache(maxsize=1)
def program_provenance() -> ProgramProvenance:
    """Program version and files of the packaged STplus data."""
    return ProgramProvenance(**_load_yaml("provenance.yaml"))


def _number(section: SteSection, key: str) -> float | None:
    entry = section.get(key)
    return None if entry is None else entry.number(0)


def _contradictions(section: SteSection) -> list[str]:
    module = _number(section, "WKZ_NORMALMODUL")
    found: list[str] = []
    for absolute_key, factor_key in ABSOLUTE_VALUES.items():
        absolute, factor = _number(section, absolute_key), _number(section, factor_key)
        if absolute is None or factor is None or module is None:
            continue
        if abs(factor * module - absolute) > CONTRADICTION_MM:
            found.append(
                f"{absolute_key} = {absolute:g} mm contradicts {factor_key} = {factor:g} at "
                f"WKZ_NORMALMODUL = {module:g} ({factor * module:g} mm); STplus computes with the "
                "factor (probe tool_contradicting_record)"
            )
    return found


def _record(
    section: SteSection, database: Literal["local", "global"], origin: str
) -> StplusToolRecord:
    issues = _contradictions(section)
    profile: ToolProfile | None = None
    notes: list[str] = []
    try:
        profile = tool_from_section(section, notes)
    except (ParseError, NotSupportedError) as error:
        issues.append(f"no tool contract: {error}")
    except ValidationError as error:
        reasons = "; ".join(
            f"{'.'.join(str(part) for part in item['loc'])}: {item['msg']}"
            for item in error.errors()
        )
        issues.append(f"no tool contract: {reasons}")
    return StplusToolRecord(
        name=section.name,
        database=database,
        origin=origin,
        entries=tuple((entry.key, " ".join(entry.values)) for entry in section.entries),
        profile=profile,
        issues=tuple(issues),
        notes=tuple(notes) if profile is not None else (),
    )


@lru_cache(maxsize=1)
def _tool_sections() -> MappingProxyType[str, tuple[SteSection, Literal["local", "global"], str]]:
    """Every tool block of the packaged tool databases by name with its database and origin:
    local database first, then global (a name of the local database hides the global one)."""
    provenance = program_provenance()
    sections: dict[str, tuple[SteSection, Literal["local", "global"], str]] = {}
    for file in provenance.files:
        if not file.role.startswith("Werkzeugdatei"):
            continue
        database: Literal["local", "global"] = "local" if file.role.endswith("lokal") else "global"
        text = data_path(DIRECTORY, file.stored).read_text(encoding=file.encoding)
        for section in parse_ste(text, path=file.original).sections:
            if section.name.upper() in {"ANFANG", "ENDE"} or section.name in sections:
                continue
            sections[section.name] = (section, database, f"{provenance.label}, {file.original}")
    return MappingProxyType(sections)


@lru_cache(maxsize=1)
def tool_database() -> MappingProxyType[str, StplusToolRecord]:
    """Every record of the packaged tool databases by name: local database first, then global.

    STplus searches its tool files in this order (``Werkzeugdatei_lokal``, ``Werkzeugdatei_global``
    of ``stplus.cfg``); a name of the local database hides the same name of the global one.
    """
    return MappingProxyType(
        {
            name: _record(section, database, origin)
            for name, (section, database, origin) in _tool_sections().items()
        }
    )


def stplus_tool(
    name: str,
    *,
    normal_module_mm: float | None = None,
    normal_pressure_angle_deg: float | None = None,
    notes: list[str] | None = None,
) -> ToolProfile:
    """The tool contract of the database record ``name``, as STplus computes with it.

    Without further arguments it is the ``profile`` of the record. A record that names no module
    or no profile angle takes those of the gear (probe ``tool_without_tip_rounding``); with
    ``normal_module_mm`` and ``normal_pressure_angle_deg`` the record is completed for that gear,
    and ``notes`` (required then) receives every preset and correction applied.

    An unknown name is an ``InputRangeError``; a record that is no valid contract is a
    ``NotSupportedError`` that names the reasons.
    """
    sections = _tool_sections()
    if not isinstance(name, str) or name not in sections:
        raise InputRangeError(
            f"unknown tool {name!r} in the STplus tool databases; packaged: {sorted(sections)}"
        )
    if normal_module_mm is None and normal_pressure_angle_deg is None:
        if notes is not None:
            raise InputRangeError(
                "notes are taken with the module and the pressure angle of the gear; the notes of "
                "the record itself are tool_database()[name].notes"
            )
        record = tool_database()[name]
        if record.profile is None:
            raise NotSupportedError(f"tool {name!r} ({record.origin}): " + "; ".join(record.issues))
        return record.profile
    if not isinstance(notes, list):
        raise InputRangeError(
            "a tool completed with the data of a gear needs notes: a list that takes the record "
            "of every preset and correction of STplus"
        )
    section, _, origin = sections[name]
    try:
        return tool_from_section(
            section,
            notes,
            normal_module_mm=normal_module_mm,
            normal_pressure_angle_deg=normal_pressure_angle_deg,
        )
    except ParseError as error:
        raise NotSupportedError(f"tool {name!r} ({origin}): no tool contract: {error}") from error


@lru_cache(maxsize=1)
def stplus_defaults() -> MappingProxyType[str, StplusDefault]:
    """The defaults of STplus by name, each labelled with program and version."""
    origin = program_provenance().label
    loaded = _load_yaml("defaults.yaml")["defaults"]
    return MappingProxyType(
        {name: StplusDefault(name=name, origin=origin, **entry) for name, entry in loaded.items()}
    )


def stplus_default(name: str) -> StplusDefault:
    """The default ``name``; an unknown name is an ``InputRangeError``."""
    defaults = stplus_defaults()
    if not isinstance(name, str) or name not in defaults:
        raise InputRangeError(f"unknown STplus default {name!r}; known: {sorted(defaults)}")
    return defaults[name]


def stplus_default_tool() -> ToolProfile:
    """The hob STplus uses when no tool is given (probe ``defaults_minimal``), as a named tool.

    Module and profile angle are those of the gear (``None`` in the contract). The computing
    core never falls back on this tool; the ``.ste`` importer sets it for a gear without a tool
    and says so (ADR-114). The factors hold as they stand up to a pressure angle of 26,8 degrees:
    beyond it STplus reduces the tip rounding to the full radius, from 29,3 degrees also the root
    form height (probes ``default_hob_at_twenty_eight_degrees``, ``…_thirty_degrees``);
    ``stplus_tool_factors`` with the angle of the gear gives the tool STplus computes with.
    """
    default = stplus_default("default_rack_tool")
    if default.tool is None:
        raise ParseError("defaults.yaml: default_rack_tool carries no tool factors")
    return ToolProfile(name=f"{default.origin} default tool", **default.tool)


REGISTER_END = "# Ende der konfigurierbaren Eingabedaten"
"""Comment line of ``bin/DEFAULT.STY`` after which program-internal control data follows."""


def input_key_register() -> tuple[tuple[str, str], ...]:
    """Every entry ``(input key, register default)`` of the configurable input data of
    ``bin/DEFAULT.STY``, in the order of the file.

    The register is an INI-like list ``[KEY]`` / ``DEFAULT=value``; six keys appear twice. The
    program-internal control data after the line ``REGISTER_END`` ("NICHT VERAENDERN") is kept in
    the packaged file and not returned. Whether the program uses the entries as defaults of the
    computation is not documented.
    """
    text = data_path(DIRECTORY, "input_key_register.txt").read_text(encoding="latin-1")
    if REGISTER_END not in text:
        raise ParseError(
            "input key register: the end mark of the configurable input data is missing"
        )
    entries: list[tuple[str, str]] = []
    key: str | None = None
    for number, raw in enumerate(text.split(REGISTER_END, 1)[0].splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]") and key is None:
            key = line[1:-1]
        elif line.startswith("DEFAULT=") and key is not None:
            entries.append((key, line.removeprefix("DEFAULT=")))
            key = None
        else:
            raise ParseError(f"input key register line {number}: cannot read {line!r}")
    if key is not None:
        raise ParseError(f"input key register: key {key} has no DEFAULT entry")
    return tuple(entries)


# --- rules of the program ---------------------------------------------------------------------------
#
# What STplus 11.1F does with an incomplete or contradicting input, as functions with a name. None
# of it is a norm. Each rule is evidenced by the manual and by probe runs (``defaults.yaml``,
# ``probes/``); where the manual and the program disagree, the program is followed (user decision
# 2026-10-03, ADR-114). The `.ste` importer applies the rules and records each application in
# its notes; the contracts of the computing core stay explicit.


def _preset(name: str) -> float:
    """The number of the default ``name`` of ``defaults.yaml``."""
    value = stplus_default(name).value
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ParseError(f"defaults.yaml: {name} carries no number")
    return float(value)


def _tool_angle(alpha_n_rad: float) -> float:
    """The profile angle of a rack tool whose limits are asked for: in (0, 90 deg). A flank
    without inclination (the grinding wheel of the manual's example 1) has no such limit."""
    alpha = pressure_angle(alpha_n_rad, "normal pressure angle alpha_n")
    if alpha <= 0.0:
        raise InputRangeError(
            "the limits of a rack tool need a profile angle above zero, got "
            f"{math.degrees(alpha)!r} deg"
        )
    return alpha


MIN_TOOL_TIP_LAND_RANGE = (0.1, 1.0)
"""Range of the control MIN_WKZ_ZAHNKOPFDICKE* (manual p. 224), an open interval."""

MIN_TOOL_SPACE_RANGE = (0.1, 0.6)
"""Range of the control MIN_LUECKENWEITE_EFF0* (manual Bild 4.231), an open interval."""

MIN_TOOL_ROOT_SPACE_RANGE = (0.1, 0.6)
"""Values of the control MIN_LUECKENWEITE_EF0* that take effect in STplus 11.1F, an open
interval. The manual names 0,01 to 0,6; values up to 0,1 leave the preset in place (probe
``tool_root_space_control_without_effect``)."""


def stplus_max_tool_addendum_factor(
    alpha_n_rad: float, *, min_tip_land_factor: float | None = None
) -> float:
    """Largest addendum factor h_aP0* of a rack tool: the straight flanks may narrow the tip of
    the tool tooth to s_a0* m_n, h_aP0* = (pi / 2 - s_a0*) / (2 tan(alpha_n)).

    s_a0* is the control MIN_WKZ_ZAHNKOPFDICKE* (``min_tip_land_factor`` where the input sets
    it). The program presets it with 0,12; the manual says 0,2 (p. 224). Varying the control
    shows it: without it and with 0.12 STplus limits an addendum at 20 degrees to 1,993, with 0.2
    to 1,883 (probes ``tool_tip_land_control*``; "Werkzeugdaten h_aP0*, d_a0, rho_aP0 oder
    rho_at0 ... geaendert").
    """
    alpha = _tool_angle(alpha_n_rad)
    land = (
        _preset("tool_tip_land_limit")
        if min_tip_land_factor is None
        else _in_range(min_tip_land_factor, "MIN_WKZ_ZAHNKOPFDICKE*", MIN_TOOL_TIP_LAND_RANGE)
    )
    return finite_result(
        (math.pi / 2.0 - land) / (2.0 * math.tan(alpha)), "largest tool addendum factor"
    )


def stplus_max_tool_tip_radius_factor(h_aP0_factor: float, alpha_n_rad: float) -> float:
    """Largest tip rounding factor rho_aP0* of a rack tool: the full radius, at which the
    roundings of both flanks meet on the tip line,
    rho* = (pi / 4 - h_aP0* tan(alpha_n)) / (1 / cos(alpha_n) - tan(alpha_n)).

    STplus reduces a larger rounding to it and says "Werkzeugdaten h_aP0*, d_a0, rho_aP0 oder
    rho_at0 ... geaendert" (probes ``tool_tip_rounding_limited``, ``tool_contradicting_record``).
    """
    h = positive_input(h_aP0_factor, "tool addendum factor h_aP0*")
    alpha = _tool_angle(alpha_n_rad)
    land = math.pi / 4.0 - h * math.tan(alpha)
    if land < 0.0:
        raise GeometryInfeasibleError(
            f"tool addendum factor h_aP0* = {h!r}: the tool tooth is pointed below its tip line"
        )
    return land / (1.0 / math.cos(alpha) - math.tan(alpha))


def stplus_max_tool_root_form_height_factor(
    alpha_n_rad: float, *, min_space_factor: float | None = None
) -> float:
    """Largest root form height factor h_FfP0* of a rack tool: the straight flanks may narrow
    the tool space to e_Ff0* m_n, h_FfP0* = (pi / 2 - e_Ff0*) / (2 tan(alpha_n)).

    e_Ff0* is the control MIN_LUECKENWEITE_EFF0* (``min_space_factor`` where the input sets
    it). The program presets it with 0,11; the manual says 0,4 (p. 224). Without the control
    STplus limits a root form height at 15, 17,5, 20 and 25 degrees to 2,726, 2,317, 2,007 and
    1,566; with 0.4 given at 20 degrees to 1,608 (probe ``tool_space_control``).
    """
    alpha = _tool_angle(alpha_n_rad)
    width = (
        _preset("tool_space_width_at_root_form_height")
        if min_space_factor is None
        else _in_range(min_space_factor, "MIN_LUECKENWEITE_EFF0*", MIN_TOOL_SPACE_RANGE)
    )
    return finite_result(
        (math.pi / 2.0 - width) / (2.0 * math.tan(alpha)), "largest tool root form height factor"
    )


def stplus_max_tool_dedendum_factor(
    h_FfP0_factor: float,
    alpha_n_rad: float,
    alpha_K_rad: float,
    *,
    min_root_space_factor: float | None = None,
) -> float:
    """Largest dedendum factor h_fP0* of a rack tool whose edge break flanks (angle alpha_K)
    start at h_FfP0*: the flanks may narrow the tool space on the root line to
    2 e_f0* tan(alpha_n) m_n,
    h_f0max* = h_FfP0* + (pi / 2 - 2 (h_FfP0* + e_f0*) tan(alpha_n)) / (2 tan(alpha_K)).

    e_f0* is the control MIN_LUECKENWEITE_EF0* (``min_root_space_factor`` where the input sets
    it, effective between 0,1 and 0,6); without it the program computes with e_f0* = 0,03, a
    root space of 0,06 tan(alpha_n) m_n (the manual names 0,06 as the preset of the control,
    p. 224). STplus reduces a larger dedendum to the limit and says "Wkz.daten h_FfP0*, d_Ff0,
    alfa_Kn0 oder alfa_Kt0 ... geaendert". The formula is not printed in the manual; it agrees
    in five decimals with the runs in which the control was varied (0,15 to 0,59 at alpha_n 20
    and 25 degrees, alpha_K 30 and 45 degrees; probe ``tool_root_space_control``) and in the
    three printed decimals with the tools of the repository whose dedendum STplus limits.
    """
    h_Ff = finite_input(h_FfP0_factor, "tool root form height factor h_FfP0*")
    alpha = _tool_angle(alpha_n_rad)
    alpha_K = finite_input(alpha_K_rad, "edge break angle alpha_K")
    if not 0.0 < alpha_K < HALF_PI:
        raise InputRangeError(
            f"edge break angle must lie in (0, 90 deg), got {math.degrees(alpha_K)!r} deg (at 90 "
            "deg the tool has no edge break flank and its dedendum is the root form height)"
        )
    e_f0 = (
        _preset("min_tool_space_width_root")
        if min_root_space_factor is None
        else _in_range(min_root_space_factor, "MIN_LUECKENWEITE_EF0*", MIN_TOOL_ROOT_SPACE_RANGE)
    )
    width = math.pi / 2.0 - 2.0 * (h_Ff + e_f0) * math.tan(alpha)
    if width < 0.0:
        raise GeometryInfeasibleError(
            f"tool root form height factor h_FfP0* = {h_Ff!r}: the tool space is narrower than "
            f"{2.0 * e_f0 * math.tan(alpha)!r} m_n at that height already, there is no room for "
            "an edge break flank"
        )
    return finite_result(
        h_Ff + width / (2.0 * math.tan(alpha_K)), "largest tool dedendum factor h_f0max*"
    )


STPLUS_MAX_EDGE_BREAK_ANGLE_DEG = 85.0
"""Steepest edge break flank STplus 11.1F is known to compute (probe
``tool_edge_break_angle_eighty_five_degrees``); at 88 degrees it aborts ("Iteration IREG = 10
fuer Rad 1 nach 100 Schritten abgebrochen", probe ``tool_edge_break_angle_eighty_eight_degrees``)."""


def stplus_tool_factors(
    name: str,
    *,
    addendum: float | None,
    tip_radius: float | None,
    root_form_height: float | None,
    dedendum: float | None,
    edge_break_angle_deg: float | None,
    alpha_n_deg: float | None,
    notes: list[str],
    min_tip_land_factor: float | None = None,
    min_space_factor: float | None = None,
    min_root_space_factor: float | None = None,
) -> dict[str, float | None]:
    """The factors of a rack tool as STplus 11.1F completes them (``None`` = not given).

    1. h_aP0* missing: 1,25. Beyond ``stplus_max_tool_addendum_factor`` it is reduced.
       rho_aP0* missing: 0,25. A rounding beyond the full radius is reduced to it.
    2. h_FfP0* missing: 1,3. Beyond ``stplus_max_tool_root_form_height_factor`` it is reduced and
       the dedendum follows it.
    3. h_fP0* missing: 1,3. A dedendum below the root form height is set equal to it: the tool
       then has no edge break flank (so a lone FUSSHOEHENFAKTOR = 1,0 has no effect, kst-E).
    4. Where the dedendum exceeds the root form height, the tool has an edge break flank between
       the two; its angle is the given one, else alpha_n0 + 10 degrees (manual p. 186), and the
       dedendum is limited by ``stplus_max_tool_dedendum_factor``.
    5. The edge break angle: 90 degrees is the tool without edge break flank of manual p. 186
       (the dedendum is the root form height); so is an angle equal to the profile angle (probe
       ``tool_edge_break_angle_equal_to_pressure_angle``); an angle below the profile angle is
       replaced by alpha_n0 + 10 degrees (probe ``tool_edge_break_angle_below_pressure_angle``).
       STplus computes a flank of 85 degrees and aborts its iteration at 88 degrees (probes):
       an angle between ``STPLUS_MAX_EDGE_BREAK_ANGLE_DEG`` and 90 is a ``NotSupportedError``.

    The limits apply to a preset as to a given value (probes ``default_hob_at_*``,
    ``tool_addendum_limited_without_tip_rounding``). Every rule applied is appended to ``notes``.
    ``alpha_n_deg`` is the profile angle of the tool (that of the gear where the tool gives
    none); the limits need it, so a tool without it is a ``ParseError``. An addendum that is not
    positive is passed on for the contract to reject. The manual presets h_Ff0* with 1,1
    (p. 224) and sends h_f0 < h_Ff0 to h_f0max (p. 186); the program does what is stated here
    (probes ``tool_root_*``). The three ``min_..._factor`` arguments are the controls of the
    limits (MIN_WKZ_ZAHNKOPFDICKE*, MIN_LUECKENWEITE_EFF0*, MIN_LUECKENWEITE_EF0*) where the
    input sets them; ``None`` is the preset of the program.
    """
    if not isinstance(notes, list):
        raise InputRangeError(f"notes must be a list, got {type(notes).__name__}")
    if not isinstance(name, str):
        raise InputRangeError(f"the name of the tool must be a string, got {type(name).__name__}")
    if alpha_n_deg is None:
        raise ParseError(
            f"tool {name!r}: the limits of STplus need the profile angle of the tool or the "
            "pressure angle of the gear"
        )
    alpha_deg = finite_input(alpha_n_deg, "profile angle of the tool")
    if not 0.0 < alpha_deg < 90.0:
        raise InputRangeError(
            f"tool {name!r}: the profile angle of a rack tool must lie in (0, 90) deg, got "
            f"{alpha_deg!r}"
        )
    alpha = math.radians(alpha_deg)

    def given(value: float | None, what: str) -> float | None:
        return None if value is None else finite_input(value, f"tool {name!r}: {what}")

    h_a = given(addendum, "KOPFHOEHENFAKTOR")
    rho = given(tip_radius, "KOPFABRUNDUNGSFAKTOR")
    h_Ff = given(root_form_height, "FUSSFORMHOEHENFAKTOR")
    h_f = given(dedendum, "FUSSHOEHENFAKTOR")
    alpha_K = given(edge_break_angle_deg, "KANTENBRECHWINKEL")
    if alpha_K is not None and not 0.0 < alpha_K <= 90.0:
        raise InputRangeError(
            f"tool {name!r}: KANTENBRECHWINKEL must lie in (0, 90] deg, got {alpha_K!r}"
        )

    was = "KOPFHOEHENFAKTOR = "
    if h_a is None:
        h_a = _preset("tool_addendum")
        was = "the preset h_aP0* = "
        notes.append(
            f"tool {name!r}: KOPFHOEHENFAKTOR not given → h_aP0* = {h_a!r} (STplus default)"
        )
    if h_a > 0.0:
        tallest = stplus_max_tool_addendum_factor(alpha, min_tip_land_factor=min_tip_land_factor)
        if h_a > tallest:
            land = math.pi / 2.0 - 2.0 * tallest * math.tan(alpha)
            notes.append(
                f"tool {name!r}: {was}{h_a!r} reduced to h_aP0* = {tallest!r} as STplus does "
                f"(the tip of the tool tooth narrows to {land:.3g} m_n there)"
            )
            h_a = tallest
    was = "KOPFABRUNDUNGSFAKTOR = "
    if rho is None:
        rho = _preset("tool_tip_radius")
        was = "the preset rho_aP0* = "
        notes.append(
            f"tool {name!r}: KOPFABRUNDUNGSFAKTOR not given → rho_aP0* = {rho!r} (STplus default)"
        )
    if h_a > 0.0:
        # (an addendum that is not positive is left to the contract)
        full = stplus_max_tool_tip_radius_factor(h_a, alpha)
        if rho > full:
            notes.append(
                f"tool {name!r}: {was}{rho!r} reduced to the full radius rho_aP0* = {full!r} as "
                "STplus does"
            )
            rho = full

    was = "FUSSFORMHOEHENFAKTOR = "
    if h_Ff is None:
        h_Ff = _preset("tool_root_form_height")
        was = "the preset h_FfP0* = "
        notes.append(
            f"tool {name!r}: FUSSFORMHOEHENFAKTOR not given → h_FfP0* = {h_Ff!r} (STplus default)"
        )
    limited = False
    highest = stplus_max_tool_root_form_height_factor(alpha, min_space_factor=min_space_factor)
    if h_Ff > highest:
        space = math.pi / 2.0 - 2.0 * highest * math.tan(alpha)
        notes.append(
            f"tool {name!r}: {was}{h_Ff!r} reduced to h_FfP0* = {highest!r} as STplus does (the "
            f"tool space narrows to {space:.3g} m_n there)"
        )
        if h_f is not None and h_f > h_Ff:
            raise NotSupportedError(
                f"tool {name!r}: a root form height beyond the limit of STplus together with "
                "a larger dedendum is not probed"
            )
        h_Ff, limited = highest, True
    dedendum_preset: float | None = None
    if h_f is None:
        h_f = dedendum_preset = _preset("tool_dedendum")
        notes.append(
            f"tool {name!r}: FUSSHOEHENFAKTOR not given → h_fP0* = {h_f!r} (STplus default)"
        )
    if alpha_K is not None and alpha_K < alpha_deg * (1.0 - EPS):
        # probe tool_edge_break_angle_below_pressure_angle: 15 degrees at alpha_n = 20 degrees
        # is run with "alfa_K0 = 30.00 grd" and "Wkz.daten ... alfa_Kn0 ... geaendert"
        replaced = alpha_deg + _preset("tool_edge_break_angle")
        notes.append(
            f"tool {name!r}: KANTENBRECHWINKEL = {alpha_K!r} deg lies below the profile angle "
            f"→ alpha_K0 = {replaced!r} deg (alpha_n0 + 10 deg), as STplus replaces it"
        )
        alpha_K = replaced
    flat = alpha_K is not None and abs(alpha_K - alpha_deg) <= EPS * alpha_deg
    if alpha_K is not None and (flat or alpha_K >= 90.0 * (1.0 - EPS)):
        # manual p. 186: "Ein Kopfueberschneider ohne Kantenbrecher kann mit h_Ff0 und
        # alpha_Kn0 = 90 Grad oder h_Ff0 = h_f0 eingegeben werden" (probe
        # tool_edge_break_angle_ninety_degrees); an angle equal to the profile angle is read the
        # same way (probe tool_edge_break_angle_equal_to_pressure_angle)
        notes.append(
            f"tool {name!r}: KANTENBRECHWINKEL = {alpha_K!r} deg → a tool without edge break "
            f"flank, as STplus reads it: h_fP0* = h_FfP0* = {h_Ff!r} and no angle"
            + ("" if h_f in (h_Ff, dedendum_preset) else f" (h_fP0* = {h_f!r} is not used)")
        )
        h_f, alpha_K = h_Ff, None
    elif alpha_K is not None and alpha_K > STPLUS_MAX_EDGE_BREAK_ANGLE_DEG:
        raise NotSupportedError(
            f"tool {name!r}: KANTENBRECHWINKEL = {alpha_K!r} deg: STplus computes an edge break "
            f"flank of {STPLUS_MAX_EDGE_BREAK_ANGLE_DEG!r} deg and aborts its iteration at 88 deg "
            "(probes); what it does in between is not known. A tool without edge break flank "
            "is given by 90 deg"
        )
    elif limited or h_f < h_Ff:
        if h_f != h_Ff:
            notes.append(
                f"tool {name!r}: h_fP0* = {h_f!r} set to the root form height h_FfP0* = {h_Ff!r} "
                "as STplus does (no edge break flank)"
            )
        h_f = h_Ff
    if h_f > h_Ff:
        if alpha_K is None:
            alpha_K = alpha_deg + _preset("tool_edge_break_angle")
            notes.append(
                f"tool {name!r}: KANTENBRECHWINKEL not given → alpha_K0 = {alpha_K!r} deg "
                "(STplus default alpha_n0 + 10 deg for the flank between h_FfP0 and h_fP0)"
            )
        highest = stplus_max_tool_dedendum_factor(
            h_Ff, alpha, math.radians(alpha_K), min_root_space_factor=min_root_space_factor
        )
        if h_f > highest:
            notes.append(
                f"tool {name!r}: h_fP0* = {h_f!r} reduced to h_f0max* = {highest!r} as STplus "
                "does (the edge break flanks close the tool space there)"
            )
            h_f = highest
    return {
        "addendum_factor": h_a,
        "tip_radius_factor": rho,
        "root_form_height_factor": h_Ff,
        "dedendum_factor": h_f,
        "edge_break_angle_deg": alpha_K,
    }


def stplus_helix_angle_deg(
    a_w_mm: float, m_n_mm: float, alpha_n_deg: float, z_1: int, z_2: int, sum_x: float
) -> float:
    """Helix angle STplus computes where none is given: the angle at which the centre distance
    of the pair with the sum of the profile shift coefficients ``sum_x`` equals ``a_w_mm``
    (manual p. 16 and Bild 4.12: two of a, beta and the sum of x; subroutine GE12; probe
    ``helix_angle_from_centre_distance``).

    The centre distance grows with the helix angle, so there is one solution in [0, 45] degrees
    or none; none is a ``GeometryInfeasibleError``.
    """
    a_w = positive_input(a_w_mm, "centre distance a_w")
    m_n = positive_input(m_n_mm, "normal module m_n")
    alpha_n = math.radians(finite_input(alpha_n_deg, "normal pressure angle alpha_n"))
    total = finite_input(sum_x, "sum of the profile shift coefficients")

    def excess(beta: float) -> float:
        alpha_wt = pr.working_pressure_angle_without_backlash(z_1, z_2, alpha_n, beta, total)
        return pr.centre_distance(z_1, z_2, m_n, alpha_n, beta, alpha_wt) - a_w

    highest = math.radians(HELIX_ANGLE_RANGE_DEG[1])
    spur, steepest = excess(0.0), excess(highest)
    if abs(spur) <= EPS * a_w:
        return 0.0
    if abs(steepest) <= EPS * a_w:
        return HELIX_ANGLE_RANGE_DEG[1]
    if spur > 0.0 or steepest < 0.0:
        raise GeometryInfeasibleError(
            f"no helix angle in [0, {HELIX_ANGLE_RANGE_DEG[1]!r}] deg gives the centre distance "
            f"{a_w!r} mm with the sum of the profile shift coefficients {total!r}"
        )
    beta = brentq(excess, 0.0, highest, xtol=1e-15, rtol=4.0 * sys.float_info.epsilon)
    return math.degrees(float(beta))


MAX_TIP_CHAMFER_RANGE = (0.0, 0.5)
"""Range of the control MAX_KOPFKANTENBRUCH (manual p. 225: "zwischen 0 und 0,5"), an open
interval: STplus does not accept the ends (0 and 0.5 leave the preset, 0.01 and 0.49 act; probe
``controls_at_the_ends_of_their_ranges``)."""

TANGENTIAL_AMOUNT_RANGE = (0.3, 1.5)
"""Range of the control TANG_BETRAG_ZU_H_KGF (manual p. 225: "zwischen 0,3 und 1,5"), an open
interval: 0.3 and 1.5 leave the preset 0,7 in place, 0.31 and 1.49 act."""


def _in_range(value: float, what: str, bounds: tuple[float, float]) -> float:
    """A value of a control inside its range. STplus accepts the values between the ends of the
    range it documents, not the ends themselves (probes)."""
    number = finite_input(value, what)
    if not bounds[0] < number < bounds[1]:
        raise InputRangeError(
            f"{what} = {number!r} does not lie between {bounds[0]:g} and {bounds[1]:g}, the "
            "values STplus accepts"
        )
    return number


def stplus_tip_chamfer_height(
    h_K_mm: float, m_n_mm: float, *, max_factor: float | None = None
) -> float:
    """Radial height of a tip chamfer given as an input, as STplus takes it: limited to 0,20 m_n
    ("Eingabe zu Kopfkantenbruch begrenzt auf 0.20 * m_n", probe ``tip_chamfer_limits``; the
    manual presets the control MAX_KOPFKANTENBRUCH with 0,02, p. 225). ``max_factor`` is the
    control where the input sets it: the factor of the module to which the height is limited
    (probes ``tip_chamfer_limit_lowered``, ``tip_chamfer_limit_raised``)."""
    h_K = finite_input(h_K_mm, "radial height of the chamfer h_K")
    if h_K < 0.0:
        raise InputRangeError(f"radial height of the chamfer must be >= 0, got {h_K_mm!r}")
    factor = (
        _preset("tip_chamfer_max")
        if max_factor is None
        else _in_range(max_factor, "MAX_KOPFKANTENBRUCH", MAX_TIP_CHAMFER_RANGE)
    )
    # (max with a positive zero: a factor of -0.0 must not give a height of -0.0)
    return max(0.0, min(h_K, factor * positive_input(m_n_mm, "normal module m_n")))


def stplus_residual_tip_thickness(
    s_an_mm: float, h_K_mm: float, *, tangential_factor: float | None = None
) -> float:
    """Residual tip thickness STplus assumes for a chamfer given by its radial height alone, in
    the normal section: s_aK = s_an - 2 (0,7 h_K), at least 0,2 s_an.

    The tangential amount is preset to 0,7 h_K (manual p. 19 and p. 225, control
    TANG_BETRAG_ZU_H_KGF, default ``tip_chamfer_tangential``; ``tangential_factor`` is the
    control where the input sets it); the floor and the normal section are observed (probes
    ``tip_chamfer_limits``, ``tip_chamfer_helical``). A rule of the program, not of a norm: DIN
    ISO 21771 §6.1.2 defines a chamfer by h_K and s_aK.
    """
    s_an = positive_input(s_an_mm, "normal tip tooth thickness s_an")
    h_K = finite_input(h_K_mm, "radial height of the chamfer h_K")
    if h_K < 0.0:
        raise InputRangeError(f"radial height of the chamfer must be >= 0, got {h_K_mm!r}")
    factor = (
        _preset("tip_chamfer_tangential")
        if tangential_factor is None
        else _in_range(tangential_factor, "TANG_BETRAG_ZU_H_KGF", TANGENTIAL_AMOUNT_RANGE)
    )
    return max(s_an - 2.0 * factor * h_K, _preset("tip_chamfer_residual_floor") * s_an)


def stplus_transverse_residual_tip_thickness(
    s_at_mm: float, s_an_mm: float, h_K_mm: float, *, tangential_factor: float | None = None
) -> float:
    """The residual tip thickness of ``stplus_residual_tip_thickness`` as the transverse arc on
    the tip circle, which is what ``GearInput.residual_tip_thickness_mm`` carries: the normal
    value times s_at / s_an (Eq. (48) of DIN ISO 21771 relates the two on the tip circle)."""
    s_at = positive_input(s_at_mm, "transverse tip tooth thickness s_at")
    s_an = positive_input(s_an_mm, "normal tip tooth thickness s_an")
    residual = stplus_residual_tip_thickness(s_an, h_K_mm, tangential_factor=tangential_factor)
    return residual * s_at / s_an


def probe_listing(name: str) -> str:
    """The listing of the probe run ``name`` (``probes/<name>/report.sta.txt``)."""
    base = data_path(DIRECTORY, "probes")
    known = sorted(path.name for path in base.iterdir() if path.is_dir())
    if not isinstance(name, str) or name not in known:
        raise InputRangeError(f"unknown STplus probe {name!r}; packaged: {known}")
    return (base / name / "report.sta.txt").read_text(encoding="latin-1")


def stplus_chord_diameter(d_Ff_mm: float, d_Fa_mm: float) -> float:
    """Cylinder on which STplus 11.1F gives the chordal tooth thickness: the middle of the root
    form and the tip form circle, (d_Ff + d_Fa) / 2.

    Evidence: the listing prints it as 'Beruehrkreisdurchm. (oberes Abmass)'; it equals this
    value within 0,0005 mm on all 76 distinct gears of the stored listings (2026-10-04). The
    norm leaves the cylinder to the user and names d_a - 2 m_n as a diameter often used
    (DIN 21773:2014-08 §5, p. 8). A rule of the program, applied only where a caller asks.
    """
    d_Ff = positive_input(d_Ff_mm, "root form diameter d_Ff")
    d_Fa = positive_input(d_Fa_mm, "tip form diameter d_Fa")
    if d_Ff >= d_Fa:
        raise InputRangeError(
            f"root form diameter {d_Ff!r} must lie below the tip form diameter {d_Fa!r}"
        )
    return 0.5 * (d_Ff + d_Fa)


# --- choices of the program for the inspection dimensions ------------------------------------------
#
# Where the input gives neither, STplus 11.1F chooses the number of teeth spanned and the measuring
# ball itself. The manual does not say how. The rules below were found by experiment on 2026-10-04:
# the switch points of k and D_M were bisected over the tip diameter and the profile shift
# (conditions met within 0,0005 mm), then the rules were checked on random gears. The evidence is
# packaged (``inspection_choices.json``, written by ``scripts/stplus_inspection_choices.py``) and
# ``tests/test_stplus_program.py`` holds the rules against every gear of it. Rules of the program,
# not of a norm, applied only where a caller asks (ADR-109).

INSPECTION_CHOICES = "inspection_choices.json"


@lru_cache(maxsize=1)
def stplus_inspection_evidence() -> MappingProxyType[str, Any]:
    """Printed values of STplus listings the rules for k and D_M rest on: the measuring ball
    diameters the program chose over a sweep of the module (``table_mm``) and random gears with
    the k and D_M of their listings (``groups``)."""
    text = data_path(DIRECTORY, INSPECTION_CHOICES).read_text(encoding="utf-8")
    return MappingProxyType(json.loads(text))


def stplus_measuring_ball_diameters() -> tuple[float, ...]:
    """Diameters in mm from which STplus 11.1F chooses its measuring ball: 44 values from 1 to
    110 mm, every value the program printed while the module ran from 0,3 to 70 mm.

    Not DIN 3977:1981-02 Tabelle 1: the program has no value below 1 mm and none of 1,4, 3,25,
    3,75, 4,25, 5,25, 30 and 35 mm, and it has 32, 36 and 60 to 110 mm, which the norm does
    not list. Beyond 110 mm it prints D_M = 0.
    """
    return tuple(float(value) for value in stplus_inspection_evidence()["table_mm"])


def stplus_number_of_teeth_spanned(k_min: int, k_max: int) -> int:
    """Number of teeth spanned STplus 11.1F chooses where the input names none:
    k = min(INT((k_min + k_max) / 2) + 1, k_max), the middle of the usable range rounded up to
    the next number, with k_min and k_max of DIN 21773:2014-08 Eq. (12), (13) for the gear at
    its upper allowance (first forms: the planes touch between the form circles).

    Evidence: k changes exactly where the span over a whole number of teeth touches the root
    form or the tip form circle, and all 540 gears of ``inspection_choices.json`` follow the
    rule (as did the 1400 random gears of the exploratory runs, with wide and with narrow
    faces: the face width does not enter). The norm chooses the k that touches next to the
    V-cylinder (Eq. (9)).
    """
    lowest = integer_input(k_min, "smallest number of teeth spanned k_min")
    highest = integer_input(k_max, "largest number of teeth spanned k_max")
    if highest < ins.MIN_TEETH_SPANNED:
        raise GeometryInfeasibleError(
            f"no span touches below the tip form circle (k_max = {highest}); the evidence for the "
            "rule of STplus holds no such gear"
        )
    return min(math.floor((lowest + highest) / 2) + 1, highest)


def stplus_ideal_measuring_ball_diameter(
    z: int, m_n_mm: float, x: float, alpha_n_rad: float, beta_rad: float, d_y_mm: float
) -> float:
    """Diameter STplus 11.1F takes for the ball that touches the flanks on the circle d_y:
    D = abs(z_n m_n cos(alpha_n) (tan(alpha_K) - tan(alpha_y))) with z_n = z / cos^3(beta),
    cos(alpha_y) = z_n m_n cos(alpha_n) / (z_n m_n + d_y - d) and
    alpha_K = tan(alpha_y) - inv(alpha_t) + eta, eta = (pi / 2 - 2 x tan(alpha_n)) / z.

    The form of DIN 3960:1987 Eq. (3.8.24) to (3.8.27), which gives the ball that touches on the
    V-cylinder. The norm computes on the virtual spur gear throughout (z_nM = z / cos^3,3(beta),
    inv(alpha_n), eta with z_nM); the program takes the virtual number of teeth z / cos^3(beta)
    for the factor and for alpha_y, and the real gear for inv and eta. For a spur gear the result
    is the exact ball; for a helical gear it is not the ball that touches on d_y (z 40,
    beta 30 degrees: the ball it names touches about 0,95 m_n higher), and for many teeth at
    large helix angles the bracket turns negative, of which the program takes the amount.
    """
    number = teeth(z)
    m_n = positive_input(m_n_mm, "normal module m_n")
    alpha_n = pressure_angle(alpha_n_rad, "normal pressure angle alpha_n")
    beta = helix(beta_rad)
    d_y = positive_input(d_y_mm, "diameter d_y")
    d = iv.reference_diameter(number, m_n, beta)
    z_n = number / math.cos(beta) ** 3
    base = z_n * m_n * math.cos(alpha_n)
    circle = z_n * m_n + d_y - d
    if circle < base:
        raise GeometryInfeasibleError(
            f"d_y = {d_y!r} mm lies below the base circle of the virtual spur gear "
            f"(z_n = {z_n!r}): no profile angle there"
        )
    tangent = math.tan(math.acos(min(1.0, base / circle)))
    alpha_t = iv.transverse_pressure_angle(alpha_n, beta)
    alpha_K = tangent - iv.inv(alpha_t) + iv.space_width_half_angle(number, x, alpha_n)
    if not -HALF_PI < alpha_K < HALF_PI:
        raise GeometryInfeasibleError(
            f"alpha_K = {alpha_K!r} rad of the rule of STplus is no profile angle"
        )
    return finite_result(
        abs(base * (math.tan(alpha_K) - tangent)), "ball diameter of the rule of STplus"
    )


def _two_ball_dimension(
    D_M: float, z: int, m_n: float, x: float, alpha_n: float, beta: float
) -> float | None:
    """M_dK of the ball D_M (DIN 21773 Eq. (30), (31), (35), (36)); None where the ball does not
    rest on the involutes of the tooth space."""
    alpha_t = iv.transverse_pressure_angle(alpha_n, beta)
    eta = iv.space_width_half_angle(z, x, alpha_n)
    try:
        alpha_Kt = ins.ball_centre_profile_angle(D_M, z, m_n, alpha_n, eta, alpha_t)
    except GeometryInfeasibleError:
        return None
    d_K = ins.ball_centre_circle_diameter(iv.base_diameter(z, m_n, alpha_n, beta), alpha_Kt)
    return ins.diametral_two_ball_dimension(d_K, D_M, z)


def stplus_measuring_ball_diameter(
    z: int,
    m_n_mm: float,
    x: float,
    alpha_n_rad: float,
    beta_rad: float,
    d_a_mm: float,
    d_Ff_mm: float,
    d_Fa_mm: float,
    *,
    given_mm: float | None = None,
) -> float:
    """Measuring ball STplus 11.1F computes with, for the gear at its upper allowance (x = x_E).

    A given ball (``MESSTUECKDM_D_M``) is taken if its diametral two-ball dimension exceeds the
    tip diameter, whatever its diameter; a given ball that does not stand above the tip is
    replaced by the ball the program chooses, without a message (probes
    ``measuring_ball_given_above_the_tip``, ``measuring_ball_given_below_the_tip``).

    The ball the program chooses is the larger of two values of
    ``stplus_measuring_ball_diameters``:

    A  the smallest whose diametral two-ball dimension M_dK exceeds the tip diameter d_a
       (odd numbers of teeth with the factor cos(pi / 2z) of DIN 21773 Eq. (36));
    B  two values below the first one above D, the ball of
       ``stplus_ideal_measuring_ball_diameter`` for the middle of the form circles
       (d_Ff + d_Fa) / 2; where the table has no value two below, that first one above D.

    Evidence: the switch points over the tip diameter meet A and B within 0,0005 mm (spur and
    helical gears, modules 0,5 to 4 mm), and all 540 gears of ``inspection_choices.json`` follow
    the rule (as did the 2000 random gears of the exploratory runs). Neither DIN 3977 nor
    DIN 21773 chooses like this: they name the ball that touches next to the V-cylinder.
    """
    number = teeth(z)
    m_n = positive_input(m_n_mm, "normal module m_n")
    alpha_n = pressure_angle(alpha_n_rad, "normal pressure angle alpha_n")
    beta = helix(beta_rad)
    d_a = positive_input(d_a_mm, "tip diameter d_a")
    middle = stplus_chord_diameter(d_Ff_mm, d_Fa_mm)
    shift = finite_input(x, "profile shift coefficient x")

    def stands_above_the_tip(D_M: float) -> bool:
        dimension = _two_ball_dimension(D_M, number, m_n, shift, alpha_n, beta)
        return dimension is not None and dimension > d_a

    if given_mm is not None and stands_above_the_tip(
        positive_input(given_mm, "measuring ball diameter D_M")
    ):
        return float(given_mm)
    table = stplus_measuring_ball_diameters()
    above_tip = next((D_M for D_M in table if stands_above_the_tip(D_M)), None)
    if above_tip is None:
        raise GeometryInfeasibleError(
            f"no ball of the table of STplus (up to {table[-1]:g} mm) stands above the tip "
            f"diameter {d_a!r} mm; the program prints D_M = 0"
        )
    ideal = stplus_ideal_measuring_ball_diameter(number, m_n, shift, alpha_n, beta, middle)
    first_above = next((i for i, value in enumerate(table) if value > ideal), len(table))
    on_flank = table[first_above - 2] if first_above >= 2 else table[first_above]
    return max(above_tip, on_flank)


InspectionChoices = tuple[tuple[int, int], tuple[float, float]]
"""(k of pinion and wheel, D_M of pinion and wheel in mm)."""


def stplus_inspection_choices(generation: GenerationResult) -> InspectionChoices:
    """Number of teeth spanned and measuring ball STplus 11.1F prints the inspection dimensions
    of the generated pair with: the values of the input where it names them
    (``number_of_teeth_spanned``, ``measuring_ball_diameter_mm``), else the rules of the program
    (``stplus_number_of_teeth_spanned``, ``stplus_measuring_ball_diameter``) for the gears at
    their upper allowance.

    The choice changes which dimension is printed, not the gear: profile shift, tooth thickness
    and allowances do not depend on it. gearcore itself chooses by the norm (DIN 21773 Eq. (9),
    DIN 3977 Tabelle 1); ``with_stplus_inspection_choices`` states the choices of STplus as
    inputs for a caller who wants the dimensions of an STplus listing.
    """
    if not isinstance(generation, GenerationResult):
        raise InputRangeError(
            f"generation must be a GenerationResult, got {type(generation).__name__}"
        )
    pair = generation.inputs
    m_n = pair.normal_module_mm
    alpha_n = math.radians(pair.normal_pressure_angle_deg)
    numbers: list[int] = []
    balls: list[float] = []
    for index, (gear, generated) in enumerate(
        zip(pair.gears.as_tuple(), generation.gears.as_tuple(), strict=True)
    ):
        beta = math.radians(pair.helix_angle_deg) * (1.0 if index == 0 else -1.0)
        z, x_E = generated.number_of_teeth, generated.generating_profile_shift_coefficient
        d_Ff, d_Fa = generated.root_form_diameter_mm, generated.tip_form_diameter_mm
        if gear.number_of_teeth_spanned is not None:
            numbers.append(gear.number_of_teeth_spanned)
        else:
            numbers.append(
                stplus_number_of_teeth_spanned(
                    ins.min_number_of_teeth_spanned(z, m_n, x_E, alpha_n, beta, d_Ff),
                    ins.max_number_of_teeth_spanned(z, m_n, x_E, alpha_n, beta, d_Fa),
                )
            )
        balls.append(
            stplus_measuring_ball_diameter(
                z,
                m_n,
                x_E,
                alpha_n,
                beta,
                generated.tip_diameter_mm,
                d_Ff,
                d_Fa,
                given_mm=gear.measuring_ball_diameter_mm,
            )
        )
    return (numbers[0], numbers[1]), (balls[0], balls[1])


def with_stplus_inspection_choices(
    generation: GenerationResult, choices: InspectionChoices | None = None
) -> GenerationResult:
    """The generation with k and D_M stated as inputs of its gears: ``choices``, or without them
    the choices of STplus (``stplus_inspection_choices``). ``compute_inspection`` of the result
    gives the inspection dimensions as an STplus listing prints them; nothing else changes.

    Where a choice of STplus does not touch the involute between the form circles (extreme
    gears: the rule for the ball is not exact on helical gears), ``compute_inspection`` raises
    ``GeometryInfeasibleError`` for it as for any such input.
    """
    k, D_M = stplus_inspection_choices(generation) if choices is None else choices
    if not (isinstance(k, tuple) and isinstance(D_M, tuple) and len(k) == 2 and len(D_M) == 2):
        raise InputRangeError(f"choices must be ((k_1, k_2), (D_M1, D_M2)), got {choices!r}")
    k = (integer_input(k[0], "k of the pinion"), integer_input(k[1], "k of the wheel"))
    D_M = (positive_input(D_M[0], "D_M of the pinion"), positive_input(D_M[1], "D_M of the wheel"))
    gears = [
        gear.model_copy(
            update={"number_of_teeth_spanned": k[index], "measuring_ball_diameter_mm": D_M[index]}
        )
        for index, gear in enumerate(generation.inputs.gears.as_tuple())
    ]
    inputs = generation.inputs.model_copy(update={"gears": Pair(pinion=gears[0], wheel=gears[1])})
    return generation.model_copy(update={"inputs": inputs})
