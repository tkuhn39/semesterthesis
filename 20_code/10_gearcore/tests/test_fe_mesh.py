"""Mesh of a gear sector for the finite element model: template, transverse mesh, solid, sets
and the mesh file (``gearcore.fe.sector_template``, ``sector_mesh``, ``solid``, ``abaqus``)."""

import math
from collections import Counter

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from scipy.spatial import cKDTree

from gearcore import contour as ct
from gearcore import data
from gearcore.errors import GeometryInfeasibleError, InputRangeError, NotSupportedError
from gearcore.fe import abaqus as ab
from gearcore.fe import sector_mesh as sm
from gearcore.fe import solid as so
from gearcore.fe.sector_template import load_sector_template
from gearcore.generation import compute_generation
from gearcore.io.ste import load_ste, pair_input_from_ste
from gearcore.models.results import GenerationResult

TOOTH_QUADS, SHOULDER_QUADS, RIM_QUADS_PER_RING, TEMPLATE_RINGS = 700, 112, 4, 25


def _generation(case: str) -> GenerationResult:
    return compute_generation(pair_input_from_ste(load_ste(data.stplus_input_path(case))).pair)


_KST_E = _generation("kst_e")


@pytest.fixture(scope="module")
def kst_e() -> GenerationResult:
    return _KST_E


@pytest.fixture(scope="module")
def sector(kst_e: GenerationResult) -> sm.SectorMesh:
    return sm.sector_mesh(kst_e, "wheel", teeth=5, rim_rings=12)


@pytest.fixture(scope="module")
def solid(sector: sm.SectorMesh) -> so.SolidMesh:
    return so.extrude(sector, face_width_mm=15.0, layers=4)


@pytest.fixture(scope="module")
def sets(solid: so.SolidMesh) -> so.GearSets:
    return so.gear_sets(solid, "WHEEL")


def _edge_counts(quads: np.ndarray) -> Counter[tuple[int, int]]:
    counts: Counter[tuple[int, int]] = Counter()
    for quad in quads.tolist():
        for k in range(4):
            a, b = quad[k], quad[(k + 1) % 4]
            counts[(min(a, b), max(a, b))] += 1
    return counts


def _tooth_nodes(sector: sm.SectorMesh, tooth: int) -> np.ndarray:
    return np.unique(sector.quads[sector.quad_tooth == tooth])


def _turned(points: np.ndarray, angle: float) -> np.ndarray:
    c, s = math.cos(angle), math.sin(angle)
    return np.column_stack(
        (c * points[:, 0] - s * points[:, 1], s * points[:, 0] + c * points[:, 1])
    )


# --- template ---------------------------------------------------------------------------------------


def test_template_holds_one_tooth_block_and_one_shoulder_block() -> None:
    template = load_sector_template()
    assert (len(template.tooth.phi), len(template.tooth.quads)) == (796, TOOTH_QUADS)
    assert (len(template.shoulder.phi), len(template.shoulder.quads)) == (145, SHOULDER_QUADS)
    assert template.rim_rings == TEMPLATE_RINGS
    assert len(template.tooth_left_interface) == len(template.shoulder_cut) == 29
    assert len(template.tooth_centre_line) == 86
    assert len(template.tooth.surface_order) == 131
    # the regular grid of the tooth and the points that divide the clockwise half of its
    # contour: gap centre, root form point, tip form point, tip corner, tooth centre
    assert sum(template.tooth_grid_quads) == 200
    assert template.tooth_surface_features == (0, 40, 58, 60, 65)
    partner = np.array(template.tooth_mirror_partner)
    assert np.array_equal(partner[partner], np.arange(len(partner)))
    # exactly mirror symmetric about the tooth centre line
    assert np.array_equal(template.tooth.phi[partner], -template.tooth.phi)
    assert np.array_equal(template.tooth.radius_mm[partner], template.tooth.radius_mm)
    assert set(template.tooth.phi[list(template.tooth_left_interface)]) == {-0.5}
    assert set(template.tooth.phi[list(template.tooth_right_interface)]) == {0.5}
    assert set(template.shoulder.phi[list(template.shoulder_cut)]) == {-1.0}
    for block in (template.tooth, template.shoulder):
        angle = block.phi * 2.0 * math.pi / template.number_of_teeth
        points = np.column_stack(
            (-block.radius_mm * np.sin(angle), block.radius_mm * np.cos(angle))
        )
        assert float(sm.scaled_jacobians(points, block.quads).min()) > 0.2
        assert not block.phi.flags.writeable


