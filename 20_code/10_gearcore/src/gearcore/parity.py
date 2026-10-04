"""Value-by-value comparison of gearcore with an STplus oracle fixture (ADR-102, ADR-106).

STplus is a numeric oracle with a limited accuracy of its own. Its listing prints lengths with
three decimals, angles and the transverse module with five and the profile shift coefficient with
four; the interface file of own runs prints five decimals. STplus computes in single precision
(binary32, about seven significant digits). gearcore computes in binary64 and keeps every digit
inside the chain. A comparison therefore reports three tolerance parts separately:

* ``print_tolerance``: half a unit of the last digit STplus printed,
* ``arithmetic_tolerance``: ``ARITHMETIC_STEPS`` binary32 steps at the printed value,
* ``input_tolerance``: effect of the rounded profile shift coefficient, only where STplus derived
  x itself (from a span measurement or the centre distance) and gearcore has to use the printed x.

Nothing in this module feeds back into the geometry: it only reads packaged fixtures.
"""

import math
from collections.abc import Iterable
from enum import StrEnum
from typing import Any, Literal

from gearcore._safe import finite_input
from gearcore.data import has_stplus, load_stplus, printed_tolerance, stplus_input_path
from gearcore.errors import ParseError
from gearcore.involute import compute_basic_gear_geometry
from gearcore.io.ste import load_ste, pair_input_from_ste
from gearcore.models.common import FrozenModel, Pair
from gearcore.models.inputs import PairInput
from gearcore.models.results import (
    BasicGearGeometry,
    GearGeneration,
    GenerationResult,
    PairGeometry,
)
from gearcore.pair import compute_pair_geometry
from gearcore.quantities import quantity_of_field

ARITHMETIC_STEPS = 2.0
"""Accuracy of a value STplus computed, in binary32 steps (largest deviation observed: 1.72)."""

REPRESENTATION_SLACK = 1.0e-9
"""Absolute slack for comparing a binary64 value with a printed decimal token."""

Origin = Literal["listing", "interface"]
Role = Literal["pinion", "wheel"]

Sensitivity = Literal["none", "transverse", "normal"]

# compared result field -> how the rounding of a printed profile shift coefficient enters it
COMPARED_FIELDS: dict[str, Sensitivity] = {
    "transverse_pressure_angle_deg": "none",
    "base_helix_angle_deg": "none",
    "transverse_module_mm": "none",
    "reference_diameter_mm": "none",
    "base_diameter_mm": "none",
    "transverse_tooth_thickness_mm": "transverse",
    "normal_tooth_thickness_mm": "normal",
    "normal_space_width_mm": "normal",
}
PROFILE_SHIFT_FIELD = "profile_shift_coefficient"


def stplus_names(field: str) -> tuple[str, str]:
    """Listing symbol and interface key of a contract field, from the quantity registry."""
    entry, _ = quantity_of_field(field)
    names = entry.stplus
    if names is None or names.symbol is None or names.interface_key is None:
        raise ParseError(
            f"the registry names no STplus listing symbol and interface key for {field}"
        )
    return names.symbol, names.interface_key


# The listing prints these as a magnitude; the interface file prints the hand of each gear.
_MAGNITUDE_IN_LISTING = frozenset({"base_helix_angle_deg"})


class ParityVerdict(StrEnum):
    IDENTICAL = "identical"
    """Equal at the precision STplus printed."""
    ORACLE_ACCURACY = "oracle_accuracy"
    """Differs by no more than the accuracy of the STplus value itself."""
    DIFFERENT = "different"
    """Differs by more than STplus's accuracy explains: a defect or a documented norm difference."""


class ParityRow(FrozenModel):
    """One quantity of one gear compared with one STplus output.

    The values carry the unit named in ``unit`` (the row is generic over quantities).
    """

    case: str
    trust: str
    origin: Origin
    field: str
    symbol: str
    unit: str
    gear: Role
    gearcore_value: float
    stplus_value: float
    stplus_token: str
    difference: float
    print_tolerance: float
    arithmetic_tolerance: float
    input_tolerance: float
    solver_tolerance: float = 0.0
    """Accuracy of a value STplus determines numerically (the form circles of the generation,
    ``FORM_CIRCLE_ACCURACY_MM``); zero for every closed formula."""
    verdict: ParityVerdict


def printed_decimals(token: str) -> int:
    """Number of decimals of a printed fixed-point token ('86.60255' -> 5)."""
    text = token.strip()
    mantissa = text.lstrip("+-")
    digits, _, decimals = mantissa.partition(".")
    if not (digits + decimals).isdigit() or not digits:
        raise ParseError(f"printed value {token!r} is not a fixed-point number")
    return len(decimals)


def binary32_step(value: float) -> float:
    """Spacing of the binary32 numbers at ``value`` (2^-149 at zero)."""
    magnitude = abs(finite_input(value, "value"))
    if magnitude == 0.0:
        return math.ldexp(1.0, -149)
    _, exponent = math.frexp(magnitude)  # magnitude = mantissa * 2^exponent, 0.5 <= mantissa < 1
    return math.ldexp(1.0, max(exponent - 24, -149))


def _per_gear(values: list[Any], gear: int) -> Any:
    return values[gear] if len(values) > 1 else values[0]


def _verdict(difference: float, print_tol: float, further_tol: float) -> ParityVerdict:
    if abs(difference) <= print_tol + REPRESENTATION_SLACK:
        return ParityVerdict.IDENTICAL
    if abs(difference) <= print_tol + further_tol + REPRESENTATION_SLACK:
        return ParityVerdict.ORACLE_ACCURACY
    return ParityVerdict.DIFFERENT


def _symbol_and_unit(model: type[FrozenModel], field: str) -> tuple[str, str]:
    """Symbol and unit of a contract field (from the quantity registry, via the schema)."""
    extra = model.model_fields[field].json_schema_extra
    if not isinstance(extra, dict):
        raise ParseError(f"{model.__name__}.{field} carries no quantity metadata")
    return str(extra["symbol"]), str(extra["unit"])


