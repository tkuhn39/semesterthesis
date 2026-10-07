"""Load case and evaluation of the mesh convergence study of the wheel sector.

The study answers why the mesh has its density: the tensile stress at the tooth root and the
displacement at the tooth tip, the quantities the analyses are made for, are computed on the
transverse section of the sector with ``fe.plane_solver`` for a series of refinements of the
mesh (``fe.refine``), and the change from level to level and the extrapolated limit give the
discretisation error of the density that is used. Stommel, Stojek, Korte, *FEM zur Berechnung
von Kunststoff- und Elastomerbauteilen*, 2nd edition, Hanser 2018, section 7.7.1 p. 424 (the
h-method: refine until the stress differences between neighbouring elements are small enough)
and section 7.7.3 p. 433 (stated for structural elements): a convergence study
on a small model under a comparable load, before the final evaluation of a simulation.

Load case (comparable to the analyses of the pair, without contact iteration): the mating gear
presses on the working flank of the middle tooth at one point of the path of contact. Preset is
the point B, the outer point of single pair tooth contact of the wheel (the point at which the
whole load lies on one tooth with the longest lever arm, where ISO 6336-3 Method B evaluates the
root stress). The force along the line of action is F_bt = T_2 / r_b2, per unit face width
F' = F_bt / b. It acts as the pressure distribution of a line contact after Hertz,
p(s) = p_0 sqrt(1 - (s / b_H)^2) over the arc |s| <= b_H of the flank around the contact point,
with the half width b_H = sqrt(4 F' rho / (pi E*)), rho = rho_1 rho_2 / (rho_1 + rho_2) the
relative radius of curvature at the contact point and E* = E / (1 - nu^2) of the plastic wheel
against the rigid steel pinion. Where the arc reaches beyond the tip form circle (the tip edge
break carries no contact) the distribution is cut there and scaled to the full force. The
pressure acts normal to the surface; its consistent nodal loads are integrated per surface
edge. The wheel is held as in the analyses: the bore and both cut planes.

Evaluation: the tensile root stress is the largest nodal maximum principal stress on the
surface of the fillet of the loaded flank (from the root form point to the centre line of the
gap); the tip displacement is the displacement of the node of the tooth centre on the tip
circle and of the tip corner of the loaded side; the strain energy of the sector is the global
measure, which converges monotonically for the displacement method.
"""

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import brentq

from gearcore import involute as iv
from gearcore._safe import finite_input, positive_input
from gearcore.errors import GeometryInfeasibleError, InputRangeError
from gearcore.fe import placement as pl
from gearcore.fe import plane_solver as ps
from gearcore.fe.refine import _band, _owners, middle_tooth
from gearcore.fe.sector_mesh import SectorMesh
from gearcore.models.results import GenerationResult
from gearcore.trace import eq

HERTZ = "NiemannWinterHoehnStahl2019"

EQ_EXEMPT = ("wheel_load_case", "fixed_nodes", "evaluate")
"""Load case of a study and its evaluation: no equation of a norm (the Hertz line contact is
the classical textbook result, used only to shape the load patch of the study)."""

Array = NDArray[np.float64]
IntArray = NDArray[np.int64]

TIP_TOLERANCE_MM = 1.0e-6
GAUSS_4 = np.polynomial.legendre.leggauss(4)
"""Points and weights of the Gauss-Legendre rule with 4 points for the loads of one edge."""


@dataclass(frozen=True)
class LoadCase:
    """The nodal loads (N, 2) in N/mm of one position, and what they are made of."""

    torque_wheel_nmm: float
    rho_1_mm: float
    force_per_mm: float
    half_width_mm: float
    max_pressure_mpa: float
    contact_point_mm: tuple[float, float]
    contact_radius_mm: float
    loaded_side: int
    loaded_tooth: int
    cut_at_tip_form_circle: bool
    loads_n_per_mm: Array
    resultant_n_per_mm: tuple[float, float]
    loaded_nodes: IntArray


