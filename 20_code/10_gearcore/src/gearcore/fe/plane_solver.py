"""Plane strain finite element solution of a sector mesh with bilinear quadrilaterals.

The transverse section of the solid model, computed with the four-node element in one of two
formulations (``FORMULATIONS``): as Abaqus formulates its first-order fully integrated solids
(CPE4, C3D8), 2 x 2 Gauss points with the volumetric strain taken at the centroid of the
element ("selectively reduced integration (reduced integration on the volumetric terms)",
Abaqus 2025 documentation, 'Solid (continuum) elements'); or with incompatible modes, the
counterpart of CPE4I and C3D8I: two quadratic displacement modes per direction inside the
element, condensed out, their derivatives taken with the Jacobian of the centroid so that a
constant strain state stays exact (the element of Wilson and Taylor; Abaqus derives its own
from Simo and Rifai, so the two agree closely, not exactly). Linear elastic, isotropic, small
displacements. Nodal forces are given per unit thickness (N/mm), displacements come out in mm,
stresses in MPa; the plane strain condition adds sigma_zz = nu (sigma_xx + sigma_yy).

Stress recovery as the 'averaged at nodes' output of Abaqus: the stresses at the Gauss points
of every element are extrapolated to its corners with the bilinear shape functions (the Gauss
points lie at +-1/sqrt(3)), and the values of all elements at a node are averaged.

This solver serves the mesh convergence study (``fe.convergence``); the analyses of the pair
run in Abaqus.
"""

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.sparse import coo_matrix, csr_matrix
from scipy.sparse.linalg import spsolve

from gearcore._safe import finite_input, positive_input
from gearcore.errors import GeometryInfeasibleError, InputRangeError

EQ_EXEMPT = (
    "plane_strain_matrix",
    "stiffness",
    "solve",
    "gauss_stresses",
    "nodal_stresses",
    "principal_stresses",
    "von_mises_plane_strain",
    "strain_energy",
)
"""Finite element method (textbook formulation): no equation of a norm."""

Array = NDArray[np.float64]
IntArray = NDArray[np.int64]
BoolArray = NDArray[np.bool_]

GAUSS = 1.0 / math.sqrt(3.0)
GAUSS_POINTS = ((-GAUSS, -GAUSS), (GAUSS, -GAUSS), (GAUSS, GAUSS), (-GAUSS, GAUSS))
"""In the order of the element corners, so that corner k is nearest to Gauss point k."""
CORNERS = ((-1.0, -1.0), (1.0, -1.0), (1.0, 1.0), (-1.0, 1.0))
FORMULATIONS = ("selectively_reduced", "incompatible_modes")
"""``selectively_reduced``: volumetric strain at the centroid (Abaqus CPE4, C3D8).
``incompatible_modes``: Wilson-Taylor element with full integration (counterpart of CPE4I, C3D8I)."""


@dataclass(frozen=True)
class PlaneSolution:
    """Displacements (N, 2) in mm, stresses (sigma_xx, sigma_yy, sigma_xy) in MPa at the Gauss
    points (M, 4, 3) and averaged at the nodes (N, 3), the nodal loads (N, 2) in N/mm and the
    strain energy in N mm per mm of thickness."""

    displacements_mm: Array
    gauss_stress_mpa: Array
    nodal_stress_mpa: Array
    loads_n_per_mm: Array
    strain_energy_nmm: float
    formulation: str = FORMULATIONS[0]


def _formulation(name: str) -> str:
    if name not in FORMULATIONS:
        raise InputRangeError(f"formulation must be one of {FORMULATIONS}, got {name!r}")
    return name


def plane_strain_matrix(youngs_modulus_mpa: float, poisson_ratio: float) -> Array:
    """The constitutive matrix of plane strain for (eps_xx, eps_yy, gamma_xy)."""
    e = positive_input(youngs_modulus_mpa, "Young's modulus")
    nu = finite_input(poisson_ratio, "Poisson's ratio")
    if not 0.0 <= nu < 0.5:
        raise InputRangeError(f"Poisson's ratio must lie in [0, 0.5) for plane strain, got {nu!r}")
    factor = e / ((1.0 + nu) * (1.0 - 2.0 * nu))
    return factor * np.array(
        [[1.0 - nu, nu, 0.0], [nu, 1.0 - nu, 0.0], [0.0, 0.0, 0.5 * (1.0 - 2.0 * nu)]]
    )


def _shape(xi: float, eta: float) -> Array:
    return 0.25 * np.array(
        [(1 - xi) * (1 - eta), (1 + xi) * (1 - eta), (1 + xi) * (1 + eta), (1 - xi) * (1 + eta)]
    )


