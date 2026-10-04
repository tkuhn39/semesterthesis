"""Inspection dimensions of the tooth thickness of an external cylindrical gear.

Sources: DIN 21773:2014-08 §4 (which dimension an equation yields), §5 chordal tooth thickness,
§6 constant chord, §7 span measurement, §8 to §11 dimensions over balls and rollers, §13 tip
cylinder cut by the tool, §14 allowances and allowance factors; DIN 3977:1981-02 for the
diameters of the measuring balls and rollers (Tabelle 1, Abschnitt 6); DIN 3960:1987-03
Eq. (3.8.15) for the measuring circle of the span of a helical gear, which the current norm
prints for spur gears only. Every function realises one equation; angles are radians
(``_rad``), lengths millimetres (``_mm``), allowances micrometres (``_um``) like the contract.
Formulas are written for external gears (``z/|z| = +1``).

Which dimension (§4, p. 8). An equation of §5 to §13 gives the nominal dimension when the
profile shift coefficient x is put in, and the upper limit, the mean or the lower limit of the
finished gear when the generating profile shift coefficient x_Es, x_Em or x_Ei takes its place.
The functions therefore take "x" and say nothing about which of the four it is; the caller
does. The limits of §14 (mean plus or minus half the tolerance times the allowance factor) are
the linearised form of the same statement and are kept beside it.

Number of teeth spanned. Eq. (9) puts the contact of the measuring planes next to the
V-cylinder; Eq. (12) and (13) bound k by the root form and the tip form circle. As printed,
Eq. (10) and the second forms of Eq. (12) and (13) (with s_bn and p_bn) are smaller by 0,5 than
Eq. (9) and the first forms: s_bn / p_bn = z psi_b / pi contains the half pitch pi / (2 z) of
the tooth thickness half angle. The first forms are the ones that agree with the geometry
(W_k = (k - 1) p_bn + s_bn touches the circle d_y where sqrt(d_y^2 - d_b^2) / cos(beta_b) =
W_k) and with DIN 3960 Eq. (3.8.13) for a spur gear; they are implemented (finding of
increment 4, ``norm_map.md``).

Measuring balls. Eq. (26), (27) give the diameter whose contact points lie on the V-cylinder;
the ball that is used has a diameter of DIN 3977 Tabelle 1, and every dimension is computed with
that actual diameter (p. 20). Abschnitt 6 of DIN 3977 admits a measuring circle between
0,1 m_n below and 0,5 m_n above the V-cylinder for an external gear.
"""

import math
from functools import lru_cache

import yaml
from scipy.optimize import brentq

from gearcore import involute as iv
from gearcore._guards import HALF_PI, helix, pressure_angle, teeth
from gearcore._safe import (
    EPS,
    finite_input,
    finite_result,
    integer_input,
    positive_input,
    safe_div,
)
from gearcore.data import data_path
from gearcore.errors import GeometryInfeasibleError, InputRangeError
from gearcore.models.common import DimensionLimits, InputWarning, Pair
from gearcore.models.inputs import GearInput, PairInput
from gearcore.models.results import (
    GearGeneration,
    GearInspection,
    GenerationResult,
    InspectionResult,
)
from gearcore.trace import eq

SOURCE = "DIN21773:2014"
GEOMETRY = "ISO21771:2014"
BALLS = "DIN3977:1981"
OLD = "DIN3960:1987"
EXAMPLE = "ISOTR6336-30:2022"

EQ_EXEMPT = (
    "standard_measuring_ball_diameters",
    "profile_shift_coefficient_from_ball_dimension",
    "compute_inspection",
)
"""A table, a chain of traced inversions and the orchestrator carry no equation of their own."""

MIN_TEETH_SPANNED = 2
"""A span over one tooth would touch next to the base cylinder; the contract requires k >= 2."""

MEASURING_CIRCLE_ABOVE_V_CYLINDER = 0.5
MEASURING_CIRCLE_BELOW_V_CYLINDER = 0.1
"""DIN 3977:1981-02 Abschnitt 6 (p. 2), external gears: the radial distance 0,5 (d_M - d_v)
between the measuring circle and the V-cylinder may lie between -0,1 m_n and +0,5 m_n."""


def _shift(x: float) -> float:
    return finite_input(x, "profile shift coefficient x")


# --- V-cylinder and base cylinder ----------------------------------------------------------------


@eq(GEOMETRY, "(32)", section="4.5.1", page=33)
def v_circle_diameter(d_mm: float, x: float, m_n_mm: float) -> float:
    """V-circle diameter: d_v = d + 2 x m_n (external gear).

    With x_E in place of x it is the V-circle of the generated gear (DIN 3977 Bild 1: "bei
    Stirnrädern mit Zahndickenabmaßen tritt x_E an Stelle von x").
    """
    d = positive_input(d_mm, "reference diameter d")
    d_v = d + 2.0 * _shift(x) * positive_input(m_n_mm, "normal module m_n")
    if d_v <= 0.0:
        raise GeometryInfeasibleError(f"V-circle diameter d_v = {d_v!r} is not positive")
    return finite_result(d_v, "V-circle diameter d_v")


@eq(GEOMETRY, "(29)", section="4.4.5", page=33)
def normal_base_pitch(m_n_mm: float, alpha_n_rad: float) -> float:
    """Normal base pitch: p_bn = p_n cos(alpha_n) = pi m_n cos(alpha_n)."""
    m_n = positive_input(m_n_mm, "normal module m_n")
    alpha_n = pressure_angle(alpha_n_rad, "normal pressure angle alpha_n")
    return finite_result(math.pi * m_n * math.cos(alpha_n), "normal base pitch p_bn")


@eq(GEOMETRY, "(38)", section="4.7.1", page=35, note="on the base cylinder")
@eq(GEOMETRY, "(48)", section="4.7.5", page=37, note="on the base cylinder")
def normal_base_tooth_thickness(d_b_mm: float, psi_b_rad: float, beta_b_rad: float) -> float:
    """Normal tooth thickness on the base cylinder: s_bn = d_b psi_b cos(beta_b)."""
    d_b = positive_input(d_b_mm, "base diameter d_b")
    psi_b = finite_input(psi_b_rad, "base tooth thickness half angle psi_b")
    return finite_result(d_b * psi_b * math.cos(helix(beta_b_rad)), "s_bn")


# --- §5 chordal tooth thickness, §6 constant chord ----------------------------------------------


@eq(SOURCE, "(2)", section="5", page=9)
@eq(SOURCE, "(4)", section="5", page=9, note="on the reference cylinder")
@eq(SOURCE, "(1)", section="5", page=9, note="the same with psi_y = s_yn / (d_y cos beta_y)")
@eq(SOURCE, "(3)", section="5", page=9, note="on the reference cylinder, with psi")
def chordal_tooth_thickness(s_yn_mm: float, d_y_mm: float, beta_y_rad: float) -> float:
    """Normal chordal tooth thickness on the cylinder d_y:
    s_cy = sqrt((s_yn sin(beta_y))^2 + (d_y sin(s_yn cos(beta_y) / d_y))^2).

    With the reference cylinder (d, beta, s_n) it is s_c of Eq. (4).
    """
    s_yn = positive_input(s_yn_mm, "normal tooth thickness s_yn")
    d_y = positive_input(d_y_mm, "diameter d_y")
    beta_y = helix(beta_y_rad)
    half_angle = finite_result(s_yn * math.cos(beta_y) / d_y, "s_yn cos(beta_y) / d_y")
    if half_angle >= HALF_PI:
        raise GeometryInfeasibleError(
            f"chordal tooth thickness: the tooth spans {half_angle!r} rad on each side of its "
            "centre line; no chord of a tooth"
        )
    return finite_result(
        math.hypot(s_yn * math.sin(beta_y), d_y * math.sin(half_angle)), "chordal thickness s_cy"
    )