@dataclass(frozen=True)
class Evaluation:
    """What the convergence study compares, from one solution."""

    nodes: int
    elements: int
    root_sigma1_max_mpa: float
    root_node: int
    root_radius_mm: float
    root_angle_deg: float
    root_von_mises_max_mpa: float
    tip_centre_node: int
    tip_centre_displacement_mm: tuple[float, float]
    tip_centre_magnitude_mm: float
    tip_corner_node: int
    tip_corner_displacement_mm: tuple[float, float]
    tip_corner_magnitude_mm: float
    strain_energy_nmm: float
    fillet_arc_mm: Array
    fillet_sigma1_mpa: Array
    fillet_nodes: IntArray


@dataclass(frozen=True)
class Richardson:
    """Extrapolation of a quantity over the element size h: f(h) = f_0 + C h^p fitted through
    the last three levels; ``order`` and ``limit`` are None when the sequence does not
    converge monotonically."""

    h: tuple[float, ...]
    values: tuple[float, ...]
    successive_change: tuple[float, ...]
    order: float | None
    limit: float | None
    relative_error: tuple[float, ...] | None


def _wrapped(angle: float) -> float:
    return math.atan2(math.sin(angle), math.cos(angle))


@eq(HERTZ, "Tab. 13.1", section="13.2.1", page=372, note="p_H = sqrt(K E'/pi), b = 2 D_1 p_H / E'")
@eq(
    HERTZ,
    "(13.5)",
    section="13.2.3",
    page=376,
    note="1/E' = 1/2 ((1-nu_1^2)/E_1 + (1-nu_2^2)/E_2), E_2 -> inf",
)
@eq(HERTZ, "(13.6)", section="13.2.3", page=376, note="R = R_1 R_2 / (R_1 + R_2), D_1 = 2 R")
@eq(
    "VDI2736-2:2014",
    "(15)",
    section="Flankentragfähigkeit",
    page=15,
    note="plastic gear: modulus at operating temperature",
)
def hertz_line_contact(
    force_per_mm: float,
    rho_1_mm: float,
    rho_2_mm: float,
    youngs_modulus_mpa: float,
    poisson_ratio: float,
) -> tuple[float, float]:
    """Half width b (mm) and pressure p_H (MPa) of the Hertz line contact between the elastic
    gear (E, nu) and a rigid counterpart, for the line load F' = F_N / l_eff in N/mm and the
    radii of curvature of both flanks at the contact point.

    Written in the quantities of Tab. 13.1: the equivalent diameter D_1 = 2 R with R from
    (13.6), the Stribeck pressure K = F_N / (D_1 l_eff), the reduced modulus E' from (13.5) with
    the rigid counterpart (E_2 -> infinity). VDI 2736 Blatt 2 applies the same Hertz pressure
    to plastic gears with the modulus at operating temperature (Eq. (15), Z_E).
    """
    force = positive_input(force_per_mm, "line load")
    rho_1 = positive_input(rho_1_mm, "radius of curvature rho_1")
    rho_2 = positive_input(rho_2_mm, "radius of curvature rho_2")
    e = positive_input(youngs_modulus_mpa, "Young's modulus")
    nu = finite_input(poisson_ratio, "Poisson's ratio")
    if not 0.0 <= nu < 0.5:
        raise InputRangeError(f"Poisson's ratio must lie in [0, 0.5), got {nu!r}")
    e_prime = 2.0 * e / (1.0 - nu**2)
    d_1 = 2.0 * rho_1 * rho_2 / (rho_1 + rho_2)
    k = force / d_1
    p_h = math.sqrt(k * e_prime / math.pi)
    b = 2.0 * d_1 * p_h / e_prime
    return b, p_h


def _surface_edges_of(section: SectorMesh) -> list[tuple[int, int, int, int, str]]:
    """(a, b, tooth, side, band) of every edge of the surface path."""
    owner = _owners(section.quads)
    radius = np.hypot(section.points_mm[:, 0], section.points_mm[:, 1])
    result = []
    path = section.surface_path
    for a, b in zip(path[:-1].tolist(), path[1:].tolist(), strict=True):
        q = owner[(a, b) if a < b else (b, a)]
        tooth = int(section.quad_tooth[q])
        band = _band(section, a, b, radius) if tooth > 0 else "shoulder"
        result.append((a, b, tooth, int(section.quad_side[q]), band))
    return result


