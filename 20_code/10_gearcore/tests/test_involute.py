"""DIN ISO 21771:2014-08 §4.2, §4.3, §4.7 — unit tests.

References are independent of the code under test: the values printed in ISO/TR 6336-30:2022
(Annex A, example 1; tolerance = half a unit of the last printed digit) and values computed with
45-digit decimal arithmetic and Taylor series ("decimal reference", no libm, no gearcore).
"""

import math

import pytest
from scipy.optimize import brentq

from gearcore import involute as iv
from gearcore.data import load_worked_example, printed_tolerance
from gearcore.errors import (
    GeometryInfeasibleError,
    InputRangeError,
    NotSupportedError,
    SolverError,
)

SRC = "ISO21771:2014"
EXAMPLE = load_worked_example("iso_tr_6336_30_2022_annex_a_example_1")
IN = EXAMPLE["inputs"]
EXP = EXAMPLE["expected"]
ALPHA_N = math.radians(IN["normal_pressure_angle_deg"]["value"])
BETA = math.radians(IN["helix_angle_deg"]["value"])
M_N = IN["normal_module_mm"]["value"]
ULP = math.ulp(1.0)
CLOSE = 16 * ULP
"""Relative tolerance against a decimal reference: a chain of about ten rounded operations."""

# Decimal references. Case A: z = 17, m_n = 8, alpha_n = 20°, beta = 15,8°, x = 0,14522 (pinion of
# ISO/TR 6336-30 example 1). Case B: z = 25, m_n = 3, alpha_n = 20°, beta = 30°, x = 0,3.
REFERENCE = {
    "A": {
        "args": (17, 8.0, 15.8, 0.14522),
        "m_t": 8.3141242980263578,
        "d": 141.34011306644808,
        "d_b": 132.19856920126215,
        "alpha_t_deg": 20.719711765850834,
        "beta_b_deg": 14.824534684016514,
        "inv_alpha_t": 0.01663453068056688,
        "s_t": 13.938694581970712,
        "e_t": 12.18089723374129,
        "s_n": 13.41206273308138,
        "e_n": 11.720678495636966,
        "psi_deg": 5.6504013909577866,
        "eta_deg": 4.9378339031598604,
        "psi_b_deg": 6.6034897931351498,
        "eta_b_deg": 3.9847455009824973,
        "d_y": 148.40711871977049,
        "alpha_yt_deg": 27.028170071206116,
        "s_yt": 11.403349122739664,
        "rho_y": 33.720213477390508,
        "beta_y_deg": 16.547740169191937,
    },
    "B": {
        "args": (25, 3.0, 30.0, 0.3),
        "m_t": 3.4641016151377546,
        "d": 86.602540378443865,
        "d_b": 79.83810541369732,
        "alpha_t_deg": 22.795877258858474,
        "beta_b_deg": 28.024320673604696,
        "inv_alpha_t": 0.022413511413626085,
        "s_t": 6.1978960185328247,
        "e_t": 4.6849001668724824,
        "s_n": 5.3675354020638541,
        "e_n": 4.0572425587055256,
        "psi_deg": 4.10049499900419,
        "eta_deg": 3.09950500099581,
        "psi_b_deg": 5.3846946070732642,
        "eta_b_deg": 1.8153053929267358,
        "d_y": 90.932667397366058,
        "alpha_yt_deg": 28.598984439677599,
        "s_yt": 4.3586196711557476,
        "rho_y": 21.763656195314211,
        "beta_y_deg": 31.224988638308451,
    },
}
INV_ALPHA_20_DEG = 0.014904383867336446  # decimal reference


def tol(entry: dict[str, float]) -> float:
    """Half a unit of the last printed digit (+ representation slack of the decimal literal)."""
    return printed_tolerance(int(entry["decimals"])) + 1e-9


# --- worked example of the norm ------------------------------------------------------------------


@pytest.mark.eq(SRC, "(2)")
def test_transverse_module_matches_worked_example() -> None:
    entry = EXP["transverse_module_mm"]
    assert abs(iv.transverse_module(M_N, BETA) - entry["value"]) <= tol(entry)