# --- transverse mesh ---------------------------------------------------------------------------------


def test_four_teeth_with_all_rim_rings_have_the_topology_of_the_reference(
    kst_e: GenerationResult,
) -> None:
    reference = sm.sector_mesh(kst_e, "wheel", teeth=4, rim_rings=25)
    assert (len(reference.points_mm), len(reference.quads)) == (3329, 3024)
    valence = Counter(reference.quads.ravel().tolist())
    interior = [n for n, kind in enumerate(reference.node_kind) if kind == "interior"]
    assert Counter(valence[n] for n in interior) == {4: 2716, 5: 2, 6: 3}
    assert Counter(reference.node_kind) == {"interior": 2721, "surface": 527, "cut": 58, "bore": 23}
    quality = sm.scaled_jacobians(reference.points_mm, reference.quads)
    # the reference has 6 cells per tooth below 0.35 at the tooth tips (smallest 0.245, one row
    # 6.5 micrometres thin); the smoothing of the tip region removes them
    assert float(quality.min()) > 0.44
    edges = np.concatenate(
        [
            np.hypot(
                *(
                    reference.points_mm[reference.quads[:, k]]
                    - reference.points_mm[reference.quads[:, (k + 1) % 4]]
                ).T
            )
            for k in range(4)
        ]
    )
    assert float(edges.min()) > 0.016


def test_sector_is_one_conformal_patch(sector: sm.SectorMesh) -> None:
    assert (len(sector.points_mm), len(sector.quads)) == (3719, 3360)
    counts = _edge_counts(sector.quads)
    assert set(counts.values()) == {1, 2}
    boundary = [edge for edge, n in counts.items() if n == 1]
    ends = Counter(node for edge in boundary for node in edge)
    assert set(ends.values()) == {2}  # one closed loop, no branching
    # a disc: nodes - edges + quads = 1
    assert len(sector.points_mm) - len(counts) + len(sector.quads) == 1
    assert len(np.unique(sector.quads)) == len(sector.points_mm)
    tree = cKDTree(sector.points_mm)
    assert not tree.query_pairs(1e-6)  # no two nodes at the same place
    assert float(sm.scaled_jacobians(sector.points_mm, sector.quads).min()) > 0.44
    kinds = Counter(sector.node_kind)
    assert (
        kinds["surface"] + 2 == len(sector.surface_path) == len(set(sector.surface_path.tolist()))
    )
    assert Counter(sector.quad_tooth.tolist()) == {0: 120, 1: 648, 2: 648, 3: 648, 4: 648, 5: 648}
    assert Counter(sector.quad_side.tolist()) == {0: 120, 1: 1620, -1: 1620}


def test_teeth_are_congruent_and_mirror_symmetric(sector: sm.SectorMesh) -> None:
    first = sector.points_mm[_tooth_nodes(sector, 1)]
    tree = cKDTree(first)
    for tooth in range(2, sector.teeth + 1):
        nodes = sector.points_mm[_tooth_nodes(sector, tooth)]
        back = _turned(nodes, -(tooth - 1) * sector.pitch_angle_rad)
        distance, _ = tree.query(back)
        assert len(nodes) == len(first)
        assert float(distance.max()) < 1e-11
    middle = sector.points_mm[_tooth_nodes(sector, 3)]  # its centre line is +y
    distance, _ = cKDTree(middle).query(middle * np.array([-1.0, 1.0]))
    assert float(distance.max()) < 1e-11
    # the whole sector is mirror symmetric about its bisector
    distance, _ = cKDTree(sector.points_mm).query(sector.points_mm * np.array([-1.0, 1.0]))
    assert float(distance.max()) < 1e-11


