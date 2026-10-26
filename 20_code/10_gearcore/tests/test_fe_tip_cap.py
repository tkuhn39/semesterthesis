"""The cap of the tooth tip (``gearcore.fe.resample.TipCap``): the rows of the template above
the tangency point rebuilt as three blocks, so that no quad corner sits on the arc of the
measured tip corner (known limit FE-26)."""

import numpy as np
import pytest

from gearcore import contour as ct
from gearcore import data
from gearcore import manufactured as mf
from gearcore.errors import InputRangeError
from gearcore.fe import resample as rs
from gearcore.fe import sector_mesh as sm
from gearcore.fe.sector_template import load_sector_template
from gearcore.io.ste import load_ste, pair_input_from_ste

RINGS = 12
SERIES = {
    "over_tooth_height": 18,
    "at_tip_edge_break": 3,
    "at_tooth_root": 60,
    "over_tooth_thickness": 14,
    "root_layers": 4,
    "rim_rings": RINGS,
    "shoulder_columns": 2,
}


@pytest.fixture(scope="module")
def measured() -> mf.ManufacturedResult:
    pair = pair_input_from_ste(load_ste(data.stplus_input_path("kst_e"))).pair
    return mf.apply(pair, mf.load_variant("kst_e", "kunststoff"))


def _mesh(measured: mf.ManufacturedResult, **counts: int) -> sm.SectorMesh:
    return sm.sector_mesh(
        measured.generation,
        "wheel",
        teeth=3,
        rim_rings=RINGS,
        bore_radius_mm=16.5,
        counts=rs.MeshCounts(**SERIES, **counts),
        modification=measured.modification("wheel"),
    )


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


