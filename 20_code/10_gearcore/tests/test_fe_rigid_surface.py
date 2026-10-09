"""Rigid tooth surface of the steel gear (``gearcore.fe.rigid_surface`` and its file)."""

import math
from collections import Counter

import numpy as np
import pytest
from matplotlib.path import Path as PolygonPath

from gearcore import contour as ct
from gearcore import data
from gearcore.errors import GeometryInfeasibleError, InputRangeError, NotSupportedError
from gearcore.fe import abaqus as ab
from gearcore.fe import rigid_surface as rs
from gearcore.generation import compute_generation
from gearcore.io.ste import load_ste, pair_input_from_ste
from gearcore.models.results import GenerationResult

WHEEL_LEVELS = np.linspace(-7.5, 7.5, 5)  # four layers of a wheel 15 mm wide


def _generation(case: str) -> GenerationResult:
    return compute_generation(pair_input_from_ste(load_ste(data.stplus_input_path(case))).pair)


@pytest.fixture(scope="module")
def kst_e() -> GenerationResult:
    return _generation("kst_e")


@pytest.fixture(scope="module")
def surface(kst_e: GenerationResult) -> rs.RigidSurface:
    levels = rs.surface_z_levels(WHEEL_LEVELS, 17.0)
    return rs.rigid_surface(kst_e, "pinion", teeth=7, max_edge_mm=0.05, z_levels_mm=levels)


def test_levels_are_those_of_the_mating_gear_and_the_overhang() -> None:
    levels = rs.surface_z_levels(WHEEL_LEVELS, 17.0)
    assert levels.tolist() == [-8.5, -7.5, -3.75, 0.0, 3.75, 7.5, 8.5]
    # the reference division: 80 layers of 0.1875 mm, the overhang of 1 mm in six steps
    fine = rs.surface_z_levels(np.linspace(-7.5, 7.5, 81), 17.0)
    assert len(fine) == 81 + 12
    assert float(np.diff(fine).max()) <= 0.1875 * (1.0 + 1e-9)
    assert set(np.linspace(-7.5, 7.5, 81).tolist()) <= set(fine.tolist())
    assert (fine[0], fine[-1]) == (-8.5, 8.5)
    # a narrower surface keeps the levels inside it and gets its own ends
    narrow = rs.surface_z_levels(WHEEL_LEVELS, 10.0, z_centre_mm=1.0)
    assert narrow.tolist() == [-4.0, -3.75, 0.0, 3.75, 6.0]
    for levels_in, width in (([0.0], 17.0), ([0.0, math.nan], 17.0), (WHEEL_LEVELS, 0.0)):
        with pytest.raises(InputRangeError):
            rs.surface_z_levels(np.asarray(levels_in), width)


