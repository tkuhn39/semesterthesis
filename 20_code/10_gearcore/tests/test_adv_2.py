"""Regression tests of the adversarial gate of increment 2 (pair geometry).

Second part: findings G2V-xx of the verification review of the fixes.

Findings G2A-xx (formulas, guards, tests) and G2B-xx (comparison with STplus, importer, registry,
documentation) of ``gate_reports/increment_2.md``.
"""

import importlib.util
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError
from test_pair import CASES, REFERENCE, base_diameters, close, make_pair, working_angle

from gearcore import inspection as ins
from gearcore import involute as iv
from gearcore import pair as pr
from gearcore._safe import EPS
from gearcore.data import has_stplus, load_stplus, stplus_case_dirs
from gearcore.errors import (
    GearCoreError,
    GeometryInfeasibleError,
    InputRangeError,
    NotSupportedError,
    ParseError,
)
from gearcore.io.ste import (
    ABSENT_MEANS_NONE,
    material_from_section,
    pair_input_from_ste,
    parse_ste,
    tool_from_section,
)
from gearcore.models.common import Pair
from gearcore.models.inputs import (
    DimensionKind,
    GearInput,
    GearKind,
    MaterialKind,
    PairInput,
    SpanMeasurement,
    ToolProfile,
)
from gearcore.models.results import PairGeometry
from gearcore.parity import (
    PAIR_FIELDS,
    ParityVerdict,
    compare_basic_geometry,
    compare_pair_geometry,
    compute_pair_from_data,
    detection_limits,
    pair_data,
    rows_repeating_an_input,
)
from gearcore.quantities import quantity

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"

# decimal references of scripts/decimal_reference_pair.py: case B with root form circles
LIMITED: dict[str, dict[str, float]] = {
    "D": {  # d_Ff = 22,9 / 78,4: both gears limited (Eq. (66) to (69))
        "d_Nf1": 22.9,
        "d_Nf2": 78.4,
        "d_Na1": 27.3838996158237,
        "d_Na2": 82.42948115276994,
        "g_alpha": 5.779446162989436,
        "g_a1": 3.406310863161494,
        "g_a2": 2.373135299827942,
        "eps_alpha": 0.9788599003831299,
        "K_ga1": 0.36627503082542323,
        "K_ga2": 0.25517935385692647,
        "zeta_f1": -1.5528009180992495,
        "zeta_f2": -1.32659469872301,
    },
    "E": {  # d_Ff = 22,6 / 78,4: only the wheel limited (Eq. (67), (69))
        "d_Nf1": 22.653576724323237,
        "d_Nf2": 78.4,
        "d_Na1": 27.3838996158237,
        "d_Na2": 83.2,
        "g_alpha": 6.698082056287458,
        "g_a1": 3.406310863161494,
        "g_a2": 3.291771193125964,
        "eps_alpha": 1.1344484833792812,
        "K_ga1": 0.36627503082542323,
        "K_ga2": 0.35395876761330414,
        "zeta_f1": -4.0062919912217305,
        "zeta_f2": -1.32659469872301,
    },
}
ROOT_FORMS = {"D": Pair(pinion=22.9, wheel=78.4), "E": Pair(pinion=22.6, wheel=78.4)}


def forced(pair: PairInput, role: str, **update: Any) -> PairInput:
    """A pair with one gear changed without validation (what ``model_copy`` lets through)."""
    gears = {"pinion": pair.gears.pinion, "wheel": pair.gears.wheel}
    gears[role] = gears[role].model_copy(update=update)
    return pair.model_copy(update={"gears": Pair(pinion=gears["pinion"], wheel=gears["wheel"])})


# --- G2A-17: the reference table has a committed generator ----------------------------------------


