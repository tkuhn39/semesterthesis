"""
@module: app.io.ste
@context: I/O layer — STplus (FVA 241) spur-gear input files.
@role: Parse STplus `.ste` files into a typed model and extract the gear-stage
       geometry. STplus stores `$ Section` blocks of `KEY = value(s)` lines
       (whitespace-separated tokens, often pinion/wheel pairs); `#` starts a
       comment. Values are kept as raw tokens so non-numeric entries
       (materials, tools) survive; typed extraction is opt-in.
"""

from pathlib import Path
from typing import NamedTuple

from pydantic import BaseModel, Field


class Pair[T](NamedTuple):
    """A ``(pinion, wheel)`` value pair.

    Still a tuple — indexable, iterable and ``zip``-able as before — but with
    named fields so the pinion (gear 1) and the wheel (gear 2) can never be
    silently swapped. STplus lists gear 1 before gear 2 on a line.
    """

    pinion: T
    wheel: T


class SteEntry(BaseModel):
    """A single `KEY = value(s)` line; values are raw whitespace-split tokens."""

    key: str
    values: list[str]


class SteSection(BaseModel):
    """A `$ Name` block with its entries, order preserved."""

    name: str
    entries: list[SteEntry] = Field(default_factory=list)

    def get(self, key: str) -> SteEntry | None:
        """Return the first entry with ``key`` in this section, else None."""
        for entry in self.entries:
            if entry.key == key:
                return entry
        return None


class SteFile(BaseModel):
    """A parsed STplus `.ste` file as an ordered list of sections."""

    sections: list[SteSection] = Field(default_factory=list)

    def section(self, name: str) -> SteSection | None:
        """Return the first section named ``name``, else None."""
        for section in self.sections:
            if section.name == name:
                return section
        return None

    def find(self, key: str) -> SteEntry | None:
        """Return the first entry with ``key`` across all sections, else None."""
        for section in self.sections:
            entry = section.get(key)
            if entry is not None:
                return entry
        return None


def parse_ste(text: str) -> SteFile:
    """Parse STplus `.ste` text into a :class:`SteFile`."""
    sections: list[SteSection] = []
    current: SteSection | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("$"):
            current = SteSection(name=line[1:].strip())
            sections.append(current)
            continue
        if "=" not in line:
            continue
        key, _, rhs = line.partition("=")
        if current is None:
            current = SteSection(name="")
            sections.append(current)
        current.entries.append(SteEntry(key=key.strip(), values=rhs.split()))
    return SteFile(sections=sections)


def load_ste(path: Path) -> SteFile:
    """Load and parse a `.ste` file (Latin-1, as written by STplus)."""
    return parse_ste(path.read_text(encoding="latin-1"))


class SteToolProfile(BaseModel):
    """An STplus tool reference profile (a ``$ WKZ_*`` section).

    The pre-cutting tool (hob/rack) that generates a gear. Its reference profile
    drives the generated tip/root form circles and — via the edge-break angle —
    the tip chamfer (Kopfkantenbruch ``h_K``). Height factors are referred to the
    tool normal module. All fields are optional because STplus defaults absent
    ones (e.g. an unspecified edge-break angle means no tool-cut tip chamfer).
    """

    name: str
    addendum_factor: float | None = None  # KOPFHOEHENFAKTOR      h_aP0*
    dedendum_factor: float | None = None  # FUSSHOEHENFAKTOR      h_fP0*
    root_form_height_factor: float | None = None  # FUSSFORMHOEHENFAKTOR  h_FfP0*
    tip_radius_factor: float | None = None  # KOPFABRUNDUNGSFAKTOR  rho_aP0*
    normal_module_mm: float | None = None  # WKZ_NORMALMODUL       m_n0
    pressure_angle_deg: float | None = None  # WKZ_EINGRIFFSWINKEL   alfa_n0
    edge_break_angle_deg: float | None = None  # KANTENBRECHWINKEL     alfa_Kn0


class SteGearStage(BaseModel):
    """Spur-gear stage geometry extracted from a `.ste`, as (pinion, wheel).

    Only the *defining* inputs are required. STplus computes the tip diameter and
    the center distance when they are not given in the input, so both are optional
    here. A negative tooth count denotes an internal gear (STplus convention).

    Beyond the geometry block, a `.ste` also carries the generating tool profiles
    and configuration factors that influence the geometry (tip chamfer, form
    circles, tooth-thickness allowances); these are captured here when present.
    """

    normal_module_mm: float
    teeth: Pair[int]
    pressure_angle_deg: Pair[float]
    helix_angle_deg: Pair[float]
    face_width_mm: Pair[float]
    profile_shift: Pair[float]
    center_distance_mm: float | None = None
    tip_diameter_mm: Pair[float] | None = None
    span_teeth: Pair[int] | None = None
    tools: Pair[SteToolProfile | None] | None = None
    min_tip_clearance_factor: float | None = None  # MINDESTKOPFSPIEL c*
    tooth_width_allowance_upper_um: Pair[float] | None = None  # OBERES_ZAHNW_ABMASS  A_We
    tooth_width_allowance_lower_um: Pair[float] | None = None  # UNTERES_ZAHNW_ABMASS A_Wi


