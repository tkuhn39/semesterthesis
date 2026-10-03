"""The rolling of a rack-type tool on the gear: envelope of the tool tip rounding (``trochoid``).

The straight flank of the tool must reproduce the involute of DIN ISO 21771 §4.7 exactly, the
tip line the root circle, and the fillet must leave the root circle tangentially and meet the
involute at the root form circle of Eq. (128) (Anhang NB) where the gear is free of undercut.
Nothing here is taken from a reference program.
"""

import math

import numpy as np
import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from gearcore import generation as gn
from gearcore import involute as iv
from gearcore import trochoid as tr
from gearcore.errors import GeometryInfeasibleError, InputRangeError, SolverError

SRC = "ISO21771:2014"


def _setup(
    z: int,
    m_n: float,
    alpha_n_deg: float,
    beta_deg: float,
    x_E: float,
    h_aP0_f: float,
    rho_f: float,
):
    alpha_n, beta = math.radians(alpha_n_deg), math.radians(beta_deg)
    alpha_t = iv.transverse_pressure_angle(alpha_n, beta)
    d = iv.reference_diameter(z, m_n, beta)
    d_b = iv.base_diameter(z, m_n, alpha_n, beta)
    psi_b = iv.base_tooth_thickness_half_angle(
        iv.tooth_thickness_half_angle(z, x_E, alpha_n), alpha_t
    )
    rounding = tr.tip_rounding(z, m_n, alpha_n, beta, h_aP0_f * m_n, rho_f * m_n, x_E)
    return alpha_n, beta, alpha_t, d, d_b, psi_b, rounding


@pytest.mark.eq("Linke2010", "Verzahnungsgesetz")
@pytest.mark.eq("FVA604-I:2012", "(3.3)")
@pytest.mark.parametrize("beta_deg", [0.0, 15.8, -30.0])
def test_the_straight_flank_generates_the_involute(beta_deg: float) -> None:
    """Points of the tool flank, rolled by the envelope condition, lie on the involute with the
    base half angle of Eq. (42) (x_E in Eq. (41)) to 1e-12 rad."""
    z, m_n, x_E = 23, 3.0, 0.2
    alpha_n, beta, alpha_t, d, d_b, psi_b, rounding = _setup(
        z, m_n, 20.0, beta_deg, x_E, 1.25, 0.25
    )
    r = 0.5 * d
    p_t = math.pi * m_n / math.cos(beta)
    for eta in np.linspace(-2.0, 3.0, 11):  # heights above the pitch line
        xi = p_t / 4.0 + (eta - x_E * m_n) * math.tan(alpha_t)  # right flank of the tool tooth
        c = tr.pitch_point_position(xi, eta, math.tan(alpha_t), 1.0)
        radius, angle = tr.generated_point(xi, eta, c, r)
        psi = math.pi / z - angle
        assert abs(psi - tr.involute_half_angle(float(radius), d_b, psi_b)) < 1e-12
    # the point on the pitch line generates on the reference circle
    xi_0 = p_t / 4.0 - x_E * m_n * math.tan(alpha_t)
    radius, angle = tr.generated_point(
        xi_0, 0.0, tr.pitch_point_position(xi_0, 0.0, math.tan(alpha_t), 1.0), r
    )
    assert radius == pytest.approx(r, abs=1e-12)
    assert math.pi / z - angle == pytest.approx(
        iv.tooth_thickness_half_angle(z, x_E, alpha_n), abs=1e-14
    )


def test_the_tip_line_generates_the_root_circle() -> None:
    _, _, _, d, _, _, rounding = _setup(20, 2.0, 20.0, 0.0, 0.1, 1.25, 0.3)
    eta_tip = rounding.centre_eta_mm - rounding.semi_axis_eta_mm
    for xi in np.linspace(-3.0, 3.0, 7):
        c = tr.pitch_point_position(xi, eta_tip, 1.0, 0.0)
        assert c == pytest.approx(xi, abs=1e-15)
        radius, _ = tr.generated_point(xi, eta_tip, c, 0.5 * d)
        assert radius == pytest.approx(rounding.root_radius_mm, abs=1e-12)
    assert rounding.root_radius_mm == pytest.approx(
        0.5 * gn.generated_root_diameter(d, 0.1, 2.0, 2.5), abs=1e-12
    )


