"""Geometry of an external cylindrical gear pair.

Source: DIN ISO 21771:2014-08 (ISO 21771:2007), §4.4 pitches, §4.5 diameters, §5.2 mating
quantities, §5.3 sum of the profile shift coefficients, §5.4 mesh, §5.6 sliding, and Eq. (127) of
§7.6. Every function realises one equation; angles are radians (``_rad``), lengths millimetres
(``_mm``). Index 1 is the pinion, index 2 the wheel (§5.1.3). Formulas are written for external
gear pairs (``z_2 / |z_2| = +1``); internal pairs are a prepared extension point.

Which values are given (ADR-107). Of the centre distance a_w and the nominal profile shift
coefficients x_1, x_2 exactly two are given; the third follows from Eq. (54), (55) and (62). A
given centre distance is fixed. All three given is an input error. A span measurement is not
evaluated yet: how a given span determines the profile shift (DIN 21773:2014-08 Eq. (14)) is
settled with the inspection dimensions and allowances (increments 4 and 5, open in ADR-107).

Tip diameters. The mesh needs the tip diameters. They are an input; the nominal value of
Eq. (33) is available through ``with_nominal_tip_diameters`` as an explicit choice (it needs the
addendum of the basic rack, which the tool-based input does not carry). Nothing is assumed
silently.

Form diameters. §5.4.1 limits the start of the active profile by the root form diameter d_Ff of
the gear itself (Eq. (66) to (69)); a tool with an edge break flank generates the tip form
diameter d_Fa. Both follow from the generation (§7.6, increment 3); until then they are optional
arguments and their absence is reported as a warning.

Driving gear. Points A and E of the path of contact swap with the driving gear; the quantities of
this module are written per gear and hold for either direction: g_a1 is Eq. (80), g_a2 = g_f1 is
Eq. (79).

Contact face width. Without an axial offset in the input the gears are taken as centred:
b_w = min(b_1, b_2).

Common tooth depth. Eq. (59) defines h_w with the tip circles. ``compute_pair_geometry``
evaluates it with the tip form circles instead (user decision 2026-09-30, ADR-112): beyond the
tip form circle, on a tip chamfer, the tooth does not carry. Without a chamfer both are the
same; with one the result says so and names the value of the tip circles.

Tolerance at boundaries. Boundaries are decided with the relative tolerance ``EPS``, so that the
same pair behaves the same at every module:

* a circle of the mating gear reaches beyond the tangent point of the line of action
  (interference) only if it does so by more than ``EPS`` of the distance of the tangent points;
* a root form diameter within ``EPS`` below the base circle is the base circle, a tip form
  diameter within ``EPS`` above the tip diameter is the tip diameter, a derived profile shift
  coefficient within ``EPS`` beyond its range is the limit of the range;
* the root form circle limits the active profile only if it exceeds the start of Eq. (64), (65)
  by more than ``EPS``. Close to the base circle a band of ``EPS`` in the diameter is a wide
  band in the roll length, so the contact ratio can change in its sixth digit across the band;
* a start of the active profile with d_Nf <= d_b (1 + ``EPS``) lies on the base circle. There the
  specific sliding is unbounded, and ``compute_pair_geometry`` raises. In terms of the radius of
  curvature this is about 7e-7 d_b; no result reports a start of the active profile closer to
  the base circle than that;
* an active profile without length, d_Nf >= d_Na (1 - ``EPS``), is no mesh.
"""

import math

from pydantic import ValidationError

from gearcore import involute as iv
from gearcore._guards import HALF_PI, helix, pressure_angle, teeth
from gearcore._safe import EPS, finite_input, finite_result, positive_input, safe_acos, safe_div
from gearcore.errors import GeometryInfeasibleError, InputRangeError, NotSupportedError
from gearcore.models.common import PROFILE_SHIFT_RANGE, InputWarning, Pair
from gearcore.models.inputs import GearKind, PairInput
from gearcore.models.results import BasicGearGeometry, PairGeometry
from gearcore.rack import has_edge_break_flank
from gearcore.trace import eq

SOURCE = "ISO21771:2014"

EQ_EXEMPT = ("compute_pair_geometry", "resolve_profile_shift", "with_nominal_tip_diameters")
"""Orchestrators assemble results from traced functions and carry no equation of their own."""


# --- input guards ---------------------------------------------------------------------------


def _working_angle(alpha_wt_rad: float) -> float:
    return pressure_angle(alpha_wt_rad, "working pressure angle alpha_wt")


def _gear_ratio(u: float) -> float:
    ratio = finite_input(u, "gear ratio u")
    if ratio < 1.0:
        raise InputRangeError(f"gear ratio u = z_2 / z_1 must be >= 1, got {u!r}")
    return ratio


def _roll_length(d_mm: float, d_b_mm: float) -> float:
    """sqrt(d^2 - d_b^2): twice the radius of curvature of Eq. (17) at the diameter d."""
    return 2.0 * iv.radius_of_curvature(d_mm, d_b_mm)


# --- §4.4 pitches -------------------------------------------------------------------------------


@eq(SOURCE, "(23)", section="4.4.2.1", page=31)
def transverse_pitch(m_n_mm: float, beta_rad: float) -> float:
    """Transverse pitch on the reference cylinder: p_t = pi m_n / cos(beta) = pi m_t."""
    return finite_result(math.pi * iv.transverse_module(m_n_mm, beta_rad), "p_t")


@eq(SOURCE, "(24)", section="4.4.2.2", page=32)
def normal_pitch(m_n_mm: float) -> float:
    """Normal pitch on the reference cylinder: p_n = pi m_n."""
    return finite_result(math.pi * positive_input(m_n_mm, "normal module m_n"), "p_n")


@eq(SOURCE, "(28)", section="4.4.5", page=33)
def transverse_base_pitch(m_n_mm: float, alpha_n_rad: float, beta_rad: float) -> float:
    """Transverse base pitch: p_bt = p_t cos(alpha_t)."""
    alpha_t = iv.transverse_pressure_angle(alpha_n_rad, beta_rad)
    return transverse_pitch(m_n_mm, beta_rad) * math.cos(alpha_t)


@eq(SOURCE, "(30)", section="4.4.5.1", page=33)
def transverse_contact_pitch(p_bt_mm: float) -> float:
    """Transverse pitch on the path of contact: p_et = p_bt."""
    return positive_input(p_bt_mm, "transverse base pitch p_bt")