def test_surface_lies_on_the_generated_contour(
    kst_e: GenerationResult, sector: sm.SectorMesh
) -> None:
    contour = ct.tooth_contour(kst_e, "wheel", points=3000)
    kind = np.array(sector.node_kind)
    nodes = _tooth_nodes(sector, 3)
    surface = sector.points_mm[nodes[kind[nodes] == "surface"]]
    radius = np.hypot(surface[:, 0], surface[:, 1])
    on_root_circle = np.abs(radius - sector.root_radius_mm) < 1e-9
    assert 2 <= int(on_root_circle.sum()) < len(surface) // 4
    assert float(ct.distances(contour, surface[~on_root_circle]).max()) < 1e-3  # micrometres
    assert sector.root_radius_mm == 0.5 * contour.generated_root_diameter_mm
    assert sector.tip_radius_mm == 0.5 * contour.tip_diameter_mm
    assert float(radius.max()) == pytest.approx(sector.tip_radius_mm, abs=1e-9)


def test_bore_cut_planes_and_shoulders_are_exact(sector: sm.SectorMesh) -> None:
    kind = np.array(sector.node_kind)
    radius = np.hypot(sector.points_mm[:, 0], sector.points_mm[:, 1])
    angle = np.arctan2(sector.points_mm[:, 1], sector.points_mm[:, 0]) - 0.5 * math.pi
    assert np.allclose(radius[kind == "bore"], sector.bore_radius_mm, rtol=0.0, atol=1e-12)
    half_span = (0.5 * sector.teeth + 1.0) * sector.pitch_angle_rad
    assert np.allclose(np.abs(angle[kind == "cut"]), half_span, rtol=0.0, atol=1e-13)
    assert int((kind == "cut").sum()) == 2 * 16  # 12 rim rings + 3 layers above the fan ring
    assert float(radius[kind == "cut"].min()) == pytest.approx(sector.bore_radius_mm, abs=1e-12)
    assert float(np.abs(angle).max()) == pytest.approx(half_span, abs=1e-13)
    shoulder = np.unique(sector.quads[sector.quad_tooth == 0])
    on_surface = shoulder[kind[shoulder] == "surface"]
    assert np.allclose(radius[on_surface], sector.root_radius_mm, rtol=0.0, atol=1e-12)
    assert sector.bore_radius_mm < sector.fan_ring_radius_mm < sector.root_radius_mm
    assert sector.root_radius_mm < sector.root_form_radius_mm < sector.tip_form_radius_mm


def test_fine_layers_keep_the_thickness_of_the_template(sector: sm.SectorMesh) -> None:
    template = load_sector_template()
    block = template.tooth
    angle = block.phi * 2.0 * math.pi / template.number_of_teeth
    points = np.column_stack((-block.radius_mm * np.sin(angle), block.radius_mm * np.cos(angle)))

    def lengths(xy: np.ndarray, quads: np.ndarray) -> np.ndarray:
        return np.sort(
            np.concatenate(
                [np.hypot(*(xy[quads[:, k]] - xy[quads[:, (k + 1) % 4]]).T) for k in range(4)]
            )
        )

    zone = block.radius_mm[block.quads].mean(axis=1) > template.fan_ring_radius_mm
    layers = zone & (np.array(template.tooth_grid_quads) == 0)
    assert (int(zone.sum()), int(layers.sum())) == (600, 400)
    chosen = (sector.quad_tooth == 3) & (sector.quad_zone == 1) & (sector.quad_head == 0)
    assert int(chosen.sum()) == 400
    # the gear is the gear of the template: the fine layers along the fillets keep their edges
    here = lengths(sector.points_mm, sector.quads[chosen])
    reference = lengths(points, block.quads[layers])
    assert float(np.abs(here / reference - 1.0).max()) < 0.02
    assert float(here.min()) > 0.016


def test_form_points_and_tip_corners_are_nodes(
    kst_e: GenerationResult, sector: sm.SectorMesh
) -> None:
    kind = np.array(sector.node_kind)
    radius = np.hypot(sector.points_mm[:, 0], sector.points_mm[:, 1])[kind == "surface"]
    # two nodes per tooth exactly on the root form circle and on the tip form circle
    assert int((np.abs(radius - sector.root_form_radius_mm) < 1e-9).sum()) == 2 * sector.teeth
    assert int((np.abs(radius - sector.tip_form_radius_mm) < 1e-9).sum()) == 2 * sector.teeth
    # the tip circle begins at a node: 5 faces of the template on each half of it
    # (on the chords of the sampled tip circle: within 1e-7 mm of it)
    assert int((np.abs(radius - sector.tip_radius_mm) < 1e-7).sum()) == 11 * sector.teeth
    # a gear without tip edge break: the tip corner of the template is its sharp corner, and
    # the nodes of the edge break lie on the involute
    pinion = sm.sector_mesh(kst_e, "pinion", teeth=3, rim_rings=12)
    assert pinion.tip_form_radius_mm == pytest.approx(pinion.tip_radius_mm, abs=1e-9)
    kind = np.array(pinion.node_kind)
    radius = np.hypot(pinion.points_mm[:, 0], pinion.points_mm[:, 1])[kind == "surface"]
    assert int((np.abs(radius - pinion.tip_radius_mm) < 1e-7).sum()) == 11 * pinion.teeth
    assert float(sm.scaled_jacobians(pinion.points_mm, pinion.quads).min()) > 0.5