def _gradients(xi: float, eta: float) -> Array:
    """d N_k / d xi (row 0) and d N_k / d eta (row 1) of the bilinear quad, shape (2, 4)."""
    return 0.25 * np.array(
        [
            [-(1 - eta), (1 - eta), (1 + eta), -(1 + eta)],
            [-(1 - xi), -(1 + xi), (1 + xi), (1 - xi)],
        ]
    )


def _b_matrices(coords: Array, xi: float, eta: float) -> tuple[Array, Array]:
    """Strain-displacement matrices (M, 3, 8) and Jacobian determinants (M,) of all elements
    at one point of the reference square; ``coords`` are the corners (M, 4, 2)."""
    dn = _gradients(xi, eta)
    jac = np.einsum("ka,mab->mkb", dn, coords)  # (M, 2, 2)
    det = jac[:, 0, 0] * jac[:, 1, 1] - jac[:, 0, 1] * jac[:, 1, 0]
    if not bool(np.all(det > 0.0)):
        raise GeometryInfeasibleError("the mesh has an inverted or degenerate element")
    inverse = np.empty_like(jac)
    inverse[:, 0, 0] = jac[:, 1, 1] / det
    inverse[:, 0, 1] = -jac[:, 0, 1] / det
    inverse[:, 1, 0] = -jac[:, 1, 0] / det
    inverse[:, 1, 1] = jac[:, 0, 0] / det
    dndx = np.einsum("mkb,ba->mka", inverse, dn)  # (M, 2, 4)
    b = np.zeros((len(coords), 3, 8))
    b[:, 0, 0::2] = dndx[:, 0, :]
    b[:, 1, 1::2] = dndx[:, 1, :]
    b[:, 2, 0::2] = dndx[:, 1, :]
    b[:, 2, 1::2] = dndx[:, 0, :]
    return b, det


def _inverse_jacobian(coords: Array, xi: float, eta: float) -> tuple[Array, Array]:
    """Inverse Jacobians (M, 2, 2) and determinants (M,) of all elements at one point."""
    jac = np.einsum("ka,mab->mkb", _gradients(xi, eta), coords)
    det = jac[:, 0, 0] * jac[:, 1, 1] - jac[:, 0, 1] * jac[:, 1, 0]
    if not bool(np.all(det > 0.0)):
        raise GeometryInfeasibleError("the mesh has an inverted or degenerate element")
    inverse = np.empty_like(jac)
    inverse[:, 0, 0] = jac[:, 1, 1] / det
    inverse[:, 0, 1] = -jac[:, 0, 1] / det
    inverse[:, 1, 0] = -jac[:, 1, 0] / det
    inverse[:, 1, 1] = jac[:, 0, 0] / det
    return inverse, det


def _strain_rows(dndx: Array) -> Array:
    """Strain-displacement matrix (M, 3, 2 n) from the Cartesian gradients (M, 2, n) of n
    functions: rows eps_xx, eps_yy, gamma_xy for the displacement pairs (u_x, u_y)."""
    m, _, n = dndx.shape
    b = np.zeros((m, 3, 2 * n))
    b[:, 0, 0::2] = dndx[:, 0, :]
    b[:, 1, 1::2] = dndx[:, 1, :]
    b[:, 2, 0::2] = dndx[:, 1, :]
    b[:, 2, 1::2] = dndx[:, 0, :]
    return b


def _incompatible_gradients(coords: Array, xi: float, eta: float) -> Array:
    """Strain-displacement matrix (M, 3, 4) of the incompatible modes 1 - xi^2 and 1 - eta^2
    at one point, with the inverse Jacobian of the centroid scaled by the ratio of the
    determinants (Taylor's modification), so that the modes integrate to zero over the
    element and a constant strain state remains exact."""
    inverse_0, det_0 = _inverse_jacobian(coords, 0.0, 0.0)
    _, det = _inverse_jacobian(coords, xi, eta)
    local = np.array([[-2.0 * xi, 0.0], [0.0, -2.0 * eta]])  # d/dxi, d/deta of the two modes
    dndx = np.einsum("mkb,ba->mka", inverse_0, local) * (det_0 / det)[:, None, None]
    return _strain_rows(dndx)