# --- §4.5, §7.6 diameters -----------------------------------------------------------------------


@eq(SOURCE, "(33)", section="4.5.3", page=34)
def tip_diameter(d_mm: float, x: float, m_n_mm: float, h_aP_mm: float, k: float) -> float:
    """Nominal tip diameter: d_a = d + 2 (x m_n + h_aP + k m_n) (external gear).

    ``k`` is the tip alteration coefficient of §4.5.2 (signed; negative shortens the tooth).
    """
    d = positive_input(d_mm, "reference diameter d")
    m_n = positive_input(m_n_mm, "normal module m_n")
    h_aP = positive_input(h_aP_mm, "addendum of the basic rack h_aP")
    shift = finite_input(x, "profile shift coefficient x")
    alteration = finite_input(k, "tip alteration coefficient k")
    d_a = finite_result(d + 2.0 * (shift * m_n + h_aP + alteration * m_n), "tip diameter d_a")
    if d_a <= 0.0:
        raise GeometryInfeasibleError(f"tip diameter d_a = {d_a!r} is not positive")
    return d_a


@eq(SOURCE, "(127)", section="7.6", page=68)
def tip_form_diameter(d_a_mm: float, h_K_mm: float) -> float:
    """Tip form diameter: d_Fa = d_a - 2 h_K (external gear).

    h_K is the radial amount of the tip chamfer or of the tip rounding: §7.6 gives the equation
    for both. Without either, d_Fa = d_a.
    """
    d_a = positive_input(d_a_mm, "tip diameter d_a")
    h_K = finite_input(h_K_mm, "radial amount of the tip chamfer h_K")
    if h_K < 0.0:
        raise InputRangeError(f"radial amount of the tip chamfer h_K must be >= 0, got {h_K_mm!r}")
    d_Fa = d_a - 2.0 * h_K
    if d_Fa <= 0.0:
        raise GeometryInfeasibleError(f"tip form diameter d_Fa = {d_Fa!r} is not positive")
    return d_Fa


# --- §5.2 mating quantities ---------------------------------------------------------------------


@eq(SOURCE, "(52)", section="5.2.1", page=38)
def gear_ratio(z_1: int, z_2: int) -> float:
    """Gear ratio: u = z_2 / z_1 with |u| >= 1 (index 1 is the smaller gear)."""
    pinion, wheel = teeth(z_1, "number of teeth z_1"), teeth(z_2, "number of teeth z_2")
    if wheel < pinion:
        raise InputRangeError(
            f"index 1 names the pinion (the smaller gear): z_1 = {pinion} > z_2 = {wheel}"
        )
    return wheel / pinion


def _sum_of_base_radii(
    z_1: int, z_2: int, m_n_mm: float, alpha_n_rad: float, beta_rad: float
) -> float:
    """(d_b1 + d_b2) / 2 = |z_1 + z_2| m_n cos(alpha_t) / (2 cos beta): a_w cos(alpha_wt)."""
    d_b1 = iv.base_diameter(teeth(z_1, "number of teeth z_1"), m_n_mm, alpha_n_rad, beta_rad)
    d_b2 = iv.base_diameter(teeth(z_2, "number of teeth z_2"), m_n_mm, alpha_n_rad, beta_rad)
    return 0.5 * (d_b1 + d_b2)


@eq(SOURCE, "(54)", section="5.2.4", page=39)
def transverse_working_pressure_angle(
    z_1: int, z_2: int, m_n_mm: float, alpha_n_rad: float, beta_rad: float, a_w_mm: float
) -> float:
    """Working pressure angle from the centre distance:
    alpha_wt = arccos(|z_1 + z_2| m_n cos(alpha_t) / (2 a_w cos(beta))).

    A centre distance below the sum of the base radii has no involute mesh and raises
    ``GeometryInfeasibleError``; within ``EPS`` below it the angle is zero. So does a centre
    distance so large that the angle is 90 degrees in binary64.
    """
    a_w = positive_input(a_w_mm, "centre distance a_w")
    radii = _sum_of_base_radii(z_1, z_2, m_n_mm, alpha_n_rad, beta_rad)
    alpha_wt = safe_acos(finite_result(radii / a_w, "cos alpha_wt"), what="cos alpha_wt (Eq. (54))")
    if alpha_wt >= HALF_PI:
        raise GeometryInfeasibleError(
            f"centre distance a_w = {a_w!r} is too large for the sum of the base radii "
            f"{radii!r}: the working pressure angle reaches 90 deg"
        )
    return alpha_wt


@eq(SOURCE, "(54)", section="5.2.4", page=39, note="solved for a_w")
def centre_distance(
    z_1: int, z_2: int, m_n_mm: float, alpha_n_rad: float, beta_rad: float, alpha_wt_rad: float
) -> float:
    """Centre distance for a working pressure angle:
    a_w = |z_1 + z_2| m_n cos(alpha_t) / (2 cos(beta) cos(alpha_wt))."""
    radii = _sum_of_base_radii(z_1, z_2, m_n_mm, alpha_n_rad, beta_rad)
    cosine = math.cos(_working_angle(alpha_wt_rad))
    return finite_result(safe_div(radii, cosine, what="a_w (Eq. (54))"), "centre distance a_w")


@eq(SOURCE, "(55)", section="5.2.4", page=39)
def working_pressure_angle_without_backlash(
    z_1: int,
    z_2: int,
    alpha_n_rad: float,
    beta_rad: float,
    sum_of_profile_shift_coefficients: float,
) -> float:
    """Working pressure angle of a backlash-free pair from
    inv(alpha_wt) = inv(alpha_t) + 2 tan(alpha_n) (x_1 + x_2) / (z_1 + z_2).

    A sum of the profile shift coefficients so small that inv(alpha_wt) would be negative has no
    backlash-free mesh and raises ``GeometryInfeasibleError``.
    """
    total = teeth(z_1, "number of teeth z_1") + teeth(z_2, "number of teeth z_2")
    shift = finite_input(sum_of_profile_shift_coefficients, "sum of profile shift coefficients")
    alpha_n = pressure_angle(alpha_n_rad, "normal pressure angle alpha_n")
    alpha_t = iv.transverse_pressure_angle(alpha_n, beta_rad)
    value = finite_result(iv.inv(alpha_t) + 2.0 * math.tan(alpha_n) * shift / total, "inv alpha_wt")
    if value < 0.0:
        raise GeometryInfeasibleError(
            f"inv(alpha_wt) = {value!r} < 0: the sum of the profile shift coefficients "
            f"{shift!r} is too small for a backlash-free mesh"
        )
    return iv.inv_inverse(value)