@pytest.mark.parametrize(
    ("case", "role"),
    [
        ("kst_e", "pinion"),
        ("fzg_c", "pinion"),
        ("fzg_c", "wheel"),
        ("plastic_m05_z20", "wheel"),
        ("a_x2_only_z18_45", "pinion"),
        ("chamfer_hk_z20_34", "wheel"),
        ("undercut_z12_x0", "wheel"),
    ],
)
def test_other_gears_are_meshed_with_the_quality_of_the_reference(case: str, role: str) -> None:
    mesh = sm.sector_mesh(_generation(case), role, teeth=3, rim_rings=12)  # type: ignore[arg-type]
    # with and without tip edge break, undercut, modules from 0.5 to 4.5 mm
    assert float(sm.scaled_jacobians(mesh.points_mm, mesh.quads).min()) > 0.5
    assert len(mesh.quads) == 3 * (TOOTH_QUADS - 13 * 4) + 2 * (SHOULDER_QUADS - 13 * 4)
    edges = np.concatenate(
        [
            np.hypot(
                *(mesh.points_mm[mesh.quads[:, k]] - mesh.points_mm[mesh.quads[:, (k + 1) % 4]]).T
            )
            for k in range(4)
        ]
    )
    module = (mesh.tip_radius_mm - mesh.root_radius_mm) / 2.25
    assert float(edges.min()) > 0.008 * module


def test_a_contour_the_template_does_not_fit_raises(
    kst_e: GenerationResult, monkeypatch: pytest.MonkeyPatch
) -> None:
    # every packaged gear meets the limit of the element quality; a stricter limit shows that
    # a mesh below it is refused
    monkeypatch.setattr(sm, "MIN_CORNER_SINE", 0.9)
    with pytest.raises(GeometryInfeasibleError, match="corner sine"):
        sm.sector_mesh(kst_e, "wheel", teeth=3, rim_rings=12)
    monkeypatch.undo()
    # a gear too small for twelve rim rings below its root circle
    with pytest.raises(GeometryInfeasibleError, match="circles of the sector"):
        sm.sector_mesh(_generation("small_z8_x05"), "pinion", teeth=3, rim_rings=12)


def test_inputs_of_the_sector_outside_the_scope_raise(kst_e: GenerationResult) -> None:
    with pytest.raises(NotSupportedError):
        sm.sector_mesh(_generation("helix20_z25_65"), "wheel", teeth=3, rim_rings=12)
    for teeth, rings in ((0, 12), (51, 12), (3, 0), (3, 26), (2.5, 12), (3, True)):
        with pytest.raises(InputRangeError):
            sm.sector_mesh(kst_e, "wheel", teeth=teeth, rim_rings=rings)  # type: ignore[arg-type]
    with pytest.raises(InputRangeError):
        sm.sector_mesh("kst_e", "wheel", teeth=3, rim_rings=12)  # type: ignore[arg-type]
    with pytest.raises(InputRangeError):
        sm.sector_mesh(kst_e, "sun", teeth=3, rim_rings=12)  # type: ignore[arg-type]
    for bore in (-1.0, 0.0, math.nan):
        with pytest.raises(InputRangeError):
            sm.sector_mesh(kst_e, "wheel", teeth=3, rim_rings=12, bore_radius_mm=bore)
    with pytest.raises(GeometryInfeasibleError):
        sm.sector_mesh(kst_e, "wheel", teeth=3, rim_rings=12, bore_radius_mm=24.0)
    chosen = sm.sector_mesh(kst_e, "wheel", teeth=3, rim_rings=12, bore_radius_mm=15.0)
    assert chosen.bore_radius_mm == 15.0


