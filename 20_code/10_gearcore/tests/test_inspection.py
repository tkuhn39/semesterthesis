"""Inspection dimensions of the tooth thickness (increment 4).

DIN 21773:2014-08 for the dimensions, DIN 3977:1981-02 for the measuring balls. The tests check
the single equations against calculations that do not use them (the worked examples of DIN 3977,
the geometry of a ball between two involutes, the span as a sum of base pitches), the rule that
an input states which dimension it gives (user decisions 2026-10-04, ADR-107), the reading of
``.ste`` files as STplus computes them, and the comparison with the STplus listings.
"""

import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError
from scipy.optimize import brentq, minimize_scalar

from gearcore import generation as gn
from gearcore import inspection as ins
from gearcore import involute as iv
from gearcore import pair as pr
from gearcore.data import (
    data_path,
    load_not_compared,
    load_stplus,
    stplus_case_dirs,
    stplus_input_path,
)
from gearcore.errors import GearCoreError, GeometryInfeasibleError, InputRangeError
from gearcore.io.ste import load_ste, pair_input_from_ste, parse_ste
from gearcore.models.common import DimensionLimits, Pair
from gearcore.models.inputs import (
    BallMeasurement,
    DimensionKind,
    GearInput,
    PairInput,
    SpanMeasurement,
    ToolProfile,
)
from gearcore.models.results import InspectionResult
from gearcore.parity import ParityVerdict, compare_inspection
from gearcore.stplus_program import stplus_chord_diameter

ALPHA = math.radians(20.0)
PROBES = data_path("stplus_program", "probes")


def tool(**fields: Any) -> ToolProfile:
    base: dict[str, Any] = {
        "addendum_factor": 1.25,
        "tip_radius_factor": 0.25,
        "protuberance_mm": 0.0,
        "machining_allowance_mm": 0.0,
    }
    return ToolProfile(**{**base, **fields})


def kst_b(**pinion: Any) -> PairInput:
    """The reference pair kst-B (verified by the user): centre distance and the spans of both
    finished gears; ``pinion`` adds what settles the split (STplus presets A_sne1 = -85 um)."""
    gears = Pair(
        pinion=GearInput(
            number_of_teeth=36,
            span=SpanMeasurement(
                kind=DimensionKind.UPPER_LIMIT,
                span_measurement_mm=27.827,
                number_of_teeth_spanned=5,
            ),
            face_width_mm=22.0,
            tip_diameter_mm=76.46,
            tip_chamfer_radial_mm=0.0,
            tool=tool(dedendum_factor=1.75, root_form_height_factor=1.75),
            **pinion,
        ),
        wheel=GearInput(
            number_of_teeth=54,
            span=SpanMeasurement(
                kind=DimensionKind.UPPER_LIMIT, span_measurement_mm=46.21, number_of_teeth_spanned=8
            ),
            face_width_mm=20.0,
            tip_diameter_mm=112.95,
            tip_chamfer_radial_mm=0.0,
            tool=tool(
                tip_radius_factor=0.394,
                root_form_height_factor=0.7388,
                dedendum_factor=1.3,
                edge_break_angle_deg=45.0,
            ),
        ),
    )
    return PairInput(
        normal_module_mm=2.0,
        normal_pressure_angle_deg=20.0,
        helix_angle_deg=0.0,
        centre_distance_mm=91.5,
        gears=gears,
    )


def plain_pair(
    z: tuple[int, int] = (20, 41),
    x: tuple[float, float] = (0.3, 0.1),
    *,
    m_n: float = 2.0,
    beta: float = 0.0,
    allowance: tuple[float, float] | None = (-60.0, -100.0),
    **pinion: Any,
) -> PairInput:
    """A pair with standard tip circles, both x given."""
    gears = []
    for index in range(2):
        d = z[index] * m_n / math.cos(math.radians(beta))
        fields: dict[str, Any] = {
            "number_of_teeth": z[index],
            "profile_shift_coefficient": x[index],
            "face_width_mm": 20.0 * m_n,
            "tip_diameter_mm": d + 2.0 * m_n * (1.0 + x[index]),
            "tip_chamfer_radial_mm": 0.0,
            "tool": tool(),
            "tooth_thickness_allowance_um": allowance,
        }
        if index == 0:
            fields.update(pinion)
        gears.append(GearInput(**fields))
    return PairInput(
        normal_module_mm=m_n,
        normal_pressure_angle_deg=20.0,
        helix_angle_deg=beta,
        gears=Pair(pinion=gears[0], wheel=gears[1]),
    )


def inspect(pair: PairInput, **options: Any) -> InspectionResult:
    return ins.compute_inspection(gn.compute_generation(pair), **options)


# --- DIN 3977: table, worked examples ---------------------------------------------------------------


def test_din3977_table_1_is_the_table_of_the_norm() -> None:
    table = ins.standard_measuring_ball_diameters()
    assert len(table) == 55 and table[0] == 0.17 and table[-1] == 50.0
    assert list(table) == sorted(set(table))
    # the five columns of eleven values of p. 1 begin with these values
    assert [table[i] for i in (0, 11, 22, 33, 44)] == [0.17, 0.895, 3.0, 6.5, 16.0]
    stored = json.dumps(list(table))
    assert all(token in stored for token in ("0.335", "3.25", "10.5", "45.0"))
    assert ins.next_larger_measuring_ball_diameter(6.475) == 6.5
    assert ins.next_larger_measuring_ball_diameter(3.5) == 3.5
    assert ins.next_larger_measuring_ball_diameter(3.5 * (1.0 + 1e-13)) == 3.5
    assert ins.next_larger_measuring_ball_diameter(3.5 * (1.0 + 1e-9)) == 3.75
    assert ins.next_larger_measuring_ball_diameter(1e-6) == 0.17
    with pytest.raises(InputRangeError, match="largest diameter of DIN 3977"):
        ins.next_larger_measuring_ball_diameter(50.001)
    with pytest.raises(InputRangeError):
        ins.next_larger_measuring_ball_diameter(0.0)


def _ideal_ball(z: int, m_n: float, x: float, beta: float) -> float:
    d = iv.reference_diameter(z, m_n, beta)
    d_b = iv.base_diameter(z, m_n, ALPHA, beta)
    alpha_t = iv.transverse_pressure_angle(ALPHA, beta)
    beta_b = iv.base_helix_angle(beta, ALPHA)
    alpha_vt = iv.transverse_profile_angle_at(ins.v_circle_diameter(d, x, m_n), d_b)
    eta_b = iv.base_space_width_half_angle(iv.space_width_half_angle(z, x, ALPHA), alpha_t)
    alpha_Kt = ins.ideal_ball_centre_profile_angle(alpha_vt, eta_b, beta_b)
    return ins.ideal_measuring_ball_diameter(z, m_n, ALPHA, beta_b, alpha_Kt, alpha_vt)