def _element_matrices(
    coords: Array, d_matrix: Array, formulation: str
) -> tuple[Array, Array | None]:
    """Element stiffness matrices (M, 8, 8) and, for the incompatible modes, the recovery
    matrices (M, 4, 8) that give the mode amplitudes from the nodal displacements."""
    m = len(coords)
    k_uu = np.zeros((m, 8, 8))
    if formulation == "selectively_reduced":
        for xi, eta in GAUSS_POINTS:
            b, det = _b_bar(coords, xi, eta)
            k_uu += np.einsum("mia,ij,mjb,m->mab", b, d_matrix, b, det)
        return k_uu, None
    k_ua = np.zeros((m, 8, 4))
    k_aa = np.zeros((m, 4, 4))
    for xi, eta in GAUSS_POINTS:
        b, det = _b_matrices(coords, xi, eta)
        g = _incompatible_gradients(coords, xi, eta)
        k_uu += np.einsum("mia,ij,mjb,m->mab", b, d_matrix, b, det)
        k_ua += np.einsum("mia,ij,mjb,m->mab", b, d_matrix, g, det)
        k_aa += np.einsum("mia,ij,mjb,m->mab", g, d_matrix, g, det)
    recovery = np.asarray(
        -np.linalg.solve(k_aa, k_ua.transpose(0, 2, 1)), dtype=np.float64
    )  # alpha = recovery @ u_e
    return k_uu + k_ua @ recovery, recovery


def _b_bar(coords: Array, xi: float, eta: float) -> tuple[Array, Array]:
    """The strain-displacement matrices at one Gauss point with the volumetric strain
    (eps_xx + eps_yy of plane strain) replaced by its value at the centroid: the two normal
    strain rows each carry half of the difference, the shear row stays."""
    b, det = _b_matrices(coords, xi, eta)
    centre, _ = _b_matrices(coords, 0.0, 0.0)
    shift = 0.5 * ((centre[:, 0, :] + centre[:, 1, :]) - (b[:, 0, :] + b[:, 1, :]))
    b[:, 0, :] += shift
    b[:, 1, :] += shift
    return b, det


def _checked(points_mm: Array, quads: IntArray) -> tuple[Array, IntArray]:
    points = np.asarray(points_mm, dtype=np.float64)
    connectivity = np.asarray(quads, dtype=np.int64)
    if points.ndim != 2 or points.shape[1] != 2 or len(points) < 4:
        raise InputRangeError("points must be an array (n, 2)")
    if connectivity.ndim != 2 or connectivity.shape[1] != 4 or len(connectivity) < 1:
        raise InputRangeError("quads must be an array (m, 4)")
    if int(connectivity.min()) < 0 or int(connectivity.max()) >= len(points):
        raise InputRangeError("quads name nodes the mesh does not have")
    return points, connectivity


def stiffness(
    points_mm: Array,
    quads: IntArray,
    d_matrix: Array,
    formulation: str = FORMULATIONS[0],
) -> csr_matrix:
    """The global stiffness matrix (2 N x 2 N) for unit thickness."""
    points, connectivity = _checked(points_mm, quads)
    coords = points[connectivity]
    m = len(connectivity)
    ke, _ = _element_matrices(coords, d_matrix, _formulation(formulation))
    dof = np.empty((m, 8), dtype=np.int64)
    dof[:, 0::2] = 2 * connectivity
    dof[:, 1::2] = 2 * connectivity + 1
    rows = np.repeat(dof, 8, axis=1).ravel()
    cols = np.tile(dof, (1, 8)).ravel()
    n = len(points)
    return coo_matrix((ke.ravel(), (rows, cols)), shape=(2 * n, 2 * n)).tocsr()


def solve(
    points_mm: Array,
    quads: IntArray,
    *,
    d_matrix: Array,
    fixed: BoolArray,
    loads_n_per_mm: Array,
    formulation: str = FORMULATIONS[0],
) -> PlaneSolution:
    """Displacements for the nodal loads with the ``fixed`` nodes held in both directions,
    and the stresses recovered from them."""
    kind = _formulation(formulation)
    points, connectivity = _checked(points_mm, quads)
    held = np.asarray(fixed, dtype=bool)
    loads = np.asarray(loads_n_per_mm, dtype=np.float64)
    if held.shape != (len(points),) or loads.shape != (len(points), 2):
        raise InputRangeError("fixed must be (n,) and loads (n, 2) for n nodes")
    if not held.any():
        raise InputRangeError("no node is fixed: the structure would move freely")
    if not bool(np.all(np.isfinite(loads))):
        raise InputRangeError("the loads must be finite")
    k_global = stiffness(points, connectivity, d_matrix, kind)
    free = np.flatnonzero(np.repeat(~held, 2))
    rhs = loads.ravel()
    u = np.zeros(2 * len(points))
    u[free] = spsolve(k_global[free][:, free].tocsc(), rhs[free])
    if not bool(np.all(np.isfinite(u))):
        raise GeometryInfeasibleError("the solution is not finite: the system is singular")
    displacements = u.reshape(-1, 2)
    gauss = gauss_stresses(points, connectivity, displacements, d_matrix, kind)
    return PlaneSolution(
        displacements_mm=displacements,
        gauss_stress_mpa=gauss,
        nodal_stress_mpa=nodal_stresses(points, connectivity, gauss),
        loads_n_per_mm=loads,
        strain_energy_nmm=strain_energy(displacements, loads),
        formulation=kind,
    )


