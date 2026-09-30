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
from gearcore.models.results import BasicGearGeometry, PairGeometry
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
    pair = pair_input_from_ste(load_ste(stplus_input_path(case))).pair
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
        if gear.tip_diameter_mm is not None:
            values[f"d_a{number}"] = gear.tip_diameter_mm
        else:
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
        tolerance = row.print_tolerance + row.arithmetic_tolerance + row.input_tolerance
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
