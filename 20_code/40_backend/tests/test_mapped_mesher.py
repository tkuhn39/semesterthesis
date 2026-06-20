"""
@module: tests.test_mapped_mesher
@context: Domain-layer tests — FE rolling model, the structured (transfinite) mesher.
@role: The mapped mesher partitions one pitch into 5 transfinite blocks and meshes them
       structured with the FVA element counts as seeds — clean quads that meet the FVA
       Jacobi-Güte ≥ 0.35 target, swept to C3D8 hexahedra.
"""

import numpy as np
import pytest

from app.io.ste import Pair
from app.services.geometry.gear import GearStage, ToolReferenceProfile
from app.services.geometry.tooth_form import ToothProfile
from app.services.model.mapped_mesher import mesh_pitch_mapped_2d, mesh_pitch_mapped_3d


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


def test_mapped_2d_block_counts_and_jacobi() -> None:
    """5 transfinite blocks → the seeded quad count; Jacobi-Güte well above the 0.35 target."""
    h, r, t, rim, g = 12, 10, 5, 6, 6
    mesh, quality = mesh_pitch_mapped_2d(
        _profile(),
        height_elements=h,
        root_elements=r,
        thickness_elements=t,
        rim_elements=rim,
        gap_elements=g,
    )
    assert mesh.n_quads == (h + r + rim) * t + 2 * rim * g
    assert quality.min() >= 0.35  # the FVA "Sollvorgabe Jacobi-Güte"
    assert np.median(quality) > 0.9


def test_mapped_2d_enforces_jacobi_target() -> None:
    """An impossible target is rejected (the Jacobi-Güte guard)."""
    with pytest.raises(ValueError, match="Jacobi"):
        mesh_pitch_mapped_2d(_profile(), min_jacobi=0.999)


def test_mapped_3d_sweep_quality() -> None:
    """Sweeping to C3D8 keeps the structure and the Jacobi-Güte over the face width."""
    mesh = mesh_pitch_mapped_3d(
        _profile(),
        face_width_mm=20.0,
        face_layers=10,
        height_elements=12,
        root_elements=10,
        thickness_elements=5,
    )
    assert mesh.hexes.shape[1] == 8
    assert mesh.quality is not None and mesh.quality.min() >= 0.35
    assert mesh.nodes[:, 2].max() == pytest.approx(20.0)