def _offset(z: int, m_n: float, x: float, beta: float, D_M: float) -> float:
    """0,5 (d_M - d_v) / m_n of the ball D_M (DIN 3977 Abschnitt 6)."""
    d = iv.reference_diameter(z, m_n, beta)
    d_b = iv.base_diameter(z, m_n, ALPHA, beta)
    alpha_t = iv.transverse_pressure_angle(ALPHA, beta)
    beta_b = iv.base_helix_angle(beta, ALPHA)
    eta = iv.space_width_half_angle(z, x, ALPHA)
    alpha_Kt = ins.ball_centre_profile_angle(D_M, z, m_n, ALPHA, eta, alpha_t)
    alpha_Mt = ins.ball_contact_profile_angle(alpha_Kt, D_M, d_b, beta_b)
    d_M = ins.ball_measuring_circle_diameter(d_b, alpha_Mt)
    return ins.measuring_circle_offset_factor(d_M, ins.v_circle_diameter(d, x, m_n), m_n)


def test_din3977_example_of_bild_1() -> None:
    """DIN 3977 Bild 1 (p. 3; the same example in DIN 21773 Bild 8, B1): z = 22, beta = 30
    degrees, x = 0,5 give D_M = 1,85 mm for m_n = 1 mm; for m_n = 3,5 mm 'ist somit ein
    Meßstück mit dem Durchmesser D_M = 6,5 mm zu benutzen'. The value is read off a diagram."""
    beta = math.radians(30.0)
    ideal = _ideal_ball(22, 1.0, 0.5, beta)
    assert ideal == pytest.approx(1.85, abs=0.01)
    assert ins.next_larger_measuring_ball_diameter(3.5 * ideal) == 6.5
    # the ball of Eq. (26) touches on the V-cylinder (spur exactly, helical closely: p. 18)
    assert abs(_offset(22, 1.0, 0.5, beta, ideal)) < 2e-3
    assert abs(_offset(22, 1.0, 0.5, 0.0, _ideal_ball(22, 1.0, 0.5, 0.0))) < 1e-12


def test_din3977_example_of_bild_2() -> None:
    """DIN 3977 Bild 2 (p. 4): for z_nM = 35 and x = +0,5 measuring pieces with
    1,73 m_n < D_M < 2,54 m_n are usable: the measuring circle lies 0,1 m_n below to 0,5 m_n
    above the V-cylinder. z_nM = 35 belongs to z = 22 at beta = 30 degrees (Bild 1)."""
    beta = math.radians(30.0)
    smallest = brentq(lambda D: _offset(22, 1.0, 0.5, beta, D) + 0.1, 1.4, 2.0)
    largest = brentq(lambda D: _offset(22, 1.0, 0.5, beta, D) - 0.5, 2.0, 3.2)
    assert smallest == pytest.approx(1.73, abs=0.02)
    assert largest == pytest.approx(2.54, abs=0.03)
    assert ins.MEASURING_CIRCLE_BELOW_V_CYLINDER == 0.1
    assert ins.MEASURING_CIRCLE_ABOVE_V_CYLINDER == 0.5


# --- the ball between two involutes, without the equations of the norm -------------------------------


@pytest.mark.parametrize(
    "z, x, D_M", [(20, 0.3, 3.5), (12, 0.0, 4.0), (54, 0.3037, 3.5), (17, -0.3, 3.25)]
)
def test_ball_touches_both_flanks_of_a_spur_gear(z: int, x: float, D_M: float) -> None:
    """A circle of the diameter D_M with its centre on the centre line of a tooth space at the
    radius d_K / 2 has the distance D_M / 2 from the involute, and touches it on d_M."""
    m_n = 2.0
    d_b = iv.base_diameter(z, m_n, ALPHA, 0.0)
    eta = iv.space_width_half_angle(z, x, ALPHA)
    alpha_Kt = ins.ball_centre_profile_angle(D_M, z, m_n, ALPHA, eta, ALPHA)
    d_K = ins.ball_centre_circle_diameter(d_b, alpha_Kt)
    d_M = ins.ball_measuring_circle_diameter(
        d_b, ins.ball_contact_profile_angle(alpha_Kt, D_M, d_b, 0.0)
    )
    eta_b = iv.base_space_width_half_angle(eta, ALPHA)

    def distance(roll_angle: float) -> float:
        # the flank that bounds the space: polar angle eta_b + inv at the roll angle
        radius = 0.5 * d_b * math.hypot(1.0, roll_angle)
        angle = eta_b + roll_angle - math.atan(roll_angle)
        return math.hypot(radius * math.sin(angle), radius * math.cos(angle) - 0.5 * d_K)

    found = minimize_scalar(distance, bounds=(0.0, 1.5), method="bounded", options={"xatol": 1e-13})
    assert found.fun == pytest.approx(0.5 * D_M, rel=1e-10)
    assert d_b * math.hypot(1.0, found.x) == pytest.approx(d_M, rel=1e-6)
    assert ins.radial_single_ball_dimension(d_K, D_M) == 0.5 * (d_K + D_M)


# --- span measurement --------------------------------------------------------------------------------

teeth = st.integers(8, 200)
shifts = st.floats(-0.6, 1.0)
helices = st.floats(-40.0, 40.0)
modules = st.floats(0.3, 20.0)


@settings(max_examples=200, deadline=None)
@given(z=teeth, x=shifts, beta_deg=helices, m_n=modules, k=st.integers(2, 12))
def test_span_is_k_minus_one_base_pitches_and_a_base_tooth_thickness(
    z: int, x: float, beta_deg: float, m_n: float, k: int
) -> None:
    """Third form of Eq. (14), built from DIN ISO 21771 alone."""
    beta = math.radians(beta_deg)
    alpha_t = iv.transverse_pressure_angle(ALPHA, beta)
    psi_b = iv.base_tooth_thickness_half_angle(iv.tooth_thickness_half_angle(z, x, ALPHA), alpha_t)
    d_b = iv.base_diameter(z, m_n, ALPHA, beta)
    s_bn = ins.normal_base_tooth_thickness(d_b, psi_b, iv.base_helix_angle(beta, ALPHA))
    span = ins.span_measurement(z, m_n, x, ALPHA, beta, k)
    assert span == pytest.approx((k - 1) * ins.normal_base_pitch(m_n, ALPHA) + s_bn, rel=1e-12)
    back = ins.profile_shift_coefficient_from_span(span, k, z, m_n, ALPHA, beta)
    assert back == pytest.approx(x, abs=1e-11)