def gauss_stresses(
    points_mm: Array,
    quads: IntArray,
    displacements_mm: Array,
    d_matrix: Array,
    formulation: str = FORMULATIONS[0],
) -> Array:
    """Stresses (M, 4, 3) at the Gauss points, in the order of ``GAUSS_POINTS``."""
    kind = _formulation(formulation)
    points, connectivity = _checked(points_mm, quads)
    coords = points[connectivity]
    ue = np.asarray(displacements_mm, dtype=np.float64)[connectivity].reshape(len(connectivity), 8)
    result = np.empty((len(connectivity), 4, 3))
    if kind == "selectively_reduced":
        for g, (xi, eta) in enumerate(GAUSS_POINTS):
            b, _ = _b_bar(coords, xi, eta)
            result[:, g, :] = np.einsum("mib,mb->mi", b, ue) @ d_matrix.T
        return result
    _, recovery = _element_matrices(coords, d_matrix, kind)
    assert recovery is not None
    alpha = np.einsum("mab,mb->ma", recovery, ue)
    for g, (xi, eta) in enumerate(GAUSS_POINTS):
        b, _ = _b_matrices(coords, xi, eta)
        strain = np.einsum("mib,mb->mi", b, ue) + np.einsum(
            "mib,mb->mi", _incompatible_gradients(coords, xi, eta), alpha
        )
        result[:, g, :] = strain @ d_matrix.T
    return result


def nodal_stresses(points_mm: Array, quads: IntArray, gauss_stress_mpa: Array) -> Array:
    """Stresses (N, 3) averaged at the nodes from the Gauss point values of the elements that
    share the node, each extrapolated to the corner with the bilinear shape functions."""
    points, connectivity = _checked(points_mm, quads)
    gauss = np.asarray(gauss_stress_mpa, dtype=np.float64)
    if gauss.shape != (len(connectivity), 4, 3):
        raise InputRangeError("gauss stresses must be (m, 4, 3)")
    # value at corner c = sum_g N_g(corner c scaled by sqrt 3) * value at Gauss point g, with
    # the bilinear functions taken over the square of the Gauss points
    extrapolation = np.array(
        [_shape(xi * math.sqrt(3.0), eta * math.sqrt(3.0)) for xi, eta in CORNERS]
    )  # (4 corners, 4 Gauss points)
    at_corners = np.einsum("cg,mgi->mci", extrapolation, gauss)
    sums = np.zeros((len(points), 3))
    counts = np.zeros(len(points))
    for c in range(4):
        np.add.at(sums, connectivity[:, c], at_corners[:, c, :])
        np.add.at(counts, connectivity[:, c], 1.0)
    counts[counts == 0.0] = 1.0
    return sums / counts[:, None]


def principal_stresses(stress_mpa: Array) -> tuple[Array, Array]:
    """The larger and the smaller in-plane principal stress of (sigma_xx, sigma_yy, sigma_xy)."""
    s = np.asarray(stress_mpa, dtype=np.float64)
    if s.shape[-1] != 3:
        raise InputRangeError("a stress has three in-plane components")
    centre = 0.5 * (s[..., 0] + s[..., 1])
    radius = np.sqrt(0.25 * (s[..., 0] - s[..., 1]) ** 2 + s[..., 2] ** 2)
    return centre + radius, centre - radius


def von_mises_plane_strain(stress_mpa: Array, poisson_ratio: float) -> Array:
    """The equivalent stress of the distortion energy hypothesis with sigma_zz = nu (sigma_xx
    + sigma_yy) of plane strain."""
    s = np.asarray(stress_mpa, dtype=np.float64)
    nu = finite_input(poisson_ratio, "Poisson's ratio")
    sx, sy, txy = s[..., 0], s[..., 1], s[..., 2]
    sz = nu * (sx + sy)
    return np.sqrt(0.5 * ((sx - sy) ** 2 + (sy - sz) ** 2 + (sz - sx) ** 2) + 3.0 * txy**2)


def strain_energy(displacements_mm: Array, loads_n_per_mm: Array) -> float:
    """Half the work of the nodal loads: the strain energy of the linear solution."""
    u = np.asarray(displacements_mm, dtype=np.float64)
    f = np.asarray(loads_n_per_mm, dtype=np.float64)
    if u.shape != f.shape:
        raise InputRangeError("displacements and loads must have the same shape")
    return float(0.5 * np.sum(u * f))
