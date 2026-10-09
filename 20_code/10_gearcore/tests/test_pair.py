"""DIN ISO 21771:2014-08 §4.4, §4.5, §5.2 to §5.6 — pair geometry.

References are independent of the code under test: values computed with 45-digit decimal
arithmetic and Taylor series ("decimal reference", no libm, no gearcore; formulas typed from the
norm pages; generator ``scripts/decimal_reference_pair.py``, checked in ``test_adv_2.py``), the
values printed in ISO/TR 6336-30:2022 Annex A example 1 (in
``test_worked_examples.py``), the STplus fixtures (in ``test_stplus_parity.py``), and invariants.
"""

import math
from typing import Any

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from gearcore import involute as iv
from gearcore import pair as pr
from gearcore.errors import GeometryInfeasibleError, InputRangeError, NotSupportedError
from gearcore.models.common import Pair
from gearcore.models.inputs import (
    DimensionKind,
    GearInput,
    PairInput,
    SpanMeasurement,
    ToolProfile,
)
from gearcore.models.results import PairGeometry

SRC = "ISO21771:2014"
CLOSE = 1.0e-12
"""Relative (and absolute) tolerance against a decimal reference; the chains contain differences
of nearly equal terms (g_alpha, inv(alpha_wt) - inv(alpha_t)), which cost a few digits."""

# Decimal references. A: ISO/TR 6336-30 example 1 (z = 17/103, m_n = 8, alpha_n = 20°,
# beta = 15,8°, a_w = 500, d_a = 159,66/872,35, b_w = 100). B: spur, z = 12/40, m_n = 2,
# x = 0,3/-0,1, d_a = 28/83,2, b_w = 20. C: helical, z = 25/40, m_n = 3, alpha_n = 22,5°,
# beta = -30°, x = 0,3/-0,1, d_a = 94,4/144, b_w = 30.
CASES: dict[str, dict[str, Any]] = {
    "A": {"z": (17, 103), "m_n": 8.0, "alpha_n": 20.0, "beta": 15.8, "b": 100.0,
          "d_a": (159.66, 872.35), "a_w": 500.0, "x": (None, 0.0)},
    "B": {"z": (12, 40), "m_n": 2.0, "alpha_n": 20.0, "beta": 0.0, "b": 20.0,
          "d_a": (28.0, 83.2), "a_w": None, "x": (0.3, -0.1)},
    "C": {"z": (25, 40), "m_n": 3.0, "alpha_n": 22.5, "beta": -30.0, "b": 30.0,
          "d_a": (94.4, 144.0), "a_w": None, "x": (0.3, -0.1)},
}  # fmt: skip
REFERENCE: dict[str, dict[str, float]] = {
    "A": {
        "alpha_wt_deg": 21.066099804698517,
        "a_w": 500.0,
        "sum_x": 0.1452220936512015,
        "d_w1": 141.66666666666666,
        "d_w2": 858.3333333333334,
        "p_t": 26.119591815712003,
        "p_bt": 24.43023845986865,
        "T1T2": 179.72237224912726,
        "d_Nf1": 132.920685546483,
        "d_Nf2": 845.2252368254899,
        "g_alpha": 37.84464046282067,
        "g_a1": 19.30218880978518,
        "g_a2": 18.54245165303549,
        "h_w": 16.005,
        "eps_alpha": 1.549090096889056,
        "eps_beta": 1.0833686805697453,
        "K_ga1": 0.3174774630050332,
        "K_ga2": 0.3049815006324512,
        "zeta_f1": -3.1226042716215328,
        "zeta_f2": -1.0095675396542998,
    },
    "B": {
        "alpha_wt_deg": 21.13868827687391,
        "a_w": 52.38927831334764,
        "sum_x": 0.2,
        "d_w1": 24.179666913852756,
        "d_w2": 80.59888971284252,
        "p_t": 6.283185307179586,
        "p_bt": 5.904262868187098,
        "T1T2": 18.892972108605324,
        "d_Nf1": 22.653576724323237,
        "d_Nf2": 78.1051679820969,
        "g_alpha": 7.229131220081783,
        "g_a1": 3.937360026955819,
        "g_a2": 3.291771193125964,
        "h_w": 3.210721686652363,
        "eps_alpha": 1.224391830355867,
        "eps_beta": 0.0,
        "K_ga1": 0.4233778780558875,
        "K_ga2": 0.35395876761330414,
        "zeta_f1": -4.0062919912217305,
        "zeta_f2": -1.6102665034892834,
    },
    "C": {
        "alpha_wt_deg": 26.182356800441667,
        "a_w": 113.17655661808965,
        "sum_x": 0.2,
        "d_w1": 87.0588897062228,
        "d_w2": 139.2942235299565,
        "p_t": 10.882796185405308,
        "p_bt": 9.817621520794615,
        "T1T2": 49.93683971759001,
        "d_Nf1": 83.12303952174517,
        "d_Nf2": 133.50574122587557,
        "g_alpha": 12.300881944540036,
        "g_a1": 7.287223991662883,
        "g_a2": 5.0136579528771525,
        "h_w": 6.023443381910353,
        "eps_alpha": 1.2529391073475025,
        "eps_beta": 1.5915494309189533,
        "K_ga1": 0.27203974290073585,
        "K_ga2": 0.1871651292801412,
        "zeta_f1": -0.5740363667628802,
        "zeta_f2": -0.8082016000448594,
    },
}
NAMES = sorted(CASES)