@eq(SOURCE, "(62)", section="5.3", page=41)
def sum_of_profile_shift_coefficients(
    z_1: int, z_2: int, alpha_n_rad: float, beta_rad: float, alpha_wt_rad: float
) -> float:
    """Sum of the profile shift coefficients of a backlash-free pair:
    x_1 + x_2 = (z_1 + z_2) (inv(alpha_wt) - inv(alpha_t)) / (2 tan(alpha_n))."""
    total = teeth(z_1, "number of teeth z_1") + teeth(z_2, "number of teeth z_2")
    alpha_n = pressure_angle(alpha_n_rad, "normal pressure angle alpha_n")
    alpha_t = iv.transverse_pressure_angle(alpha_n, beta_rad)
    difference = iv.inv(_working_angle(alpha_wt_rad)) - iv.inv(alpha_t)
    return finite_result(
        safe_div(total * difference, 2.0 * math.tan(alpha_n), what="sum of x (Eq. (62))"),
        "sum of x",
    )


@eq(SOURCE, "(56)", section="5.2.5", page=39, note="corrected in Anhang NB, p. 6")
@eq(SOURCE, "(57)", section="5.2.5", page=39, note="corrected in Anhang NB, p. 6")
def working_pitch_diameter(d_b_mm: float, alpha_wt_rad: float) -> float:
    """Working pitch diameter: d_w = d_b / cos(alpha_wt) (last form of Eq. (56) and (57))."""
    d_b = positive_input(d_b_mm, "base diameter d_b")
    cosine = math.cos(_working_angle(alpha_wt_rad))
    return finite_result(safe_div(d_b, cosine, what="d_w"), "working pitch diameter d_w")


@eq(SOURCE, "(59)", section="5.2.6", page=41)
def common_tooth_depth(d_a1_mm: float, d_a2_mm: float, a_w_mm: float) -> float:
    """Common tooth depth of the pair: h_w = (d_a1 + d_a2) / 2 - a_w (external pair).

    Eq. (59) writes the tip diameters. ``compute_pair_geometry`` calls this function with the
    tip form diameters (ADR-112). Signed: a value <= 0 means that the circles do not overlap.
    """
    d_a1 = positive_input(d_a1_mm, "tip diameter d_a1")
    d_a2 = positive_input(d_a2_mm, "tip diameter d_a2")
    return finite_result(0.5 * (d_a1 + d_a2) - positive_input(a_w_mm, "centre distance a_w"), "h_w")


@eq(SOURCE, "(60)", section="5.2.7", page=41)
def tip_clearance(a_w_mm: float, d_a_mm: float, d_fE_mm: float) -> float:
    """Tip clearance of a gear: c = a_w - d_a / 2 - d_fE / 2 with the generated root diameter of
    the mating gear (both formulas of Eq. (60), external pair).

    Signed: a negative value means that the tip cuts into the root of the mating gear.
    """
    a_w = positive_input(a_w_mm, "centre distance a_w")
    d_a = positive_input(d_a_mm, "tip diameter d_a")
    d_fE = positive_input(d_fE_mm, "generated root diameter d_fE of the mating gear")
    return finite_result(a_w - 0.5 * d_a - 0.5 * d_fE, "tip clearance c")


# --- §5.4 mesh ----------------------------------------------------------------------------------


@eq(SOURCE, "(87)", section="5.4.5.3", page=46)
def length_between_tangent_points(a_w_mm: float, alpha_wt_rad: float) -> float:
    """Distance of the tangent points T_1 and T_2 on the line of action: a_w sin(alpha_wt)."""
    a_w = positive_input(a_w_mm, "centre distance a_w")
    return finite_result(a_w * math.sin(_working_angle(alpha_wt_rad)), "T_1 T_2")


@eq(SOURCE, "(83)", section="5.4.5.3", page=46)
@eq(SOURCE, "(84)", section="5.4.5.3", page=46)
def radius_of_curvature_at_active_tip(d_Na_mm: float, d_b_mm: float) -> float:
    """Radius of curvature of a flank at its active tip circle: rho = sqrt(d_Na^2 - d_b^2) / 2.

    Eq. (84) for the pinion (rho_E1), Eq. (83) for the wheel (rho_A2); Eq. (17) at d_Na.
    """
    return iv.radius_of_curvature(d_Na_mm, d_b_mm)


def _rest_to_tangent_point(
    a_w_mm: float, alpha_wt_rad: float, d_other_mm: float, d_b_other_mm: float
) -> tuple[float, bool]:
    """(rest, beyond): ``rest`` = 2 a_w sin(alpha_wt) - sqrt(d_other^2 - d_b_other^2) is twice the
    distance on the line of action between the tangent point of a gear and the point that the
    circle ``d_other`` of the other gear cuts. ``beyond`` says that this circle reaches past the
    tangent point by more than rounding noise (``EPS`` relative to the distance of the tangent
    points)."""
    span = 2.0 * length_between_tangent_points(a_w_mm, alpha_wt_rad)
    rest = span - _roll_length(d_other_mm, d_b_other_mm)
    return rest, rest < -EPS * span


def _diameter_at_mating_point(
    a_w_mm: float, alpha_wt_rad: float, d_other_mm: float, d_b_other_mm: float, d_b_mm: float
) -> float:
    """Diameter of a gear at the point of the line of action that the circle ``d_other`` of the
    other gear cuts: sqrt((2 a_w sin(alpha_wt) - sqrt(d_other^2 - d_b_other^2))^2 + d_b^2).

    Raises ``GeometryInfeasibleError`` if that circle reaches beyond the tangent point of the
    gear (interference: there is no involute to mate with).
    """
    d_b = positive_input(d_b_mm, "base diameter d_b")
    rest, beyond = _rest_to_tangent_point(a_w_mm, alpha_wt_rad, d_other_mm, d_b_other_mm)
    if beyond:
        raise GeometryInfeasibleError(
            f"the circle d = {d_other_mm!r} reaches {-0.5 * rest!r} mm beyond the tangent point "
            "of the line of action on the base circle of the other gear: no involute to mate "
            "with (interference)"
        )
    return finite_result(math.hypot(rest, d_b), "diameter at the mating point")


