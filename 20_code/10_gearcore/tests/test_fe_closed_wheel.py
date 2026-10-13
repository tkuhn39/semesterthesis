"""The closed wheel of ``sector_mesh``: every tooth, no shoulders, the ring joined on itself
(for a CONVERSE mapping of the whole part, ADR-116 item 49)."""

import math

import numpy as np
import pytest

from gearcore import data
from gearcore.errors import InputRangeError
from gearcore.fe import sector_mesh as sm
from gearcore.fe import solid as so
from gearcore.generation import compute_generation
from gearcore.io.ste import load_ste, pair_input_from_ste
from gearcore.models.results import GenerationResult


@pytest.fixture(scope="module")
def kst_e() -> GenerationResult:
    return compute_generation(pair_input_from_ste(load_ste(data.stplus_input_path("kst_e"))).pair)


@pytest.fixture(scope="module")
def closed(kst_e: GenerationResult) -> sm.SectorMesh:
    return sm.sector_mesh(kst_e, "wheel", teeth=52, rim_rings=4, closed=True)


@pytest.fixture(scope="module")
def sector(kst_e: GenerationResult) -> sm.SectorMesh:
    return sm.sector_mesh(kst_e, "wheel", teeth=3, rim_rings=4)


def test_closed_wheel_has_every_tooth_and_no_cut(closed: sm.SectorMesh) -> None:
    assert closed.closed and closed.teeth == 52 == closed.number_of_teeth
    kinds = set(closed.node_kind)
    assert "cut" not in kinds and "bore" in kinds
    assert set(np.unique(closed.quad_tooth)) == set(range(1, 53))  # no shoulder quads (0)
    # every node is used, every quad references existing nodes
    assert closed.quads.max() == len(closed.points_mm) - 1
    assert len(np.unique(closed.quads)) == len(closed.points_mm)
    # the seam is shared: no two nodes coincide
    rounded = np.round(closed.points_mm, 6)
    assert len(np.unique(rounded, axis=0)) == len(closed.points_mm)
    # the quads form a closed ring: every edge is shared by exactly two quads except the
    # outline (teeth surface) and the bore
    edges: dict[tuple[int, int], int] = {}
    for quad in closed.quads:
        for k in range(4):
            a, b = int(quad[k]), int(quad[(k + 1) % 4])
            edges[(min(a, b), max(a, b))] = edges.get((min(a, b), max(a, b)), 0) + 1
    boundary = [e for e, n in edges.items() if n == 1]
    boundary_nodes = {n for e in boundary for n in e}
    radius = np.hypot(closed.points_mm[:, 0], closed.points_mm[:, 1])
    # boundary nodes lie on the bore or on the tooth surface, never on a cut plane between
    assert np.all(
        (radius[list(boundary_nodes)] <= closed.bore_radius_mm + 1e-6)
        | (radius[list(boundary_nodes)] >= closed.fan_ring_radius_mm - 1e-6)
    )


def test_closed_wheel_tooth_is_congruent_with_the_sector(
    closed: sm.SectorMesh, sector: sm.SectorMesh
) -> None:
    # the same tooth block in both: the number of quads per tooth agrees
    per_tooth_closed = np.bincount(closed.quad_tooth)[1:]
    per_tooth_sector = np.bincount(sector.quad_tooth)[1:]
    assert np.all(per_tooth_closed == per_tooth_sector[0])
    assert len(closed.quads) == 52 * per_tooth_sector[0]

    # tooth 27 of the closed wheel sits on +y like the middle tooth (2) of the 3-tooth sector:
    # the node positions of both teeth coincide, so a sector mapping fits the full wheel
    def tooth_points(mesh: sm.SectorMesh, tooth: int) -> set[tuple[float, float]]:
        nodes = np.unique(mesh.quads[mesh.quad_tooth == tooth])
        return {(round(float(x), 5), round(float(y), 5)) for x, y in mesh.points_mm[nodes]}

    assert tooth_points(closed, 27) == tooth_points(sector, 2)
    assert closed.tooth_centre_angle_rad(27) == pytest.approx(math.pi / 2)
    assert sector.tooth_centre_angle_rad(2) == pytest.approx(math.pi / 2)
    assert closed.tooth_centre_angle_rad(28) == pytest.approx(math.pi / 2 + closed.pitch_angle_rad)
    with pytest.raises(InputRangeError):
        closed.tooth_centre_angle_rad(53)


def test_closed_wheel_sets_and_sweep(closed: sm.SectorMesh) -> None:
    solid = so.extrude(closed, face_width_mm=15.0, layers=2)
    sets = so.gear_sets(solid, "WHEEL")
    names = set(sets.element_sets)
    assert "WHEEL_ROOT_T52_T1" in names and "WHEEL_ROOT_T1_T2" in names
    assert "WHEEL_HEAD_T52" in names
    fesselung = sets.node_sets["WHEEL_FESSELUNG"]
    nodes = np.asarray(solid.nodes_mm)
    radius = np.hypot(nodes[fesselung, 0], nodes[fesselung, 1])
    assert np.allclose(radius, closed.bore_radius_mm, atol=1e-6)  # the bore alone


def test_closed_wheel_refuses_other_counts(kst_e: GenerationResult) -> None:
    with pytest.raises(InputRangeError):
        sm.sector_mesh(kst_e, "wheel", teeth=51, rim_rings=4, closed=True)
    with pytest.raises(InputRangeError):
        sm.sector_mesh(kst_e, "wheel", teeth=52, rim_rings=4)