def _row(
    *,
    case: str,
    trust: str,
    origin: Origin,
    field: str,
    gear: Role,
    value: float,
    reference: float,
    token: str,
    input_tolerance: float,
) -> ParityRow:
    symbol, unit = _symbol_and_unit(BasicGearGeometry, field)
    by_magnitude = origin == "listing" and field in _MAGNITUDE_IN_LISTING
    difference = abs(value) - abs(reference) if by_magnitude else value - reference
    print_tol = printed_tolerance(printed_decimals(token))
    arithmetic_tol = ARITHMETIC_STEPS * binary32_step(reference)
    return ParityRow(
        case=case,
        trust=trust,
        origin=origin,
        field=field,
        symbol=symbol,
        unit=unit,
        gear=gear,
        gearcore_value=value,
        stplus_value=reference,
        stplus_token=token,
        difference=difference,
        print_tolerance=print_tol,
        arithmetic_tolerance=arithmetic_tol,
        input_tolerance=input_tolerance,
        verdict=_verdict(difference, print_tol, arithmetic_tol + input_tolerance),
    )


def compare_basic_geometry(case: str) -> tuple[ParityRow, ...]:
    """Compare the basic single-gear geometry of a packaged STplus case, value by value.

    Where the importer passes a profile shift coefficient of ``input.ste`` on (two of a_w, x_1,
    x_2, ADR-107), gearcore computes with that input and the printed x is compared as a
    quantity of its own. Where STplus determined x itself (from the centre distance, or for a
    file with span measurements), gearcore computes with the printed x and its rounding enters
    ``input_tolerance`` of the thickness quantities.
    """
    meta = load_stplus(case, "meta")
    listing = load_stplus(case, "geometry")
    interface = load_stplus(case, "interface") if has_stplus(case, "interface") else None
    pair = pair_input_from_ste(load_ste(stplus_input_path(case))).pair
    trust = str(meta["trust"])

    outputs: list[tuple[Origin, dict[str, Any], str]] = [("listing", listing, "tokens")]
    if interface is not None:
        outputs.append(("interface", interface, "values"))

    rows: list[ParityRow] = []
    for gear, gear_input in enumerate(pair.gears.as_tuple()):
        role: Role = "pinion" if gear == 0 else "wheel"
        printed_shift: dict[Origin, tuple[float, str]] = {}
        for origin, document, tokens in outputs:
            symbol, interface_key = stplus_names(PROFILE_SHIFT_FIELD)
            key = symbol if origin == "listing" else f"GEOMETRIEDATEN/{interface_key}"
            printed_shift[origin] = (document[key]["numbers"][gear], document[key][tokens][gear])

        best: Origin = outputs[-1][0]  # the interface file prints more decimals than the listing
        # the importer passes on what STplus uses: with a, x_1 and x_2 in the file it drops x_2,
        # which STplus overrides (kst-E: input 0.3143, used 0.31433)
        given = gear_input.profile_shift_coefficient
        shift_is_input = given is not None
        shift = printed_shift[best][0] if given is None else given
        shift_rounding = (
            0.0 if shift_is_input else printed_tolerance(printed_decimals(printed_shift[best][1]))
        )
        ours = compute_basic_gear_geometry(
            number_of_teeth=gear_input.number_of_teeth,
            normal_module_mm=pair.normal_module_mm,
            normal_pressure_angle_deg=pair.normal_pressure_angle_deg,
            helix_angle_deg=pair.helix_angle_deg if gear == 0 else -pair.helix_angle_deg,
            profile_shift_coefficient=shift,
        )
        tangent = math.tan(math.radians(pair.normal_pressure_angle_deg))
        sensitivity = {
            "none": 0.0,
            "transverse": 2.0 * ours.transverse_module_mm * tangent,
            "normal": 2.0 * ours.normal_module_mm * tangent,
        }

        for origin, document, tokens in outputs:
            if shift_is_input:
                rows.append(
                    _row(
                        case=case,
                        trust=trust,
                        origin=origin,
                        field="profile_shift_coefficient",
                        gear=role,
                        value=shift,
                        reference=printed_shift[origin][0],
                        token=printed_shift[origin][1],
                        input_tolerance=0.0,
                    )
                )
            for field, depends_on_shift in COMPARED_FIELDS.items():
                symbol, key = stplus_names(field)
                entry = document[symbol if origin == "listing" else f"GEOMETRIEDATEN/{key}"]
                rows.append(
                    _row(
                        case=case,
                        trust=trust,
                        origin=origin,
                        field=field,
                        gear=role,
                        value=getattr(ours, field),
                        reference=_per_gear(entry["numbers"], gear),
                        token=_per_gear(entry[tokens], gear),
                        input_tolerance=sensitivity[depends_on_shift] * shift_rounding,
                    )
                )
    return tuple(rows)


# --- pair geometry (increment 2) ------------------------------------------------------------------
#
# Pair quantities are differences and quotients of larger numbers (h_w = (d_a1 + d_a2) / 2 - a_w,
# alpha_wt from an arc cosine, zeta near the base circle). The accuracy of a single-precision
# result is then set by the magnitude of the operands, not of the result. The arithmetic tolerance
# of a pair value is therefore a first-order error propagation: every number STplus holds (module,
# angles, centre distance, profile shift, diameters, face widths) is shifted by ``ARITHMETIC_STEPS``
# binary32 steps, the absolute changes of the value are summed, and ``ARITHMETIC_STEPS`` steps at
# the printed value are added for the final operations. Printed inputs are treated the same way
# with half a unit of their last digit (``input_tolerance``).
#
# Without a given centre distance the working pressure angle is the inverse involute of
# inv(alpha_wt). In single precision inv = tan(alpha) - alpha cancels: its error is that of
# tan(alpha_wt), which the inverse amplifies by 1 / tan^2(alpha_wt). This enters as one more
# shifted computation (x_1 shifted by the equivalent of ``ARITHMETIC_STEPS`` steps of
# tan(alpha_wt) in Eq. (55)).

# compared field of PairGeometry -> one value per gear?
PAIR_FIELDS: dict[str, bool] = {
    "gear_ratio": False,
    "centre_distance_mm": False,
    "transverse_working_pressure_angle_deg": False,
    "sum_of_profile_shift_coefficients": False,
    "profile_shift_coefficient": True,
    "working_pitch_diameter_mm": True,
    "tip_form_diameter_mm": True,
    "active_tip_diameter_mm": True,
    "sap_diameter_mm": True,
    "common_tooth_depth_mm": False,
    "normal_pitch_mm": False,
    "transverse_pitch_mm": False,
    "transverse_contact_pitch_mm": False,
    "contact_face_width_mm": False,
    "length_of_path_of_contact_mm": False,
    "length_of_addendum_path_of_contact_mm": True,
    "transverse_contact_ratio": False,
    "overlap_ratio": False,
    "total_contact_ratio": False,
    "sliding_factor_at_tip": True,
    "specific_sliding_at_end_points": True,
}
ROLES: tuple[Role, Role] = ("pinion", "wheel")


