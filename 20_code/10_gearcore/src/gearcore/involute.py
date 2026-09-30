"""Involute fundamentals of a single cylindrical gear.

Source: DIN ISO 21771:2014-08 (ISO 21771:2007), §4.2 reference quantities, §4.3 involute helicoid,
§4.7 tooth thickness and space width. Every function realises one equation of the norm; angles
are radians (``_rad``), lengths millimetres (``_mm``). Formulas are written for external gears
(``z/|z| = +1``); internal gears (``z < 0``) are a prepared extension point and raise
``NotSupportedError``.

The norm defines the involute function (18) but no inverse; ``inv_inverse`` inverts (18)
numerically with a bracketed Newton iteration — the only inverse-involute implementation of the
package (project rule 6).

Signed quantities. Tooth thickness, space width and their half angles at the reference cylinder
(Eq. (39), (41), (44), (46), (49), (51)) and the space half angles (45), (47) are returned with
their sign: a value <= 0 says that there is no tooth (no space) on that cylinder, which happens
in feasible gears whose toothed zone does not contain the cylinder (eta_b < 0 when the two
involutes that bound a tooth space meet above the base circle, for x = 0, alpha_n = 20°, beta = 0
from z = 106 on). Eq. (40) is different: a tooth thickness half angle at
d_y below zero means d_y lies beyond the pointed tooth, where no tooth exists, and is an error.
"""

import math

from gearcore._guards import HALF_PI
from gearcore._guards import helix as _helix
from gearcore._guards import pressure_angle as _pressure_angle
from gearcore._guards import teeth as _teeth
from gearcore._safe import (
    EPS,
    finite_input,
    finite_result,
    positive_input,
    safe_acos,
    safe_asin,
    safe_div,
    safe_tan,
)
from gearcore.errors import (
    GeometryInfeasibleError,
    InputRangeError,
    SolverError,
)
from gearcore.models.common import (
    HELIX_ANGLE_RANGE_DEG,
    NORMAL_MODULE_RANGE_MM,
    PRESSURE_ANGLE_RANGE_DEG,
    PROFILE_SHIFT_RANGE,
    TEETH_RANGE,
    InputWarning,
)
from gearcore.models.results import BasicGearGeometry
from gearcore.trace import eq

SOURCE = "ISO21771:2014"
INV_ALPHA_MAX_RAD = math.radians(89.0)
"""Largest angle ``inv_inverse`` returns; inv grows without bound towards 90°."""
INV_MAX = math.tan(INV_ALPHA_MAX_RAD) - INV_ALPHA_MAX_RAD

EQ_EXEMPT = ("compute_basic_gear_geometry",)
"""Orchestrators assemble results from traced functions and carry no equation of their own."""


# --- input guards ---------------------------------------------------------------------------


def _shift(x: float) -> float:
    return finite_input(x, "profile shift coefficient x")


def _in_range(value: float, limits: tuple[float, float], what: str) -> float:
    number = finite_input(value, what)
    if not limits[0] <= number <= limits[1]:
        raise InputRangeError(
            f"{what} must lie in [{limits[0]!r}, {limits[1]!r}] (verified range), got {value!r}"
        )
    return number


# --- §4.2 reference quantities ------------------------------------------------------------------


@eq(SOURCE, "(2)", section="4.2.7", page=24)
def transverse_module(m_n_mm: float, beta_rad: float) -> float:
    """Transverse module: m_t = m_n / cos(beta)."""
    m_n = positive_input(m_n_mm, "normal module m_n")
    quotient = safe_div(m_n, math.cos(_helix(beta_rad)), what="m_t = m_n / cos beta")
    return finite_result(quotient, "transverse module m_t")


@eq(SOURCE, "(1)", section="4.2.4", page=23)
def reference_diameter(z: int, m_n_mm: float, beta_rad: float) -> float:
    """Reference diameter: d = |z| m_t = |z| m_n / cos(beta)."""
    teeth = float(_teeth(z))
    return finite_result(teeth * transverse_module(m_n_mm, beta_rad), "reference diameter d")


