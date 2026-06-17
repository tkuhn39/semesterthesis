"""
@module: app.services.materials
@context: Domain layer — gear materials for the capacity methods.
@role: A typed material model shared by the steel (DIN 3990) and plastic
       (VDI 2736) tooth-capacity methods. Steel carries the DIN 3990 endurance
       limits; plastic additionally carries the VDI 2736 specifics (allowable
       temperature, wear coefficient, and — where available — the temperature-
       and cycle-dependent strength curves).

Design rule (from the project): missing *non-essential* fields must never block a
calculation — a capacity sub-result that needs an absent field is reported as a
warning and skipped, the rest still runs. So most fields are optional; the
consuming method decides what it strictly needs.
"""

import math
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

from app.io.ste import SteFile, SteSection


class MaterialKind(StrEnum):
    """Whether a gear body is metal (DIN 3990) or polymer (VDI 2736)."""

    STEEL = "steel"
    PLASTIC = "plastic"


class StrengthPoint(BaseModel):
    """One point of a temperature/cycle-dependent strength curve (VDI 2736 plastics)."""

    temperature_c: float
    cycles: float
    stress_mpa: float


class NonlinearCurve(BaseModel):
    """A measured x–y material curve for nonlinear behaviour or a property dependence.

    Generic so measurements can be supplied directly — and later imported from
    Matscape material cards — instead of only linear constants. Examples: a
    stress–strain curve (``x = strain``, ``y = stress_mpa``) for a nonlinear FE
    material, or a property over temperature/cycles (``x = temperature_c`` |
    ``cycles``, ``y = modulus_mpa`` | ``stress_mpa``) for the analytical methods.
    Shared by the capacity methods, RIKOR, STplus and the FE material model.
    """

    quantity: str  # what the curve describes, e.g. "stress_strain", "modulus_vs_temperature"
    x_label: str
    y_label: str
    points: list[tuple[float, float]]  # measured (x, y), strictly ascending in x
    condition_temperature_c: float | None = None
    source: str = "manual"  # provenance: manual | matscape | datasheet

    @field_validator("points")
    @classmethod
    def _ascending_and_nonempty(
        cls, points: list[tuple[float, float]]
    ) -> list[tuple[float, float]]:
        if len(points) < 2:
            raise ValueError("a nonlinear curve needs at least two points")
        xs = [x for x, _ in points]
        if any(later <= earlier for earlier, later in zip(xs, xs[1:], strict=False)):
            raise ValueError("curve x values must be strictly ascending")
        return points

    def value_at(self, x: float) -> float:
        """Linear interpolation of y at ``x``, clamped to the measured range."""
        if x <= self.points[0][0]:
            return self.points[0][1]
        if x >= self.points[-1][0]:
            return self.points[-1][1]
        for (x0, y0), (x1, y1) in zip(self.points, self.points[1:], strict=False):
            if x0 <= x <= x1:
                return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
        return self.points[-1][1]


class Material(BaseModel):
    """Elastic and strength data for one gear material.

    Lengths/stresses in N/mm² (= MPa). Endurance limits are optional so a partly
    specified material (e.g. plastic without a wear coefficient) still loads and
    only blocks the sub-results that truly need the missing value.
    """

    name: str
    kind: MaterialKind
    elastic_modulus_mpa: float
    poisson_ratio: float

    # Endurance limits — DIN 3990 for steel; VDI 2736 baseline for plastic.
    sigma_hlim_mpa: float | None = None  # flank endurance limit
    sigma_flim_mpa: float | None = None  # root (bending) endurance limit
    sigma_fe_mpa: float | None = None  # basic root strength (DIN 3990 sigma_FE)
    reference_cycles_flank: float | None = None
    reference_cycles_root: float | None = None

    # VDI 2736 plastic specifics (optional → graceful when absent).
    allowable_temperature_c: float | None = None
    wear_coefficient_mm3_per_nm: float | None = None  # k_W
    # Optional measured strength curves (sigma_Flim/N/T, sigma_Hlim/N/T).
    root_strength_curve: list[StrengthPoint] | None = None
    flank_strength_curve: list[StrengthPoint] | None = None

    # Provenance and generic nonlinear measured curves (e.g. stress-strain).
    source: str = "manual"  # manual | matscape | datasheet
    nonlinear_curves: list[NonlinearCurve] = Field(default_factory=list)

    @property
    def is_plastic(self) -> bool:
        return self.kind is MaterialKind.PLASTIC

    def curve(self, quantity: str) -> NonlinearCurve | None:
        """Return the first nonlinear curve describing ``quantity``, else None."""
        for curve in self.nonlinear_curves:
            if curve.quantity == quantity:
                return curve
        return None

    def root_strength_at(self, temperature_c: float, cycles: float) -> float | None:
        """σ_Flim,N at the root temperature and load-cycle count (VDI 2736 Table 5)."""
        return _strength_at(self.root_strength_curve, temperature_c, cycles, self.sigma_flim_mpa)

    def flank_strength_at(self, temperature_c: float, cycles: float) -> float | None:
        """σ_Hlim,N at the flank temperature and load-cycle count (VDI 2736)."""
        return _strength_at(self.flank_strength_curve, temperature_c, cycles, self.sigma_hlim_mpa)