class PairData(FrozenModel):
    """The numbers of one comparison: what STplus computed the pair from.

    ``values`` holds every number by name (m_n, alpha_n, beta, a_w, x_1, x_2, d_a1, d_a2, d_Fa1,
    d_Fa2, d_Ff1, d_Ff2, b_1, b_2; absent = follows from the others). ``printed`` names those
    taken from an STplus output, with half a unit of their last printed digit.
    """

    pair: PairInput
    values: dict[str, float]
    printed: dict[str, float]


def _printed(
    document: dict[str, Any], origin: Origin, field: str, gear: int
) -> tuple[float, float]:
    symbol, key = stplus_names(field)
    entry = document[symbol if origin == "listing" else f"GEOMETRIEDATEN/{key}"]
    token = _per_gear(entry["tokens" if origin == "listing" else "values"], gear)
    return _per_gear(entry["numbers"], gear), printed_tolerance(printed_decimals(token))


def pair_data(case: str) -> PairData:
    """The pair as STplus computed it: values of ``input.ste`` where STplus used them, values of
    its most precise output elsewhere (the nominal profile shift coefficient x_1 it prints for a
    file that gives span measurements only, tip diameters STplus chose itself, tip form diameters
    generated by an edge break flank of the tool, root form diameters of the generation).

    How STplus arrives at the nominal x_1 of a file with spans is not reproduced here; it
    belongs to the inspection dimensions (DIN 21773, increment 4)."""
    imported = pair_input_from_ste(load_ste(stplus_input_path(case)))
    pair = imported.pair
    origin: Origin = "interface" if has_stplus(case, "interface") else "listing"
    document = load_stplus(case, "interface" if origin == "interface" else "geometry")
    values: dict[str, float] = {
        "m_n": pair.normal_module_mm,
        "alpha_n": pair.normal_pressure_angle_deg,
        "beta": pair.helix_angle_deg,
    }
    printed: dict[str, float] = {}
    shifts = [gear.profile_shift_coefficient for gear in pair.gears.as_tuple()]
    needed: tuple[int, ...] = (0, 1)
    if pair.centre_distance_mm is not None:
        values["a_w"] = pair.centre_distance_mm
        # ADR-107: with a centre distance one coefficient is given and the other follows. Where
        # the file gives none (span measurements), x_1 is taken from the STplus output
        needed = (1,) if shifts[0] is None and shifts[1] is not None else (0,)
    for index, gear in enumerate(pair.gears.as_tuple()):
        number = index + 1
        values[f"b_{number}"] = gear.face_width_mm
        if index in needed:
            if gear.profile_shift_coefficient is not None:
                values[f"x_{number}"] = gear.profile_shift_coefficient
            else:
                values[f"x_{number}"], printed[f"x_{number}"] = _printed(
                    document, origin, PROFILE_SHIFT_FIELD, index
                )
        if gear.tip_diameter_mm is not None and not imported.preset_tip_diameters[index]:
            values[f"d_a{number}"] = gear.tip_diameter_mm
        else:
            # no KOPFKREISDM in the file: STplus presets the tip circle and may shorten it
            values[f"d_a{number}"], printed[f"d_a{number}"] = _printed(
                document, origin, "tip_diameter_mm", index
            )
        form, tolerance = _printed(document, origin, "tip_form_diameter_mm", index)
        from_chamfer = values[f"d_a{number}"] - 2.0 * gear.tip_chamfer_radial_mm
        if abs(form - from_chamfer) > tolerance + printed.get(f"d_a{number}", 0.0) + 1.0e-9:
            # the tool broke the tip edge: d_Fa is a result of the generation
            values[f"d_Fa{number}"], printed[f"d_Fa{number}"] = form, tolerance
        values[f"d_Ff{number}"], printed[f"d_Ff{number}"] = _printed(
            document, origin, "root_form_diameter_mm", index
        )
    return PairData(pair=pair, values=values, printed=printed)


def compute_pair_from_data(data: PairData, values: dict[str, float]) -> PairGeometry:
    """The pair geometry for one set of numbers (``values`` replaces ``data.values``)."""
    gears = []
    for index, gear in enumerate(data.pair.gears.as_tuple()):
        number = index + 1
        gears.append(
            gear.model_copy(
                update={
                    "span": None,
                    "ball_dimension": None,
                    "span_allowance_um": None,
                    "profile_shift_coefficient": values.get(f"x_{number}"),
                    "tip_diameter_mm": values[f"d_a{number}"],
                    "face_width_mm": values[f"b_{number}"],
                }
            )
        )
    pair = data.pair.model_copy(
        update={
            "normal_module_mm": values["m_n"],
            "normal_pressure_angle_deg": values["alpha_n"],
            "helix_angle_deg": values["beta"],
            "centre_distance_mm": values.get("a_w"),
            "gears": Pair(pinion=gears[0], wheel=gears[1]),
        }
    )
    form: Pair[float] | None = None
    if "d_Fa1" in values or "d_Fa2" in values:
        chamfer = [gear.tip_chamfer_radial_mm for gear in gears]
        form = Pair(
            pinion=values.get("d_Fa1", values["d_a1"] - 2.0 * chamfer[0]),
            wheel=values.get("d_Fa2", values["d_a2"] - 2.0 * chamfer[1]),
        )
    return compute_pair_geometry(
        pair,
        root_form_diameter_mm=Pair(pinion=values["d_Ff1"], wheel=values["d_Ff2"]),
        tip_form_diameter_mm=form,
    )


def _pair_value(result: PairGeometry, field: str, gear: int) -> float:
    value = getattr(result, field)
    return float(value.as_tuple()[gear]) if isinstance(value, Pair) else float(value)


def _is_input(data: PairData, field: str, gear: int) -> bool:
    """True if the compared field was an input of the comparison for this gear."""
    number = gear + 1
    if field == PROFILE_SHIFT_FIELD:
        return f"x_{number}" in data.values
    if field == "centre_distance_mm":
        return "a_w" in data.values
    if field == "tip_form_diameter_mm":
        return f"d_Fa{number}" in data.values
    return False