@settings(max_examples=200, deadline=None)
@given(z=teeth, x=st.floats(-0.3, 1.0), beta_deg=helices)
def test_number_of_teeth_spanned_touches_next_to_the_v_cylinder(
    z: int, x: float, beta_deg: float
) -> None:
    """Eq. (9): of all k, the planes over this k touch nearest to the V-cylinder, measured
    along the line of action (the span changes by one base pitch per tooth)."""
    beta, m_n = math.radians(beta_deg), 3.0
    d = iv.reference_diameter(z, m_n, beta)
    d_b = iv.base_diameter(z, m_n, ALPHA, beta)
    d_v = ins.v_circle_diameter(d, x, m_n)
    if d_v <= d_b * 1.001:
        return
    k = ins.number_of_teeth_spanned(z, m_n, x, ALPHA, beta, d_v)
    beta_b = iv.base_helix_angle(beta, ALPHA)
    wanted = math.sqrt(d_v * d_v - d_b * d_b) / math.cos(beta_b)  # the span that touches on d_v
    p_bn = ins.normal_base_pitch(m_n, ALPHA)
    if k < 2:
        return
    assert abs(ins.span_measurement(z, m_n, x, ALPHA, beta, k) - wanted) <= 0.5 * p_bn * (1 + 1e-9)
    # ... and on the measuring circle the transverse projection of the span is a chord of it
    circle = ins.span_measuring_circle_diameter(d_b, wanted, beta_b)
    assert circle == pytest.approx(math.hypot(d_b, wanted * math.cos(beta_b)), rel=1e-14)


def test_eq_10_and_the_second_forms_of_eq_12_and_13_are_half_a_tooth_lower() -> None:
    """Finding of increment 4. As printed (DIN 21773 p. 12), Eq. (10) and the second forms of
    Eq. (12) and (13) hold (sqrt(d_y^2 - d_b^2) / cos(beta_b) - s_bn) / p_bn where Eq. (9) and
    the first forms hold z / pi (...): the two differ by 0,5, because s_bn / p_bn contains the
    half pitch of the tooth thickness half angle. The first forms are the ones the geometry
    asks for; kst-B (pinion): Eq. (9) gives 5 like STplus, Eq. (10) as printed gives 4."""
    z, m_n, x = 36, 2.0, 0.1823
    d = iv.reference_diameter(z, m_n, 0.0)
    d_b = iv.base_diameter(z, m_n, ALPHA, 0.0)
    d_v = ins.v_circle_diameter(d, x, m_n)
    psi_b = iv.base_tooth_thickness_half_angle(iv.tooth_thickness_half_angle(z, x, ALPHA), ALPHA)
    s_bn = ins.normal_base_tooth_thickness(d_b, psi_b, 0.0)
    p_bn = ins.normal_base_pitch(m_n, ALPHA)
    first_form = ins._measuring_position(z, m_n, x, ALPHA, 0.0, d_v)
    second_form = (math.sqrt(d_v * d_v - d_b * d_b) - s_bn) / p_bn
    assert first_form - second_form == pytest.approx(0.5, abs=1e-12)
    assert ins.number_of_teeth_spanned(z, m_n, x, ALPHA, 0.0, d_v) == 5
    assert math.floor(second_form + 1.0) == 4
    listing = load_stplus("kst_b", "geometry")
    assert listing["k"]["numbers"][0] == 5.0
    # the span over 5 teeth touches nearer to the V-cylinder than the span over 4
    touch = {
        k: ins.span_measuring_circle_diameter(
            d_b, ins.span_measurement(z, m_n, x, ALPHA, 0.0, k), 0.0
        )
        for k in (4, 5)
    }
    assert abs(touch[5] - d_v) < abs(touch[4] - d_v)


def test_usable_range_of_the_number_of_teeth_spanned() -> None:
    """Eq. (12), (13): within the range the planes touch between the form circles, one tooth
    beyond it they do not."""
    z, m_n, x, beta = 30, 2.5, 0.2, math.radians(15.0)
    d_b = iv.base_diameter(z, m_n, ALPHA, beta)
    beta_b = iv.base_helix_angle(beta, ALPHA)
    d_Ff, d_Fa = 76.0, 85.0
    k_min = ins.min_number_of_teeth_spanned(z, m_n, x, ALPHA, beta, d_Ff)
    k_max = ins.max_number_of_teeth_spanned(z, m_n, x, ALPHA, beta, d_Fa)
    assert k_min <= k_max

    def circle(k: int) -> float:
        return ins.span_measuring_circle_diameter(
            d_b, ins.span_measurement(z, m_n, x, ALPHA, beta, k), beta_b
        )

    assert all(d_Ff <= circle(k) <= d_Fa for k in range(k_min, k_max + 1))
    assert circle(k_min - 1) < d_Ff and circle(k_max + 1) > d_Fa
    with pytest.raises(InputRangeError, match=">= 2"):
        ins.span_measurement(z, m_n, x, ALPHA, beta, 1)
    with pytest.raises(InputRangeError):
        ins.span_measurement(z, m_n, x, ALPHA, beta, 2.0)  # type: ignore[arg-type]


def test_face_width_for_the_span_of_a_helical_gear() -> None:
    assert ins.contact_line_overlap(50.0) == pytest.approx(1.2 + 0.018 * 50.0)
    beta_b = math.radians(25.0)
    b_Fmin = ins.min_usable_face_width(50.0, beta_b, 2.1)
    assert b_Fmin == pytest.approx(50.0 * math.sin(beta_b) + 2.1 * math.cos(beta_b))
    assert ins.min_usable_face_width(50.0, -beta_b, 2.1) == b_Fmin  # the hand does not matter
    narrow = inspect(plain_pair((20, 41), (0.2, 0.1), beta=30.0, face_width_mm=6.0))
    assert "face_width_below_minimum_for_span" in [w.code for w in narrow.gears.pinion.warnings]
    assert narrow.gears.pinion.min_usable_face_width_mm is not None
    assert inspect(plain_pair()).gears.pinion.min_usable_face_width_mm is None  # spur gear


# --- balls and rollers ----------------------------------------------------------------------------------