@eq(SOURCE, "(5)", section="5", page=10)
@eq(SOURCE, "(6)", section="5", page=10, note="on the reference cylinder")
def chordal_height(d_a_mm: float, s_yn_mm: float, d_y_mm: float, beta_y_rad: float) -> float:
    """Height above the chord s_cy, measured from the tip circle:
    h_cy = d_a / 2 - d_y / 2 cos(s_yn cos(beta_y) / d_y).

    The norm prints the absolute value (the sign changes for an internal gear). For an external
    gear the chord lies below the tip circle; a cylinder whose chord lies above it raises.
    """
    d_a = positive_input(d_a_mm, "tip diameter d_a")
    s_yn = positive_input(s_yn_mm, "normal tooth thickness s_yn")
    d_y = positive_input(d_y_mm, "diameter d_y")
    half_angle = finite_result(s_yn * math.cos(helix(beta_y_rad)) / d_y, "s_yn cos(beta_y) / d_y")
    if half_angle >= HALF_PI:
        raise GeometryInfeasibleError(
            f"chordal height: the tooth spans {half_angle!r} rad on each side of its centre "
            "line; no chord of a tooth"
        )
    height = 0.5 * d_a - 0.5 * d_y * math.cos(half_angle)
    if height < 0.0:
        raise GeometryInfeasibleError(
            f"chordal height: the chord on d_y = {d_y!r} lies above the tip circle d_a = {d_a!r}"
        )
    return finite_result(height, "chordal height h_cy")


@eq(SOURCE, "(7)", section="6", page=11)
def constant_chord(s_n_mm: float, alpha_t_rad: float, beta_rad: float) -> float:
    """Constant chord: s_cc = s_n cos^2(alpha_t) / cos(beta)."""
    s_n = positive_input(s_n_mm, "normal tooth thickness s_n")
    alpha_t = pressure_angle(alpha_t_rad, "transverse pressure angle alpha_t")
    cosine = math.cos(helix(beta_rad))
    return finite_result(
        safe_div(s_n * math.cos(alpha_t) ** 2, cosine, what="s_cc (Eq. (7))"), "constant chord"
    )


@eq(SOURCE, "(8)", section="6", page=11)
def height_above_constant_chord(h_a_mm: float, s_t_mm: float, alpha_t_rad: float) -> float:
    """Height above the constant chord: h_cc = h_a - s_t / 2 sin(alpha_t) cos(alpha_t).

    h_a is the addendum (d_a - d) / 2 of the gear as it is, s_t the transverse tooth thickness.
    """
    h_a = finite_input(h_a_mm, "addendum h_a")
    s_t = positive_input(s_t_mm, "transverse tooth thickness s_t")
    alpha_t = pressure_angle(alpha_t_rad, "transverse pressure angle alpha_t")
    return finite_result(h_a - 0.5 * s_t * math.sin(alpha_t) * math.cos(alpha_t), "h_cc")


def _constant_chord_contact_diameter(d: float, s_cc: float, h_a: float, h_cc: float) -> float:
    """Circle through the end points of the constant chord: they lie s_cc / 2 beside the centre
    line of the tooth and h_a - h_cc above the reference circle (§6, Bild 4)."""
    return 2.0 * math.hypot(0.5 * d + h_a - h_cc, 0.5 * s_cc)


# --- §7 span measurement --------------------------------------------------------------------------


def _measuring_position(
    z: int, m_n_mm: float, x: float, alpha_n_rad: float, beta_rad: float, d_y_mm: float
) -> float:
    """The bracket of Eq. (9), (12) and (13) for the circle d_y:
    z / pi (tan(alpha_yt) / cos^2(beta_b) - inv(alpha_t) - 2 x tan(alpha_n) / z).

    The measuring planes over k teeth touch the circle d_y for k = bracket + 0,5.
    """
    number = teeth(z)
    alpha_n = pressure_angle(alpha_n_rad, "normal pressure angle alpha_n")
    beta = helix(beta_rad)
    alpha_t = iv.transverse_pressure_angle(alpha_n, beta)
    beta_b = iv.base_helix_angle(beta, alpha_n)
    d_b = iv.base_diameter(number, m_n_mm, alpha_n, beta)
    alpha_yt = iv.transverse_profile_angle_at(d_y_mm, d_b)
    bracket = (
        math.tan(alpha_yt) / math.cos(beta_b) ** 2
        - iv.inv(alpha_t)
        - 2.0 * _shift(x) * math.tan(alpha_n) / number
    )
    return finite_result(number / math.pi * bracket, "measuring position (Eq. (9))")


@eq(SOURCE, "(9)", section="7.2", page=12)
@eq(OLD, "(3.8.13)", section="3.8.2", page=21, note="the same for a spur gear")
def number_of_teeth_spanned(
    z: int, m_n_mm: float, x: float, alpha_n_rad: float, beta_rad: float, d_v_mm: float
) -> int:
    """Number of teeth spanned whose measuring planes touch next to the V-cylinder:
    k = INT[z / pi (tan(alpha_vt) / cos^2(beta_b) - inv(alpha_t) - 2 x tan(alpha_n) / z) + 1],
    cos(alpha_vt) = d_b / d_v. INT is the next integer that is not larger.

    Eq. (10), printed as an alternative, is smaller by 0,5 inside INT (module docstring).
    """
    return math.floor(_measuring_position(z, m_n_mm, x, alpha_n_rad, beta_rad, d_v_mm) + 1.0)


@eq(SOURCE, "(12)", section="7.2", page=12, note="first form")
def min_number_of_teeth_spanned(
    z: int, m_n_mm: float, x: float, alpha_n_rad: float, beta_rad: float, d_Ff_mm: float
) -> int:
    """Smallest number of teeth spanned of a flank without modification, limited by the root
    form circle: k_min = INT[z / pi (tan(alpha_Ff) / cos^2(beta_b) - inv(alpha_t)
    - 2 x tan(alpha_n) / z) + 1,5], cos(alpha_Ff) = d_b / d_Ff."""
    return math.floor(_measuring_position(z, m_n_mm, x, alpha_n_rad, beta_rad, d_Ff_mm) + 1.5)


@eq(SOURCE, "(13)", section="7.2", page=12, note="first form")
def max_number_of_teeth_spanned(
    z: int, m_n_mm: float, x: float, alpha_n_rad: float, beta_rad: float, d_Fa_mm: float
) -> int:
    """Largest number of teeth spanned of a flank without modification, limited by the tip form
    circle: k_max = INT[z / pi (tan(alpha_Fa) / cos^2(beta_b) - inv(alpha_t)
    - 2 x tan(alpha_n) / z) + 0,5], cos(alpha_Fa) = d_b / d_Fa."""
    return math.floor(_measuring_position(z, m_n_mm, x, alpha_n_rad, beta_rad, d_Fa_mm) + 0.5)


def _spanned(k: int) -> int:
    number = integer_input(k, "number of teeth spanned k")
    if number < MIN_TEETH_SPANNED:
        raise InputRangeError(
            f"number of teeth spanned k must be >= {MIN_TEETH_SPANNED}, got {k!r}"
        )
    return number


@eq(SOURCE, "(14)", section="7.2", page=13)
@eq(OLD, "(3.8.18)", section="3.8.2", page=21)
def span_measurement(
    z: int, m_n_mm: float, x: float, alpha_n_rad: float, beta_rad: float, k: int
) -> float:
    """Span measurement over k teeth:
    W_k = m_n cos(alpha_n) [pi (k - 0,5) + z inv(alpha_t)] + 2 x m_n sin(alpha_n)."""
    number = teeth(z)
    m_n = positive_input(m_n_mm, "normal module m_n")
    alpha_n = pressure_angle(alpha_n_rad, "normal pressure angle alpha_n")
    alpha_t = iv.transverse_pressure_angle(alpha_n, beta_rad)
    bracket = math.pi * (_spanned(k) - 0.5) + number * iv.inv(alpha_t)
    return finite_result(
        m_n * math.cos(alpha_n) * bracket + 2.0 * _shift(x) * m_n * math.sin(alpha_n),
        "span measurement W_k",
    )


@eq(SOURCE, "(14)", section="7.2", page=13, note="solved for x")
@eq(EXAMPLE, "x_E1", section="A.6", page=45, note="generating profile shift from W_k")
def profile_shift_coefficient_from_span(
    W_k_mm: float, k: int, z: int, m_n_mm: float, alpha_n_rad: float, beta_rad: float
) -> float:
    """The coefficient a span corresponds to:
    x = (W_k - m_n cos(alpha_n) [pi (k - 0,5) + z inv(alpha_t)]) / (2 m_n sin(alpha_n)).

    It is x for a nominal span and x_Es, x_Em or x_Ei for a span that is the upper limit, the
    mean or the lower limit of the finished gear (§4).
    """
    W_k = positive_input(W_k_mm, "span measurement W_k")
    number = teeth(z)
    m_n = positive_input(m_n_mm, "normal module m_n")
    alpha_n = pressure_angle(alpha_n_rad, "normal pressure angle alpha_n")
    alpha_t = iv.transverse_pressure_angle(alpha_n, beta_rad)
    without_shift = (
        m_n * math.cos(alpha_n) * (math.pi * (_spanned(k) - 0.5) + number * iv.inv(alpha_t))
    )
    return finite_result(
        safe_div(W_k - without_shift, 2.0 * m_n * math.sin(alpha_n), what="x from W_k (Eq. (14))"),
        "profile shift coefficient from the span",
    )