def compare_pair_geometry(case: str) -> tuple[ParityRow, ...]:
    """Compare the pair geometry of a packaged STplus case, value by value.

    Tolerances per value: half a unit of the last printed digit; the arithmetic tolerance from
    the error propagation described above; the input tolerance from the rounding of the inputs
    taken from an STplus output.
    """
    trust = str(load_stplus(case, "meta")["trust"])
    data = pair_data(case)
    ours = compute_pair_from_data(data, data.values)
    by_rounding = [
        compute_pair_from_data(data, {**data.values, name: data.values[name] + half_unit})
        for name, half_unit in data.printed.items()
    ]
    by_arithmetic = [
        compute_pair_from_data(
            data, {**data.values, name: value + ARITHMETIC_STEPS * binary32_step(value)}
        )
        for name, value in data.values.items()
        if value != 0.0
    ]
    if "a_w" not in data.values:
        teeth = sum(gear.number_of_teeth for gear in data.pair.gears.as_tuple())
        tangent = math.tan(math.radians(ours.transverse_working_pressure_angle_deg))
        involute = ARITHMETIC_STEPS * binary32_step(tangent)
        shift = teeth * involute / (2.0 * math.tan(math.radians(data.values["alpha_n"])))
        by_arithmetic.append(
            compute_pair_from_data(data, {**data.values, "x_1": data.values["x_1"] + shift})
        )
    outputs: list[tuple[Origin, dict[str, Any], str]] = [
        ("listing", load_stplus(case, "geometry"), "tokens")
    ]
    if has_stplus(case, "interface"):
        outputs.append(("interface", load_stplus(case, "interface"), "values"))

    rows: list[ParityRow] = []
    for field, per_gear in PAIR_FIELDS.items():
        symbol, key = stplus_names(field)
        field_symbol, field_unit = _symbol_and_unit(PairGeometry, field)
        for gear in range(2 if per_gear else 1):
            if _is_input(data, field, gear):
                continue  # an input of the comparison is no result of gearcore
            value = _pair_value(ours, field, gear)
            rounding = sum(abs(_pair_value(o, field, gear) - value) for o in by_rounding)
            propagated = sum(abs(_pair_value(o, field, gear) - value) for o in by_arithmetic)
            for origin, document, tokens in outputs:
                entry = document[symbol if origin == "listing" else f"GEOMETRIEDATEN/{key}"]
                reference = _per_gear(entry["numbers"], gear)
                token = _per_gear(entry[tokens], gear)
                print_tol = printed_tolerance(printed_decimals(token))
                arithmetic_tol = propagated + ARITHMETIC_STEPS * binary32_step(reference)
                rows.append(
                    ParityRow(
                        case=case,
                        trust=trust,
                        origin=origin,
                        field=field,
                        symbol=field_symbol,
                        unit=field_unit,
                        gear=ROLES[gear],
                        gearcore_value=value,
                        stplus_value=reference,
                        stplus_token=token,
                        difference=value - reference,
                        print_tolerance=print_tol,
                        arithmetic_tolerance=arithmetic_tol,
                        input_tolerance=rounding,
                        verdict=_verdict(value - reference, print_tol, arithmetic_tol + rounding),
                    )
                )
    return tuple(rows)


def detection_limits(rows: Iterable[ParityRow]) -> dict[tuple[str, Origin], float]:
    """What a comparison can show: per compared field and STplus output the largest tolerance
    relative to the STplus value. A smaller relative error of gearcore would go unnoticed.

    Rows with an STplus value of zero (overlap ratio of a spur pair, a sum of profile shift
    coefficients of zero) have no relative limit and are left out.
    """
    limits: dict[tuple[str, Origin], float] = {}
    for row in rows:
        if row.stplus_value == 0.0:
            continue
        tolerance = (
            row.print_tolerance
            + row.arithmetic_tolerance
            + row.input_tolerance
            + row.solver_tolerance
        )
        key = (row.field, row.origin)
        limits[key] = max(limits.get(key, 0.0), tolerance / abs(row.stplus_value))
    return limits


def rows_repeating_an_input(case: str) -> tuple[ParityRow, ...]:
    """The rows of ``compare_pair_geometry`` whose gearcore value equals a number the comparison
    was computed from (or zero): a tip form diameter without a chamfer, an active tip diameter
    that is not limited, the contact face width, an overlap ratio of zero. Such a row tests a
    decision, not a formula."""
    given = {*pair_data(case).values.values(), 0.0}
    return tuple(row for row in compare_pair_geometry(case) if row.gearcore_value in given)


def rows_without_evidence(rows: Iterable[ParityRow]) -> tuple[ParityRow, ...]:
    """Rows whose tolerance is at least the magnitude of the STplus value: they can never be
    ``different`` and count as identical or within the accuracy of STplus without saying anything
    about the formula (a form over-dimension of a few micrometres against the accuracy of the
    STplus form circles)."""
    return tuple(
        row
        for row in rows
        if row.print_tolerance
        + row.arithmetic_tolerance
        + row.input_tolerance
        + row.solver_tolerance
        >= abs(row.stplus_value)
    )


# --- tool-based generation (increment 3) ------------------------------------------------------------
#
# The generation is computed from the pair of ``input.ste`` with the tooth thickness allowances
# STplus printed (it takes them from a DIN 3967 series, increment 5): STplus prints the transverse
# allowance A_ste = E_sns / cos(beta) (registry note of ``tooth_thickness_allowance``), so the
# normal allowance of the contract is the printed value times cos(beta). The tip diameters follow
# ``pair_data``. Tip form and root form diameters are results here, not inputs.
#
# Tolerances as for the pair geometry: half a unit of the last printed digit, the error
# propagation of every number STplus holds (inputs of the file and the tool factors shifted by
# ``ARITHMETIC_STEPS`` binary32 steps), the rounding of printed inputs. One more part for the
# form circles: STplus determines the root form diameter (and the tip form diameter of an edge
# break) as the junction of two curves found numerically, not by a closed formula. Evidence
# (2026-09-30, ``test_stplus_parity``): the junction is a dedicated vertex of its contour export
# (d_Ff / 2 equals a vertex radius within 4e-5 mm on all 14 own runs, the vertex is doubled),
# while its curves agree with gearcore's within 0,6 um. A tangential junction found with a normal
# tolerance e lies within sqrt(2 e / delta kappa) along the curves, so a tolerance of a tenth of
# a micrometre moves the junction by micrometres. Measured against Eq. (128) and the exact
# intersection: up to 6,4 um (diametral) over the 36 gears of the 18 cases. The comparison
# therefore allows ``FORM_CIRCLE_ACCURACY_MM`` for d_Ff and d_Fa as the accuracy of the STplus
# value and half of it for c_F and h_K, their radial halves; the measured maxima are pinned.
# The manual documents the iteration limit behind it (p. 227, control BOGENDIFFERENZ): STplus
# takes two tooth thickness arcs as equal where they differ by less than m_n / 10 000. At its
# printed d_Ff of the four undercut pinions the arcs of fillet and involute differ by 1,0 to
# 4,0 times that limit. Confirmed by experiment (2026-10-03): with the limit tightened to
# m_n / 20 000 and m_n / 50 000 the d_Ff STplus prints for the undercut pinion of fzg_c moves
# from 6,4 um to 2,6 um and 0,7 um above gearcore's intersection (probes form_circle_limit_*,
# GEN-06).