# --- §4.3 involute helicoid ---------------------------------------------------------------------


@eq(SOURCE, "(14)", section="4.3.6", page=30)
def transverse_pressure_angle(alpha_n_rad: float, beta_rad: float) -> float:
    """Transverse pressure angle from tan(alpha_n) = tan(alpha_t) cos(beta)."""
    alpha_n = _pressure_angle(alpha_n_rad, "normal pressure angle alpha_n")
    ratio = safe_div(math.tan(alpha_n), math.cos(_helix(beta_rad)), what="tan alpha_n / cos beta")
    return math.atan(ratio)


@eq(SOURCE, "(6)", section="4.3.3", page=28)
def base_helix_angle(beta_rad: float, alpha_n_rad: float) -> float:
    """Base helix angle from sin(beta_b) = sin(beta) cos(alpha_n); keeps the sign of beta."""
    alpha_n = _pressure_angle(alpha_n_rad, "normal pressure angle alpha_n")
    return safe_asin(math.sin(_helix(beta_rad)) * math.cos(alpha_n), what="sin beta_b")


@eq(SOURCE, "(8)", section="4.3.3", page=28)
def helix_angle_at(d_y_mm: float, d_mm: float, beta_rad: float) -> float:
    """Helix angle on the cylinder d_y: tan(beta_y) = tan(beta) d_y / d."""
    d_y = positive_input(d_y_mm, "diameter d_y")
    d = positive_input(d_mm, "reference diameter d")
    tangent = finite_result(math.tan(_helix(beta_rad)) * d_y / d, "tan beta_y")
    return math.atan(tangent)


def _on_base_circle(d_y: float, d_b: float, what: str) -> bool:
    """True if d_y equals d_b within the rounding tolerance; raises if d_y lies below d_b.

    One criterion for Eq. (12) and Eq. (17): d_b / d_y <= 1 + EPS counts as "on the base circle".
    """
    if d_y > d_b:
        return False
    if d_b / d_y > 1.0 + EPS:
        raise GeometryInfeasibleError(
            f"{what}: d_y = {d_y!r} lies below the base circle d_b = {d_b!r}"
        )
    return True


@eq(SOURCE, "(12)", section="4.3.5", page=29)
def transverse_profile_angle_at(d_y_mm: float, d_b_mm: float) -> float:
    """Transverse profile angle at d_y: cos(alpha_yt) = d_b / d_y (requires d_y >= d_b)."""
    d_y = positive_input(d_y_mm, "diameter d_y")
    d_b = positive_input(d_b_mm, "base diameter d_b")
    if _on_base_circle(d_y, d_b, "alpha_yt"):
        return 0.0
    return safe_acos(finite_result(d_b / d_y, "d_b / d_y"), what="cos alpha_yt = d_b / d_y")


@eq(SOURCE, "(15)", section="4.3.6", page=30)
def normal_profile_angle_at(alpha_yt_rad: float, beta_y_rad: float) -> float:
    """Normal profile angle at d_y: tan(alpha_yn) = tan(alpha_yt) cos(beta_y)."""
    alpha_yt = _pressure_angle(alpha_yt_rad, "transverse profile angle alpha_yt")
    return math.atan(math.tan(alpha_yt) * math.cos(_helix(beta_y_rad)))


@eq(SOURCE, "(16)", section="4.3.7", page=30)
def roll_angle(alpha_yt_rad: float) -> float:
    """Roll angle of the involute: xi_y = tan(alpha_yt)."""
    return safe_tan(_pressure_angle(alpha_yt_rad, "transverse profile angle alpha_yt"), what="xi_y")


