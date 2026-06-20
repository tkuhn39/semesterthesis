"""
@module: tests.test_gmsh_mesher
@context: Domain-layer tests — FE rolling model, the gmsh tooth/rim mesher.
@role: gmsh meshes the STplus tooth+rim outline into clean quads and extrudes them to
       C3D8 hexahedra: the fillet is resolved without inverted cells, and the hex mesh
       is FE-quality by the scaled Jacobian (the FVA "Jacobi-Güte") over the face width.
"""

import numpy as np
import pytest

from app.io.ste import Pair
from app.services.geometry.gear import GearStage, ToolReferenceProfile
from app.services.geometry.tooth_form import ToothProfile
from app.services.model.gmsh_mesher import mesh_tooth_pitch, mesh_tooth_pitch_3d


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


def test_pitch_2d_quads_resolve_the_fillet() -> None:
    """The 2-D pitch meshes to quads spanning the tooth down to the root circle."""
    profile = _profile()
    mesh = mesh_tooth_pitch(profile, height_elements=10, root_elements=12, thickness_elements=4)
    assert mesh.n_quads > 100
    r = mesh.radii()
    assert r.min() < profile.root_diameter_mm / 2.0 + 0.1  # reaches the root/rim
    assert r.max() == pytest.approx(profile.d_Na / 2.0, abs=0.05)  # the tip


def test_pitch_3d_hex_quality_and_extrusion() -> None:
    """Extrusion gives C3D8 hexes over the face width, FE-quality by the Jacobi-Güte."""
    mesh = mesh_tooth_pitch_3d(
        _profile(),
        face_width_mm=20.0,
        face_layers=8,
        height_elements=10,
        root_elements=12,
        thickness_elements=4,
    )
    assert mesh.n_hexes > 800
    assert mesh.hexes.shape[1] == 8
    z = mesh.nodes[:, 2]
    assert z.min() == pytest.approx(0.0, abs=1e-6)
    assert z.max() == pytest.approx(20.0, abs=1e-6)
    assert mesh.quality is not None
    assert np.all(mesh.quality > 0.0)  # no inverted hexes (positive scaled Jacobian)
    assert np.median(mesh.quality) > 0.7  # FVA Jacobi-Güte target ≥ 0.35, comfortably met