def test_g2a17_reference_tables_are_the_output_of_the_committed_generator() -> None:
    spec = importlib.util.spec_from_file_location(
        "decimal_reference_pair", SCRIPTS / "decimal_reference_pair.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for name in ("A", "B", "C"):
        for key, value in REFERENCE[name].items():
            assert float(module.CASES[name][key]) == value, (name, key)
    for name, table in LIMITED.items():
        for key, value in table.items():
            assert float(module.CASES[name][key]) == value, (name, key)


# --- G2A-01: internal gears --------------------------------------------------------------------------


def test_g2a01_internal_gear_kind_is_not_computed_as_external() -> None:
    pair = forced(make_pair(CASES["B"]), "wheel", kind=GearKind.INTERNAL)
    no_tips = forced(forced(pair, "pinion", tip_diameter_mm=None), "wheel", tip_diameter_mm=None)
    for call in (
        lambda: pr.compute_pair_geometry(pair),
        lambda: pr.resolve_profile_shift(pair),
        lambda: pr.with_nominal_tip_diameters(no_tips, h_aP_mm=2.0),
    ):
        with pytest.raises(NotSupportedError, match="internal gears"):
            call()


# --- G2A-02, G2B-14: start of the active profile on the base circle ----------------------------------


@pytest.mark.parametrize("m_n", [0.05, 2.0, 100.0])
def test_g2a02_active_profile_on_the_base_circle_is_rejected_at_every_size(m_n: float) -> None:
    """The criterion is relative: the same pair scaled by the module behaves the same."""
    case = {
        **CASES["B"],
        "m_n": m_n,
        "x": (0.0, 0.0),
        "b": 10.0 * m_n,
        "d_a": (14.0 * m_n, 42.0 * m_n),  # the wheel tip reaches beyond T_1
    }
    pair = make_pair(case)
    d_b1, _ = base_diameters(case)
    with pytest.raises(GeometryInfeasibleError, match="starts on the base circle"):
        pr.compute_pair_geometry(pair, root_form_diameter_mm=Pair(pinion=d_b1, wheel=38.3 * m_n))
    # a root form circle slightly above the base circle gives a finite, large specific sliding
    result = pr.compute_pair_geometry(
        pair, root_form_diameter_mm=Pair(pinion=d_b1 * 1.001, wheel=38.3 * m_n)
    )
    zeta = result.specific_sliding_at_end_points.pinion
    assert math.isfinite(zeta) and -200.0 < zeta < -5.0


@pytest.mark.parametrize("factor", [1.0 - 1e-14, 1.0, 1.0 + 1e-14])
def test_g2a02_wheel_tip_at_the_tangent_point_is_no_garbage(factor: float) -> None:
    """A wheel tip that ends at T_1 within rounding noise: typed error, never a sign-flipped or
    astronomically large specific sliding."""
    case, ref = CASES["B"], REFERENCE["B"]
    d_b1, d_b2 = base_diameters(case)
    at_tangent_point = math.hypot(2.0 * ref["T1T2"], d_b2)
    pair = make_pair({**case, "d_a": (28.0, at_tangent_point * factor)})
    with pytest.raises(GeometryInfeasibleError, match="starts on the base circle"):
        pr.compute_pair_geometry(pair)
    # clearly before the tangent point the value is finite and negative
    before = pr.compute_pair_geometry(make_pair({**case, "d_a": (28.0, at_tangent_point - 0.01)}))
    assert before.sap_diameter_mm.pinion > d_b1
    assert -1.0e4 < before.specific_sliding_at_end_points.pinion < 0.0
    # clearly beyond it Eq. (64) has no value: interference
    with pytest.raises(GeometryInfeasibleError, match="interference"):
        pr.compute_pair_geometry(make_pair({**case, "d_a": (28.0, at_tangent_point + 0.01)}))


def test_g2a11_sliding_functions_guard_their_arguments() -> None:
    with pytest.raises(InputRangeError, match="must be >= 1"):
        pr.sliding_factor_at_tip(3.0, 24.0, 0.5)
    with pytest.raises(InputRangeError, match="radii of curvature"):
        pr.specific_sliding_of_pinion(-3.0, 5.0, 2.0)
    with pytest.raises(InputRangeError, match="radii of curvature"):
        pr.specific_sliding_of_wheel(3.0, -5.0, 2.0)
    with pytest.raises(GeometryInfeasibleError):
        pr.specific_sliding_of_wheel(3.0, 0.0, 2.0)
    # relative criterion: a radius of 1e-13 of the distance T_1 T_2 counts as zero at any size
    for scale in (1e-3, 1.0, 1e3):
        with pytest.raises(GeometryInfeasibleError):
            pr.specific_sliding_of_pinion(1e-13 * scale, scale, 2.0)
    # signed sliding factor: an active tip circle inside the working pitch circle
    assert pr.sliding_factor_at_tip(-0.5, 24.0, 2.0) < 0.0


# --- G2A-03, G2A-09, G2A-15: typed errors for what bypassed the contract ------------------------------


@pytest.mark.parametrize(
    "role, update",
    [
        ("pinion", {"face_width_mm": "20"}),
        ("pinion", {"face_width_mm": None}),
        ("wheel", {"profile_shift_coefficient": "0.3"}),
        ("wheel", {"tool": None}),
        ("wheel", {"tip_diameter_mm": "83.2"}),
        ("pinion", {"tip_chamfer_radial_mm": None}),
        ("pinion", {"number_of_teeth": 12.0}),
    ],
)
def test_g2a03_gear_values_that_bypassed_validation_are_input_errors(
    role: str, update: dict[str, Any]
) -> None:
    with pytest.raises(InputRangeError):
        pr.compute_pair_geometry(forced(make_pair(CASES["B"]), role, **update))


@pytest.mark.parametrize(
    "update",
    [
        {"helix_angle_deg": "15"},
        {"helix_angle_deg": None},
        {"normal_pressure_angle_deg": None},
        {"normal_pressure_angle_deg": 1 + 2j},
        {"normal_module_mm": "2"},
        {"centre_distance_mm": "52"},
        {"gears": None},
    ],
)
def test_g2a03_pair_values_that_bypassed_validation_are_input_errors(
    update: dict[str, Any],
) -> None:
    pair = make_pair(CASES["B"]).model_copy(update=update)
    for call in (pr.compute_pair_geometry, pr.resolve_profile_shift):
        with pytest.raises(InputRangeError):
            call(pair)


def test_g2a03_optional_arguments_are_checked() -> None:
    pair = make_pair(CASES["B"])
    with pytest.raises(InputRangeError, match="a PairInput is required"):
        pr.compute_pair_geometry(pair.model_dump())  # type: ignore[arg-type]
    with pytest.raises(InputRangeError, match="must be a Pair"):
        pr.compute_pair_geometry(pair, root_form_diameter_mm=(22.7, 78.2))  # type: ignore[arg-type]
    with pytest.raises(InputRangeError, match="must be a Pair"):
        pr.compute_pair_geometry(pair, tip_form_diameter_mm=[28.0, 83.2])  # type: ignore[arg-type]
    not_finite = Pair[float].model_construct(pinion=math.nan, wheel=78.2)
    with pytest.raises(InputRangeError):
        pr.compute_pair_geometry(pair, root_form_diameter_mm=not_finite)
    with pytest.raises(InputRangeError, match="must be a Pair"):
        pr.with_nominal_tip_diameters(pair, h_aP_mm=2.0, k=(0.0, 0.0))  # type: ignore[arg-type]
    # G2A-09: the arguments are validated even if both tip diameters are given
    for wrong in ("2", math.nan, -1.0, 0.0):
        with pytest.raises(InputRangeError):
            pr.with_nominal_tip_diameters(pair, h_aP_mm=wrong)  # type: ignore[arg-type]


def test_g2a09_public_orchestrators_enforce_the_verified_range() -> None:
    case = CASES["B"]
    far = make_pair({**case, "a_w": 70.0, "x": (0.3, None), "d_a": (None, None)})
    for call in (
        lambda: pr.resolve_profile_shift(far),
        lambda: pr.with_nominal_tip_diameters(far, h_aP_mm=2.0),
        lambda: pr.compute_pair_geometry(far),
    ):
        with pytest.raises(GeometryInfeasibleError, match="follows from the centre distance"):
            call()
    given = forced(make_pair(case), "pinion", profile_shift_coefficient=5.0)
    with pytest.raises(InputRangeError, match="profile_shift_coefficient"):
        pr.resolve_profile_shift(given)


def test_g2a13_a_huge_centre_distance_is_named_in_the_error() -> None:
    """The message names what the user gave, not the working pressure angle derived from it."""
    alpha_n = math.radians(20.0)
    with pytest.raises(GeometryInfeasibleError, match="centre distance a_w = 1e\\+300"):
        pr.transverse_working_pressure_angle(12, 40, 2.0, alpha_n, 0.0, 1e300)
    huge = make_pair({**CASES["B"], "a_w": 1e300, "x": (0.3, None)})
    with pytest.raises(GeometryInfeasibleError, match="centre distance a_w"):
        pr.compute_pair_geometry(huge)


def test_g2a15_the_pinion_is_the_smaller_gear_in_the_contract() -> None:
    with pytest.raises(ValidationError, match="the pinion is the smaller gear"):
        make_pair({**CASES["B"], "z": (40, 12)})
    equal = make_pair({**CASES["B"], "z": (20, 20), "d_a": (44.8, 43.2)})
    assert pr.compute_pair_geometry(equal).gear_ratio == 1.0
    swapped = forced(forced(make_pair(CASES["B"]), "pinion", number_of_teeth=40), "wheel",
                     number_of_teeth=12)  # fmt: skip
    with pytest.raises(InputRangeError, match="the pinion is the smaller gear"):
        pr.compute_pair_geometry(swapped)
    # G2A-15: the verified ranges of the contract hold for a forced pair as well, so every
    # result passes its own contract again
    wide = forced(make_pair(CASES["B"]), "pinion", face_width_mm=5000.0)
    with pytest.raises(InputRangeError, match="face_width_mm"):
        pr.compute_pair_geometry(wide)


def test_g2a15_given_tip_form_diameter_and_chamfer_input_are_reported() -> None:
    pair = make_pair(CASES["B"], chamfer=(0.0, 0.5))
    result = pr.compute_pair_geometry(pair, tip_form_diameter_mm=Pair(pinion=28.0, wheel=82.6))
    assert result.tip_form_diameter_mm.wheel == 82.6
    assert "tip_chamfer_input_not_used" in [w.code for w in result.warnings]


# --- G2A-04, G2A-10: limit of the active profile against decimal references ---------------------------


@pytest.mark.eq("ISO21771:2014", "(66)")
@pytest.mark.eq("ISO21771:2014", "(67)")
@pytest.mark.eq("ISO21771:2014", "(68)")
@pytest.mark.eq("ISO21771:2014", "(69)")
@pytest.mark.eq("ISO21771:2014", "(83)")
@pytest.mark.eq("ISO21771:2014", "(84)")
@pytest.mark.eq("ISO21771:2014", "(116)")
@pytest.mark.eq("ISO21771:2014", "(117)")
@pytest.mark.parametrize("name", sorted(LIMITED))
def test_g2a04_limited_active_profile_against_decimal_references(name: str) -> None:
    ref = LIMITED[name]
    result = pr.compute_pair_geometry(make_pair(CASES["B"]), root_form_diameter_mm=ROOT_FORMS[name])
    assert close(result.sap_diameter_mm.pinion, ref["d_Nf1"])
    assert close(result.sap_diameter_mm.wheel, ref["d_Nf2"])
    assert close(result.active_tip_diameter_mm.pinion, ref["d_Na1"])
    assert close(result.active_tip_diameter_mm.wheel, ref["d_Na2"])
    assert close(result.length_of_path_of_contact_mm, ref["g_alpha"])
    assert close(result.length_of_addendum_path_of_contact_mm.pinion, ref["g_a1"])
    assert close(result.length_of_addendum_path_of_contact_mm.wheel, ref["g_a2"])
    assert close(result.transverse_contact_ratio, ref["eps_alpha"])
    assert close(result.sliding_factor_at_tip.pinion, ref["K_ga1"])
    assert close(result.sliding_factor_at_tip.wheel, ref["K_ga2"])
    assert close(result.specific_sliding_at_end_points.pinion, ref["zeta_f1"])
    assert close(result.specific_sliding_at_end_points.wheel, ref["zeta_f2"])
    limited = [w.message.split(":")[0] for w in result.warnings if "limited" in w.code]
    assert limited == (["pinion", "wheel"] if name == "D" else ["wheel"])
    # single equations: Eq. (69) is Eq. (68) with the indices swapped; Eq. (84) at d_Na1
    case = CASES["B"]
    d_b1, d_b2 = base_diameters(case)
    a_w, alpha_wt = REFERENCE["B"]["a_w"], working_angle("B")
    assert close(pr.active_tip_diameter(a_w, alpha_wt, 78.4, d_b2, d_b1), ref["d_Na1"])
    rho_E1 = pr.radius_of_curvature_at_active_tip(ref["d_Na1"], d_b1)
    assert close(rho_E1, 0.5 * math.sqrt(ref["d_Na1"] ** 2 - d_b1**2))
    assert pr.root_form_circle_limits_active_profile(a_w, alpha_wt, 28.0, d_b1, d_b2, 78.4)
    assert not pr.root_form_circle_limits_active_profile(a_w, alpha_wt, 28.0, d_b1, d_b2, 78.0)


def test_g2a10_root_form_circle_on_the_start_of_the_active_profile_limits_nothing() -> None:
    """The norm limits 'wenn d_Ff größer ist' (p. 43): equality changes nothing and warns not."""
    pair = make_pair(CASES["B"])
    free = pr.compute_pair_geometry(pair)
    on_it = pr.compute_pair_geometry(pair, root_form_diameter_mm=free.sap_diameter_mm)
    assert on_it.warnings == ()
    assert on_it.active_tip_diameter_mm == free.active_tip_diameter_mm
    assert on_it.length_of_path_of_contact_mm == free.length_of_path_of_contact_mm


def test_g2a07_noise_at_a_boundary_is_folded_onto_the_boundary() -> None:
    case = {**CASES["B"], "x": (0.0, 0.0), "d_a": (28.0, 84.0)}  # wheel tip beyond T_1
    pair = make_pair(case)
    d_b1, _ = base_diameters(case)
    # a root form diameter within EPS below the base circle is the base circle (this mesh then
    # starts on the base circle and is rejected)
    with pytest.raises(GeometryInfeasibleError, match="starts on the base circle"):
        pr.compute_pair_geometry(
            pair, root_form_diameter_mm=Pair(pinion=d_b1 * (1.0 - 5e-13), wheel=76.5)
        )
    with pytest.raises(GeometryInfeasibleError, match="lies below the base circle"):
        pr.compute_pair_geometry(
            pair, root_form_diameter_mm=Pair(pinion=d_b1 * (1.0 - 1e-9), wheel=76.5)
        )
    # a tip form diameter within EPS above the tip diameter is the tip diameter
    ordinary = make_pair(CASES["B"])
    folded = pr.compute_pair_geometry(
        ordinary, tip_form_diameter_mm=Pair(pinion=28.0 * (1.0 + 5e-13), wheel=83.2)
    )
    assert folded.tip_form_diameter_mm.pinion == 28.0
    assert folded.active_tip_diameter_mm.pinion <= folded.tip_diameter_mm.pinion
    # a centre distance within EPS below the sum of the base radii gives alpha_wt = 0
    radii = 0.5 * sum(base_diameters(CASES["B"]))
    alpha_n = math.radians(20.0)
    assert (
        pr.transverse_working_pressure_angle(12, 40, 2.0, alpha_n, 0.0, radii * (1 - 5e-13)) == 0.0
    )
    with pytest.raises(GeometryInfeasibleError):
        pr.transverse_working_pressure_angle(12, 40, 2.0, alpha_n, 0.0, radii * (1 - 1e-9))


def test_g2a06_roll_length_is_the_radius_of_curvature_of_the_involute_module() -> None:
    """One implementation of Eq. (17): the pair module calls ``involute.radius_of_curvature``."""
    import inspect

    source = inspect.getsource(pr)
    assert "iv.radius_of_curvature" in source and "math.sqrt" not in source
    assert pr.length_of_addendum_path_of_contact(28.0, 22.5, 0.0) == iv.radius_of_curvature(
        28.0, 22.5
    )


def test_g2a12_sum_of_profile_shift_guards_its_angles() -> None:
    with pytest.raises(InputRangeError):
        pr.sum_of_profile_shift_coefficients(12, 40, -0.35, 0.0, 0.37)
    with pytest.raises(InputRangeError):
        pr.sum_of_profile_shift_coefficients(12, 40, 2.0, 0.0, 0.37)
    # inverse of Eq. (55) with the same arguments
    alpha_n, beta = math.radians(20.0), math.radians(12.0)
    alpha_wt = pr.working_pressure_angle_without_backlash(12, 40, alpha_n, beta, 0.25)
    assert pr.sum_of_profile_shift_coefficients(12, 40, alpha_n, beta, alpha_wt) == pytest.approx(
        0.25, abs=1e-13
    )
    assert pr.form_over_dimension(22.6, 22.8) == pytest.approx(-0.1), "signed"


# --- G2A-05, G2B-06: span measurements (not evaluated in increment 2, evaluated since increment 4) ------


def _span(case: dict[str, Any], gear: int, x: float, kind: DimensionKind) -> SpanMeasurement:
    """The span over two teeth of a gear of ``case`` with the coefficient ``x``."""
    alpha_n, beta = math.radians(case["alpha_n"]), math.radians(case["beta"])
    width = ins.span_measurement(case["z"][gear], case["m_n"], x, alpha_n, beta, 2)
    return SpanMeasurement(kind=kind, span_measurement_mm=width, number_of_teeth_spanned=2)


def test_g2a05_span_measurements_determine_what_their_kind_says() -> None:
    """Increment 2 reported a span and did not use it. Since increment 4 the input states which
    dimension a span is (DIN 21773 §4) and the pair is resolved from it (user decisions
    2026-10-04, ADR-107)."""
    case = CASES["B"]
    a_w = REFERENCE["B"]["a_w"]
    upper = _span(case, 0, 0.25, DimensionKind.UPPER_LIMIT)
    # a_w + x_2 + the upper limit of W_k1 (the data of ISO/TR 6336-30 Table A.1): x_1 follows
    # from a_w and x_2, the upper allowance of the pinion from x_1 and the span
    pair = forced(make_pair({**case, "a_w": a_w, "x": (None, -0.1)}), "pinion", span=upper)
    resolved = pr.resolve_tooth_thickness(pair)
    assert resolved.profile_shift_coefficient[0] == pytest.approx(0.3, abs=1e-13)
    allowance = resolved.tooth_thickness_allowance_um[0]
    assert allowance is not None
    assert allowance[0] == pytest.approx(
        1.0e3 * 2.0 * case["m_n"] * math.tan(math.radians(20.0)) * (0.25 - 0.3), rel=1e-12
    )
    assert allowance[0] == allowance[1]
    codes = [w.code for w in pr.compute_pair_geometry(pair).warnings]
    assert "upper_allowance_from_inspection_dimension" in codes
    assert "span_measurement_not_used" not in codes
    # x and the upper limit on the same gear: the allowance follows as well
    both = forced(make_pair(case), "wheel", span=_span(case, 1, -0.15, DimensionKind.UPPER_LIMIT))
    wheel = pr.resolve_tooth_thickness(both).tooth_thickness_allowance_um[1]
    assert wheel is not None and wheel[0] < 0.0
    # x and a nominal span on the same gear state the same value twice
    twice = forced(make_pair(case), "wheel", span=_span(case, 1, -0.1, DimensionKind.NOMINAL))
    with pytest.raises(InputRangeError, match="over-determined"):
        pr.compute_pair_geometry(twice)
    # a nominal span stands in for x
    nominal = forced(
        make_pair(case),
        "wheel",
        profile_shift_coefficient=None,
        span=_span(case, 1, -0.1, DimensionKind.NOMINAL),
    )
    assert pr.resolve_tooth_thickness(nominal).profile_shift_coefficient[1] == pytest.approx(
        -0.1, abs=1e-13
    )
    # the centre distance and the upper limits of both gears: the sum of the allowances is
    # fixed, its split is not (the importer applies the rule of STplus, the core demands it)
    only_spans = forced(
        forced(make_pair({**case, "a_w": a_w, "x": (0.3, None)}), "pinion",
               profile_shift_coefficient=None, span=upper),
        "wheel", span=_span(case, 1, -0.15, DimensionKind.UPPER_LIMIT),
    )  # fmt: skip
    with pytest.raises(InputRangeError, match="not its split between the gears"):
        pr.compute_pair_geometry(only_spans)
    # ... one allowance settles it
    settled = forced(only_spans, "pinion", tooth_thickness_allowance_um=(-70.0, -110.0))
    x_1, x_2, _, _ = pr.resolve_profile_shift(settled)
    assert x_1 == pytest.approx(0.25 + 0.07 / (2.0 * case["m_n"] * math.tan(math.radians(20.0))))
    assert x_1 + x_2 == pytest.approx(REFERENCE["B"]["sum_x"], abs=1e-12)
    # a mean or a lower limit needs the allowances to reach the upper limit
    mean = forced(make_pair(case), "wheel", span=_span(case, 1, -0.15, DimensionKind.MEAN))
    with pytest.raises(InputRangeError, match="only together with the allowances"):
        pr.compute_pair_geometry(mean)
    # only the centre distance, no span: the contract rejects it (the importer names the
    # distribution of the sum as the extension point)
    nothing = forced(
        make_pair({**case, "a_w": a_w, "x": (0.3, None)}), "pinion", profile_shift_coefficient=None
    )
    with pytest.raises(InputRangeError, match="profile shift undetermined"):
        pr.compute_pair_geometry(nothing)


# --- G2B-04, -05, -07, -21: importer --------------------------------------------------------------------

STE = """$ Anfang

$ Geometriedaten
ZAHNBREITE = 20 20
NORMALMODUL = 2
ZAEHNEZAHL = 12 40
{lines}
WERKZEUG_VORVERZ. = WKZ_1 WKZ_2

$ WKZ_1
KOPFHOEHENFAKTOR = 1.25
KOPFABRUNDUNGSFAKTOR = 0.25

$ WKZ_2
KOPFHOEHENFAKTOR = 1.25
KOPFABRUNDUNGSFAKTOR = 0.25

$ Ende
"""
ANGLES = "EINGRIFFSWINKEL = 20\nSCHRAEGUNGSWINKEL = 0\n"


def imported(lines: str) -> Any:
    return pair_input_from_ste(parse_ste(STE.format(lines=lines)))


def test_g2b07_missing_pressure_angle_is_a_parse_error() -> None:
    """STplus rejects such a batch input (probe no_pressure_angle); 20 degrees is no default."""
    with pytest.raises(ParseError, match="EINGRIFFSWINKEL missing"):
        imported("SCHRAEGUNGSWINKEL = 0\nPROFILVERSCHIEBUNG_N = 0.3 -0.1")
    with pytest.raises(ParseError, match="EINGRIFFSWINKEL missing"):
        imported("EINGRIFFSWINKEL = %\nPROFILVERSCHIEBUNG_N = 0.3 -0.1")
    assert imported(ANGLES + "PROFILVERSCHIEBUNG_N = 0.3 -0.1").pair.centre_distance_mm is None


def test_g2b04_centre_distance_is_a_pair_key() -> None:
    with pytest.raises(ParseError, match="ACHSABSTAND"):
        imported(ANGLES + "ACHSABSTAND = % 52.4\nPROFILVERSCHIEBUNG_N = 0.3 %")
    with pytest.raises(NotSupportedError, match="ACHSABSTAND"):
        imported(ANGLES + "ACHSABSTAND = 52.4 53\nPROFILVERSCHIEBUNG_N = 0.3 %")
    assert (
        imported(ANGLES + "ACHSABSTAND = 52.4\nPROFILVERSCHIEBUNG_N = 0.3").pair.centre_distance_mm
        == 52.4
    )


def test_g2b05_undetermined_pairs_leave_the_importer_as_typed_errors() -> None:
    with pytest.raises(NotSupportedError, match="distribution of the sum"):
        imported(ANGLES + "ACHSABSTAND = 52.4")
    with pytest.raises(ParseError, match="both gears need PROFILVERSCHIEBUNG_N"):
        imported(ANGLES + "PROFILVERSCHIEBUNG_N = 0.3")
    # whatever the contract rejects is a parse error of the file, never a raw validation error
    text = STE.format(lines=ANGLES + "PROFILVERSCHIEBUNG_N = 0.3 -0.1").replace("12 40", "40 12")
    with pytest.raises(ParseError, match="the pinion is the smaller gear") as caught:
        pair_input_from_ste(parse_ste(text))
    assert isinstance(caught.value, GearCoreError)
    # a + x_2 only: x_1 stays open and follows from the centre distance
    only_wheel = imported(ANGLES + "ACHSABSTAND = 52.4\nPROFILVERSCHIEBUNG_N = % -0.1").pair
    assert only_wheel.gears.pinion.profile_shift_coefficient is None
    assert only_wheel.gears.wheel.profile_shift_coefficient == -0.1


def test_g2b21_a_third_value_on_a_gear_key_is_a_parse_error() -> None:
    with pytest.raises(ParseError, match="has 3 values"):
        imported(ANGLES + "PROFILVERSCHIEBUNG_N = 0.1 0.15 0.3")


# --- G2B-01, -02, -03, -11, -13: registry entries -------------------------------------------------------


def test_g2b_registry_entries_of_increment_2_state_what_the_pages_print() -> None:
    total = quantity("sum_of_profile_shift_coefficients")
    assert total.location is not None and "§3.1 symbol list, p. 17" in total.location
    assert total.note is not None and "does not list" not in total.note
    assert total.stplus is not None and total.stplus.input_key == "PR.VERSCH.SUMME"
    alteration = quantity("tip_alteration_coefficient")
    assert [(p.symbol, p.description) for p in alteration.replaced] == [
        ("k*", "Kopfhöhenänderungsfaktor")
    ]
    path = quantity("length_of_addendum_path_of_contact")
    assert [p.symbol for p in path.replaced] == ["g_a"], "DIN 3960 Eq. (4.4.13) writes g_a"
    assert "(4.4.13)" in path.replaced[0].location
    tip = quantity("active_tip_diameter")
    assert tip.english is not None
    assert (tip.english.text, tip.english.source) == (
        "active tip diameter of pinion or wheel",
        "ISO6336-1:2019",
    )
    assert [(item.description, item.source) for item in tip.also] == [
        ("Effective tip diameter", "ISOTS6336-21:2022")
    ]
    # the older norm is cited by the clause that defines the quantity (file header, ADR-108)
    for name in (
        "sum_of_profile_shift_coefficients",
        "tip_alteration_coefficient",
        "tip_form_diameter",
        "active_tip_diameter",
        "common_tooth_depth",
        "sliding_factor_at_tip",
        "specific_sliding_at_end_points",
    ):
        (item,) = quantity(name).replaced
        assert item.location.startswith("§") and not item.location.startswith("§2.1"), name
        assert "p. " in item.location, name


# --- G2B-09, G2B-10: what the comparison with STplus can and cannot show -------------------------------


def _pair_rows() -> list[Any]:
    return [row for case in stplus_case_dirs() for row in compare_pair_geometry(case.name)]


@pytest.mark.oracle
def test_g2b09_detection_limit_of_the_pair_comparison_per_output() -> None:
    """Largest tolerance relative to the value, over all cases: the interface file (five
    decimals, own runs) resolves 4e-4 or better, the listing (three decimals) 6e-3 or better."""
    limits = detection_limits(_pair_rows())
    interface = {field: limit for (field, origin), limit in limits.items() if origin == "interface"}
    listing = {field: limit for (field, origin), limit in limits.items() if origin == "listing"}
    assert set(interface) == set(listing) == set(PAIR_FIELDS)
    assert 1.0e-4 < max(interface.values()) < 4.0e-4
    assert 1.0e-3 < max(listing.values()) < 6.0e-3
    coarse = {field for field, limit in interface.items() if limit > 4.0e-5}
    assert coarse == {
        "profile_shift_coefficient",
        "sum_of_profile_shift_coefficients",
        "sliding_factor_at_tip",
        "specific_sliding_at_end_points",
    }
    # the values quoted in ADR-110
    assert interface["specific_sliding_at_end_points"] == pytest.approx(1.8e-4, rel=0.05)
    assert interface["profile_shift_coefficient"] == pytest.approx(3.2e-4, rel=0.05)
    assert interface["length_of_addendum_path_of_contact_mm"] == pytest.approx(3.0e-5, rel=0.05)
    assert listing["sliding_factor_at_tip"] == pytest.approx(5.8e-3, rel=0.05)
    # a zero value has no relative limit
    zero = [row for row in _pair_rows() if row.stplus_value == 0.0]
    assert zero and {row.field for row in zero} <= {
        "overlap_ratio",
        "sum_of_profile_shift_coefficients",
        "profile_shift_coefficient",
    }


@pytest.mark.oracle
def test_g2b10_rows_that_repeat_an_input_are_counted() -> None:
    """Some compared values equal an input of the comparison (a tip form diameter without
    chamfer, the contact face width, an overlap ratio of zero): they test a decision, not a
    formula. The count is part of the documented state (ADR-110)."""
    repeated = [row for case in stplus_case_dirs() for row in rows_repeating_an_input(case.name)]
    assert len(repeated) == REPEATED_ROWS
    assert len(_pair_rows()) - len(repeated) == 682
    assert {row.field for row in repeated} == {
        "tip_form_diameter_mm",
        "active_tip_diameter_mm",
        "sap_diameter_mm",
        "contact_face_width_mm",
        "overlap_ratio",
        "sum_of_profile_shift_coefficients",
    }


REPEATED_ROWS = 173


# --- G2B-23: further STplus values checked with gearcore functions ---------------------------------------


@pytest.mark.eq("ISO21771:2014", "(76)")
@pytest.mark.oracle
def test_g2b23_form_over_dimension_against_stplus() -> None:
    checked = 0
    for path in stplus_case_dirs():
        if not has_stplus(path.name, "interface"):
            continue
        table = load_stplus(path.name, "interface")

        def numbers(key: str, source: dict[str, Any] = table) -> list[float]:
            return [float(v) for v in source[f"GEOMETRIEDATEN/{key}"]["numbers"]]

        starts, forms, printed = (
            numbers("NUTZKREISDURCHM_FUSS"),
            numbers("FUSSFORMKREISDURCHM"),
            numbers("FORMUEBERMASS"),
        )
        for gear in (0, 1):
            ours = pr.form_over_dimension(starts[gear], forms[gear])
            assert ours == pytest.approx(printed[gear], abs=2e-5), (path.name, gear)
            checked += 1
    assert checked == 28


@pytest.mark.eq("ISO21771:2014", "(60)")
@pytest.mark.eq("ISO21771:2014", "(76)")
@pytest.mark.oracle
def test_g2b23_tip_clearance_and_form_over_dimension_against_the_listings() -> None:
    """The supplied cases have a listing only (three decimals): every printed operand carries
    half a unit of its last digit. The listing prints the form over-dimension c_F of Eq. (76)
    under the symbol c_n."""
    half = 0.5e-3
    checked = 0
    for path in stplus_case_dirs():
        table = load_stplus(path.name, "geometry")

        def numbers(symbol: str, source: dict[str, Any] = table) -> list[float]:
            return [float(v) for v in source[symbol]["numbers"]]

        (a_w,) = numbers("a")
        tips, roots, starts, forms = (
            numbers("d_a"),
            numbers("d_f"),
            numbers("d_Nf"),
            numbers("d_Ff"),
        )
        clearances, over_dimensions = numbers("c"), numbers("c_n")
        for gear in (0, 1):
            clearance = pr.tip_clearance(a_w, tips[gear], roots[1 - gear])
            assert clearance == pytest.approx(clearances[gear], abs=3.0 * half), (path.name, gear)
            over = pr.form_over_dimension(starts[gear], forms[gear])
            assert over == pytest.approx(over_dimensions[gear], abs=2.0 * half), (path.name, gear)
            checked += 1
    assert checked == 36


@pytest.mark.oracle
def test_g2b10_fixtures_added_by_the_gate() -> None:
    """Three STplus runs close gaps of the comparison: Eq. (127) with a tip chamfer given as an
    input, a helical pair with different face widths, and a centre distance with x_2 only (the
    rule of ADR-107, case 2: STplus derives x_1 from a_w as gearcore does)."""

    def rows(case: str, field: str) -> list[Any]:
        return [row for row in compare_pair_geometry(case) if row.field == field]

    chamfer = pair_data("chamfer_hk_z20_34")
    assert [g.tip_chamfer_radial_mm for g in chamfer.pair.gears.as_tuple()] == [0.2, 0.3]
    assert "d_Fa1" not in chamfer.values and "d_Fa2" not in chamfer.values, "Eq. (127) is used"
    forms = rows("chamfer_hk_z20_34", "tip_form_diameter_mm")
    assert len(forms) == 4 and all(row.verdict is not ParityVerdict.DIFFERENT for row in forms)
    assert {round(row.stplus_value, 3) for row in forms} == {44.4, 71.8}

    unequal = pair_data("helix15_b_unequal")
    assert (unequal.values["b_1"], unequal.values["b_2"]) == (30.0, 24.0)
    for field in ("contact_face_width_mm", "overlap_ratio", "total_contact_ratio"):
        found = rows("helix15_b_unequal", field)
        assert len(found) == 2, field
        assert all(row.verdict is not ParityVerdict.DIFFERENT for row in found), field
    assert rows("helix15_b_unequal", "contact_face_width_mm")[0].gearcore_value == 24.0

    open_x1 = pair_data("a_x2_only_z18_45")
    assert open_x1.pair.gears.pinion.profile_shift_coefficient is None
    assert open_x1.values["x_2"] == 0.1 and "x_1" not in open_x1.values
    shifts = rows("a_x2_only_z18_45", "profile_shift_coefficient")
    assert [(row.gear, row.origin) for row in shifts] == [
        ("pinion", "listing"),
        ("pinion", "interface"),
    ]
    assert [row.stplus_token for row in shifts] == ["0.4284", "0.42842"]
    assert all(row.verdict is ParityVerdict.IDENTICAL for row in shifts)


@pytest.mark.oracle
def test_g2b_no_row_is_different_without_documentation() -> None:
    different = [row for row in _pair_rows() if row.verdict is ParityVerdict.DIFFERENT]
    assert different == []


# === verification review of the fixes (G2V-xx) =====================================================


def _at_module(m_n: float, **changes: Any) -> dict[str, Any]:
    """Case B scaled to the module m_n (z 12/40, x 0.3/-0.1, d_a = 14 m_n / 41.6 m_n)."""
    scaled = {**CASES["B"], "m_n": m_n, "b": 10.0 * m_n, "d_a": (14.0 * m_n, 41.6 * m_n)}
    return {**scaled, **changes}


# --- G2V-01, -02, -05: no result reports a start of the active profile on the base circle -------


@pytest.mark.oracle
@pytest.mark.parametrize("case", ["undercut_z12_x0", "neg_shift_z17_xm08"])
def test_g2v01_root_form_circle_on_the_base_circle_of_a_fixture_is_rejected(case: str) -> None:
    """The original repro of G2B-14: in these cases the wheel tip reaches the tangent point, so
    the pinion's involute ends at its root form circle. On the base circle, and within EPS of it
    on either side, the mesh is rejected; above the band the specific sliding is large and finite."""
    data = pair_data(case)
    d_b1 = compute_pair_from_data(data, data.values).gears.pinion.base_diameter_mm
    band = (d_b1 * (1.0 - 5e-13), d_b1, math.nextafter(d_b1, math.inf), d_b1 * (1.0 + 5e-13))
    for d_Ff1 in band:
        with pytest.raises(GeometryInfeasibleError, match="starts on the base circle"):
            compute_pair_from_data(data, {**data.values, "d_Ff1": d_Ff1})
    near = compute_pair_from_data(data, {**data.values, "d_Ff1": d_b1 * (1.0 + 1e-9)})
    assert near.sap_diameter_mm.pinion == d_b1 * (1.0 + 1e-9)
    assert "active_profile_limited_by_root_form_circle" in [w.code for w in near.warnings]
    zeta = near.specific_sliding_at_end_points.pinion
    assert math.isfinite(zeta) and -1.0e6 < zeta < -1.0e3


def test_g2v01_a_start_that_equals_the_base_circle_in_binary64_is_rejected() -> None:
    """A wheel tip that ends shortly before the tangent point T_1 leaves a positive rest on the
    line of action, but a start of the active profile that equals d_b1 within EPS."""
    case, ref = CASES["B"], REFERENCE["B"]
    d_b1, d_b2 = base_diameters(case)
    at_tangent_point = math.hypot(2.0 * ref["T1T2"], d_b2)
    for short_of_it in (1e-10, 1e-8, 1e-6):
        pair = make_pair({**case, "d_a": (28.0, at_tangent_point - short_of_it)})
        with pytest.raises(GeometryInfeasibleError, match="starts on the base circle"):
            pr.compute_pair_geometry(pair)
    # the criterion is the reported diameter: the first result lies above d_b (1 + EPS)
    result = pr.compute_pair_geometry(make_pair({**case, "d_a": (28.0, at_tangent_point - 1e-3)}))
    assert result.sap_diameter_mm.pinion > d_b1 * (1.0 + EPS)
    assert -1.0e6 < result.specific_sliding_at_end_points.pinion < -1.0e2


def test_g2w02_the_wheel_side_of_the_criterion() -> None:
    """The mirrored case: the pinion tip ends shortly before the tangent point T_2, so the active
    profile of the wheel starts on its base circle."""
    case, ref = CASES["B"], REFERENCE["B"]
    d_b1, d_b2 = base_diameters(case)
    at_tangent_point = math.hypot(2.0 * ref["T1T2"], d_b1)
    for short_of_it in (1e-10, 1e-8, 1e-6):
        pair = make_pair({**case, "d_a": (at_tangent_point - short_of_it, 83.2)})
        with pytest.raises(GeometryInfeasibleError, match="wheel: the active profile starts on"):
            pr.compute_pair_geometry(pair)
    result = pr.compute_pair_geometry(make_pair({**case, "d_a": (at_tangent_point - 1e-3, 83.2)}))
    assert result.sap_diameter_mm.wheel > d_b2 * (1.0 + EPS)
    assert -1.0e6 < result.specific_sliding_at_end_points.wheel < -1.0e2
    # the same through the root form circle of the wheel
    for d_Ff2 in (d_b2 * (1.0 - 5e-13), d_b2, d_b2 * (1.0 + 5e-13)):
        pair = make_pair({**case, "d_a": (at_tangent_point + 0.5, 83.2)})
        with pytest.raises(GeometryInfeasibleError, match="wheel: the active profile starts on"):
            pr.compute_pair_geometry(pair, root_form_diameter_mm=Pair(pinion=22.9, wheel=d_Ff2))


@pytest.mark.parametrize("m_n", [0.05, 2.0, 100.0])
def test_g2w03_an_active_profile_without_length_is_no_mesh_at_any_module(m_n: float) -> None:
    """a_w and both root form circles 1e-6 above their limits: the active profiles have no
    length within rounding noise. The first version answered this differently per module (and
    returned d_Nf > d_Na at m_n = 2)."""
    case = _at_module(m_n)
    d_b1, d_b2 = base_diameters(case)
    a_w = 0.5 * (d_b1 + d_b2) * (1.0 + 1e-6)
    pair = make_pair({**case, "a_w": a_w, "x": (0.3, None)})
    forms = Pair(pinion=d_b1 * (1.0 + 1e-6), wheel=d_b2 * (1.0 + 1e-6))
    with pytest.raises(GeometryInfeasibleError, match="the teeth do not mesh"):
        pr.compute_pair_geometry(pair, root_form_diameter_mm=forms)


@pytest.mark.parametrize("m_n", [0.05, 2.0, 100.0])
def test_g2v02_centre_distance_just_above_the_base_radii_never_returns_garbage(m_n: float) -> None:
    """a_w = (sum of the base radii) (1 + delta) with both root form circles on the base circles:
    the mesh starts on the base circles for every delta, at every module."""
    case = _at_module(m_n)
    d_b1, d_b2 = base_diameters(case)
    radii = 0.5 * (d_b1 + d_b2)
    on_base = Pair(pinion=d_b1, wheel=d_b2)
    for exponent in range(-13, -1):
        for mantissa in (1.0, 1.7, 3.3, 6.1):
            a_w = radii * (1.0 + mantissa * 10.0**exponent)
            pair = make_pair({**case, "a_w": a_w, "x": (0.3, None)})
            with pytest.raises(GeometryInfeasibleError, match="starts on the base circle"):
                pr.compute_pair_geometry(pair, root_form_diameter_mm=on_base)


def test_g2v07_original_repro_of_the_large_gear() -> None:
    """G2A-02 (a) as reported: z 11/172, m_n 100, d_Ff1 on the base circle returned -1.4e14."""
    case = {"z": (11, 172), "m_n": 100.0, "alpha_n": 20.0, "beta": 0.0, "b": 500.0,
            "d_a": (1240.0, 17360.0), "a_w": None, "x": (-0.3, -0.2)}  # fmt: skip
    d_b1, d_b2 = base_diameters(case)
    for m_n in (100.0, 2.0, 0.05):
        scale = m_n / 100.0
        scaled = {**case, "m_n": m_n, "b": 5.0 * m_n, "d_a": (1240.0 * scale, 17360.0 * scale)}
        forms = Pair(pinion=d_b1 * scale, wheel=1.01 * d_b2 * scale)
        with pytest.raises(GeometryInfeasibleError, match="starts on the base circle"):
            pr.compute_pair_geometry(make_pair(scaled), root_form_diameter_mm=forms)


# --- G2V-04, -17: the validated pair is what is computed and returned -------------------------------


def test_g2v04_the_validated_pair_is_what_is_computed_and_returned() -> None:
    pair = make_pair(CASES["B"])
    reference = pr.compute_pair_geometry(pair)
    assert reference.inputs == pair
    # nested models replaced by their dumps: validated back into the contract, no AttributeError
    tool_as_dict = forced(pair, "wheel", tool=pair.gears.wheel.tool.model_dump())
    gears_as_dict = pair.model_copy(update={"gears": pair.gears.model_dump()})
    for loose in (tool_as_dict, gears_as_dict):
        result = pr.compute_pair_geometry(loose)
        assert result == reference
        assert isinstance(result.inputs.gears.wheel.tool, ToolProfile)
        assert pr.resolve_profile_shift(loose) == pr.resolve_profile_shift(pair)
        assert pr.with_nominal_tip_diameters(loose, h_aP_mm=2.0) == pair
    # numbers of another type come back as the floats of the contract
    for module in (2, np.float64(2.0), np.float32(2.0)):
        result = pr.compute_pair_geometry(pair.model_copy(update={"normal_module_mm": module}))
        assert type(result.inputs.normal_module_mm) is float
        assert result == reference
        assert PairGeometry.model_validate_json(result.model_dump_json()) == result
    # a bool is no number
    with pytest.raises(InputRangeError):
        pr.compute_pair_geometry(pair.model_copy(update={"helix_angle_deg": True}))


def test_g2v04_a_pair_with_every_optional_field_passes_the_second_validation() -> None:
    """Every optional field at once, as far as the inputs do not state the same thing twice:
    the pinion gives the upper limit of its span beside x, the wheel its allowances."""
    span = _span(CASES["B"], 0, 0.25, DimensionKind.UPPER_LIMIT)
    full_tool = ToolProfile(
        name="WKZ_1",
        normal_module_mm=2.0,
        profile_angle_deg=20.0,
        addendum_factor=1.25,
        tip_radius_factor=0.25,
        dedendum_factor=1.3,
        root_form_height_factor=1.1,
        edge_break_angle_deg=45.0,
        protuberance_mm=0.05,
        protuberance_angle_deg=10.0,
        machining_allowance_mm=0.1,
    )
    dump = make_pair(CASES["B"]).model_dump()
    for gear in ("pinion", "wheel"):
        dump["gears"][gear].update(
            tool=full_tool.model_dump(),
            finishing_tool=full_tool.model_dump(),
            material={"kind": "plastic", "name": "WST_PA66"},
            number_of_teeth_spanned=3,
            measuring_ball_diameter_mm=3.5,
            allowance_series="cd25",
            quality_grade=7,
            quality_system="ISO1328",
        )
    dump["gears"]["pinion"].update(span=span.model_dump())
    dump["gears"]["wheel"].update(span_allowance_um=(-40, -80))
    dump["min_tip_clearance_factor"] = 0.2
    pair = PairInput.model_validate(dump)
    result = pr.compute_pair_geometry(pair)
    assert result.inputs == pair
    assert PairGeometry.model_validate_json(result.model_dump_json()) == result


# --- G2V-06, -10 to -13, and the boundaries the mutations of the review slipped through ---------------


@pytest.mark.parametrize("m_n", [0.05, 2.0, 100.0])
def test_g2v06_a_path_of_contact_of_zero_is_no_mesh_at_any_module(m_n: float) -> None:
    """The pinion tip ends where the wheel tip begins: g_alpha = 0 within rounding noise."""
    case = _at_module(m_n)
    free = pr.compute_pair_geometry(make_pair(case))
    start = free.sap_diameter_mm.pinion
    for factor in (1.0 - 1e-13, 1.0, 1.0 + 1e-13):
        pair = make_pair({**case, "d_a": (start * factor, 41.6 * m_n)})
        with pytest.raises(GeometryInfeasibleError, match="the teeth do not mesh"):
            pr.compute_pair_geometry(pair)
    short = pr.compute_pair_geometry(make_pair({**case, "d_a": (start * 1.001, 41.6 * m_n)}))
    assert 0.0 < short.transverse_contact_ratio < 0.1
    assert short.sap_diameter_mm.pinion < short.active_tip_diameter_mm.pinion


def test_g2v10_a_derived_profile_shift_at_the_limit_of_the_range() -> None:
    case = {**CASES["B"], "x": (0.3, 2.0), "d_a": (28.0, 92.0)}
    a_w = pr.resolve_profile_shift(make_pair(case))[2]
    derived = pr.resolve_profile_shift(make_pair({**case, "a_w": a_w, "x": (0.3, None)}))[1]
    assert derived == pytest.approx(2.0, abs=1e-12) and derived <= 2.0
    with pytest.raises(GeometryInfeasibleError, match="outside the verified range"):
        pr.resolve_profile_shift(make_pair({**case, "a_w": a_w * (1.0 + 1e-9), "x": (0.3, None)}))


def test_g2v11_root_form_circle_that_leaves_no_involute() -> None:
    pair = make_pair(CASES["B"])
    for d_Ff1 in (60.0, 28.0):
        with pytest.raises(
            GeometryInfeasibleError, match="does not lie below the tip form diameter"
        ):
            pr.compute_pair_geometry(pair, root_form_diameter_mm=Pair(pinion=d_Ff1, wheel=78.0))


def test_g2v12_noise_above_the_start_of_the_active_profile_limits_nothing() -> None:
    pair = make_pair(CASES["B"])
    free = pr.compute_pair_geometry(pair)
    start = free.sap_diameter_mm
    one_ulp_above = Pair(
        pinion=math.nextafter(start.pinion, math.inf), wheel=math.nextafter(start.wheel, math.inf)
    )
    result = pr.compute_pair_geometry(pair, root_form_diameter_mm=one_ulp_above)
    assert result.warnings == ()
    assert result.active_tip_diameter_mm == free.active_tip_diameter_mm
    assert result.sap_diameter_mm == start
    # the band is EPS relative: beyond it the root form circle limits
    a_w, alpha_wt = REFERENCE["B"]["a_w"], working_angle("B")
    d_b1, d_b2 = base_diameters(CASES["B"])
    limits = pr.root_form_circle_limits_active_profile
    assert not limits(a_w, alpha_wt, 83.2, d_b2, d_b1, start.pinion * (1.0 + 5e-13))
    assert limits(a_w, alpha_wt, 83.2, d_b2, d_b1, start.pinion * (1.0 + 2e-12))


def test_g2v13_the_result_echoes_the_root_form_diameters_it_used() -> None:
    pair = make_pair(CASES["B"])
    d_b1, _ = base_diameters(CASES["B"])
    result = pr.compute_pair_geometry(
        pair, root_form_diameter_mm=Pair(pinion=d_b1 * (1.0 - 5e-13), wheel=78.0)
    )
    assert result.root_form_diameter_mm == Pair(pinion=d_b1, wheel=78.0)
    assert result.sap_diameter_mm.pinion > d_b1, "not limited: the start follows from the wheel tip"
    assert pr.compute_pair_geometry(pair).root_form_diameter_mm is None


def test_g2v07_tip_form_diameter_boundaries() -> None:
    pair = make_pair(CASES["B"])
    d_b1, _ = base_diameters(CASES["B"])
    with pytest.raises(GeometryInfeasibleError, match="does not lie above the base circle"):
        pr.compute_pair_geometry(pair, tip_form_diameter_mm=Pair(pinion=d_b1, wheel=83.2))
    with pytest.raises(InputRangeError, match="exceeds the tip diameter"):
        pr.compute_pair_geometry(
            pair, tip_form_diameter_mm=Pair(pinion=28.0 * (1.0 + 1e-9), wheel=83.2)
        )


# --- G2V-07: properties of the orchestrator over the verified ranges -----------------------------------

KNOWN_WARNINGS = {
    "root_form_diameter_not_checked",
    "active_profile_limited_by_root_form_circle",
    "tip_form_diameter_not_generated",
    "tip_chamfer_input_not_used",
    "transverse_contact_ratio_below_one",
    "common_tooth_depth_with_tip_form_circles",
}
meshes = st.fixed_dictionaries(
    {
        "z_1": st.integers(5, 1000),
        "more": st.integers(0, 995),
        "m_n": st.floats(0.05, 100.0),
        "alpha_n": st.floats(10.0, 30.0),
        "beta": st.floats(-45.0, 45.0),
        "x": st.tuples(st.floats(-2.0, 2.0), st.floats(-2.0, 2.0)),
        "addendum": st.tuples(st.floats(0.4, 1.4), st.floats(0.4, 1.4)),
        "width": st.tuples(st.floats(0.5, 20.0), st.floats(0.5, 20.0)),
        "chamfer": st.tuples(st.floats(0.0, 0.3), st.floats(0.0, 0.3)),
        "given_centre_distance": st.booleans(),
        "root_form": st.none() | st.tuples(st.floats(0.0, 1.05), st.floats(0.0, 1.05)),
        "tip_form": st.none() | st.tuples(st.floats(0.97, 1.0), st.floats(0.97, 1.0)),
    }
)


@given(meshes)
def test_g2v07_orchestrator_returns_a_consistent_result_or_a_typed_error(
    mesh: dict[str, Any],
) -> None:
    z = (mesh["z_1"], min(mesh["z_1"] + mesh["more"], 1000))
    m_n = mesh["m_n"]
    beta = math.radians(mesh["beta"])
    tips = [
        iv.reference_diameter(z[i], m_n, beta) + 2.0 * m_n * (mesh["x"][i] + mesh["addendum"][i])
        for i in range(2)
    ]
    gears = [
        GearInput(
            number_of_teeth=z[i],
            profile_shift_coefficient=mesh["x"][i],
            face_width_mm=mesh["width"][i] * m_n,
            tip_diameter_mm=tips[i],
            tip_chamfer_radial_mm=mesh["chamfer"][i] * m_n,
            tool=ToolProfile(
                addendum_factor=1.25,
                tip_radius_factor=0.25,
                protuberance_mm=0.0,
                machining_allowance_mm=0.0,
            ),
        )
        for i in range(2)
    ]
    pair = PairInput(
        normal_module_mm=m_n,
        normal_pressure_angle_deg=mesh["alpha_n"],
        helix_angle_deg=mesh["beta"],
        gears=Pair(pinion=gears[0], wheel=gears[1]),
    )
    root_form = tip_form = None
    try:
        if mesh["given_centre_distance"]:
            a_w = pr.resolve_profile_shift(pair)[2]
            open_wheel = gears[1].model_copy(update={"profile_shift_coefficient": None})
            pair = pair.model_copy(
                update={"centre_distance_mm": a_w, "gears": Pair(pinion=gears[0], wheel=open_wheel)}
            )
        alpha_n = math.radians(mesh["alpha_n"])
        bases = [iv.base_diameter(z[i], m_n, alpha_n, beta) for i in range(2)]
        if mesh["root_form"] is not None:
            root_form = Pair(
                pinion=bases[0] + mesh["root_form"][0] * abs(tips[0] - bases[0]),
                wheel=bases[1] + mesh["root_form"][1] * abs(tips[1] - bases[1]),
            )
        if mesh["tip_form"] is not None:
            tip_form = Pair(
                pinion=tips[0] * mesh["tip_form"][0], wheel=tips[1] * mesh["tip_form"][1]
            )
        result = pr.compute_pair_geometry(
            pair, root_form_diameter_mm=root_form, tip_form_diameter_mm=tip_form
        )
    except GearCoreError:
        return  # a typed error is an answer; anything else fails the test
    assert {w.code for w in result.warnings} <= KNOWN_WARNINGS
    assert result.inputs == pair
    for role in ("pinion", "wheel"):
        d_b = getattr(result.gears, role).base_diameter_mm
        d_Nf = getattr(result.sap_diameter_mm, role)
        d_Na = getattr(result.active_tip_diameter_mm, role)
        d_Fa = getattr(result.tip_form_diameter_mm, role)
        d_a = getattr(result.tip_diameter_mm, role)
        assert d_b * (1.0 + EPS) < d_Nf < d_Na * (1.0 - EPS), role
        assert d_Na <= d_Fa <= d_a, role
        assert getattr(result.specific_sliding_at_end_points, role) < 1.0
        if result.root_form_diameter_mm is not None:
            assert getattr(result.root_form_diameter_mm, role) <= d_Nf * (1.0 + EPS), role
    a_w = result.centre_distance_mm
    g_a = result.length_of_addendum_path_of_contact_mm
    assert g_a.pinion + g_a.wheel == pytest.approx(
        result.length_of_path_of_contact_mm, abs=1e-12 * a_w
    )
    d_w = result.working_pitch_diameter_mm
    assert d_w.pinion + d_w.wheel == pytest.approx(2.0 * a_w, rel=1e-12)
    assert result.total_contact_ratio == result.transverse_contact_ratio + result.overlap_ratio
    assert result.length_of_path_of_contact_mm > 0.0
    # the two radii of curvature at an end point add up to T_1 T_2: the start of the active
    # profile of a gear mates with the active tip of the other gear
    alpha_wt = math.radians(result.transverse_working_pressure_angle_deg)
    span = 2.0 * pr.length_between_tangent_points(a_w, alpha_wt)
    d_b1 = result.gears.pinion.base_diameter_mm
    d_b2 = result.gears.wheel.base_diameter_mm
    root_1 = 2.0 * iv.radius_of_curvature(result.sap_diameter_mm.pinion, d_b1)
    tip_2 = 2.0 * iv.radius_of_curvature(result.active_tip_diameter_mm.wheel, d_b2)
    assert root_1 + tip_2 == pytest.approx(span, rel=1e-9, abs=1e-9 * d_b2)
    assert PairGeometry.model_validate_json(result.model_dump_json()) == result
    json.loads(result.model_dump_json())


# --- G2V-03, -14: importer --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text, model_field",
    [
        (STE.format(lines=ANGLES + "PROFILVERSCHIEBUNG_N = 0.3 -0.1").replace("20 20", "5000 20"),
         "face_width_mm"),
        (STE.format(lines=ANGLES + "PROFILVERSCHIEBUNG_N = 3 -0.1"), "profile_shift_coefficient"),
        (STE.format(lines=ANGLES + "PROFILVERSCHIEBUNG_N = 0.3 -0.1").replace("12 40", "3 40"),
         "number_of_teeth"),
        (STE.format(lines=ANGLES + "PROFILVERSCHIEBUNG_N = 0.3 -0.1\nKOPFKREISDM = 0 83.2"),
         "tip_diameter_mm"),
        (STE.format(lines=ANGLES + "PROFILVERSCHIEBUNG_N = 0.3 -0.1\nKOPFKANTENBRUCH = -0.1 0"),
         "tip_chamfer_radial_mm"),
        (STE.format(lines=ANGLES + "PROFILVERSCHIEBUNG_N = 0.3 -0.1\nISO_QUALITAET = 13 7"),
         "quality_grade"),
        (STE.format(lines=ANGLES + "ACHSABSTAND = 52.4\nPROFILVERSCHIEBUNG_N = 0.3\n"
                    "ZAHNWEITE = % 27.8\nMESSZAEHNEZAHL = % 1"), "number_of_teeth_spanned"),
        (STE.format(lines=ANGLES + "PROFILVERSCHIEBUNG_N = 0.3 -0.1").replace(
            "KOPFHOEHENFAKTOR = 1.25", "KOPFHOEHENFAKTOR = -1", 1), "addendum_factor"),
        (STE.format(lines=ANGLES + "PROFILVERSCHIEBUNG_N = 0.3 -0.1\n"
                    "OBERES_ZAHNW_ABMASS = -80 -80\nUNTERES_ZAHNW_ABMASS = -40 -40"),
         "span_allowance_um"),
        (STE.format(lines=ANGLES + "PROFILVERSCHIEBUNG_N = 0.3 -0.1\nMESSTUECKDM_D_M = -3 3"),
         "measuring_ball_diameter_mm"),
    ],
)  # fmt: skip
def test_g2v03_whatever_a_contract_rejects_is_a_parse_error(text: str, model_field: str) -> None:
    """Every model the importer builds: ``GearInput``, ``SpanMeasurement``, ``ToolProfile``."""
    with pytest.raises(ParseError, match="is no valid input") as caught:
        pair_input_from_ste(parse_ste(text))
    assert model_field in str(caught.value)
    assert isinstance(caught.value.__cause__, ValidationError)