@eq(SOURCE, "(16)", section="7.2", page=13)
def contact_line_overlap(W_k_mm: float) -> float:
    """Overlap of the contact lines the span measurement of a helical gear needs:
    b_M = 1,2 + 0,018 W_k (mm)."""
    return finite_result(1.2 + 0.018 * positive_input(W_k_mm, "span measurement W_k"), "b_M")


@eq(SOURCE, "(15)", section="7.2", page=13)
def min_usable_face_width(W_k_mm: float, beta_b_rad: float, b_M_mm: float) -> float:
    """Smallest usable face width for the span measurement:
    b_Fmin = W_k sin(beta_b) + b_M cos(beta_b), with the amount of the base helix angle."""
    W_k = positive_input(W_k_mm, "span measurement W_k")
    beta_b = abs(helix(beta_b_rad))
    b_M = positive_input(b_M_mm, "contact line overlap b_M")
    return finite_result(W_k * math.sin(beta_b) + b_M * math.cos(beta_b), "b_Fmin")


@eq(SOURCE, "(17)", section="7.2", page=14, note="spur gear")
@eq(OLD, "(3.8.15)", section="3.8.2", page=21, note="helical gear: W_k cos(beta_b)")
def span_measuring_circle_diameter(d_b_mm: float, W_k_mm: float, beta_b_rad: float) -> float:
    """Measuring circle of the span with the measuring planes placed symmetrically:
    d_M = sqrt(d_b^2 + (W_k cos(beta_b))^2).

    DIN 21773 Eq. (17) prints d_M = sqrt(d_b^2 + W_k^2) for a spur gear; the transverse
    projection W_k cos(beta_b) of the span of a helical gear is DIN 3960 Eq. (3.8.15).
    """
    d_b = positive_input(d_b_mm, "base diameter d_b")
    W_k = positive_input(W_k_mm, "span measurement W_k")
    return finite_result(math.hypot(d_b, W_k * math.cos(helix(beta_b_rad))), "measuring circle d_M")


# --- §8 to §11 dimensions over balls and rollers ------------------------------------------------


@eq(SOURCE, "(27)", section="8", page=18)
@eq(SOURCE, "(29)", section="8", page=20, note="spur gear: explicit")
def ideal_ball_centre_profile_angle(
    alpha_vt_rad: float, eta_b_rad: float, beta_b_rad: float
) -> float:
    """Transverse profile angle alpha_Kt at the circle through the centre of a ball that touches
    the flanks on the V-cylinder, from
    alpha_Kt + inv(alpha_Kt) sin^2(beta_b) = tan(alpha_vt) + eta_b cos^2(beta_b).

    For a spur gear the equation is explicit: alpha_K = tan(alpha_v) + eta_b (Eq. (29)).
    """
    alpha_vt = pressure_angle(alpha_vt_rad, "transverse profile angle alpha_vt at the V-circle")
    eta_b = finite_input(eta_b_rad, "base space width half angle eta_b")
    sine_squared = math.sin(helix(beta_b_rad)) ** 2
    target = finite_result(math.tan(alpha_vt) + eta_b * (1.0 - sine_squared), "Eq. (27)")
    if sine_squared == 0.0:
        angle = target
    else:

        def residual(alpha: float) -> float:
            return alpha + (math.tan(alpha) - alpha) * sine_squared - target

        if target < 0.0 or residual(iv.INV_ALPHA_MAX_RAD) < 0.0:
            raise GeometryInfeasibleError(
                f"ideal measuring ball: Eq. (27) has no solution in [0, 89 deg] (right side {target!r})"
            )
        angle = float(brentq(residual, 0.0, iv.INV_ALPHA_MAX_RAD, xtol=4.0e-16, rtol=8.9e-16))
    if not 0.0 <= angle < HALF_PI - EPS:
        raise GeometryInfeasibleError(
            f"ideal measuring ball: profile angle alpha_Kt = {angle!r} rad lies outside [0, 90 deg)"
        )
    return angle


@eq(SOURCE, "(26)", section="8", page=18)
def ideal_measuring_ball_diameter(
    z: int,
    m_n_mm: float,
    alpha_n_rad: float,
    beta_b_rad: float,
    alpha_Kt_rad: float,
    alpha_vt_rad: float,
) -> float:
    """Diameter of the measuring ball whose contact points lie on the V-cylinder:
    D_M = z m_n cos(alpha_n) (tan(alpha_Kt) - tan(alpha_vt)) / cos^2(beta_b)."""
    number = teeth(z)
    m_n = positive_input(m_n_mm, "normal module m_n")
    alpha_n = pressure_angle(alpha_n_rad, "normal pressure angle alpha_n")
    alpha_Kt = pressure_angle(alpha_Kt_rad, "profile angle alpha_Kt")
    alpha_vt = pressure_angle(alpha_vt_rad, "transverse profile angle alpha_vt at the V-circle")
    difference = math.tan(alpha_Kt) - math.tan(alpha_vt)
    D_M = number * m_n * math.cos(alpha_n) * difference / math.cos(helix(beta_b_rad)) ** 2
    if D_M <= 0.0:
        raise GeometryInfeasibleError(
            f"ideal measuring ball diameter D_M = {D_M!r} is not positive: the tooth space has "
            "no width on the V-cylinder"
        )
    return finite_result(D_M, "ideal measuring ball diameter D_M")


def _inv_alpha_Kt(
    D_M: float, z: int, m_n_mm: float, alpha_n_rad: float, eta_rad: float, alpha_t_rad: float
) -> float:
    """Right side of Eq. (30): D_M / (z m_n cos(alpha_n)) - eta + inv(alpha_t)."""
    number = teeth(z)
    m_n = positive_input(m_n_mm, "normal module m_n")
    alpha_n = pressure_angle(alpha_n_rad, "normal pressure angle alpha_n")
    eta = finite_input(eta_rad, "space width half angle eta")
    return finite_result(
        D_M / (number * m_n * math.cos(alpha_n)) - eta + iv.inv(alpha_t_rad), "inv alpha_Kt"
    )


@eq(SOURCE, "(30)", section="8", page=20)
def ball_centre_profile_angle(
    D_M_mm: float, z: int, m_n_mm: float, alpha_n_rad: float, eta_rad: float, alpha_t_rad: float
) -> float:
    """Transverse profile angle at the circle through the centre of the ball D_M, from
    inv(alpha_Kt) = D_M / (z m_n cos(alpha_n)) - eta + inv(alpha_t)."""
    D_M = positive_input(D_M_mm, "measuring ball diameter D_M")
    value = _inv_alpha_Kt(D_M, z, m_n_mm, alpha_n_rad, eta_rad, alpha_t_rad)
    if value < 0.0:
        raise GeometryInfeasibleError(
            f"measuring ball D_M = {D_M!r} mm: inv(alpha_Kt) = {value!r} < 0, the ball is too "
            "small to rest on the involutes of the tooth space"
        )
    if value > iv.INV_MAX:
        raise GeometryInfeasibleError(
            f"measuring ball D_M = {D_M!r} mm: inv(alpha_Kt) = {value!r} exceeds inv(89 deg), the "
            "ball is too large for this tooth space"
        )
    return iv.inv_inverse(value)


@eq(SOURCE, "(31)", section="8", page=20)
def ball_centre_circle_diameter(d_b_mm: float, alpha_Kt_rad: float) -> float:
    """Diameter of the circle on which the centre of the ball lies: d_K = d_b / cos(alpha_Kt)."""
    d_b = positive_input(d_b_mm, "base diameter d_b")
    alpha_Kt = pressure_angle(alpha_Kt_rad, "profile angle alpha_Kt")
    return finite_result(safe_div(d_b, math.cos(alpha_Kt), what="d_K (Eq. (31))"), "d_K")


@eq(SOURCE, "(32)", section="8", page=20)
def radial_single_ball_dimension(d_K_mm: float, D_M_mm: float) -> float:
    """Radial single-ball dimension: M_rK = (d_K + D_M) / 2 (external gear)."""
    d_K = positive_input(d_K_mm, "ball centre circle diameter d_K")
    return finite_result(
        0.5 * (d_K + positive_input(D_M_mm, "measuring ball diameter D_M")), "M_rK"
    )


