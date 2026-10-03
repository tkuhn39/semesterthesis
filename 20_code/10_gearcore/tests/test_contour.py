"""Transverse tooth contour against the STplus contour exports and by construction.

The STplus export (``contour_wz1/2.json``, transverse section, one tooth from root to root) is the
oracle for the shape: fillet, involute and tip of every own run must lie within the gate of the
plan (5 um on the involute, 10 um in the root); the values reached are pinned far below.
"""

import math

import numpy as np
import pytest

from gearcore import contour as ct
from gearcore import generation as gn
from gearcore import involute as iv
from gearcore.data import has_stplus, stplus_case_dirs
from gearcore.errors import GeometryInfeasibleError, InputRangeError
from gearcore.models.common import Pair
from gearcore.parity import compute_generation_from_data, generation_data
from gearcore.stplus_program import stplus_default, stplus_transverse_residual_tip_thickness

GATE_INVOLUTE_UM = 5.0
GATE_ROOT_UM = 10.0
REACHED_UM = {"fillet": 0.6, "involute": 0.25, "tip": 0.01}
"""Largest deviations reached on the 14 own runs (2026-09-30: 0,587 / 0,241 / 0,006 um); a
regression beyond fails."""


def _own_runs_with_contours() -> list[tuple[str, int]]:
    cases = []
    for path in stplus_case_dirs():
        for gear in (1, 2):
            if has_stplus(path.name, f"contour_wz{gear}"):
                cases.append((path.name, gear))
    return cases


def _generation(case: str):
    """The pair as STplus generated it (allowances of its output, its tip diameters) and the
    generation; ``result.inputs`` is that pair as the contract validated it."""
    data = generation_data(case)
    result = compute_generation_from_data(data, data.values)
    return result.inputs, result


def _with_stplus_chamfer(pair, result):
    """A chamfer given by h_K only takes its residual thickness from the STplus default
    (tangential 0,7 h_K, manual p. 19), applied explicitly here."""
    assert stplus_default("tip_chamfer_tangential").value == 0.7
    gears = []
    for gear, generated in zip(pair.gears.as_tuple(), result.gears.as_tuple(), strict=True):
        if gear.tip_chamfer_radial_mm > 0.0 and gear.residual_tip_thickness_mm is None:
            s_aK = stplus_transverse_residual_tip_thickness(
                generated.transverse_tip_tooth_thickness_mm,
                generated.normal_tip_tooth_thickness_mm,
                gear.tip_chamfer_radial_mm,
            )
            gears.append(gear.model_copy(update={"residual_tip_thickness_mm": s_aK}))
        else:
            gears.append(gear)
    pair = pair.model_copy(update={"gears": Pair(pinion=gears[0], wheel=gears[1])})
    return pair, gn.compute_generation(pair)


@pytest.mark.oracle
@pytest.mark.parametrize("case, gear", _own_runs_with_contours())
def test_contour_matches_the_stplus_export(case: str, gear: int) -> None:
    pair, result = _with_stplus_chamfer(*_generation(case))
    role = "pinion" if gear == 1 else "wheel"
    ours = ct.tooth_contour(result, role)
    reference = ct.stplus_contour(case, gear)
    diff = ct.compare(ours, reference)
    assert diff.reference_points == len(reference) and diff.reference_points >= 50
    assert diff.involute_max_um <= GATE_INVOLUTE_UM and diff.fillet_max_um <= GATE_ROOT_UM
    assert diff.fillet_max_um <= REACHED_UM["fillet"], (case, gear, diff)
    assert diff.involute_max_um <= REACHED_UM["involute"], (case, gear, diff)
    assert diff.tip_max_um <= REACHED_UM["tip"], (case, gear, diff)
    assert diff.fillet_points > 0 and diff.involute_points > 0
    # the STplus contour starts where the fillet leaves the root circle, like ours (spur gears:
    # on the root circle within the six digits of the export; helical gears: its first vertex
    # lies up to 4 um above it and 0,1 mm along the fillet)
    first, ours_first = reference[0], ours.as_array()[0]
    r_f = 0.5 * ours.generated_root_diameter_mm
    assert r_f - 1e-4 <= np.hypot(*first) <= r_f + 0.005  # the export prints seven digits
    assert np.linalg.norm(first - ours_first) < 0.2
    assert ct.ContourDiff.model_validate_json(diff.model_dump_json()) == diff


