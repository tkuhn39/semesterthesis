"""The gears as manufactured: the measured numbers of the rig parts put onto the STplus case
for the FE variants (user decisions of 2026-10-19, ADR-116).

A variant of ``data/fe/as_manufactured.yaml`` names, per gear, a set of measured numbers: the
span W_k the part was measured with, its tip and root diameters, the tip relief of the pinion,
the profile slope and the tip corner radius of the wheel. ``apply`` turns them into a pair the
generation accepts and into the profile modifications of the contour:

- the span sets the span allowance of the gear so that the generated span (DIN 21773 Eq. (14)
  with x_Es) equals the measured one; the nominal x of the case stays;
- the tip diameter is given to the generation as it is; a tool whose dedendum would top it
  (the STplus rule of ADR-114) gets its dedendum raised, because a moulded wheel has no such
  tool;
- the root diameter sets the tool addendum so that the generated root diameter
  d_fE = d + 2 x_E m_n - 2 h_aP0 (DIN ISO 21771 Eq. (125)) equals the measured one; the fillet
  keeps the tool tip radius of the case;
- the tip relief, the profile slope and the tip corner radius go into
  ``contour.ProfileModification``; the slope pivots on the measuring circle of the span d_M
  (DIN 21773 Eq. (17)), so that the measured span keeps its value; a tip corner radius replaces
  the edge break flank of the tool, and the generation gets the chamfer of the arc instead
  (h_K and s_aK of its tangent points, DIN ISO 21771 §6.1.2), so that the tip form diameter,
  the start A of the path of contact and the contact ratio are those of the rounded tooth.

Nothing of the STplus case is changed on disk; the result carries the pair, its generation and
the numbers of every change for the manifest of a deck folder.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Self

from pydantic import Field, ValidationError, model_validator

from gearcore import contour as ct
from gearcore import data
from gearcore import involute as iv
from gearcore._safe import EPS, positive_input
from gearcore.errors import GeometryInfeasibleError, InputRangeError, NotSupportedError
from gearcore.generation import compute_generation
from gearcore.inspection import (
    compute_inspection,
    span_measurement,
    span_measuring_circle_diameter,
)
from gearcore.models.common import FrozenModel, Pair
from gearcore.models.inputs import GearInput, PairInput, ToolProfile
from gearcore.models.results import GenerationResult
from gearcore.quantities import Q

ROLES: tuple[ct.Role, ...] = ("pinion", "wheel")
DEDENDUM_MARGIN = 0.01
"""Module factor added to the dedendum of a tool that would top the measured tip circle."""
TARGET_TOLERANCE = 1.0e-9
"""Relative tolerance within which the generated numbers must meet the measured targets."""


class ManufacturedGear(FrozenModel):
    """One set of measured numbers of a gear (``as_manufactured.yaml``, ``gears``). A number
    that is ``None`` (or zero for a modification) leaves the STplus case as it is."""

    description: str = ""
    span_measurement_mm: float | None = Q("span_measurement", default=None, gt=0.0)
    number_of_teeth_spanned: int | None = Q(
        "number_of_teeth_spanned", default=None, ge=2, strict=True
    )
    tip_diameter_mm: float | None = Q("tip_diameter", default=None, gt=0.0)
    root_diameter_mm: float | None = Q("generated_root_diameter", default=None, gt=0.0)
    tip_relief_um: float = Q("tip_relief", default=0.0, ge=0.0)
    tip_relief_start_diameter_mm: float | None = Q(
        "tip_relief_start_diameter", default=None, gt=0.0
    )
    profile_slope_um: float = Q("profile_slope_deviation", default=0.0)
    profile_control_diameter_mm: float | None = Q("profile_control_diameter", default=None, gt=0.0)
    tip_edge_radius_mm: float = Q("tip_edge_radius", default=0.0, ge=0.0)
    sources: tuple[str, ...] = ()
    note: str = ""

    @model_validator(mode="after")
    def _complete(self) -> Self:
        if self.tip_relief_um > 0.0 and self.tip_relief_start_diameter_mm is None:
            raise ValueError("a tip relief needs tip_relief_start_diameter_mm")
        if self.profile_slope_um != 0.0 and self.profile_control_diameter_mm is None:
            raise ValueError("a profile slope needs profile_control_diameter_mm")
        return self


class ManufacturedVariant(FrozenModel):
    """Which measured set each gear of a case takes (``as_manufactured.yaml``, ``variants``)."""

    case: str = Field(min_length=1)
    label: str = Field(min_length=1)
    description: str = ""
    pinion: ManufacturedGear | None = None
    wheel: ManufacturedGear | None = None
    set_names: dict[str, str | None] = Field(default_factory=dict)
    """Name of the measured set per role (``pinion``, ``wheel``), None where the case stays."""

    @model_validator(mode="after")
    def _one_gear_at_least(self) -> Self:
        if self.pinion is None and self.wheel is None:
            raise ValueError(f"variant {self.label!r} changes neither gear")
        return self

    def gear(self, role: ct.Role) -> ManufacturedGear | None:
        return self.pinion if role == "pinion" else self.wheel


@dataclass(frozen=True)
class GearChanges:
    """What ``apply`` did to one gear and what the generation then gives (manifest numbers)."""

    role: str
    set_name: str
    span_target_mm: float | None = None
    span_nominal_mm: float | None = None
    span_allowance_um: float | None = None
    span_generated_mm: float | None = None
    number_of_teeth_spanned: int | None = None
    tip_diameter_mm: float | None = None
    root_diameter_mm: float | None = None
    addendum_factor: float | None = None
    dedendum_factor: float | None = None
    tip_form_diameter_mm: float | None = None
    tip_chamfer_radial_mm: float | None = None
    residual_tip_thickness_mm: float | None = None
    span_measuring_circle_diameter_mm: float | None = None
    generating_profile_shift_coefficient: float | None = None
    root_form_diameter_mm: float | None = None
    modification: ct.ProfileModification | None = None
    notes: tuple[str, ...] = field(default_factory=tuple)

    def as_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            key: value
            for key, value in self.__dict__.items()
            if key not in ("modification", "notes")
        }
        out["modification"] = None if self.modification is None else self.modification.model_dump()
        out["notes"] = list(self.notes)
        return out


@dataclass(frozen=True)
class ManufacturedResult:
    """The pair with the measured numbers, its generation and the changes per gear."""

    variant: ManufacturedVariant
    pair: PairInput
    generation: GenerationResult
    changes: dict[str, GearChanges]

    def modification(self, role: ct.Role) -> ct.ProfileModification | None:
        change = self.changes.get(role)
        return None if change is None else change.modification


def variant_labels(case: str) -> list[str]:
    """Labels of the variants of a case, in the order of the file."""
    document = data.load_as_manufactured()
    if case not in document["cases"]:
        raise InputRangeError(
            f"no as-manufactured variants for the case {case!r}; cases: {sorted(document['cases'])}"
        )
    return list(document["cases"][case]["variants"])


def load_variant(case: str, label: str) -> ManufacturedVariant:
    """One variant of ``as_manufactured.yaml`` with its measured sets."""
    document = data.load_as_manufactured()
    if case not in document["cases"]:
        raise InputRangeError(
            f"no as-manufactured variants for the case {case!r}; cases: {sorted(document['cases'])}"
        )
    entry = document["cases"][case]
    if not isinstance(label, str) or label not in entry["variants"]:
        raise InputRangeError(
            f"unknown as-manufactured variant {label!r} of {case!r}; known: {list(entry['variants'])}"
        )
    chosen = entry["variants"][label]
    sets: dict[str, ManufacturedGear | None] = {}
    for role in ROLES:
        name = chosen[role]
        if name is None:
            sets[role] = None
            continue
        raw = dict(entry["gears"][name])
        raw["sources"] = tuple(raw.get("sources", ()))
        try:
            sets[role] = ManufacturedGear(**raw)
        except ValidationError as error:
            raise InputRangeError(f"as_manufactured.yaml: gear set {name!r}: {error}") from error
    try:
        return ManufacturedVariant(
            case=case,
            label=label,
            description=str(chosen.get("description", "")),
            pinion=sets["pinion"],
            wheel=sets["wheel"],
            set_names={role: chosen[role] for role in ROLES},
        )
    except ValidationError as error:
        raise InputRangeError(f"as_manufactured.yaml: variant {label!r}: {error}") from error


def _gear_input(gear: GearInput, update: dict[str, Any], tool_update: dict[str, Any]) -> GearInput:
    """The gear with the fields of ``update`` and the tool fields of ``tool_update`` replaced,
    validated again (``model_copy`` would not validate)."""
    try:
        tool = ToolProfile(**{**gear.tool.model_dump(), **tool_update})
        return GearInput(**{**gear.model_dump(), **update, "tool": tool})
    except ValidationError as error:
        raise InputRangeError(f"the measured numbers give no valid gear: {error}") from error


def _pair_with(pair: PairInput, gears: dict[str, GearInput]) -> PairInput:
    return PairInput(
        **{
            **pair.model_dump(exclude={"gears"}),
            "gears": Pair(pinion=gears["pinion"], wheel=gears["wheel"]),
        }
    )


def _gear_of(generation: GenerationResult, role: str) -> Any:
    return generation.gears.pinion if role == "pinion" else generation.gears.wheel


def _apply_gear(
    role: ct.Role,
    pair: PairInput,
    gears: dict[str, GearInput],
    base: GenerationResult,
    spec: ManufacturedGear,
    set_name: str,
) -> tuple[GearInput, GearChanges]:
    gear = gears[role]
    m_n = pair.normal_module_mm
    alpha_n = math.radians(pair.normal_pressure_angle_deg)
    z = gear.number_of_teeth
    d = iv.reference_diameter(z, m_n, 0.0)
    d_b = iv.base_diameter(z, m_n, alpha_n, 0.0)
    update: dict[str, Any] = {}
    tool_update: dict[str, Any] = {}
    numbers: dict[str, Any] = {"role": role, "set_name": set_name}
    notes: list[str] = []

    # 1 the span: the allowance that generates the measured span with the nominal x of the case
    if spec.span_measurement_mm is not None:
        if gear.span is not None or gear.ball_dimension is not None:
            raise NotSupportedError(
                f"{role}: the case gives the tooth thickness by an inspection dimension; the "
                "measured span replaces a span allowance only"
            )
        if gear.tooth_thickness_allowance_um is not None:
            raise NotSupportedError(
                f"{role}: the case gives tooth thickness allowances; the measured span replaces "
                "span allowances only"
            )
        k = spec.number_of_teeth_spanned or gear.number_of_teeth_spanned
        if k is None:
            raise InputRangeError(f"{role}: the measured span needs the number of teeth spanned")
        x = _gear_of(base, role).profile_shift_coefficient
        nominal = span_measurement(z, m_n, x, alpha_n, 0.0, k)
        allowance = (spec.span_measurement_mm - nominal) * 1.0e3
        update["span_allowance_um"] = (allowance, allowance)
        update["number_of_teeth_spanned"] = k
        numbers.update(
            span_target_mm=spec.span_measurement_mm,
            span_nominal_mm=nominal,
            span_allowance_um=allowance,
            number_of_teeth_spanned=k,
        )

    # 2 the tip circle as measured
    if spec.tip_diameter_mm is not None:
        update["tip_diameter_mm"] = spec.tip_diameter_mm
        numbers["tip_diameter_mm"] = spec.tip_diameter_mm

    # x_E with the new thickness, from the generation of the intermediate pair
    stage = _gear_input(gear, update, {})
    x_E = _gear_of(
        compute_generation(_pair_with(pair, {**gears, role: stage})), role
    ).generating_profile_shift_coefficient

    # 3 the root circle: the tool addendum that generates it (Eq. (125) solved for h_aP0)
    if spec.root_diameter_mm is not None:
        h_aP0 = 0.5 * (d + 2.0 * x_E * m_n - spec.root_diameter_mm)
        tool_update["addendum_factor"] = h_aP0 / m_n
        numbers["root_diameter_mm"] = spec.root_diameter_mm
        numbers["addendum_factor"] = h_aP0 / m_n

    # 4 a tool dedendum that would top the measured tip circle (STplus rule, ADR-114) is raised
    d_a = spec.tip_diameter_mm if spec.tip_diameter_mm is not None else gear.tip_diameter_mm
    if gear.tool.dedendum_factor is not None and d_a is not None:
        topping = d + 2.0 * (x_E * m_n + gear.tool.dedendum_factor * m_n)
        if topping < d_a * (1.0 + EPS):
            needed = 0.5 * (d_a - d) / m_n - x_E + DEDENDUM_MARGIN
            tool_update["dedendum_factor"] = needed
            notes.append(
                f"tool dedendum factor raised from {gear.tool.dedendum_factor:g} to {needed:.4f}: "
                f"the root line of the tool would top the measured tip circle at {topping:.4f} mm "
                "(STplus rule of ADR-114; a moulded gear has no such tool)"
            )
            numbers["dedendum_factor"] = needed

    # 5 the deviations of the flank
    pivot: float | None = None
    if spec.profile_slope_um != 0.0:
        W_k = spec.span_measurement_mm
        if W_k is None:
            inspection = compute_inspection(
                compute_generation(_pair_with(pair, {**gears, role: stage}))
            )
            limits = getattr(inspection.gears, role).span_measurement_mm
            if limits is None:
                raise InputRangeError(f"{role}: the pivot of the profile slope needs a span")
            W_k = limits.upper
        pivot = span_measuring_circle_diameter(d_b, W_k, 0.0)
        numbers["span_measuring_circle_diameter_mm"] = pivot
    modification = ct.ProfileModification(
        tip_relief_um=spec.tip_relief_um,
        tip_relief_start_diameter_mm=spec.tip_relief_start_diameter_mm,
        profile_slope_um=spec.profile_slope_um,
        profile_control_diameter_mm=spec.profile_control_diameter_mm,
        profile_slope_pivot_diameter_mm=pivot,
        tip_edge_radius_mm=spec.tip_edge_radius_mm,
    )
    if spec.tip_edge_radius_mm > 0.0:
        # the arc replaces the edge break flank of the tool; the generation gets the chamfer of
        # the arc (h_K, s_aK of its tangent points) so that d_Fa and A are those of the arc
        tool_update["edge_break_angle_deg"] = None
        tool_update["root_form_height_factor"] = None
        first = _gear_input(
            gear,
            {**update, "tip_chamfer_radial_mm": 0.0, "residual_tip_thickness_mm": None},
            tool_update,
        )
        pass_1 = compute_generation(_pair_with(pair, {**gears, role: first}))
        rounded = ct.tooth_contour(pass_1, role, modification=modification)
        r_a = 0.5 * _gear_of(pass_1, role).tip_diameter_mm
        tip = rounded.segment("tip")
        psi_tip = math.atan2(float(tip[-1][0]), float(tip[-1][1]))
        update["tip_chamfer_radial_mm"] = r_a - 0.5 * rounded.tip_form_diameter_mm
        update["residual_tip_thickness_mm"] = 2.0 * r_a * psi_tip
        numbers["tip_chamfer_radial_mm"] = update["tip_chamfer_radial_mm"]
        numbers["residual_tip_thickness_mm"] = update["residual_tip_thickness_mm"]
        notes.append(
            f"tip corner radius {spec.tip_edge_radius_mm:g} mm in place of the edge break flank "
            f"of the tool: tip form diameter {rounded.tip_form_diameter_mm:.4f} mm (tangent point "
            f"of the arc), residual tip thickness {update['residual_tip_thickness_mm']:.4f} mm"
        )
    if modification.is_empty:
        numbers["modification"] = None
    else:
        numbers["modification"] = modification
    numbers["notes"] = tuple(notes)
    return _gear_input(gear, update, tool_update), GearChanges(**numbers)


def _check(role: str, what: str, got: float, target: float | None) -> None:
    if target is not None and abs(got - target) > TARGET_TOLERANCE * max(abs(target), 1.0):
        raise GeometryInfeasibleError(
            f"{role}: the generation gives {what} = {got!r} mm, the measured target is {target!r} mm"
        )


def apply(pair: PairInput, variant: ManufacturedVariant) -> ManufacturedResult:
    """The pair with the measured numbers of ``variant`` and its generation; the numbers the
    generation gives are checked against the targets (``GeometryInfeasibleError`` when a target
    is missed, for instance a tip circle the tool still tops)."""
    if not isinstance(pair, PairInput):
        raise InputRangeError(f"a PairInput is required, got {type(pair).__name__}")
    if not isinstance(variant, ManufacturedVariant):
        raise InputRangeError(f"a ManufacturedVariant is required, got {type(variant).__name__}")
    if pair.helix_angle_deg != 0.0:
        raise NotSupportedError("the measured geometry is applied to spur gears only")
    base = compute_generation(pair)
    gears: dict[str, GearInput] = {"pinion": pair.gears.pinion, "wheel": pair.gears.wheel}
    changes: dict[str, GearChanges] = {}
    for role in ROLES:
        spec = variant.gear(role)
        if spec is None:
            continue
        name = variant.set_names.get(role) or role
        gears[role], changes[role] = _apply_gear(role, pair, gears, base, spec, name)
    final = _pair_with(pair, gears)
    generation = compute_generation(final)
    inspection = compute_inspection(generation)
    for role in ROLES:
        if role not in changes:
            continue
        change = changes[role]
        generated = _gear_of(generation, role)
        limits = getattr(inspection.gears, role).span_measurement_mm
        span_generated = None if limits is None else limits.upper
        _check(role, "the span W_k", span_generated or 0.0, change.span_target_mm)
        _check(role, "the tip diameter d_a", generated.tip_diameter_mm, change.tip_diameter_mm)
        _check(
            role,
            "the root diameter d_fE",
            generated.generated_root_diameter_mm,
            change.root_diameter_mm,
        )
        if change.modification is not None and change.modification.tip_edge_radius_mm > 0.0:
            contour = ct.tooth_contour(generation, role, modification=change.modification)
            _check(
                role,
                "the tip form diameter d_Fa of the arc",
                generated.tip_form_diameter_mm,
                contour.tip_form_diameter_mm,
            )
        changes[role] = GearChanges(
            **{
                **change.__dict__,
                "span_generated_mm": span_generated,
                "tip_form_diameter_mm": generated.tip_form_diameter_mm,
                "generating_profile_shift_coefficient": generated.generating_profile_shift_coefficient,
                "root_form_diameter_mm": generated.root_form_diameter_mm,
                "addendum_factor": positive_input(generated.tool_addendum_mm, "h_aP0")
                / pair.normal_module_mm,
            }
        )
    return ManufacturedResult(variant=variant, pair=final, generation=generation, changes=changes)


__all__ = [
    "GearChanges",
    "ManufacturedGear",
    "ManufacturedResult",
    "ManufacturedVariant",
    "apply",
    "load_variant",
    "variant_labels",
]