def wheel_load_case(
    generation: GenerationResult,
    section: SectorMesh,
    *,
    torque_wheel_nmm: float,
    youngs_modulus_mpa: float,
    poisson_ratio: float,
    face_width_mm: float,
    working_flank: pl.Flank = "right",
    rho_1_mm: float | None = None,
    half_width_scale: float = 1.0,
) -> LoadCase:
    """The loads of the wheel sector for the torque at the wheel, in the position of the pinion
    flank curvature radius ``rho_1_mm`` (preset: point B of the wheel). ``half_width_scale``
    stretches the Hertz patch for sensitivity checks."""
    if not isinstance(generation, GenerationResult):
        raise InputRangeError("a GenerationResult of compute_generation is required")
    if not isinstance(section, SectorMesh):
        raise InputRangeError("a SectorMesh of the wheel is required")
    wheel = generation.gears.wheel
    if section.number_of_teeth != wheel.number_of_teeth:
        raise InputRangeError("the sector mesh is not the wheel of this generation")
    torque = positive_input(torque_wheel_nmm, "torque at the wheel")
    e_mod = positive_input(youngs_modulus_mpa, "Young's modulus")
    nu = finite_input(poisson_ratio, "Poisson's ratio")
    width = positive_input(face_width_mm, "face width")
    scale = positive_input(half_width_scale, "half width scale")
    pair = generation.inputs
    geometry = generation.pair_geometry
    rho_a, rho_e = pl.path_of_contact_limits(generation)
    rho_1 = rho_e - geometry.transverse_base_pitch_mm if rho_1_mm is None else rho_1_mm
    rho_1 = finite_input(rho_1, "rho_1")
    if not rho_a <= rho_1 <= rho_e:
        raise InputRangeError(f"rho_1 = {rho_1!r} mm lies outside the path of contact")
    position = pl.mesh_position(generation, rho_1, working_flank=working_flank)
    place = pl.fixed_axes(position)

    # force along the line of action and the Hertz patch
    r_b2 = 0.5 * iv.base_diameter(
        wheel.number_of_teeth,
        pair.normal_module_mm,
        math.radians(pair.normal_pressure_angle_deg),
        0.0,
    )
    force_per_mm = torque / r_b2 / width
    rho = position.radius_of_curvature_mm
    hertz_half_width, _ = hertz_line_contact(force_per_mm, rho.pinion, rho.wheel, e_mod, nu)
    half_width = scale * hertz_half_width
    max_pressure = 2.0 * force_per_mm / (math.pi * half_width)

    # contact point in the frame of the sector: the middle tooth on its centre line
    axis = place.axis_mm.wheel
    v = (position.contact_point_mm[0] - axis[0], position.contact_point_mm[1] - axis[1])
    offset = _wrapped(math.atan2(v[1], v[0]) - math.radians(place.tooth_centre_angle_deg.wheel))
    contact_radius = math.hypot(*v)
    side = 1 if offset > 0.0 else -1
    tooth = middle_tooth(section.teeth)
    theta = 0.5 * math.pi + (tooth - 0.5 * (section.teeth + 1)) * section.pitch_angle_rad
    contact = (contact_radius * math.cos(theta + offset), contact_radius * math.sin(theta + offset))

    # the loaded flank as a polyline with its arc length; the contact point on it
    edges = _surface_edges_of(section)
    flank = [e for e in edges if e[2] == tooth and e[3] == side and e[4] == "height"]
    if not flank:
        raise GeometryInfeasibleError("the loaded flank has no surface edges")
    points = section.points_mm
    nodes = [flank[0][0]] + [e[1] for e in flank]
    poly = points[nodes]
    lengths = np.hypot(*(poly[1:] - poly[:-1]).T)
    arc = np.concatenate(([0.0], np.cumsum(lengths)))
    best, s_contact = None, 0.0
    for k in range(len(poly) - 1):
        d = poly[k + 1] - poly[k]
        t = float(
            np.clip(np.dot(np.array(contact) - poly[k], d) / max(float(d @ d), 1e-300), 0.0, 1.0)
        )
        foot = poly[k] + t * d
        gap = float(np.hypot(*(foot - np.array(contact))))
        if best is None or gap < best:
            best, s_contact = gap, float(arc[k] + t * lengths[k])
    if best is None or best > 0.05 * pair.normal_module_mm:
        raise GeometryInfeasibleError(
            f"the contact point lies {best} mm from the flank: the position and the mesh disagree"
        )
    # the patch along the arc, cut where the flank ends (the involute runs from the root form
    # point at s = 0 to the tip form point at s = arc[-1])
    lower, upper = s_contact - half_width, s_contact + half_width
    cut = upper > arc[-1] + 1.0e-12 or lower < -1.0e-12
    lower, upper = max(lower, 0.0), min(upper, float(arc[-1]))

    def pressure(s: Array) -> Array:
        inside = (s >= lower) & (s <= upper)
        x = np.clip((s - s_contact) / half_width, -1.0, 1.0)
        return np.where(inside, max_pressure * np.sqrt(np.maximum(1.0 - x * x, 0.0)), 0.0)

    xi, weights = GAUSS_4
    loads = np.zeros((len(points), 2))
    for k in range(len(poly) - 1):
        a, b = nodes[k], nodes[k + 1]
        if arc[k + 1] < lower or arc[k] > upper:
            continue
        s = arc[k] + 0.5 * (xi + 1.0) * lengths[k]
        p = pressure(s)
        tangent = (poly[k + 1] - poly[k]) / lengths[k]
        outward = np.array([tangent[1], -tangent[0]])  # the material lies on the left of the path
        weight = 0.5 * lengths[k] * weights
        shape_a, shape_b = 0.5 * (1.0 - xi), 0.5 * (1.0 + xi)
        loads[a] += -outward * float(np.sum(weight * p * shape_a))
        loads[b] += -outward * float(np.sum(weight * p * shape_b))
    total = float(np.hypot(*loads.sum(axis=0)))
    if total <= 0.0:
        raise GeometryInfeasibleError("the load patch meets no surface edge")
    loads *= force_per_mm / total  # exact total force, also where the patch was cut
    resultant = loads.sum(axis=0)
    if float(np.dot(resultant, contact)) >= 0.0:
        raise GeometryInfeasibleError("the resultant of the pressure does not point into the gear")
    loaded = np.flatnonzero(np.hypot(loads[:, 0], loads[:, 1]) > 0.0)
    return LoadCase(
        torque_wheel_nmm=torque,
        rho_1_mm=rho_1,
        force_per_mm=force_per_mm,
        half_width_mm=half_width,
        max_pressure_mpa=max_pressure,
        contact_point_mm=contact,
        contact_radius_mm=contact_radius,
        loaded_side=side,
        loaded_tooth=tooth,
        cut_at_tip_form_circle=bool(cut),
        loads_n_per_mm=loads,
        resultant_n_per_mm=(float(resultant[0]), float(resultant[1])),
        loaded_nodes=loaded.astype(np.int64),
    )