GENERATION_FIELDS: tuple[str, ...] = (
    "generating_profile_shift_coefficient",
    "generated_root_diameter_mm",
    "root_form_diameter_mm",
    "tip_form_diameter_mm",
    "tip_chamfer_radial_mm",
    "residual_tip_thickness_mm",
    "normal_tip_tooth_thickness_mm",
    "tooth_depth_mm",
    "addendum_mm",
)
GENERATION_PAIR_FIELDS: tuple[str, ...] = ("tip_clearance_mm", "form_over_dimension_mm")
ALLOWANCE_KEYS = (("A_ste", "OBERES_ZAHNDICKENABM"), ("A_sti", "UNTERES_ZAHNDICKENABM"))
"""Listing symbol and interface key of the upper and the lower tooth thickness allowance."""
FORM_CIRCLE_ACCURACY_MM = 0.007
"""Accuracy of a form diameter STplus finds as the numerical junction of two curves (measured:
up to 0,0064 mm, see the module comment above and ``test_stplus_parity``)."""
NUMERICAL_FORM_CIRCLES: dict[str, float] = {
    "root_form_diameter_mm": 1.0,
    "tip_form_diameter_mm": 1.0,
    "form_over_dimension_mm": 0.5,
    "tip_chamfer_radial_mm": 0.5,
}
"""Fields STplus determines numerically, with the factor of ``FORM_CIRCLE_ACCURACY_MM`` that enters."""


class GenerationData(FrozenModel):
    """The numbers of one comparison of the generation (see ``PairData``).

    ``values`` holds m_n, alpha_n, beta, a_w or x_1/x_2, d_a1, d_a2, the normal allowances E_sns1,
    E_sni1, E_sns2, E_sni2 in micrometres and the tool factors h_aP0*, rho_aP0*, h_FfP0*,
    h_fP0*, alpha_kP per gear as the importer completed them like STplus; ``printed`` the
    rounding of values taken from an STplus output.
    """

    pair: PairInput
    values: dict[str, float]
    printed: dict[str, float]


def _allowance(
    document: dict[str, Any], origin: Origin, gear: int
) -> tuple[tuple[float, float], tuple[float, float]]:
    """((E_sns, E_sni) in mm as printed (transverse), (half units))."""
    values, roundings = [], []
    for symbol, key in ALLOWANCE_KEYS:
        entry = document[symbol if origin == "listing" else f"GEOMETRIEDATEN/{key}"]
        token = _per_gear(entry["tokens" if origin == "listing" else "values"], gear)
        values.append(float(_per_gear(entry["numbers"], gear)))
        roundings.append(printed_tolerance(printed_decimals(token)))
    return (values[0], values[1]), (roundings[0], roundings[1])


def generation_data(case: str) -> GenerationData:
    """The pair as STplus generated it: the file's values where STplus used them, the printed
    allowances (transverse, converted to the normal allowance of the contract), the printed tip
    diameters where STplus chose them."""
    base = pair_data(case)
    pair = base.pair
    origin: Origin = "interface" if has_stplus(case, "interface") else "listing"
    document = load_stplus(case, "interface" if origin == "interface" else "geometry")
    values = {k: v for k, v in base.values.items() if not k.startswith(("d_Fa", "d_Ff"))}
    printed = {k: v for k, v in base.printed.items() if not k.startswith(("d_Fa", "d_Ff"))}
    cos_beta = math.cos(math.radians(pair.helix_angle_deg))
    for index, gear in enumerate(pair.gears.as_tuple()):
        number = index + 1
        (upper, lower), (upper_half, lower_half) = _allowance(document, origin, index)
        values[f"E_sns{number}"] = 1.0e3 * upper * cos_beta
        values[f"E_sni{number}"] = 1.0e3 * lower * cos_beta
        printed[f"E_sns{number}"] = 1.0e3 * upper_half * cos_beta
        printed[f"E_sni{number}"] = 1.0e3 * lower_half * cos_beta
        tool = gear.tool
        values[f"h_aP0*{number}"] = tool.addendum_factor
        values[f"rho_aP0*{number}"] = tool.tip_radius_factor
        if tool.root_form_height_factor is not None:
            values[f"h_FfP0*{number}"] = tool.root_form_height_factor
        if tool.dedendum_factor is not None:
            values[f"h_fP0*{number}"] = tool.dedendum_factor
        if tool.edge_break_angle_deg is not None:
            values[f"alpha_kP{number}"] = tool.edge_break_angle_deg
    return GenerationData(pair=pair, values=values, printed=printed)