@pytest.mark.eq("FVA604-I:2012", "p. 28")
@pytest.mark.parametrize("beta_deg", [0.0, 20.0, -45.0])
def test_the_fillet_leaves_the_root_circle_and_meets_the_involute_tangentially(
    beta_deg: float,
) -> None:
    """Free of undercut: the fillet starts on the root circle (parameter -pi/2) and ends on the
    involute at the root form circle of Eq. (128), with the same tangent (a smooth profile)."""
    z, m_n, x_E, h_f, rho_f = 30, 2.5, 0.15, 1.25, 0.38
    alpha_n, beta, alpha_t, d, d_b, psi_b, rounding = _setup(
        z, m_n, 20.0, beta_deg, x_E, h_f, rho_f
    )
    h_FaP0 = gn.tool_tip_form_height(h_f * m_n, rho_f * m_n, alpha_n)
    assert x_E > gn.min_generating_profile_shift_coefficient(h_FaP0, m_n, z, alpha_t, beta)
    r_start, psi_start = tr.fillet_point(rounding, -math.pi / 2.0)
    assert r_start == pytest.approx(rounding.root_radius_mm, abs=1e-12)
    assert psi_start == pytest.approx(rounding.start_half_angle_rad, abs=1e-14)
    r_end, psi_end = tr.fillet_point(rounding, rounding.flank_parameter_rad)
    d_Ff = gn.root_form_diameter(d, alpha_t, h_FaP0, x_E, m_n, d_b)
    assert 2.0 * r_end == pytest.approx(d_Ff, rel=1e-13)
    assert psi_end == pytest.approx(tr.involute_half_angle(r_end, d_b, psi_b), abs=1e-13)
    # tangent continuity: the last fillet step points along the involute
    theta, radius, psi = tr.fillet_curve(rounding, n=2001)
    x, y = radius * np.sin(psi), radius * np.cos(psi)
    fillet_dir = np.array([x[-1] - x[-2], y[-1] - y[-2]])
    r2 = radius[-1] * (1.0 + 1e-6)
    p2 = tr.involute_half_angle(float(r2), d_b, psi_b)
    inv_dir = np.array([r2 * math.sin(p2) - x[-1], r2 * math.cos(p2) - y[-1]])
    cosine = np.dot(fillet_dir, inv_dir) / np.linalg.norm(fillet_dir) / np.linalg.norm(inv_dir)
    assert cosine > 1.0 - 1e-6
    # monotonic: the fillet rises from the root circle
    assert np.all(np.diff(radius) > 0.0)
    found = tr.root_form_diameter_by_intersection(rounding, d_b, psi_b)
    assert found[2] is False and found[0] == pytest.approx(d_Ff, rel=1e-12)


def test_undercut_fillet_cuts_the_involute() -> None:
    """z = 12, x_E below x_Emin: the fillet crosses the involute from inside to outside and ends
    on the mirrored branch of the involute beyond the tangent point T; the root form circle is
    the crossing, above the base circle."""
    z, m_n, x_E = 12, 2.0, -0.0446
    alpha_n, beta, alpha_t, d, d_b, psi_b, rounding = _setup(z, m_n, 20.0, 0.0, x_E, 1.25, 0.25)
    h_FaP0 = gn.tool_tip_form_height(2.5, 0.5, alpha_n)
    assert x_E < gn.min_generating_profile_shift_coefficient(h_FaP0, m_n, z, alpha_t, beta)
    with pytest.raises(GeometryInfeasibleError, match="undercut"):
        gn.root_form_diameter(d, alpha_t, h_FaP0, x_E, m_n, d_b)
    d_Ff, theta, undercut = tr.root_form_diameter_by_intersection(rounding, d_b, psi_b)
    assert undercut and d_b < d_Ff < d
    r_star, psi_star = tr.fillet_point(rounding, theta)
    assert 2.0 * r_star == pytest.approx(d_Ff, abs=1e-12)
    assert psi_star == pytest.approx(tr.involute_half_angle(r_star, d_b, psi_b), abs=1e-12)
    # below the crossing the fillet lies inside the involute, above it outside
    r_low, psi_low = tr.fillet_point(rounding, theta - 0.002)
    r_high, psi_high = tr.fillet_point(rounding, theta + 0.002)
    assert 0.5 * d_b < r_low < r_star < r_high
    assert psi_low < tr.involute_half_angle(r_low, d_b, psi_b)
    assert psi_high > tr.involute_half_angle(r_high, d_b, psi_b)
    # the end of the fillet (flank tangent point) lies beyond the crossing, outside the involute
    r_end, psi_end = tr.fillet_point(rounding, rounding.flank_parameter_rad)
    assert r_end > r_star and psi_end > tr.involute_half_angle(r_end, d_b, psi_b)


