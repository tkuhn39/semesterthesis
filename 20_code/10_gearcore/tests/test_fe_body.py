"""Wheel body with pockets (``fe.body``): the transcribed drawing, the rings of the rim, the
sweep with levels on the pocket floors, the carving, the body sets and the mesh file."""

import math

import numpy as np
import pytest

from gearcore import data
from gearcore.errors import GeometryInfeasibleError, InputRangeError
from gearcore.fe import abaqus as ab
from gearcore.fe import body as bd
from gearcore.fe import resample as rs
from gearcore.fe import sector_mesh as sm
from gearcore.fe import solid as so
from gearcore.generation import compute_generation
from gearcore.io.ste import load_ste, pair_input_from_ste
from gearcore.models.results import GenerationResult

TEETH = 3
COUNTS = rs.MeshCounts(
    over_tooth_height=8,
    at_tip_edge_break=1,
    at_tooth_root=16,
    over_tooth_thickness=8,
    root_layers=2,
    rim_rings=8,
    shoulder_columns=2,
)
BODY_COUNTS = bd.BodyCounts(hub_rings=3, pocket_rings=3, rim_rings=2, web_layers=2, flange_layers=3)
TAN_DRAFT = math.tan(math.radians(3.0))


@pytest.fixture(scope="module")
def kst_e() -> GenerationResult:
    return compute_generation(pair_input_from_ste(load_ste(data.stplus_input_path("kst_e"))).pair)


@pytest.fixture(scope="module")
def body() -> bd.BodySection:
    return bd.body_section("kst_e", "wheel")


@pytest.fixture(scope="module")
def section(kst_e: GenerationResult, body: bd.BodySection) -> sm.SectorMesh:
    return sm.sector_mesh(
        kst_e, "wheel", teeth=TEETH, rim_rings=12, bore_radius_mm=body.bore_radius_mm, counts=COUNTS
    )


@pytest.fixture(scope="module")
def built(section: sm.SectorMesh, body: bd.BodySection) -> bd.BodyMesh:
    return bd.body_mesh(section, body, BODY_COUNTS, "WHEEL")


# --- the drawing ------------------------------------------------------------------------------------


def test_body_section_of_kst_e_is_the_drawing(body: bd.BodySection) -> None:
    assert (body.face_width_mm, body.tip_radius_mm, body.bore_radius_mm) == (15.0, 27.011, 16.5)
    assert (body.hub_wall_radius_mm, body.hub_wall_height_mm) == (19.107, 0.0)
    assert (body.rim_wall_radius_mm, body.rim_wall_height_mm) == (22.168, 0.474)
    assert (body.pocket_depth_mm, body.wall_angle_deg, body.corner_radius_mm) == (5.5, 93.0, 0.5)
    assert "Schnitt_Symmetrie_Zahnradkoerper_mit_Zahn.png" in body.source
    assert body.web_thickness_mm == pytest.approx(4.0) and body.bottom_z_mm == pytest.approx(2.0)
    assert body.draft_angle_rad == pytest.approx(math.radians(3.0))
    # the walls lean into the pocket: the hub wall grows, the rim wall shrinks with the depth
    assert body.hub_wall_radius_at(0.0) == pytest.approx(19.107)
    assert body.hub_wall_radius_at(5.5) == pytest.approx(19.107 + 5.5 * TAN_DRAFT)
    assert body.rim_wall_radius_at(0.474) == pytest.approx(22.168)
    assert body.rim_wall_radius_at(0.0) == pytest.approx(22.168 + 0.474 * TAN_DRAFT)
    assert body.rim_wall_radius_at(5.5) == pytest.approx(22.168 - (5.5 - 0.474) * TAN_DRAFT)
    # the height of the measured point is the tangent point of the R 0,5 on the 93 deg wall
    assert body.rim_wall_height_mm == pytest.approx(
        0.5 * (1.0 - math.sin(math.radians(3.0))), abs=5e-4
    )
    # the pocket volume: Simpson against a fine trapezoidal integration of the annulus
    angle = 0.7
    depth = np.linspace(0.0, 5.5, 20001)
    annulus = np.array(
        [
            0.5 * angle * (body.rim_wall_radius_at(d) ** 2 - body.hub_wall_radius_at(d) ** 2)
            for d in depth
        ]
    )
    numeric = 2.0 * float(np.trapezoid(annulus, depth))
    assert body.pocket_volume_mm3(angle) == pytest.approx(numeric, rel=1e-9)
    with pytest.raises(InputRangeError):
        body.pocket_volume_mm3(0.0)


