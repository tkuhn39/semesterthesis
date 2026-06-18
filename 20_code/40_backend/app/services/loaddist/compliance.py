"""
@module: app.services.loaddist.compliance
@context: Domain layer — RIKOR (FVA 30) load distribution, the compliance matrix.
@role: Assemble the influence-number (compliance) matrix δ of the loaded tooth
       contact analysis (FVA 30 XI §2.12, eq. 2.12.16): δ = δ^W + δ^Z + δ^H, the
       deflection at face support point i per unit force at j. This module builds
       the **source-independent** blocks:
         • δ^W — shaft/bearing: bending (unit-load columns through the native
           `beam.py`) plus the torsional wind-up (analytic, with the equivalent
           torsion diameter d_T) of both shafts, in the line of action;
         • the **local** mesh compliance 1/c_γ on the diagonal — a placeholder for
           δ^Z (tooth, Weber–Banaschek) + δ^H (Hertz) without the gear-body
           cross-influence (FVA-AB T309), which slots into the off-diagonals later.
       Units: force [N], deflection [mm]; the matrix is symmetric (Maxwell–Betti).
"""

import math

import numpy as np
from numpy.typing import NDArray

from app.io.rie import Bearing, Gear, RikorInput, Shaft
from app.io.ste import Pair
from app.services.loaddist.beam import BeamModel
from app.services.loaddist.forces import evaluate_mesh

Array = NDArray[np.float64]

_E_STEEL_MPA = 210000.0
_POISSON = 0.3
_G_STEEL = _E_STEEL_MPA / (2.0 * (1.0 + _POISSON))
_SHEAR_KAPPA = 6.0 * (1.0 + _POISSON) / (7.0 + 6.0 * _POISSON)


def _sorted_stations(shaft: Shaft) -> list:
    return sorted(shaft.stations, key=lambda s: s.position_mm)


def _diameter_at(stations: list, position: float, *, inner: bool = False) -> float:
    value = 0.0
    for s in stations:
        if s.position_mm <= position:
            value = s.inner_diameter_mm if inner else s.outer_diameter_mm
    return value


def _shaft_beam(shaft: Shaft, gear: Gear, bearings: list[Bearing], face_x: Array) -> BeamModel:
    """A Timoshenko beam for the shaft with nodes at the stations, bearings and face grid."""
    stations = _sorted_stations(shaft)
    nodes = np.array(
        sorted(
            {s.position_mm for s in stations}
            | {b.position_mm for b in bearings if b.position_mm is not None}
            | set(face_x.tolist())
        )
    )
    ei = np.empty(nodes.size - 1)
    ga = np.empty(nodes.size - 1)
    for e in range(nodes.size - 1):
        mid = 0.5 * (nodes[e] + nodes[e + 1])
        d_o = _diameter_at(stations, mid)
        d_i = _diameter_at(stations, mid, inner=True)
        area = math.pi / 4.0 * max(d_o**2 - d_i**2, 1.0)
        inertia = math.pi / 64.0 * max(d_o**4 - d_i**4, 1.0e3)
        ei[e] = _E_STEEL_MPA * inertia
        ga[e] = _G_STEEL * _SHEAR_KAPPA * area
    beam = BeamModel(nodes, ei, ga)
    for b in bearings:
        if b.position_mm is not None and b.radial_stiffness_n_per_um is not None:
            beam.add_support(b.position_mm, b.radial_stiffness_n_per_um)
    return beam


def _bending_compliance(beam: BeamModel, face_x: Array) -> Array:
    """δ_bend[i,j] = deflection at face_x[i] from a unit point load at face_x[j] (mm/N)."""
    n = face_x.size
    out = np.empty((n, n))
    for j in range(n):
        unit = BeamModel(beam.x, beam.ei, beam.ga)
        unit.k = beam.k.copy()  # reuse the assembled stiffness (supports included)
        unit.add_point_load(face_x[j], 1.0)
        out[:, j] = unit.deflection_at(face_x)
    return 0.5 * (out + out.T)  # enforce symmetry (Maxwell–Betti)


def _torsion_compliance(
    shaft: Shaft, gear: Gear, base_radius_mm: float, torsion_diameter_mm: float, face_x: Array
) -> Array:
    """δ_tors[i,j] = r_b²·min(s_i,s_j)/(G·J_T), s = |x − x_ref| from the torque reaction.

    A unit tangential load at j applies a torque r_b about the axis, reacted at the
    drive/output coupling; the shaft twist tilts the flank by r_b·φ. The twist shared
    between i and j is the common torque path length min(s_i, s_j).
    """
    stations = _sorted_stations(shaft)
    x_ref = next((s.position_mm for s in stations if s.applied_torque_nm is not None), face_x[0])
    s = np.abs(face_x - x_ref)
    j_t = math.pi / 32.0 * torsion_diameter_mm**4
    coeff = base_radius_mm**2 / (_G_STEEL * j_t)
    return coeff * np.minimum.outer(s, s)


def shaft_compliance(ri: RikorInput, *, points: int | None = None) -> tuple[Array, Array]:
    """The shaft/bearing compliance δ^W (mm/N) over the common face width.

    Sums the bending (unit-load) and torsion compliance of both meshing shafts; the
    returned face coordinate runs 0…b_common.
    """
    mesh = evaluate_mesh(ri)
    stage = mesh.stage
    n = points or (ri.stage.face_steps if ri.stage and ri.stage.face_steps else 30)
    width = stage.face_width_mm or Pair(0.0, 0.0)
    common = min(w for w in width if w > 0.0)
    face = np.linspace(0.0, common, n)

    from app.services.loaddist.forces import _drive_then_driven

    gears = _drive_then_driven(ri)
    delta = np.zeros((n, n))
    mn = stage.normal_module_mm
    for index, gear in enumerate(gears):
        shaft = next(s for s in ri.shafts if s.index == gear.shaft_index)
        bearings = ri.bearings_on(gear.shaft_index)
        g0 = gear.axial_position_mm or 0.0
        face_x = g0 + face
        beam = _shaft_beam(shaft, gear, bearings, face_x)
        delta += _bending_compliance(beam, face_x)
        r_b = stage.base_diameter_mm[index] / 2.0
        d_ref = stage.reference_diameter_mm[index]
        h_a0 = gear.addendum_factor or 1.0
        d_t = d_ref - mn * h_a0  # equivalent torsion diameter (derived; ≈ RIKOR d_T)
        delta += _torsion_compliance(shaft, gear, r_b, d_t, face_x)
    return delta, face


def local_mesh_compliance(c_gamma_n_um_mm: float, widths_mm: Array) -> Array:
    """Diagonal local compliance 1/c_γ (mm/N) per support — the δ^Z(diag)+δ^H placeholder.

    A point force F over the support width Δb gives a line load w = F/Δb and a local
    deflection w/c_γ [µm]; per unit force the compliance is 1/(c_γ·Δb·1000) [mm/N].
    """
    return np.diag(1.0 / (c_gamma_n_um_mm * widths_mm * 1000.0))


def support_widths(face: Array) -> Array:
    """Tributary width Δb of each support point (trapezoidal)."""
    edges = np.empty(face.size + 1)
    edges[1:-1] = 0.5 * (face[:-1] + face[1:])
    edges[0] = face[0]
    edges[-1] = face[-1]
    return np.diff(edges)
