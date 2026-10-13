"""``gearcore.fe.fibre``: orientation tensors of the mapped elements, zone tensors, the
anisotropy index of FVA 856 I, the angle in the transverse plane and the zone names; the mesh
readers of ``deck`` for node coordinates and sets."""

import math

import numpy as np
import pytest

from gearcore.errors import InputRangeError, ParseError
from gearcore.fe import deck as dk
from gearcore.fe import fibre as fb

EYE = np.eye(3)


def test_orientation_tensor_from_frame_and_state() -> None:
    tensor = fb.orientation_tensor(EYE, 0.7, 0.2)
    assert np.allclose(tensor, np.diag([0.7, 0.2, 0.1]))
    # a turned frame keeps the eigenvalues
    c, s = math.cos(0.4), math.sin(0.4)
    frame = np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
    turned = fb.orientation_tensor(frame, 0.7, 0.2)
    assert np.allclose(np.linalg.eigvalsh(turned), [0.1, 0.2, 0.7])
    assert np.allclose(turned @ frame[:, 0], 0.7 * frame[:, 0])
    with pytest.raises(InputRangeError):
        fb.orientation_tensor(EYE, 0.2, 0.7)  # not ordered
    with pytest.raises(InputRangeError):
        fb.orientation_tensor(EYE, 0.8, 0.3)  # sum above one
    with pytest.raises(InputRangeError):
        fb.orientation_tensor(np.ones((3, 3)), 0.5, 0.3)  # not orthonormal


def test_hexahedron_volumes_exact_for_boxes_and_sheared_boxes() -> None:
    cube = np.array(
        [
            [0, 0, 0],
            [1, 0, 0],
            [1, 1, 0],
            [0, 1, 0],
            [0, 0, 1],
            [1, 0, 1],
            [1, 1, 1],
            [0, 1, 1],
        ],
        dtype=float,
    )
    box = cube * np.array([2.0, 3.0, 0.5])
    shear = cube + np.outer(cube[:, 2], np.array([0.4, -0.2, 0.0]))  # top slid sideways
    volumes = fb.hexahedron_volumes(np.stack([cube, box, shear]))
    assert volumes == pytest.approx([1.0, 3.0, 1.0])
    # a trapezoidal prism: bottom 1 x 1, top 0,5 x 1 at height 1 -> 0,75
    taper = cube.copy()
    taper[4:, 0] *= 0.5
    assert fb.hexahedron_volumes(taper[np.newaxis]) == pytest.approx([0.75])
    inverted = cube[[4, 5, 6, 7, 0, 1, 2, 3]]
    with pytest.raises(InputRangeError):
        fb.hexahedron_volumes(inverted[np.newaxis])


def test_zone_tensor_eigenvalues_and_anisotropy_index() -> None:
    aligned = fb.orientation_tensor(EYE, 1.0, 0.0)
    isotropic = fb.orientation_tensor(EYE, 1.0 / 3.0, 1.0 / 3.0)
    mean = fb.zone_tensor(np.stack([aligned, isotropic]), np.array([1.0, 3.0]))
    values, vectors = fb.eigen_sorted(mean)
    assert values == pytest.approx([0.25, 0.25, 0.5])
    assert abs(vectors[0, 2]) == pytest.approx(1.0)
    assert fb.anisotropy_index(values) == pytest.approx(0.5)
    assert fb.anisotropy_index([1.0, 0.0, 0.0]) == 1.0
    assert fb.anisotropy_index([1 / 3, 1 / 3, 1 / 3]) == pytest.approx(0.0)
    # the printed zones of the report reproduce their AI from their eigenvalues
    for name, (l1, l2, l3, ai) in fb.FVA856_ZONES.items():
        assert l1 <= l2 <= l3, name
        assert l1 + l2 + l3 == pytest.approx(1.0, abs=0.011), name
        assert fb.anisotropy_index([l1, l2, l3]) == pytest.approx(ai, abs=0.011), name
    with pytest.raises(InputRangeError):
        fb.zone_tensor(np.stack([aligned]), np.array([0.0]))
    with pytest.raises(InputRangeError):
        fb.anisotropy_index([0.0, 0.0, 0.0])