def close(value: float, reference: float) -> bool:
    return abs(value - reference) <= CLOSE * max(1.0, abs(reference))


def tool() -> ToolProfile:
    return ToolProfile(
        addendum_factor=1.25,
        tip_radius_factor=0.25,
        protuberance_mm=0.0,
        machining_allowance_mm=0.0,
    )


def make_pair(
    case: dict[str, Any], *, chamfer: tuple[float, float] = (0.0, 0.0), **overrides: Any
) -> PairInput:
    gears = [
        GearInput(
            number_of_teeth=case["z"][i],
            profile_shift_coefficient=case["x"][i],
            face_width_mm=case["b"],
            tip_diameter_mm=case["d_a"][i],
            tip_chamfer_radial_mm=chamfer[i],
            tool=tool(),
        )
        for i in range(2)
    ]
    fields: dict[str, Any] = {
        "normal_module_mm": case["m_n"],
        "normal_pressure_angle_deg": case["alpha_n"],
        "helix_angle_deg": case["beta"],
        "centre_distance_mm": case["a_w"],
        "gears": Pair(pinion=gears[0], wheel=gears[1]),
    }
    fields.update(overrides)
    return PairInput(**fields)


def angles(case: dict[str, Any]) -> tuple[float, float]:
    return math.radians(case["alpha_n"]), math.radians(case["beta"])


def base_diameters(case: dict[str, Any]) -> tuple[float, float]:
    alpha_n, beta = angles(case)
    d_b1 = iv.base_diameter(case["z"][0], case["m_n"], alpha_n, beta)
    return d_b1, iv.base_diameter(case["z"][1], case["m_n"], alpha_n, beta)


def working_angle(name: str) -> float:
    return math.radians(REFERENCE[name]["alpha_wt_deg"])


# --- single equations against the decimal references ----------------------------------------------


@pytest.mark.eq(SRC, "(23)")
@pytest.mark.eq(SRC, "(24)")
@pytest.mark.eq(SRC, "(28)")
@pytest.mark.eq(SRC, "(30)")
@pytest.mark.parametrize("name", NAMES)
def test_pitches(name: str) -> None:
    case, ref = CASES[name], REFERENCE[name]
    alpha_n, beta = angles(case)
    assert close(pr.transverse_pitch(case["m_n"], beta), ref["p_t"])
    assert pr.normal_pitch(case["m_n"]) == math.pi * case["m_n"]
    p_bt = pr.transverse_base_pitch(case["m_n"], alpha_n, beta)
    assert close(p_bt, ref["p_bt"])
    assert pr.transverse_contact_pitch(p_bt) == p_bt
    # Eq. (28): p_bt = pi d_b / z
    d_b1, _ = base_diameters(case)
    assert close(p_bt, math.pi * d_b1 / case["z"][0])


@pytest.mark.eq(SRC, "(33)")
@pytest.mark.eq(SRC, "(127)")
def test_tip_diameters() -> None:
    # d = 40, x = 0,5, m_n = 2, h_aP = 2, k = -0,1: d_a = 40 + 2 (1 + 2 - 0,2) = 45,6
    assert pr.tip_diameter(40.0, 0.5, 2.0, 2.0, -0.1) == pytest.approx(45.6, rel=1e-15)
    assert pr.tip_diameter(40.0, 0.0, 2.0, 2.0, 0.0) == 44.0
    assert pr.tip_form_diameter(45.6, 0.3) == pytest.approx(45.0, rel=1e-15)
    assert pr.tip_form_diameter(45.6, 0.0) == 45.6
    with pytest.raises(GeometryInfeasibleError):
        pr.tip_diameter(40.0, -2.0, 2.0, 2.0, -9.0)
    with pytest.raises(InputRangeError):
        pr.tip_form_diameter(45.6, -0.1)
    with pytest.raises(GeometryInfeasibleError):
        pr.tip_form_diameter(45.6, 23.0)


@pytest.mark.eq(SRC, "(52)")
def test_gear_ratio() -> None:
    assert pr.gear_ratio(17, 103) == 103 / 17
    assert pr.gear_ratio(20, 20) == 1.0
    with pytest.raises(InputRangeError, match="index 1 names the pinion"):
        pr.gear_ratio(40, 12)
    with pytest.raises(NotSupportedError):
        pr.gear_ratio(17, -103)
    with pytest.raises(InputRangeError):
        pr.gear_ratio(17, 0)


