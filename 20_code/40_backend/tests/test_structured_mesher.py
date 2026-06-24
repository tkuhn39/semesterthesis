"""
@module: tests.test_structured_mesher
@context: Domain-layer tests — FE rolling model, native structured body-mesh building blocks.
@role: The reusable pieces toward the reference body mesh: the transfinite tooth section + its d_f
       interface extraction (`mapped_mesher.tooth_section_2d`), and the native all-quad coarsening
       body (`structured_mesher.body_section_2d`) — conformal, all-quad, grown from that interface.
"""

from collections import Counter

import numpy as np

from app.io.ste import Pair
from app.services.geometry.gear import GearStage, ToolReferenceProfile
from app.services.geometry.tooth_form import ToothProfile
from app.services.model.mapped_mesher import tooth_section_2d
from app.services.model.structured_mesher import body_section_2d, scaled_jacobian


def _profile(index: int = 1) -> ToothProfile:
    tool = ToolReferenceProfile(addendum_factor=1.25, tip_radius_factor=0.38)
    stage = GearStage.from_parameters(
        normal_module_mm=2.0,
        teeth=Pair(24, 60),
        profile_shift=Pair(0.3, 0.1),
        face_width_mm=Pair(20.0, 20.0),
        tool=Pair(tool, tool),
    )
    return ToothProfile.from_stage(stage, index)


def test_tooth_section_interface_ordered_and_quality() -> None:
    """Tooth+fillet (no rim) meshes to FE quality and exposes an ordered d_f base interface."""
    p = _profile()
    mesh, quality, base = tooth_section_2d(
        p, height_elements=8, root_elements=8, thickness_elements=14, flank_bias=0.18
    )
    assert len(base) == 15  # thickness_elements + 1
    angles = np.degrees(np.arctan2(mesh.nodes[base, 0], mesh.nodes[base, 1]))
    assert np.all(np.diff(angles) > 0)  # left → right
    radii = np.hypot(mesh.nodes[base, 0], mesh.nodes[base, 1])
    assert 2.0 * radii.min() < p.d_Ff  # interface sits at d_f, below the form circle d_Ff
    assert quality.min() >= 0.35  # FVA Jacobi-Güte


def test_body_section_is_all_quad_and_conformal() -> None:
    """The native body block (4→2 coarsening + ring) is all-quad and edge-conformal."""
    p = _profile()
    mesh, _, base = tooth_section_2d(p, height_elements=6, root_elements=6, thickness_elements=14)
    body, bore = body_section_2d(p, mesh.nodes[base], bore_radius_mm=10.0, n_gap=1, bore_columns=4)
    assert body.quads.shape[1] == 4  # all quads
    assert np.all(body.element_areas() != 0.0)  # no degenerate cells
    edges: Counter[frozenset[int]] = Counter()
    for quad in body.quads:
        for k in range(4):
            edges[frozenset((int(quad[k]), int(quad[(k + 1) % 4])))] += 1
    assert max(edges.values()) <= 2  # conformal: no edge shared by > 2 quads
    assert len(bore) >= 2 and scaled_jacobian(body).size == body.n_quads