def test_g2w06_public_section_importers_raise_parse_errors() -> None:
    """``tool_from_section`` and ``material_from_section`` are public: the verdict of their
    contracts is a ``ParseError`` there as well."""
    tool_text = STE.format(lines=ANGLES + "PROFILVERSCHIEBUNG_N = 0.3 -0.1").replace(
        "KOPFHOEHENFAKTOR = 1.25", "KOPFHOEHENFAKTOR = -1", 1
    )
    section = parse_ste(tool_text).section("WKZ_1")
    assert section is not None
    with pytest.raises(ParseError, match="tool 'WKZ_1' is no valid input: addendum_factor"):
        tool_from_section(section, [], normal_pressure_angle_deg=20.0)
    # (an addendum beyond the limit of STplus is reduced, not rejected: ADR-114)
    assert tool_from_section(
        parse_ste(tool_text.replace("KOPFHOEHENFAKTOR = -1", "KOPFHOEHENFAKTOR = 5")).section(  # type: ignore[arg-type]
            "WKZ_1"
        ),
        [],
        normal_pressure_angle_deg=20.0,
    ).addendum_factor == pytest.approx(1.993, abs=5e-4)
    material_text = (
        "$ Anfang\n\n$ WST_X\nELASTIZITAETSMODUL = -1\nQUERKONTRAKTIONSZAHL = 0.3\n\n$ Ende\n"
    )
    material = parse_ste(material_text).section("WST_X")
    assert material is not None
    with pytest.raises(ParseError, match="material 'WST_X' is no valid input") as caught:
        material_from_section(material, MaterialKind.STEEL)
    assert isinstance(caught.value.__cause__, ValidationError)
    three_materials = STE.format(lines=ANGLES + "PROFILVERSCHIEBUNG_N = 0.3 -0.1").replace(
        "$ Ende", "$ Tragfaehigkeit_Allgem\nWERKSTOFF = WST_X WST_X WST_X\n\n$ Ende"
    )
    with pytest.raises(ParseError, match="WERKSTOFF has 3 values"):
        pair_input_from_ste(parse_ste(three_materials))


