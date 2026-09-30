"""Input contracts of the geometry chain.

Names, symbols, units and designations of the fields come from the quantity registry
(``gearcore.quantities``, ``data/quantities.yaml``): a field is declared with ``Q(<quantity>)``
and carries the symbol of the governing norm, its designation and the STplus key in its schema.
Range limits are the ranges the implementation is verified for, not physical limits; wider
inputs are rejected with a pydantic ``ValidationError`` rather than computed silently.

Feasibility checks that need geometry (a >= a_min, d_a > d_Ff, tip clearance) live in the
computational modules and raise ``GeometryInfeasibleError``; models stay data.
"""

import math
from enum import StrEnum
from typing import ClassVar, Self

from pydantic import Field, model_validator

from gearcore.models.common import (
    HELIX_ANGLE_RANGE_DEG,
    NORMAL_MODULE_RANGE_MM,
    PRESSURE_ANGLE_RANGE_DEG,
    PROFILE_SHIFT_RANGE,
    TEETH_RANGE,
    FrozenModel,
    Pair,
)
from gearcore.quantities import Q


class GearKind(StrEnum):
    EXTERNAL = "external"
    INTERNAL = (
        "internal"  # prepared extension point (extension_points.md); stage 1: NotSupportedError
    )


class ToolKind(StrEnum):
    RACK = "rack"  # hob, rack cutter, grinding wheel (STplus: Fräser/Hobelkamm/Schleifscheibe)
    SHAPER = "shaper"  # pinion-type cutter (STplus SR_*); extension point
    PROFILE = "profile"  # form tool (STplus PW_*); extension point


class MaterialKind(StrEnum):
    """Steel and plastic branches are never mixed; every material-dependent function dispatches on this."""

    STEEL = "steel"
    PLASTIC = "plastic"


class QualitySystem(StrEnum):
    """Tolerance system a quality grade refers to; DIN 3962 Q7 and ISO 1328 Q7 are not the same."""

    DIN3962 = "DIN3962"  # withdrawn tables (STplus DIN_QUALITAET), cross-check only
    ISO1328 = "ISO1328"  # DIN ISO 1328-1:2018 (STplus ISO_QUALITAET)


class MaterialRef(FrozenModel):
    """Reference to a material record (name in the database or in the ``.ste`` file) with its kind."""

    kind: MaterialKind
    name: str = Field(description="record name, e.g. '16MnCr5' or 'WST_PA66'", min_length=1)


class ToolProfile(FrozenModel):
    """Tool reference profile of a rack-type tool (DIN ISO 21771:2014 §7.1; DIN 3972; DIN 867).

    Height factors refer to the tool normal module ``m_n0``. ``normal_module_mm`` and
    ``profile_angle_deg`` default to ``None`` = "same as the gear" (STplus manual §4.16.2: tool
    module and profile angle are entered only when they deviate from the gear). Other optional
    fields stay ``None`` when the tool does not define them; the generation module then applies the
    norm default and reports it in ``warnings`` — never a silent fallback inside the model.

    ``protuberance_mm`` and ``machining_allowance_mm`` are required (user decision 2026-09-30):
    a tool without protuberance or allowance states the zero instead of leaving it to a default.
    """

    QUANTITY_PREFIX: ClassVar[str] = "tool_"

    kind: ToolKind = ToolKind.RACK
    name: str | None = Field(default=None, description="STplus section name ($ WKZ_...)")
    normal_module_mm: float | None = Q("tool_normal_module", default=None, gt=0.0)
    profile_angle_deg: float | None = Q(
        "tool_profile_angle",
        default=None,
        ge=PRESSURE_ANGLE_RANGE_DEG[0],
        le=PRESSURE_ANGLE_RANGE_DEG[1],
    )
    addendum_factor: float = Q("tool_addendum", factor=True, gt=0.0, le=2.5)
    tip_radius_factor: float = Q("tool_tip_radius", factor=True, ge=0.0, le=0.6)
    dedendum_factor: float | None = Q("tool_dedendum", factor=True, default=None, gt=0.0, le=2.5)
    root_form_height_factor: float | None = Q(
        "tool_root_form_height", factor=True, default=None, ge=0.0, le=2.5
    )
    edge_break_angle_deg: float | None = Q("tool_edge_break_angle", default=None, gt=0.0, lt=90.0)
    protuberance_mm: float = Q("tool_protuberance", ge=0.0)
    protuberance_angle_deg: float | None = Q(
        "tool_protuberance_angle", default=None, gt=0.0, lt=90.0
    )
    machining_allowance_mm: float = Q("machining_allowance", ge=0.0)