def test_body_sections_are_validated() -> None:
    good = bd.body_section("kst_e", "wheel")
    fields = {
        name: getattr(good, name)
        for name in (
            "face_width_mm",
            "tip_radius_mm",
            "bore_radius_mm",
            "hub_wall_radius_mm",
            "hub_wall_height_mm",
            "rim_wall_radius_mm",
            "rim_wall_height_mm",
            "pocket_depth_mm",
            "wall_angle_deg",
            "corner_radius_mm",
        )
    }
    assert bd.BodySection(**fields) == bd.BodySection(**fields, source="")
    for changes in (
        {"bore_radius_mm": 19.2},
        {"rim_wall_radius_mm": 27.5},
        {"pocket_depth_mm": 7.5},
        {"wall_angle_deg": 89.0},
        {"rim_wall_height_mm": 5.5},
        {"corner_radius_mm": -0.1},
        {"hub_wall_radius_mm": math.nan},
    ):
        with pytest.raises(InputRangeError):
            bd.BodySection(**{**fields, **changes})
    # walls that cross above the floor
    with pytest.raises(GeometryInfeasibleError):
        bd.BodySection(**{**fields, "hub_wall_radius_mm": 22.0, "rim_wall_radius_mm": 22.1})
    with pytest.raises(InputRangeError):
        bd.body_section("kst_e", "pinion")
    with pytest.raises(InputRangeError):
        bd.body_section("unknown", "wheel")
    assert set(data.load_body_sections()) == {"kst_e"}


def test_body_counts_are_validated() -> None:
    counts = bd.BodyCounts()
    assert (counts.rings, counts.layers) == (8, 20)
    assert BODY_COUNTS.label() == "hub3_pocket3_rim2_web2_flange3"
    for changes in ({"web_layers": 3}, {"hub_rings": 0}, {"flange_layers": 1.5}):
        with pytest.raises(InputRangeError):
            bd.BodyCounts(**changes)


# --- rings and levels ---------------------------------------------------------------------------------


def test_rings_of_the_rim_are_found(section: sm.SectorMesh) -> None:
    index, means = bd.rim_ring_index(section)
    radius = np.hypot(section.points_mm[:, 0], section.points_mm[:, 1])
    assert int(index.max()) == COUNTS.rim_rings and len(means) == COUNTS.rim_rings + 1
    assert means[0] == pytest.approx(section.bore_radius_mm, abs=1e-9)
    assert means[-1] == pytest.approx(section.fan_ring_radius_mm, abs=5e-3)
    assert bool(np.all(np.diff(means) > 0.5))
    above = radius > section.fan_ring_radius_mm + bd.FAN_TOLERANCE_MM
    assert bool(np.all(index[above] == -1)) and bool(np.all(index[~above] >= 0))
    kind = np.array(section.node_kind)
    assert bool(np.all(index[kind == "bore"] == 0))
    # every rim quad lies between two adjacent rings
    rings = index[section.quads]
    rim = np.all(rings >= 0, axis=1)
    assert bool(np.all(rings[rim].max(axis=1) - rings[rim].min(axis=1) == 1))
    assert set(np.flatnonzero(rim).tolist()) == set(np.flatnonzero(section.quad_zone == 0).tolist())
    with pytest.raises(InputRangeError):
        bd.rim_ring_index("section")  # type: ignore[arg-type]