@eq(SOURCE, "(34)", section="8", page=20)
def ball_contact_profile_angle(
    alpha_Kt_rad: float, D_M_mm: float, d_b_mm: float, beta_b_rad: float
) -> float:
    """Transverse profile angle at the measuring circle of the ball:
    tan(alpha_Mt) = tan(alpha_Kt) - D_M cos(beta_b) / d_b."""
    alpha_Kt = pressure_angle(alpha_Kt_rad, "profile angle alpha_Kt")
    D_M = positive_input(D_M_mm, "measuring ball diameter D_M")
    d_b = positive_input(d_b_mm, "base diameter d_b")
    tangent = math.tan(alpha_Kt) - D_M * math.cos(helix(beta_b_rad)) / d_b
    if tangent < 0.0:
        raise GeometryInfeasibleError(
            f"measuring ball D_M = {D_M!r} mm: tan(alpha_Mt) = {tangent!r} < 0, the contact "
            "points would lie below the base circle"
        )
    return math.atan(finite_result(tangent, "tan alpha_Mt"))


@eq(SOURCE, "(33)", section="8", page=20)
def ball_measuring_circle_diameter(d_b_mm: float, alpha_Mt_rad: float) -> float:
    """Diameter of the cylinder on which the ball touches the flanks:
    d_M = d_b / cos(alpha_Mt)."""
    d_b = positive_input(d_b_mm, "base diameter d_b")
    alpha_Mt = pressure_angle(alpha_Mt_rad, "profile angle alpha_Mt at the measuring circle")
    return finite_result(safe_div(d_b, math.cos(alpha_Mt), what="d_M (Eq. (33))"), "d_M")


@eq(SOURCE, "(35)", section="10", page=21, note="even number of teeth")
@eq(SOURCE, "(36)", section="10", page=21, note="odd number of teeth")
def diametral_two_ball_dimension(d_K_mm: float, D_M_mm: float, z: int) -> float:
    """Diametral two-ball dimension of an external gear: M_dK = d_K + D_M for an even number of
    teeth, M_dK = d_K cos(pi / (2 z)) + D_M for an odd one."""
    d_K = positive_input(d_K_mm, "ball centre circle diameter d_K")
    D_M = positive_input(D_M_mm, "measuring ball diameter D_M")
    number = teeth(z)
    across = d_K if number % 2 == 0 else d_K * math.cos(math.pi / (2.0 * number))
    return finite_result(across + D_M, "diametral two-ball dimension M_dK")


@eq(SOURCE, "(35)", section="10", page=21, note="applied to rollers by §11, p. 22: even z")
@eq(SOURCE, "(36)", section="10", page=21, note="applied to rollers by §11, p. 22: spur, odd z")
@eq(SOURCE, "(37)", section="11", page=22, note="equal to twice Eq. (32) for an odd helical gear")
def diametral_two_roller_dimension(d_K_mm: float, D_M_mm: float, z: int, beta_rad: float) -> float:
    """Diametral two-roller dimension of an external gear.

    For an even number of teeth and for a spur gear it equals the two-ball dimension. On a
    helical gear with an odd number of teeth the rollers screw themselves into positions
    exactly opposite each other: the dimension is twice the radial single-roller dimension,
    M_dZ = d_K + D_M (§11, p. 22).
    """
    d_K = positive_input(d_K_mm, "ball centre circle diameter d_K")
    D_M = positive_input(D_M_mm, "measuring roller diameter D_M")
    number = teeth(z)
    if number % 2 == 0 or helix(beta_rad) != 0.0:
        return finite_result(d_K + D_M, "diametral two-roller dimension M_dZ")
    return finite_result(d_K * math.cos(math.pi / (2.0 * number)) + D_M, "M_dZ")


@eq(SOURCE, "(35)", section="10", page=21, note="solved for d_K")
@eq(SOURCE, "(36)", section="10", page=21, note="solved for d_K")
def ball_centre_circle_diameter_from_dimension(M_dK_mm: float, D_M_mm: float, z: int) -> float:
    """Ball centre circle of a diametral two-ball dimension: d_K = M_dK - D_M for an even number
    of teeth, d_K = (M_dK - D_M) / cos(pi / (2 z)) for an odd one."""
    M_dK = positive_input(M_dK_mm, "diametral two-ball dimension M_dK")
    D_M = positive_input(D_M_mm, "measuring ball diameter D_M")
    number = teeth(z)
    across = M_dK - D_M
    if across <= 0.0:
        raise GeometryInfeasibleError(
            f"two-ball dimension M_dK = {M_dK!r} mm does not exceed the ball diameter {D_M!r} mm"
        )
    if number % 2 == 1:
        across /= math.cos(math.pi / (2.0 * number))
    return finite_result(across, "ball centre circle diameter d_K")


@eq(SOURCE, "(30)", section="8", page=20, note="solved for eta")
@eq(BALLS, "(3)", section="Anhang A", page=6, note="the same as the actual allowance A_s")
def space_width_half_angle_from_ball(
    D_M_mm: float,
    z: int,
    m_n_mm: float,
    alpha_n_rad: float,
    alpha_t_rad: float,
    alpha_Kt_rad: float,
) -> float:
    """Space width half angle of the gear a ball rests in:
    eta = D_M / (z m_n cos(alpha_n)) + inv(alpha_t) - inv(alpha_Kt)."""
    D_M = positive_input(D_M_mm, "measuring ball diameter D_M")
    number = teeth(z)
    m_n = positive_input(m_n_mm, "normal module m_n")
    alpha_n = pressure_angle(alpha_n_rad, "normal pressure angle alpha_n")
    return finite_result(
        D_M / (number * m_n * math.cos(alpha_n)) + iv.inv(alpha_t_rad) - iv.inv(alpha_Kt_rad),
        "space width half angle eta",
    )


@eq(GEOMETRY, "(46)", section="4.7.4", page=36, note="solved for x")
def profile_shift_coefficient_from_space_half_angle(
    eta_rad: float, z: int, alpha_n_rad: float
) -> float:
    """The coefficient of a space width half angle: x = (pi - 2 z eta) / (4 tan(alpha_n))."""
    eta = finite_input(eta_rad, "space width half angle eta")
    alpha_n = pressure_angle(alpha_n_rad, "normal pressure angle alpha_n")
    return finite_result(
        safe_div(math.pi - 2.0 * teeth(z) * eta, 4.0 * math.tan(alpha_n), what="x from eta"),
        "profile shift coefficient from the space width half angle",
    )


def profile_shift_coefficient_from_ball_dimension(
    M_dK_mm: float, D_M_mm: float, z: int, m_n_mm: float, alpha_n_rad: float, beta_rad: float
) -> float:
    """The coefficient a diametral two-ball dimension corresponds to (Eq. (35), (36), (31),
    (30) and DIN ISO 21771 Eq. (46), each solved for the unknown). Like a span it is x, x_Es,
    x_Em or x_Ei, depending on what the dimension is (§4)."""
    number = teeth(z)
    alpha_n = pressure_angle(alpha_n_rad, "normal pressure angle alpha_n")
    alpha_t = iv.transverse_pressure_angle(alpha_n, beta_rad)
    d_b = iv.base_diameter(number, m_n_mm, alpha_n, beta_rad)
    d_K = ball_centre_circle_diameter_from_dimension(M_dK_mm, D_M_mm, number)
    alpha_Kt = iv.transverse_profile_angle_at(d_K, d_b)
    eta = space_width_half_angle_from_ball(D_M_mm, number, m_n_mm, alpha_n, alpha_t, alpha_Kt)
    return profile_shift_coefficient_from_space_half_angle(eta, number, alpha_n)


# --- DIN 3977: diameters of the measuring balls and rollers --------------------------------------


@lru_cache(maxsize=1)
def standard_measuring_ball_diameters() -> tuple[float, ...]:
    """Nominal diameters D_M of measuring balls and rollers in mm, ascending (DIN 3977:1981-02
    Tabelle 1, p. 1; ``data/din3977_table_1.yaml``)."""
    loaded = yaml.safe_load(data_path("din3977_table_1.yaml").read_text(encoding="utf-8"))
    values = tuple(float(value) for value in loaded["diameters_mm"])
    if list(values) != sorted(set(values)) or not values:
        raise ValueError("din3977_table_1.yaml: diameters must be ascending and distinct")
    return values