@settings(max_examples=150, deadline=None)
@given(z=teeth, x=st.floats(-0.3, 0.8), beta_deg=helices, factor=st.floats(1.6, 2.0))
def test_ball_dimension_and_profile_shift_determine_each_other(
    z: int, x: float, beta_deg: float, factor: float
) -> None:
    beta, m_n = math.radians(beta_deg), 2.0
    D_M = factor * m_n
    d_b = iv.base_diameter(z, m_n, ALPHA, beta)
    alpha_t = iv.transverse_pressure_angle(ALPHA, beta)
    eta = iv.space_width_half_angle(z, x, ALPHA)
    if not 0.0 <= ins._inv_alpha_Kt(D_M, z, m_n, ALPHA, eta, alpha_t) <= 1.0:
        return
    d_K = ins.ball_centre_circle_diameter(
        d_b, ins.ball_centre_profile_angle(D_M, z, m_n, ALPHA, eta, alpha_t)
    )
    M_dK = ins.diametral_two_ball_dimension(d_K, D_M, z)
    assert ins.ball_centre_circle_diameter_from_dimension(M_dK, D_M, z) == pytest.approx(d_K)
    back = ins.profile_shift_coefficient_from_ball_dimension(M_dK, D_M, z, m_n, ALPHA, beta)
    assert back == pytest.approx(x, abs=1e-9)
    # balls: an odd number of teeth puts the balls half a pitch off the diameter (Eq. (36))
    across = d_K if z % 2 == 0 else d_K * math.cos(math.pi / (2 * z))
    assert M_dK == pytest.approx(across + D_M, rel=1e-15)
    # rollers of a helical gear with an odd number of teeth lie opposite each other (§11)
    M_dZ = ins.diametral_two_roller_dimension(d_K, D_M, z, beta)
    if z % 2 == 1 and beta != 0.0:
        assert M_dZ == pytest.approx(2.0 * ins.radial_single_ball_dimension(d_K, D_M))
        converted = (M_dK - D_M) / math.cos(math.pi / (2 * z)) + D_M  # Eq. (37)
        assert M_dZ == pytest.approx(converted, rel=1e-14)
    else:
        assert M_dZ == M_dK


def test_balls_that_do_not_rest_on_the_flanks_are_typed_errors() -> None:
    z, m_n, x = 20, 2.0, 0.0
    d_b = iv.base_diameter(z, m_n, ALPHA, 0.0)
    eta = iv.space_width_half_angle(z, x, ALPHA)
    with pytest.raises(GeometryInfeasibleError, match="too small"):
        ins.ball_centre_profile_angle(0.5, z, m_n, ALPHA, eta, ALPHA)
    with pytest.raises(GeometryInfeasibleError, match="too large"):
        ins.ball_centre_profile_angle(1.0e6, z, m_n, ALPHA, eta, ALPHA)
    # (between 2,392 and 2,395 mm the centre lies above the base circle, the contact below it)
    alpha_Kt = ins.ball_centre_profile_angle(2.393, z, m_n, ALPHA, eta, ALPHA)
    with pytest.raises(GeometryInfeasibleError, match="below the base circle"):
        ins.ball_contact_profile_angle(alpha_Kt, 2.393, d_b, 0.0)
    with pytest.raises(GeometryInfeasibleError, match="does not exceed the ball diameter"):
        ins.ball_centre_circle_diameter_from_dimension(3.0, 3.5, z)
    with pytest.raises(GeometryInfeasibleError, match="no width on the V-cylinder"):
        ins.ideal_measuring_ball_diameter(z, m_n, ALPHA, 0.0, 0.2, 0.3)


# --- chords -----------------------------------------------------------------------------------------------


def test_chords_against_plane_geometry() -> None:
    """Spur gear: the chord of the arc s on the circle d is d sin(s / d), its height below the
    tip d_a / 2 - d / 2 cos(s / d). The two printed forms (1) and (2) are the same."""
    d, d_a, s = 40.0, 45.0, 3.4
    assert ins.chordal_tooth_thickness(s, d, 0.0) == pytest.approx(d * math.sin(s / d), rel=1e-15)
    assert ins.chordal_height(d_a, s, d, 0.0) == pytest.approx(
        0.5 * d_a - 0.5 * d * math.cos(s / d)
    )
    beta_y = math.radians(22.0)
    psi_y = s / (d * math.cos(beta_y))  # s_yn = d_y psi_y cos(beta_y)
    form_1 = d * math.hypot(
        psi_y * math.cos(beta_y) * math.sin(beta_y), math.sin(psi_y * math.cos(beta_y) ** 2)
    )
    assert ins.chordal_tooth_thickness(s, d, beta_y) == pytest.approx(form_1, rel=1e-14)
    assert ins.chordal_tooth_thickness(s, d, beta_y) < s  # a chord is shorter than its arc
    with pytest.raises(GeometryInfeasibleError, match="above the tip circle"):
        ins.chordal_height(39.0, s, d, 0.0)
    # constant chord: the same for every number of teeth of a spur gear (§6, Anmerkung)
    s_n = iv.normal_tooth_thickness(2.0, 0.25, ALPHA)
    assert ins.constant_chord(s_n, ALPHA, 0.0) == pytest.approx(s_n * math.cos(ALPHA) ** 2)
    h_cc = ins.height_above_constant_chord(2.5, s_n, ALPHA)
    assert h_cc == pytest.approx(2.5 - 0.5 * s_n * math.sin(ALPHA) * math.cos(ALPHA))
    assert ins.chordal_tooth_thickness_allowance_factor(d, 0.0, d, 0.0) == 1.0  # Eq. (48)


# --- limits: §4 exactly, §14 linearised ----------------------------------------------------------------


def test_limits_follow_section_4_and_agree_with_the_allowance_factors_of_section_14() -> None:
    result = inspect(kst_b(tooth_thickness_allowance_um=(-85.0, -125.0)))
    pinion = result.gears.pinion
    assert pinion.tooth_thickness_tolerance_um == pytest.approx(40.0)
    assert pinion.mean_generating_profile_shift_coefficient == pytest.approx(
        0.5
        * (
            pinion.upper_generating_profile_shift_coefficient
            + pinion.lower_generating_profile_shift_coefficient
        ),
        abs=1e-15,
    )
    span = pinion.span_measurement_mm
    assert span is not None and pinion.span_allowance_um is not None
    assert span.upper == pytest.approx(27.827, abs=1e-12)  # the given upper limit comes back
    half = pinion.tooth_thickness_tolerance_um
    # the span is linear in x: Eq. (55), (56) are exact
    assert ins.upper_limit_dimension(
        span.mean, half, pinion.span_allowance_factor
    ) == pytest.approx(span.upper, abs=1e-12)
    assert ins.lower_limit_dimension(
        span.mean, half, pinion.span_allowance_factor
    ) == pytest.approx(span.lower, abs=1e-12)
    assert pinion.span_allowance_um[0] == pytest.approx(-85.0 * math.cos(ALPHA))
    assert span.upper - span.nominal == pytest.approx(1e-3 * pinion.span_allowance_um[0], abs=1e-12)
    # the ball dimension is not: Eq. (62), (63) agree with §4 to the second order
    balls = pinion.diametral_two_ball_dimension_mm
    factor = pinion.diametral_ball_dimension_allowance_factor
    by_factor = ins.upper_limit_dimension(balls.mean, half, factor)
    curvature = balls.upper - 2.0 * balls.mean + balls.lower  # second difference of M_dK
    assert curvature < -1e-4
    assert by_factor - balls.upper == pytest.approx(-0.5 * curvature, abs=2e-6)
    assert ins.lower_limit_dimension(balls.mean, half, factor) - balls.lower == pytest.approx(
        -0.5 * curvature, abs=2e-6
    )
    assert pinion.radial_ball_dimension_allowance_factor == pytest.approx(0.5 * factor)
    # chord on the reference cylinder: allowance factor 1 (Eq. (48)), to the second order
    chord = pinion.chordal_tooth_thickness_mm
    assert chord is not None
    assert chord.upper - chord.lower == pytest.approx(0.040, abs=2e-4)
    with pytest.raises(InputRangeError, match="must not lie below"):
        ins.tooth_thickness_tolerance(-100.0, -60.0)
    with pytest.raises(InputRangeError, match=">= 0"):
        ins.upper_limit_dimension(10.0, -1.0, 1.0)