def test_g2v14_a_third_name_on_a_per_gear_key_is_a_parse_error() -> None:
    valid = STE.format(lines=ANGLES + "PROFILVERSCHIEBUNG_N = 0.3 -0.1")
    assert pair_input_from_ste(parse_ste(valid)).pair.gears.wheel.profile_shift_coefficient == -0.1
    three_tools = valid.replace("= WKZ_1 WKZ_2", "= WKZ_1 WKZ_2 WKZ_2")
    with pytest.raises(ParseError, match="WERKZEUG_VORVERZ. has 3 values"):
        pair_input_from_ste(parse_ste(three_tools))
    three_series = STE.format(
        lines=ANGLES + "PROFILVERSCHIEBUNG_N = 0.3 -0.1\nABMASS_TOL_REIHE = cd25 cd25 cd25"
    )
    with pytest.raises(ParseError, match="ABMASS_TOL_REIHE has 3 values"):
        pair_input_from_ste(parse_ste(three_series))


# --- G2V-15: the basic comparison uses the inputs the importer passes on ------------------------------


@pytest.mark.oracle
def test_g2v15_basic_comparison_of_the_case_with_x2_only() -> None:
    rows = compare_basic_geometry("a_x2_only_z18_45")
    shifts = [(row.gear, row.origin) for row in rows if row.field == "profile_shift_coefficient"]
    assert shifts == [("wheel", "listing"), ("wheel", "interface")], "x_2 is the input, x_1 is not"
    thickness = [row for row in rows if row.field == "normal_tooth_thickness_mm"]
    assert {row.gear: row.input_tolerance > 0.0 for row in thickness} == {
        "pinion": True,
        "wheel": False,
    }
    assert all(row.verdict is not ParityVerdict.DIFFERENT for row in rows)