@eq(SOURCE, "(17)", section="4.3.8", page=30)
def radius_of_curvature(d_y_mm: float, d_b_mm: float) -> float:
    """Radius of curvature = length of roll at d_y: rho_y = sqrt(d_y^2 - d_b^2) / 2 (external).

    Evaluated as sqrt((d_y - d_b) (d_y + d_b)) / 2, which does not cancel near the base circle.
    """
    d_y = positive_input(d_y_mm, "diameter d_y")
    d_b = positive_input(d_b_mm, "base diameter d_b")
    if _on_base_circle(d_y, d_b, "rho_y"):
        return 0.0
    return finite_result(0.5 * math.sqrt((d_y - d_b) * (d_y + d_b)), "rho_y")


@eq(SOURCE, "(18)", section="4.3.9", page=31)
def inv(alpha_rad: float) -> float:
    """Involute function: inv(alpha) = tan(alpha) - alpha.

    Conditioning: the difference cancels for tiny angles (relative error about 1e-6 at 1e-5 rad);
    the absolute error stays below one ulp of tan(alpha).
    """
    alpha = _pressure_angle(alpha_rad, "angle alpha")
    return safe_tan(alpha, what="inv alpha") - alpha


@eq(SOURCE, "(18)", section="4.3.9", page=31, note="numerical inverse; the norm gives no inverse")
def inv_inverse(value: float) -> float:
    """Angle alpha in [0, 89 deg] with inv(alpha) = value (bracketed Newton, bisection fallback).

    Conditioning: inv(a) = tan(a) - a cancels for tiny angles, so a value carries an absolute
    error of about 1e-16 * a and the inverse one of about 1e-16 / a (1e-10 rad at a = 1e-6 rad).
    Pressure angles of gears are far above that range; the absolute accuracy of inv is unaffected.

    Termination: the residual is known to about one ulp of tan(alpha) only, so the iteration stops
    when the residual reaches that level or when the Newton step falls below the spacing of alpha.
    The error bound is 8 ulp(tan a) / tan(a)^2 + 1e-15 rad; within that bound the result is not
    strictly monotonic in ``value`` (rounding noise of the residual).

    The start value cbrt(3 value) lies above the root and inv is convex, so Newton converges from
    above; the bracket and the bisection step are a safety net that no tested input reaches.
    """
    target = finite_input(value, "inv value")
    if target < 0.0:
        raise SolverError(f"inverse involute: value must be >= 0, got {value!r}")
    if target > INV_MAX:
        raise SolverError(
            f"inverse involute: value {value!r} exceeds inv(89 deg) = {INV_MAX!r} (outside the supported range)"
        )
    if target == 0.0:
        return 0.0
    low, high = 0.0, INV_ALPHA_MAX_RAD
    alpha = min(high, math.cbrt(3.0 * target))  # inv(a) ~ a^3 / 3 for small a
    for _ in range(200):
        tangent = math.tan(alpha)
        residual = tangent - alpha - target
        if abs(residual) <= 4.0 * math.ulp(tangent):
            return alpha  # residual at the rounding level of tan: no iterate is closer to the root
        if residual > 0.0:
            high = alpha
        else:
            low = alpha
        slope = tangent * tangent
        candidate = alpha - residual / slope if slope > 0.0 else 0.5 * (low + high)
        if not low <= candidate <= high:
            candidate = 0.5 * (low + high)
        if abs(candidate - alpha) <= 4.0e-16 * max(1.0, alpha) or high - low <= 4.0e-16:
            return candidate
        alpha = candidate
    raise SolverError(f"inverse involute did not converge for value {value!r}")


@eq(SOURCE, "(19)", section="4.3.10", page=31)
def base_diameter(z: int, m_n_mm: float, alpha_n_rad: float, beta_rad: float) -> float:
    """Base diameter: d_b = d cos(alpha_t)."""
    alpha_t = transverse_pressure_angle(alpha_n_rad, beta_rad)
    return reference_diameter(z, m_n_mm, beta_rad) * math.cos(alpha_t)