def test_dimension_limits_are_ordered() -> None:
    assert DimensionLimits.same(3.0) == DimensionLimits(nominal=3.0, upper=3.0, mean=3.0, lower=3.0)
    with pytest.raises(ValidationError, match="ordered"):
        DimensionLimits(nominal=3.0, upper=2.9, mean=2.95, lower=2.8)
    without = inspect(plain_pair(allowance=None)).gears.pinion
    assert (
        without.tooth_thickness_allowance_um is None
        and without.tooth_thickness_tolerance_um is None
    )
    balls = without.diametral_two_ball_dimension_mm
    assert balls.nominal == balls.upper == balls.mean == balls.lower


# --- the reference pair kst-B -----------------------------------------------------------------------------


def test_kst_b_follows_from_its_spans_and_one_allowance() -> None:
    """kst-B (verified by the user) gives the centre distance and the spans of both finished
    gears. With the upper allowance of the pinion that STplus presets (c25: -85 um) gearcore
    arrives at what the listing prints: the nominal x, the allowance of the wheel as the rest,
    the nominal dimensions and their allowances."""
    pair = kst_b(tooth_thickness_allowance_um=(-85.0, -125.0))
    resolved = pr.resolve_tooth_thickness(pair)
    listing = load_stplus("kst_b", "geometry")
    for index in range(2):
        assert resolved.profile_shift_coefficient[index] == pytest.approx(
            listing["x"]["numbers"][index], abs=5e-5
        )
    wheel_allowance = resolved.tooth_thickness_allowance_um[1]
    assert wheel_allowance is not None
    assert 1e-3 * wheel_allowance[0] == pytest.approx(listing["A_sne"]["numbers"][1], abs=5e-4)
    assert wheel_allowance[0] == wheel_allowance[1]  # no tolerance follows from a span
    generation = gn.compute_generation(pair)
    chords = Pair(
        pinion=stplus_chord_diameter(
            generation.gears.pinion.root_form_diameter_mm,
            generation.gears.pinion.tip_form_diameter_mm,
        ),
        wheel=stplus_chord_diameter(
            generation.gears.wheel.root_form_diameter_mm,
            generation.gears.wheel.tip_form_diameter_mm,
        ),
    )
    with_ball = generation.model_copy(
        update={
            "inputs": pair.model_copy(
                update={
                    "gears": Pair(
                        pinion=pair.gears.pinion.model_copy(
                            update={"measuring_ball_diameter_mm": 3.5}
                        ),
                        wheel=pair.gears.wheel.model_copy(
                            update={"measuring_ball_diameter_mm": 3.5}
                        ),
                    )
                }
            )
        }
    )
    result = ins.compute_inspection(with_ball, chord_diameter_mm=chords)
    for index, gear in enumerate(result.gears.as_tuple()):
        assert gear.span_measurement_mm is not None
        assert gear.span_measurement_mm.nominal == pytest.approx(
            listing["W_k"]["numbers"][index], abs=6e-4
        )
        assert gear.number_of_teeth_spanned == int(listing["k"]["numbers"][index])
        balls = gear.diametral_two_ball_dimension_mm
        assert balls.nominal == pytest.approx(listing["M_dK"]["numbers"][index], abs=6e-4)
        assert balls.upper - balls.nominal == pytest.approx(
            listing["A_Mde"]["numbers"][index], abs=1e-3
        )
        assert gear.chordal_tooth_thickness_at_y_mm is not None
        assert gear.chordal_tooth_thickness_at_y_mm.nominal == pytest.approx(
            listing["s_n-"]["numbers"][index], abs=1e-3
        )
        assert gear.height_above_chord_at_y_mm == pytest.approx(
            listing["h_a-"]["numbers"][index], abs=1e-3
        )
        assert gear.ideal_measuring_ball_diameter_mm == pytest.approx(3.48, abs=0.01)
        assert -0.1 <= gear.measuring_circle_offset_factor <= 0.5
    assert result.gears.pinion.overcut_tip_diameter_mm == pytest.approx(
        72.0 + 2.0 * 2.0 * (result.gears.pinion.upper_generating_profile_shift_coefficient + 1.75)
    )
    assert InspectionResult.model_validate_json(result.model_dump_json()) == result
    # without the allowance the split of the sum is open: the core demands it, nothing is preset
    with pytest.raises(InputRangeError, match="not its split between the gears"):
        gn.compute_generation(kst_b())
    # ... the allowances of both gears say too much
    wheel = pair.gears.wheel.model_copy(update={"tooth_thickness_allowance_um": (-300.0, -340.0)})
    both = pair.model_copy(update={"gears": Pair(pinion=pair.gears.pinion, wheel=wheel)})
    with pytest.raises(InputRangeError, match="over-determined"):
        gn.compute_generation(both)


