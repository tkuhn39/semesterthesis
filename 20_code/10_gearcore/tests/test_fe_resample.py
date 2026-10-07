"""Resampling of the sector template to given numbers of elements (``gearcore.fe.resample``)."""

import numpy as np
import pytest
from scipy.spatial import cKDTree

from gearcore import data
from gearcore.errors import InputRangeError
from gearcore.fe import refine as rf
from gearcore.fe import resample as rs
from gearcore.fe import sector_mesh as sm
from gearcore.fe import solid as so
from gearcore.fe.sector_template import load_sector_template
from gearcore.generation import compute_generation
from gearcore.io.ste import load_ste, pair_input_from_ste
from gearcore.models.results import GenerationResult

RINGS = 12


def _generation(case: str) -> GenerationResult:
    return compute_generation(pair_input_from_ste(load_ste(data.stplus_input_path(case))).pair)


_KST_E = _generation("kst_e")


@pytest.fixture(scope="module")
def kst_e() -> GenerationResult:
    return _KST_E


def _resampled(counts: rs.MeshCounts) -> rs.ResampledTemplate:
    tpl = load_sector_template()
    tooth, shoulder, lists, _ = sm._trimmed(tpl, RINGS)
    return rs.resample_template(
        tooth,
        shoulder,
        lists.tooth_left,
        lists.tooth_right,
        lists.shoulder_interface,
        lists.shoulder_cut,
        tpl.tooth_surface_features,
        RINGS,
        tpl.number_of_teeth,
        counts,
    )


def test_counts_are_validated() -> None:
    counts = rs.MeshCounts()
    assert counts.per_class == {
        "height": 18,
        "chamfer": 2,
        "root": 40,
        "root_layers": 3,
        "centre": 2,
        "rim_rings": 12,
        "shoulder": 4,
    }
    with pytest.raises(InputRangeError):
        rs.MeshCounts(at_tooth_root=41)
    with pytest.raises(InputRangeError):
        rs.MeshCounts(over_tooth_thickness=9)
    with pytest.raises(InputRangeError):
        rs.MeshCounts(over_tooth_thickness=6, root_layers=3)
    with pytest.raises(InputRangeError):
        rs.MeshCounts(rim_rings=0)
    with pytest.raises(InputRangeError):
        rs.MeshCounts(over_tooth_height=2.0)  # type: ignore[arg-type]


def test_template_patches_and_classes() -> None:
    tpl = load_sector_template()
    tooth, _, lists, _ = sm._trimmed(tpl, RINGS)
    order = np.array(tooth.surface_order)
    forced = tuple(int(order[k]) for k in (40, 58, 65, 90, 72)) + (
        int(lists.tooth_left[RINGS]),
        int(lists.tooth_right[RINGS]),
    )
    grids = rs.patches(tooth, forced)
    sizes = sorted((g.shape[0] - 1) * (g.shape[1] - 1) for g in grids)
    # per half: root band 40 x 3, dome 40 x 2, head 18 x 3 and 18 x 2, chamfer 2 x 3 and 2 x 2, rim 12 x 2
    assert sizes == [4, 4, 6, 6, 24, 24, 36, 36, 54, 54, 80, 80, 120, 120]
    assert sum(sizes) == len(tooth.quads)


def test_own_counts_reproduce_the_template() -> None:
    tpl = load_sector_template()
    tooth, shoulder, lists, _ = sm._trimmed(tpl, RINGS)
    out = _resampled(rs.MeshCounts())
    for old, new in ((tooth, out.tooth), (shoulder, out.shoulder)):
        assert len(new.phi) == len(old.phi) and len(new.quads) == len(old.quads)
        distance, index = cKDTree(np.column_stack((old.phi, old.radius_mm))).query(
            np.column_stack((new.phi, new.radius_mm))
        )
        assert float(distance.max()) < 1.0e-12
        assert len(set(index.tolist())) == len(old.phi)
        assert [old.kind[int(i)] for i in index] == list(new.kind)
        old_quads = {frozenset(q) for q in old.quads.tolist()}
        new_quads = {frozenset(int(index[n]) for n in q) for q in new.quads.tolist()}
        assert old_quads == new_quads
    assert out.tooth_surface_features == tpl.tooth_surface_features
    assert int(out.tooth_grid.sum()) == int(lists.tooth_grid.sum()) == 200
    assert len(out.tooth_left_interface) == len(lists.tooth_left) == RINGS + 4
    assert len(out.shoulder_cut) == len(lists.shoulder_cut)