@settings(max_examples=25, deadline=None)
@given(teeth=st.integers(min_value=1, max_value=9), rings=st.integers(min_value=1, max_value=25))
def test_any_number_of_teeth_and_rim_rings_gives_a_patch(teeth: int, rings: int) -> None:
    mesh = sm.sector_mesh(_KST_E, "wheel", teeth=teeth, rim_rings=rings)
    removed = RIM_QUADS_PER_RING * (TEMPLATE_RINGS - rings)
    assert len(mesh.quads) == teeth * (TOOTH_QUADS - removed) + 2 * (SHOULDER_QUADS - removed)
    counts = _edge_counts(mesh.quads)
    assert set(counts.values()) == {1, 2}
    assert len(mesh.points_mm) - len(counts) + len(mesh.quads) == 1
    assert float(sm.scaled_jacobians(mesh.points_mm, mesh.quads).min()) > 0.44
    assert mesh.rim_rings == rings and mesh.teeth == teeth
    radius = np.hypot(mesh.points_mm[:, 0], mesh.points_mm[:, 1])
    assert float(radius.min()) == pytest.approx(mesh.bore_radius_mm, abs=1e-12)


def test_harmonic_continuation_is_periodic_across_an_interface() -> None:
    # a strip of 8 x 5 cells, periodic in x: the column 8 is the column 0 again
    columns, rows = 8, 5
    points = np.array([[float(i), float(j)] for j in range(rows + 1) for i in range(columns + 1)])
    index = np.arange((rows + 1) * (columns + 1)).reshape(rows + 1, columns + 1)
    quads = np.array(
        [
            [index[j, i], index[j, i + 1], index[j + 1, i + 1], index[j + 1, i]]
            for j in range(rows)
            for i in range(columns)
        ]
    )
    same_as = np.arange(len(points))
    same_as[index[:, columns]] = index[:, 0]
    fixed = np.zeros(len(points), dtype=bool)
    fixed[index[0]] = fixed[index[rows]] = True

    def solve(shift: int) -> np.ndarray:
        values = np.zeros((len(points), 1))
        top = [
            math.sin(2.0 * math.pi * k / columns) + 0.3 * math.cos(4.0 * math.pi * k / columns)
            for k in range(columns)
        ]
        for i in range(columns + 1):
            values[index[rows, i], 0] = top[(i - shift) % columns]
        return sm._harmonic(points, quads, fixed, values, same_as)[:, 0][index]

    plain = solve(0)
    assert np.allclose(plain[:, columns], plain[:, 0], rtol=0.0, atol=1e-14)
    assert float(np.abs(plain[1:rows]).max()) > 0.05
    # the data moved by three columns give the solution moved by three columns: the interface
    # is a place like any other (an edge on it must not count twice)
    moved = solve(3)
    assert np.allclose(moved[:, 3:columns], plain[:, : columns - 3], rtol=0.0, atol=1e-13)
    assert np.allclose(moved[:, :3], plain[:, columns - 3 : columns], rtol=0.0, atol=1e-13)


# --- solid and sets -------------------------------------------------------------------------------------


def test_sweep_stacks_the_transverse_mesh(sector: sm.SectorMesh, solid: so.SolidMesh) -> None:
    n, m = len(sector.points_mm), len(sector.quads)
    assert solid.layers == 4
    assert solid.nodes_mm.shape == (5 * n, 3) and solid.hexes.shape == (4 * m, 8)
    assert solid.z_levels_mm.tolist() == [-7.5, -3.75, 0.0, 3.75, 7.5]
    for level, z in enumerate(solid.z_levels_mm):
        assert np.array_equal(solid.nodes_mm[level * n : (level + 1) * n, :2], sector.points_mm)
        assert set(solid.nodes_mm[level * n : (level + 1) * n, 2].tolist()) == {float(z)}
    assert np.array_equal(solid.hexes[:m, :4], sector.quads)
    assert np.array_equal(solid.hexes[:m, 4:], sector.quads + n)
    assert float(so.hex_corner_volumes(solid).min()) > 0.0
    shifted = so.extrude(sector, face_width_mm=10.0, layers=1, z_centre_mm=2.0)
    assert shifted.z_levels_mm.tolist() == [-3.0, 7.0]
    for width, layers in ((0.0, 4), (-1.0, 4), (15.0, 0), (15.0, 2.5), (math.inf, 4)):
        with pytest.raises(InputRangeError):
            so.extrude(sector, face_width_mm=width, layers=layers)  # type: ignore[arg-type]
    with pytest.raises(InputRangeError):
        so.extrude("sector", face_width_mm=15.0, layers=4)  # type: ignore[arg-type]