@pytest.mark.eq(SRC, "(54)")
@pytest.mark.eq(SRC, "(55)")
@pytest.mark.eq(SRC, "(62)")
@pytest.mark.parametrize("name", NAMES)
def test_working_pressure_angle_centre_distance_and_shift_sum(name: str) -> None:
    case, ref = CASES[name], REFERENCE[name]
    z_1, z_2 = case["z"]
    alpha_n, beta = angles(case)
    from_distance = pr.transverse_working_pressure_angle(
        z_1, z_2, case["m_n"], alpha_n, beta, ref["a_w"]
    )
    assert close(math.degrees(from_distance), ref["alpha_wt_deg"])
    from_shift = pr.working_pressure_angle_without_backlash(z_1, z_2, alpha_n, beta, ref["sum_x"])
    assert close(math.degrees(from_shift), ref["alpha_wt_deg"])
    alpha_wt = working_angle(name)
    assert close(pr.centre_distance(z_1, z_2, case["m_n"], alpha_n, beta, alpha_wt), ref["a_w"])
    total = pr.sum_of_profile_shift_coefficients(z_1, z_2, alpha_n, beta, alpha_wt)
    assert close(total, ref["sum_x"])


@pytest.mark.eq(SRC, "(56)")
@pytest.mark.eq(SRC, "(57)")
@pytest.mark.parametrize("name", NAMES)
def test_working_pitch_diameters(name: str) -> None:
    case, ref = CASES[name], REFERENCE[name]
    d_b1, d_b2 = base_diameters(case)
    d_w1 = pr.working_pitch_diameter(d_b1, working_angle(name))
    d_w2 = pr.working_pitch_diameter(d_b2, working_angle(name))
    assert close(d_w1, ref["d_w1"]) and close(d_w2, ref["d_w2"])
    # first form of Eq. (56), (57) as corrected in Anhang NB: d_w1 = 2 a_w z_1 / (z_1 + z_2)
    z_1, z_2 = case["z"]
    assert close(d_w1, 2.0 * ref["a_w"] * z_1 / (z_1 + z_2))
    assert close(d_w1 + d_w2, 2.0 * ref["a_w"])  # Eq. (58)


@pytest.mark.eq(SRC, "(59)")
@pytest.mark.eq(SRC, "(60)")
@pytest.mark.parametrize("name", NAMES)
def test_common_tooth_depth_and_tip_clearance(name: str) -> None:
    case, ref = CASES[name], REFERENCE[name]
    d_a1, d_a2 = case["d_a"]
    assert close(pr.common_tooth_depth(d_a1, d_a2, ref["a_w"]), ref["h_w"])
    assert pr.common_tooth_depth(10.0, 10.0, 12.0) == -2.0, "signed: tip circles do not overlap"
    # Eq. (60): c_1 = a_w - d_fE2 / 2 - d_a1 / 2
    assert pr.tip_clearance(100.0, 60.0, 139.0) == pytest.approx(0.5, rel=1e-15)
    assert pr.tip_clearance(100.0, 62.0, 139.0) < 0.0, "signed: the tip cuts into the root"


@pytest.mark.eq(SRC, "(87)")
@pytest.mark.eq(SRC, "(64)")
@pytest.mark.eq(SRC, "(65)")
@pytest.mark.eq(SRC, "(77)")
@pytest.mark.eq(SRC, "(79)")
@pytest.mark.eq(SRC, "(80)")
@pytest.mark.eq(SRC, "(90)")
@pytest.mark.eq(SRC, "(93)")
@pytest.mark.eq(SRC, "(97)")
@pytest.mark.parametrize("name", NAMES)
def test_mesh_quantities(name: str) -> None:
    case, ref = CASES[name], REFERENCE[name]
    alpha_wt = working_angle(name)
    d_b1, d_b2 = base_diameters(case)
    d_a1, d_a2 = case["d_a"]
    a_w = ref["a_w"]
    assert close(pr.length_between_tangent_points(a_w, alpha_wt), ref["T1T2"])
    assert close(pr.sap_diameter(a_w, alpha_wt, d_a2, d_b2, d_b1), ref["d_Nf1"])
    assert close(pr.sap_diameter(a_w, alpha_wt, d_a1, d_b1, d_b2), ref["d_Nf2"])
    g_alpha = pr.length_of_path_of_contact(d_a1, d_b1, d_a2, d_b2, a_w, alpha_wt)
    assert close(g_alpha, ref["g_alpha"])
    g_a1 = pr.length_of_addendum_path_of_contact(d_a1, d_b1, alpha_wt)
    g_a2 = pr.length_of_addendum_path_of_contact(d_a2, d_b2, alpha_wt)
    assert close(g_a1, ref["g_a1"]) and close(g_a2, ref["g_a2"])
    assert close(g_a1 + g_a2, g_alpha)
    epsilon_alpha = pr.transverse_contact_ratio(g_alpha, ref["p_bt"])
    assert close(epsilon_alpha, ref["eps_alpha"])
    epsilon_beta = pr.overlap_ratio(case["b"], math.radians(case["beta"]), case["m_n"])
    assert close(epsilon_beta, ref["eps_beta"])
    assert pr.total_contact_ratio(epsilon_alpha, epsilon_beta) == epsilon_alpha + epsilon_beta