@pytest.mark.parametrize(
    "counts",
    [
        rs.MeshCounts(over_tooth_thickness=14, root_layers=5),
        rs.MeshCounts(over_tooth_height=9, at_tip_edge_break=1, at_tooth_root=40),
        rs.MeshCounts(
            over_tooth_height=12,
            at_tip_edge_break=3,
            at_tooth_root=56,
            over_tooth_thickness=8,
            root_layers=2,
            rim_rings=5,
            shoulder_columns=2,
        ),
    ],
)
def test_other_counts_give_the_requested_mesh(
    kst_e: GenerationResult, counts: rs.MeshCounts
) -> None:
    section = sm.sector_mesh(kst_e, "wheel", teeth=3, rim_rings=RINGS, counts=counts)
    effective = rf.effective_counts(section)
    assert effective.over_tooth_height == counts.over_tooth_height + counts.at_tip_edge_break
    assert effective.at_tooth_root == counts.at_tooth_root
    assert effective.over_tooth_thickness == counts.over_tooth_thickness
    assert section.counts == counts
    assert float(sm.scaled_jacobians(section.points_mm, section.quads).min()) >= sm.MIN_CORNER_SINE
    # the interface lists hold the rim rings plus the layers above the fan ring
    out = _resampled(counts)
    assert len(out.tooth_left_interface) == counts.rim_rings + counts.root_layers + 1
    assert len(out.shoulder_cut) == counts.rim_rings + counts.root_layers + 1
    # the feature points are nodes: root form point, tip form point, tip corner on the contour
    radius = np.hypot(section.points_mm[:, 0], section.points_mm[:, 1])
    surface = section.surface_path
    assert np.min(np.abs(radius[surface] - section.root_form_radius_mm)) < 1.0e-9
    assert np.min(np.abs(radius[surface] - section.tip_form_radius_mm)) < 1.0e-9
    # the teeth stay congruent and the extruded sets exist
    solid = so.extrude(section, face_width_mm=15.0, layers=1)
    sets = so.gear_sets(solid, "WHEEL")
    assert len(sets.surfaces["WHEEL_T2_LEFT_SURF_FLANK"]) == counts.over_tooth_height
    assert len(sets.surfaces["WHEEL_T2_LEFT_SURF_ROOT"]) == counts.at_tooth_root >> 1
    assert float(so.hex_corner_volumes(solid).min()) > 0.0


def test_bore_radius_and_rings_are_independent(kst_e: GenerationResult) -> None:
    coarse = sm.sector_mesh(
        kst_e, "wheel", teeth=1, rim_rings=RINGS, counts=rs.MeshCounts(rim_rings=4)
    )
    base = sm.sector_mesh(kst_e, "wheel", teeth=1, rim_rings=RINGS)
    assert coarse.bore_radius_mm == pytest.approx(base.bore_radius_mm)
    # fewer rings over the same depth: fewer nodes, the same bore circle
    assert len(coarse.points_mm) < len(base.points_mm)
    assert int((np.array(coarse.node_kind) == "bore").sum()) == int(
        (np.array(base.node_kind) == "bore").sum()
    )
    with pytest.raises(InputRangeError):
        sm.sector_mesh(kst_e, "wheel", teeth=1, rim_rings=RINGS, counts="fine")  # type: ignore[arg-type]