@pytest.mark.eq(SRC, "(1)")
@pytest.mark.parametrize("role", ["pinion", "wheel"])
def test_reference_diameter_matches_worked_example(role: str) -> None:
    entry = EXP["reference_diameter_mm"]
    assert abs(iv.reference_diameter(IN["number_of_teeth"][role], M_N, BETA) - entry[role]) <= tol(
        entry
    )


@pytest.mark.eq(SRC, "(14)")
def test_transverse_pressure_angle_matches_worked_example() -> None:
    entry = EXP["transverse_pressure_angle_deg"]
    alpha_t = iv.transverse_pressure_angle(ALPHA_N, BETA)
    assert abs(math.degrees(alpha_t) - entry["value"]) <= tol(entry)


@pytest.mark.eq(SRC, "(18)")
def test_involute_function_matches_worked_example() -> None:
    assert abs(iv.inv(ALPHA_N) - EXP["inv_alpha_n_rad"]["value"]) <= tol(EXP["inv_alpha_n_rad"])
    alpha_t = iv.transverse_pressure_angle(ALPHA_N, BETA)
    assert abs(iv.inv(alpha_t) - EXP["inv_alpha_t_rad"]["value"]) <= tol(EXP["inv_alpha_t_rad"])


@pytest.mark.eq(SRC, "(19)")
@pytest.mark.parametrize("role", ["pinion", "wheel"])
def test_base_diameter_matches_worked_example(role: str) -> None:
    entry = EXP["base_diameter_mm"]
    assert abs(
        iv.base_diameter(IN["number_of_teeth"][role], M_N, ALPHA_N, BETA) - entry[role]
    ) <= tol(entry)


@pytest.mark.eq(SRC, "(6)")
def test_base_helix_angle_matches_worked_example() -> None:
    entry = EXP["base_helix_angle_deg"]
    assert abs(math.degrees(iv.base_helix_angle(BETA, ALPHA_N)) - entry["value"]) <= tol(entry)


# --- decimal references --------------------------------------------------------------------------


@pytest.mark.eq(SRC, "(1)")
@pytest.mark.eq(SRC, "(2)")
@pytest.mark.eq(SRC, "(6)")
@pytest.mark.eq(SRC, "(14)")
@pytest.mark.eq(SRC, "(19)")
@pytest.mark.eq(SRC, "(39)")
@pytest.mark.eq(SRC, "(41)")
@pytest.mark.eq(SRC, "(42)")
@pytest.mark.eq(SRC, "(44)")
@pytest.mark.eq(SRC, "(46)")
@pytest.mark.eq(SRC, "(47)")
@pytest.mark.eq(SRC, "(49)")
@pytest.mark.eq(SRC, "(51)")
@pytest.mark.parametrize("case", sorted(REFERENCE))
def test_basic_geometry_against_decimal_references(case: str) -> None:
    reference = REFERENCE[case]
    z, m_n, beta_deg, x = reference["args"]  # type: ignore[misc]
    result = iv.compute_basic_gear_geometry(
        number_of_teeth=z,
        normal_module_mm=m_n,
        normal_pressure_angle_deg=20.0,
        helix_angle_deg=beta_deg,
        profile_shift_coefficient=x,
    )
    expected = {
        "transverse_module_mm": "m_t",
        "reference_diameter_mm": "d",
        "base_diameter_mm": "d_b",
        "transverse_pressure_angle_deg": "alpha_t_deg",
        "base_helix_angle_deg": "beta_b_deg",
        "transverse_tooth_thickness_mm": "s_t",
        "transverse_space_width_mm": "e_t",
        "normal_tooth_thickness_mm": "s_n",
        "normal_space_width_mm": "e_n",
        "tooth_thickness_half_angle_deg": "psi_deg",
        "space_width_half_angle_deg": "eta_deg",
        "base_tooth_thickness_half_angle_deg": "psi_b_deg",
        "base_space_width_half_angle_deg": "eta_b_deg",
    }
    for field, key in expected.items():
        assert getattr(result, field) == pytest.approx(reference[key], rel=CLOSE), field
    assert result.warnings == ()