@eq(BALLS, "Tab. 1", section="4", page=1)
def next_larger_measuring_ball_diameter(D_M_mm: float) -> float:
    """The smallest diameter of DIN 3977 Tabelle 1 that is not smaller than ``D_M_mm``.

    Abschnitt 1 has the diameter to be used selected from Tabelle 1 after the value the
    equations give; Anhang A (p. 6) says that a somewhat larger diameter is mostly practical for
    an external gear. A value within ``EPS`` above a tabulated diameter is that diameter.
    """
    wanted = positive_input(D_M_mm, "measuring ball diameter D_M")
    for diameter in standard_measuring_ball_diameters():
        if diameter * (1.0 + EPS) >= wanted:
            return diameter
    raise InputRangeError(
        f"measuring ball diameter {D_M_mm!r} mm exceeds the largest diameter of DIN 3977 "
        f"Tabelle 1 ({standard_measuring_ball_diameters()[-1]!r} mm)"
    )


@eq(BALLS, "Abschnitt 6", section="6", page=2)
def measuring_circle_offset_factor(d_M_mm: float, d_v_mm: float, m_n_mm: float) -> float:
    """Radial distance of the measuring circle from the V-cylinder as a factor of the module:
    0,5 (d_M - d_v) / m_n. DIN 3977 admits -0,1 to +0,5 for an external gear."""
    d_M = positive_input(d_M_mm, "measuring circle diameter d_M")
    d_v = positive_input(d_v_mm, "V-circle diameter d_v")
    return finite_result(0.5 * (d_M - d_v) / positive_input(m_n_mm, "normal module m_n"), "offset")


# --- §13 tip cylinder cut by the tool --------------------------------------------------------------


@eq(SOURCE, "(40)", section="13", page=23)
def overcut_tip_diameter(d_mm: float, x_Es: float, m_n_mm: float, h_fP0_mm: float) -> float:
    """Diameter of the tip cylinder a topping hob generates: d_aM = d + 2 x_Es m_n + 2 h_fP0."""
    d = positive_input(d_mm, "reference diameter d")
    shift = finite_input(x_Es, "generating profile shift coefficient x_Es")
    m_n = positive_input(m_n_mm, "normal module m_n")
    h_fP0 = positive_input(h_fP0_mm, "tool dedendum h_fP0")
    return finite_result(d + 2.0 * (shift * m_n + h_fP0), "overcut tip diameter d_aM")


# --- x, x_E and the tooth thickness allowance --------------------------------------------------------


@eq(GEOMETRY, "(123)", section="7.4", page=67, note="solved for x")
@eq(GEOMETRY, "(124)", section="7.4", page=67, note="solved for x")
@eq(SOURCE, "(44)", section="14.1", page=24, note="solved for x")
def profile_shift_coefficient_from_generating(
    x_E: float, m_n_mm: float, alpha_n_rad: float, tooth_thickness_allowance_um: float
) -> float:
    """Nominal profile shift coefficient of a gear whose generating profile shift coefficient
    and tooth thickness allowance are known: x = x_E - E_sn / (2 m_n tan(alpha_n)).

    x_Es goes with E_sns, x_Em with E_snm, x_Ei with E_sni. The allowance is in micrometres.
    """
    shift = finite_input(x_E, "generating profile shift coefficient x_E")
    m_n = positive_input(m_n_mm, "normal module m_n")
    alpha_n = pressure_angle(alpha_n_rad, "normal pressure angle alpha_n")
    allowance = 1.0e-3 * finite_input(
        tooth_thickness_allowance_um, "tooth thickness allowance E_sn"
    )
    return finite_result(
        shift
        - safe_div(allowance, 2.0 * m_n * math.tan(alpha_n), what="E_sn / (2 m_n tan alpha_n)"),
        "profile shift coefficient x",
    )


@eq(GEOMETRY, "(123)", section="7.4", page=67, note="solved for E_sns")
@eq(GEOMETRY, "(124)", section="7.4", page=67, note="solved for E_sni")
def tooth_thickness_allowance_from_generating(
    x_E: float, x: float, m_n_mm: float, alpha_n_rad: float
) -> float:
    """Tooth thickness allowance in micrometres of a gear whose nominal and generating profile
    shift coefficients are known: E_sn = 2 m_n tan(alpha_n) (x_E - x)."""
    generated = finite_input(x_E, "generating profile shift coefficient x_E")
    m_n = positive_input(m_n_mm, "normal module m_n")
    alpha_n = pressure_angle(alpha_n_rad, "normal pressure angle alpha_n")
    return finite_result(
        1.0e3 * 2.0 * m_n * math.tan(alpha_n) * (generated - _shift(x)),
        "tooth thickness allowance E_sn",
    )


# --- §14 allowances, allowance factors, limits ---------------------------------------------------


@eq(SOURCE, "(45)", section="14.2", page=24, note="solved for T_sn")
def tooth_thickness_tolerance(E_sns_um: float, E_sni_um: float) -> float:
    """Tooth thickness tolerance in micrometres: T_sn = E_sns - E_sni (not negative)."""
    upper = finite_input(E_sns_um, "upper tooth thickness allowance E_sns")
    lower = finite_input(E_sni_um, "lower tooth thickness allowance E_sni")
    if upper < lower:
        raise InputRangeError(
            f"upper tooth thickness allowance {upper!r} must not lie below the lower one {lower!r}"
        )
    return finite_result(upper - lower, "tooth thickness tolerance T_sn")


@eq(SOURCE, "(43)", section="14.1", page=24)
def mean_tooth_thickness_allowance(E_sns_um: float, T_sn_um: float) -> float:
    """Mean tooth thickness allowance in micrometres: E_snm = E_sns - T_sn / 2."""
    upper = finite_input(E_sns_um, "upper tooth thickness allowance E_sns")
    tolerance = finite_input(T_sn_um, "tooth thickness tolerance T_sn")
    if tolerance < 0.0:
        raise InputRangeError(f"tooth thickness tolerance T_sn must be >= 0, got {T_sn_um!r}")
    return finite_result(upper - 0.5 * tolerance, "mean tooth thickness allowance E_snm")


@eq(SOURCE, "(54)", section="14.4", page=25)
def span_allowance_factor(alpha_n_rad: float) -> float:
    """Allowance factor of the span measurement: E_W* = cos(alpha_n)."""
    return math.cos(pressure_angle(alpha_n_rad, "normal pressure angle alpha_n"))


@eq(SOURCE, "(54)", section="14.4", page=25, note="E_W = E_sn E_W*")
def span_allowance(tooth_thickness_allowance_um: float, alpha_n_rad: float) -> float:
    """Span allowance of a tooth thickness allowance, in micrometres: E_W = E_sn cos(alpha_n)."""
    allowance = finite_input(tooth_thickness_allowance_um, "tooth thickness allowance E_sn")
    return finite_result(allowance * span_allowance_factor(alpha_n_rad), "span allowance E_W")


@eq(SOURCE, "(54)", section="14.4", page=25, note="solved for E_sn")
def tooth_thickness_allowance_from_span_allowance(
    span_allowance_um: float, alpha_n_rad: float
) -> float:
    """Tooth thickness allowance of a span allowance, in micrometres:
    E_sn = E_W / cos(alpha_n)."""
    allowance = finite_input(span_allowance_um, "span allowance E_W")
    return finite_result(
        safe_div(allowance, span_allowance_factor(alpha_n_rad), what="E_sn = E_W / cos alpha_n"),
        "tooth thickness allowance E_sn",
    )


@eq(SOURCE, "(51)", section="14.3", page=25)
@eq(SOURCE, "(48)", section="14.3", page=25, note="on the reference cylinder: 1")
def chordal_tooth_thickness_allowance_factor(
    d_y_mm: float, beta_y_rad: float, d_mm: float, beta_rad: float
) -> float:
    """Allowance factor of the chordal tooth thickness on the cylinder d_y:
    E_scny* = d_y cos(beta_y) / (d cos(beta)); 1 on the reference cylinder (Eq. (48)), which
    the norm sets "bei Zähnezahlen über z = 12 im Allgemeinen" (p. 25; the chord of fewer teeth
    changes by less than the arc: z = 6 about 0,966). The limits of the result do not use the
    factor; they are computed with x_Es, x_Em and x_Ei (§4)."""
    d_y = positive_input(d_y_mm, "diameter d_y")
    d = positive_input(d_mm, "reference diameter d")
    numerator = d_y * math.cos(helix(beta_y_rad))
    return finite_result(
        safe_div(numerator, d * math.cos(helix(beta_rad)), what="E_scny* (Eq. (51))"), "E_scny*"
    )