@pytest.mark.eq(SRC, "(68)")
@pytest.mark.eq(SRC, "(69)")
@pytest.mark.eq(SRC, "(76)")
def test_active_tip_diameter_and_form_over_dimension() -> None:
    case, ref = CASES["B"], REFERENCE["B"]
    alpha_wt = working_angle("B")
    d_b1, d_b2 = base_diameters(case)
    a_w = ref["a_w"]
    # a root form circle of the pinion at the start of the active profile uses the whole wheel tip
    d_Nf1 = ref["d_Nf1"]
    assert close(pr.active_tip_diameter(a_w, alpha_wt, d_Nf1, d_b1, d_b2), case["d_a"][1])
    # a larger root form circle of the pinion shortens the active tip of the wheel
    assert pr.active_tip_diameter(a_w, alpha_wt, d_Nf1 + 0.2, d_b1, d_b2) < case["d_a"][1]
    assert pr.form_over_dimension(22.8, 22.6) == pytest.approx(0.1, rel=1e-13)


@pytest.mark.eq(SRC, "(112)")
@pytest.mark.eq(SRC, "(113)")
@pytest.mark.eq(SRC, "(114)")
@pytest.mark.eq(SRC, "(115)")
@pytest.mark.parametrize("name", NAMES)
def test_sliding(name: str) -> None:
    case, ref = CASES[name], REFERENCE[name]
    u = case["z"][1] / case["z"][0]
    assert close(pr.sliding_factor_at_tip(ref["g_a1"], ref["d_w1"], u), ref["K_ga1"])
    assert close(pr.sliding_factor_at_tip(ref["g_a2"], ref["d_w1"], u), ref["K_ga2"])
    d_b1, d_b2 = base_diameters(case)
    rho_A2 = iv.radius_of_curvature(case["d_a"][1], d_b2)
    rho_E1 = iv.radius_of_curvature(case["d_a"][0], d_b1)
    zeta_f1 = pr.specific_sliding_of_pinion(ref["T1T2"] - rho_A2, rho_A2, u)
    zeta_f2 = pr.specific_sliding_of_wheel(rho_E1, ref["T1T2"] - rho_E1, u)
    assert close(zeta_f1, ref["zeta_f1"]) and close(zeta_f2, ref["zeta_f2"])
    # no sliding in the pitch point: rho_C2 / rho_C1 = u
    rho_C1 = 0.5 * d_b1 * math.tan(working_angle(name))
    assert abs(pr.specific_sliding_of_pinion(rho_C1, u * rho_C1, u)) < 1e-15
    assert abs(pr.specific_sliding_of_wheel(rho_C1, u * rho_C1, u)) < 1e-15
    with pytest.raises(GeometryInfeasibleError):
        pr.specific_sliding_of_pinion(0.0, 5.0, u)  # unbounded at the base circle


# --- orchestrator ---------------------------------------------------------------------------------


@pytest.mark.parametrize("name", NAMES)
def test_compute_pair_geometry_against_the_decimal_references(name: str) -> None:
    case, ref = CASES[name], REFERENCE[name]
    result = pr.compute_pair_geometry(make_pair(case))
    assert isinstance(result, PairGeometry)
    assert close(result.transverse_working_pressure_angle_deg, ref["alpha_wt_deg"])
    assert close(result.centre_distance_mm, ref["a_w"])
    assert close(result.sum_of_profile_shift_coefficients, ref["sum_x"])
    assert close(result.working_pitch_diameter_mm.pinion, ref["d_w1"])
    assert close(result.working_pitch_diameter_mm.wheel, ref["d_w2"])
    assert close(result.sap_diameter_mm.pinion, ref["d_Nf1"])
    assert close(result.sap_diameter_mm.wheel, ref["d_Nf2"])
    assert close(result.length_of_path_of_contact_mm, ref["g_alpha"])
    assert close(result.length_of_addendum_path_of_contact_mm.pinion, ref["g_a1"])
    assert close(result.length_of_addendum_path_of_contact_mm.wheel, ref["g_a2"])
    assert close(result.common_tooth_depth_mm, ref["h_w"])
    assert close(result.transverse_contact_ratio, ref["eps_alpha"])
    assert close(result.overlap_ratio, ref["eps_beta"])
    assert close(result.total_contact_ratio, ref["eps_alpha"] + ref["eps_beta"])
    assert close(result.sliding_factor_at_tip.pinion, ref["K_ga1"])
    assert close(result.sliding_factor_at_tip.wheel, ref["K_ga2"])
    assert close(result.specific_sliding_at_end_points.pinion, ref["zeta_f1"])
    assert close(result.specific_sliding_at_end_points.wheel, ref["zeta_f2"])
    assert result.tip_form_diameter_mm == result.tip_diameter_mm == result.active_tip_diameter_mm
    assert result.contact_face_width_mm == case["b"]
    assert [w.code for w in result.warnings] == ["root_form_diameter_not_checked"]
    # the wheel has the opposite hand of helix
    assert result.gears.wheel.helix_angle_deg == -result.gears.pinion.helix_angle_deg
    assert result.inputs == make_pair(case)
    assert PairGeometry.model_validate_json(result.model_dump_json()) == result