def fixed_nodes(section: SectorMesh) -> NDArray[np.bool_]:
    """The nodes of the bore and of both cut planes: the Fesselung of the analyses."""
    if not isinstance(section, SectorMesh):
        raise InputRangeError("a SectorMesh is required")
    kind = np.array(section.node_kind)
    return np.asarray((kind == "bore") | (kind == "cut"), dtype=np.bool_)


def evaluate(
    section: SectorMesh, solution: ps.PlaneSolution, load: LoadCase, poisson_ratio: float
) -> Evaluation:
    """Root stress, tip displacement and strain energy of one solution (see the module
    docstring)."""
    if not isinstance(section, SectorMesh) or not isinstance(solution, ps.PlaneSolution):
        raise InputRangeError("a SectorMesh and its PlaneSolution are required")
    if len(solution.displacements_mm) != len(section.points_mm):
        raise InputRangeError("the solution does not belong to this mesh")
    nu = finite_input(poisson_ratio, "Poisson's ratio")
    points = section.points_mm
    radius = np.hypot(points[:, 0], points[:, 1])
    tooth, side = load.loaded_tooth, load.loaded_side
    theta = 0.5 * math.pi + (tooth - 0.5 * (section.teeth + 1)) * section.pitch_angle_rad
    edges = _surface_edges_of(section)
    # the fillet of the loaded flank, from the root form point towards the centre line of the
    # gap: the root edges of that half in the order of the path
    root_edges = [e for e in edges if e[2] == tooth and e[3] == side and e[4] == "root"]
    if not root_edges:
        raise GeometryInfeasibleError("the loaded flank has no fillet edges")
    chain = [root_edges[0][0]] + [e[1] for e in root_edges]
    # the path runs counter-clockwise: on the left half it leaves the tooth at the root form
    # point, on the right half it arrives there, so that half is reversed to start at the point
    fillet = np.array(chain if side == 1 else chain[::-1], dtype=np.int64)
    arc = np.concatenate(
        ([0.0], np.cumsum(np.hypot(*(points[fillet[1:]] - points[fillet[:-1]]).T)))
    )
    sigma1, _ = ps.principal_stresses(solution.nodal_stress_mpa)
    mises = ps.von_mises_plane_strain(solution.nodal_stress_mpa, nu)
    where = int(np.argmax(sigma1[fillet]))
    node = int(fillet[where])
    angle = math.degrees(_wrapped(math.atan2(points[node, 1], points[node, 0]) - theta))
    # tip: the nodes of the middle tooth on the tip circle
    tip = [
        n
        for n in np.unique(section.surface_path).tolist()
        if radius[n] > section.tip_radius_mm - TIP_TOLERANCE_MM
    ]
    offsets = {n: _wrapped(math.atan2(points[n, 1], points[n, 0]) - theta) for n in tip}
    own = [n for n in tip if abs(offsets[n]) < 0.5 * section.pitch_angle_rad]
    if not own:
        raise GeometryInfeasibleError("the middle tooth has no node on the tip circle")
    centre = min(own, key=lambda n: abs(offsets[n]))
    on_side = [n for n in own if side * offsets[n] > 0.0]
    corner = max(on_side, key=lambda n: abs(offsets[n])) if on_side else centre
    u = solution.displacements_mm
    return Evaluation(
        nodes=len(points),
        elements=len(section.quads),
        root_sigma1_max_mpa=float(sigma1[node]),
        root_node=node,
        root_radius_mm=float(radius[node]),
        root_angle_deg=angle,
        root_von_mises_max_mpa=float(mises[fillet].max()),
        tip_centre_node=int(centre),
        tip_centre_displacement_mm=(float(u[centre, 0]), float(u[centre, 1])),
        tip_centre_magnitude_mm=float(np.hypot(*u[centre])),
        tip_corner_node=int(corner),
        tip_corner_displacement_mm=(float(u[corner, 0]), float(u[corner, 1])),
        tip_corner_magnitude_mm=float(np.hypot(*u[corner])),
        strain_energy_nmm=solution.strain_energy_nmm,
        fillet_arc_mm=arc,
        fillet_sigma1_mpa=np.asarray(sigma1[fillet], dtype=np.float64),
        fillet_nodes=fillet,
    )