@pytest.mark.eq(SRC, "(8)")
@pytest.mark.eq(SRC, "(12)")
@pytest.mark.eq(SRC, "(17)")
@pytest.mark.eq(SRC, "(18)")
@pytest.mark.eq(SRC, "(38)")
@pytest.mark.eq(SRC, "(40)")
@pytest.mark.parametrize("case", sorted(REFERENCE))
def test_quantities_at_a_diameter_against_decimal_references(case: str) -> None:
    """At d_y = 1,05 d: profile angle, helix angle, radius of curvature and tooth thickness."""
    reference = REFERENCE[case]
    z, m_n, beta_deg, x = reference["args"]  # type: ignore[misc]
    beta = math.radians(beta_deg)
    d = iv.reference_diameter(z, m_n, beta)
    d_b = iv.base_diameter(z, m_n, ALPHA_N, beta)
    d_y = reference["d_y"]
    assert d_y == pytest.approx(1.05 * d, rel=4 * ULP)
    alpha_t = iv.transverse_pressure_angle(ALPHA_N, beta)
    alpha_yt = iv.transverse_profile_angle_at(d_y, d_b)  # type: ignore[arg-type]
    assert math.degrees(alpha_yt) == pytest.approx(reference["alpha_yt_deg"], rel=CLOSE)
    assert iv.inv(alpha_t) == pytest.approx(reference["inv_alpha_t"], rel=64 * ULP)
    assert iv.radius_of_curvature(d_y, d_b) == pytest.approx(reference["rho_y"], rel=CLOSE)  # type: ignore[arg-type]
    assert math.degrees(iv.helix_angle_at(d_y, d, beta)) == pytest.approx(  # type: ignore[arg-type]
        reference["beta_y_deg"], rel=CLOSE
    )
    psi = iv.tooth_thickness_half_angle(z, x, ALPHA_N)
    psi_y = iv.tooth_thickness_half_angle_at(psi, alpha_t, alpha_yt)
    # psi_y is a difference of nearly equal terms: absolute accuracy of inv, relative 1e-14
    assert iv.transverse_tooth_thickness_at(d_y, psi_y) == pytest.approx(  # type: ignore[arg-type]
        reference["s_yt"], rel=1e-14
    )


@pytest.mark.eq(SRC, "(18)")
def test_involute_function_against_the_decimal_reference() -> None:
    assert iv.inv(ALPHA_N) == pytest.approx(INV_ALPHA_20_DEG, abs=2 * math.ulp(math.tan(ALPHA_N)))
    assert iv.inv(0.0) == 0.0


# --- identities between alternative forms of the norm --------------------------------------------


@pytest.mark.eq(SRC, "(20)")
def test_base_diameter_alternative_form_eq_20() -> None:
    """(20): d_b = |z| m_n cos(alpha_n) / cos(beta_b) equals (19)."""
    beta_b = iv.base_helix_angle(BETA, ALPHA_N)
    for z in (17, 103):
        eq20 = z * M_N * math.cos(ALPHA_N) / math.cos(beta_b)
        assert iv.base_diameter(z, M_N, ALPHA_N, BETA) == pytest.approx(eq20, rel=4 * ULP)


@pytest.mark.eq(SRC, "(5)")
@pytest.mark.eq(SRC, "(7)")
def test_base_helix_angle_forms_5_and_7_agree_with_6() -> None:
    alpha_t = iv.transverse_pressure_angle(ALPHA_N, BETA)
    beta_b = iv.base_helix_angle(BETA, ALPHA_N)
    assert math.tan(beta_b) == pytest.approx(math.tan(BETA) * math.cos(alpha_t), rel=4 * ULP)
    assert math.cos(beta_b) == pytest.approx(
        math.cos(BETA) * math.cos(ALPHA_N) / math.cos(alpha_t), rel=4 * ULP
    )
    assert math.cos(beta_b) == pytest.approx(
        math.cos(ALPHA_N) * math.sqrt(math.tan(ALPHA_N) ** 2 + math.cos(BETA) ** 2), rel=4 * ULP
    )