def test_levels_put_the_floors_and_the_mid_plane_on_levels(body: bd.BodySection) -> None:
    z = bd.body_levels(body, BODY_COUNTS)
    assert len(z) == BODY_COUNTS.layers + 1
    assert np.allclose(z, -z[::-1], atol=0.0)
    assert bool(np.all(np.diff(z) > 0.0))
    for level in (0.0, 2.0, -2.0, 7.5, -7.5):
        assert float(np.abs(z - level).min()) < 1e-12
    assert np.allclose(np.diff(z)[-3:], 5.5 / 3.0)
    assert np.allclose(np.diff(z)[3:5], 2.0)
    with pytest.raises(InputRangeError):
        bd.body_levels(body, "counts")  # type: ignore[arg-type]


# --- the carved mesh ---------------------------------------------------------------------------------


def test_body_mesh_cuts_the_pockets(
    built: bd.BodyMesh, section: sm.SectorMesh, body: bd.BodySection
) -> None:
    index = built.ring_index
    n, m = len(section.points_mm), len(section.quads)
    hub, pocket = BODY_COUNTS.hub_rings, BODY_COUNTS.pocket_rings
    rings = index[section.quads]
    low = np.where(np.all(rings >= 0, axis=1), rings.min(axis=1), -1)
    pocket_quads = np.flatnonzero((low >= hub) & (low < hub + pocket))
    flange_layers = 2 * BODY_COUNTS.flange_layers
    assert len(built.removed_elements) == len(pocket_quads) * flange_layers
    assert len(built.solid.hexes) == len(built.full.hexes) - len(built.removed_elements)
    assert np.array_equal(built.solid.z_levels_mm, bd.body_levels(body, BODY_COUNTS))
    assert built.solid.layers == BODY_COUNTS.layers
    # no orphan node, no inverted element, the maps are consistent
    assert np.array_equal(np.unique(built.solid.hexes), np.arange(len(built.solid.nodes_mm)))
    assert float(so.hex_corner_volumes(built.solid).min()) > 0.0
    kept = np.flatnonzero(built.element_map >= 0)
    assert np.array_equal(built.element_map[kept], np.arange(len(kept)))
    assert np.array_equal(
        np.sort(np.concatenate((kept, built.removed_elements))), np.arange(len(built.full.hexes))
    )
    assert np.allclose(built.solid.nodes_mm, built.full.nodes_mm[built.node_map >= 0], atol=0.0)
    # the removed volume is the volume of both pockets of the drawing within the sector
    full_volume = so.hex_volumes(built.full)
    removed_volume = float(full_volume[built.removed_elements].sum())
    sector_angle = (TEETH + 2) * section.pitch_angle_rad
    assert removed_volume == pytest.approx(body.pocket_volume_mm3(sector_angle), rel=2e-3)
    assert float(so.hex_volumes(built.solid).sum()) + removed_volume == pytest.approx(
        float(full_volume.sum()), rel=1e-12
    )
    # the walls stand at the radii of the drawing, level by level with their draft
    radius = np.hypot(built.full.nodes_mm[:, 0], built.full.nodes_mm[:, 1])
    z = built.full.z_levels_mm
    for level, z_level in enumerate(z.tolist()):
        depth = min(7.5 - abs(z_level), 5.5)
        at = slice(level * n, (level + 1) * n)
        hub_wall = radius[at][index == hub]
        rim_wall = radius[at][index == hub + pocket]
        assert np.allclose(hub_wall, body.hub_wall_radius_at(depth), atol=1e-9)
        assert np.allclose(rim_wall, body.rim_wall_radius_at(depth), atol=1e-9)
        assert np.allclose(radius[at][index == 0], 16.5, atol=1e-9)
        inside = np.flatnonzero((index > hub) & (index < hub + pocket)) + level * n
        removed_nodes = built.node_map[inside] < 0
        if abs(z_level) > 2.0 + 1e-9:
            assert bool(np.all(removed_nodes))
        else:
            assert not bool(np.any(removed_nodes))
        tooth_zone = np.flatnonzero(index < 0) + level * n
        assert bool(np.all(built.node_map[tooth_zone] >= 0))
    # the transverse section carries the stations of the face; the tooth zone is untouched
    face = np.hypot(built.section.points_mm[:, 0], built.section.points_mm[:, 1])
    assert np.allclose(face[index == hub], 19.107, atol=1e-9)
    assert np.allclose(built.section.points_mm[index < 0], section.points_mm[index < 0], atol=0.0)
    assert np.array_equal(built.section.quads, section.quads)
    # the sets of the teeth are carried over in full, the Fesselung loses the pocket nodes
    for name in (
        "WHEEL_TEETH_SURF_NODES",
        "WHEEL_T2_LEFT_SURF_ROOT_NODES",
        "WHEEL_HEAD_T2_SURF_NODES",
    ):
        assert len(built.sets.node_sets[name]) == len(built.full_sets.node_sets[name])
    for name in ("WHEEL_TEETH_SURF", "WHEEL_T2_RIGHT_SURF_ROOT", "WHEEL_ROOT_T1_T2_SURF"):
        assert len(built.sets.surfaces[name]) == len(built.full_sets.surfaces[name])
    for name in ("WHEEL_T2_LEFT_HALF", "WHEEL_HEAD_T2", "WHEEL_TOOTH_ZONE"):
        assert len(built.sets.element_sets[name]) == len(built.full_sets.element_sets[name])
    fixed_full = built.full_sets.node_sets["WHEEL_FESSELUNG"]
    expected = built.node_map[fixed_full]
    assert np.array_equal(
        np.sort(built.sets.node_sets["WHEEL_FESSELUNG"]), np.sort(expected[expected >= 0])
    )
    assert len(built.sets.node_sets["WHEEL_FESSELUNG"]) < len(fixed_full)
    assert len(built.sets.node_sets["WHEEL_NODES"]) == len(built.solid.nodes_mm)
    assert len(built.sets.element_sets["WHEEL"]) == len(built.solid.hexes)
    # hub, web and rim partition the rim below the fan ring; the web lies in the web layers
    hub_set = set(built.sets.element_sets["WHEEL_BODY_HUB"].tolist())
    web_set = set(built.sets.element_sets["WHEEL_BODY_WEB"].tolist())
    rim_set = set(built.sets.element_sets["WHEEL_BODY_RIM"].tolist())
    assert hub_set | web_set | rim_set == set(built.sets.element_sets["WHEEL_RIM"].tolist())
    assert not (hub_set & web_set) and not (web_set & rim_set) and not (hub_set & rim_set)
    assert len(web_set) == len(pocket_quads) * BODY_COUNTS.web_layers
    centre_z = built.solid.nodes_mm[built.solid.hexes[sorted(web_set)], 2].mean(axis=1)
    assert bool(np.all(np.abs(centre_z) < 2.0))
    assert (
        len(hub_set)
        == int((low >= 0).sum() - len(pocket_quads) - int((low >= hub + pocket).sum()))
        * BODY_COUNTS.layers
    )
    del m