def test_kinds_of_a_given_dimension() -> None:
    """DIN 21773 §4: the upper limit, the mean and the lower limit of the same gear give the
    same pair when each is stated as what it is."""
    reference = inspect(kst_b(tooth_thickness_allowance_um=(-85.0, -125.0))).gears.pinion
    span = reference.span_measurement_mm
    assert span is not None
    for kind, value in (
        (DimensionKind.UPPER_LIMIT, span.upper),
        (DimensionKind.MEAN, span.mean),
        (DimensionKind.LOWER_LIMIT, span.lower),
    ):
        given = SpanMeasurement(kind=kind, span_measurement_mm=value, number_of_teeth_spanned=5)
        pair = kst_b(tooth_thickness_allowance_um=(-85.0, -125.0))
        pinion = pair.gears.pinion.model_copy(update={"span": given})
        pair = pair.model_copy(update={"gears": Pair(pinion=pinion, wheel=pair.gears.wheel)})
        x_1 = pr.resolve_tooth_thickness(pair).profile_shift_coefficient[0]
        assert x_1 == pytest.approx(reference.profile_shift_coefficient, abs=1e-12), kind
    # the two-ball dimension of the finished gear in place of the span: the same gear
    balls = BallMeasurement(
        kind=DimensionKind.UPPER_LIMIT,
        diametral_two_ball_dimension_mm=reference.diametral_two_ball_dimension_mm.upper,
        measuring_ball_diameter_mm=reference.measuring_ball_diameter_mm,
    )
    pair = kst_b(tooth_thickness_allowance_um=(-85.0, -125.0))
    pinion = pair.gears.pinion.model_copy(update={"span": None, "ball_dimension": balls})
    pair = pair.model_copy(update={"gears": Pair(pinion=pinion, wheel=pair.gears.wheel)})
    by_balls = inspect(pair).gears.pinion
    assert by_balls.profile_shift_coefficient == pytest.approx(
        reference.profile_shift_coefficient, abs=1e-10
    )
    assert by_balls.measuring_ball_diameter_mm == reference.measuring_ball_diameter_mm
    # one inspection dimension and one pair of allowances per gear
    with pytest.raises(ValidationError, match="one inspection dimension"):
        GearInput.model_validate({**pinion.model_dump(), "span": kst_b().gears.pinion.span})
    with pytest.raises(ValidationError, match="the same statement"):
        GearInput.model_validate({**pinion.model_dump(), "span_allowance_um": (-80.0, -117.0)})
    # span allowances are the tooth thickness allowances times cos(alpha_n) (Eq. (54))
    by_span_allowance = kst_b(span_allowance_um=(-85.0 * math.cos(ALPHA), -125.0 * math.cos(ALPHA)))
    assert pr.resolve_tooth_thickness(by_span_allowance).profile_shift_coefficient[
        0
    ] == pytest.approx(reference.profile_shift_coefficient, abs=1e-12)


def test_upper_limits_without_backlash_are_reported() -> None:
    pair = kst_b(tooth_thickness_allowance_um=(-85.0, -125.0))
    thick = SpanMeasurement(
        kind=DimensionKind.UPPER_LIMIT, span_measurement_mm=46.80, number_of_teeth_spanned=8
    )
    wheel = pair.gears.wheel.model_copy(update={"span": thick})
    pair = pair.model_copy(update={"gears": Pair(pinion=pair.gears.pinion, wheel=wheel)})
    resolved = pr.resolve_tooth_thickness(pair)
    assert "no_backlash_at_upper_allowances" in [w.code for w in resolved.warnings]


# --- choices: number of teeth spanned, measuring ball --------------------------------------------------


def test_number_of_teeth_spanned_and_ball_of_the_result() -> None:
    plain = inspect(plain_pair()).gears.pinion
    # nothing given: Eq. (9), and the next larger diameter of DIN 3977 above the ideal one
    assert plain.number_of_teeth_spanned == 3
    assert plain.min_number_of_teeth_spanned <= 3 <= plain.max_number_of_teeth_spanned
    assert plain.ideal_measuring_ball_diameter_mm is not None
    table = ins.standard_measuring_ball_diameters()
    assert plain.measuring_ball_diameter_mm == min(
        d for d in table if d >= plain.ideal_measuring_ball_diameter_mm
    )
    assert plain.warnings == ()
    # given values are used; a k whose planes do not touch the usable flank is no measurement
    given = inspect(
        plain_pair(number_of_teeth_spanned=4, measuring_ball_diameter_mm=4.0)
    ).gears.pinion
    assert given.number_of_teeth_spanned == 4 and given.measuring_ball_diameter_mm == 4.0
    with pytest.raises(GeometryInfeasibleError, match="usable range is 2 to 4"):
        inspect(plain_pair(number_of_teeth_spanned=6))
    # a ball that does not stand above the tip circle is reported, one that touches outside the
    # involute is no measurement
    low = inspect(plain_pair(measuring_ball_diameter_mm=3.25)).gears.pinion
    assert "measuring_ball_below_tip_circle" in [w.code for w in low.warnings]
    with pytest.raises(GeometryInfeasibleError, match="outside the involute"):
        inspect(plain_pair(measuring_ball_diameter_mm=9.0))
    assert inspect(plain_pair(measuring_ball_diameter_mm=5.0)).gears.pinion.warnings == ()
    wide = inspect(plain_pair(measuring_ball_diameter_mm=6.0)).gears.pinion
    assert [w.code for w in wide.warnings] == ["measuring_circle_outside_din3977_range"]
    assert wide.measuring_circle_offset_factor > 0.5
    # a tip cylinder above the ball of the table: the next larger ones are tried, and said
    chosen = {}
    for tip in (64.0, 65.0, 66.0):
        tall = plain_pair((30, 41), (0.0, 0.1), allowance=None)
        pinion = tall.gears.pinion.model_copy(update={"tip_diameter_mm": tip})
        tall = tall.model_copy(update={"gears": Pair(pinion=pinion, wheel=tall.gears.wheel)})
        result = inspect(tall).gears.pinion
        assert result.ideal_measuring_ball_diameter_mm == pytest.approx(3.411, abs=1e-3)
        moved = "measuring_ball_larger_than_next_table_value" in [w.code for w in result.warnings]
        chosen[tip] = (result.measuring_ball_diameter_mm, moved)
    assert chosen == {64.0: (3.5, False), 65.0: (3.75, True), 66.0: (4.0, True)}
    # chord cylinder outside the usable flank
    with pytest.raises(GeometryInfeasibleError, match="between the form circles"):
        inspect(plain_pair(), chord_diameter_mm=Pair(pinion=30.0, wheel=84.0))
    with pytest.raises(InputRangeError, match="GenerationResult"):
        ins.compute_inspection(plain_pair())  # type: ignore[arg-type]
    with pytest.raises(InputRangeError, match="must be a Pair"):
        inspect(plain_pair(), chord_diameter_mm=(40.0, 84.0))


# --- .ste files, read as STplus computes them -----------------------------------------------------------


def _probe_pair(name: str) -> tuple[PairInput, tuple[str, ...], dict[str, Any]]:
    folder = Path(str(PROBES)) / name
    read = pair_input_from_ste(load_ste(folder / "input.ste"))
    listing = (folder / "report.sta.txt").read_text(encoding="latin-1")
    rows: dict[str, Any] = {}
    for label, key in (
        ("Profilverschiebungsfaktor (Nennw.)", "x"),
        ("oberes Abmass der Z.dickensehne", "A_sne"),
        ("Erz.-Profilversch.faktor", "x_E"),
        ("Messtueckdurchmesser", "D_M"),
    ):
        for line in listing.splitlines():
            if label in line and "=" not in line:
                rows[key] = [float(token) for token in line.split() if _is_number(token)][-2:]
                break
    return read.pair, read.notes, rows