@eq(
    "DahmenReusken2022",
    "(10.35)",
    section="10.4",
    page=528,
    note="N(h) = J + c_1 h^q + ..., one term kept, q fitted",
)
@eq("DahmenReusken2022", "(10.36)", section="10.4", page=528, note="extrapolation to h = 0")
@eq(
    "Bathe1996",
    "(4.102)",
    section="4.3.5",
    page=247,
    note="a priori order of the finite element error",
)
def richardson(
    h: tuple[float, ...] | list[float], values: tuple[float, ...] | list[float]
) -> Richardson:
    """Successive relative changes and, from the last three levels, the order and the
    extrapolated limit of f(h) = f_0 + C h^p.

    The model of the error follows the a priori estimate of the displacement-based finite
    element method, Bathe, *Finite Element Procedures*, Prentice-Hall 1996, section 4.3.5,
    Eq. (4.101) and (4.102), p. 247: the error of the solution is bounded by c h^k with the
    order k of the complete polynomial of the element (k = 1 for the four-node element), and
    section 4.3.6, p. 254: the stress jumps decrease with the mesh at a rate set by the
    element order. The extrapolation to h = 0 from a series of meshes is Richardson's
    (source to be registered, known limit FE-13). ``order`` and ``limit`` are None when the
    sequence does not converge monotonically.
    """
    sizes = tuple(positive_input(x, "element size") for x in h)
    f = tuple(finite_input(x, "value") for x in values)
    if len(sizes) != len(f) or len(f) < 2:
        raise InputRangeError("at least two levels with their element sizes are required")
    if any(b >= a for a, b in zip(sizes[:-1], sizes[1:], strict=True)):
        raise InputRangeError("the element sizes must decrease from level to level")
    change = tuple(abs(b - a) / abs(b) for a, b in zip(f[:-1], f[1:], strict=True) if b != 0.0)
    order = limit = None
    errors = None
    if len(f) >= 3:
        h1, h2, h3 = sizes[-3:]
        f1, f2, f3 = f[-3:]
        d12, d23 = f1 - f2, f2 - f3
        if d23 != 0.0 and d12 / d23 > 0.0:
            target = d12 / d23

            def g(p: float) -> float:
                return float((h1**p - h2**p) / (h2**p - h3**p) - target)

            try:
                p = float(brentq(g, 0.05, 8.0))
            except ValueError:
                p = None
            if p is not None:
                c = d23 / (h2**p - h3**p)
                f0 = f3 - c * h3**p
                order, limit = p, float(f0)
                if f0 != 0.0:
                    errors = tuple((x - f0) / abs(f0) for x in f)
    return Richardson(
        h=sizes, values=f, successive_change=change, order=order, limit=limit, relative_error=errors
    )