# --- §4.7 tooth thickness and space width -------------------------------------------------------


@eq(SOURCE, "(41)", section="4.7.2", page=35)
def tooth_thickness_half_angle(z: int, x: float, alpha_n_rad: float) -> float:
    """Tooth thickness half angle at the reference circle: psi = (pi + 4 x tan alpha_n) / (2 |z|).

    Signed (see module docstring).
    """
    alpha_n = _pressure_angle(alpha_n_rad, "normal pressure angle alpha_n")
    numerator = finite_result(math.pi + 4.0 * _shift(x) * math.tan(alpha_n), "psi")
    return numerator / (2.0 * _teeth(z))


@eq(SOURCE, "(40)", section="4.7.2", page=35)
def tooth_thickness_half_angle_at(psi_rad: float, alpha_t_rad: float, alpha_yt_rad: float) -> float:
    """Half angle at d_y: psi_y = psi + inv(alpha_t) - inv(alpha_yt) (external gear).

    A negative result means d_y lies beyond the intersection of the two flanks (pointed tooth) and
    raises ``GeometryInfeasibleError``; rounding noise within EPS of the pointed tooth is zero.
    """
    psi_y = finite_input(psi_rad, "psi") + inv(alpha_t_rad) - inv(alpha_yt_rad)
    if psi_y >= 0.0:
        return psi_y
    if psi_y < -EPS:
        raise GeometryInfeasibleError(
            f"tooth thickness half angle psi_y = {psi_y!r} < 0: the flanks intersect below this diameter"
        )
    return 0.0


@eq(SOURCE, "(42)", section="4.7.2", page=35)
def base_tooth_thickness_half_angle(psi_rad: float, alpha_t_rad: float) -> float:
    """Half angle at the base circle: psi_b = psi + inv(alpha_t) (external gear)."""
    return finite_input(psi_rad, "psi") + inv(alpha_t_rad)


@eq(SOURCE, "(39)", section="4.7.1", page=35)
def transverse_tooth_thickness(
    m_n_mm: float, x: float, alpha_n_rad: float, beta_rad: float
) -> float:
    """Transverse tooth thickness at the reference circle: s_t = m_t (pi/2 + 2 x tan alpha_n).

    Signed (see module docstring).
    """
    alpha_n = _pressure_angle(alpha_n_rad, "normal pressure angle alpha_n")
    factor = HALF_PI + 2.0 * _shift(x) * math.tan(alpha_n)
    return finite_result(transverse_module(m_n_mm, beta_rad) * factor, "s_t")


@eq(SOURCE, "(38)", section="4.7.1", page=35)
def transverse_tooth_thickness_at(d_y_mm: float, psi_y_rad: float) -> float:
    """Transverse tooth thickness (arc) at d_y: s_yt = d_y psi_y (psi_y >= 0 from Eq. (40))."""
    psi_y = finite_input(psi_y_rad, "psi_y")
    if psi_y < 0.0:
        raise InputRangeError(
            f"psi_y must be >= 0 (Eq. (40) raises beyond the pointed tooth), got {psi_y_rad!r}"
        )
    return finite_result(positive_input(d_y_mm, "diameter d_y") * psi_y, "s_yt")


@eq(SOURCE, "(46)", section="4.7.4", page=36)
def space_width_half_angle(z: int, x: float, alpha_n_rad: float) -> float:
    """Space width half angle at the reference circle: eta = (pi - 4 x tan alpha_n) / (2 |z|).

    Signed (see module docstring).
    """
    alpha_n = _pressure_angle(alpha_n_rad, "normal pressure angle alpha_n")
    numerator = finite_result(math.pi - 4.0 * _shift(x) * math.tan(alpha_n), "eta")
    return numerator / (2.0 * _teeth(z))


