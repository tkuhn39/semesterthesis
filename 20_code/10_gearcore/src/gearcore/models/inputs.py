"""Input contracts of the geometry chain.

Symbols follow DIN ISO 21771:2014-08 (tool reference profile §7.1: h_aP0*, rho_aP0*, h_fP0*,
h_FfP0*, pr_P0, alpha_prP0); STplus key names are given in the field descriptions so ``.ste``
files map one-to-one. Range limits are the ranges the implementation is verified for, not
physical limits; wider inputs are rejected with a pydantic ``ValidationError`` rather than
computed silently.

Feasibility checks that need geometry (a >= a_min, d_a > d_Ff, tip clearance) live in the
computational modules and raise ``GeometryInfeasibleError``; models stay data.
"""

import math
from enum import StrEnum
from typing import Self

from pydantic import Field, model_validator

from gearcore.models.common import F, FrozenModel, Pair


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
    ``pressure_angle_deg`` default to ``None`` = "same as the gear" (STplus manual §4.16.2: tool
    module and pressure angle are entered only when they deviate from the gear). Other optional
    fields stay ``None`` when the tool does not define them; the generation module then applies the
    norm default and reports it in ``warnings`` — never a silent fallback inside the model.
    """

    kind: ToolKind = ToolKind.RACK
    name: str | None = Field(default=None, description="STplus section name ($ WKZ_...)")
    normal_module_mm: float | None = F(
        "m_n0", "mm", "WKZ_NORMALMODUL; None = gear normal module", default=None, gt=0.0
    )
    pressure_angle_deg: float | None = F(
        "alpha_P0",
        "deg",
        "WKZ_EINGRIFFSWINKEL; None = gear pressure angle",
        default=None,
        ge=10.0,
        le=30.0,
    )
    addendum_factor: float = F(
        "h_aP0*", "-", "KOPFHOEHENFAKTOR — tool addendum = gear dedendum factor", gt=0.0, le=2.5
    )
    tip_radius_factor: float = F(
        "rho_aP0*", "-", "KOPFABRUNDUNGSFAKTOR — tool tip rounding", ge=0.0, le=0.6
    )
    dedendum_factor: float | None = F(
        "h_fP0*", "-", "FUSSHOEHENFAKTOR — tool dedendum", default=None, gt=0.0, le=2.5
    )
    root_form_height_factor: float | None = F(
        "h_FfP0*",
        "-",
        "FUSSFORMHOEHENFAKTOR — start of the tool's edge-break flank",
        default=None,
        ge=0.0,
        le=2.5,
    )
    edge_break_angle_deg: float | None = F(
        "alpha_K0",
        "deg",
        "KANTENBRECHWINKEL — tool-cut tip chamfer flank angle",
        default=None,
        gt=0.0,
        lt=90.0,
    )
    protuberance_mm: float = F(
        "pr_P0", "mm", "PROTUBERANZBETRAG (extension point)", default=0.0, ge=0.0
    )
    protuberance_angle_deg: float | None = F(
        "alpha_prP0", "deg", "PROTUBERANZWINKEL (extension point)", default=None, gt=0.0, lt=90.0
    )
    machining_allowance_mm: float = F(
        "q", "mm", "BEARBEITUNGSZUGABE per flank (extension point)", default=0.0, ge=0.0
    )


class SpanMeasurement(FrozenModel):
    """Base tangent length W_k over k teeth (DIN 21773:2014 §7) as an alternative to x."""

    span_mm: float = F("W_k", "mm", "ZAHNWEITE", gt=0.0)
    teeth: int = F("k", "-", "MESSZAEHNEZAHL", ge=2, strict=True)


class GearInput(FrozenModel):
    """One gear of a pair. Either ``profile_shift`` or ``span`` (or a and the mate's x) fixes x."""

    kind: GearKind = GearKind.EXTERNAL
    teeth: int = F(
        "z",
        "-",
        "ZAEHNEZAHL (>0; negative STplus values map to INTERNAL)",
        ge=5,
        le=1000,
        strict=True,
    )
    profile_shift: float | None = F(
        "x",
        "-",
        "PROFILVERSCHIEBUNG_N — nominal profile shift coefficient",
        default=None,
        ge=-2.0,
        le=2.0,
    )
    span: SpanMeasurement | None = None
    face_width_mm: float = F("b", "mm", "ZAHNBREITE", gt=0.0, le=2000.0)
    tip_diameter_mm: float | None = F(
        "d_a",
        "mm",
        "KOPFKREISDM — given tip diameter; None = from the basic rack",
        default=None,
        gt=0.0,
    )
    tip_chamfer_radial_mm: float = F(
        "h_K",
        "mm",
        "KOPFKANTENBRUCH — separately machined tip chamfer (radial amount)",
        default=0.0,
        ge=0.0,
    )
    tool: ToolProfile
    finishing_tool: ToolProfile | None = None  # WERKZEUG_FERTIGVERZ. (extension point)
    material: MaterialRef | None = None  # geometry needs no material; load capacity requires it
    span_teeth: int | None = F(
        "k",
        "-",
        "MESSZAEHNEZAHL_K — teeth for the span check dimension (None = auto per DIN 21773)",
        default=None,
        ge=2,
        strict=True,
    )
    tooth_thickness_allowance_um: tuple[float, float] | None = F(
        "E_sns/E_sni",
        "um",
        "upper/lower tooth-thickness allowance (DIN 3967 A_sne/A_sni)",
        default=None,
    )
    span_allowance_um: tuple[float, float] | None = F(
        "A_We/A_Wi", "um", "OBERES/UNTERES_ZAHNW_ABMASS — upper/lower span allowance", default=None
    )
    allowance_series: str | None = Field(
        default=None, description="ABMASS_TOL_REIHE — DIN 3967 designation such as 'C25' or 'cd25'"
    )
    quality_grade: int | None = F(
        "Q",
        "-",
        "DIN_QUALITAET / ISO_QUALITAET flank tolerance class",
        default=None,
        ge=0,
        le=12,
        strict=True,
    )
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

    normal_module_mm: float = F("m_n", "mm", "NORMALMODUL", ge=0.05, le=100.0)
    pressure_angle_deg: float = F(
        "alpha_n", "deg", "EINGRIFFSWINKEL", default=20.0, ge=10.0, le=30.0
    )
    helix_angle_deg: float = F(
        "beta",
        "deg",
        "SCHRAEGUNGSWINKEL (STplus sign: + = pinion right-hand)",
        default=0.0,
        ge=-45.0,
        le=45.0,
    )
    center_distance_mm: float | None = F(
        "a", "mm", "ACHSABSTAND; None = from the profile-shift sum", default=None, gt=0.0
    )
    gears: Pair[GearInput]
    min_tip_clearance_factor: float | None = F(
        "c_min*",
        "-",
        "MINDESTKOPFSPIEL — minimum tip clearance factor for a tip-diameter check",
        default=None,
        ge=0.0,
    )

    @model_validator(mode="after")
    def _profile_shift_determinable(self) -> Self:
        """Each gear's x must follow from x, from W_k, or from a together with the mate's x."""
        fixed = [g.profile_shift is not None or g.span is not None for g in self.gears.as_tuple()]
        if all(fixed):
            return self
        if self.center_distance_mm is None:
            raise ValueError(
                "profile shift undetermined: give x or a span measurement for both gears, "
                "or the centre distance together with one gear's x"
            )
        if not any(fixed):
            raise ValueError(
                "profile shift undetermined: with a given centre distance at least one gear needs x or a span"
            )
        return self

    @model_validator(mode="after")
    def _tool_modules_consistent(self) -> Self:
        """A tool may deviate in module/pressure angle only if it generates the same basic rack.

        Generating condition: equal normal base pitch, m_n0·cos α_n0 = m_n·cos α_n
        (p_bn = π·m_n·cos α_n, DIN ISO 21771:2014-08 §4.4). The STplus manual §4.16.2 admits a
        deviating tool module/pressure angle as input; ``None`` means "same as the gear".
        """
        rhs = self.normal_module_mm * math.cos(math.radians(self.pressure_angle_deg))
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
        pair.pressure_angle_deg if tool.pressure_angle_deg is None else tool.pressure_angle_deg
    )
    return m_n0, alpha_n0