@eq(
    "DahmenReusken2022",
    "(10.35)",
    section="10.4",
    page=528,
    note="N(h) = J + c_1 h^q + ..., one term kept, q fitted",
)
@eq("DahmenReusken2022", "(10.36)", section="10.4", page=528, note="extrapolation to h = 0")
@eq(
    "Bathe1996",
    "(4.102)",
    section="4.3.5",
    page=247,
    note="a priori order of the finite element error",
)
def richardson_fit(
    h: tuple[float, ...] | list[float], values: tuple[float, ...] | list[float]
) -> Richardson:
    """Least squares fit of f(h) = f_0 + C h^p through all levels (four or more): for every
    order p the linear parameters f_0 and C follow directly, the order with the smallest
    residual is taken. More robust than the three-point extrapolation when the levels are
    not a clean series h, h/2, h/3 ..."""
    sizes = tuple(positive_input(x, "element size") for x in h)
    f = np.array([finite_input(x, "value") for x in values], dtype=np.float64)
    if len(sizes) != len(f) or len(f) < 4:
        raise InputRangeError("at least four levels with their element sizes are required")
    hs = np.array(sizes, dtype=np.float64)
    change = tuple(abs(b - a) / abs(b) for a, b in zip(f[:-1], f[1:], strict=True) if b != 0.0)

    def fit(p: float) -> tuple[float, float, float]:
        design = np.column_stack((np.ones(len(hs)), hs**p))
        (f0, c), residual, _, _ = np.linalg.lstsq(design, f, rcond=None)
        error = float(residual[0]) if len(residual) else float(np.sum((design @ (f0, c) - f) ** 2))
        return float(f0), float(c), error

    orders = np.linspace(0.2, 6.0, 117)
    errors = [fit(float(p))[2] for p in orders]
    best = orders[int(np.argmin(errors))]
    for step in (0.02, 0.004, 0.0008):
        candidates = np.clip(np.linspace(best - 5 * step, best + 5 * step, 11), 0.05, 8.0)
        best = candidates[int(np.argmin([fit(float(p))[2] for p in candidates]))]
    f0, c, _ = fit(float(best))
    if f0 == 0.0 or not math.isfinite(f0):
        return Richardson(
            h=sizes,
            values=tuple(f.tolist()),
            successive_change=change,
            order=None,
            limit=None,
            relative_error=None,
        )
    return Richardson(
        h=sizes,
        values=tuple(f.tolist()),
        successive_change=change,
        order=float(best),
        limit=f0,
        relative_error=tuple(float((x - f0) / abs(f0)) for x in f),
    )