@pytest.mark.eq(SRC, "(12)")
@pytest.mark.eq(SRC, "(8)")
@pytest.mark.eq(SRC, "(15)")
def test_angles_at_the_reference_cylinder_reduce_to_the_reference_values() -> None:
    d = iv.reference_diameter(17, M_N, BETA)
    d_b = iv.base_diameter(17, M_N, ALPHA_N, BETA)
    alpha_t = iv.transverse_pressure_angle(ALPHA_N, BETA)
    # acos near cos = 0.935 amplifies one ulp of the ratio by 1 / sin(alpha_t) = 2.8
    assert iv.transverse_profile_angle_at(d, d_b) == pytest.approx(alpha_t, abs=8 * ULP)
    assert iv.helix_angle_at(d, d, BETA) == pytest.approx(BETA, abs=ULP)
    assert iv.normal_profile_angle_at(alpha_t, BETA) == pytest.approx(ALPHA_N, abs=2 * ULP)
    assert iv.helix_angle_at(d_b, d, BETA) == pytest.approx(
        iv.base_helix_angle(BETA, ALPHA_N), abs=2 * ULP
    )
    assert iv.transverse_profile_angle_at(d_b, d_b) == 0.0


@pytest.mark.eq(SRC, "(16)")
@pytest.mark.eq(SRC, "(17)")
def test_roll_angle_and_radius_of_curvature_are_consistent() -> None:
    d_b = iv.base_diameter(17, M_N, ALPHA_N, BETA)
    d_y = 150.0
    alpha_yt = iv.transverse_profile_angle_at(d_y, d_b)
    assert iv.radius_of_curvature(d_y, d_b) == pytest.approx(
        0.5 * d_b * iv.roll_angle(alpha_yt), rel=8 * ULP
    )
    assert iv.radius_of_curvature(d_b, d_b) == 0.0


@pytest.mark.eq(SRC, "(39)")
@pytest.mark.eq(SRC, "(44)")
@pytest.mark.eq(SRC, "(49)")
@pytest.mark.eq(SRC, "(51)")
def test_tooth_thickness_and_space_width_add_up_to_the_pitch() -> None:
    x = IN["profile_shift_coefficient"]["pinion"]
    s_t = iv.transverse_tooth_thickness(M_N, x, ALPHA_N, BETA)
    e_t = iv.transverse_space_width(M_N, x, ALPHA_N, BETA)
    s_n = iv.normal_tooth_thickness(M_N, x, ALPHA_N)
    e_n = iv.normal_space_width(M_N, x, ALPHA_N)
    assert s_t + e_t == pytest.approx(math.pi * iv.transverse_module(M_N, BETA), rel=4 * ULP)
    assert s_n + e_n == pytest.approx(math.pi * M_N, rel=4 * ULP)
    assert s_n == pytest.approx(s_t * math.cos(BETA), rel=4 * ULP)
    assert e_n == pytest.approx(e_t * math.cos(BETA), rel=4 * ULP)