@pytest.mark.eq(SRC, "(135)")
@settings(max_examples=60, deadline=None)
@given(
    z=st.integers(min_value=8, max_value=80),
    x_E=st.floats(min_value=-0.6, max_value=1.0),
    rho_f=st.floats(min_value=0.05, max_value=0.4),
    h_f=st.floats(min_value=1.0, max_value=1.4),
    beta_deg=st.floats(min_value=-40.0, max_value=40.0),
)
def test_undercut_limit_of_the_norm_agrees_with_the_fillet(
    z: int, x_E: float, rho_f: float, h_f: float, beta_deg: float
) -> None:
    """Eq. (135) says undercut exactly when the fillet cuts into the involute (numerical)."""
    m_n = 2.0
    # G3W-01: the box of the strategy holds tools whose tip roundings overlap (rho* 0,4 above
    # h* 1,388); they are no tools and `tip_rounding` rejects them (test_adv_3: G3A-03)
    alpha = math.radians(20.0)
    assume(h_f < rho_f + (math.pi / 4.0 - rho_f / math.cos(alpha)) / math.tan(alpha))
    alpha_n, beta, alpha_t, d, d_b, psi_b, rounding = _setup(
        z, m_n, 20.0, beta_deg, x_E, h_f, rho_f
    )
    h_FaP0 = gn.tool_tip_form_height(h_f * m_n, rho_f * m_n, alpha_n)
    x_Emin = gn.min_generating_profile_shift_coefficient(h_FaP0, m_n, z, alpha_t, beta)
    if abs(x_E - x_Emin) < 1e-3:
        # at the limit both descriptions meet on the base circle; without the knowledge of the
        # caller the band below it is not decidable here (test_adv_3: G3A-01, G3V-06 cover it)
        return
    try:
        d_Ff, _, undercut = tr.root_form_diameter_by_intersection(rounding, d_b, psi_b)
    except GeometryInfeasibleError:
        assert x_E > x_Emin, "a fillet below the base circle needs no undercut"
        return
    assert undercut == (x_E < x_Emin), (x_E, x_Emin)
    if not undercut:
        assert d_Ff == pytest.approx(
            gn.root_form_diameter(d, alpha_t, h_FaP0, x_E, m_n, d_b), rel=1e-11
        )


def test_the_helix_angle_enters_symmetrically_and_continuously() -> None:
    plus = _setup(25, 3.0, 20.0, 30.0, 0.3, 1.25, 0.38)
    minus = _setup(25, 3.0, 20.0, -30.0, 0.3, 1.25, 0.38)
    theta = np.linspace(-math.pi / 2.0, -math.radians(20.0), 50)
    r_plus, p_plus = tr.fillet_point(plus[-1], theta)
    r_minus, p_minus = tr.fillet_point(minus[-1], theta)
    assert np.allclose(r_plus, r_minus, rtol=0, atol=1e-12) and np.allclose(
        p_plus, p_minus, atol=1e-14
    )
    spur = _setup(25, 3.0, 20.0, 0.0, 0.3, 1.25, 0.38)
    small = _setup(25, 3.0, 20.0, 1e-7, 0.3, 1.25, 0.38)
    r_0, p_0 = tr.fillet_point(spur[-1], theta)
    r_s, p_s = tr.fillet_point(small[-1], theta)
    assert np.max(np.abs(r_s - r_0)) < 1e-9 and np.max(np.abs(p_s - p_0)) < 1e-12


def test_the_transverse_tip_rounding_is_an_ellipse() -> None:
    """Semi-axis rho / cos(beta) along the rack, rho radially; the flank tangent point at -alpha_n."""
    rho, beta = 0.76, math.radians(25.0)
    rounding = tr.tip_rounding(25, 2.0, math.radians(20.0), beta, 2.5, rho, 0.0)
    assert rounding.semi_axis_eta_mm == rho
    assert rounding.semi_axis_xi_mm == pytest.approx(rho / math.cos(beta))
    assert rounding.flank_parameter_rad == -math.radians(20.0)
    xi, eta = rounding.point(rounding.flank_parameter_rad)
    t_xi, t_eta = rounding.tangent(rounding.flank_parameter_rad)
    alpha_t = iv.transverse_pressure_angle(math.radians(20.0), beta)
    assert t_eta / t_xi == pytest.approx(1.0 / math.tan(alpha_t))  # tangent to the flank
    # the tangent point lies on the flank line of the tool
    p_t = math.pi * 2.0 / math.cos(beta)
    assert xi == pytest.approx(p_t / 4.0 + (eta - 0.0) * math.tan(alpha_t), abs=1e-12)


def test_typed_errors() -> None:
    alpha_n = math.radians(20.0)
    with pytest.raises(GeometryInfeasibleError, match="overlap"):
        tr.tip_rounding(20, 2.0, alpha_n, 0.0, 2.5, 1.5, 0.0)
    with pytest.raises(GeometryInfeasibleError, match="no straight flank"):
        tr.tip_rounding(20, 2.0, alpha_n, 0.0, 2.5, 4.0, 0.0)
    with pytest.raises(InputRangeError):
        tr.tip_rounding(20, 2.0, alpha_n, 0.0, 2.5, -0.1, 0.0)
    with pytest.raises(SolverError, match="radial"):
        tr.pitch_point_position(1.0, 1.0, 0.0, 1.0)
    rounding = tr.tip_rounding(20, 2.0, alpha_n, 0.0, 2.5, 0.5, 0.0)
    with pytest.raises(InputRangeError):
        tr.fillet_point(rounding, 0.0)
    with pytest.raises(InputRangeError):
        tr.fillet_curve(rounding, n=2)
    with pytest.raises(InputRangeError):
        tr.fillet_curve(rounding, theta_end_rad=0.5)
    with pytest.raises(GeometryInfeasibleError):
        tr.involute_half_angle(0.5 * 0.9 * 37.5877, 37.5877, 0.1)
    for bad in (float("nan"), float("inf"), "1", None, True):
        with pytest.raises(InputRangeError):
            tr.involute_half_angle(bad, 37.5877, 0.1)  # type: ignore[arg-type]