class SpanMeasurement(FrozenModel):
    """Base tangent length W_k over k teeth (DIN 21773:2014-08 §7, Eq. (14)).

    Carried as given and not evaluated yet. A span and a profile shift coefficient determine
    each other; whether a given span stands for the nominal x or, with the tooth thickness
    allowance, for x_E is settled with increments 4 and 5 (open in ADR-107).
    """

    span_measurement_mm: float = Q("span_measurement", gt=0.0)
    number_of_teeth_spanned: int = Q("number_of_teeth_spanned", ge=2, strict=True)


class GearInput(FrozenModel):
    """One gear of a pair. Its nominal x is given, or follows from a_w and the mate's x
    (ADR-107); ``span`` is carried and not evaluated yet."""

    kind: GearKind = GearKind.EXTERNAL
    number_of_teeth: int = Q("number_of_teeth", ge=TEETH_RANGE[0], le=TEETH_RANGE[1], strict=True)
    profile_shift_coefficient: float | None = Q(
        "profile_shift_coefficient",
        default=None,
        ge=PROFILE_SHIFT_RANGE[0],
        le=PROFILE_SHIFT_RANGE[1],
    )
    span: SpanMeasurement | None = None
    face_width_mm: float = Q("face_width", gt=0.0, le=2000.0)
    tip_diameter_mm: float | None = Q("tip_diameter", default=None, gt=0.0)
    # required (user decision 2026-09-30): a gear without tip chamfer states 0
    tip_chamfer_radial_mm: float = Q("tip_chamfer_radial", ge=0.0)
    tool: ToolProfile
    finishing_tool: ToolProfile | None = None  # WERKZEUG_FERTIGVERZ. (extension point)
    material: MaterialRef | None = None  # geometry needs no material; load capacity requires it
    # STplus MESSZAEHNEZAHL_K: teeth spanned by the check dimension (None = per DIN 21773)
    number_of_teeth_spanned: int | None = Q(
        "number_of_teeth_spanned", default=None, ge=2, strict=True
    )
    tooth_thickness_allowance_um: tuple[float, float] | None = Q(
        "tooth_thickness_allowance", default=None
    )
    span_allowance_um: tuple[float, float] | None = Q("span_allowance", default=None)
    allowance_series: str | None = Field(
        default=None, description="ABMASS_TOL_REIHE — DIN 3967 designation such as 'C25' or 'cd25'"
    )
    quality_grade: int | None = Q("quality_grade", default=None, ge=0, le=12, strict=True)
    quality_system: QualitySystem | None = None

    @model_validator(mode="after")
    def _allowances_ordered(self) -> Self:
        for label, pair in (
            ("tooth_thickness_allowance_um", self.tooth_thickness_allowance_um),
            ("span_allowance_um", self.span_allowance_um),
        ):
            if pair is not None and pair[0] < pair[1]:
                raise ValueError(
                    f"{label}: upper allowance {pair[0]} must be >= lower allowance {pair[1]}"
                )
        return self

    @model_validator(mode="after")
    def _quality_needs_system(self) -> Self:
        if (self.quality_grade is None) != (self.quality_system is None):
            raise ValueError("quality_grade and quality_system must be given together")
        return self