@eq(SOURCE, "(64)", section="5.4.1", page=43)
@eq(SOURCE, "(65)", section="5.4.1", page=43)
def sap_diameter(
    a_w_mm: float, alpha_wt_rad: float, d_Fa2_mm: float, d_b2_mm: float, d_b1_mm: float
) -> float:
    """Start of the active profile limited by the tip form circle of the mating gear:
    d_Nf1 = sqrt((2 a_w sin(alpha_wt) - sqrt(d_Fa2^2 - d_b2^2))^2 + d_b1^2).

    Written for gear 1 (Eq. (64)); Eq. (65) is the same with the indices swapped.
    """
    return _diameter_at_mating_point(a_w_mm, alpha_wt_rad, d_Fa2_mm, d_b2_mm, d_b1_mm)


@eq(SOURCE, "(66)", section="5.4.1", page=43)
@eq(SOURCE, "(67)", section="5.4.1", page=43)
def root_form_circle_limits_active_profile(
    a_w_mm: float,
    alpha_wt_rad: float,
    d_Fa2_mm: float,
    d_b2_mm: float,
    d_b1_mm: float,
    d_Ff1_mm: float,
) -> bool:
    """True if the root form diameter d_Ff1 is larger than the start of the active profile of
    Eq. (64); then d_Nf1 = d_Ff1 (Eq. (66)). Eq. (67) is the same with the indices swapped.

    "Larger" means by more than rounding noise (``EPS``, relative): a root form diameter that
    equals the value of Eq. (64) limits nothing. Also true if the tip form circle of the mating
    gear reaches beyond the tangent point, where Eq. (64) has no value: the involute of the gear
    ends at its root form circle.
    """
    d_Ff1 = positive_input(d_Ff1_mm, "root form diameter d_Ff")
    _, beyond = _rest_to_tangent_point(a_w_mm, alpha_wt_rad, d_Fa2_mm, d_b2_mm)
    if beyond:
        return True
    start = sap_diameter(a_w_mm, alpha_wt_rad, d_Fa2_mm, d_b2_mm, d_b1_mm)
    return d_Ff1 > start * (1.0 + EPS)


@eq(SOURCE, "(68)", section="5.4.1", page=43)
@eq(SOURCE, "(69)", section="5.4.1", page=43)
def active_tip_diameter(
    a_w_mm: float, alpha_wt_rad: float, d_Ff1_mm: float, d_b1_mm: float, d_b2_mm: float
) -> float:
    """Active tip diameter of a gear whose mate is limited by its own root form circle:
    d_Na2 = sqrt((2 a_w sin(alpha_wt) - sqrt(d_Ff1^2 - d_b1^2))^2 + d_b2^2).

    Written for gear 2 (Eq. (68)); Eq. (69) is the same with the indices swapped.
    """
    return _diameter_at_mating_point(a_w_mm, alpha_wt_rad, d_Ff1_mm, d_b1_mm, d_b2_mm)


@eq(SOURCE, "(76)", section="5.4.4", page=45)
def form_over_dimension(d_Nf_mm: float, d_Ff_mm: float) -> float:
    """Form over-dimension: c_F = (d_Nf - d_Ff) / 2 (external gear).

    Signed. For a start of the active profile determined by Eq. (64) to (67) it is not negative
    beyond rounding noise (the root form circle limits only beyond ``EPS``, so c_F can be
    negative by up to ``EPS`` d_Nf / 2).
    """
    d_Nf = positive_input(d_Nf_mm, "start of active profile diameter d_Nf")
    d_Ff = positive_input(d_Ff_mm, "root form diameter d_Ff")
    return 0.5 * (d_Nf - d_Ff)


@eq(SOURCE, "(79)", section="5.4.5.2", page=46)
@eq(SOURCE, "(80)", section="5.4.5.2", page=46)
def length_of_addendum_path_of_contact(d_Na_mm: float, d_b_mm: float, alpha_wt_rad: float) -> float:
    """Length of the path of contact between the pitch point and the active tip circle of a gear:
    g_a = (sqrt(d_Na^2 - d_b^2) - d_b tan(alpha_wt)) / 2.

    Eq. (80) for the pinion (g_a1 = g_f2), Eq. (79) for the wheel (g_a2 = g_f1). Signed: negative
    if the active tip circle lies inside the working pitch circle.
    """
    d_b = positive_input(d_b_mm, "base diameter d_b")
    roll = _roll_length(d_Na_mm, d_b)
    return finite_result(0.5 * (roll - d_b * math.tan(_working_angle(alpha_wt_rad))), "g_a")


@eq(SOURCE, "(77)", section="5.4.5.2", page=45)
def length_of_path_of_contact(
    d_Na1_mm: float,
    d_b1_mm: float,
    d_Na2_mm: float,
    d_b2_mm: float,
    a_w_mm: float,
    alpha_wt_rad: float,
) -> float:
    """Length of the path of contact:
    g_alpha = (sqrt(d_Na1^2 - d_b1^2) + sqrt(d_Na2^2 - d_b2^2) - 2 a_w sin(alpha_wt)) / 2.

    Signed: a value <= 0 means that the active tip circles do not reach each other.
    """
    reach = _roll_length(d_Na1_mm, d_b1_mm) + _roll_length(d_Na2_mm, d_b2_mm)
    return finite_result(
        0.5 * reach - length_between_tangent_points(a_w_mm, alpha_wt_rad), "g_alpha"
    )


@eq(SOURCE, "(90)", section="5.4.7.1", page=47)
def transverse_contact_ratio(g_alpha_mm: float, p_et_mm: float) -> float:
    """Transverse contact ratio: epsilon_alpha = g_alpha / p_et."""
    g_alpha = finite_input(g_alpha_mm, "length of path of contact g_alpha")
    return finite_result(g_alpha / positive_input(p_et_mm, "p_et"), "epsilon_alpha")


@eq(SOURCE, "(93)", section="5.4.7.3", page=48)
def overlap_ratio(b_w_mm: float, beta_rad: float, m_n_mm: float) -> float:
    """Overlap ratio: epsilon_beta = b_w sin|beta| / (pi m_n).

    Eq. (93) writes b; the overlap angle of Eq. (91) is defined with the contact face width b_w,
    which is used here. Zero for spur gears.
    """
    b_w = positive_input(b_w_mm, "contact face width b_w")
    return finite_result(
        b_w * math.sin(abs(helix(beta_rad))) / normal_pitch(m_n_mm), "epsilon_beta"
    )