@eq(SOURCE, "(57)", section="14.5", page=25)
def radial_ball_dimension_allowance_factor(
    alpha_t_rad: float, alpha_Kt_rad: float, beta_rad: float
) -> float:
    """Allowance factor of the radial single-ball or single-roller dimension:
    E_MrK* = cos(alpha_t) / (2 sin(alpha_Kt) cos(beta))."""
    alpha_t = pressure_angle(alpha_t_rad, "transverse pressure angle alpha_t")
    alpha_Kt = pressure_angle(alpha_Kt_rad, "profile angle alpha_Kt")
    denominator = 2.0 * math.sin(alpha_Kt) * math.cos(helix(beta_rad))
    return finite_result(
        safe_div(math.cos(alpha_t), denominator, what="E_MrK* (Eq. (57))"), "E_MrK*"
    )


@eq(SOURCE, "(60)", section="14.6", page=26, note="even number of teeth")
@eq(SOURCE, "(61)", section="14.6", page=26, note="odd number of teeth")
def diametral_ball_dimension_allowance_factor(
    alpha_t_rad: float, alpha_Kt_rad: float, beta_rad: float, z: int
) -> float:
    """Allowance factor of the diametral two-ball dimension (and of the two-roller dimension
    wherever that equals it): E_MdK* = cos(alpha_t) / (sin(alpha_Kt) cos(beta)), times
    cos(pi / (2 z)) for an odd number of teeth. Rollers on a helical gear with an odd number of
    teeth lie opposite each other (§11): their factor is twice E_MrK*, without the cosine."""
    number = teeth(z)
    factor = 2.0 * radial_ball_dimension_allowance_factor(alpha_t_rad, alpha_Kt_rad, beta_rad)
    if number % 2 == 1:
        factor *= math.cos(math.pi / (2.0 * number))
    return finite_result(factor, "E_MdK*")


@eq(SOURCE, "(49)", section="14.3", page=25)
@eq(SOURCE, "(52)", section="14.3", page=25)
@eq(SOURCE, "(55)", section="14.4", page=25)
@eq(SOURCE, "(58)", section="14.5", page=25)
@eq(SOURCE, "(62)", section="14.6", page=26)
def upper_limit_dimension(mean_mm: float, T_sn_um: float, allowance_factor: float) -> float:
    """Upper limit of an inspection dimension from its mean: mean + T_sn / 2 times the allowance
    factor (s_cns, s_cnys, W_ks, M_rKs, M_dKs). The tolerance is given in micrometres."""
    return _limit_dimension(mean_mm, T_sn_um, allowance_factor, 0.5)


@eq(SOURCE, "(50)", section="14.3", page=25)
@eq(SOURCE, "(53)", section="14.3", page=25)
@eq(SOURCE, "(56)", section="14.4", page=25)
@eq(SOURCE, "(59)", section="14.5", page=25)
@eq(SOURCE, "(63)", section="14.6", page=26)
def lower_limit_dimension(mean_mm: float, T_sn_um: float, allowance_factor: float) -> float:
    """Lower limit of an inspection dimension from its mean: mean - T_sn / 2 times the allowance
    factor (s_cni, s_cnyi, W_ki, M_rKi, M_dKi). The tolerance is given in micrometres."""
    return _limit_dimension(mean_mm, T_sn_um, allowance_factor, -0.5)


def _limit_dimension(mean_mm: float, T_sn_um: float, allowance_factor: float, half: float) -> float:
    mean = positive_input(mean_mm, "mean of the inspection dimension")
    tolerance = finite_input(T_sn_um, "tooth thickness tolerance T_sn")
    if tolerance < 0.0:
        raise InputRangeError(f"tooth thickness tolerance T_sn must be >= 0, got {T_sn_um!r}")
    factor = finite_input(allowance_factor, "allowance factor")
    return finite_result(mean + half * 1.0e-3 * tolerance * factor, "limit of the dimension")


# --- orchestrator ------------------------------------------------------------------------------------

ROLES = ("pinion", "wheel")


def _warning(code: str, field: str, message: str) -> InputWarning:
    return InputWarning(code=code, field=field, message=message)


def _limits(values: dict[str, float]) -> DimensionLimits:
    return DimensionLimits(
        nominal=values["nominal"], upper=values["upper"], mean=values["mean"], lower=values["lower"]
    )


class _Gear:
    """Constants of one gear the inspection dimensions are computed from."""

    def __init__(self, role: str, generated: GearGeneration, pair: PairInput) -> None:
        self.role = role
        self.z = generated.number_of_teeth
        self.m_n = pair.normal_module_mm
        self.alpha_n = math.radians(pair.normal_pressure_angle_deg)
        sign = 1.0 if role == "pinion" else -1.0
        self.beta = sign * math.radians(pair.helix_angle_deg)
        self.alpha_t = iv.transverse_pressure_angle(self.alpha_n, self.beta)
        self.beta_b = iv.base_helix_angle(self.beta, self.alpha_n)
        self.d = iv.reference_diameter(self.z, self.m_n, self.beta)
        self.d_b = iv.base_diameter(self.z, self.m_n, self.alpha_n, self.beta)
        self.d_a = generated.tip_diameter_mm
        self.d_Fa = generated.tip_form_diameter_mm
        self.d_Ff = generated.root_form_diameter_mm

    def ball(self, D_M: float, x: float) -> tuple[float, float, float]:
        """(alpha_Kt, d_K, d_M) of the ball D_M in the gear with the coefficient x."""
        eta = iv.space_width_half_angle(self.z, x, self.alpha_n)
        alpha_Kt = ball_centre_profile_angle(D_M, self.z, self.m_n, self.alpha_n, eta, self.alpha_t)
        d_K = ball_centre_circle_diameter(self.d_b, alpha_Kt)
        alpha_Mt = ball_contact_profile_angle(alpha_Kt, D_M, self.d_b, self.beta_b)
        return alpha_Kt, d_K, ball_measuring_circle_diameter(self.d_b, alpha_Mt)

    def ball_rests_on_the_flanks(self, D_M: float, x: float) -> bool:
        """True if Eq. (30) and (34) have a solution: the ball rests on the two involutes."""
        eta = iv.space_width_half_angle(self.z, x, self.alpha_n)
        value = _inv_alpha_Kt(D_M, self.z, self.m_n, self.alpha_n, eta, self.alpha_t)
        if not 0.0 <= value <= iv.INV_MAX:
            return False
        tangent = math.tan(iv.inv_inverse(value)) - D_M * math.cos(self.beta_b) / self.d_b
        return tangent >= 0.0

    def on_usable_flank(self, d_M: float) -> bool:
        return self.d_Ff * (1.0 - EPS) <= d_M <= self.d_Fa * (1.0 + EPS)


def _number_of_teeth_spanned(
    g: _Gear, gear: GearInput, x_Es: float, d_v: float, warnings: list[InputWarning]
) -> tuple[int | None, int, int]:
    """(k, k_min, k_max): the k of the input, else Eq. (9) within the range of Eq. (12), (13)."""
    k_min = max(
        min_number_of_teeth_spanned(g.z, g.m_n, x_Es, g.alpha_n, g.beta, g.d_Ff), MIN_TEETH_SPANNED
    )
    k_max = max_number_of_teeth_spanned(g.z, g.m_n, x_Es, g.alpha_n, g.beta, g.d_Fa)
    given = gear.number_of_teeth_spanned
    if given is None and gear.span is not None:
        given = gear.span.number_of_teeth_spanned
    if given is not None:
        if not k_min <= given <= k_max:
            raise GeometryInfeasibleError(
                f"{g.role}: the measuring planes over the given number of teeth spanned "
                f"k = {given} do not touch the involute between the form circles: the usable "
                f"range is {k_min} to {k_max} (DIN 21773 Eq. (12), (13))"
            )
        return given, k_min, k_max
    if k_min > k_max:
        warnings.append(
            _warning(
                "span_not_measurable",
                "span_measurement_mm",
                f"{g.role}: no number of teeth spanned touches the flank between the form "
                f"circles (k_min = {k_min} > k_max = {k_max}, DIN 21773 Eq. (12), (13)); no span "
                "measurement is given",
            )
        )
        return None, k_min, k_max
    if d_v <= g.d_b * (1.0 + EPS):
        warnings.append(
            _warning(
                "v_circle_below_base_circle",
                "number_of_teeth_spanned",
                f"{g.role}: the V-circle d_v = {d_v!r} mm does not lie above the base circle, "
                f"Eq. (9) has no value; the smallest usable number of teeth spanned {k_min} is "
                "taken",
            )
        )
        return k_min, k_min, k_max
    k = number_of_teeth_spanned(g.z, g.m_n, x_Es, g.alpha_n, g.beta, d_v)
    if not k_min <= k <= k_max:
        moved = min(max(k, k_min), k_max)
        warnings.append(
            _warning(
                "number_of_teeth_spanned_moved_into_usable_range",
                "number_of_teeth_spanned",
                f"{g.role}: Eq. (9) gives k = {k}, outside the usable range {k_min} to {k_max} of "
                f"Eq. (12), (13); k = {moved} is taken",
            )
        )
        k = moved
    return k, k_min, k_max


