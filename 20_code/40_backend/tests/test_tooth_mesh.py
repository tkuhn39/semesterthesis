"""
@module: tests.test_tooth_mesh
@context: Domain-layer tests — FE rolling model, the structured tooth mesh.
@role: The native tooth mesher turns the STplus involute flank into a clean
       structured quad mesh: right node/element counts, no inverted/degenerate
       cells, bounded aspect ratio, the radius range d_Ff…d_Na, and the flanks as
       exact boundaries — the foundation of the C3D8R toothing mesh.
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


def test_mesh_counts_and_no_inversion() -> None:
    """radial × circumferential cells, a full node grid, all cells positively oriented."""
    mesh = tooth_sector_2d(_profile(), radial=20, circumferential=10)
    assert mesh.n_nodes == 21 * 11
    assert mesh.n_quads == 20 * 10
    areas = mesh.element_areas()
    assert np.all(areas > 0.0)  # no inverted or degenerate quad


def test_mesh_quality_and_radius_range() -> None:
    """FE-usable shape (bounded aspect) spanning the involute flank d_Ff … d_Na."""
    profile = _profile()
    mesh = tooth_sector_2d(profile, radial=20, circumferential=10, root_bias=1.5)
    assert mesh.aspect_ratios().max() < 20.0
    r = mesh.radii()
    assert r.min() == pytest.approx(profile.d_Ff / 2.0, abs=1e-3)
    assert r.max() == pytest.approx(profile.d_Na / 2.0, abs=1e-3)


def test_flanks_are_exact_boundaries() -> None:
    """The j=0/j=last columns sit on the (mirrored) involute flank, centred on +y."""
    profile = _profile()
    n_c = 10
    mesh = tooth_sector_2d(profile, radial=20, circumferential=n_c)
    grid = mesh.nodes.reshape(21, n_c + 1, 2)
    # symmetry about the +y axis (left flank mirrors the right)
    assert np.allclose(grid[:, 0, 0], -grid[:, -1, 0], atol=1e-9)
    assert np.allclose(grid[:, 0, 1], grid[:, -1, 1], atol=1e-9)
    # the right boundary matches the analytic flank thickness at each radius
    flank = {round(float(np.hypot(p[0], p[1])), 4): p for p in profile.flank_points(400)}
    for node in grid[:, -1]:
        radius = round(float(np.hypot(node[0], node[1])), 4)
        match = min(flank, key=lambda r: abs(r - radius))
        assert node[0] == pytest.approx(flank[match][0], abs=0.02)


def test_root_bias_refines_the_base() -> None:
    """A larger root bias makes the first radial row thinner (finer at the root form)."""
    profile = _profile()
    thin = tooth_sector_2d(profile, radial=20, circumferential=4, root_bias=2.0)
    flat = tooth_sector_2d(profile, radial=20, circumferential=4, root_bias=1.0)
    row_thin = thin.radii().reshape(21, 5)[1, 0] - thin.radii().reshape(21, 5)[0, 0]
    row_flat = flat.radii().reshape(21, 5)[1, 0] - flat.radii().reshape(21, 5)[0, 0]
    assert row_thin < row_flat