def _is_number(token: str) -> bool:
    return token.replace(".", "", 1).replace("-", "", 1).isdigit()


def test_ste_span_is_read_as_the_upper_limit_and_stplus_split_needs_din_3967() -> None:
    pair, notes, _ = _probe_pair("span_of_both_gears")
    for gear in pair.gears.as_tuple():
        assert gear.span is not None and gear.span.kind is DimensionKind.UPPER_LIMIT
    assert sum("read as the upper limit of the finished gear" in note for note in notes) == 2
    assert any("series c25 of DIN 3967" in note for note in notes)
    with pytest.raises(InputRangeError, match="STplus presets the allowance of gear 1"):
        gn.compute_generation(pair)
    # the supplied files of the same kind
    for case in ("kst_a", "kst_b", "kst_c"):
        supplied = pair_input_from_ste(load_ste(stplus_input_path(case))).pair
        assert supplied.gears.wheel.span is not None
        with pytest.raises(InputRangeError, match="not its split between the gears"):
            pr.compute_pair_geometry(supplied)


@pytest.mark.parametrize(
    "name, dropped",
    [
        ("span_with_upper_allowance_of_gear_one", False),
        ("span_with_upper_allowance_of_gear_two", False),
        ("span_with_upper_allowances_of_both_gears", True),
        ("span_of_gear_two_beside_x_of_gear_one", False),
    ],
)
def test_ste_spans_with_what_settles_the_split_give_the_numbers_of_stplus(
    name: str, dropped: bool
) -> None:
    pair, notes, listing = _probe_pair(name)
    assert any("not passed on" in note for note in notes) is dropped
    resolved = pr.resolve_tooth_thickness(pair)
    for index in range(2):
        assert resolved.profile_shift_coefficient[index] == pytest.approx(
            listing["x"][index], abs=6e-5
        )
    generation = gn.compute_generation(pair)
    measured = [gear.span is not None for gear in pair.gears.as_tuple()]
    for index, generated in enumerate(generation.gears.as_tuple()):
        if not measured[index]:
            continue  # (a gear given by x gets the preset series of STplus: increment 5)
        assert generated.generating_profile_shift_coefficient == pytest.approx(
            listing["x_E"][index], abs=6e-5
        )
        allowance = generated.tooth_thickness_allowance_um
        assert allowance is not None
        assert 1e-3 * allowance[0] == pytest.approx(listing["A_sne"][index], abs=6e-4)


def test_ste_inputs_stplus_rejects_or_gearcore_does_not_translate() -> None:
    for name, error, text in (
        ("span_without_centre_distance", GearCoreError, "needs ACHSABSTAND"),
        ("span_of_one_gear_only", GearCoreError, "nothing for the other"),
        ("generating_profile_shift_given", GearCoreError, "PROFILVERSCHIEBUNG_F"),
        ("span_of_gear_one_beside_x_of_gear_two", GearCoreError, "replaces that x_2"),
    ):
        folder = Path(str(PROBES)) / name
        with pytest.raises(error, match=text):
            pair_input_from_ste(load_ste(folder / "input.ste"))
    # STplus says nothing in its listing where it rejects an input
    rejected = (Path(str(PROBES)) / "span_without_centre_distance" / "report.sta.txt").read_text(
        encoding="latin-1"
    )
    assert "unvollstaendig oder unzulaessig" in rejected
    thick = (
        Path(str(PROBES)) / "spans_too_thick_for_the_centre_distance" / "report.sta.txt"
    ).read_text(encoding="latin-1")
    assert "eingegebener Achsabstand a < spielfreier Achsabstand" in thick
    # x beside the span of the same gear: STplus ignores the span, the importer says so
    pair, notes, listing = _probe_pair("span_beside_x_of_the_same_gear")
    assert pair.gears.pinion.span is None and pair.gears.pinion.profile_shift_coefficient == 0.30
    assert any("STplus ignores it" in note for note in notes)
    assert listing["x"][0] == 0.30


def test_ste_ball_dimension_and_given_ball() -> None:
    pair, notes, listing = _probe_pair("ball_dimension_given")
    for index, gear in enumerate(pair.gears.as_tuple()):
        assert gear.ball_dimension is not None
        assert gear.ball_dimension.kind is DimensionKind.UPPER_LIMIT
        sign = 1.0 if index == 0 else -1.0
        x_E = ins.profile_shift_coefficient_from_ball_dimension(
            gear.ball_dimension.diametral_two_ball_dimension_mm,
            gear.ball_dimension.measuring_ball_diameter_mm,
            gear.number_of_teeth,
            pair.normal_module_mm,
            ALPHA,
            sign * 0.0,
        )
        assert x_E == pytest.approx(listing["x_E"][index], abs=6e-5)
    assert any("DIAMETRALES_MASS" in note for note in notes)
    # MESSTUECKDM_D_M: STplus accepts a ball that stands above the tip circle and replaces one
    # that does not by its own without a message; gearcore computes with the given ball and
    # reports that it does not stand above the tip
    above, _, listing_above = _probe_pair("measuring_ball_given_above_the_tip")
    below, _, listing_below = _probe_pair("measuring_ball_given_below_the_tip")
    assert above.gears.pinion.measuring_ball_diameter_mm == 3.25 == listing_above["D_M"][0]
    assert below.gears.pinion.measuring_ball_diameter_mm == 3.0 and listing_below["D_M"][0] == 4.0
    assert "measuring_ball_below_tip_circle" not in [
        w.code for w in inspect(above).gears.pinion.warnings
    ]
    assert "measuring_ball_below_tip_circle" in [
        w.code for w in inspect(below).gears.pinion.warnings
    ]
    with pytest.raises(GearCoreError, match="both given"):
        pair_input_from_ste(
            parse_ste(
                (Path(str(PROBES)) / "span_of_both_gears" / "input.ste")
                .read_text(encoding="latin-1")
                .replace(
                    "MESSZAEHNEZAHL = 5 8",
                    "MESSZAEHNEZAHL = 5 8\nMESSTUECKDM_KUGEL = 3.5 %\nDIAMETRALES_MASS = 77.6 %",
                )
            )
        )