def _strength_at(
    curve: list[StrengthPoint] | None, temperature_c: float, cycles: float, fallback: float | None
) -> float | None:
    """Bilinear lookup of a strength curve over temperature and log₁₀(cycles).

    Returns the constant ``fallback`` (temperature-independent endurance limit) when
    no measured grid is supplied, so the caller degrades gracefully (ADR-013).
    """
    if not curve:
        return fallback
    log_n = math.log10(max(cycles, 1.0))
    temps = sorted({p.temperature_c for p in curve})

    def _at_temp(temp: float) -> float:
        pts = sorted((p for p in curve if p.temperature_c == temp), key=lambda p: p.cycles)
        xs = [math.log10(max(p.cycles, 1.0)) for p in pts]
        ys = [p.stress_mpa for p in pts]
        if log_n <= xs[0]:
            return ys[0]
        if log_n >= xs[-1]:
            return ys[-1]
        for (x0, y0), (x1, y1) in zip(
            zip(xs, ys, strict=True), zip(xs[1:], ys[1:], strict=True), strict=False
        ):
            if x0 <= log_n <= x1:
                return y0 + (y1 - y0) * (log_n - x0) / (x1 - x0)
        return ys[-1]

    if temperature_c <= temps[0]:
        return _at_temp(temps[0])
    if temperature_c >= temps[-1]:
        return _at_temp(temps[-1])
    for t0, t1 in zip(temps, temps[1:], strict=False):
        if t0 <= temperature_c <= t1:
            s0, s1 = _at_temp(t0), _at_temp(t1)
            return s0 + (s1 - s0) * (temperature_c - t0) / (t1 - t0)
    return _at_temp(temps[-1])


def _section_float(section: SteSection, key: str) -> float | None:
    entry = section.get(key)
    if entry is None:
        return None
    for token in entry.values:
        try:
            return float(token)
        except ValueError:
            continue
    return None


# Heuristic: STplus plastic materials carry the reduced DIN-3990 limits and a low
# modulus. The kind is decided from the modulus (steel ~ 200 GPa, polymer < 20 GPa).
_PLASTIC_MODULUS_CEILING_MPA = 20_000.0


def material_from_ste(ste: SteFile, name: str) -> Material:
    """Build a :class:`Material` from the ``$ name`` material section of a `.ste`.

    Raises ``KeyError`` if the section or the elastic data is missing (those are
    essential); all strength limits are optional.
    """
    section = ste.section(name)
    if section is None:
        raise KeyError(f"material section not found: {name}")
    modulus = _section_float(section, "ELASTIZITAETSMODUL")
    poisson = _section_float(section, "QUERKONTRAKTIONSZAHL")
    if modulus is None or poisson is None:
        raise KeyError(f"material {name!r} lacks elastic data (modulus/poisson)")
    label = section.get("WERKSTOFFBEZEICHNUNG")
    kind = MaterialKind.PLASTIC if modulus < _PLASTIC_MODULUS_CEILING_MPA else MaterialKind.STEEL
    return Material(
        name=label.values[0] if label and label.values else name,
        kind=kind,
        elastic_modulus_mpa=modulus,
        poisson_ratio=poisson,
        sigma_hlim_mpa=_section_float(section, "DIN3990/87_SIGMA_HLIM"),
        sigma_flim_mpa=_section_float(section, "DIN3990/87_SIGMA_FLIM"),
        sigma_fe_mpa=_section_float(section, "DIN3990/87_SIGMA_FE"),
        reference_cycles_flank=_section_float(section, "DIN3990/87_NL_REF_H"),
        reference_cycles_root=_section_float(section, "DIN3990/87_NL_REF_F"),
    )