def _arc_centre(measured: mf.ManufacturedResult) -> tuple[np.ndarray, float]:
    contour = ct.tooth_contour(
        measured.generation, "wheel", points=2000, modification=measured.modification("wheel")
    )
    arc = contour.segment("left_tip_flank")
    a, b, c = arc[0], arc[len(arc) // 2], arc[-1]
    d = 2.0 * (a[0] * (b[1] - c[1]) + b[0] * (c[1] - a[1]) + c[0] * (a[1] - b[1]))
    ux = ((a @ a) * (b[1] - c[1]) + (b @ b) * (c[1] - a[1]) + (c @ c) * (a[1] - b[1])) / d
    uy = ((a @ a) * (c[0] - b[0]) + (b @ b) * (a[0] - c[0]) + (c @ c) * (b[0] - a[0])) / d
    centre = np.array([ux, uy])
    return centre, float(np.hypot(*(a - centre)))


def test_cap_layers_are_validated() -> None:
    assert rs.MeshCounts(**SERIES).cap_layers == 0
    assert "_cap" not in rs.MeshCounts(**SERIES).label()
    assert rs.MeshCounts(**SERIES, cap_layers=1).label().endswith("_cap1")
    with pytest.raises(InputRangeError):
        rs.MeshCounts(**SERIES, cap_layers=-1)
    with pytest.raises(InputRangeError):
        rs.MeshCounts(**SERIES, cap_layers=7)  # as deep as the half thickness: no land left
    assert rs.MeshCounts(**SERIES, cap_layers=6).cap_layers == 6


def test_without_the_cap_the_template_block_is_kept() -> None:
    plain = _resampled(rs.MeshCounts(**SERIES))
    assert plain.tip_cap is None
    assert plain.tooth_surface_features[-1] - plain.tooth_surface_features[-2] == 7


def test_cap_topology_of_the_resampled_block() -> None:
    capped = _resampled(rs.MeshCounts(**SERIES, cap_layers=1))
    cap = capped.tip_cap
    assert cap is not None
    assert cap.corner_grid.shape == (2, 4)  # cap_layers + 1 rows, chamfer + 1 columns
    assert cap.land_grid.shape == (2, 7)  # land of 7 - 1 = 6 segments
    assert cap.core_grid.shape == (4, 7)
    assert (cap.corner_grid[-1, :] == cap.core_grid[:, 0]).all()
    assert (cap.corner_grid[:, -1] == cap.land_grid[:, 0]).all()
    assert (cap.land_grid[-1, :] == cap.core_grid[-1, :]).all()
    # the land lost one segment per half, the rest of the surface is the template's
    plain = _resampled(rs.MeshCounts(**SERIES))
    assert capped.tooth_surface_features[:4] == plain.tooth_surface_features[:4]
    assert capped.tooth_surface_features[4] == plain.tooth_surface_features[4] - 1
    assert len(capped.tooth.surface_order) == len(plain.tooth.surface_order) - 2
    # valences: the inner corner has three quads, every surface node of the cap two
    topology = rs._Topology(capped.tooth.quads)
    assert topology.valence(int(cap.land_grid[-1, 0])) == 3
    for node in np.concatenate((cap.corner_grid[0, :], cap.land_grid[0, :])).tolist():
        assert topology.valence(int(node)) == 2
    assert all(capped.tooth.kind[int(n)] == "surface" for n in cap.land_grid[0, :].tolist())
    assert all(capped.tooth.kind[int(n)] == "interior" for n in cap.core_grid[1:, :-1].ravel())
    # mirror symmetric: the partner list exists and keeps the centre line nodes fixed
    centre = cap.core_grid[:, -1]
    assert (capped.tooth_partner[centre] == centre).all()
    # the head flags mark every quad of the cap
    assert int(capped.tooth_grid.sum()) == int(plain.tooth_grid.sum()) - 2 * 3 * 7 + 2 * (
        3 + 6 + 18
    )


def test_cap_quads_are_well_shaped_on_the_measured_wheel(measured: mf.ManufacturedResult) -> None:
    plain = _mesh(measured)
    capped = _mesh(measured, cap_layers=1)
    quality_plain = sm.scaled_jacobians(plain.points_mm, plain.quads)[plain.quad_head == 1]
    quality = sm.scaled_jacobians(capped.points_mm, capped.quads)[capped.quad_head == 1]
    assert float(quality_plain.min()) < 0.25  # the sliver of FE-26
    assert float(quality.min()) >= 0.5
    assert capped.tip_form_radius_mm == pytest.approx(
        0.5
        * ct.tooth_contour(
            measured.generation, "wheel", modification=measured.modification("wheel")
        ).tip_form_diameter_mm
    )
    # the surface path lost one node per half tooth and still follows element edges
    assert len(capped.surface_path) == len(plain.surface_path) - 2 * capped.teeth
    edges = {
        tuple(sorted(e))
        for quad in capped.quads.tolist()
        for e in zip(quad, quad[1:] + quad[:1], strict=True)
    }
    path = capped.surface_path.tolist()
    assert all(tuple(sorted(pair)) in edges for pair in zip(path, path[1:], strict=False))


def test_cap_surface_nodes_lie_on_the_arc(measured: mf.ManufacturedResult) -> None:
    capped = _mesh(measured, cap_layers=1)
    centre, r_k = _arc_centre(measured)
    assert r_k == pytest.approx(0.21, abs=1e-6)
    turn = 0.5 * np.pi - capped.tooth_centre_angle_rad(2)
    rotation = np.array([[np.cos(turn), -np.sin(turn)], [np.sin(turn), np.cos(turn)]])
    xy = capped.points_mm @ rotation.T
    radius = np.hypot(xy[:, 0], xy[:, 1])
    surface = np.array([kind == "surface" for kind in capped.node_kind])
    for sign in (1.0, -1.0):
        on_arc = (
            surface
            & (sign * xy[:, 0] > 0.0)
            & (np.abs(xy[:, 0]) < 0.6)
            & (radius > capped.tip_form_radius_mm - 1e-6)
            & (radius < capped.tip_radius_mm - 1e-6)
        )
        assert (
            int(on_arc.sum()) == 3
        )  # tangency point and two nodes on the arc; the end is on the tip circle
        distance = np.hypot(*(xy[on_arc] - centre * np.array([-sign, 1.0])).T)
        assert np.abs(distance - r_k).max() < 1e-6