def test_two_of_centre_distance_and_profile_shifts_determine_the_third() -> None:
    """ADR-107: a_w + x_1, a_w + x_2 and x_1 + x_2 describe the same pair."""
    case = CASES["B"]
    reference = pr.compute_pair_geometry(make_pair(case))  # x_1 and x_2 given
    a_w = reference.centre_distance_mm
    with_x1 = pr.compute_pair_geometry(make_pair({**case, "a_w": a_w, "x": (0.3, None)}))
    with_x2 = pr.compute_pair_geometry(make_pair({**case, "a_w": a_w, "x": (None, -0.1)}))
    for other in (with_x1, with_x2):
        assert other.centre_distance_mm == a_w
        assert other.profile_shift_coefficient.pinion == pytest.approx(0.3, abs=1e-13)
        assert other.profile_shift_coefficient.wheel == pytest.approx(-0.1, abs=1e-13)
        assert other.length_of_path_of_contact_mm == pytest.approx(
            reference.length_of_path_of_contact_mm, rel=1e-12
        )
    assert with_x1.profile_shift_coefficient.pinion == 0.3, "a given value is kept exactly"
    assert with_x2.profile_shift_coefficient.wheel == -0.1


def test_three_given_values_are_an_error_in_every_layer() -> None:
    case = {**CASES["B"], "a_w": 52.4}
    with pytest.raises(ValueError, match="only two of the three may be given"):
        make_pair(case)
    # a pair that bypassed the validation is rejected by the computation as well
    valid = make_pair({**CASES["B"], "a_w": 52.4, "x": (0.3, None)})
    wheel = valid.gears.wheel.model_copy(update={"profile_shift_coefficient": -0.1})
    forced = valid.model_copy(update={"gears": Pair(pinion=valid.gears.pinion, wheel=wheel)})
    with pytest.raises(InputRangeError, match="only two of the"):
        pr.compute_pair_geometry(forced)


def test_inputs_the_pair_geometry_cannot_resolve_are_typed_errors() -> None:
    case = CASES["B"]
    missing_tip = make_pair({**case, "d_a": (28.0, None)})
    with pytest.raises(InputRangeError, match="wheel: the mesh needs the tip diameter"):
        pr.compute_pair_geometry(missing_tip)
    valid = make_pair(case)
    # the upper limit of a span without the allowances and without a centre distance leaves
    # the nominal profile shift coefficient open (DIN 21773 §4; ADR-107)
    span = SpanMeasurement(
        kind=DimensionKind.UPPER_LIMIT, span_measurement_mm=9.5, number_of_teeth_spanned=2
    )
    pinion = valid.gears.pinion.model_copy(update={"profile_shift_coefficient": None, "span": span})
    from_span = valid.model_copy(update={"gears": Pair(pinion=pinion, wheel=valid.gears.wheel)})
    with pytest.raises(InputRangeError, match="is not determined"):
        pr.compute_pair_geometry(from_span)
    # a centre distance below the sum of the base radii has no involute mesh
    with pytest.raises(GeometryInfeasibleError, match="cos alpha_wt"):
        pr.compute_pair_geometry(make_pair({**case, "a_w": 48.0, "x": (0.3, None)}))
    # a profile shift that follows from the centre distance and leaves the verified range
    with pytest.raises(GeometryInfeasibleError, match="outside the verified range"):
        pr.compute_pair_geometry(make_pair({**case, "a_w": 58.0, "x": (0.3, None)}))
    # tip circles that do not reach each other
    with pytest.raises(GeometryInfeasibleError, match="the teeth do not mesh"):
        pr.compute_pair_geometry(make_pair({**case, "d_a": (23.0, 76.0)}))
    # a tip circle inside the base circle has no involute
    with pytest.raises(GeometryInfeasibleError, match="does not lie above the base circle"):
        pr.compute_pair_geometry(make_pair({**case, "d_a": (22.0, 83.2)}))
    # a sum of profile shifts without a backlash-free mesh
    with pytest.raises(GeometryInfeasibleError, match="too small for a backlash-free mesh"):
        pr.working_pressure_angle_without_backlash(12, 40, math.radians(20), 0.0, -3.0)