# === user decisions after the gate (2026-09-30) =====================================================


def test_user_decision_no_default_for_helix_chamfer_protuberance_allowance() -> None:
    """Helix angle, tip chamfer, protuberance and machining allowance are required inputs: zero is
    stated, not assumed. The schema lists them as required."""
    pair = make_pair(CASES["B"])
    dump = pair.model_dump()
    required = {
        ("helix_angle_deg",): "helix_angle_deg",
        ("gears", "pinion", "tip_chamfer_radial_mm"): "tip_chamfer_radial_mm",
        ("gears", "wheel", "tool", "protuberance_mm"): "protuberance_mm",
        ("gears", "wheel", "tool", "machining_allowance_mm"): "machining_allowance_mm",
        ("normal_pressure_angle_deg",): "normal_pressure_angle_deg",
    }
    for path, name in required.items():
        without = json.loads(json.dumps(dump))
        holder = without
        for part in path[:-1]:
            holder = holder[part]
        del holder[path[-1]]
        with pytest.raises(ValidationError, match=f"{name}\\n +Field required"):
            PairInput.model_validate(without)
    assert {"helix_angle_deg", "normal_pressure_angle_deg"} <= set(
        PairInput.model_json_schema()["required"]
    )
    assert "tip_chamfer_radial_mm" in GearInput.model_json_schema()["required"]
    assert {"protuberance_mm", "machining_allowance_mm"} <= set(
        ToolProfile.model_json_schema()["required"]
    )