@eq(SOURCE, "(97)", section="5.4.7.5", page=49)
def total_contact_ratio(epsilon_alpha: float, epsilon_beta: float) -> float:
    """Total contact ratio: epsilon_gamma = epsilon_alpha + epsilon_beta."""
    return finite_input(epsilon_alpha, "epsilon_alpha") + finite_input(epsilon_beta, "epsilon_beta")


# --- §5.6 sliding -------------------------------------------------------------------------------


@eq(SOURCE, "(112)", section="5.6.2", page=54)
@eq(SOURCE, "(113)", section="5.6.2", page=54)
def sliding_factor_at_tip(g_a_mm: float, d_w1_mm: float, u: float) -> float:
    """Sliding factor at the end of the path of contact on the tip of a gear:
    K_g = 2 g_a / d_w1 (1 + 1 / u), with g_a of that gear.

    Eq. (113) with g_a1 (the norm's K_ga, end point E for a driving pinion); Eq. (112) with
    g_a2 = g_f1 (the norm's K_gf, end point A). Signed like g_a: negative if the active tip
    circle lies inside the working pitch circle.
    """
    g_a = finite_input(g_a_mm, "length of addendum path of contact g_a")
    d_w1 = positive_input(d_w1_mm, "working pitch diameter d_w1")
    return finite_result(2.0 * g_a / d_w1 * (1.0 + 1.0 / _gear_ratio(u)), "sliding factor K_g")


def _radii_of_curvature(rho_y1_mm: float, rho_y2_mm: float) -> tuple[float, float]:
    rho_1 = finite_input(rho_y1_mm, "radius of curvature rho_y1")
    rho_2 = finite_input(rho_y2_mm, "radius of curvature rho_y2")
    if rho_1 < 0.0 or rho_2 < 0.0:
        raise InputRangeError(
            f"radii of curvature of an external pair are >= 0, got {rho_y1_mm!r}, {rho_y2_mm!r}"
        )
    return rho_1, rho_2


def _at_base_circle(rho: float, other: float) -> bool:
    """A radius of curvature that is zero within rounding noise, relative to T_1 T_2."""
    return rho <= EPS * (rho + other)


@eq(SOURCE, "(114)", section="5.6.3", page=54)
@eq(SOURCE, "(116)", section="5.6.3", page=54, note="Eq. (114) at the end point A")
def specific_sliding_of_pinion(rho_y1_mm: float, rho_y2_mm: float, u: float) -> float:
    """Specific sliding on the pinion flank at a point Y: zeta_1 = 1 - rho_y2 / (u rho_y1).

    Eq. (116) is this equation at the end point A (root of the pinion). Unbounded at the base
    circle of the pinion (rho_y1 = 0), which raises ``GeometryInfeasibleError``.
    """
    rho_1, rho_2 = _radii_of_curvature(rho_y1_mm, rho_y2_mm)
    if _at_base_circle(rho_1, rho_2):
        raise GeometryInfeasibleError(
            "specific sliding zeta_1 is unbounded at the base circle of the pinion (rho_y1 = 0)"
        )
    return finite_result(1.0 - rho_2 / (_gear_ratio(u) * rho_1), "zeta_1")


@eq(SOURCE, "(115)", section="5.6.3", page=54)
@eq(SOURCE, "(117)", section="5.6.3", page=54, note="Eq. (115) at the end point E")
def specific_sliding_of_wheel(rho_y1_mm: float, rho_y2_mm: float, u: float) -> float:
    """Specific sliding on the wheel flank at a point Y: zeta_2 = 1 - u rho_y1 / rho_y2.

    Eq. (117) is this equation at the end point E (root of the wheel). Unbounded at the base
    circle of the wheel (rho_y2 = 0), which raises ``GeometryInfeasibleError``.
    """
    rho_1, rho_2 = _radii_of_curvature(rho_y1_mm, rho_y2_mm)
    if _at_base_circle(rho_2, rho_1):
        raise GeometryInfeasibleError(
            "specific sliding zeta_2 is unbounded at the base circle of the wheel (rho_y2 = 0)"
        )
    return finite_result(1.0 - _gear_ratio(u) * rho_1 / rho_2, "zeta_2")


# --- orchestrators ------------------------------------------------------------------------------

ROLES = ("pinion", "wheel")


def _checked(pair: PairInput) -> PairInput:
    """The pair as the contract validates it.

    A pair can bypass the validation (``model_copy``, ``model_construct``). The contract is
    therefore applied again, in strict mode, and the validated pair is what the computation reads
    and what the result carries as ``inputs``: types, finite numbers, the verified ranges and the
    rule of ADR-107 hold for every call. A violation is an ``InputRangeError``.
    """
    if not isinstance(pair, PairInput):
        raise InputRangeError(f"a PairInput is required, got {type(pair).__name__}")
    try:
        valid = PairInput.model_validate(pair.model_dump(warnings=False), strict=True)
    except ValidationError as error:
        raise InputRangeError(f"the pair is no valid input: {error}") from error
    for role, gear in zip(ROLES, valid.gears.as_tuple(), strict=True):
        if gear.kind is not GearKind.EXTERNAL:
            raise NotSupportedError(
                f"{role}: internal gears (GearKind.INTERNAL) are a prepared extension point"
            )
    return valid


def _pair_of_numbers(value: Pair[float] | None, what: str) -> tuple[float, float] | None:
    if value is None:
        return None
    if not isinstance(value, Pair):
        raise InputRangeError(f"{what} must be a Pair (pinion, wheel), got {type(value).__name__}")
    return (
        positive_input(value.pinion, f"{what} of the pinion"),
        positive_input(value.wheel, f"{what} of the wheel"),
    )


def _derived_shift(x: float, role: str) -> float:
    """A profile shift coefficient that follows from the centre distance, within the range the
    contract admits for a given one (rounding noise within ``EPS`` beyond a limit is the limit)."""
    low, high = PROFILE_SHIFT_RANGE
    if low <= x <= high:
        return x
    if low - EPS <= x <= high + EPS:
        return low if x < low else high
    raise GeometryInfeasibleError(
        f"{role}: the profile shift coefficient that follows from the centre distance, "
        f"x = {x!r}, lies outside the verified range {PROFILE_SHIFT_RANGE}"
    )


