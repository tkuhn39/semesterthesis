"""
@module: tests.test_tooth_mesh
@context: Domain-layer tests — FE rolling model, the structured tooth mesh.
@role: The native tooth mesher turns the STplus involute flank (+ root fillet) into a
       clean structured quad mesh: the FVA-377 element counts, no inverted/degenerate
       cells, bounded aspect ratio, the radius range, and the flanks as exact
       boundaries — the foundation of the C3D8R toothing mesh.
"""

import numpy as np
import pytest

from app.io.ste import Pair
from app.services.geometry.gear import GearStage, ToolReferenceProfile
from app.services.geometry.tooth_form import ToothProfile
from app.services.model.tooth_mesh import tooth_sector_2d


def _profile(index: int = 0) -> ToothProfile:
    tool = ToolReferenceProfile(addendum_factor=1.25, tip_radius_factor=0.38)
    stage = GearStage.from_parameters(
        normal_module_mm=2.0,
        teeth=Pair(24, 60),
        profile_shift=Pair(0.3, 0.1),
        face_width_mm=Pair(20.0, 20.0),
        tool=Pair(tool, tool),
    )
    return ToothProfile.from_stage(stage, index)


def test_counts_match_fva377_parameters() -> None:
    """height × thickness (+ root × thickness) cells; a full node grid; positive cells."""
    mesh = tooth_sector_2d(_profile(), height_elements=12, root_elements=5, thickness_elements=5)
    assert mesh.n_quads == (12 + 5) * 5
    assert mesh.n_nodes == (12 + 5 + 1) * (5 + 1)
    assert np.all(mesh.element_areas() > 0.0)  # no inverted / degenerate quad


def test_tooth_proper_quality_and_radius_range() -> None:
    """Without the fillet: FE-usable shape over the involute flank d_Ff … d_Na."""
    profile = _profile()
    mesh = tooth_sector_2d(profile, height_elements=12, thickness_elements=5, include_fillet=False)
    assert mesh.n_quads == 12 * 5
    assert mesh.aspect_ratios().max() < 15.0
    r = mesh.radii()
    assert r.min() == pytest.approx(profile.d_Ff / 2.0, abs=1e-3)
    assert r.max() == pytest.approx(profile.d_Na / 2.0, abs=1e-3)


def test_fillet_reaches_the_root_circle() -> None:
    """With the fillet the mesh extends down to the root circle d_f (the 30°-tangent zone)."""
    profile = _profile()
    mesh = tooth_sector_2d(profile, height_elements=12, root_elements=5, thickness_elements=5)
    assert mesh.radii().min() == pytest.approx(profile.root_diameter_mm / 2.0, abs=2e-2)
    assert np.all(mesh.element_areas() > 0.0)


def test_flanks_are_exact_boundaries() -> None:
    """The j=0/j=last columns sit on the (mirrored) involute flank, centred on +y."""
    profile = _profile()
    n_c = 5
    mesh = tooth_sector_2d(
        profile, height_elements=12, thickness_elements=n_c, include_fillet=False
    )
    grid = mesh.nodes.reshape(13, n_c + 1, 2)
    assert np.allclose(grid[:, 0, 0], -grid[:, -1, 0], atol=1e-9)  # left mirrors right
    assert np.allclose(grid[:, 0, 1], grid[:, -1, 1], atol=1e-9)
    flank = {round(float(np.hypot(p[0], p[1])), 4): p for p in profile.flank_points(400)}
    for node in grid[:, -1]:
        match = min(flank, key=lambda r: abs(r - float(np.hypot(node[0], node[1]))))
        assert node[0] == pytest.approx(flank[match][0], abs=0.02)