@eq(SOURCE, "(45)", section="4.7.4", page=36)
def space_width_half_angle_at(eta_rad: float, alpha_t_rad: float, alpha_yt_rad: float) -> float:
    """Space half angle at d_y: eta_y = eta - (inv(alpha_t) - inv(alpha_yt)) (external gear).

    Signed: negative below the intersection of the flanks of neighbouring teeth.
    """
    return finite_input(eta_rad, "eta") - (inv(alpha_t_rad) - inv(alpha_yt_rad))


@eq(SOURCE, "(47)", section="4.7.4", page=36)
def base_space_width_half_angle(eta_rad: float, alpha_t_rad: float) -> float:
    """Space half angle at the base circle: eta_b = eta - inv(alpha_t) (external gear); signed."""
    return finite_input(eta_rad, "eta") - inv(alpha_t_rad)


@eq(SOURCE, "(44)", section="4.7.3", page=36)
def transverse_space_width(m_n_mm: float, x: float, alpha_n_rad: float, beta_rad: float) -> float:
    """Transverse space width at the reference circle: e_t = m_t (pi/2 - 2 x tan alpha_n).

    Signed (see module docstring).
    """
    alpha_n = _pressure_angle(alpha_n_rad, "normal pressure angle alpha_n")
    factor = HALF_PI - 2.0 * _shift(x) * math.tan(alpha_n)
    return finite_result(transverse_module(m_n_mm, beta_rad) * factor, "e_t")


@eq(SOURCE, "(43)", section="4.7.3", page=35)
def transverse_space_width_at(d_y_mm: float, eta_y_rad: float) -> float:
    """Transverse space width (arc) at d_y: e_yt = d_y eta_y (signed like eta_y)."""
    eta_y = finite_input(eta_y_rad, "eta_y")
    return finite_result(positive_input(d_y_mm, "diameter d_y") * eta_y, "e_yt")


@eq(SOURCE, "(49)", section="4.7.5", page=37)
def normal_tooth_thickness(m_n_mm: float, x: float, alpha_n_rad: float) -> float:
    """Normal tooth thickness at the reference cylinder: s_n = m_n (pi/2 + 2 x tan alpha_n).

    Signed (see module docstring).
    """
    alpha_n = _pressure_angle(alpha_n_rad, "normal pressure angle alpha_n")
    factor = HALF_PI + 2.0 * _shift(x) * math.tan(alpha_n)
    return finite_result(positive_input(m_n_mm, "normal module m_n") * factor, "s_n")


@eq(SOURCE, "(48)", section="4.7.5", page=37)
def normal_tooth_thickness_at(s_yt_mm: float, beta_y_rad: float) -> float:
    """Normal tooth thickness on the cylinder d_y: s_yn = s_yt cos(beta_y)."""
    return finite_input(s_yt_mm, "s_yt") * math.cos(_helix(beta_y_rad))


@eq(SOURCE, "(51)", section="4.7.6", page=37)
def normal_space_width(m_n_mm: float, x: float, alpha_n_rad: float) -> float:
    """Normal space width at the reference cylinder: e_n = m_n (pi/2 - 2 x tan alpha_n).

    Signed (see module docstring).
    """
    alpha_n = _pressure_angle(alpha_n_rad, "normal pressure angle alpha_n")
    factor = HALF_PI - 2.0 * _shift(x) * math.tan(alpha_n)
    return finite_result(positive_input(m_n_mm, "normal module m_n") * factor, "e_n")


@eq(SOURCE, "(50)", section="4.7.6", page=37)
def normal_space_width_at(e_yt_mm: float, beta_y_rad: float) -> float:
    """Normal space width on the cylinder d_y: e_yn = e_yt cos(beta_y)."""
    return finite_input(e_yt_mm, "e_yt") * math.cos(_helix(beta_y_rad))


# --- orchestrator -------------------------------------------------------------------------------