def test_choices_of_stplus_that_are_not_those_of_the_norm() -> None:
    """Documented differences (``norm_map.md``): STplus prints the span over the number of teeth
    of its rule, not over the one of the input, and chooses the measuring ball from a table of
    the program by the tip circle and the middle of the flank (``test_stplus_choices``)."""
    _, _, _ = _probe_pair("span_of_both_gears")
    listing = (Path(str(PROBES)) / "span_of_both_gears" / "report.sta.txt").read_text(
        encoding="latin-1"
    )
    row = next(line for line in listing.splitlines() if "Messzaehnezahl  " in line)
    assert row.split()[-3:-1] == ["5", "7"]  # the input said 5 and 8
    forced = (
        Path(str(PROBES)) / "number_of_teeth_spanned_for_the_listing" / "report.sta.txt"
    ).read_text(encoding="latin-1")
    row = next(line for line in forced.splitlines() if "Messzaehnezahl  " in line)
    assert row.split()[-3:-1] == ["5", "8"]
    small, _, listing_small = _probe_pair("measuring_ball_of_the_program")
    large, _, listing_large = _probe_pair("measuring_ball_of_the_program_larger_tip")
    assert (listing_small["D_M"][0], listing_large["D_M"][0]) == (3.5, 4.0)
    table = ins.standard_measuring_ball_diameters()
    assert 3.5 in table and 4.0 in table
    # gearcore: the next larger table value above the ideal diameter 3,53 mm, the same for both
    # tip circles (the ball stands above both), and a value STplus never chooses itself
    ours = [inspect(pair).gears.pinion for pair in (small, large)]
    assert [gear.measuring_ball_diameter_mm for gear in ours] == [3.75, 3.75]
    assert all(
        gear.ideal_measuring_ball_diameter_mm == pytest.approx(3.532, abs=1e-3) for gear in ours
    )


# --- comparison with STplus ----------------------------------------------------------------------------


def _all_rows() -> list[Any]:
    return [row for folder in stplus_case_dirs() for row in compare_inspection(folder.name)]


def test_verdict_counts_of_the_inspection_dimensions() -> None:
    rows = _all_rows()
    counts = Counter(row.verdict for row in rows)
    assert len(rows) == 876
    assert counts[ParityVerdict.IDENTICAL] == 675
    assert counts[ParityVerdict.ORACLE_ACCURACY] == 201
    assert counts[ParityVerdict.DIFFERENT] == 0
    compared = {row.field for row in rows}
    assert len(compared) == 15 and "diametral_two_roller_dimension_mm" in compared
    # k and D_M follow the rules of STplus and are the ones of the listing, gear by gear
    choices = [
        row
        for row in rows
        if row.field in ("number_of_teeth_spanned", "measuring_ball_diameter_mm")
    ]
    assert len(choices) == 72 and all(row.difference == 0.0 for row in choices)
    # what STplus defines differently is documented and not compared value by value
    documented = load_not_compared()
    assert set(documented) == {
        "diametral_ball_dimension_allowance_factor",
        "chordal_tooth_thickness_allowance",
        "number_of_teeth_spanned",
        "measuring_ball_diameter",
    }
    assert "diametral_ball_dimension_allowance_factor" not in compared
    # the confirmed reference pairs are part of it
    assert {"kst_b", "kst_e"} <= {row.case for row in rows if row.trust == "verified"}


@pytest.mark.parametrize(
    "function, shift",
    [
        ("span_measurement", 2.0e-3),
        ("diametral_two_ball_dimension", 2.0e-3),
        ("chordal_tooth_thickness", 2.0e-3),
        ("chordal_height", 2.0e-3),
        ("span_measuring_circle_diameter", 2.0e-3),
        ("ball_measuring_circle_diameter", 2.0e-3),
    ],
)
def test_the_comparison_detects_an_error_of_two_micrometres(
    monkeypatch: pytest.MonkeyPatch, function: str, shift: float
) -> None:
    original = getattr(ins, function)
    monkeypatch.setattr(ins, function, lambda *args: original(*args) + shift)
    rows = compare_inspection("kst_b_rerun")
    assert any(row.verdict is ParityVerdict.DIFFERENT for row in rows), function


def test_the_chord_is_compared_on_the_cylinder_stplus_prints() -> None:
    """The cylinder of the chord follows the form circles STplus finds numerically (compared
    within their accuracy); chord and height are computed on the printed cylinder and carry no
    such allowance."""
    rows = compare_inspection("kst_e_rerun")
    by_field = {row.field: row for row in rows if row.gear == "pinion" and row.origin == "listing"}
    assert by_field["y_diameter_mm"].solver_tolerance == 0.007
    for name in ("chordal_tooth_thickness_at_y_mm", "height_above_chord_at_y_mm"):
        assert by_field[name].solver_tolerance == 0.0
        assert 0.0 < by_field[name].input_tolerance < 1.0e-3


# --- properties of the orchestrator --------------------------------------------------------------------


@settings(max_examples=120, deadline=None)
@given(
    z_1=st.integers(10, 60),
    more=st.integers(0, 80),
    x_1=st.floats(-0.2, 0.8),
    x_2=st.floats(-0.3, 0.6),
    beta=st.floats(-35.0, 35.0),
    m_n=st.floats(0.5, 12.0),
    upper=st.floats(-150.0, 0.0),
    tolerance=st.floats(0.0, 80.0),
)
def test_inspection_of_generated_pairs(
    z_1: int,
    more: int,
    x_1: float,
    x_2: float,
    beta: float,
    m_n: float,
    upper: float,
    tolerance: float,
) -> None:
    """Whatever the generation accepts: a typed error or a result whose limits are ordered and
    whose given dimensions determine the same gear again."""
    scale = m_n / 2.0
    pair = plain_pair(
        (z_1, z_1 + more),
        (x_1, x_2),
        m_n=m_n,
        beta=beta,
        allowance=(upper * scale, (upper - tolerance) * scale),
    )
    try:
        result = inspect(pair)
    except GearCoreError:
        return
    for index, gear in enumerate(result.gears.as_tuple()):
        balls = gear.diametral_two_ball_dimension_mm
        slack = 1e-12 * balls.nominal  # (rounding of equal limits, as the contract allows)
        assert balls.nominal + slack >= balls.upper >= balls.mean - slack >= balls.lower - 2 * slack
        assert gear.measuring_ball_diameter_mm in ins.standard_measuring_ball_diameters()
        sign = 1.0 if index == 0 else -1.0
        back = ins.profile_shift_coefficient_from_ball_dimension(
            balls.upper,
            gear.measuring_ball_diameter_mm,
            gear.number_of_teeth,
            m_n,
            ALPHA,
            sign * math.radians(beta),
        )
        assert back == pytest.approx(gear.upper_generating_profile_shift_coefficient, abs=1e-8)
        if gear.span_measurement_mm is not None:
            assert gear.number_of_teeth_spanned is not None
            assert gear.min_number_of_teeth_spanned <= gear.number_of_teeth_spanned
            assert gear.number_of_teeth_spanned <= gear.max_number_of_teeth_spanned
            span = gear.span_measurement_mm
            assert span.nominal + slack >= span.upper >= span.mean - slack >= span.lower - 2 * slack
    assert InspectionResult.model_validate_json(result.model_dump_json()) == result
