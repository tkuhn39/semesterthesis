"""
@module: app.services.model.plane_fe
@context: Domain layer — FE rolling model, native 2D quick solver (plan v2 workstream B).
@role: Plane-strain Q4 finite-element solver (numpy/scipy sparse, solves the 2D gear sector in
       well under a second) powering the **mesh-convergence quick check** before any long Abaqus
       run: unit flank load on a mid tooth, bore fixed (Fesselung), track the maximum tensile
       surface stress along the loaded tooth's root fillet over the FVA density levels. Root and
       flank density groups converge in **separate** searches (user decision: no region gets
       over-refined because of the other).

Scope notes: this is a convergence/ranking instrument, not the load-capacity result — the load
is a single static point force at the tooth tip (Method-C-like), materials are linear-elastic,
and the real 3D rolling contact lives in the Abaqus deck. For optimized root fillets the norm
factors Y_F/Y_S do not apply; this solver evaluates the whole fillet (max tensile stress along
the curve), which is exactly the criterion the fillet-strategy literature uses.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.sparse import coo_matrix
from scipy.sparse.linalg import spsolve

from app.services.geometry.tooth_form import ToothProfile
from app.services.model.template_mesher import SectorMesh2D, generate_sector_2d

Array = NDArray[np.float64]

_GAUSS = 1.0 / math.sqrt(3.0)
_GAUSS_POINTS = [(-_GAUSS, -_GAUSS), (_GAUSS, -_GAUSS), (_GAUSS, _GAUSS), (-_GAUSS, _GAUSS)]


def _dmatrix(e_mpa: float, nu: float) -> Array:
    """Plane-strain constitutive matrix."""
    f = e_mpa / ((1.0 + nu) * (1.0 - 2.0 * nu))
    return f * np.array(
        [
            [1.0 - nu, nu, 0.0],
            [nu, 1.0 - nu, 0.0],
            [0.0, 0.0, (1.0 - 2.0 * nu) / 2.0],
        ]
    )


def _shape_derivs(xi: float, eta: float) -> Array:
    """dN/d(xi,eta) for the bilinear quad, shape (2, 4)."""
    return 0.25 * np.array(
        [
            [-(1 - eta), (1 - eta), (1 + eta), -(1 + eta)],
            [-(1 - xi), -(1 + xi), (1 + xi), (1 - xi)],
        ]
    )


def solve_plane_strain(
    pts: Array,
    quads: list[tuple[int, ...]],
    *,
    e_mpa: float,
    nu: float,
    fixed: set[int],
    loads: dict[int, tuple[float, float]],
) -> Array:
    """Nodal displacements (N, 2) for point loads with fully fixed ``fixed`` nodes."""
    n = len(pts)
    conn = np.asarray(quads, dtype=np.int64)
    coords = pts[conn]  # (M, 4, 2)
    d_mat = _dmatrix(e_mpa, nu)
    m = len(conn)
    ke = np.zeros((m, 8, 8))
    for xi, eta in _GAUSS_POINTS:
        dn = _shape_derivs(xi, eta)  # (2, 4)
        jac = np.einsum("ka,mab->mkb", dn, coords)  # (M, 2, 2): J = dN @ coords
        det = jac[:, 0, 0] * jac[:, 1, 1] - jac[:, 0, 1] * jac[:, 1, 0]
        inv = np.empty_like(jac)
        inv[:, 0, 0] = jac[:, 1, 1] / det
        inv[:, 0, 1] = -jac[:, 0, 1] / det
        inv[:, 1, 0] = -jac[:, 1, 0] / det
        inv[:, 1, 1] = jac[:, 0, 0] / det
        dndx = np.einsum("mkb,ba->mka", inv, dn)  # (M, 2, 4): d/dx, d/dy of N_a
        b = np.zeros((m, 3, 8))
        b[:, 0, 0::2] = dndx[:, 0, :]
        b[:, 1, 1::2] = dndx[:, 1, :]
        b[:, 2, 0::2] = dndx[:, 1, :]
        b[:, 2, 1::2] = dndx[:, 0, :]
        ke += np.einsum("mia,ij,mjb,m->mab", b, d_mat, b, det)

    dof = np.empty((m, 8), dtype=np.int64)
    dof[:, 0::2] = 2 * conn
    dof[:, 1::2] = 2 * conn + 1
    rows = np.repeat(dof, 8, axis=1).ravel()
    cols = np.tile(dof, (1, 8)).ravel()
    k_global = coo_matrix((ke.ravel(), (rows, cols)), shape=(2 * n, 2 * n)).tocsr()

    rhs = np.zeros(2 * n)
    for node, (fx, fy) in loads.items():
        rhs[2 * node] += fx
        rhs[2 * node + 1] += fy
    free = np.ones(2 * n, dtype=bool)
    for node in fixed:
        free[2 * node] = free[2 * node + 1] = False
    u = np.zeros(2 * n)
    idx = np.where(free)[0]
    u[idx] = spsolve(k_global[idx][:, idx], rhs[idx])
    return u.reshape(-1, 2)


def nodal_principal_stress(
    pts: Array,
    quads: list[tuple[int, ...]],
    u: Array,
    *,
    e_mpa: float,
    nu: float,
) -> Array:
    """Max principal stress per node (element-centre stresses averaged over incident elements)."""
    conn = np.asarray(quads, dtype=np.int64)
    coords = pts[conn]
    d_mat = _dmatrix(e_mpa, nu)
    dn = _shape_derivs(0.0, 0.0)
    jac = np.einsum("ka,mab->mkb", dn, coords)
    det = jac[:, 0, 0] * jac[:, 1, 1] - jac[:, 0, 1] * jac[:, 1, 0]
    inv = np.empty_like(jac)
    inv[:, 0, 0] = jac[:, 1, 1] / det
    inv[:, 0, 1] = -jac[:, 0, 1] / det
    inv[:, 1, 0] = -jac[:, 1, 0] / det
    inv[:, 1, 1] = jac[:, 0, 0] / det
    dndx = np.einsum("mkb,ba->mka", inv, dn)
    ue = u[conn].reshape(len(conn), 8)
    b = np.zeros((len(conn), 3, 8))
    b[:, 0, 0::2] = dndx[:, 0, :]
    b[:, 1, 1::2] = dndx[:, 1, :]
    b[:, 2, 0::2] = dndx[:, 1, :]
    b[:, 2, 1::2] = dndx[:, 0, :]
    strain = np.einsum("mib,mb->mi", b, ue)
    stress = strain @ d_mat.T  # (M, 3): sxx, syy, sxy
    centre = 0.5 * (stress[:, 0] + stress[:, 1])
    radius = np.sqrt(0.25 * (stress[:, 0] - stress[:, 1]) ** 2 + stress[:, 2] ** 2)
    s1 = centre + radius
    sums = np.zeros(len(pts))
    counts = np.zeros(len(pts))
    for k in range(4):
        np.add.at(sums, conn[:, k], s1)
        np.add.at(counts, conn[:, k], 1.0)
    return sums / np.maximum(counts, 1.0)


@dataclass(frozen=True)
class RootStressResult:
    """One quick-solve: peak tensile fillet stress of the loaded tooth."""

    sigma_max_mpa: float
    node: int
    n_nodes: int
    n_quads: int


def _tip_load_stress(
    mesh: SectorMesh2D,
    profile: ToothProfile,
    *,
    load_n: float,
    e_mpa: float,
    nu: float,
) -> np.ndarray:
    """Solve the unit tip load on the +0.5-pitch tooth; return nodal σ1 for the whole mesh."""
    pts = mesh.points
    pitch = 2.0 * math.pi / profile.z
    phi = (np.arctan2(pts[:, 1], pts[:, 0]) - math.pi / 2.0) / pitch
    radii = np.hypot(pts[:, 0], pts[:, 1])
    kinds = np.asarray(mesh.kind)

    # Load node: the loaded (right) flank top of the tooth at +0.5 pitch — highest surface
    # node below the chamfer on the flank side facing the +1-pitch gap.
    flank_mask = (
        (kinds == "surface")
        & (phi > 0.5)
        & (phi < 1.0)
        & (radii > profile.d_Na / 2.0 - 0.15)
        & (radii <= profile.d_Na / 2.0 + 1e-6)
    )
    candidates = np.where(flank_mask)[0]
    load_node = int(candidates[np.argmax(radii[candidates])])
    # Force along the flank normal (line-of-action direction), pointing into the tooth.
    alpha_y = math.acos(min(1.0, profile.d_b / (2.0 * radii[load_node])))
    tangent_dir = math.atan2(pts[load_node, 1], pts[load_node, 0]) + (math.pi / 2.0 - alpha_y)
    force = (-load_n * math.cos(tangent_dir), -load_n * math.sin(tangent_dir))

    bore_nodes = {int(i) for i in np.where(kinds == "bore")[0]}
    u = solve_plane_strain(
        pts, mesh.quads, e_mpa=e_mpa, nu=nu, fixed=bore_nodes, loads={load_node: force}
    )
    return nodal_principal_stress(pts, mesh.quads, u, e_mpa=e_mpa, nu=nu)


def root_tensile_stress(
    mesh: SectorMesh2D,
    profile: ToothProfile,
    *,
    load_n: float = 100.0,
    e_mpa: float = 3200.0,
    nu: float = 0.35,
    fillet_limit_radius_mm: float | None = None,
) -> RootStressResult:
    """Unit tip load on the +0.5-pitch tooth; max principal stress along its root fillet.

    ``fillet_limit_radius_mm`` bounds the evaluated fillet band (default d_Ff/2); pass the
    strategy's junction radius for fillets that leave the involute above d_Ff (Landi).
    """
    pts = mesh.points
    pitch = 2.0 * math.pi / profile.z
    phi = (np.arctan2(pts[:, 1], pts[:, 0]) - math.pi / 2.0) / pitch
    radii = np.hypot(pts[:, 0], pts[:, 1])
    kinds = np.asarray(mesh.kind)
    s1 = _tip_load_stress(mesh, profile, load_n=load_n, e_mpa=e_mpa, nu=nu)
    r_limit = profile.d_Ff / 2.0 if fillet_limit_radius_mm is None else fillet_limit_radius_mm
    fillet_mask = (kinds == "surface") & (np.abs(phi - 0.5) < 0.5) & (radii < r_limit + 1e-6)
    fillet_nodes = np.where(fillet_mask)[0]
    best = int(fillet_nodes[np.argmax(s1[fillet_nodes])])
    return RootStressResult(
        sigma_max_mpa=float(s1[best]),
        node=best,
        n_nodes=len(pts),
        n_quads=len(mesh.quads),
    )


@dataclass(frozen=True)
class FilletSurfaceStress:
    """Tensile-side fillet surface stress of the loaded tooth, in ITS tooth frame."""

    xy_tooth: np.ndarray  # (N, 2) node positions rotated so the loaded tooth centre is +y
    sigma1_mpa: np.ndarray  # (N,) nodal max principal stress
    sigma_junction_mpa: float  # σ at the node closest to the junction radius (CAO σ_ref)


def fillet_surface_stress(
    mesh: SectorMesh2D,
    profile: ToothProfile,
    *,
    load_n: float = 100.0,
    e_mpa: float = 3200.0,
    nu: float = 0.35,
    fillet_limit_radius_mm: float | None = None,
) -> FilletSurfaceStress:
    """Surface σ1 along the LOADED (tensile) side root fillet — the CAO growth input.

    Returns the fillet-band surface nodes of the +0.5-pitch tooth's loaded-flank gap
    (phi ∈ (0.5, 1)), rotated into the tooth frame (+y = loaded tooth centre) and MIRRORED
    onto the right half (the loaded gap lies CCW of the tooth, x < 0 after rotation; the
    tooth is mirror-symmetric) so they overlay the strategies' right-half fillet polyline.
    """
    pts = mesh.points
    pitch = 2.0 * math.pi / profile.z
    phi = (np.arctan2(pts[:, 1], pts[:, 0]) - math.pi / 2.0) / pitch
    radii = np.hypot(pts[:, 0], pts[:, 1])
    kinds = np.asarray(mesh.kind)
    s1 = _tip_load_stress(mesh, profile, load_n=load_n, e_mpa=e_mpa, nu=nu)
    r_limit = profile.d_Ff / 2.0 if fillet_limit_radius_mm is None else fillet_limit_radius_mm
    mask = (kinds == "surface") & (phi > 0.5) & (phi < 1.0) & (radii < r_limit + 1e-6)
    idx = np.where(mask)[0]
    if len(idx) < 4:
        raise ValueError("fillet surface stress: too few tensile-side fillet nodes")
    # rotate the loaded tooth (centre at +0.5 pitch) onto +y — the strategies' tooth frame
    c, s = math.cos(-0.5 * pitch), math.sin(-0.5 * pitch)
    xy = np.stack([-(c * pts[idx, 0] - s * pts[idx, 1]), s * pts[idx, 0] + c * pts[idx, 1]], axis=1)
    junction = int(np.argmin(np.abs(np.hypot(xy[:, 0], xy[:, 1]) - r_limit)))
    return FilletSurfaceStress(
        xy_tooth=xy,
        sigma1_mpa=s1[idx],
        sigma_junction_mpa=float(s1[idx][junction]),
    )


@dataclass(frozen=True)
class ConvergenceResult:
    """Density sweep of one refinement group: stress per level + first converged level."""

    target: str
    levels: list[int]
    sigma_mpa: list[float]
    relative_change: list[float]  # vs previous level, starting at level[1]
    converged_level: int | None


def density_convergence(
    profile: ToothProfile,
    *,
    target: str = "root",
    levels: tuple[int, ...] = (1, 2, 3),
    tol: float = 0.02,
    bore_radius_mm: float | None = None,
) -> ConvergenceResult:
    """Sweep ONE density group (root or flank) and report the first converged level.

    Root and flank stay separate by design (plan v2): the swept group refines, the other stays
    at the reference density. Convergence = relative σ_max change below ``tol``.
    """
    if target not in ("root", "flank"):
        raise ValueError(f"unknown convergence target: {target}")
    sigmas: list[float] = []
    for level in levels:
        mesh = generate_sector_2d(
            profile,
            bore_radius_mm=bore_radius_mm,
            refine_root=level if target == "root" else 1,
            refine_flank=level if target == "flank" else 1,
        )
        sigmas.append(root_tensile_stress(mesh, profile).sigma_max_mpa)
    changes = [abs(b - a) / max(abs(b), 1e-12) for a, b in zip(sigmas, sigmas[1:], strict=False)]
    converged = next(
        (levels[i] for i, change in enumerate(changes) if change < tol),
        None,
    )
    return ConvergenceResult(
        target=target,
        levels=list(levels),
        sigma_mpa=sigmas,
        relative_change=changes,
        converged_level=converged,
    )