@pytest.mark.oracle
def test_undercut_contours_are_covered() -> None:
    undercut = []
    for case, gear in _own_runs_with_contours():
        _, result = _generation(case)
        if result.gears.as_tuple()[gear - 1].undercut:
            undercut.append((case, gear))
    assert set(undercut) == {
        ("fzg_c", 1),
        ("undercut_z12_x0", 1),
        ("neg_shift_z17_xm08", 1),
        ("small_z8_x05", 1),
    }


def test_contour_structure() -> None:
    pair, result = _with_stplus_chamfer(*_generation("chamfer_hk_z20_34"))
    contour = ct.tooth_contour(result, "pinion", points=64)
    names = [s.name for s in contour.segments]
    assert names == list(ct.SEGMENTS)
    assert contour.segments[0].start == 0 and contour.segments[-1].end == len(contour.points)
    for previous, following in zip(contour.segments, contour.segments[1:], strict=False):
        assert previous.end == following.start
    points = contour.as_array()
    radius = np.hypot(points[:, 0], points[:, 1])
    # symmetric about +y, runs from the left root over the tip to the right root
    assert np.allclose(points[::-1, 0], -points[:, 0], atol=1e-12)
    assert np.allclose(points[::-1, 1], points[:, 1], atol=1e-12)
    assert radius[0] == pytest.approx(0.5 * contour.generated_root_diameter_mm)
    assert np.max(radius) == pytest.approx(0.5 * contour.tip_diameter_mm)
    fillet = contour.segment("left_fillet")
    assert np.hypot(*fillet[-1]) == pytest.approx(0.5 * contour.root_form_diameter_mm, rel=1e-12)
    involute = contour.segment("left_involute")
    # the point shared by two elements belongs to the earlier one (no zero-length segment)
    assert np.hypot(*involute[0]) > 0.5 * contour.root_form_diameter_mm
    assert np.hypot(*involute[-1]) == pytest.approx(0.5 * contour.tip_form_diameter_mm, rel=1e-12)
    chamfer = contour.segment("left_tip_flank")
    assert len(chamfer) == 15 and np.hypot(*chamfer[-1]) == pytest.approx(
        0.5 * contour.tip_diameter_mm
    )
    assert len(contour.segment("tip")) == 15  # the shared points belong to the elements before
    assert ct.ToothContour.model_validate_json(contour.model_dump_json()) == contour
    with pytest.raises(InputRangeError):
        contour.segment("root")


def test_gear_polygon_is_closed_and_periodic() -> None:
    pair, result = _generation("fzg_c")
    contour = ct.tooth_contour(result, "wheel", points=40)
    polygon = ct.gear_polygon(contour, arc_points=4)
    z = contour.number_of_teeth
    per_tooth = len(contour.points) + 4
    assert polygon.shape == (z * per_tooth, 2)
    # every tooth is the first one rotated by 2 pi / z (the polygon is counter-clockwise, the
    # last piece of the array is the tooth on +Y, the one before it lies towards +X)
    pitch = 2.0 * math.pi / z
    blocks = polygon[::-1]
    for k in range(1, z):
        phi = k * pitch
        c, s = math.cos(phi), math.sin(phi)
        rotated = np.column_stack(
            (
                blocks[:per_tooth, 0] * c + blocks[:per_tooth, 1] * s,
                -blocks[:per_tooth, 0] * s + blocks[:per_tooth, 1] * c,
            )
        )
        assert np.allclose(blocks[k * per_tooth : (k + 1) * per_tooth], rotated, atol=1e-12)
    # counter-clockwise (positive area) between the root and the tip circle
    x, y = polygon[:, 0], polygon[:, 1]
    area = 0.5 * np.sum(x * np.roll(y, -1) - np.roll(x, -1) * y)
    r_f, r_a = 0.5 * contour.generated_root_diameter_mm, 0.5 * contour.tip_diameter_mm
    assert math.pi * r_f**2 < area < math.pi * r_a**2
    # no self-intersection: the polar angle runs monotonically once around the gear
    angles = np.unwrap(np.arctan2(y, x))
    assert np.all(np.diff(angles) >= -1e-12)
    assert 2.0 * math.pi * (1.0 - 1.0 / z) < angles[-1] - angles[0] < 2.0 * math.pi
    radius = np.hypot(x, y)
    assert np.min(radius) == pytest.approx(r_f, abs=1e-9) and np.max(radius) == pytest.approx(
        r_a, abs=1e-9
    )
    with pytest.raises(InputRangeError):
        ct.gear_polygon(contour, arc_points=1)