class PairInput(FrozenModel):
    """A cylindrical gear pair: common module, angles, optional centre distance, two gears."""

    normal_module_mm: float = Q(
        "normal_module", ge=NORMAL_MODULE_RANGE_MM[0], le=NORMAL_MODULE_RANGE_MM[1]
    )
    normal_pressure_angle_deg: float = Q(
        "normal_pressure_angle",
        ge=PRESSURE_ANGLE_RANGE_DEG[0],
        le=PRESSURE_ANGLE_RANGE_DEG[1],
    )
    # required (user decision 2026-09-30): a spur pair states 0
    helix_angle_deg: float = Q(
        "helix_angle", ge=HELIX_ANGLE_RANGE_DEG[0], le=HELIX_ANGLE_RANGE_DEG[1]
    )
    # None = the centre distance follows from the profile shift sum; a given one is fixed (ADR-107)
    centre_distance_mm: float | None = Q("centre_distance", default=None, gt=0.0)
    gears: Pair[GearInput]
    min_tip_clearance_factor: float | None = Q(
        "min_tip_clearance", factor=True, default=None, ge=0.0
    )

    @model_validator(mode="after")
    def _index_1_is_the_pinion(self) -> Self:
        """DIN ISO 21771:2014-08 §5.1.3: index 1 names the smaller gear of an external pair."""
        z_1, z_2 = self.gears.pinion.number_of_teeth, self.gears.wheel.number_of_teeth
        if z_1 > z_2:
            raise ValueError(
                f"the pinion is the smaller gear: z_1 = {z_1} > z_2 = {z_2}; swap the gears"
            )
        return self

    @model_validator(mode="after")
    def _profile_shift_determinable(self) -> Self:
        """Of a_w, x_1 and x_2 two are given; all three are over-determined (user decision
        2026-09-30, ADR-107). A pair that gives span measurements in place of a missing x is
        accepted as an input, because such files exist and have to be readable; spans are not
        evaluated yet (open in ADR-107), so the pair geometry answers such a pair with
        ``NotSupportedError``."""
        fixed = [
            g.profile_shift_coefficient is not None or g.span is not None
            for g in self.gears.as_tuple()
        ]
        shifts = [g.profile_shift_coefficient is not None for g in self.gears.as_tuple()]
        if self.centre_distance_mm is not None and all(shifts):
            raise ValueError(
                "over-determined: the centre distance and both profile shift coefficients are "
                "given; only two of the three may be given (a given centre distance is fixed, "
                "ADR-107)"
            )
        if all(fixed):
            return self
        if self.centre_distance_mm is None:
            raise ValueError(
                "profile shift undetermined: give the nominal x of both gears, or the centre "
                "distance together with the x of one gear (ADR-107)"
            )
        if not any(fixed):
            raise ValueError(
                "profile shift undetermined: with a given centre distance one gear needs its "
                "nominal x (ADR-107)"
            )
        return self

    @model_validator(mode="after")
    def _tool_modules_consistent(self) -> Self:
        """A tool may deviate in module/pressure angle only if it generates the same basic rack.

        Generating condition: equal normal base pitch, m_n0·cos α_n0 = m_n·cos α_n
        (p_bn = π·m_n·cos α_n, DIN ISO 21771:2014-08 §4.4). The STplus manual §4.16.2 admits a
        deviating tool module/pressure angle as input; ``None`` means "same as the gear".
        """
        rhs = self.normal_module_mm * math.cos(math.radians(self.normal_pressure_angle_deg))
        for role, gear in (("pinion", self.gears.pinion), ("wheel", self.gears.wheel)):
            m_n0, alpha_n0 = resolve_tool_module_and_angle(self, gear.tool)
            lhs = m_n0 * math.cos(math.radians(alpha_n0))
            if abs(lhs - rhs) > 1e-6 * rhs:
                raise ValueError(
                    f"{role} tool: m_n0*cos(alpha_n0) = {lhs:.6f} differs from m_n*cos(alpha_n) = {rhs:.6f}; "
                    "the tool cannot generate this basic rack"
                )
        return self


def resolve_tool_module_and_angle(pair: PairInput, tool: ToolProfile) -> tuple[float, float]:
    """Tool normal module and pressure angle with the "None = same as the gear" rule applied."""
    m_n0 = pair.normal_module_mm if tool.normal_module_mm is None else tool.normal_module_mm
    alpha_n0 = (
        pair.normal_pressure_angle_deg if tool.profile_angle_deg is None else tool.profile_angle_deg
    )
    return m_n0, alpha_n0