def compute_generation_from_data(data: GenerationData, values: dict[str, float]) -> Any:
    """``compute_generation`` for one set of numbers (``values`` replaces ``data.values``).

    A shifted lower allowance may exceed the upper one (equal allowances in a listing); the
    contract orders them, so the lower is clipped to the upper. Only d_fEi depends on it, which
    is not compared. A tool module or angle equal to the gear's is passed as ``None`` so that a
    shifted gear module stays "the same as the gear".
    """
    from gearcore.generation import compute_generation

    gears = []
    for index, gear in enumerate(data.pair.gears.as_tuple()):
        number = index + 1
        tool_update: dict[str, Any] = {
            "addendum_factor": values[f"h_aP0*{number}"],
            "tip_radius_factor": values[f"rho_aP0*{number}"],
        }
        if f"h_FfP0*{number}" in values:
            tool_update["root_form_height_factor"] = values[f"h_FfP0*{number}"]
        if f"h_fP0*{number}" in values:
            # a tool without edge break flank keeps its dedendum on the root form height when
            # the latter is shifted (the corner of the tool, not two independent numbers)
            dedendum = values[f"h_fP0*{number}"]
            form = values.get(f"h_FfP0*{number}", dedendum)
            sharp = gear.tool.dedendum_factor == gear.tool.root_form_height_factor
            tool_update["dedendum_factor"] = form if sharp else max(dedendum, form)
        if f"alpha_kP{number}" in values:
            tool_update["edge_break_angle_deg"] = values[f"alpha_kP{number}"]
        if gear.tool.normal_module_mm == data.pair.normal_module_mm:
            tool_update["normal_module_mm"] = None
        if gear.tool.profile_angle_deg == data.pair.normal_pressure_angle_deg:
            tool_update["profile_angle_deg"] = None
        upper, lower = values[f"E_sns{number}"], values[f"E_sni{number}"]
        gears.append(
            gear.model_copy(
                update={
                    "span": None,
                    "ball_dimension": None,
                    "span_allowance_um": None,
                    "profile_shift_coefficient": values.get(f"x_{number}"),
                    "tip_diameter_mm": values[f"d_a{number}"],
                    "face_width_mm": values[f"b_{number}"],
                    "tooth_thickness_allowance_um": (upper, min(upper, lower)),
                    # the residual thickness the importer set belongs to the gear without
                    # allowance; with the allowances of STplus it is the caller's to state
                    "residual_tip_thickness_mm": None,
                    "tool": gear.tool.model_copy(update=tool_update),
                }
            )
        )
    pair = data.pair.model_copy(
        update={
            "normal_module_mm": values["m_n"],
            "normal_pressure_angle_deg": values["alpha_n"],
            "helix_angle_deg": values["beta"],
            "centre_distance_mm": values.get("a_w"),
            "gears": Pair(pinion=gears[0], wheel=gears[1]),
        }
    )
    return compute_generation(pair)


def _generation_value(result: Any, field: str, gear: int) -> float | None:
    if field in GENERATION_PAIR_FIELDS:
        return float(getattr(result, field).as_tuple()[gear])
    value = getattr(result.gears.as_tuple()[gear], field)
    return None if value is None else float(value)


def _stplus_keys(field: str) -> tuple[str | None, str | None]:
    entry, _ = quantity_of_field(field)
    names = entry.stplus
    if names is None:
        return None, None
    return names.symbol, names.interface_key


def compare_generation(case: str) -> tuple[ParityRow, ...]:
    """Compare the tool-based generation of a packaged STplus case, value by value.

    The residual tip thickness is compared with RESTDICKE where gearcore reports one (a chamfer
    generated by the tool); STplus prints the tip tooth thickness there without a chamfer, which
    ``test_stplus_parity`` checks separately. A chamfer given as an input has its residual
    thickness from the rule of STplus (0,7 h_K tangential in the normal section), which is no
    result of the generation; ``tests/test_stplus_reading.py`` checks that rule on its own.
    """
    trust = str(load_stplus(case, "meta")["trust"])
    data = generation_data(case)
    ours = compute_generation_from_data(data, data.values)
    by_rounding = [
        compute_generation_from_data(data, {**data.values, name: data.values[name] + half_unit})
        for name, half_unit in data.printed.items()
    ]
    by_arithmetic = [
        compute_generation_from_data(
            data, {**data.values, name: value + ARITHMETIC_STEPS * binary32_step(value)}
        )
        for name, value in data.values.items()
        if value != 0.0
    ]
    if "a_w" not in data.values:
        teeth = sum(gear.number_of_teeth for gear in data.pair.gears.as_tuple())
        tangent = math.tan(math.radians(ours.pair_geometry.transverse_working_pressure_angle_deg))
        involute = ARITHMETIC_STEPS * binary32_step(tangent)
        shift = teeth * involute / (2.0 * math.tan(math.radians(data.values["alpha_n"])))
        by_arithmetic.append(
            compute_generation_from_data(data, {**data.values, "x_1": data.values["x_1"] + shift})
        )
    outputs: list[tuple[Origin, dict[str, Any], str]] = [
        ("listing", load_stplus(case, "geometry"), "tokens")
    ]
    if has_stplus(case, "interface"):
        outputs.append(("interface", load_stplus(case, "interface"), "values"))

    rows: list[ParityRow] = []
    for field in (*GENERATION_FIELDS, *GENERATION_PAIR_FIELDS):
        symbol, key = _stplus_keys(field)
        model = GenerationResult if field in GENERATION_PAIR_FIELDS else GearGeneration
        field_symbol, field_unit = _symbol_and_unit(model, field)
        for gear in range(2):
            generated = ours.gears.as_tuple()[gear]
            if (
                field in ("tip_chamfer_radial_mm", "tip_form_diameter_mm")
                and generated.tool_edge_break_angle_deg is None
            ):
                continue  # an input, or Eq. (127) of an input chamfer (an echo of d_a and h_K)
            if field == "residual_tip_thickness_mm" and (
                generated.residual_tip_thickness_mm is None
                or generated.tool_edge_break_angle_deg is None
            ):
                continue  # no chamfer, or the shape of a given chamfer (STplus default)
            value = _generation_value(ours, field, gear)
            if value is None:
                continue
            rounding = sum(
                abs((_generation_value(o, field, gear) or 0.0) - value) for o in by_rounding
            )
            propagated = sum(
                abs((_generation_value(o, field, gear) or 0.0) - value) for o in by_arithmetic
            )
            solver = NUMERICAL_FORM_CIRCLES.get(field, 0.0) * FORM_CIRCLE_ACCURACY_MM
            for origin, document, tokens in outputs:
                name = symbol if origin == "listing" else key
                if name is None:
                    continue
                entry = document.get(name if origin == "listing" else f"GEOMETRIEDATEN/{name}")
                if entry is None:
                    continue
                reference = _per_gear(entry["numbers"], gear)
                token = _per_gear(entry[tokens], gear)
                print_tol = printed_tolerance(printed_decimals(token))
                arithmetic_tol = propagated + ARITHMETIC_STEPS * binary32_step(reference)
                rows.append(
                    ParityRow(
                        case=case,
                        trust=trust,
                        origin=origin,
                        field=field,
                        symbol=field_symbol,
                        unit=field_unit,
                        gear=ROLES[gear],
                        gearcore_value=value,
                        stplus_value=reference,
                        stplus_token=token,
                        difference=value - reference,
                        print_tolerance=print_tol,
                        arithmetic_tolerance=arithmetic_tol,
                        input_tolerance=rounding,
                        solver_tolerance=solver,
                        verdict=_verdict(
                            value - reference, print_tol, arithmetic_tol + rounding + solver
                        ),
                    )
                )
    return tuple(rows)