def test_pocket_surface_is_the_walls_and_the_floors(
    built: bd.BodyMesh, body: bd.BodySection
) -> None:
    faces = built.sets.surfaces["WHEEL_POCKET_SURF"]
    nodes = built.sets.node_sets["WHEEL_POCKET_SURF_NODES"]
    index = built.ring_index
    hub, pocket = BODY_COUNTS.hub_rings, BODY_COUNTS.pocket_rings
    segments_hub = int((index == hub).sum()) - 1
    segments_rim = int((index == hub + pocket).sum()) - 1
    rings = index[built.section.quads]
    low = np.where(np.all(rings >= 0, axis=1), rings.min(axis=1), -1)
    pocket_quads = int(((low >= hub) & (low < hub + pocket)).sum())
    flange = BODY_COUNTS.flange_layers
    assert len(faces) == 2 * (segments_hub * flange + segments_rim * flange + pocket_quads)
    assert len({(int(e), int(f)) for e, f in faces}) == len(faces)
    on_pocket = np.zeros(len(built.solid.nodes_mm), dtype=bool)
    on_pocket[nodes] = True
    xyz = built.solid.nodes_mm
    radius = np.hypot(xyz[:, 0], xyz[:, 1])
    # every face is exposed, lies on a wall or a floor, and all its corners are pocket nodes
    all_faces = np.sort(
        np.stack([built.solid.hexes[:, so.FACE_NODES[f]] for f in range(1, 7)], axis=1).reshape(
            -1, 4
        ),
        axis=1,
    )
    _, occurrences = np.unique(all_faces, axis=0, return_counts=True)
    keys = {
        tuple(row): count
        for row, count in zip(
            np.unique(all_faces, axis=0).tolist(), occurrences.tolist(), strict=True
        )
    }
    walls = floors = 0
    for element, face in faces.tolist():
        corners = built.solid.hexes[element][list(so.FACE_NODES[face])]
        assert keys[tuple(sorted(corners.tolist()))] == 1
        assert bool(np.all(on_pocket[corners]))
        z = xyz[corners, 2]
        if np.allclose(np.abs(z), 2.0, atol=1e-9):
            floors += 1
            continue
        depth = np.minimum(7.5 - np.abs(z), 5.5)
        r = radius[corners]
        hub_wall = np.array([body.hub_wall_radius_at(d) for d in depth])
        rim_wall = np.array([body.rim_wall_radius_at(d) for d in depth])
        assert np.allclose(r, hub_wall, atol=1e-9) or np.allclose(r, rim_wall, atol=1e-9)
        walls += 1
    assert floors == 2 * pocket_quads and walls == 2 * flange * (segments_hub + segments_rim)
    assert bool(np.all(np.abs(xyz[nodes, 2]) >= 2.0 - 1e-9))