def _measuring_ball(
    g: _Gear,
    gear: GearInput,
    x_Es: float,
    x_Ei: float,
    d_v: float,
    d_fE: float,
    warnings: list[InputWarning],
) -> tuple[float, float | None]:
    """(D_M, ideal D_M): the ball of the input, else the next larger diameter of DIN 3977
    Tabelle 1 above the ideal one that rests on the usable flank and stands above the tip."""
    ideal: float | None = None
    if d_v > g.d_b * (1.0 + EPS):
        alpha_vt = iv.transverse_profile_angle_at(d_v, g.d_b)
        eta = iv.space_width_half_angle(g.z, x_Es, g.alpha_n)
        eta_b = iv.base_space_width_half_angle(eta, g.alpha_t)
        # (a tooth space without width on the V-cylinder holds no ball there)
        if iv.space_width_half_angle_at(eta, g.alpha_t, alpha_vt) > 0.0:
            alpha_Kt = ideal_ball_centre_profile_angle(alpha_vt, eta_b, g.beta_b)
            ideal = ideal_measuring_ball_diameter(
                g.z, g.m_n, g.alpha_n, g.beta_b, alpha_Kt, alpha_vt
            )
    given = gear.measuring_ball_diameter_mm
    if given is None and gear.ball_dimension is not None:
        given = gear.ball_dimension.measuring_ball_diameter_mm

    def stands_above_the_tip(D_M: float) -> bool:
        return g.ball(D_M, x_Ei)[1] + D_M > g.d_a

    def clears_the_root(D_M: float) -> bool:
        return g.ball(D_M, x_Ei)[1] - D_M > d_fE

    if given is not None:
        for x in (x_Es, x_Ei):
            d_M = g.ball(given, x)[2]
            if not g.on_usable_flank(d_M):
                raise GeometryInfeasibleError(
                    f"{g.role}: the measuring ball D_M = {given!r} mm touches the flanks on the "
                    f"circle d_M = {d_M!r} mm, outside the involute between the root form circle "
                    f"{g.d_Ff!r} mm and the tip form circle {g.d_Fa!r} mm (DIN 3977 Abschnitt 6)"
                )
        if not stands_above_the_tip(given):
            warnings.append(
                _warning(
                    "measuring_ball_below_tip_circle",
                    "measuring_ball_diameter_mm",
                    f"{g.role}: the measuring ball D_M = {given!r} mm does not stand above the tip "
                    "cylinder (DIN 3977 Abschnitt 6)",
                )
            )
        if not clears_the_root(given):
            warnings.append(
                _warning(
                    "measuring_ball_touches_root",
                    "measuring_ball_diameter_mm",
                    f"{g.role}: the measuring ball D_M = {given!r} mm reaches the root circle "
                    "(DIN 3977 Abschnitt 6)",
                )
            )
        return given, ideal
    table = standard_measuring_ball_diameters()
    if ideal is not None and ideal > table[-1] * (1.0 + EPS):
        raise GeometryInfeasibleError(
            f"{g.role}: the ball that touches on the V-cylinder has the diameter {ideal!r} mm, "
            f"above the largest of DIN 3977 Tabelle 1 ({table[-1]:g} mm): give "
            "measuring_ball_diameter_mm"
        )
    start = table[0] if ideal is None else next_larger_measuring_ball_diameter(ideal)
    for D_M in table[table.index(start) :]:
        if not (g.ball_rests_on_the_flanks(D_M, x_Es) and g.ball_rests_on_the_flanks(D_M, x_Ei)):
            continue
        if not all(g.on_usable_flank(g.ball(D_M, x)[2]) for x in (x_Es, x_Ei)):
            continue
        if stands_above_the_tip(D_M) and clears_the_root(D_M):
            if start != D_M:
                warnings.append(
                    _warning(
                        "measuring_ball_larger_than_next_table_value",
                        "measuring_ball_diameter_mm",
                        f"{g.role}: the next larger diameter of DIN 3977 Tabelle 1 above the "
                        f"ideal one, {start!r} mm, does not rest on the usable flank or does not "
                        f"stand above the tip cylinder; D_M = {D_M!r} mm is taken",
                    )
                )
            return D_M, ideal
    raise GeometryInfeasibleError(
        f"{g.role}: no measuring ball of DIN 3977 Tabelle 1 rests on the involute between the form "
        "circles, stands above the tip cylinder and clears the root: give "
        "measuring_ball_diameter_mm"
    )