def test_compare_measures_normal_distances_per_region() -> None:
    pair, result = _generation("kst_c_rerun")  # the wheel has a chamfer generated by the tool
    contour = ct.tooth_contour(result, "wheel")
    points = contour.as_array()
    exact = ct.compare(contour, points[::7])
    assert exact.max_um < 1e-9 and exact.rms_um < 1e-9
    # a radial shift of 3 um of the tip flank points shows up in the tip region only
    shifted = points.copy()
    radius = np.hypot(points[:, 0], points[:, 1])
    tip = radius > 0.5 * contour.tip_form_diameter_mm * (1.0 + 1e-6)
    assert np.any(tip)
    shifted[tip] *= 1.0 + 3e-3 / radius[tip][:, None]
    diff = ct.compare(contour, shifted)
    assert 2.0 <= diff.tip_max_um <= 3.0 + 1e-9 and diff.region_of_max == "tip"
    assert diff.involute_max_um < 1e-9 and diff.fillet_max_um < 1e-9
    assert diff.fillet_points + diff.involute_points + diff.tip_points == diff.reference_points
    # the tip region of a gear without chamfer is empty (the tip circle is the tip form circle)
    plain = ct.tooth_contour(result, "pinion")
    assert ct.compare(plain, plain.as_array()).tip_points == 0
    with pytest.raises(InputRangeError):
        ct.compare(contour, np.zeros((3, 3)))
    with pytest.raises(InputRangeError):
        ct.compare(contour, np.array([[float("nan"), 1.0]]))


def test_involute_flank_samples_the_involute() -> None:
    d_b, psi_b = 37.588, 0.12
    radius, psi = ct.involute_flank(d_b, psi_b, 38.0, 44.0, 25)
    assert (
        len(radius) == 25 and radius[0] == pytest.approx(19.0) and radius[-1] == pytest.approx(22.0)
    )
    for r, p in zip(radius, psi, strict=True):
        alpha = iv.transverse_profile_angle_at(2.0 * r, d_b)
        assert p == pytest.approx(psi_b - iv.inv(alpha), abs=1e-14)
    with pytest.raises(InputRangeError):
        ct.involute_flank(d_b, psi_b, 44.0, 38.0, 25)
    with pytest.raises(InputRangeError):
        ct.involute_flank(d_b, psi_b, 30.0, 38.0, 25)
    with pytest.raises(InputRangeError):
        ct.involute_flank(d_b, psi_b, 38.0, 44.0, 1)


def test_chamfer_flank() -> None:
    radius, psi = ct.chamfer_flank(22.2, 0.03, 22.4, 0.9, 5)
    assert radius[0] == pytest.approx(22.2) and radius[-1] == pytest.approx(22.4)
    assert psi[0] == pytest.approx(0.03) and psi[-1] == pytest.approx(0.5 * 0.9 / 22.4)
    with pytest.raises(GeometryInfeasibleError):
        ct.chamfer_flank(22.2, 0.03, 22.4, 2.0, 5)


def test_a_given_chamfer_without_its_shape_has_no_contour() -> None:
    pair, result = _generation("chamfer_hk_z20_34")
    with pytest.raises(InputRangeError, match="residual tip thickness"):
        ct.tooth_contour(result, "pinion")
    with pytest.raises(InputRangeError):
        ct.tooth_contour(result, "left")  # type: ignore[arg-type]
    with pytest.raises(InputRangeError):
        ct.tooth_contour(result, "wheel", points=4)


def test_stplus_contour_loader() -> None:
    points = ct.stplus_contour("fzg_c", 1)
    assert points.shape == (254, 2)
    with pytest.raises(InputRangeError):
        ct.stplus_contour("fzg_c", 3)
    with pytest.raises(InputRangeError):
        ct.stplus_contour("kst_b", 1)  # supplied listing without contour export
