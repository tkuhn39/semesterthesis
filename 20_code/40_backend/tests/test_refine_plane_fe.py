"""
@module: tests.test_refine_plane_fe
@context: Domain-layer tests — parametric mesh density + native 2D quick solver (plan v2).
@role: Chord refinement keeps the reference topology signature, quality gates and exact tooth
       congruence at every density level; the plane-strain quick solver produces a physical
       root-stress result and the density convergence study confirms the reference density.
"""

import math
from pathlib import Path

import numpy as np
import pytest
from scipy.spatial import cKDTree

from app.io.ste import gear_stage_from_ste, load_ste
from app.services.geometry.gear import GearStage
from app.services.geometry.tooth_form import ToothProfile
from app.services.model.plane_fe import density_convergence, root_tensile_stress
from app.services.model.reference_slice import load_reference_template, measure
from app.services.model.template_mesher import generate_sector_2d, scaled_jacobians

_REF_STE = (
    Path(__file__).resolve().parents[3]
    / "30_references_and_examples"
    / "33_STplus"
    / "kst-E_eingabe.ste"
)

pytestmark = pytest.mark.skipif(not _REF_STE.exists(), reason="STplus reference .ste not present")


@pytest.fixture(scope="module")
def wheel() -> ToothProfile:
    stage = GearStage.from_ste(gear_stage_from_ste(load_ste(_REF_STE)))
    return ToothProfile.from_stage(stage, 1)


@pytest.fixture(scope="module")
def bore() -> float:
    return float(load_reference_template().meta["bore_radius_mm"])


def test_refinement_keeps_structure_and_gates(wheel: ToothProfile, bore: float) -> None:
    """Density levels stay conformal all-quad with the reference irregular-node signature."""
    mesh = generate_sector_2d(wheel, bore_radius_mm=bore, refine_root=2, refine_flank=2)
    assert mesh.meta["n_quads"] > 5000  # actually refined
    coords = {i: (c[0], c[1]) for i, c in enumerate(mesh.coords)}
    metrics = measure(mesh.quads, coords)
    assert metrics.interior_valence[5] == 2
    assert metrics.interior_valence[6] == 3
    assert set(metrics.interior_valence) == {4, 5, 6}
    sj = scaled_jacobians(mesh.coords, mesh.quads)
    assert float(sj.min()) >= 0.35
    # Exact tooth congruence survives refinement.
    pts = mesh.points
    pitch = 2.0 * math.pi / wheel.z
    phi = (np.arctan2(pts[:, 1], pts[:, 0]) - math.pi / 2.0) / pitch
    base = pts[(phi >= 0.001) & (phi <= 0.999)]
    tree = cKDTree(base)
    for k in (-2, 1):
        seg = pts[(phi >= k + 0.001) & (phi <= k + 0.999)]
        ang = -k * pitch
        c, s = math.cos(ang), math.sin(ang)
        dist, _ = tree.query(seg @ np.array([[c, s], [-s, c]]))
        assert len(seg) == len(base)
        assert float(dist.max()) < 1e-9


def test_quick_solver_root_stress(wheel: ToothProfile, bore: float) -> None:
    """Physical result: tensile peak in the loaded tooth's fillet, solver runs sub-second."""
    mesh = generate_sector_2d(wheel, bore_radius_mm=bore)
    res = root_tensile_stress(mesh, wheel)
    assert res.sigma_max_mpa > 0.0
    pts = mesh.points
    r = math.hypot(pts[res.node][0], pts[res.node][1])
    assert r < wheel.d_Ff / 2.0 + 1e-6  # in the fillet region
    theta = math.degrees(math.atan2(pts[res.node][1], pts[res.node][0]))
    assert 90.0 < theta < 100.0  # loaded-side fillet of the +0.5-pitch tooth


def test_density_convergence_confirms_reference(wheel: ToothProfile, bore: float) -> None:
    """The mined reference density is already converged for the root stress (< 2 % change)."""
    conv = density_convergence(wheel, target="root", levels=(1, 2), bore_radius_mm=bore)
    assert conv.relative_change[0] < 0.02
    assert conv.converged_level == 1
