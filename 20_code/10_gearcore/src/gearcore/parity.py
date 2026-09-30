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
from enum import StrEnum
from typing import Any, Literal

from gearcore._safe import finite_input
from gearcore.data import has_stplus, load_stplus, printed_tolerance, stplus_input_path
from gearcore.errors import ParseError
from gearcore.involute import compute_basic_gear_geometry
from gearcore.io.ste import load_ste, pair_input_from_ste
from gearcore.models.common import FrozenModel
from gearcore.models.results import BasicGearGeometry
from gearcore.quantities import quantity_of_field

ARITHMETIC_STEPS = 2.0
"""Accuracy of a value STplus computed, in binary32 steps (largest deviation observed: 1.5)."""

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
    extra = BasicGearGeometry.model_fields[field].json_schema_extra
    assert isinstance(extra, dict)
    by_magnitude = origin == "listing" and field in _MAGNITUDE_IN_LISTING
    difference = abs(value) - abs(reference) if by_magnitude else value - reference
    print_tol = printed_tolerance(printed_decimals(token))
    arithmetic_tol = ARITHMETIC_STEPS * binary32_step(reference)
    return ParityRow(
        case=case,
        trust=trust,
        origin=origin,
        field=field,
        symbol=str(extra["symbol"]),
        unit=str(extra["unit"]),
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

    Where STplus uses the profile shift coefficient of ``input.ste`` (x1 always, x2 if no centre
    distance is given), gearcore computes with that input and the printed x is compared as a
    quantity of its own. Where STplus derived x (span measurement, centre distance), gearcore
    computes with the printed x and its rounding enters ``input_tolerance`` of the thickness
    quantities.
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
        # STplus takes x1 as given; with a centre distance it derives x2 from a and overrides a
        # given x2 (kst-E: input 0.3143, used 0.31433)
        shift_is_input = gear_input.profile_shift_coefficient is not None and (
            gear == 0 or pair.centre_distance_mm is None
        )
        shift = gear_input.profile_shift_coefficient if shift_is_input else printed_shift[best][0]
        assert shift is not None
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
