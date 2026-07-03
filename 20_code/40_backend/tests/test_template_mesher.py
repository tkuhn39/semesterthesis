"""
@module: tests.test_template_mesher
@context: Domain-layer tests — reference-topology gear-sector mesher (ADR-019).
@role: The generated kst-E wheel sector is topology-identical to the ANSA/FVA reference,
       meets the MESHING_SPEC quality gates, and is exactly tooth-congruent and (for the
       symmetric .ste input) mirror-symmetric within each tooth.
"""

import math
from pathlib import Path
from typing import cast

import numpy as np
import pytest
from scipy.spatial import cKDTree

from app.io.ste import gear_stage_from_ste, load_ste
from app.services.geometry.gear import GearStage
from app.services.geometry.tooth_form import ToothProfile
from app.services.model.reference_slice import Quad, load_reference_template, measure
from app.services.model.template_mesher import (
    SectorMesh2D,
    generate_sector_2d,
    scaled_jacobians,
)

_REF_STE = (
    Path(__file__).resolve().parents[3]
    / "30_references_and_examples"
    / "33_STplus"
    / "kst-E_eingabe.ste"
)

pytestmark = pytest.mark.skipif(not _REF_STE.exists(), reason="STplus reference .ste not present")


@pytest.fixture(scope="module")
def wheel_mesh() -> tuple[ToothProfile, SectorMesh2D]:
    stage = GearStage.from_ste(gear_stage_from_ste(load_ste(_REF_STE)))
    profile = ToothProfile.from_stage(stage, 1)  # wheel z=52 (plastic side)
    template = load_reference_template()
    mesh = generate_sector_2d(profile, bore_radius_mm=float(template.meta["bore_radius_mm"]))
    return profile, mesh


def test_topology_matches_reference(wheel_mesh: tuple[ToothProfile, SectorMesh2D]) -> None:
    """Same quad count and the reference's exact irregular-node signature."""
    _, mesh = wheel_mesh
    coords = {i: (c[0], c[1]) for i, c in enumerate(mesh.coords)}
    metrics = measure(cast("list[Quad]", mesh.quads), coords)
    assert metrics.n_quads == 3024
    assert metrics.interior_valence == {4: 2716, 5: 2, 6: 3}


def test_quality_gates(wheel_mesh: tuple[ToothProfile, SectorMesh2D]) -> None:
    """MESHING_SPEC §3: det(J)min ≥ 0.35 with zero cells below (better than the reference)."""
    _, mesh = wheel_mesh
    sj = scaled_jacobians(mesh.coords, mesh.quads)
    assert float(sj.min()) >= 0.35
    assert int((sj < 0.35).sum()) == 0
    # Root band (the thesis-critical fillet region) is comfortably above the gate.
    pts = mesh.points
    r_f = 24.7616
    radii = np.hypot(pts[:, 0], pts[:, 1])
    band = (radii > r_f - 1.2) & (radii < r_f + 1.2)
    in_band = np.array([band[list(q)].any() for q in mesh.quads])
    assert float(sj[in_band].min()) >= 0.5


def test_teeth_exactly_congruent(wheel_mesh: tuple[ToothProfile, SectorMesh2D]) -> None:
    """Every tooth is a pure rotation of the base tooth (MESHING_SPEC §6, user requirement)."""
    profile, mesh = wheel_mesh
    pts = mesh.points
    pitch = 2.0 * math.pi / profile.z
    phi = (np.arctan2(pts[:, 1], pts[:, 0]) - math.pi / 2.0) / pitch
    base = pts[(phi >= 0.001) & (phi <= 0.999)]
    tree = cKDTree(base)
    for k in (-2, -1, 1):
        seg = pts[(phi >= k + 0.001) & (phi <= k + 0.999)]
        ang = -k * pitch
        c, s = math.cos(ang), math.sin(ang)
        moved = seg @ np.array([[c, s], [-s, c]])
        dist, _ = tree.query(moved)
        assert len(seg) == len(base)
        assert float(dist.max()) < 1e-9


def test_base_tooth_mirror_symmetric(wheel_mesh: tuple[ToothProfile, SectorMesh2D]) -> None:
    """Symmetric input parameters (is_flank_symmetric) → exact in-tooth mirror symmetry."""
    profile, mesh = wheel_mesh
    assert profile.is_flank_symmetric()
    pts = mesh.points
    pitch = 2.0 * math.pi / profile.z
    phi = (np.arctan2(pts[:, 1], pts[:, 0]) - math.pi / 2.0) / pitch
    base = pts[(phi >= 0.001) & (phi <= 0.999)]
    axis = math.pi / 2.0 + 0.5 * pitch
    normal = np.array([-math.sin(axis), math.cos(axis)])
    mirrored = base - 2.0 * np.outer(base @ normal, normal)
    dist, _ = cKDTree(base).query(mirrored)
    assert float(dist.max()) < 1e-9