def test_nominal_tip_diameters_are_an_explicit_choice() -> None:
    case = {**CASES["B"], "d_a": (None, None)}
    pair = make_pair(case)
    with pytest.raises(InputRangeError, match="with_nominal_tip_diameters"):
        pr.compute_pair_geometry(pair)
    nominal = pr.with_nominal_tip_diameters(pair, h_aP_mm=2.0)
    # Eq. (33): d_a = z m_n + 2 (x m_n + h_aP)
    assert nominal.gears.pinion.tip_diameter_mm == pytest.approx(24.0 + 2 * (0.6 + 2.0), rel=1e-15)
    assert nominal.gears.wheel.tip_diameter_mm == pytest.approx(80.0 + 2 * (-0.2 + 2.0), rel=1e-15)
    shortened = pr.with_nominal_tip_diameters(pair, h_aP_mm=2.0, k=Pair(pinion=-0.05, wheel=0.0))
    assert shortened.gears.pinion.tip_diameter_mm == pytest.approx(29.0, rel=1e-15)
    kept = pr.with_nominal_tip_diameters(make_pair(CASES["B"]), h_aP_mm=2.0)
    assert kept == make_pair(CASES["B"]), "given tip diameters are kept"
    assert pr.compute_pair_geometry(nominal).tip_diameter_mm.pinion == pytest.approx(
        29.2, rel=1e-15
    )


def test_root_form_diameter_limits_the_active_profile() -> None:
    """Eq. (66) to (69): the active profile cannot start below the root form circle."""
    case, ref = CASES["B"], REFERENCE["B"]
    pair = make_pair(case)
    free = pr.compute_pair_geometry(pair)
    # root form circles below the start of the active profile change nothing
    below: Pair[float] = Pair(pinion=ref["d_Nf1"] - 0.05, wheel=ref["d_Nf2"] - 0.05)
    unchanged = pr.compute_pair_geometry(pair, root_form_diameter_mm=below)
    assert unchanged.sap_diameter_mm == free.sap_diameter_mm and unchanged.warnings == ()
    assert unchanged.root_form_diameter_mm == below
    # a root form circle of the pinion above it: Eq. (66) and (68)
    above: Pair[float] = Pair(pinion=ref["d_Nf1"] + 0.2, wheel=ref["d_Nf2"] - 0.05)
    limited = pr.compute_pair_geometry(pair, root_form_diameter_mm=above)
    assert limited.sap_diameter_mm.pinion == above.pinion
    assert limited.active_tip_diameter_mm.wheel < case["d_a"][1]
    assert limited.active_tip_diameter_mm.pinion == case["d_a"][0]
    assert limited.length_of_path_of_contact_mm < free.length_of_path_of_contact_mm
    assert [w.code for w in limited.warnings] == ["active_profile_limited_by_root_form_circle"]
    # the active tip circle of the wheel meets the pinion at its root form circle
    d_b1, d_b2 = base_diameters(case)
    alpha_wt = working_angle("B")
    assert limited.active_tip_diameter_mm.wheel == pr.active_tip_diameter(
        ref["a_w"], alpha_wt, above.pinion, d_b1, d_b2
    )
    with pytest.raises(GeometryInfeasibleError, match="below the base circle"):
        pr.compute_pair_geometry(pair, root_form_diameter_mm=Pair(pinion=20.0, wheel=77.0))


def test_mating_tip_beyond_the_tangent_point_is_interference() -> None:
    """z = 12 without profile shift: the tip of the wheel reaches beyond T_1 (undercut case)."""
    case = {**CASES["B"], "x": (0.0, 0.0), "d_a": (28.0, 84.0)}
    pair = make_pair(case)
    with pytest.raises(GeometryInfeasibleError, match="interference"):
        pr.compute_pair_geometry(pair)
    # with the root form circle of the generated (undercut) pinion the mesh is defined
    d_b1, _ = base_diameters(case)
    limited = pr.compute_pair_geometry(
        pair, root_form_diameter_mm=Pair(pinion=d_b1 + 0.1, wheel=76.5)
    )
    assert limited.sap_diameter_mm.pinion == d_b1 + 0.1
    assert limited.active_tip_diameter_mm.wheel < 84.0