def _resolve(pair: PairInput) -> tuple[float, float, float, float]:
    """``resolve_profile_shift`` for a pair that the contract has validated."""
    pinion, wheel = pair.gears.pinion, pair.gears.wheel
    z_1, z_2 = pinion.number_of_teeth, wheel.number_of_teeth
    m_n = pair.normal_module_mm
    alpha_n = math.radians(pair.normal_pressure_angle_deg)
    beta = math.radians(pair.helix_angle_deg)
    x_1, x_2 = pinion.profile_shift_coefficient, wheel.profile_shift_coefficient
    # what the contract leaves open: a gear without x carries a span measurement, or a_w and the
    # x of the mating gear are given
    from_span = NotSupportedError(
        "the nominal profile shift coefficient is not given and does not follow from the centre "
        "distance and the mating gear; a span measurement is not evaluated yet (DIN 21773, "
        "increments 4 and 5; open in ADR-107)"
    )
    a_w = pair.centre_distance_mm
    if a_w is None:
        if x_1 is None or x_2 is None:
            raise from_span
        alpha_wt = working_pressure_angle_without_backlash(z_1, z_2, alpha_n, beta, x_1 + x_2)
        return x_1, x_2, centre_distance(z_1, z_2, m_n, alpha_n, beta, alpha_wt), alpha_wt
    alpha_wt = transverse_working_pressure_angle(z_1, z_2, m_n, alpha_n, beta, a_w)
    total = sum_of_profile_shift_coefficients(z_1, z_2, alpha_n, beta, alpha_wt)
    if x_1 is not None:
        return x_1, _derived_shift(total - x_1, "wheel"), a_w, alpha_wt
    if x_2 is not None:
        return _derived_shift(total - x_2, "pinion"), x_2, a_w, alpha_wt
    raise from_span


def resolve_profile_shift(pair: PairInput) -> tuple[float, float, float, float]:
    """(x_1, x_2, a_w in mm, alpha_wt in rad) of a pair by the rule of ADR-107.

    Exactly two of a_w, x_1 and x_2 are given. With a_w given, the other coefficient follows from
    Eq. (54) and (62); with both coefficients given, a_w follows from Eq. (55) and (54). A span
    measurement is not evaluated yet (open in ADR-107): a gear that carries only a span gets its
    coefficient from the centre distance and the mating gear; where that is not possible, the
    pair is not supported (``NotSupportedError``).
    """
    return _resolve(_checked(pair))


def with_nominal_tip_diameters(
    pair: PairInput, *, h_aP_mm: float, k: Pair[float] | None = None
) -> PairInput:
    """The pair with the nominal tip diameters of Eq. (33) where none is given.

    An explicit choice of the caller: ``h_aP_mm`` is the addendum of the basic rack, ``k`` the
    tip alteration coefficients (default 0 for both gears). Given tip diameters are kept.
    """
    h_aP = positive_input(h_aP_mm, "addendum of the basic rack h_aP")
    if k is not None and not isinstance(k, Pair):
        raise InputRangeError(f"k must be a Pair (pinion, wheel), got {type(k).__name__}")
    alteration = (
        (0.0, 0.0)
        if k is None
        else (
            finite_input(k.pinion, "tip alteration coefficient k of the pinion"),
            finite_input(k.wheel, "tip alteration coefficient k of the wheel"),
        )
    )
    pair = _checked(pair)
    x_1, x_2, _, _ = _resolve(pair)
    beta = math.radians(pair.helix_angle_deg)
    gears = []
    for gear, shift, coefficient in zip(pair.gears.as_tuple(), (x_1, x_2), alteration, strict=True):
        if gear.tip_diameter_mm is not None:
            gears.append(gear)
            continue
        d = iv.reference_diameter(gear.number_of_teeth, pair.normal_module_mm, beta)
        d_a = tip_diameter(d, shift, pair.normal_module_mm, h_aP, coefficient)
        gears.append(gear.model_copy(update={"tip_diameter_mm": d_a}))
    return pair.model_copy(update={"gears": Pair(pinion=gears[0], wheel=gears[1])})


def _warning(code: str, field: str, message: str) -> InputWarning:
    return InputWarning(code=code, field=field, message=message)


def _tip_form_diameters(
    pair: PairInput, given: tuple[float, float] | None, warnings: list[InputWarning]
) -> tuple[float, float, float, float]:
    """(d_a1, d_a2, d_Fa1, d_Fa2). Tip form diameters: from the generation where given, else
    Eq. (127) with the chamfer of the input. A value within ``EPS`` above the tip diameter is
    the tip diameter."""
    tips: list[float] = []
    forms: list[float] = []
    for index, (role, gear) in enumerate(zip(ROLES, pair.gears.as_tuple(), strict=True)):
        d_a = gear.tip_diameter_mm
        if d_a is None:
            raise InputRangeError(
                f"{role}: the mesh needs the tip diameter; give tip_diameter_mm or apply "
                "with_nominal_tip_diameters (Eq. (33)) explicitly"
            )
        tips.append(d_a)
        if given is None:
            forms.append(tip_form_diameter(d_a, gear.tip_chamfer_radial_mm))
            tool = gear.tool
            # (an angle without the height at which the flank starts cannot be judged here;
            # the generation rejects such a tool)
            if has_edge_break_flank(tool) or (
                tool.edge_break_angle_deg is not None and tool.root_form_height_factor is None
            ):
                warnings.append(
                    _warning(
                        "tip_form_diameter_not_generated",
                        "tip_form_diameter_mm",
                        f"{role}: the tool has an edge break flank; the tip form diameter it "
                        "generates follows from the generation (increment 3). Computed with "
                        "d_Fa = d_a - 2 h_K (Eq. (127)) instead",
                    )
                )
            continue
        d_Fa = given[index]
        if d_Fa > d_a:
            if d_Fa / d_a > 1.0 + EPS:
                raise InputRangeError(
                    f"{role}: tip form diameter {d_Fa!r} exceeds the tip diameter {d_a!r}"
                )
            d_Fa = d_a
        if gear.tip_chamfer_radial_mm > 0.0:
            warnings.append(
                _warning(
                    "tip_chamfer_input_not_used",
                    "tip_chamfer_radial_mm",
                    f"{role}: the given tip form diameter is used; the radial amount of the tip "
                    f"chamfer of the input ({gear.tip_chamfer_radial_mm!r} mm) is not",
                )
            )
        forms.append(d_Fa)
    return tips[0], tips[1], forms[0], forms[1]