def test_in_plane_angle_convention() -> None:
    radial = np.array([0.0, 1.0, 0.0])
    across = np.array([-1.0, 0.0, 0.0])  # the report's arrow: 90° to the left
    assert fb.in_plane_angle(radial, radial, across) == pytest.approx((0.0, 1.0))
    assert fb.in_plane_angle(-radial, radial, across) == pytest.approx((0.0, 1.0))
    assert fb.in_plane_angle(across, radial, across)[0] == pytest.approx(90.0)
    assert fb.in_plane_angle(-across, radial, across)[0] == pytest.approx(90.0)
    tilt_left = radial + across * math.tan(math.radians(20.0))
    assert fb.in_plane_angle(tilt_left, radial, across)[0] == pytest.approx(20.0)
    assert fb.in_plane_angle(-tilt_left, radial, across)[0] == pytest.approx(20.0)
    tilt_right = radial - across * math.tan(math.radians(20.0))
    assert fb.in_plane_angle(tilt_right, radial, across)[0] == pytest.approx(-20.0)
    # a fibre along the axis of the wheel has no in-plane share
    angle, share = fb.in_plane_angle(np.array([0.0, 0.0, 1.0]), radial, across)
    assert share == pytest.approx(0.0)
    with pytest.raises(InputRangeError):
        fb.in_plane_angle(radial, radial, radial)


def test_zone_names_follow_the_report() -> None:
    name = fb.zone_name
    assert name(side="L", kind="flank", depth_mm=0.1, skin_mm=0.2, height_fraction=0.3) == "LFU"
    assert name(side="L", kind="flank", depth_mm=0.1, skin_mm=0.2, height_fraction=0.7) == "LFO"
    assert name(side="R", kind="root", depth_mm=0.2, skin_mm=0.2, height_fraction=0.05) == "RF"
    assert name(side="R", kind="valley", depth_mm=0.0, skin_mm=0.2, height_fraction=-0.1) == "RT"
    assert name(side="L", kind="tip", depth_mm=0.1, skin_mm=0.2, height_fraction=0.98) == "S"
    assert name(side="L", kind="flank", depth_mm=0.3, skin_mm=0.2, height_fraction=0.3) == "LÜM"
    assert name(side="R", kind="flank", depth_mm=0.3, skin_mm=0.2, height_fraction=0.8) == "RÜO"
    assert name(side="L", kind="root", depth_mm=0.3, skin_mm=0.2, height_fraction=0.1) == "LÜU"
    assert name(side="L", kind="tip", depth_mm=0.3, skin_mm=0.2, height_fraction=0.9) == "M"
    assert name(side="L", kind="valley", depth_mm=0.3, skin_mm=0.2, height_fraction=-0.1) == "U"
    assert name(side="L", kind="flank", depth_mm=0.9, skin_mm=0.2, height_fraction=0.5) == "M"
    assert name(side="L", kind="valley", depth_mm=0.9, skin_mm=0.2, height_fraction=-0.3) == "U"
    assert set(fb.ZONE_ORDER) >= set(fb.FVA856_ZONES)
    with pytest.raises(InputRangeError):
        name(side="X", kind="flank", depth_mm=0.1, skin_mm=0.2, height_fraction=0.3)
    with pytest.raises(InputRangeError):
        name(side="L", kind="rim", depth_mm=0.1, skin_mm=0.2, height_fraction=0.3)


def test_third_of_width() -> None:
    assert fb.third_of_width(-7.0, 7.5) == "z-"
    assert fb.third_of_width(0.0, 7.5) == "mid"
    assert fb.third_of_width(2.4, 7.5) == "mid"
    assert fb.third_of_width(2.6, 7.5) == "z+"
    with pytest.raises(InputRangeError):
        fb.third_of_width(8.0, 7.5)