def test_tooth_halves_partition_the_tooth_zone(
    sector: sm.SectorMesh, solid: so.SolidMesh, sets: so.GearSets
) -> None:
    m = len(sector.quads)
    zone = set(sets.element_sets["WHEEL_TOOTH_ZONE"].tolist())
    rim = set(sets.element_sets["WHEEL_RIM"].tolist())
    assert zone | rim == set(range(len(solid.hexes))) and not zone & rim
    assert len(sets.element_sets["WHEEL"]) == len(solid.hexes)
    in_teeth: set[int] = set()
    for tooth in range(1, 6):
        left = set(sets.element_sets[f"WHEEL_T{tooth}_LEFT_HALF"].tolist())
        right = set(sets.element_sets[f"WHEEL_T{tooth}_RIGHT_HALF"].tolist())
        assert len(left) == len(right) == 4 * 300 and not left & right
        quads = {element % m for element in left | right}
        assert quads == set(
            np.flatnonzero((sector.quad_tooth == tooth) & (sector.quad_zone == 1)).tolist()
        )
        for side, half in (("LEFT", left), ("RIGHT", right)):
            root = set(sets.element_sets[f"WHEEL_T{tooth}_{side}_ROOT"].tolist())
            head = set(sets.element_sets[f"WHEEL_T{tooth}_{side}_HEAD"].tolist())
            assert root | head == half and not root & head
            assert (len(root), len(head)) == (4 * 200, 4 * 100)
            root_layer = set(sets.element_sets[f"WHEEL_T{tooth}_{side}_ROOT_LAYER1"].tolist())
            head_layer = set(sets.element_sets[f"WHEEL_T{tooth}_{side}_HEAD_LAYER1"].tolist())
            layer = set(sets.element_sets[f"WHEEL_T{tooth}_{side}_LAYER1"].tolist())
            assert root_layer | head_layer == layer and not root_layer & head_layer
            assert root_layer == {
                int(e) for e, _ in sets.surfaces[f"WHEEL_T{tooth}_{side}_SURF_ROOT"]
            }
            # 65 faces on 64 elements: the element at the tip corner has two faces on the surface
            assert layer <= half and len(layer) == 4 * 64
            centre = solid.nodes_mm[solid.hexes[sorted(half)]].mean(axis=1)
            angle = np.arctan2(centre[:, 1], centre[:, 0]) - 0.5 * math.pi
            offset = angle - (tooth - 3) * sector.pitch_angle_rad
            assert bool(np.all(offset > 0.0)) if side == "LEFT" else bool(np.all(offset < 0.0))
        assert not in_teeth & (left | right)
        in_teeth |= left | right
    # the root of a tooth space and the head of a tooth are joined from the halves
    for tooth in range(1, 5):
        name = f"WHEEL_ROOT_T{tooth}_T{tooth + 1}"
        for ending in ("", "_LAYER1"):
            assert set(sets.element_sets[f"{name}{ending}"].tolist()) == set(
                sets.element_sets[f"WHEEL_T{tooth}_LEFT_ROOT{ending}"].tolist()
            ) | set(sets.element_sets[f"WHEEL_T{tooth + 1}_RIGHT_ROOT{ending}"].tolist())
        faces = {(int(e), int(f)) for e, f in sets.surfaces[f"{name}_SURF"]}
        assert faces == {
            (int(e), int(f)) for e, f in sets.surfaces[f"WHEEL_T{tooth}_LEFT_SURF_ROOT"]
        } | {(int(e), int(f)) for e, f in sets.surfaces[f"WHEEL_T{tooth + 1}_RIGHT_SURF_ROOT"]}
        # one connected fillet from flank to flank: its nodes lie between the two tooth centres
        xy = solid.nodes_mm[sets.node_sets[f"{name}_SURF_NODES"], :2]
        angle = (np.arctan2(xy[:, 1], xy[:, 0]) - 0.5 * math.pi) / sector.pitch_angle_rad
        assert tooth - 3.0 < float(angle.min()) and float(angle.max()) < tooth - 2.0
    for tooth in range(1, 6):
        name = f"WHEEL_HEAD_T{tooth}"
        assert set(sets.element_sets[name].tolist()) == set(
            sets.element_sets[f"WHEEL_T{tooth}_LEFT_HEAD"].tolist()
        ) | set(sets.element_sets[f"WHEEL_T{tooth}_RIGHT_HEAD"].tolist())
        assert len(sets.surfaces[f"{name}_SURF"]) == sum(
            len(sets.surfaces[f"WHEEL_T{tooth}_{side}_SURF_{part}"])
            for side in ("LEFT", "RIGHT")
            for part in ("FLANK", "TIP")
        )
    # the tooth zone of the shoulders belongs to no tooth
    assert zone - in_teeth == {element for element in zone if sector.quad_tooth[element % m] == 0}