@pytest.mark.eq(SRC, "(38)")
@pytest.mark.eq(SRC, "(40)")
@pytest.mark.eq(SRC, "(41)")
@pytest.mark.eq(SRC, "(42)")
@pytest.mark.eq(SRC, "(43)")
@pytest.mark.eq(SRC, "(45)")
@pytest.mark.eq(SRC, "(46)")
@pytest.mark.eq(SRC, "(47)")
@pytest.mark.eq(SRC, "(48)")
@pytest.mark.eq(SRC, "(50)")
def test_half_angles_and_arc_thickness_at_any_diameter() -> None:
    z, x = 17, IN["profile_shift_coefficient"]["pinion"]
    d = iv.reference_diameter(z, M_N, BETA)
    d_b = iv.base_diameter(z, M_N, ALPHA_N, BETA)
    alpha_t = iv.transverse_pressure_angle(ALPHA_N, BETA)
    psi = iv.tooth_thickness_half_angle(z, x, ALPHA_N)
    eta = iv.space_width_half_angle(z, x, ALPHA_N)
    assert psi + eta == pytest.approx(math.pi / z, rel=4 * ULP)
    # at the reference circle the general forms reduce to (39)/(44)
    assert iv.tooth_thickness_half_angle_at(psi, alpha_t, alpha_t) == psi
    assert iv.transverse_tooth_thickness_at(d, psi) == pytest.approx(
        iv.transverse_tooth_thickness(M_N, x, ALPHA_N, BETA), rel=4 * ULP
    )
    assert iv.transverse_space_width_at(d, eta) == pytest.approx(
        iv.transverse_space_width(M_N, x, ALPHA_N, BETA), rel=4 * ULP
    )
    # at the base circle: (42) and (47)
    assert iv.tooth_thickness_half_angle_at(
        psi, alpha_t, 0.0
    ) == iv.base_tooth_thickness_half_angle(psi, alpha_t)
    assert iv.space_width_half_angle_at(eta, alpha_t, 0.0) == iv.base_space_width_half_angle(
        eta, alpha_t
    )
    # tooth gets thinner towards the tip, space wider; their sum stays the pitch angle
    previous = math.inf
    for d_y in (d_b, d, 150.0, IN["tip_diameter_mm"]["pinion"]):
        alpha_yt = iv.transverse_profile_angle_at(d_y, d_b)
        psi_y = iv.tooth_thickness_half_angle_at(psi, alpha_t, alpha_yt)
        eta_y = iv.space_width_half_angle_at(eta, alpha_t, alpha_yt)
        assert psi_y < previous
        assert psi_y + eta_y == pytest.approx(math.pi / z, rel=8 * ULP)
        beta_y = iv.helix_angle_at(d_y, d, BETA)
        s_yt = iv.transverse_tooth_thickness_at(d_y, psi_y)
        e_yt = iv.transverse_space_width_at(d_y, eta_y)
        assert s_yt + e_yt == pytest.approx(math.pi * d_y / z, rel=8 * ULP)
        s_yn = iv.normal_tooth_thickness_at(s_yt, beta_y)
        e_yn = iv.normal_space_width_at(e_yt, beta_y)
        assert 0.0 < s_yn < s_yt and 0.0 < e_yn < e_yt
        assert s_yn / s_yt == pytest.approx(e_yn / e_yt, rel=4 * ULP)
        previous = psi_y


# --- inverse involute ----------------------------------------------------------------------------


def _inverse_bound(alpha: float) -> float:
    tangent = math.tan(alpha)
    return 8.0 * math.ulp(tangent) / (tangent * tangent) + 1.0e-15


@pytest.mark.eq(SRC, "(18)")
@pytest.mark.parametrize("deg", [0.1, 0.5, 5.0, 14.5, 20.0, 25.0, 45.0, 70.0, 88.999])
def test_inverse_involute_agrees_with_brentq(deg: float) -> None:
    alpha = math.radians(deg)
    value = math.tan(alpha) - alpha
    ours = iv.inv_inverse(value)
    reference = brentq(
        lambda a: math.tan(a) - a - value, 0.0, math.radians(89.0), xtol=1e-16, rtol=4 * ULP
    )
    assert abs(ours - alpha) <= _inverse_bound(alpha)
    assert abs(ours - reference) <= 2.0 * _inverse_bound(alpha)


@pytest.mark.eq(SRC, "(18)")
def test_inverse_involute_of_the_decimal_reference() -> None:
    assert iv.inv_inverse(INV_ALPHA_20_DEG) == pytest.approx(ALPHA_N, abs=4 * ULP)
    assert iv.inv_inverse(REFERENCE["A"]["inv_alpha_t"]) == pytest.approx(  # type: ignore[arg-type]
        math.radians(REFERENCE["A"]["alpha_t_deg"]),  # type: ignore[arg-type]
        abs=4 * ULP,
    )