def test_evaluate_zone_reports_the_dominant_direction() -> None:
    radial = np.array([0.0, 1.0, 0.0])
    across = np.array([-1.0, 0.0, 0.0])
    c, s = math.cos(math.radians(30.0)), math.sin(math.radians(30.0))
    e1 = np.array([-s, c, 0.0])  # 30° towards the left of the tooth axis
    e2 = np.array([c, s, 0.0])
    frame = np.stack([e1, e2, np.cross(e1, e2)], axis=1)
    tensors = np.stack([fb.orientation_tensor(frame, 0.8, 0.15)] * 3)
    result = fb.evaluate_zone(
        "LFO", tensors, np.array([1.0, 1.0, 2.0]), [0.8, 0.8, 0.8], radial, across
    )
    assert result.elements == 3 and result.volume_mm3 == pytest.approx(4.0)
    assert result.eigenvalues == pytest.approx((0.05, 0.15, 0.8))
    assert result.anisotropy_index == pytest.approx(1.0 - 0.05 / 0.8)
    assert result.angle_deg == pytest.approx(30.0)
    assert result.in_plane == pytest.approx(1.0)
    assert result.a11_mean == pytest.approx(0.8)
    # the diagonal in the tooth frame: 0,8 cos² 30° + 0,15 sin² 30° along the axis, the rest across,
    # 0,05 along the face width
    assert result.diagonal == pytest.approx(
        (0.8 * c * c + 0.15 * s * s, 0.8 * s * s + 0.15 * c * c, 0.05)
    )
    assert result.tilt_deg == pytest.approx(0.0, abs=1e-9)
    # the same fibres raised by 40° towards +z: the in-plane angle stays, the tilt is 40°
    c40, s40 = math.cos(math.radians(40.0)), math.sin(math.radians(40.0))
    raised = np.array([-s * c40, c * c40, s40])
    other = np.cross(raised, np.array([0.0, 0.0, 1.0]))
    other /= np.linalg.norm(other)
    frame = np.stack([raised, other, np.cross(raised, other)], axis=1)
    tensors = np.stack([fb.orientation_tensor(frame, 0.8, 0.15)] * 2)
    lifted = fb.evaluate_zone("LFO", tensors, np.array([1.0, 1.0]), [0.8, 0.8], radial, across)
    assert lifted.angle_deg == pytest.approx(30.0)
    assert lifted.tilt_deg == pytest.approx(40.0)
    assert lifted.in_plane == pytest.approx(c40)
    # the mirror image (towards −z) gives −40°, and the mean of both halves loses its anisotropy
    mirror = frame * np.array([[1.0], [1.0], [-1.0]])
    tensors = np.stack(
        [fb.orientation_tensor(frame, 0.8, 0.15), fb.orientation_tensor(mirror, 0.8, 0.15)]
    )
    both = fb.evaluate_zone("LFO", tensors, np.array([1.0, 1.0]), [0.8, 0.8], radial, across)
    assert both.eigenvalues[2] < 0.8 - 0.1
    assert both.a11_mean == pytest.approx(0.8)
    with pytest.raises(InputRangeError):
        fb.evaluate_zone("LFO", tensors, np.array([1.0, 1.0, 2.0]), [0.8], radial, across)


MESH = """** comment
*NODE, NSET=WHEEL_NODES
1, 0.0, 0.0, 0.0
2, 1.0, 0.0, 0.0
3, 1.0, 1.0, 0.0
4, 0.0, 1.0, 0.0
5, 0.0, 0.0, 1.0
6, 1.0, 0.0, 1.0
7, 1.0, 1.0, 1.0
8, 0.0, 1.0, 1.0
*ELEMENT, TYPE=C3D8I, ELSET=WHEEL
1, 1, 2, 3, 4, 5, 6, 7, 8
*NSET, NSET=Top
5, 6, 7,
8
*NSET, NSET=all_gen, GENERATE
1, 8, 1
*NSET, NSET=GENERATED_TOP
1, 8
*ELSET, ELSET=one
1
"""


def test_read_node_coordinates_and_sets() -> None:
    nodes = dk.read_node_coordinates(MESH)
    assert len(nodes) == 8 and nodes[7] == (1.0, 1.0, 1.0)
    node_sets, element_sets = dk.read_sets(MESH)
    assert node_sets["WHEEL_NODES"] == tuple(range(1, 9))
    assert node_sets["TOP"] == (5, 6, 7, 8)
    assert node_sets["ALL_GEN"] == tuple(range(1, 9))
    assert node_sets["GENERATED_TOP"] == (1, 8)  # the name is no GENERATE parameter
    assert element_sets["WHEEL"] == (1,) and element_sets["ONE"] == (1,)
    with pytest.raises(ParseError):
        dk.read_sets("*NSET, NSET=A\nOTHER_SET\n")  # a set name inside a set
    with pytest.raises(ParseError):
        dk.read_node_coordinates("*ELEMENT, TYPE=C3D8\n1, 1, 2, 3, 4, 5, 6, 7, 8\n")
    with pytest.raises(ParseError):
        dk.read_sets("*NSET\n1, 2\n")
    with pytest.raises(ParseError):
        dk.read_sets("*NSET, NSET=A, GENERATE\n8, 1\n")