def test_mesh_file_of_the_body(built: bd.BodyMesh) -> None:
    text = ab.mesh_text(
        built.solid, built.sets, element_type="C3D8I", title="kst_e wheel, body pocket"
    )
    lines = text.splitlines()
    assert text.isascii()
    first_node = lines.index("*NODE, NSET=WHEEL_NODES") + 1
    first_element = lines.index("*ELEMENT, TYPE=C3D8I, ELSET=WHEEL")
    assert first_element - first_node == len(built.solid.nodes_mm)
    assert lines[first_element + len(built.solid.hexes) + 1].startswith("*")
    assert "*ELSET, ELSET=WHEEL_BODY_WEB" in lines and "*ELSET, ELSET=WHEEL_BODY_HUB" in lines
    assert "*SURFACE, TYPE=ELEMENT, NAME=WHEEL_POCKET_SURF" in lines
    assert "*NSET, NSET=WHEEL_POCKET_SURF_NODES" in lines
    assert (
        f"{built.solid.layers} layers, {len(built.solid.nodes_mm)} nodes, {len(built.solid.hexes)} elements"
        in lines[1]
    )


def test_inputs_of_the_body_mesh_raise(
    kst_e: GenerationResult, section: sm.SectorMesh, body: bd.BodySection
) -> None:
    with pytest.raises(InputRangeError):
        bd.body_mesh(
            section, body, bd.BodyCounts(hub_rings=2, pocket_rings=3, rim_rings=2), "WHEEL"
        )
    with pytest.raises(InputRangeError):
        bd.body_mesh(section, body, BODY_COUNTS, "wheel")
    with pytest.raises(InputRangeError):
        bd.body_mesh(section, "body", BODY_COUNTS, "WHEEL")  # type: ignore[arg-type]
    with pytest.raises(InputRangeError):
        bd.body_mesh("section", body, BODY_COUNTS, "WHEEL")  # type: ignore[arg-type]
    other_bore = sm.sector_mesh(kst_e, "wheel", teeth=1, rim_rings=12, counts=COUNTS)
    assert other_bore.bore_radius_mm != pytest.approx(16.5)
    with pytest.raises(InputRangeError):
        bd.body_mesh(other_bore, body, BODY_COUNTS, "WHEEL")
    # a drawing of another gear: the tip does not fit
    other_gear = bd.BodySection(
        **{
            **{
                name: getattr(body, name)
                for name in (
                    "face_width_mm",
                    "bore_radius_mm",
                    "hub_wall_radius_mm",
                    "hub_wall_height_mm",
                    "rim_wall_radius_mm",
                    "rim_wall_height_mm",
                    "pocket_depth_mm",
                    "wall_angle_deg",
                    "corner_radius_mm",
                )
            },
            "tip_radius_mm": 28.0,
        }
    )
    with pytest.raises(GeometryInfeasibleError):
        bd.body_mesh(section, other_gear, BODY_COUNTS, "WHEEL")