def _root_form_diameter(d_Ff: float, d_b: float, d_Fa: float, role: str) -> float:
    """The root form diameter the mesh is computed with: below the tip form circle of the gear,
    on or above its base circle (within ``EPS`` below the base circle it is the base circle)."""
    if d_Ff >= d_Fa:
        raise GeometryInfeasibleError(
            f"{role}: root form diameter d_Ff = {d_Ff!r} does not lie below the tip form "
            f"diameter d_Fa = {d_Fa!r}: the gear has no involute"
        )
    if d_Ff >= d_b:
        return d_Ff
    if d_b / d_Ff > 1.0 + EPS:
        raise GeometryInfeasibleError(
            f"{role}: root form diameter d_Ff = {d_Ff!r} lies below the base circle d_b = {d_b!r}"
        )
    return d_b


def _limited(role: str) -> InputWarning:
    return _warning(
        "active_profile_limited_by_root_form_circle",
        "root_form_diameter_mm",
        f"{role}: the active profile starts at the root form circle (Eq. (66), (67)); the tip "
        "of the mating gear is used up to its active tip diameter only (Eq. (68), (69))",
    )


def compute_pair_geometry(
    pair: PairInput,
    *,
    root_form_diameter_mm: Pair[float] | None = None,
    tip_form_diameter_mm: Pair[float] | None = None,
) -> PairGeometry:
    """Mating quantities of an external gear pair (DIN ISO 21771:2014-08 §5).

    ``root_form_diameter_mm`` are the root form diameters d_Ff of the generated gears. Without
    them the start of the active profile is computed from the tip form circle of the mating gear
    alone (Eq. (64), (65)) and the result carries the warning ``root_form_diameter_not_checked``.
    The result echoes the values the mesh was computed with.

    ``tip_form_diameter_mm`` are the tip form diameters d_Fa of the generated gears. Without them
    d_Fa = d_a - 2 h_K (Eq. (127)) with the radial amount of the tip chamfer of the input; a tool
    that breaks the tip edge itself then yields the warning ``tip_form_diameter_not_generated``.

    A mesh whose active profile starts on the base circle of a gear, d_Nf <= d_b (1 + ``EPS``),
    raises ``GeometryInfeasibleError``: the specific sliding is unbounded there. So does a mesh
    without an active profile, d_Nf >= d_Na (1 - ``EPS``) on a gear.
    """
    pair = _checked(pair)
    x_1, x_2, a_w, alpha_wt = _resolve(pair)
    root_forms = _pair_of_numbers(root_form_diameter_mm, "root form diameter d_Ff")
    tip_forms = _pair_of_numbers(tip_form_diameter_mm, "tip form diameter d_Fa")
    pinion, wheel = pair.gears.pinion, pair.gears.wheel
    warnings: list[InputWarning] = []
    d_a1, d_a2, d_Fa1, d_Fa2 = _tip_form_diameters(pair, tip_forms, warnings)
    for role, gear in zip(ROLES, pair.gears.as_tuple(), strict=True):
        if gear.span is not None:
            warnings.append(
                _warning(
                    "span_measurement_not_used",
                    "span",
                    f"{role}: the span measurement is not evaluated yet (DIN 21773, increment "
                    "4); the pair geometry is computed from the centre distance and the "
                    "profile shift coefficients",
                )
            )
    m_n = pair.normal_module_mm
    alpha_n = math.radians(pair.normal_pressure_angle_deg)
    beta = math.radians(pair.helix_angle_deg)
    z_1, z_2 = pinion.number_of_teeth, wheel.number_of_teeth
    u = gear_ratio(z_1, z_2)
    basic: Pair[BasicGearGeometry] = Pair(
        pinion=iv.compute_basic_gear_geometry(
            number_of_teeth=z_1,
            normal_module_mm=m_n,
            normal_pressure_angle_deg=pair.normal_pressure_angle_deg,
            helix_angle_deg=pair.helix_angle_deg,
            profile_shift_coefficient=x_1,
        ),
        wheel=iv.compute_basic_gear_geometry(
            number_of_teeth=z_2,
            normal_module_mm=m_n,
            normal_pressure_angle_deg=pair.normal_pressure_angle_deg,
            helix_angle_deg=-pair.helix_angle_deg,
            profile_shift_coefficient=x_2,
        ),
    )
    d_b1, d_b2 = basic.pinion.base_diameter_mm, basic.wheel.base_diameter_mm
    for role, d_Fa, d_b in (("pinion", d_Fa1, d_b1), ("wheel", d_Fa2, d_b2)):
        if d_Fa <= d_b:
            raise GeometryInfeasibleError(
                f"{role}: the tip form diameter {d_Fa!r} does not lie above the base circle {d_b!r}"
            )

    # start of the active profile (Eq. (64) to (67)) and active tip diameters (Eq. (68), (69))
    d_Na1, d_Na2 = d_Fa1, d_Fa2
    pinion_limited = wheel_limited = False
    used_root_forms: Pair[float] | None = None
    if root_forms is None:
        warnings.append(
            _warning(
                "root_form_diameter_not_checked",
                "root_form_diameter_mm",
                "no root form diameters given: the start of the active profile follows from "
                "the tip form circle of the mating gear alone (Eq. (64), (65)); the limit by "
                "the root form circle (Eq. (66) to (69)) is not applied",
            )
        )
    else:
        d_Ff1 = _root_form_diameter(root_forms[0], d_b1, d_Fa1, "pinion")
        d_Ff2 = _root_form_diameter(root_forms[1], d_b2, d_Fa2, "wheel")
        used_root_forms = Pair(pinion=d_Ff1, wheel=d_Ff2)
        pinion_limited = root_form_circle_limits_active_profile(
            a_w, alpha_wt, d_Fa2, d_b2, d_b1, d_Ff1
        )
        wheel_limited = root_form_circle_limits_active_profile(
            a_w, alpha_wt, d_Fa1, d_b1, d_b2, d_Ff2
        )
    if pinion_limited:
        d_Nf1 = d_Ff1  # Eq. (66); the wheel tip is used up to d_Na2 only, Eq. (68)
        d_Na2 = active_tip_diameter(a_w, alpha_wt, d_Ff1, d_b1, d_b2)
        warnings.append(_limited("pinion"))
    else:
        d_Nf1 = sap_diameter(a_w, alpha_wt, d_Fa2, d_b2, d_b1)
    if wheel_limited:
        d_Nf2 = d_Ff2  # Eq. (67); the pinion tip is used up to d_Na1 only, Eq. (69)
        d_Na1 = active_tip_diameter(a_w, alpha_wt, d_Ff2, d_b2, d_b1)
        warnings.append(_limited("wheel"))
    else:
        d_Nf2 = sap_diameter(a_w, alpha_wt, d_Fa1, d_b1, d_b2)
    for role, d_Nf, d_b in (("pinion", d_Nf1, d_b1), ("wheel", d_Nf2, d_b2)):
        if d_Nf <= d_b * (1.0 + EPS):
            raise GeometryInfeasibleError(
                f"{role}: the active profile starts on the base circle (d_Nf = {d_Nf!r}, "
                f"d_b = {d_b!r}); the specific sliding is unbounded there. Shorten the tip of "
                "the mating gear or give a root form diameter above the base circle"
            )
    for role, d_Nf, d_Na in (("pinion", d_Nf1, d_Na1), ("wheel", d_Nf2, d_Na2)):
        if d_Nf >= d_Na * (1.0 - EPS):
            raise GeometryInfeasibleError(
                f"{role}: the active profile has no length (d_Nf = {d_Nf!r}, d_Na = {d_Na!r}): "
                "the teeth do not mesh"
            )

    tangent_length = length_between_tangent_points(a_w, alpha_wt)
    p_bt = transverse_base_pitch(m_n, alpha_n, beta)
    p_et = transverse_contact_pitch(p_bt)
    # positive: the start of the active profile of each gear lies below its active tip circle
    g_alpha = length_of_path_of_contact(d_Na1, d_b1, d_Na2, d_b2, a_w, alpha_wt)
    g_a1 = length_of_addendum_path_of_contact(d_Na1, d_b1, alpha_wt)
    g_a2 = length_of_addendum_path_of_contact(d_Na2, d_b2, alpha_wt)
    epsilon_alpha = transverse_contact_ratio(g_alpha, p_et)
    b_w = min(pinion.face_width_mm, wheel.face_width_mm)
    epsilon_beta = overlap_ratio(b_w, beta, m_n)
    if epsilon_alpha < 1.0:
        warnings.append(
            _warning(
                "transverse_contact_ratio_below_one",
                "tip_diameter_mm",
                f"transverse contact ratio {epsilon_alpha:.4f} < 1",
            )
        )
    d_w1 = working_pitch_diameter(d_b1, alpha_wt)

    # common tooth depth: Eq. (59) with the tip form circles (user decision, ADR-112)
    h_w = common_tooth_depth(d_Fa1, d_Fa2, a_w)
    if d_Fa1 < d_a1 or d_Fa2 < d_a2:
        by_tip_circles = common_tooth_depth(d_a1, d_a2, a_w)
        warnings.append(
            _warning(
                "common_tooth_depth_with_tip_form_circles",
                "common_tooth_depth_mm",
                "the common tooth depth is evaluated with the tip form circles (ADR-112); with "
                f"the tip circles, by the letter of Eq. (59), it is {by_tip_circles!r} mm",
            )
        )

    # Radii of curvature at the ends of the path of contact. The two radii of an end point add up
    # to T_1 T_2 (Eq. (87)); the one that is evaluated directly is the one whose circle is given:
    # the root form circle where it limits (Eq. (17) at d_Nf), else the active tip circle of the
    # mating gear (Eq. (83), (84)). The small radius at the root then carries no round trip
    # through a diameter.
    if pinion_limited:
        rho_A1 = iv.radius_of_curvature(d_Nf1, d_b1)
        rho_A2 = tangent_length - rho_A1
    else:
        rho_A2 = radius_of_curvature_at_active_tip(d_Na2, d_b2)
        rho_A1 = tangent_length - rho_A2
    if wheel_limited:
        rho_E2 = iv.radius_of_curvature(d_Nf2, d_b2)
        rho_E1 = tangent_length - rho_E2
    else:
        rho_E1 = radius_of_curvature_at_active_tip(d_Na1, d_b1)
        rho_E2 = tangent_length - rho_E1

    return PairGeometry(
        inputs=pair,
        gears=basic,
        gear_ratio=u,
        centre_distance_mm=a_w,
        transverse_working_pressure_angle_deg=math.degrees(alpha_wt),
        profile_shift_coefficient=Pair(pinion=x_1, wheel=x_2),
        sum_of_profile_shift_coefficients=x_1 + x_2,
        working_pitch_diameter_mm=Pair(pinion=d_w1, wheel=working_pitch_diameter(d_b2, alpha_wt)),
        tip_diameter_mm=Pair(pinion=d_a1, wheel=d_a2),
        tip_form_diameter_mm=Pair(pinion=d_Fa1, wheel=d_Fa2),
        active_tip_diameter_mm=Pair(pinion=d_Na1, wheel=d_Na2),
        sap_diameter_mm=Pair(pinion=d_Nf1, wheel=d_Nf2),
        root_form_diameter_mm=used_root_forms,
        common_tooth_depth_mm=h_w,
        normal_pitch_mm=normal_pitch(m_n),
        transverse_pitch_mm=transverse_pitch(m_n, beta),
        transverse_base_pitch_mm=p_bt,
        transverse_contact_pitch_mm=p_et,
        contact_face_width_mm=b_w,
        length_of_path_of_contact_mm=g_alpha,
        length_of_addendum_path_of_contact_mm=Pair(pinion=g_a1, wheel=g_a2),
        transverse_contact_ratio=epsilon_alpha,
        overlap_ratio=epsilon_beta,
        total_contact_ratio=total_contact_ratio(epsilon_alpha, epsilon_beta),
        sliding_factor_at_tip=Pair(
            pinion=sliding_factor_at_tip(g_a1, d_w1, u),
            wheel=sliding_factor_at_tip(g_a2, d_w1, u),
        ),
        specific_sliding_at_end_points=Pair(
            pinion=specific_sliding_of_pinion(rho_A1, rho_A2, u),
            wheel=specific_sliding_of_wheel(rho_E1, rho_E2, u),
        ),
        warnings=tuple(warnings),
    )
