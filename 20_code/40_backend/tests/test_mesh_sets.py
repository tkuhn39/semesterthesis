"""
@module: tests.test_mesh_sets
@context: Domain-layer tests — FE rolling model, the mesh → assembly surface tagging.
@role: The structured sector's boundary is classified into the named surfaces the
       WoBe-892 deck needs — bore (Fesselung), radial cut faces, tip, and per-tooth
       per-side involute flanks (contact pairs) — each mapped to swept C3D8 side faces.
"""

import numpy as np

from app.io.ste import Pair
from app.services.geometry.gear import GearStage, ToolReferenceProfile
from app.services.geometry.tooth_form import ToothProfile
from app.services.model.mapped_mesher import mesh_sector_mapped_2d
from app.services.model.mesh_sets import tag_gear_reference, tag_sector_surfaces


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


def test_sector_surface_tags_match_seeds() -> None:
    n_teeth, n_seg, layers = 3, 1, 4
    h, t, rim = 12, 5, 6
    section, _ = mesh_sector_mapped_2d(
        _profile(),
        n_teeth=n_teeth,
        n_segments=n_seg,
        height_elements=h,
        root_elements=14,
        thickness_elements=t,
        rim_elements=rim,
        gap_elements=6,
    )
    surf = tag_sector_surfaces(
        section, profile=_profile(), n_teeth=n_teeth, n_segments=n_seg, layers=layers
    )

    # one flank surface per tooth and side, each = height_elements edges × layers swept faces
    for tooth in range(n_teeth):
        for side in ("L", "R"):
            name = f"FLANK_T{tooth}_{side}"
            assert name in surf.faces
            assert len(surf.faces[name]) == h * layers
    assert len(surf.faces["TIP"]) == n_teeth * t * layers  # tip land = thickness per tooth
    assert len(surf.faces["CUT"]) == 2 * rim * layers  # two radial sector edges
    assert "BORE" in surf.faces


def test_sector_faces_reference_valid_hexes() -> None:
    n_teeth, n_seg, layers = 2, 1, 3
    section, _ = mesh_sector_mapped_2d(
        _profile(), n_teeth=n_teeth, n_segments=n_seg, height_elements=10, root_elements=10
    )
    surf = tag_sector_surfaces(
        section, profile=_profile(), n_teeth=n_teeth, n_segments=n_seg, layers=layers
    )
    n_hexes = section.n_quads * layers
    for entries in surf.faces.values():
        for hex_index, face in entries:
            assert 0 <= hex_index < n_hexes
            assert face in {"S3", "S4", "S5", "S6"}
    # node sets index real nodes
    for nodes in surf.node_sets.values():
        assert nodes.min() >= 0 and nodes.max() < section.n_nodes
        assert np.array_equal(nodes, np.unique(nodes))


def test_reference_tags_name_every_tooth_flank_and_bore() -> None:
    """The reference tagging yields G{g}T{nnn}F{f} sets for both flanks of every tooth + a bore."""
    n_teeth, n_seg, layers = 3, 1, 4
    h, t, rim = 10, 5, 6
    section, _ = mesh_sector_mapped_2d(
        _profile(),
        n_teeth=n_teeth,
        n_segments=n_seg,
        height_elements=h,
        root_elements=12,
        thickness_elements=t,
        rim_elements=rim,
        gap_elements=6,
    )
    ref = tag_gear_reference(
        section, profile=_profile(), gear=1, n_teeth=n_teeth, n_segments=n_seg, layers=layers
    )

    n_3d_nodes = (layers + 1) * section.n_nodes
    n_3d_hexes = layers * section.n_quads
    assert ref.bore_nodes.size > 0
    assert ref.bore_nodes.min() >= 1 and ref.bore_nodes.max() <= n_3d_nodes
    for tooth in range(1, n_teeth + 1):
        for flank in (1, 2):
            key = (tooth, flank)
            assert key in ref.flank_nodes and key in ref.flank_faces
            # one swept side face per flank edge per layer; element set = the same hexes (unique)
            assert len(ref.flank_faces[key]) == h * layers
            assert ref.flank_elements[key].size == h * layers
            assert ref.flank_elements[key].max() <= n_3d_hexes
            assert ref.flank_nodes[key].min() >= 1 and ref.flank_nodes[key].max() <= n_3d_nodes
            assert all(face in {"S3", "S4", "S5", "S6"} for _, face in ref.flank_faces[key])