@pytest.mark.eq(SRC, "(18)")
def test_inverse_involute_terminates_at_the_rounding_level() -> None:
    """Regression: for inv = 2^-8 the Newton step alternated by +-19 ulp of alpha, because the
    residual alternated by +-1 ulp of tan(alpha); neither termination criterion was met."""
    alpha = iv.inv_inverse(0.00390625)
    tangent = math.tan(alpha)
    assert abs(tangent - alpha - 0.00390625) <= 4.0 * math.ulp(tangent)


@pytest.mark.eq(SRC, "(18)")
def test_inverse_involute_is_accurate_to_its_conditioning_on_a_dense_sweep() -> None:
    """0.01 deg steps up to 89 deg: the error stays within the rounding of tan mapped to the angle."""
    worst = 0.0
    for step in range(1, 8901):
        alpha = math.radians(step / 100.0)
        bound = _inverse_bound(alpha)
        error = abs(iv.inv_inverse(math.tan(alpha) - alpha) - alpha)
        assert error <= bound, f"alpha = {step / 100.0} deg: error {error:.3e} > bound {bound:.3e}"
        worst = max(worst, error / bound)
    assert 0.0 < worst < 0.75


@pytest.mark.eq(SRC, "(18)")
def test_inverse_involute_converges_for_powers_of_two_and_subnormals() -> None:
    for exponent in range(-1074, 6):
        value = math.ldexp(1.0, exponent)
        alpha = iv.inv_inverse(value)
        assert 0.0 < alpha < iv.INV_ALPHA_MAX_RAD
        tangent = math.tan(alpha)
        assert abs(tangent - alpha - value) <= 4.0 * math.ulp(tangent) + 3.6e-13


def test_inverse_involute_domain() -> None:
    assert iv.inv_inverse(0.0) == 0.0
    assert iv.inv_inverse(iv.INV_MAX) == pytest.approx(iv.INV_ALPHA_MAX_RAD, abs=4 * ULP)
    below = math.nextafter(iv.INV_MAX, 0.0)
    assert iv.inv_inverse(below) <= iv.INV_ALPHA_MAX_RAD
    with pytest.raises(SolverError, match=">= 0"):
        iv.inv_inverse(-1e-12)
    with pytest.raises(SolverError, match="exceeds"):
        iv.inv_inverse(math.nextafter(iv.INV_MAX, math.inf))
    for bad in (math.nan, math.inf, -math.inf):
        with pytest.raises(InputRangeError, match="finite"):
            iv.inv_inverse(bad)


@pytest.mark.eq(SRC, "(18)")
@pytest.mark.parametrize("alpha", [1e-7, 1e-6, 1e-5, 1e-4, 1e-3])
def test_inverse_involute_conditioning_for_tiny_angles(alpha: float) -> None:
    """tan(a) - a cancels for tiny a: inv carries an absolute error of about 1e-16 * a, which the
    inverse maps to about 1e-16 / a in the angle. The round trip stays within that bound."""
    assert iv.inv_inverse(iv.inv(alpha)) == pytest.approx(alpha, abs=4e-16 / alpha + 1e-15)
    assert iv.inv(alpha) == pytest.approx(alpha**3 / 3.0, abs=4e-16 * alpha + alpha**5)


# --- guards --------------------------------------------------------------------------------------


def test_pointed_tooth_and_base_circle_are_typed_errors() -> None:
    z, x = 17, 0.0
    d_b = iv.base_diameter(z, M_N, ALPHA_N, 0.0)
    alpha_t = ALPHA_N
    psi = iv.tooth_thickness_half_angle(z, x, ALPHA_N)
    far_outside = iv.transverse_profile_angle_at(1.6 * d_b, d_b)
    with pytest.raises(GeometryInfeasibleError, match="flanks intersect"):
        iv.tooth_thickness_half_angle_at(psi, alpha_t, far_outside)
    with pytest.raises(GeometryInfeasibleError, match="below the base circle"):
        iv.transverse_profile_angle_at(0.99 * d_b, d_b)
    with pytest.raises(GeometryInfeasibleError, match="below the base circle"):
        iv.radius_of_curvature(0.99 * d_b, d_b)