def test_tip_form_diameter_from_chamfer_or_from_the_generation() -> None:
    case = CASES["B"]
    chamfered = pr.compute_pair_geometry(make_pair(case, chamfer=(0.0, 0.3)))
    assert chamfered.tip_form_diameter_mm.wheel == pytest.approx(83.2 - 0.6, rel=1e-15)
    given = pr.compute_pair_geometry(
        make_pair(case), tip_form_diameter_mm=Pair(pinion=28.0, wheel=82.6)
    )
    assert given.sap_diameter_mm.pinion == pytest.approx(
        chamfered.sap_diameter_mm.pinion, rel=1e-14
    )
    assert given.sap_diameter_mm.wheel == chamfered.sap_diameter_mm.wheel
    # ADR-112: the common tooth depth follows the tip form circles; the note names the value of
    # the tip circles (Eq. (59) by its letter)
    free = pr.compute_pair_geometry(make_pair(case))
    assert given.common_tooth_depth_mm == pytest.approx(chamfered.common_tooth_depth_mm, rel=1e-14)
    assert chamfered.common_tooth_depth_mm == pytest.approx(
        free.common_tooth_depth_mm - 0.3, rel=1e-13
    )
    noted = [w for w in chamfered.warnings if w.code == "common_tooth_depth_with_tip_form_circles"]
    assert len(noted) == 1 and repr(free.common_tooth_depth_mm) in noted[0].message
    assert not [w for w in free.warnings if w.field == "common_tooth_depth_mm"]
    with pytest.raises(InputRangeError, match="exceeds the tip diameter"):
        pr.compute_pair_geometry(
            make_pair(case), tip_form_diameter_mm=Pair(pinion=28.0, wheel=83.3)
        )
    # a tool with an edge break flank generates d_Fa: without it the result says so
    breaking = tool().model_copy(update={"edge_break_angle_deg": 45.0})
    pair = make_pair(case)
    wheel = pair.gears.wheel.model_copy(update={"tool": breaking})
    warned = pr.compute_pair_geometry(
        pair.model_copy(update={"gears": Pair(pinion=pair.gears.pinion, wheel=wheel)})
    )
    assert "tip_form_diameter_not_generated" in [w.code for w in warned.warnings]


def test_contact_ratio_below_one_is_a_warning() -> None:
    case = {**CASES["B"], "d_a": (26.6, 81.4)}
    result = pr.compute_pair_geometry(make_pair(case))
    assert result.transverse_contact_ratio < 1.0
    assert "transverse_contact_ratio_below_one" in [w.code for w in result.warnings]


def test_face_widths_and_hand_of_helix() -> None:
    case = CASES["C"]
    pair = make_pair(case)
    narrow = pair.gears.pinion.model_copy(update={"face_width_mm": 24.0})
    result = pr.compute_pair_geometry(
        pair.model_copy(update={"gears": Pair(pinion=narrow, wheel=pair.gears.wheel)})
    )
    assert result.contact_face_width_mm == 24.0
    assert result.overlap_ratio == pytest.approx(
        REFERENCE["C"]["eps_beta"] * 24.0 / 30.0, rel=1e-14
    )
    mirrored = pr.compute_pair_geometry(make_pair({**case, "beta": 30.0}))
    original = pr.compute_pair_geometry(pair)
    for field in ("centre_distance_mm", "length_of_path_of_contact_mm", "overlap_ratio"):
        assert getattr(mirrored, field) == getattr(original, field), field
    assert mirrored.gears.pinion.base_helix_angle_deg == -original.gears.pinion.base_helix_angle_deg


@pytest.mark.parametrize(
    "call",
    [
        lambda: pr.transverse_pitch(0.0, 0.1),
        lambda: pr.normal_pitch(math.nan),
        lambda: pr.transverse_working_pressure_angle(17, 103, 8.0, 0.35, 0.2, 0.0),
        lambda: pr.centre_distance(17, 103, 8.0, 0.35, 0.2, math.pi / 2),
        lambda: pr.working_pitch_diameter(-1.0, 0.3),
        lambda: pr.working_pitch_diameter(10.0, math.inf),
        lambda: pr.overlap_ratio(10.0, math.pi / 2, 1.0),
        lambda: pr.overlap_ratio(0.0, 0.2, 1.0),
        lambda: pr.transverse_contact_ratio(5.0, 0.0),
        lambda: pr.sliding_factor_at_tip(1.0, 0.0, 2.0),
        lambda: pr.length_between_tangent_points(True, 0.3),
        lambda: pr.gear_ratio(17.0, 103),  # type: ignore[arg-type]
        lambda: pr.tip_clearance(100.0, "60", 139.0),  # type: ignore[arg-type]
    ],
)
def test_invalid_arguments_are_input_errors(call: Any) -> None:
    with pytest.raises(InputRangeError):
        call()


def test_diameters_below_the_base_circle_are_infeasible() -> None:
    with pytest.raises(GeometryInfeasibleError, match="below the base circle"):
        pr.length_of_addendum_path_of_contact(22.0, 22.5, 0.35)
    with pytest.raises(GeometryInfeasibleError, match="below the base circle"):
        pr.length_of_path_of_contact(22.0, 22.5, 83.0, 75.0, 52.0, 0.35)
    # on the base circle within the rounding tolerance the roll length is zero
    assert pr.length_of_addendum_path_of_contact(22.5 * (1 - 1e-13), 22.5, 0.0) == 0.0


# --- properties -----------------------------------------------------------------------------------