def _gear_inspection(
    role: str,
    gear: GearInput,
    generated: GearGeneration,
    pair: PairInput,
    d_y: float | None,
) -> GearInspection:
    from gearcore import generation as gn  # (generation imports pair, pair imports this module)

    g = _Gear(role, generated, pair)
    warnings: list[InputWarning] = []
    x = generated.profile_shift_coefficient
    x_Es = generated.upper_generating_profile_shift_coefficient
    x_Ei = generated.lower_generating_profile_shift_coefficient
    allowance = generated.tooth_thickness_allowance_um
    tolerance: float | None = None
    span_allowances: tuple[float, float] | None = None
    x_Em = x
    if allowance is not None:
        tolerance = tooth_thickness_tolerance(allowance[0], allowance[1])
        mean = mean_tooth_thickness_allowance(allowance[0], tolerance)
        x_Em = gn.generating_profile_shift_coefficient(x, g.m_n, g.alpha_n, mean)
        span_allowances = (
            span_allowance(allowance[0], g.alpha_n),
            span_allowance(allowance[1], g.alpha_n),
        )
    states = {"nominal": x, "upper": x_Es, "mean": x_Em, "lower": x_Ei}
    d_v = v_circle_diameter(g.d, x_Es, g.m_n)

    # span measurement: §7
    k, k_min, k_max = _number_of_teeth_spanned(g, gear, x_Es, d_v, warnings)
    span: DimensionLimits | None = None
    span_circle: float | None = None
    b_Fmin: float | None = None
    if k is not None:
        span = _limits(
            {
                state: span_measurement(g.z, g.m_n, shift, g.alpha_n, g.beta, k)
                for state, shift in states.items()
            }
        )
        span_circle = span_measuring_circle_diameter(g.d_b, span.upper, g.beta_b)
        if g.beta != 0.0:
            b_Fmin = min_usable_face_width(span.upper, g.beta_b, contact_line_overlap(span.upper))
            if gear.face_width_mm < b_Fmin:
                warnings.append(
                    _warning(
                        "face_width_below_minimum_for_span",
                        "face_width_mm",
                        f"{role}: the face width {gear.face_width_mm!r} mm lies below the "
                        f"smallest usable face width b_Fmin = {b_Fmin!r} mm for the span over "
                        f"{k} teeth (DIN 21773 Eq. (15)); the span cannot be measured safely "
                        "(b is taken for the usable face width b_F: edge breaks of the face "
                        "are no input)",
                    )
                )

    # chords: §5 on the reference cylinder and on the cylinder the caller names, §6
    thickness = {
        state: iv.normal_tooth_thickness(g.m_n, shift, g.alpha_n) for state, shift in states.items()
    }
    chord: DimensionLimits | None = None
    chord_height: float | None = None
    constant: DimensionLimits | None = None
    constant_height: float | None = None
    if min(thickness.values()) > 0.0:
        constant = _limits(
            {state: constant_chord(s_n, g.alpha_t, g.beta) for state, s_n in thickness.items()}
        )
        constant_height = height_above_constant_chord(
            generated.addendum_mm,
            iv.transverse_tooth_thickness(g.m_n, x, g.alpha_n, g.beta),
            g.alpha_t,
        )
        touching = _constant_chord_contact_diameter(
            g.d, constant.nominal, generated.addendum_mm, constant_height
        )
        if not g.on_usable_flank(touching):
            warnings.append(
                _warning(
                    "constant_chord_outside_usable_flank",
                    "constant_chord_mm",
                    f"{role}: the end points of the constant chord lie on the circle "
                    f"{touching!r} mm, outside the involute between the form circles "
                    f"{g.d_Ff!r} mm and {g.d_Fa!r} mm (DIN 21773 §6); no constant chord is given",
                )
            )
            constant, constant_height = None, None
        if g.d_Ff < g.d < g.d_Fa:
            chord = _limits(
                {
                    state: chordal_tooth_thickness(s_n, g.d, g.beta)
                    for state, s_n in thickness.items()
                }
            )
            chord_height = chordal_height(g.d_a, thickness["nominal"], g.d, g.beta)
    if chord is None:
        warnings.append(
            _warning(
                "reference_cylinder_outside_usable_flank",
                "chordal_tooth_thickness_mm",
                f"{role}: the reference cylinder d = {g.d!r} mm does not lie between the form "
                f"circles {g.d_Ff!r} mm and {g.d_Fa!r} mm; no chordal tooth thickness is given on it",
            )
        )
    chord_y: DimensionLimits | None = None
    chord_y_height: float | None = None
    chord_y_factor: float | None = None
    if d_y is not None:
        if not g.d_Ff <= d_y <= g.d_Fa:
            raise GeometryInfeasibleError(
                f"{role}: the cylinder d_y = {d_y!r} mm of the chordal tooth thickness does not "
                f"lie between the form circles {g.d_Ff!r} mm and {g.d_Fa!r} mm"
            )
        alpha_yt = iv.transverse_profile_angle_at(d_y, g.d_b)
        beta_y = iv.helix_angle_at(d_y, g.d, g.beta)
        thickness_y = {}
        for state, shift in states.items():
            psi_y = iv.tooth_thickness_half_angle_at(
                iv.tooth_thickness_half_angle(g.z, shift, g.alpha_n), g.alpha_t, alpha_yt
            )
            thickness_y[state] = iv.normal_tooth_thickness_at(
                iv.transverse_tooth_thickness_at(d_y, psi_y), beta_y
            )
        if min(thickness_y.values()) <= 0.0:
            raise GeometryInfeasibleError(
                f"{role}: the tooth has no thickness on the cylinder d_y = {d_y!r} mm"
            )
        chord_y = _limits(
            {
                state: chordal_tooth_thickness(s_yn, d_y, beta_y)
                for state, s_yn in thickness_y.items()
            }
        )
        chord_y_height = chordal_height(g.d_a, thickness_y["nominal"], d_y, beta_y)
        chord_y_factor = chordal_tooth_thickness_allowance_factor(d_y, beta_y, g.d, g.beta)

    # balls and rollers: §8 to §11, DIN 3977
    D_M, ideal = _measuring_ball(
        g, gear, x_Es, x_Ei, d_v, generated.generated_root_diameter_mm, warnings
    )
    centres = {state: g.ball(D_M, shift) for state, shift in states.items()}
    alpha_Kt_upper, d_K_upper, d_M_upper = centres["upper"]
    offset = measuring_circle_offset_factor(d_M_upper, d_v, g.m_n)
    if not -MEASURING_CIRCLE_BELOW_V_CYLINDER <= offset <= MEASURING_CIRCLE_ABOVE_V_CYLINDER:
        warnings.append(
            _warning(
                "measuring_circle_outside_din3977_range",
                "measuring_ball_diameter_mm",
                f"{role}: the measuring circle of the ball D_M = {D_M!r} mm lies {offset!r} m_n "
                "from the V-cylinder; DIN 3977 Abschnitt 6 admits -0,1 m_n to +0,5 m_n",
            )
        )
    alpha_Kt_mean = centres["mean"][0]
    overcut: float | None = None
    if gear.tool.dedendum_factor is not None:
        overcut = overcut_tip_diameter(g.d, x_Es, g.m_n, gear.tool.dedendum_factor * g.m_n)

    return GearInspection(
        number_of_teeth=g.z,
        profile_shift_coefficient=x,
        upper_generating_profile_shift_coefficient=x_Es,
        mean_generating_profile_shift_coefficient=x_Em,
        lower_generating_profile_shift_coefficient=x_Ei,
        tooth_thickness_allowance_um=allowance,
        tooth_thickness_tolerance_um=tolerance,
        span_allowance_um=span_allowances,
        v_circle_diameter_mm=d_v,
        number_of_teeth_spanned=k,
        min_number_of_teeth_spanned=k_min,
        max_number_of_teeth_spanned=k_max,
        span_measurement_mm=span,
        span_measuring_circle_diameter_mm=span_circle,
        span_allowance_factor=span_allowance_factor(g.alpha_n),
        min_usable_face_width_mm=b_Fmin,
        chordal_tooth_thickness_mm=chord,
        height_above_chord_mm=chord_height,
        y_diameter_mm=d_y,
        chordal_tooth_thickness_at_y_mm=chord_y,
        height_above_chord_at_y_mm=chord_y_height,
        chordal_tooth_thickness_allowance_factor=chord_y_factor,
        constant_chord_mm=constant,
        height_above_constant_chord_mm=constant_height,
        ideal_measuring_ball_diameter_mm=ideal,
        measuring_ball_diameter_mm=D_M,
        ball_centre_circle_diameter_mm=d_K_upper,
        ball_measuring_circle_diameter_mm=d_M_upper,
        measuring_circle_offset_factor=offset,
        radial_single_ball_dimension_mm=_limits(
            {state: radial_single_ball_dimension(c[1], D_M) for state, c in centres.items()}
        ),
        diametral_two_ball_dimension_mm=_limits(
            {state: diametral_two_ball_dimension(c[1], D_M, g.z) for state, c in centres.items()}
        ),
        diametral_two_roller_dimension_mm=_limits(
            {
                state: diametral_two_roller_dimension(c[1], D_M, g.z, g.beta)
                for state, c in centres.items()
            }
        ),
        radial_ball_dimension_allowance_factor=radial_ball_dimension_allowance_factor(
            g.alpha_t, alpha_Kt_mean, g.beta
        ),
        diametral_ball_dimension_allowance_factor=diametral_ball_dimension_allowance_factor(
            g.alpha_t, alpha_Kt_mean, g.beta, g.z
        ),
        overcut_tip_diameter_mm=overcut,
        warnings=tuple(warnings),
    )


def compute_inspection(
    generation: GenerationResult, *, chord_diameter_mm: Pair[float] | None = None
) -> InspectionResult:
    """Inspection dimensions of the tooth thickness of both gears of a generated pair
    (DIN 21773:2014-08; measuring balls per DIN 3977:1981-02).

    ``generation`` is the result of ``gearcore.generation.compute_generation``: it carries the
    profile shift coefficients, the allowances the inputs determine and the form circles that
    bound the usable flank. ``chord_diameter_mm`` names, per gear, a cylinder on which the
    chordal tooth thickness is wanted beside the reference cylinder (DIN 21773 §5 leaves it to
    the user; ``stplus_program.stplus_chord_diameter`` is the one STplus takes).
    """
    if not isinstance(generation, GenerationResult):
        raise InputRangeError(f"a GenerationResult is required, got {type(generation).__name__}")
    cylinders: tuple[float | None, float | None] = (None, None)
    if chord_diameter_mm is not None:
        if not isinstance(chord_diameter_mm, Pair):
            raise InputRangeError(
                f"chord_diameter_mm must be a Pair (pinion, wheel), got {type(chord_diameter_mm).__name__}"
            )
        cylinders = (
            positive_input(chord_diameter_mm.pinion, "chord cylinder d_y of the pinion"),
            positive_input(chord_diameter_mm.wheel, "chord cylinder d_y of the wheel"),
        )
    pair = generation.inputs
    gears: Pair[GearInspection] = Pair(
        pinion=_gear_inspection(
            "pinion", pair.gears.pinion, generation.gears.pinion, pair, cylinders[0]
        ),
        wheel=_gear_inspection(
            "wheel", pair.gears.wheel, generation.gears.wheel, pair, cylinders[1]
        ),
    )
    return InspectionResult(
        inputs=pair,
        gears=gears,
        warnings=(*generation.warnings, *gears.pinion.warnings, *gears.wheel.warnings),
    )
