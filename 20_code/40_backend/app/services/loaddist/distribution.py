"""
@module: app.services.loaddist.distribution
@context: Domain layer — RIKOR (FVA 30) load distribution, the LTCA solver (R3).
@role: Solve the loaded tooth contact analysis for the line-load distribution w(b)
       over the face width and the face load factor K_Hβ. Given the total compliance
       matrix δ (`compliance.py`) and the initial misalignment f_app, find the support
       forces F and the common approach λ from the elastic compatibility
       δ·F + f_app = λ·1 with Σ F = F_n, dropping supports that lose contact
       (F_j < 0) and re-solving (FVA 30 XI §2.12.4). Then K_Hβ = w_max/w̄.

Scaffolding state: uses δ^W (shaft) + the diagonal local mesh compliance 1/c_γ. The
gear-body cross-influence δ^Z (Weber–Banaschek / FVA-AB T309) slots into δ later for
a bit-exact K_Hβ; the solver and δ^W are final.
"""

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel

from app.io.rie import RikorInput
from app.io.ste import Pair
from app.services.capacity.iso6336_dynamics import face_load_factor_root
from app.services.loaddist.compliance import (
    local_mesh_compliance,
    shaft_compliance,
    support_widths,
)
from app.services.loaddist.forces import evaluate_mesh

Array = NDArray[np.float64]


class LoadDistribution(BaseModel):
    """The solved face load distribution and the resulting factors."""

    face_mm: list[float]
    line_load_n_per_mm: list[float]  # w(b)
    mean_line_load_n_per_mm: float  # F_bt/b
    face_load_factor_flank: float  # K_Hβ = w_max / w̄
    face_load_factor_root: float  # K_Fβ
    equivalent_misalignment_um: float  # f_βx (peak gap of the uniform-load deflection)
    correction_um: list[float]  # Gesamtkorrektur g(b) (uniform-load deflection, referenced)


def solve_contact(delta: Array, misalignment_mm: Array, total_force_n: float) -> Array:
    """Solve δ·F + f_app = λ·1, Σ F = F_total with non-negative forces (contact loss).

    Returns the support forces F (N). Supports that would pull (F < 0) are released and
    the reduced system re-solved until all active forces are non-negative.
    """
    n = delta.shape[0]
    active = np.ones(n, dtype=bool)
    forces = np.zeros(n)
    for _ in range(n):
        idx = np.flatnonzero(active)
        m = idx.size
        # [δ_aa  -1; 1ᵀ 0] [F_a; λ] = [-f_app_a; F_total]
        system = np.zeros((m + 1, m + 1))
        system[:m, :m] = delta[np.ix_(idx, idx)]
        system[:m, m] = -1.0
        system[m, :m] = 1.0
        rhs = np.empty(m + 1)
        rhs[:m] = -misalignment_mm[idx]
        rhs[m] = total_force_n
        sol = np.linalg.solve(system, rhs)
        f_a = sol[:m]
        if np.all(f_a >= -1e-9):
            forces[:] = 0.0
            forces[idx] = np.maximum(f_a, 0.0)
            return forces
        active[idx[np.argmin(f_a)]] = False  # release the most negative, retry
    return forces


def evaluate_load_distribution(
    ri: RikorInput, *, points: int | None = None, misalignment_um: Array | None = None
) -> LoadDistribution:
    """Solve the LTCA for a RIKOR input → w(b), K_Hβ, K_Fβ and the correction."""
    mesh = evaluate_mesh(ri)
    delta_w, face = shaft_compliance(ri, points=points)
    widths = support_widths(face)
    delta = delta_w + local_mesh_compliance(mesh.stiffness.mesh_alpha, widths)

    f_app = (
        np.zeros(face.size)
        if misalignment_um is None
        else np.asarray(misalignment_um, float) / 1000.0
    )
    total = mesh.forces.tangential_force_n
    forces = solve_contact(delta, f_app, total)
    w = forces / widths
    w_mean = total / float(widths.sum())
    k_hb = float(w.max() / w_mean) if w_mean > 0 else 1.0

    # Gesamtkorrektur g(b): the correction for uniform load = max approach − approach,
    # i.e. material to add where the loaded flanks deflect *least* (the lightly loaded ends).
    uniform = total * widths / float(widths.sum())
    deflection_mm = delta_w @ uniform
    gap_um = 1000.0 * (deflection_mm.max() - deflection_mm)

    width_pair = mesh.stage.face_width_mm or Pair(1.0, 1.0)
    common = min(x for x in width_pair if x > 0.0)
    height = 2.25 * mesh.stage.normal_module_mm  # ~ tooth height for the K_Fβ ratio
    k_fb = face_load_factor_root(k_hb, common / height)
    return LoadDistribution(
        face_mm=[round(float(b), 3) for b in face],
        line_load_n_per_mm=[round(float(v), 2) for v in w],
        mean_line_load_n_per_mm=round(w_mean, 2),
        face_load_factor_flank=round(k_hb, 4),
        face_load_factor_root=round(k_fb, 4),
        equivalent_misalignment_um=round(float(gap_um.max()), 3),
        correction_um=[round(float(v), 3) for v in gap_um],
    )