def _numbers(entry: SteEntry) -> list[float]:
    """Numeric tokens of an entry; non-numeric flags (e.g. STplus ``%``) are dropped."""
    numbers: list[float] = []
    for token in entry.values:
        try:
            numbers.append(float(token))
        except ValueError:
            continue
    return numbers


def _required(ste: SteFile, key: str) -> list[float]:
    entry = ste.find(key)
    if entry is None:
        raise KeyError(f"STplus key not found: {key}")
    numbers = _numbers(entry)
    if not numbers:
        raise ValueError(f"STplus key {key!r} has no numeric value")
    return numbers


def _optional(ste: SteFile, key: str) -> list[float] | None:
    entry = ste.find(key)
    if entry is None:
        return None
    return _numbers(entry) or None


def _pair(numbers: list[float]) -> Pair[float]:
    return Pair(numbers[0], numbers[0] if len(numbers) == 1 else numbers[1])


def _section_float(section: SteSection, key: str) -> float | None:
    """First numeric value of ``key`` within a single section, else None."""
    entry = section.get(key)
    if entry is None:
        return None
    numbers = _numbers(entry)
    return numbers[0] if numbers else None


def _tool_from_section(ste: SteFile, name: str) -> SteToolProfile | None:
    """Build a :class:`SteToolProfile` from the ``$ name`` tool section, if present."""
    section = ste.section(name)
    if section is None:
        return None
    return SteToolProfile(
        name=name,
        addendum_factor=_section_float(section, "KOPFHOEHENFAKTOR"),
        dedendum_factor=_section_float(section, "FUSSHOEHENFAKTOR"),
        root_form_height_factor=_section_float(section, "FUSSFORMHOEHENFAKTOR"),
        tip_radius_factor=_section_float(section, "KOPFABRUNDUNGSFAKTOR"),
        normal_module_mm=_section_float(section, "WKZ_NORMALMODUL"),
        pressure_angle_deg=_section_float(section, "WKZ_EINGRIFFSWINKEL"),
        edge_break_angle_deg=_section_float(section, "KANTENBRECHWINKEL"),
    )


def _tools_from_ste(ste: SteFile) -> Pair[SteToolProfile | None] | None:
    """Resolve the two gears' tool profiles via ``WERKZEUG_VORVERZ.`` references."""
    entry = ste.find("WERKZEUG_VORVERZ.")
    if entry is None or len(entry.values) < 2:
        return None
    return Pair(
        _tool_from_section(ste, entry.values[0]),
        _tool_from_section(ste, entry.values[1]),
    )


def gear_stage_from_ste(ste: SteFile) -> SteGearStage:
    """Extract the spur-gear stage geometry from a parsed `.ste`.

    Requires the defining inputs (module, teeth, pressure/helix angle, face width,
    profile shift). Center distance, tip diameter, span teeth, the generating tool
    profiles and the configuration factors (tip clearance, tooth-width allowances)
    are taken only when present — they refine the generated geometry.
    """
    teeth = _required(ste, "ZAEHNEZAHL")
    if len(teeth) < 2:
        raise ValueError(
            "'.ste' defines a single gear (one ZAEHNEZAHL value), not a two-gear stage"
        )
    center = _optional(ste, "ACHSABSTAND")
    tip = _optional(ste, "KOPFKREISDM")
    span = _optional(ste, "MESSZAEHNEZAHL_K")
    clearance = _optional(ste, "MINDESTKOPFSPIEL")
    upper = _optional(ste, "OBERES_ZAHNW_ABMASS")
    lower = _optional(ste, "UNTERES_ZAHNW_ABMASS")
    return SteGearStage(
        normal_module_mm=_required(ste, "NORMALMODUL")[0],
        teeth=Pair(int(teeth[0]), int(teeth[1])),
        pressure_angle_deg=_pair(_required(ste, "EINGRIFFSWINKEL")),
        helix_angle_deg=_pair(_required(ste, "SCHRAEGUNGSWINKEL")),
        face_width_mm=_pair(_required(ste, "ZAHNBREITE")),
        profile_shift=_pair(_required(ste, "PROFILVERSCHIEBUNG_N")),
        center_distance_mm=center[0] if center else None,
        tip_diameter_mm=_pair(tip) if tip else None,
        span_teeth=Pair(int(span[0]), int(span[1])) if span and len(span) >= 2 else None,
        tools=_tools_from_ste(ste),
        min_tip_clearance_factor=clearance[0] if clearance else None,
        tooth_width_allowance_upper_um=_pair(upper) if upper else None,
        tooth_width_allowance_lower_um=_pair(lower) if lower else None,
    )
