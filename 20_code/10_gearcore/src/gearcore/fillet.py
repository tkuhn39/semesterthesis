"""Alternative root fillets of a generated spur gear: the inclined ellipse of Frühe, the bionic
contour (tangent function and circle) of the Voith patent DE 10 2008 045 318 B3 and the cubic
Bézier contour of the Voith patent DE 10 2013 004 861 B3.

A variant replaces the trochoid of the tool tip rounding between a transition diameter on the
flank and the centre line of the gap; the involute above the transition stays the generated one,
the tip is untouched. Every curve is tangent-continuous at the transition and crosses the centre
line of the gap at a right angle, so the mirrored half continues it smoothly; the root circle of
the variant is the circle through that crossing.

Transition diameters as the sources define them: the ellipse starts at the root form circle
d_Ff of the generated gear (Frühe 2012, Abbildung 41: the fillet between the root form point
P_Ff and the root point P_f); the bionic and the Bézier contour start at the "relevant diameter"
d_r, the arithmetic mean of the start of the active profile d_N and the clearance circle d_FR to
which the mating tip dips (DE 10 2008 045 318 B3, Anspruch 12 and [0022]), unless given.

The frame of a gap: origin at the gear axis, y along the centre line of the gap outwards, x
towards the tooth whose left fillet is built (the patents' frame, DE 10 2008 045 318 B3 [0018]);
the tooth frame of ``contour.ToothContour`` has the tooth centre on +y and the left gap at the
angle -pi/z.

The clearance of a variant against the tip corner of the mating gear is checked kinematically
(``mating_tip_clearance``): the corners of the mating teeth are carried through the gap by the
rolling motion of ``fe.placement`` and their smallest radial distance to the fillet is reported.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import Literal

import numpy as np
from numpy.typing import NDArray
from pydantic import Field
from scipy.optimize import brentq

from gearcore import contour as ct
from gearcore import involute as iv
from gearcore._safe import integer_input
from gearcore.errors import GeometryInfeasibleError, InputRangeError, NotSupportedError
from gearcore.fe import placement as pl
from gearcore.models.common import FrozenModel
from gearcore.models.results import GenerationResult
from gearcore.quantities import Q
from gearcore.trace import eq

Array = NDArray[np.float64]

FRUEHE = "Fruehe2012"
BIONIC = "DE102008045318B3:2009"
BEZIER = "DE102013004861B3:2014"
ROTH = "RothOpferkuch2017"

FilletKind = Literal["ellipse", "bezier", "bionic"]
FILLET_KINDS: tuple[FilletKind, ...] = ("ellipse", "bezier", "bionic")

EQ_EXEMPT = (
    "ellipse_fillet",
    "bezier_fillet",
    "bionic_fillet",
    "apply",
    "transition_diameter",
    "clearance_circle_diameter",
    "gap_frame_to_tooth_frame",
    "mating_tip_clearance",
    "polyline_min_curvature_radius",
)
"""Assembly, frames and checks: no equation of a source."""

CLEARANCE_SAMPLES = 400
"""Positions of the rolling motion per trace of a mating tip corner."""

CENTRE_LINE_TOLERANCE_RAD = 1.0e-7
ARC_TOLERANCE = 1.0e-12


class FilletVariant(FrozenModel):
    """One alternative root fillet and its parameters.

    ``ellipse``: ``inclination_deg`` is gamma, the inclination of the major axis against the
    radial direction (towards the tooth), ``axis_ratio`` is a/b (Frühe 2012, section 5.4.1; his
    optimum over 19 gearings gamma = 30 deg, a/b = 3,0, section 5.4.2). ``bezier``:
    ``control_factor`` is f of Anspruch 8 of DE 10 2013 004 861 B3, k = (0,25 + 0,1 f) l
    (preferred 0,5 to 1,5, Anspruch 9). ``bionic``: ``root_angle_deg`` is phi, the slope angle
    of the tangent function on the centre line of the gap (None: 45 deg - 180 deg / z - alpha_r
    of Anspruch 5), ``root_radius_factor`` times the chord of the space width at d_r is the
    radius r of the circle (0,1 to 0,6, example 0,3; Anspruch 9 and [0050]).
    ``transition_diameter_mm`` overrides the transition diameter of the kind.
    """

    kind: FilletKind
    inclination_deg: float = Q("fillet_ellipse_inclination", default=30.0, gt=0.0, lt=90.0)
    axis_ratio: float = Q("fillet_ellipse_axis_ratio", default=3.0, gt=0.0)
    control_factor: float = Q("bezier_control_factor", default=1.0, ge=0.0, le=3.0)
    root_angle_deg: float | None = Q("bionic_root_angle", default=None, gt=0.0, lt=90.0)
    root_radius_factor: float = Field(default=0.3, gt=0.0, le=1.0)
    transition_diameter_mm: float | None = Field(default=None, gt=0.0)

    def label(self) -> str:
        """A file-name part naming the variant and its parameters."""
        if self.kind == "ellipse":
            return f"ellipse_g{self.inclination_deg:g}_ab{self.axis_ratio:g}"
        if self.kind == "bezier":
            return f"bezier_f{self.control_factor:g}"
        angle = "auto" if self.root_angle_deg is None else f"{self.root_angle_deg:g}"
        return f"bionic_phi{angle}_r{self.root_radius_factor:g}"


class FilletResult(FrozenModel):
    """What ``apply`` built: the contour with the variant and the numbers of the variant."""

    variant: FilletVariant
    contour: ct.ToothContour
    transition_diameter_mm: float = Field(gt=0.0)
    root_diameter_mm: float = Field(gt=0.0)
    """Diameter of the circle through the root point on the centre line of the gap."""
    min_curvature_radius_mm: float = Field(ge=0.0)
    """Smallest radius of curvature along the variant fillet (from the sampled polyline)."""
    details: dict[str, float]
    """Numbers of the construction (ellipse axes, Bézier control distance, bionic circle ...)."""


# ---------------------------------------------------------------------------------------------
# ellipse after Frühe (2012), section 5.4.1


@eq(FRUEHE, "(89)", section="5.4.1", page=95)
def ellipse_x_star(d_Ff_mm: float, z: int, s_Ff_half_rad: float, gamma_rad: float) -> float:
    """Length x* of the line from the root form point P_Ff, inclined by gamma, to the centre
    line of the gap: x* = sin(pi/z - s_Ff/2) (d_Ff/2) / sin(pi/z + gamma)."""
    tau = math.pi / z
    return math.sin(tau - s_Ff_half_rad) * 0.5 * d_Ff_mm / math.sin(tau + gamma_rad)


@eq(FRUEHE, "(95)", section="5.4.1", page=97)
def ellipse_slope_at_root_form(
    gamma_rad: float, alpha_Ff_rad: float, s_Ff_half_rad: float
) -> float:
    """Slope of the flank tangent at the root form point in the frame of the ellipse,
    m_Ff = -tan(gamma - alpha_Ff + s_Ff/2)."""
    return -math.tan(gamma_rad - alpha_Ff_rad + s_Ff_half_rad)


@eq(FRUEHE, "(96)", section="5.4.1", page=97)
def ellipse_slope_at_root(gamma_rad: float, z: int) -> float:
    """Slope of the tangent at the root point (perpendicular to the centre line of the gap) in
    the frame of the ellipse, m_f = tan(pi/2 - pi/z - gamma) > 0."""
    m_f = math.tan(0.5 * math.pi - math.pi / z - gamma_rad)
    if m_f <= 0.0:
        raise GeometryInfeasibleError(
            f"gamma {math.degrees(gamma_rad):g} deg must stay below 90 deg - 180 deg / z = "
            f"{90.0 - 180.0 / z:g} deg (Frühe 2012, Eq. (96): m_f > 0)"
        )
    return m_f


@eq(FRUEHE, "(93)", section="5.4.1", page=97)
def ellipse_x_of_slope(m: float, a_mm: float, axis_ratio: float) -> float:
    """x of the point of the ellipse x^2/a^2 + y^2/b^2 = 1 (upper half) whose tangent has the
    slope m: x = -(m/|m|) a / sqrt((b/a)^2 / m^2 + 1), with a/b = ``axis_ratio``."""
    if m == 0.0:
        raise InputRangeError("a slope of zero names the apex of the ellipse, not a fillet point")
    b_over_a = 1.0 / axis_ratio
    return -(m / abs(m)) * a_mm / math.sqrt(b_over_a**2 / m**2 + 1.0)


@eq(FRUEHE, "(94)", section="5.4.1", page=97)
def ellipse_y_of_slope(m: float, a_mm: float, axis_ratio: float) -> float:
    """y of that point: y = a sqrt((b/a)^2 - 1 / (1/m^2 + (a/b)^2))."""
    if m == 0.0:
        raise InputRangeError("a slope of zero names the apex of the ellipse, not a fillet point")
    b_over_a = 1.0 / axis_ratio
    return a_mm * math.sqrt(b_over_a**2 - 1.0 / (1.0 / m**2 + axis_ratio**2))


@eq(
    FRUEHE,
    "(100)",
    section="5.4.1",
    page=98,
    note="(97), (98) and (89) put into (99), solved for a",
)
@eq(FRUEHE, "(99)", section="5.4.1", page=98)
@eq(FRUEHE, "(98)", section="5.4.1", page=97)
@eq(FRUEHE, "(97)", section="5.4.1", page=97)
def ellipse_major_axis(
    x_star_mm: float, m_Ff: float, m_f: float, axis_ratio: float, z: int, gamma_rad: float
) -> float:
    """The major axis a of the ellipse that is tangent-continuous at both ends.

    With the slopes m_Ff and m_f the points P_Ff and P_f lie at x and y proportional to a:
    delta x = x_Ff - x_f = a X, delta y = y_Ff - y_f = a Y by Eq. (97) and (98); the root point
    lies on the centre line of the gap, delta y = (x* - delta x) tan(pi/z + gamma) by Eq. (99),
    so a = x* tan(pi/z + gamma) / (Y + X tan(pi/z + gamma)) (Eq. (100)).
    """
    x_unit = ellipse_x_of_slope(m_Ff, 1.0, axis_ratio) - ellipse_x_of_slope(m_f, 1.0, axis_ratio)
    y_unit = ellipse_y_of_slope(m_Ff, 1.0, axis_ratio) - ellipse_y_of_slope(m_f, 1.0, axis_ratio)
    t = math.tan(math.pi / z + gamma_rad)
    denominator = y_unit + x_unit * t
    if denominator <= 0.0:
        raise GeometryInfeasibleError(
            f"no ellipse with gamma {math.degrees(gamma_rad):g} deg and a/b {axis_ratio:g} fits "
            "the root tangent-continuously (Frühe 2012, Eq. (100))"
        )
    a = x_star_mm * t / denominator
    if a <= 0.0 or x_unit * a >= x_star_mm:
        raise GeometryInfeasibleError(
            f"the ellipse with gamma {math.degrees(gamma_rad):g} deg and a/b {axis_ratio:g} "
            "does not reach the centre line of the gap"
        )
    return a


@eq(FRUEHE, "(91)", section="5.4.1", page=96)
@eq(FRUEHE, "(90)", section="5.4.1", page=96)
def ellipse_arc(a_mm: float, axis_ratio: float, x_from_mm: float, x_to_mm: float, n: int) -> Array:
    """``n`` points (x, y) of the upper half of the ellipse, y = sqrt(b^2 - (b/a)^2 x^2), from
    x_from to x_to, evenly spaced in the eccentric angle."""
    b = a_mm / axis_ratio
    ratios = (x_from_mm / a_mm, x_to_mm / a_mm)
    if any(abs(r) > 1.0 + ARC_TOLERANCE for r in ratios):
        raise GeometryInfeasibleError(
            f"the arc limits {x_from_mm:.6g} and {x_to_mm:.6g} mm lie outside the ellipse (a = {a_mm:.6g} mm)"
        )
    t_from, t_to = (math.acos(max(-1.0, min(1.0, r))) for r in ratios)  # rounding only
    t = np.linspace(t_from, t_to, n)
    return np.column_stack((a_mm * np.cos(t), b * np.sin(t)))


# ---------------------------------------------------------------------------------------------
# Bézier contour of DE 10 2013 004 861 B3 (Roth, Opferkuch 2017)


@eq(BEZIER, "Anspruch 8", page=10)
def bezier_control_distance(l_mm: float, f: float) -> float:
    """Distance k of a control point from its main point on the tangent, k = (0,25 + 0,1 f) l,
    with l the distance of the main point from the intersection of the two tangents."""
    if not 0.0 <= f <= 3.0:
        raise InputRangeError(f"the Bézier factor f must lie in 0 to 3, got {f!r}")
    return (0.25 + 0.1 * f) * l_mm


@eq(ROTH, "(1)", section="3.1", note="Bernstein form of the cubic Bézier curve")
def bezier_points(p0: Array, p1: Array, p2: Array, p3: Array, t: Array) -> Array:
    """Points of the cubic Bézier curve with the control points p0 .. p3 at the parameters t."""
    u = 1.0 - t
    return (
        np.outer(u**3, p0)
        + np.outer(3.0 * u**2 * t, p1)
        + np.outer(3.0 * u * t**2, p2)
        + np.outer(t**3, p3)
    )


# ---------------------------------------------------------------------------------------------
# bionic contour of DE 10 2008 045 318 B3


@eq(BIONIC, "Anspruch 5", page=9)
def bionic_root_angle(z: int, alpha_r_rad: float) -> float:
    """The slope angle phi of the tangent function on the centre line of the gap as the patent
    chooses it: phi = 45 deg - 180 deg / z - alpha_r (alpha_r the profile angle at d_r)."""
    phi = 0.25 * math.pi - math.pi / z - alpha_r_rad
    if phi <= 0.0:
        raise GeometryInfeasibleError(
            f"Anspruch 5 gives phi = {math.degrees(phi):.2f} deg for z = {z} and alpha_r = "
            f"{math.degrees(alpha_r_rad):.2f} deg: give root_angle_deg"
        )
    return phi


@eq(
    BIONIC,
    "(Gl. 12) to (Gl. 14)",
    page=5,
    note="a, b, c of (Gl. 1) y(x) = a tan(b x) + c from the conditions (1) to (3) of [0026], (Gl. 10)",
)
def bionic_tangent_function(
    x_P_mm: float, y_P_mm: float, m_P: float, phi_rad: float
) -> tuple[float, float, float]:
    """The coefficients (a, b, c) of y(x) = a tan(b x) + c through the flank point P = (x_P, y_P)
    with the flank slope m_P there and the slope tan(phi) on the centre line x = 0."""
    t = math.tan(phi_rad)
    if m_P <= t:
        raise GeometryInfeasibleError(
            f"the flank slope {m_P:.3f} at the transition is not steeper than tan(phi) = {t:.3f}: "
            "no tangent function joins them (choose a smaller root angle)"
        )
    # y'(x) = a b / cos^2(b x); y'(0) = a b = tan(phi); y'(x_P) = m_P
    b = math.acos(math.sqrt(t / m_P)) / x_P_mm
    a = t / b
    c = y_P_mm - a * math.tan(b * x_P_mm)
    return a, b, c


@eq(
    BIONIC,
    "(Gl. 18) to (Gl. 21)",
    page=6,
    note="tangent point x_ue and centre of the circle (Gl. 2) of radius r on the centre line",
)
def bionic_circle(a: float, b: float, c: float, r_mm: float, x_P_mm: float) -> tuple[float, float]:
    """The point x_ue where a circle of radius r centred on the centre line of the gap touches
    the tangent function, and the y of its centre: the normal of the curve at x_ue passes the
    centre line at the distance r."""

    def centre_x(x: float) -> float:
        slope = a * b / math.cos(b * x) ** 2
        return x - r_mm * slope / math.sqrt(1.0 + slope**2)

    lo, hi = 1.0e-9 * x_P_mm, x_P_mm * (1.0 - 1.0e-9)
    if centre_x(lo) > 0.0 or centre_x(hi) < 0.0:
        raise GeometryInfeasibleError(
            f"no circle of radius {r_mm:.4f} mm on the centre line touches the tangent function "
            "between the centre line and the transition (choose another root radius)"
        )
    x_ue = float(brentq(centre_x, lo, hi, xtol=1.0e-14))
    slope = a * b / math.cos(b * x_ue) ** 2
    y_ue = a * math.tan(b * x_ue) + c
    y_centre = y_ue + r_mm / math.sqrt(1.0 + slope**2)
    return x_ue, y_centre


# ---------------------------------------------------------------------------------------------
# frames and assembly


def gap_frame_to_tooth_frame(points: Array, z: int) -> Array:
    """Points of the left gap (origin the gear axis, y along the centre line of the gap, x
    towards the tooth) in the tooth frame (tooth centre on +y)."""
    tau = math.pi / z
    x, y = points[:, 0], points[:, 1]
    return np.column_stack(
        (x * math.cos(tau) - y * math.sin(tau), x * math.sin(tau) + y * math.cos(tau))
    )


def clearance_circle_diameter(generation: GenerationResult, role: ct.Role) -> float:
    """d_FR of the gear ``role``: the deepest diameter the tip of the mating gear reaches,
    2 (a_w - d_a,mate / 2) (DE 10 2008 045 318 B3 [0018])."""
    geometry = generation.pair_geometry
    mate = geometry.tip_diameter_mm.wheel if role == "pinion" else geometry.tip_diameter_mm.pinion
    return 2.0 * geometry.centre_distance_mm - mate


def _sap_diameter(generation: GenerationResult, role: ct.Role) -> float:
    sap = generation.pair_geometry.sap_diameter_mm
    return sap.pinion if role == "pinion" else sap.wheel


def transition_diameter(
    generation: GenerationResult, role: ct.Role, variant: FilletVariant
) -> float:
    """The diameter at which the variant leaves the involute: the root form circle for the
    ellipse, the mean of d_N and d_FR for the patents, or the given one."""
    _, gear, _ = ct._gear(generation, role)
    d_N = _sap_diameter(generation, role)
    if variant.transition_diameter_mm is not None:
        d = variant.transition_diameter_mm
    elif variant.kind == "ellipse":
        d = gear.root_form_diameter_mm
    else:
        d = 0.5 * (d_N + clearance_circle_diameter(generation, role))
    if not gear.root_form_diameter_mm - 1.0e-9 <= d <= d_N + 1.0e-9:
        raise GeometryInfeasibleError(
            f"the transition diameter {d:.4f} mm must lie between the root form circle "
            f"{gear.root_form_diameter_mm:.4f} mm and the start of the active profile {d_N:.4f} mm"
        )
    return d


def _flank_at(
    generation: GenerationResult, role: ct.Role, d_mm: float, count: int
) -> tuple[Array, Array, float, float]:
    """(radius, psi) of the involute from d_mm to the tip form circle, the profile angle at d_mm
    and the tooth thickness half angle there."""
    pair, gear, beta = ct._gear(generation, role)
    alpha_n = math.radians(pair.normal_pressure_angle_deg)
    alpha_t = iv.transverse_pressure_angle(alpha_n, beta)
    d_b = iv.base_diameter(gear.number_of_teeth, pair.normal_module_mm, alpha_n, beta)
    psi_b = iv.base_tooth_thickness_half_angle(
        iv.tooth_thickness_half_angle(
            gear.number_of_teeth, gear.generating_profile_shift_coefficient, alpha_n
        ),
        alpha_t,
    )
    radius, psi = ct.involute_flank(d_b, psi_b, d_mm, gear.tip_form_diameter_mm, count)
    alpha_y = iv.transverse_profile_angle_at(d_mm, d_b)
    return radius, psi, alpha_y, float(psi[0])


def ellipse_fillet(
    generation: GenerationResult, role: ct.Role, variant: FilletVariant, count: int
) -> tuple[Array, dict[str, float]]:
    """The left fillet (tooth frame, from the root point on the centre line of the gap to the
    root form point) as the ellipse of Frühe, and its numbers."""
    _, gear, _ = ct._gear(generation, role)
    z = gear.number_of_teeth
    d_Ff = transition_diameter(generation, role, variant)
    _, _, alpha_Ff, s_half = _flank_at(generation, role, d_Ff, 8)
    gamma = math.radians(variant.inclination_deg)
    x_star = ellipse_x_star(d_Ff, z, s_half, gamma)
    m_Ff = ellipse_slope_at_root_form(gamma, alpha_Ff, s_half)
    m_f = ellipse_slope_at_root(gamma, z)
    if m_Ff >= 0.0:
        raise GeometryInfeasibleError(
            f"gamma {variant.inclination_deg:g} deg is not larger than alpha_Ff - s_Ff/2 = "
            f"{math.degrees(alpha_Ff - s_half):.2f} deg: the ellipse cannot touch the flank"
        )
    ratio = variant.axis_ratio
    a = ellipse_major_axis(x_star, m_Ff, m_f, ratio, z, gamma)
    x_Ff, y_Ff = ellipse_x_of_slope(m_Ff, a, ratio), ellipse_y_of_slope(m_Ff, a, ratio)
    x_f, y_f = ellipse_x_of_slope(m_f, a, ratio), ellipse_y_of_slope(m_f, a, ratio)
    # frame of the ellipse in the tooth frame (left flank, gap at -x): e_x radial outwards
    # inclined by gamma towards the tooth centre, e_y towards the tooth
    e_x = np.array([math.sin(gamma), math.cos(gamma)])
    e_y = np.array([math.cos(gamma), -math.sin(gamma)])
    p_Ff = np.array([-0.5 * d_Ff * math.sin(s_half), 0.5 * d_Ff * math.cos(s_half)])
    centre = p_Ff - x_Ff * e_x - y_Ff * e_y
    arc = ellipse_arc(a, ratio, x_f, x_Ff, count)
    points = centre + np.outer(arc[:, 0], e_x) + np.outer(arc[:, 1], e_y)
    root = centre + x_f * e_x + y_f * e_y
    details = {
        "a_mm": a,
        "b_mm": a / ratio,
        "x_star_mm": x_star,
        "m_Ff": m_Ff,
        "m_f": m_f,
        "centre_x_mm": float(centre[0]),
        "centre_y_mm": float(centre[1]),
        "root_point_angle_deg": math.degrees(math.atan2(float(root[0]), float(root[1]))),
    }
    return points, details


def _gap_flank_point(
    generation: GenerationResult, role: ct.Role, d_r: float
) -> tuple[float, float, float, float, float]:
    """In the frame of the gap: x_P, y_P of the flank point at d_r on the tooth at +x, the
    direction angle (from +y) of the outward flank tangent, its slope dy/dx and the half space
    angle eta_r."""
    _, gear, _ = ct._gear(generation, role)
    z = gear.number_of_teeth
    _, _, alpha_r, s_half = _flank_at(generation, role, d_r, 8)
    eta_r = math.pi / z - s_half
    x_P, y_P = 0.5 * d_r * math.sin(eta_r), 0.5 * d_r * math.cos(eta_r)
    # the outward tangent of the involute is the radial direction turned by alpha_r towards the
    # tooth centre (+x here); its direction angle from +y is eta_r + alpha_r
    tangent_angle = eta_r + alpha_r
    slope = math.cos(tangent_angle) / math.sin(tangent_angle)
    return x_P, y_P, tangent_angle, slope, eta_r


def bezier_fillet(
    generation: GenerationResult, role: ct.Role, variant: FilletVariant, count: int
) -> tuple[Array, dict[str, float]]:
    """The left fillet as the Bézier contour of the patent: one cubic Bézier curve from the main
    point of the opposite flank to the main point of this flank; the half from the centre line
    of the gap (t = 1/2) to the main point (t = 1) is returned in the tooth frame."""
    _, gear, _ = ct._gear(generation, role)
    d_r = transition_diameter(generation, role, variant)
    x_P, y_P, tangent_angle, _, _ = _gap_flank_point(generation, role, d_r)
    inward = -np.array([math.sin(tangent_angle), math.cos(tangent_angle)])
    l_mm = x_P / math.sin(tangent_angle)  # main point to the intersection of the tangents
    k = bezier_control_distance(l_mm, variant.control_factor)
    p3 = np.array([x_P, y_P])
    p2 = p3 + k * inward
    p0 = p3 * np.array([-1.0, 1.0])
    p1 = p2 * np.array([-1.0, 1.0])
    t = np.linspace(0.5, 1.0, count)
    gap_points = bezier_points(p0, p1, p2, p3, t)
    s = p3 + l_mm * inward
    details = {
        "control_distance_k_mm": k,
        "tangent_length_l_mm": l_mm,
        "intersection_y_mm": float(s[1]),
        "root_point_y_mm": float(gap_points[0, 1]),
    }
    return gap_frame_to_tooth_frame(gap_points, gear.number_of_teeth), details


def bionic_fillet(
    generation: GenerationResult, role: ct.Role, variant: FilletVariant, count: int
) -> tuple[Array, dict[str, float]]:
    """The left fillet as the bionic contour of the patent: from the root point on the centre
    line along the circle to its tangent point with the tangent function, along that to the
    flank point at d_r; in the tooth frame."""
    _, gear, _ = ct._gear(generation, role)
    z = gear.number_of_teeth
    d_r = transition_diameter(generation, role, variant)
    x_P, y_P, _, slope, eta_r = _gap_flank_point(generation, role, d_r)
    _, _, alpha_r, _ = _flank_at(generation, role, d_r, 8)
    phi = (
        math.radians(variant.root_angle_deg)
        if variant.root_angle_deg is not None
        else bionic_root_angle(z, alpha_r)
    )
    chord = d_r * math.sin(eta_r)  # space width at d_r as a chord, S_L of the patent
    r = variant.root_radius_factor * chord
    a, b, c = bionic_tangent_function(x_P, y_P, slope, phi)
    x_ue, y_centre = bionic_circle(a, b, c, r, x_P)
    y_ue = a * math.tan(b * x_ue) + c
    # the circle from the root point (0, y_centre - r) to the tangent point: angle from the
    # -y direction of the centre towards +x, point = centre + r (sin theta, -cos theta)
    n_circle = max(divmod(count, 4)[0], 8)
    theta = np.linspace(0.0, math.atan2(x_ue, y_centre - y_ue), n_circle)
    circle = np.column_stack((r * np.sin(theta), y_centre - r * np.cos(theta)))
    x_t = np.linspace(x_ue, x_P, count - n_circle + 1)[1:]
    tangent = np.column_stack((x_t, a * np.tan(b * x_t) + c))
    gap_points = np.concatenate((circle, tangent))
    details = {
        "phi_deg": math.degrees(phi),
        "circle_radius_mm": r,
        "chord_S_L_mm": chord,
        "a": a,
        "b": b,
        "c": c,
        "tangent_point_x_mm": x_ue,
        "tangent_point_y_mm": y_ue,
        "circle_centre_y_mm": y_centre,
    }
    return gap_frame_to_tooth_frame(gap_points, z), details


def polyline_min_curvature_radius(points: Array) -> float:
    """The smallest radius of curvature of a polyline, from the circles through three
    consecutive points."""
    p0, p1, p2 = points[:-2], points[1:-1], points[2:]
    a = np.hypot(*(p1 - p0).T)
    b = np.hypot(*(p2 - p1).T)
    c = np.hypot(*(p2 - p0).T)
    cross = np.abs(
        (p1[:, 0] - p0[:, 0]) * (p2[:, 1] - p0[:, 1])
        - (p1[:, 1] - p0[:, 1]) * (p2[:, 0] - p0[:, 0])
    )
    with np.errstate(divide="ignore", invalid="ignore"):
        radius = a * b * c / (2.0 * cross)
    finite = radius[np.isfinite(radius)]
    return float(finite.min()) if len(finite) else math.inf


_BUILDERS: dict[
    str, Callable[[GenerationResult, ct.Role, FilletVariant, int], tuple[Array, dict[str, float]]]
] = {
    "ellipse": ellipse_fillet,
    "bezier": bezier_fillet,
    "bionic": bionic_fillet,
}


def apply(
    generation: GenerationResult,
    role: ct.Role,
    variant: FilletVariant,
    *,
    points: int = ct.DEFAULT_POINTS,
) -> FilletResult:
    """The tooth contour of the gear ``role`` with the trochoid replaced by the variant.

    The involute above the transition diameter, the tip flank and the tip circle are those of
    ``contour.tooth_contour``; the fillet of both sides is the variant, the right one mirrored.
    """
    if not isinstance(variant, FilletVariant):
        raise InputRangeError(f"a FilletVariant is required, got {type(variant).__name__}")
    count = integer_input(points, "points per segment")
    if count < 8:
        raise InputRangeError(f"points per segment must be >= 8, got {points!r}")
    base = ct.tooth_contour(generation, role, points=count)
    if base.undercut:
        raise NotSupportedError("fillet variants are built for gears free of undercut")
    left_fillet, details = _BUILDERS[variant.kind](generation, role, variant, count)
    d_t = transition_diameter(generation, role, variant)
    radius, psi, _, _ = _flank_at(generation, role, d_t, count)
    left_involute = ct._polar(radius, psi, -1.0)
    left_involute[0] = left_fillet[-1]  # the transition point, exactly
    mirror = np.array([-1.0, 1.0])
    blocks = [
        left_fillet,
        left_involute,
        base.segment("left_tip_flank"),
        base.segment("tip"),
        base.segment("right_tip_flank"),
        left_involute[::-1] * mirror,
        left_fillet[::-1] * mirror,
    ]
    all_points, ranges = ct._joined(blocks)
    segments = tuple(
        ct.ContourSegment(name=name, start=start, end=end)
        for name, (start, end) in zip(ct.SEGMENTS, ranges, strict=True)
    )
    root_diameter = 2.0 * float(np.hypot(*left_fillet[0]))
    first_angle = math.atan2(float(left_fillet[0, 0]), float(left_fillet[0, 1]))
    if abs(first_angle + math.pi / base.number_of_teeth) > CENTRE_LINE_TOLERANCE_RAD:
        raise GeometryInfeasibleError(
            "the variant fillet does not start on the centre line of the gap"
        )
    contour = ct.ToothContour(
        number_of_teeth=base.number_of_teeth,
        generated_root_diameter_mm=root_diameter,
        root_form_diameter_mm=d_t,
        tip_form_diameter_mm=base.tip_form_diameter_mm,
        tip_diameter_mm=base.tip_diameter_mm,
        undercut=False,
        points=tuple((float(x), float(y)) for x, y in all_points),
        segments=segments,
    )
    return FilletResult(
        variant=variant,
        contour=contour,
        transition_diameter_mm=d_t,
        root_diameter_mm=root_diameter,
        min_curvature_radius_mm=polyline_min_curvature_radius(left_fillet),
        details=details,
    )


def _closest_on_polyline(point: Array, polyline: Array) -> tuple[float, Array]:
    """Shortest distance of one point from a polyline (point to segment) and the closest point."""
    a, b = polyline[:-1], polyline[1:]
    ab = b - a
    length2 = np.einsum("ij,ij->i", ab, ab)
    t = np.einsum("ij,ij->i", point[None, :] - a, ab) / np.where(length2 > 0.0, length2, 1.0)
    t = np.clip(t, 0.0, 1.0)
    closest = a + t[:, None] * ab
    gaps = np.linalg.norm(point[None, :] - closest, axis=1)
    index = int(np.argmin(gaps))
    return float(gaps[index]), closest[index]


def mating_tip_clearance(
    generation: GenerationResult, contour: ct.ToothContour, *, samples: int = CLEARANCE_SAMPLES
) -> tuple[float, float]:
    """The smallest distance (mm) between the tip corners of the pinion teeth carried through
    the gaps of the wheel and the wheel contour below its transition diameter, and the wheel
    radius of the closest point of that contour. Negative: the corner lies inside the material.

    The wheel contour is the one with the variant (``apply(...).contour``) or the generated
    one; the pinion is the generated pinion. Spur gears, the wheel at rest, the pinion carried
    around it by the rolling motion of ``fe.placement`` for every rho_1 between the tangent
    points; the followed pinion tooth and its two neighbours are traced, every corner is folded
    into the left gap of the followed wheel tooth, and its Euclidean distance to the fillet
    polyline is taken; the sign comes from the radial comparison at the corner's angle.
    """
    n = integer_input(samples, "positions of the trace")
    if n < 10:
        raise InputRangeError(f"at least 10 positions are needed, got {samples!r}")
    pinion = ct.tooth_contour(generation, "pinion", points=16)
    tip = pinion.segment("tip")
    corners = np.array([tip[0], tip[-1]])
    z_1 = pinion.number_of_teeth
    z_2 = contour.number_of_teeth
    mesh = pl._mesh(generation)
    pitch = 2.0 * math.pi / z_2
    # the wheel contour below the transition on the left, in contour order (gap centre to
    # transition), and the same points sorted by the angle from +y towards -x for the sign
    wheel = contour.as_array()
    r_w = np.hypot(wheel[:, 0], wheel[:, 1])
    below = r_w <= 0.5 * contour.root_form_diameter_mm + 1.0e-9
    left = wheel[:, 0] <= 0.0
    region = wheel[below & left]
    angle_w = np.arctan2(-region[:, 0], region[:, 1])
    order = np.argsort(angle_w)
    angle_sorted, radius_sorted = angle_w[order], np.hypot(region[order, 0], region[order, 1])
    best = (math.inf, math.nan)
    for rho_1 in np.linspace(0.0, mesh.t1_t2, n):
        position = pl.mesh_position(generation, float(rho_1), working_flank="left")
        place = pl.wheel_fixed(position)
        for k in (-1, 0, 1):
            angle = place.tooth_centre_angle_deg.pinion + k * 360.0 / z_1
            traced = pl.placed(corners, place.axis_mm.pinion, angle) - np.array(
                [position.centre_distance_mm, 0.0]
            )
            for x, y in traced:
                # the followed wheel tooth is on +y: turn the corner by whole pitches onto it
                # and mirror the right gap onto the left one
                theta = math.atan2(-x, y)
                turn = theta - math.remainder(theta, pitch)  # whole pitches to the tooth
                c, s = math.cos(turn), math.sin(turn)
                x_f, y_f = x * c + y * s, -x * s + y * c
                if x_f > 0.0:
                    x_f = -x_f
                folded = np.array([x_f, y_f])
                distance, closest = _closest_on_polyline(folded, region)
                theta_f = math.atan2(-x_f, y_f)
                if angle_sorted[0] <= theta_f <= angle_sorted[-1]:
                    r_c = float(np.interp(theta_f, angle_sorted, radius_sorted))
                    if math.hypot(x_f, y_f) < r_c:
                        distance = -distance
                if distance < best[0]:
                    best = (distance, float(np.hypot(*closest)))
    return best