def _reference_cylinder_warnings(psi_rad: float, eta_rad: float) -> tuple[InputWarning, ...]:
    warnings: list[InputWarning] = []
    if psi_rad <= 0.0:
        warnings.append(
            InputWarning(
                code="no_tooth_at_reference_cylinder",
                field="profile_shift_coefficient",
                message=(
                    "the nominal tooth thickness at the reference cylinder is not positive "
                    "(x <= -pi / (4 tan alpha_n)): the reference cylinder lies above the teeth"
                ),
            )
        )
    if eta_rad <= 0.0:
        warnings.append(
            InputWarning(
                code="no_space_at_reference_cylinder",
                field="profile_shift_coefficient",
                message=(
                    "the nominal space width at the reference cylinder is not positive "
                    "(x >= pi / (4 tan alpha_n)): the reference cylinder lies below the root"
                ),
            )
        )
    return tuple(warnings)


def compute_basic_gear_geometry(
    *,
    number_of_teeth: int,
    normal_module_mm: float,
    normal_pressure_angle_deg: float,
    helix_angle_deg: float,
    profile_shift_coefficient: float,
) -> BasicGearGeometry:
    """Reference and base quantities plus nominal tooth thickness of one external gear.

    Inputs are limited to the verified ranges of the input contracts (``models.common``); the
    single-equation functions accept every mathematically valid input.
    """
    z = _teeth(number_of_teeth)
    if not TEETH_RANGE[0] <= z <= TEETH_RANGE[1]:
        raise InputRangeError(
            f"number of teeth z must lie in [{TEETH_RANGE[0]}, {TEETH_RANGE[1]}] (verified range), "
            f"got {number_of_teeth!r}"
        )
    m_n = _in_range(normal_module_mm, NORMAL_MODULE_RANGE_MM, "normal module m_n in mm")
    alpha_n_deg = _in_range(
        normal_pressure_angle_deg, PRESSURE_ANGLE_RANGE_DEG, "normal pressure angle alpha_n in deg"
    )
    beta_deg = _in_range(helix_angle_deg, HELIX_ANGLE_RANGE_DEG, "helix angle beta in deg")
    beta_deg += 0.0  # a negative zero becomes zero, so that spur gears compare equal
    x = _in_range(profile_shift_coefficient, PROFILE_SHIFT_RANGE, "profile shift coefficient x")

    alpha_n = math.radians(alpha_n_deg)
    beta = math.radians(beta_deg)
    alpha_t = transverse_pressure_angle(alpha_n, beta)
    psi = tooth_thickness_half_angle(z, x, alpha_n)
    eta = space_width_half_angle(z, x, alpha_n)
    return BasicGearGeometry(
        number_of_teeth=z,
        normal_module_mm=m_n,
        normal_pressure_angle_deg=alpha_n_deg,
        helix_angle_deg=beta_deg,
        profile_shift_coefficient=x,
        transverse_module_mm=transverse_module(m_n, beta),
        transverse_pressure_angle_deg=math.degrees(alpha_t),
        base_helix_angle_deg=math.degrees(base_helix_angle(beta, alpha_n)),
        reference_diameter_mm=reference_diameter(z, m_n, beta),
        base_diameter_mm=base_diameter(z, m_n, alpha_n, beta),
        transverse_tooth_thickness_mm=transverse_tooth_thickness(m_n, x, alpha_n, beta),
        normal_tooth_thickness_mm=normal_tooth_thickness(m_n, x, alpha_n),
        transverse_space_width_mm=transverse_space_width(m_n, x, alpha_n, beta),
        normal_space_width_mm=normal_space_width(m_n, x, alpha_n),
        tooth_thickness_half_angle_deg=math.degrees(psi),
        space_width_half_angle_deg=math.degrees(eta),
        base_tooth_thickness_half_angle_deg=math.degrees(
            base_tooth_thickness_half_angle(psi, alpha_t)
        ),
        base_space_width_half_angle_deg=math.degrees(base_space_width_half_angle(eta, alpha_t)),
        warnings=_reference_cylinder_warnings(psi, eta),
    )