# --- inspection dimensions (increment 4) ------------------------------------------------------------
#
# STplus prints the inspection dimensions of the nominal gear ("Nennmass") with their allowances,
# and the circles on which the measuring pieces touch for the gear at its upper allowance. The
# number of teeth spanned and the diameter of the measuring ball are choices of the program by
# rules that are not those of the norm (``stplus_program.stplus_number_of_teeth_spanned``,
# ``stplus_measuring_ball_diameter``, see ``norm_map.md``): the comparison computes both by these
# rules, compares them with the listing and computes the dimensions with them. STplus measures
# the chord on the middle of the form circles
# (``stplus_program.stplus_chord_diameter``), which it finds numerically: the diameter of that
# cylinder is compared within the accuracy of the form circles, the chord and its height on the
# cylinder the listing prints, so that both are compared as sharply as every other dimension.

INSPECTION_ROWS: tuple[tuple[str, str, str | None, str | None], ...] = (
    # (row name, contract field, listing symbol or label, interface key)
    ("number_of_teeth_spanned", "number_of_teeth_spanned", "k", None),
    ("measuring_ball_diameter_mm", "measuring_ball_diameter_mm", "D_M", None),
    ("span_measurement_mm", "span_measurement_mm", "W_k", "ZAHNWEITE"),
    ("span_measurement_mm: upper - nominal", "span_measurement_mm", "A_We", "OBERES_ZAHNWEITENABM"),
    (
        "span_measurement_mm: lower - nominal",
        "span_measurement_mm",
        "A_Wi",
        "UNTERES_ZAHNWEITENABM",
    ),
    (
        "span_measuring_circle_diameter_mm",
        "span_measuring_circle_diameter_mm",
        "Beruehrkreisdurchm. (Zahnweitenmessg.)",
        "BERUEHRKREISDM_ZAHNW",
    ),
    ("span_allowance_factor", "span_allowance_factor", "A_W/A_Sn", "ZAHNWEITENABMASSFAKTOR"),
    (
        "diametral_two_ball_dimension_mm",
        "diametral_two_ball_dimension_mm",
        "M_dK",
        "DIAMETR_ZWEIKUGELMASS",
    ),
    (
        "diametral_two_ball_dimension_mm: upper - nominal",
        "diametral_two_ball_dimension_mm",
        "A_Mde",
        "OBERES_DIAMETR_ABMASS",
    ),
    (
        "diametral_two_ball_dimension_mm: lower - nominal",
        "diametral_two_ball_dimension_mm",
        "A_Mdi",
        "UNTERES_DIAMETR_ABMASS",
    ),
    (
        "ball_measuring_circle_diameter_mm",
        "ball_measuring_circle_diameter_mm",
        "Beruehrkreisdurchmesser (Kugel/Flanke)",
        "BERUEHRKREISDM_ZWEIK",
    ),
    ("diametral_two_roller_dimension_mm", "diametral_two_roller_dimension_mm", "M_dR", None),
    ("y_diameter_mm", "y_diameter_mm", "Beruehrkreisdurchm. (oberes Abmass)", "BERUEHRKREISDURCHM"),
    (
        "chordal_tooth_thickness_at_y_mm",
        "chordal_tooth_thickness_at_y_mm",
        "s_n-",
        "ZAHNDICKENSEHNE",
    ),
    ("height_above_chord_at_y_mm", "height_above_chord_at_y_mm", "h_a-", "HOEHE_UEBER_ZAHNSEHNE"),
)
"""What is compared: name of the row, the contract field it belongs to, and where STplus prints
it (key of the listing document, key of the interface file)."""

INSPECTION_FORM_CIRCLES: dict[str, float] = {"y_diameter_mm": 1.0}
"""Rows that depend on the form circles STplus finds numerically, with the factor of
``FORM_CIRCLE_ACCURACY_MM`` that enters: the chord cylinder is the middle of d_Ff and d_Fa (both
may be numerical: factor 1 for the diameter)."""
CHORD_CYLINDER = "Beruehrkreisdurchm. (oberes Abmass)"
"""Listing label of the cylinder on which STplus measures the chord."""
INSPECTION_ON_PRINTED_CYLINDER: tuple[str, ...] = (
    "chordal_tooth_thickness_at_y_mm",
    "height_above_chord_at_y_mm",
)
"""Rows computed on the chord cylinder the listing prints (its printed rounding enters)."""


def printed_chord_cylinders(case: str) -> tuple[tuple[float, float], tuple[float, float]]:
    """(d_y per gear, half a unit of its last printed digit per gear) of the cylinder on which
    the listing of the case gives the chord."""
    entry = load_stplus(case, "geometry")[CHORD_CYLINDER]
    return (
        (float(_per_gear(entry["numbers"], 0)), float(_per_gear(entry["numbers"], 1))),
        (
            printed_tolerance(printed_decimals(_per_gear(entry["tokens"], 0))),
            printed_tolerance(printed_decimals(_per_gear(entry["tokens"], 1))),
        ),
    )


def compute_inspection_from_data(
    data: GenerationData,
    values: dict[str, float],
    choices: tuple[tuple[int, int], tuple[float, float]] | None = None,
    chord_diameter_mm: tuple[float, float] | None = None,
) -> Any:
    """``compute_inspection`` for one set of numbers, with the k and D_M of ``choices`` (without
    them: as STplus chooses for these numbers) and the chord on the given cylinders (without
    them: on the cylinder of the rule of STplus)."""
    from gearcore.inspection import compute_inspection
    from gearcore.stplus_program import stplus_chord_diameter, with_stplus_inspection_choices

    generation = with_stplus_inspection_choices(compute_generation_from_data(data, values), choices)
    chords: Pair[float] = (
        Pair(pinion=chord_diameter_mm[0], wheel=chord_diameter_mm[1])
        if chord_diameter_mm is not None
        else Pair(
            pinion=stplus_chord_diameter(
                generation.gears.pinion.root_form_diameter_mm,
                generation.gears.pinion.tip_form_diameter_mm,
            ),
            wheel=stplus_chord_diameter(
                generation.gears.wheel.root_form_diameter_mm,
                generation.gears.wheel.tip_form_diameter_mm,
            ),
        )
    )
    return compute_inspection(generation, chord_diameter_mm=chords)