def test_user_decision_the_importer_states_every_zero_in_its_notes() -> None:
    """A blanket zero only together with a note: a ``.ste`` file without the key means that the
    feature is absent; the importer says so for each value."""
    bare = STE.format(lines=ANGLES + "PROFILVERSCHIEBUNG_N = 0.3 -0.1")
    result = pair_input_from_ste(parse_ste(bare))
    zeros = [
        "tool 'WKZ_1': PROTUBERANZBETRAG not given → 0 (no protuberance)",
        "tool 'WKZ_1': BEARB_ZUGABE_WKZ not given → 0 (no machining allowance of the tool)",
        "tool 'WKZ_2': PROTUBERANZBETRAG not given → 0 (no protuberance)",
        "tool 'WKZ_2': BEARB_ZUGABE_WKZ not given → 0 (no machining allowance of the tool)",
        "gear 1: KOPFKANTENBRUCH not given → 0 (no tip chamfer)",
        "gear 2: KOPFKANTENBRUCH not given → 0 (no tip chamfer)",
    ]
    assert [note for note in result.notes if "→ 0 (" in note] == zeros
    # a helix angle is no such zero: STplus computes it or rejects the input (ADR-114, probes
    # helix_angle_from_centre_distance and no_helix_angle_no_centre_distance)
    with pytest.raises(ParseError, match="SCHRAEGUNGSWINKEL missing"):
        pair_input_from_ste(
            parse_ste(STE.format(lines="EINGRIFFSWINKEL = 20\nPROFILVERSCHIEBUNG_N = 0.3 -0.1"))
        )
    # given values are taken without such a note
    given = STE.format(
        lines=ANGLES + "PROFILVERSCHIEBUNG_N = 0.3 -0.1\nKOPFKANTENBRUCH = 0 0.2"
    ).replace(
        "KOPFABRUNDUNGSFAKTOR = 0.25",
        "KOPFABRUNDUNGSFAKTOR = 0.25\nPROTUBERANZBETRAG = 0\nBEARB_ZUGABE_WKZ = 0.1",
    )
    result = pair_input_from_ste(parse_ste(given))
    assert not [note for note in result.notes if "→ 0 (" in note]
    assert result.pair.gears.wheel.tip_chamfer_radial_mm == 0.2
    assert result.pair.gears.pinion.tool.machining_allowance_mm == 0.1
    # every other note of the file is a default of STplus the importer applied (ADR-114)
    assert all("STplus" in note or "not determined" in note for note in result.notes), result.notes
    # the public tool importer records the zeros and the presets in the list it is given
    section = parse_ste(bare).section("WKZ_1")
    assert section is not None
    notes: list[str] = []
    assert tool_from_section(section, notes, normal_pressure_angle_deg=20.0) == tool_from_section(
        section, [], normal_pressure_angle_deg=20.0
    )
    assert len(notes) == 4  # root form height, dedendum, protuberance, allowance


def test_user_decision_tools_of_the_package_state_their_zeros() -> None:
    from gearcore import rack
    from gearcore.stplus_program import stplus_default_tool, tool_database

    counterpart = rack.tool_from_basic_rack(
        rack.din867_basic_rack(bottom_clearance_factor=0.25, fillet_radius_factor=0.38)
    )
    assert (counterpart.protuberance_mm, counterpart.machining_allowance_mm) == (0.0, 0.0)
    assert rack.din3972_tool("II", 2.0).protuberance_mm == 0.0
    assert rack.din3972_tool("III", 2.0).machining_allowance_mm > 0.0
    default = stplus_default_tool()  # probe defaults_minimal: pr_0 = 0.000, q = 0.000
    assert (default.protuberance_mm, default.machining_allowance_mm) == (0.0, 0.0)
    valid = [record for record in tool_database().values() if record.profile is not None]
    assert valid and all(
        (record.notes != ()) == any(key not in dict(record.entries) for key in ABSENT_MEANS_NONE)
        for record in valid
    )
