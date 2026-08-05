"""
@module: app.services.model.cao_fillet
@context: Model layer — biological (CAO) root-fillet growth per Kassem et al. 2023.
@role: Direct-method Computer Aided Optimization of the tooth-root contour (Mattheck
       growth rule, Kassem et al. 2023, Proc IMechE C 238(7), Eqs. 1–3): iterate
       quick-2D-FE surface stress → normal growth displacement
       d_i = s·(σ_i − σ_ref)·n_i with s = d_per/max|d_i| and d_per = 0.025·m_n, where
       σ_ref is the stress AT THE REFERENCE NODE between involute and fillet (which never
       moves) — material grows where σ > σ_ref and recedes where σ < σ_ref, until the
       surface stress is homogeneous. Caveat vs the paper: the objective here is the
       quick-FE single tip load (Method-C-like), not the full meshing cycle with the
       loaded mating gear — the optimum therefore differs in detail from Kassem's; the
       interference check still guards the final contour via the API layer.

Caching: results are memoized in-process per (profile fingerprint, parameters) — a pure
recompute on any other node (project_rules §18: no shared mutable state, no storage).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from app.io.ste import Pair
from app.services.geometry.root_fillet import PointsFillet
from app.services.geometry.tooth_form import ToothProfile
from app.services.model.plane_fe import fillet_surface_stress
from app.services.model.template_mesher import generate_sector_2d

__all__ = ["CaoFillet", "CaoResult", "optimize_cao_fillet"]


@dataclass(frozen=True)
class CaoResult:
    """One converged (or budget-capped) CAO growth run."""

    points: tuple[tuple[float, float], ...]  # tooth frame, gap side → junction
    sigma_history_mpa: tuple[float, ...]  # max fillet σ1 per iteration (incl. start)
    uniformity_history: tuple[float, ...]  # (σ_max − σ_ref)/σ_ref per iteration
    converged: bool
    iterations_run: int


def _fingerprint(profile: ToothProfile) -> tuple[float, ...]:
    return (
        profile.mn,
        float(profile.z),
        profile.alpha,
        profile.x_e,
        profile.h_aP0,
        profile.rho_aP0,
        profile.d_b,
        profile.d_Ff,
        profile.d_Na,
        profile.rho_F,
        profile.d_a if profile.d_a is not None else -1.0,
        profile.c_aa,
        profile.d_Ca if profile.d_Ca is not None else -1.0,
    )


_CACHE: dict[tuple, CaoResult] = {}
_CACHE_MAX = 32


def _start_polyline(profile: ToothProfile, points: int) -> np.ndarray:
    """The standard ρ_F-arc fillet as the growth start design (ascending radius)."""
    boundary = profile.transverse_right_boundary(fillet_points=points, flank_points=8)
    r_limit = profile.d_Ff / 2.0 + 1e-6
    pts = [(p[0], p[1]) for p in boundary if math.hypot(p[0], p[1]) <= r_limit]
    if len(pts) < 8:
        raise ValueError("cao fillet: degenerate start fillet")
    return np.asarray(pts)


def optimize_cao_fillet(
    profile: ToothProfile,
    *,
    step: float = 1.0,
    iterations: int = 12,
    tol: float = 0.02,
    points: int = 60,
) -> CaoResult:
    """Run (or reuse) the CAO growth loop for this profile; ~0.5–1 s per iteration."""
    key = (_fingerprint(profile), round(step, 6), int(iterations), round(tol, 8), int(points))
    hit = _CACHE.get(key)
    if hit is not None:
        return hit

    pts = _start_polyline(profile, points)
    d_per = 0.025 * profile.mn * step  # Kassem Eq. (3), scaled by the user step
    sigma_hist: list[float] = []
    uni_hist: list[float] = []
    converged = False
    iterations_run = 0
    for _ in range(iterations):
        iterations_run += 1
        r_j = float(math.hypot(pts[-1][0], pts[-1][1]))
        mesh = generate_sector_2d(profile, fillet=PointsFillet(tuple(map(tuple, pts))))
        fss = fillet_surface_stress(mesh, profile, fillet_limit_radius_mm=r_j)
        # map each polyline point to its nearest surface node (mesher reprojects onto us)
        d2 = ((pts[:, None, :] - fss.xy_tooth[None, :, :]) ** 2).sum(-1)
        sig = fss.sigma1_mpa[np.argmin(d2, axis=1)]
        sig_ref = fss.sigma_junction_mpa
        sigma_hist.append(float(sig.max()))
        uni = float((sig.max() - sig_ref) / max(abs(sig_ref), 1e-9))
        uni_hist.append(uni)
        if uni < tol:
            converged = True
            break
        delta = sig - sig_ref  # Kassem Eq. (1): grow where σ > σ_ref, recede below
        d_max = float(np.abs(delta).max())
        if d_max < 1e-12:
            converged = True
            break
        d = d_per * delta / d_max  # Eq. (2): the largest step is exactly d_per
        d[-1] = 0.0  # the reference node never moves (paper, Fig. 6)
        d[1:-1] = (d[:-2] + d[1:-1] + d[2:]) / 3.0  # light smoothing against node noise
        tang = np.gradient(pts, axis=0)
        normal = np.stack([tang[:, 1], -tang[:, 0]], axis=1)  # rot −90°: points into the void
        norm = np.maximum(np.hypot(normal[:, 0], normal[:, 1]), 1e-12)
        pts = pts + (d / norm)[:, None] * normal
        # re-sample by arc length so the growth does not bunch the polyline
        seg = np.hypot(np.diff(pts[:, 0]), np.diff(pts[:, 1]))
        arc = np.concatenate([[0.0], np.cumsum(seg)])
        s_new = np.linspace(0.0, arc[-1], len(pts))
        pts = np.stack([np.interp(s_new, arc, pts[:, 0]), np.interp(s_new, arc, pts[:, 1])], axis=1)

    result = CaoResult(
        points=tuple(map(tuple, pts)),
        sigma_history_mpa=tuple(sigma_hist),
        uniformity_history=tuple(uni_hist),
        converged=converged,
        iterations_run=iterations_run,
    )
    if len(_CACHE) >= _CACHE_MAX:
        _CACHE.clear()
    _CACHE[key] = result
    return result


@dataclass(frozen=True)
class CaoFillet:
    """Lazy CAO strategy: ``right_half`` runs (or reuses) the cached growth loop."""

    cao_step: float = 1.0
    cao_iterations: int = 12
    cao_tol: float = 0.02
    points: int = 60

    def result(self, profile: ToothProfile) -> CaoResult:
        return optimize_cao_fillet(
            profile,
            step=self.cao_step,
            iterations=self.cao_iterations,
            tol=self.cao_tol,
            points=self.points,
        )

    def junction_radius_mm(self, profile: ToothProfile) -> float:
        last = self.result(profile).points[-1]
        return math.hypot(last[0], last[1])

    def right_half(self, profile: ToothProfile) -> list[Pair[float]]:
        return [Pair(x, y) for x, y in self.result(profile).points]