def test_surface_has_no_volume_and_no_end_faces(surface: rs.RigidSurface) -> None:
    n, levels = surface.profile_nodes, len(surface.z_levels_mm)
    assert surface.nodes_mm.shape == (n * levels, 3)
    assert surface.quads.shape == ((n - 1) * (levels - 1), 4)
    z = surface.nodes_mm[surface.quads][:, :, 2]
    # every element has two nodes on one level and two on the next: none lies in a z-plane
    level_of = {float(v): k for k, v in enumerate(surface.z_levels_mm)}
    for row in z[:: max(len(z) // 500, 1)].tolist():
        assert sorted(Counter(level_of[v] for v in row).values()) == [2, 2]
        assert max(level_of[v] for v in row) - min(level_of[v] for v in row) == 1
    # one open strip: the edges along the profile at both ends belong to one element only
    edges: Counter[tuple[int, int]] = Counter()
    for quad in surface.quads.tolist():
        for k in range(4):
            a, b = quad[k], quad[(k + 1) % 4]
            edges[(min(a, b), max(a, b))] += 1
    assert set(edges.values()) == {1, 2}
    assert sum(1 for count in edges.values() if count == 1) == 2 * (n - 1) + 2 * (levels - 1)
    assert not surface.nodes_mm.flags.writeable


def test_profile_lies_on_the_contour_with_its_corners_as_nodes(
    kst_e: GenerationResult, surface: rs.RigidSurface
) -> None:
    contour = ct.tooth_contour(kst_e, "pinion", points=3000)
    profile = surface.nodes_mm[: surface.profile_nodes, :2]
    steps = np.hypot(*(profile[1:] - profile[:-1]).T)
    assert float(steps.max()) <= 0.05 * (1.0 + 1e-9) and float(steps.min()) > 0.01
    angle = np.arctan2(profile[:, 0], profile[:, 1])  # from +y towards +x
    assert bool(np.all(np.diff(angle) < 0.0))  # counter-clockwise, one open path
    half_span = 0.5 * surface.teeth * surface.pitch_angle_rad
    assert angle[0] == pytest.approx(half_span, abs=1e-12)
    assert angle[-1] == pytest.approx(-half_span, abs=1e-12)
    middle = profile[np.abs(angle) < 0.5 * surface.pitch_angle_rad]
    radius = np.hypot(middle[:, 0], middle[:, 1])
    on_root_circle = np.abs(radius - 0.5 * contour.generated_root_diameter_mm) < 1e-9
    assert float(ct.distances(contour, middle[~on_root_circle]).max()) < 1e-3  # micrometres
    # the points where two elements of the contour meet are nodes
    coarse = ct.tooth_contour(kst_e, "pinion", points=rs.CONTOUR_POINTS)
    for name in ct.SEGMENTS[:-1]:
        segment = coarse.segment(name)
        if len(segment):
            assert float(np.hypot(*(middle - segment[-1]).T).min()) < 1e-9
    # every tooth is a rotation of the middle one, and the surface is mirror symmetric
    per_tooth = (surface.profile_nodes - 1) // surface.teeth
    first = profile[:per_tooth]
    for tooth in range(1, surface.teeth):
        turn = -tooth * surface.pitch_angle_rad
        c, s = math.cos(turn), math.sin(turn)
        block = profile[tooth * per_tooth : (tooth + 1) * per_tooth]
        back = np.column_stack(
            (c * block[:, 0] - s * block[:, 1], s * block[:, 0] + c * block[:, 1])
        )
        assert np.allclose(back, first, rtol=0.0, atol=1e-11)
    assert np.allclose(profile[::-1] * np.array([-1.0, 1.0]), profile, rtol=0.0, atol=1e-9)


def _turning_angles_deg(surface: rs.RigidSurface) -> tuple[np.ndarray, np.ndarray]:
    """Turning angle between consecutive facets of the profile and the radius of the node
    between them."""
    profile = surface.nodes_mm[: surface.profile_nodes, :2]
    step = profile[1:] - profile[:-1]
    heading = np.arctan2(step[:, 1], step[:, 0])
    turn = np.degrees(np.abs(np.remainder(np.diff(heading) + np.pi, 2.0 * np.pi) - np.pi))
    return turn, np.hypot(*profile[1:-1].T)


def test_tip_rounding_replaces_the_tip_corners_by_tangent_arcs(kst_e: GenerationResult) -> None:
    levels = rs.surface_z_levels(WHEEL_LEVELS, 17.0)
    sharp = rs.rigid_surface(kst_e, "pinion", teeth=1, max_edge_mm=0.05, z_levels_mm=levels)
    rounded = rs.rigid_surface(
        kst_e, "pinion", teeth=1, max_edge_mm=0.05, z_levels_mm=levels, tip_rounding_mm=0.05
    )
    r_a = float(np.hypot(*sharp.nodes_mm[: sharp.profile_nodes, :2].T).max())
    turn_sharp, radius_sharp = _turning_angles_deg(sharp)
    turn_round, radius_round = _turning_angles_deg(rounded)
    near_tip_sharp = radius_sharp > r_a - 0.2
    near_tip_round = radius_round > r_a - 0.2
    # the sharp corner turns by 90 deg minus the tip pressure angle in one node; the rounding
    # spreads the turn over at least ROUNDING_FACETS facets
    assert float(turn_sharp[near_tip_sharp].max()) > 45.0
    assert float(turn_round[near_tip_round].max()) < float(turn_sharp[near_tip_sharp].max()) / 3.0
    assert rounded.profile_nodes > sharp.profile_nodes
    # the rounded profile stays on or inside the sharp one: no node beyond the tip circle, the
    # arcs at most r (1 - cos 45 deg) = 0,015 mm inside the sharp profile and inside the gear
    sharp_profile = sharp.nodes_mm[: sharp.profile_nodes, :2]
    profile = rounded.nodes_mm[: rounded.profile_nodes, :2]
    assert float(np.hypot(*profile.T).max()) <= r_a + 1e-5  # the arcs end on the tip circle
    arcs = profile[np.hypot(*profile.T) > r_a - 0.06]
    a, b = sharp_profile[:-1], sharp_profile[1:]
    ab = b - a
    along = np.clip(
        ((arcs[:, None, :] - a[None, :, :]) * ab[None, :, :]).sum(axis=2)
        / (ab * ab).sum(axis=1)[None, :],
        0.0,
        1.0,
    )
    foot = a[None, :, :] + along[:, :, None] * ab[None, :, :]
    inside = np.hypot(*(arcs[:, None, :] - foot).transpose(2, 0, 1)).min(axis=1)
    assert float(inside.max()) < 0.016 and float(inside.max()) > 0.005
    # the interior points of the arcs lie inside the sharp tooth (closed through the axis),
    # not outside it: the rounding removes material
    tooth = PolygonPath(np.vstack((sharp_profile, [[0.0, 0.0]])))
    assert tooth.contains_points(arcs[inside > 0.002]).all()
    # the profile stays one counter-clockwise path and mirror symmetric
    angle = np.arctan2(profile[:, 0], profile[:, 1])
    assert bool(np.all(np.diff(angle) < 0.0))
    assert np.allclose(profile[::-1] * np.array([-1.0, 1.0]), profile, rtol=0.0, atol=1e-9)
    with pytest.raises(InputRangeError):
        rs.rigid_surface(
            kst_e, "pinion", teeth=1, max_edge_mm=0.05, z_levels_mm=levels, tip_rounding_mm=-0.1
        )
    with pytest.raises(GeometryInfeasibleError):
        rs.rigid_surface(
            kst_e, "pinion", teeth=1, max_edge_mm=0.05, z_levels_mm=levels, tip_rounding_mm=2.0
        )


def test_positive_side_of_the_elements_faces_out_of_the_gear(
    kst_e: GenerationResult, surface: rs.RigidSurface
) -> None:
    gear = PolygonPath(ct.gear_polygon(ct.tooth_contour(kst_e, "pinion", points=400)))
    quads = surface.quads[: surface.profile_nodes - 1]
    corner = surface.nodes_mm[quads]
    normal = np.cross(corner[:, 1] - corner[:, 0], corner[:, 3] - corner[:, 0])
    normal /= np.linalg.norm(normal, axis=1)[:, None]
    assert np.allclose(normal[:, 2], 0.0, atol=1e-12)
    centre = corner.mean(axis=1)
    assert not gear.contains_points((centre + 2e-3 * normal)[:, :2]).any()
    assert gear.contains_points((centre - 2e-3 * normal)[:, :2]).all()


def test_surface_file_holds_the_rigid_elements(surface: rs.RigidSurface) -> None:
    text = ab.rigid_surface_text(surface, "PINION", title="kst_e pinion")
    assert text.isascii()
    lines = [line for line in text.splitlines() if not line.startswith("**")]
    keywords = [line for line in lines if line.startswith("*")]
    assert keywords == [
        "*NODE, NSET=PINION_NODES",
        "*ELEMENT, TYPE=R3D4, ELSET=PINION",
        "*SURFACE, TYPE=ELEMENT, NAME=PINION_SURF",
    ]
    assert lines[-1] == "PINION, SPOS"
    node_lines = lines[1 : 1 + len(surface.nodes_mm)]
    nodes = np.array([[float(v) for v in row.split(",")] for row in node_lines])
    assert np.allclose(nodes[:, 1:], surface.nodes_mm, rtol=1e-12, atol=1e-12)
    element_lines = lines[2 + len(surface.nodes_mm) : -2]
    elements = np.array([[int(v) for v in row.split(",")] for row in element_lines])
    assert np.array_equal(elements[:, 1:], surface.quads + 1)
    assert np.array_equal(elements[:, 0], np.arange(1, len(surface.quads) + 1))
    for prefix, title in (("pinion", "x"), ("PINION", "a\nb"), (1, "x")):
        with pytest.raises(InputRangeError):
            ab.rigid_surface_text(surface, prefix, title=title)  # type: ignore[arg-type]
    with pytest.raises(InputRangeError):
        ab.rigid_surface_text("surface", "PINION", title="x")  # type: ignore[arg-type]


def test_inputs_of_the_surface_outside_the_scope_raise(kst_e: GenerationResult) -> None:
    levels = rs.surface_z_levels(WHEEL_LEVELS, 17.0)
    with pytest.raises(NotSupportedError):
        rs.rigid_surface(
            _generation("helix20_z25_65"), "pinion", teeth=3, max_edge_mm=0.05, z_levels_mm=levels
        )
    for teeth, edge in ((0, 0.05), (51, 0.05), (2.5, 0.05), (3, 0.0), (3, -1.0), (3, math.nan)):
        with pytest.raises(InputRangeError):
            rs.rigid_surface(
                kst_e,
                "pinion",
                teeth=teeth,  # type: ignore[arg-type]
                max_edge_mm=edge,
                z_levels_mm=levels,
            )
    for bad in (np.array([0.0]), np.array([1.0, 0.0]), np.array([0.0, math.inf])):
        with pytest.raises(InputRangeError):
            rs.rigid_surface(kst_e, "pinion", teeth=3, max_edge_mm=0.05, z_levels_mm=bad)
    with pytest.raises(InputRangeError):
        rs.rigid_surface("kst_e", "pinion", teeth=3, max_edge_mm=0.05, z_levels_mm=levels)  # type: ignore[arg-type]
    # the wheel of a pair can be the rigid gear as well
    wheel = rs.rigid_surface(kst_e, "wheel", teeth=3, max_edge_mm=0.1, z_levels_mm=levels)
    assert wheel.number_of_teeth == 52 and wheel.teeth == 3