def test_input_guards_raise_typed_errors() -> None:
    with pytest.raises(NotSupportedError, match="internal"):
        iv.reference_diameter(-52, 1.0, 0.0)
    with pytest.raises(InputRangeError, match="zero"):
        iv.reference_diameter(0, 1.0, 0.0)
    for bad in (17.5, 17.0, True, "17", None):
        with pytest.raises(InputRangeError, match="integer"):
            iv.reference_diameter(bad, 1.0, 0.0)  # type: ignore[arg-type]
    with pytest.raises(InputRangeError, match="> 0"):
        iv.transverse_module(0.0, 0.0)
    with pytest.raises(InputRangeError, match="< 90"):
        iv.transverse_module(1.0, math.pi / 2)
    with pytest.raises(InputRangeError, match="finite"):
        iv.transverse_module(math.nan, 0.0)
    with pytest.raises(InputRangeError, match="finite"):
        iv.normal_tooth_thickness(1.0, math.inf, ALPHA_N)
    with pytest.raises(InputRangeError, match=r"\[0, 90"):
        iv.inv(-0.1)


def test_helix_sign_only_changes_the_sign_of_helix_angles() -> None:
    plus = iv.compute_basic_gear_geometry(
        number_of_teeth=25,
        normal_module_mm=5.0,
        normal_pressure_angle_deg=20.0,
        helix_angle_deg=20.0,
        profile_shift_coefficient=0.25,
    )
    minus = iv.compute_basic_gear_geometry(
        number_of_teeth=25,
        normal_module_mm=5.0,
        normal_pressure_angle_deg=20.0,
        helix_angle_deg=-20.0,
        profile_shift_coefficient=0.25,
    )
    assert minus.base_helix_angle_deg == -plus.base_helix_angle_deg < 0.0
    assert minus.helix_angle_deg == -plus.helix_angle_deg
    for name in type(plus).model_fields:
        if name not in {"helix_angle_deg", "base_helix_angle_deg"}:
            assert getattr(minus, name) == getattr(plus, name), name


def test_spur_gear_is_the_limit_of_a_vanishing_helix() -> None:
    spur = iv.compute_basic_gear_geometry(
        number_of_teeth=51,
        normal_module_mm=1.0,
        normal_pressure_angle_deg=20.0,
        helix_angle_deg=0.0,
        profile_shift_coefficient=0.2034,
    )
    tiny = iv.compute_basic_gear_geometry(
        number_of_teeth=51,
        normal_module_mm=1.0,
        normal_pressure_angle_deg=20.0,
        helix_angle_deg=1e-9,
        profile_shift_coefficient=0.2034,
    )
    assert spur.transverse_module_mm == 1.0 and spur.reference_diameter_mm == 51.0
    assert spur.transverse_pressure_angle_deg == pytest.approx(20.0, rel=2 * ULP)
    assert spur.base_helix_angle_deg == 0.0
    assert tiny.base_helix_angle_deg == pytest.approx(1e-9 * math.cos(ALPHA_N), rel=1e-9)
    for name in type(spur).model_fields:
        if name not in {"helix_angle_deg", "base_helix_angle_deg", "warnings"}:
            assert getattr(tiny, name) == pytest.approx(getattr(spur, name), rel=2 * ULP), name
    negative_zero = iv.compute_basic_gear_geometry(
        number_of_teeth=51,
        normal_module_mm=1.0,
        normal_pressure_angle_deg=20.0,
        helix_angle_deg=-0.0,
        profile_shift_coefficient=0.2034,
    )
    assert negative_zero == spur
    assert math.copysign(1.0, negative_zero.base_helix_angle_deg) == 1.0