# --- solid: volumes and removal ------------------------------------------------------------------------


def test_hex_volumes_and_remove_elements(section: sm.SectorMesh) -> None:
    solid = so.extrude(section, face_width_mm=15.0, layers=2)
    sets = so.gear_sets(solid, "WHEEL")
    volume = so.hex_volumes(solid)
    assert bool(np.all(volume > 0.0))
    # the rim below the fan ring is a polygonal annulus sector: its volume to the chord error
    rim = sets.element_sets["WHEEL_RIM"]
    angle = (TEETH + 2) * section.pitch_angle_rad
    annulus = 0.5 * angle * (section.fan_ring_radius_mm**2 - section.bore_radius_mm**2) * 15.0
    assert float(volume[rim].sum()) == pytest.approx(annulus, rel=2e-3)
    assert float(volume[rim].sum()) < annulus
    removed = np.array([0, 1, 2, len(solid.hexes) - 1], dtype=np.int64)
    carved = so.remove_elements(solid, sets, removed)
    assert len(carved.mesh.hexes) == len(solid.hexes) - 4
    assert np.array_equal(carved.element_map[removed], [-1, -1, -1, -1])
    used = np.unique(solid.hexes[np.setdiff1d(np.arange(len(solid.hexes)), removed)])
    assert np.array_equal(np.flatnonzero(carved.node_map >= 0), used)
    assert np.array_equal(carved.node_map[used], np.arange(len(used)))
    assert np.allclose(carved.mesh.nodes_mm, solid.nodes_mm[used], atol=0.0)
    assert np.array_equal(carved.mesh.hexes, carved.node_map[solid.hexes][carved.element_map >= 0])
    assert len(carved.sets.element_sets["WHEEL"]) == len(carved.mesh.hexes)
    assert len(carved.sets.node_sets["WHEEL_NODES"]) == len(carved.mesh.nodes_mm)
    for name, rows in sets.surfaces.items():
        kept = rows[carved.element_map[rows[:, 0]] >= 0]
        assert len(carved.sets.surfaces[name]) == len(kept)
    assert np.allclose(so.hex_volumes(carved.mesh).sum() + volume[removed].sum(), volume.sum())
    for bad in (np.array([-1]), np.array([len(solid.hexes)]), np.array([0.5])):
        with pytest.raises(InputRangeError):
            so.remove_elements(solid, sets, bad)
    with pytest.raises(InputRangeError):
        so.remove_elements(section, sets, removed)  # type: ignore[arg-type]
    with pytest.raises(InputRangeError):
        so.hex_volumes(section)  # type: ignore[arg-type]
    levels = so.extrude_to_levels(section, np.array([-7.5, -2.0, 0.0, 2.0, 7.5]))
    assert levels.layers == 4 and levels.z_levels_mm.tolist() == [-7.5, -2.0, 0.0, 2.0, 7.5]
    for bad_levels in ([0.0], [0.0, 0.0], [1.0, 0.0], [0.0, math.nan]):
        with pytest.raises(InputRangeError):
            so.extrude_to_levels(section, np.array(bad_levels))