def test_surfaces_are_outward_faces_of_the_contour(
    sector: sm.SectorMesh, solid: so.SolidMesh, sets: so.GearSets
) -> None:
    # nodes of the faces S3 to S6 of a C3D8 (Abaqus 2025, 'Three-dimensional solid element
    # library', hexahedron element faces: 1-5-6-2, 2-6-7-3, 3-7-8-4, 4-8-5-1), 0-based
    face_nodes = {3: (0, 4, 5, 1), 4: (1, 5, 6, 2), 5: (2, 6, 7, 3), 6: (3, 7, 4, 0)}
    on_surface = np.zeros(len(sector.points_mm), dtype=bool)
    on_surface[sector.surface_path] = True
    n = len(sector.points_mm)
    position = {int(node): index for index, node in enumerate(sector.surface_path)}
    teeth = sets.surfaces["WHEEL_TEETH_SURF"]
    assert len(teeth) == 4 * 5 * 130  # 130 faces per tooth block and layer
    assert len({(int(e), int(f)) for e, f in teeth}) == len(teeth)
    union: set[tuple[int, int]] = set()
    for tooth in range(1, 6):
        for side in ("LEFT", "RIGHT"):
            name = f"WHEEL_T{tooth}_{side}_SURF"
            half = {(int(e), int(f)) for e, f in sets.surfaces[name]}
            assert len(half) == 4 * 65
            parts = [
                {(int(e), int(f)) for e, f in sets.surfaces[f"{name}_{part}"]}
                for part in ("ROOT", "FLANK", "TIP")
            ]
            assert set().union(*parts) == half and sum(len(p) for p in parts) == len(half)
            assert all(parts)
            union |= half
            nodes = sets.node_sets[f"{name}_NODES"]
            assert len(nodes) == 5 * 66 and bool(np.all(on_surface[nodes % n]))
            # the root part ends at the root form circle, the tip part starts at the tip form circle
            radius = np.hypot(*solid.nodes_mm[sets.node_sets[f"{name}_ROOT_NODES"], :2].T)
            assert float(radius.min()) == pytest.approx(sector.root_radius_mm, abs=1e-9)
            assert float(radius.max()) < sector.root_form_radius_mm + 0.05
            radius = np.hypot(*solid.nodes_mm[sets.node_sets[f"{name}_TIP_NODES"], :2].T)
            assert float(radius.min()) > sector.tip_form_radius_mm - 0.05
    assert union == {(int(e), int(f)) for e, f in teeth}
    for element, face in teeth[:: max(len(teeth) // 400, 1)]:
        corners = solid.nodes_mm[solid.hexes[element]]
        quad = corners[list(face_nodes[int(face)])]
        assert bool(np.all(on_surface[solid.hexes[element][list(face_nodes[int(face)])] % n]))
        del quad
        # the face is the edge of the transverse mesh between two neighbours of the surface path
        a, b = sorted({int(node) % n for node in solid.hexes[element][list(face_nodes[int(face)])]})
        assert abs(position[a] - position[b]) == 1


def test_fixed_nodes_are_the_bore_and_both_cut_planes(
    sector: sm.SectorMesh, solid: so.SolidMesh, sets: so.GearSets
) -> None:
    fixed = sets.node_sets["WHEEL_FESSELUNG"]
    xy = solid.nodes_mm[:, :2]
    radius = np.hypot(xy[:, 0], xy[:, 1])
    angle = np.abs(np.arctan2(xy[:, 1], xy[:, 0]) - 0.5 * math.pi)
    half_span = (0.5 * sector.teeth + 1.0) * sector.pitch_angle_rad
    expected = np.flatnonzero((radius < sector.bore_radius_mm + 1e-9) | (angle > half_span - 1e-9))
    assert np.array_equal(np.sort(fixed), expected)
    # bore arc: 4 columns per pitch over 7 pitches; each cut plane 16 nodes, the corners shared
    assert len(fixed) == 5 * (29 + 2 * 15)
    assert len(sets.node_sets["WHEEL_NODES"]) == len(solid.nodes_mm)
    for prefix in ("wheel", "WHEEL 1", "", 3):
        with pytest.raises(InputRangeError):
            so.gear_sets(solid, prefix)  # type: ignore[arg-type]
    with pytest.raises(InputRangeError):
        so.gear_sets(sector, "WHEEL")  # type: ignore[arg-type]


# --- mesh file ---------------------------------------------------------------------------------------------


def test_mesh_file_holds_the_mesh_and_every_set(solid: so.SolidMesh, sets: so.GearSets) -> None:
    text = ab.mesh_text(solid, sets, element_type="C3D8R", title="kst_e wheel")
    assert text.isascii() and text.endswith("\n")
    lines = text.splitlines()
    assert max(len(line) for line in lines) < 256
    blocks: dict[str, list[str]] = {}
    current = ""
    for line in lines:
        if line.startswith("**"):
            continue
        if line.startswith("*"):
            current = line
            blocks[current] = []
        else:
            blocks[current].append(line)
    assert Counter(key.split(",")[0] for key in blocks) == {
        "*NODE": 1,
        "*ELEMENT": 1,
        "*NSET": len(sets.node_sets) - 1,
        "*ELSET": len(sets.element_sets) - 1,
        "*SURFACE": len(sets.surfaces),
    }
    nodes = np.array(
        [[float(v) for v in row.split(",")] for row in blocks["*NODE, NSET=WHEEL_NODES"]]
    )
    assert np.array_equal(nodes[:, 0], np.arange(1, len(solid.nodes_mm) + 1))
    assert np.allclose(nodes[:, 1:], solid.nodes_mm, rtol=1e-12, atol=1e-12)
    elements = np.array(
        [[int(v) for v in row.split(",")] for row in blocks["*ELEMENT, TYPE=C3D8R, ELSET=WHEEL"]]
    )
    assert np.array_equal(elements[:, 0], np.arange(1, len(solid.hexes) + 1))
    assert np.array_equal(elements[:, 1:], solid.hexes + 1)
    fixed = [int(v) for row in blocks["*NSET, NSET=WHEEL_FESSELUNG"] for v in row.split(",")]
    assert fixed == (sets.node_sets["WHEEL_FESSELUNG"] + 1).tolist()
    half = [int(v) for row in blocks["*ELSET, ELSET=WHEEL_T3_RIGHT_HALF"] for v in row.split(",")]
    assert half == (sets.element_sets["WHEEL_T3_RIGHT_HALF"] + 1).tolist()
    faces = [
        row.split(", ") for row in blocks["*SURFACE, TYPE=ELEMENT, NAME=WHEEL_T3_RIGHT_SURF_ROOT"]
    ]
    assert [(int(e) - 1, int(f[1:])) for e, f in faces] == [
        (int(e), int(f)) for e, f in sets.surfaces["WHEEL_T3_RIGHT_SURF_ROOT"]
    ]
    assert all(len(name) <= 80 for name in (*sets.node_sets, *sets.element_sets, *sets.surfaces))
    for element_type, title in (
        ("c3d8r", "x"),
        ("C3D8R, X", "x"),
        ("C3D8R", "two\nlines"),
        (8, "x"),
    ):
        with pytest.raises(InputRangeError):
            ab.mesh_text(solid, sets, element_type=element_type, title=title)  # type: ignore[arg-type]
    with pytest.raises(InputRangeError):
        ab.mesh_text(sets, solid, element_type="C3D8R", title="x")  # type: ignore[arg-type]