def _inspection_value(result: Any, row: str, gear: int) -> float | None:
    inspected = result.gears.as_tuple()[gear]
    field, _, part = row.partition(": ")
    value = getattr(inspected, field)
    if value is None:
        return None
    if isinstance(value, int | float):
        return float(value)
    if part == "upper - nominal":
        return float(value.upper - value.nominal)
    if part == "lower - nominal":
        return float(value.lower - value.nominal)
    return float(value.nominal)


def _shifted_inspection_value(result: Any, row: str, gear: int) -> float:
    """The value of a run with a shifted input; a run that loses the value would turn the whole
    value into a tolerance."""
    value = _inspection_value(result, row, gear)
    if value is None:
        raise ParseError(f"{row}: a shifted input leaves the value of gear {gear + 1} undefined")
    return value


def compare_inspection(case: str) -> tuple[ParityRow, ...]:
    """Compare the inspection dimensions of a packaged STplus case, value by value.

    Not compared, because STplus defines them differently (``expected_differences.yaml``): the
    allowance factor of the ball dimension (STplus prints the ratio of its upper allowances,
    the norm the derivative) and the allowance of the chord (STplus prints the tooth thickness
    allowance itself).
    """
    from gearcore.models.results import GearInspection

    trust = str(load_stplus(case, "meta")["trust"])
    data = generation_data(case)

    def shifted(name: str, amount: float) -> dict[str, float]:
        # a lower allowance is shifted downwards: shifted upwards it would pass an equal upper
        # allowance and be clipped to it, and the lower limits would not move at all
        sign = -1.0 if name.startswith("E_sni") else 1.0
        return {**data.values, name: data.values[name] + sign * amount}

    # (k and D_M are whole choices: they are made once, for the numbers as printed, and held
    # while the numbers are shifted)
    from gearcore.stplus_program import stplus_inspection_choices

    choices = stplus_inspection_choices(compute_generation_from_data(data, data.values))

    def computed(chords: tuple[float, float] | None) -> tuple[Any, list[Any], list[Any]]:
        """The result, and the results with each number shifted by its printed rounding and by
        the single-precision steps of STplus."""
        return (
            compute_inspection_from_data(data, data.values, choices, chords),
            [
                compute_inspection_from_data(data, shifted(name, half_unit), choices, chords)
                for name, half_unit in data.printed.items()
            ],
            [
                compute_inspection_from_data(
                    data, shifted(name, ARITHMETIC_STEPS * binary32_step(value)), choices, chords
                )
                for name, value in data.values.items()
                if value != 0.0
            ],
        )

    by_rule = computed(None)
    cylinders, half_units = printed_chord_cylinders(case)
    on_printed = computed(cylinders)
    for gear in range(2):
        for results, amount in (
            (on_printed[1], half_units[gear]),
            (on_printed[2], ARITHMETIC_STEPS * binary32_step(cylinders[gear])),
        ):
            moved = [cylinders[0], cylinders[1]]
            moved[gear] += amount
            results.append(
                compute_inspection_from_data(data, data.values, choices, (moved[0], moved[1]))
            )
    outputs: list[tuple[Origin, dict[str, Any], str]] = [
        ("listing", load_stplus(case, "geometry"), "tokens")
    ]
    if has_stplus(case, "interface"):
        outputs.append(("interface", load_stplus(case, "interface"), "values"))

    rows: list[ParityRow] = []
    for row, field, symbol, key in INSPECTION_ROWS:
        field_symbol, field_unit = _symbol_and_unit(GearInspection, field)
        _, _, part = row.partition(": ")
        shown = f"{field_symbol} ({part})" if part else field_symbol
        ours, by_rounding, by_arithmetic = (
            on_printed if row in INSPECTION_ON_PRINTED_CYLINDER else by_rule
        )
        for gear in range(2):
            value = _inspection_value(ours, row, gear)
            if value is None:
                continue
            rounding = sum(
                abs(_shifted_inspection_value(o, row, gear) - value) for o in by_rounding
            )
            propagated = sum(
                abs(_shifted_inspection_value(o, row, gear) - value) for o in by_arithmetic
            )
            solver = INSPECTION_FORM_CIRCLES.get(row, 0.0) * FORM_CIRCLE_ACCURACY_MM
            if part:
                # an allowance is the difference of two dimensions STplus holds in single
                # precision: the spacing of both enters, not that of the small difference
                limits = getattr(ours.gears.as_tuple()[gear], field)
                limit = limits.upper if part.startswith("upper") else limits.lower
                propagated += ARITHMETIC_STEPS * (
                    binary32_step(limits.nominal) + binary32_step(limit)
                )
            for origin, document, tokens in outputs:
                name = symbol if origin == "listing" else key
                if name is None:
                    continue
                entry = document.get(name if origin == "listing" else f"GEOMETRIEDATEN/{name}")
                if entry is None:
                    continue
                reference = _per_gear(entry["numbers"], gear)
                token = _per_gear(entry[tokens], gear)
                print_tol = printed_tolerance(printed_decimals(token))
                arithmetic_tol = propagated + ARITHMETIC_STEPS * binary32_step(reference)
                rows.append(
                    ParityRow(
                        case=case,
                        trust=trust,
                        origin=origin,
                        field=row,
                        symbol=shown,
                        unit=field_unit,
                        gear=ROLES[gear],
                        gearcore_value=value,
                        stplus_value=reference,
                        stplus_token=token,
                        difference=value - reference,
                        print_tolerance=print_tol,
                        arithmetic_tolerance=arithmetic_tol,
                        input_tolerance=rounding,
                        solver_tolerance=solver,
                        verdict=_verdict(
                            value - reference, print_tol, arithmetic_tol + rounding + solver
                        ),
                    )
                )
    return tuple(rows)