pairs_by_shift = st.tuples(
    st.integers(12, 60),
    st.integers(0, 90),
    st.sampled_from([0.5, 1.0, 2.0, 3.5, 8.0]),
    st.floats(15.0, 25.0),
    st.floats(-35.0, 35.0),
    st.floats(-0.3, 0.8),
    st.floats(-0.3, 0.8),
)


@given(pairs_by_shift)
def test_pair_invariants(values: tuple[int, int, float, float, float, float, float]) -> None:
    z_1, more, m_n, alpha_n_deg, beta_deg, x_1, x_2 = values
    z_2 = z_1 + more
    alpha_n, beta = math.radians(alpha_n_deg), math.radians(beta_deg)
    alpha_t = iv.transverse_pressure_angle(alpha_n, beta)
    assume(iv.inv(alpha_t) + 2 * math.tan(alpha_n) * (x_1 + x_2) / (z_1 + z_2) > 1e-4)
    alpha_wt = pr.working_pressure_angle_without_backlash(z_1, z_2, alpha_n, beta, x_1 + x_2)
    a_w = pr.centre_distance(z_1, z_2, m_n, alpha_n, beta, alpha_wt)
    # a_w -> alpha_wt -> sum of x -> the same pair
    back = pr.transverse_working_pressure_angle(z_1, z_2, m_n, alpha_n, beta, a_w)
    assert back == pytest.approx(alpha_wt, abs=1e-13)
    total = pr.sum_of_profile_shift_coefficients(z_1, z_2, alpha_n, beta, alpha_wt)
    assert total == pytest.approx(x_1 + x_2, abs=2e-12)
    d_b1 = iv.base_diameter(z_1, m_n, alpha_n, beta)
    d_b2 = iv.base_diameter(z_2, m_n, alpha_n, beta)
    d_w1 = pr.working_pitch_diameter(d_b1, alpha_wt)
    d_w2 = pr.working_pitch_diameter(d_b2, alpha_wt)
    assert d_w1 + d_w2 == pytest.approx(2.0 * a_w, rel=1e-12)  # Eq. (58)
    assert d_w2 / d_w1 == pytest.approx(pr.gear_ratio(z_1, z_2), rel=1e-12)
    p_bt = pr.transverse_base_pitch(m_n, alpha_n, beta)
    assert p_bt == pytest.approx(math.pi * d_b1 / z_1, rel=1e-12)
    # tangent points: rho_C1 + rho_C2 = a_w sin(alpha_wt) (Eq. (81), (82), (87))
    rho_c = 0.5 * (d_b1 + d_b2) * math.tan(alpha_wt)
    assert rho_c == pytest.approx(pr.length_between_tangent_points(a_w, alpha_wt), rel=1e-11)
    # mesh with nominal tips (h_aP = m_n): the point of the pinion at d_Nf1 mates the wheel tip
    d_a1 = pr.tip_diameter(iv.reference_diameter(z_1, m_n, beta), x_1, m_n, m_n, 0.0)
    d_a2 = pr.tip_diameter(iv.reference_diameter(z_2, m_n, beta), x_2, m_n, m_n, 0.0)
    assume(d_a1 > d_b1 * 1.001 and d_a2 > d_b2 * 1.001)
    reach = math.sqrt(d_a2**2 - d_b2**2)
    assume(2.0 * a_w * math.sin(alpha_wt) - reach > 1e-6 * m_n)
    d_Nf1 = pr.sap_diameter(a_w, alpha_wt, d_a2, d_b2, d_b1)
    assert d_Nf1 >= d_b1
    # conditioning: the root of a difference of squares close to the base circle
    assert math.sqrt(max(d_Nf1**2 - d_b1**2, 0.0)) + reach == pytest.approx(
        2.0 * a_w * math.sin(alpha_wt), rel=1e-10
    )
    g_a1 = pr.length_of_addendum_path_of_contact(d_a1, d_b1, alpha_wt)
    g_a2 = pr.length_of_addendum_path_of_contact(d_a2, d_b2, alpha_wt)
    g_alpha = pr.length_of_path_of_contact(d_a1, d_b1, d_a2, d_b2, a_w, alpha_wt)
    assert g_a1 + g_a2 == pytest.approx(g_alpha, abs=1e-14 * a_w)
    for value in (alpha_wt, a_w, total, d_w1, d_w2, d_Nf1, g_alpha):
        assert isinstance(value, float) and math.isfinite(value)


@given(st.floats(-1e-9, 1e-9))
def test_helix_angle_is_continuous_at_zero(beta_deg: float) -> None:
    case = {**CASES["B"], "beta": beta_deg}
    spur = pr.compute_pair_geometry(make_pair({**case, "beta": 0.0}))
    near = pr.compute_pair_geometry(make_pair(case))
    assert near.centre_distance_mm == pytest.approx(spur.centre_distance_mm, rel=1e-12)
    assert near.transverse_contact_ratio == pytest.approx(spur.transverse_contact_ratio, rel=1e-12)
    assert near.overlap_ratio == pytest.approx(0.0, abs=1e-9)
