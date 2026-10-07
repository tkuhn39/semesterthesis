"""Position of a spur gear pair for the finite element model (``gearcore.fe.placement``)."""

import math

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from matplotlib.path import Path as PolygonPath

from gearcore import contour as ct
from gearcore import data
from gearcore import involute as iv
from gearcore.errors import InputRangeError, NotSupportedError
from gearcore.fe import placement as pl
from gearcore.generation import compute_generation
from gearcore.io.ste import load_ste, pair_input_from_ste
from gearcore.models.results import GenerationResult

FLANKS = ("left", "right")


def _generation(case: str) -> GenerationResult:
    return compute_generation(pair_input_from_ste(load_ste(data.stplus_input_path(case))).pair)


@pytest.fixture(scope="module")
def kst_e() -> GenerationResult:
    return _generation("kst_e")


def _positions(generation: GenerationResult, count: int) -> list[float]:
    """Radii of curvature from half a base pitch before A to half a base pitch after E."""
    rho_a, rho_e = pl.path_of_contact_limits(generation)
    margin = 0.5 * generation.pair_geometry.transverse_base_pitch_mm
    return [float(rho) for rho in np.linspace(rho_a - margin, rho_e + margin, count)]


def _flank_point(
    generation: GenerationResult, role: str, rho: float, centre_angle_deg: float, flank: str
) -> tuple[float, float]:
    """The flank point with the radius of curvature ``rho`` from the tooth thickness of the
    generated gear (Eq. (40), (42)), about the axis of the gear."""
    pair = generation.inputs
    gear = generation.gears.pinion if role == "pinion" else generation.gears.wheel
    alpha_n = math.radians(pair.normal_pressure_angle_deg)
    r_b = 0.5 * iv.base_diameter(gear.number_of_teeth, pair.normal_module_mm, alpha_n, 0.0)
    psi_b = iv.base_tooth_thickness_half_angle(
        iv.tooth_thickness_half_angle(
            gear.number_of_teeth, gear.generating_profile_shift_coefficient, alpha_n
        ),
        alpha_n,
    )
    psi_y = psi_b - iv.inv(math.atan2(rho, r_b))
    side = 1.0 if flank == "left" else -1.0
    angle = math.radians(centre_angle_deg) + side * psi_y
    radius = math.hypot(r_b, rho)
    return radius * math.cos(angle), radius * math.sin(angle)


def test_limits_of_the_path_of_contact_match_the_pair_geometry(kst_e: GenerationResult) -> None:
    rho_a, rho_e = pl.path_of_contact_limits(kst_e)
    assert rho_e - rho_a == pytest.approx(
        kst_e.pair_geometry.length_of_path_of_contact_mm, abs=1e-12
    )
    assert rho_e - kst_e.pair_geometry.length_of_addendum_path_of_contact_mm.pinion == (
        pytest.approx(
            rho_a + kst_e.pair_geometry.length_of_addendum_path_of_contact_mm.wheel, abs=1e-12
        )
    )


@pytest.mark.parametrize("flank", FLANKS)
def test_working_flanks_touch_in_every_position(kst_e: GenerationResult, flank: str) -> None:
    for rho in _positions(kst_e, 41):
        position = pl.mesh_position(kst_e, rho, working_flank=flank)  # type: ignore[arg-type]
        assert abs(pl.flank_distance(kst_e, position, flank)) < 1e-12  # type: ignore[arg-type]
        # the contact point lies on both flanks, each built from its own tooth thickness
        x1, y1 = _flank_point(kst_e, "pinion", rho, position.tooth_centre_angle_deg.pinion, flank)
        x2, y2 = _flank_point(
            kst_e,
            "wheel",
            position.radius_of_curvature_mm.wheel,
            position.tooth_centre_angle_deg.wheel,
            flank,
        )
        x2 += position.centre_distance_mm
        assert math.hypot(x1 - x2, y1 - y2) < 1e-11
        assert math.hypot(x1 - position.contact_point_mm[0], y1 - position.contact_point_mm[1]) < (
            1e-11
        )


@pytest.mark.parametrize("flank", FLANKS)
def test_every_pair_on_the_path_touches(kst_e: GenerationResult, flank: str) -> None:
    for rho in _positions(kst_e, 15):
        position = pl.mesh_position(kst_e, rho, working_flank=flank)  # type: ignore[arg-type]
        assert 1 <= len(position.tooth_pairs_on_path) <= 2
        for k in position.tooth_pairs_on_path:
            distance = pl.flank_distance(
                kst_e,
                position,
                flank,  # type: ignore[arg-type]
                pinion_tooth=k,
                wheel_tooth=-k,
            )
            assert abs(distance) < 1e-12


def test_followed_pair_is_on_the_path_between_a_and_e(kst_e: GenerationResult) -> None:
    rho_a, rho_e = pl.path_of_contact_limits(kst_e)
    assert 0 in pl.mesh_position(kst_e, rho_a, working_flank="left").tooth_pairs_on_path
    assert 0 in pl.mesh_position(kst_e, rho_e, working_flank="left").tooth_pairs_on_path
    assert 0 not in pl.mesh_position(kst_e, rho_a - 1e-6, working_flank="left").tooth_pairs_on_path
    assert 0 not in pl.mesh_position(kst_e, rho_e + 1e-6, working_flank="left").tooth_pairs_on_path


def test_back_flank_distance_is_the_backlash_stplus_prints(kst_e: GenerationResult) -> None:
    # listing: 'Verdrehfl.spiel(Waelzkr.)/Normalfl.spiel  j_t / j_n', upper tooth thickness limit
    printed = data.load_stplus("kst_e")["fuer Nennachsabstand u. obere Zahnabm."]
    j_t, j_n = printed["numbers"]
    tolerance = data.printed_tolerance(3)
    distance = pl.back_flank_distance(kst_e)
    alpha_wt = math.radians(kst_e.pair_geometry.transverse_working_pressure_angle_deg)
    assert distance == pytest.approx(j_n, abs=tolerance)
    assert distance / math.cos(alpha_wt) == pytest.approx(j_t, abs=tolerance)


@pytest.mark.parametrize("flank", FLANKS)
def test_back_flanks_are_open_by_the_backlash(kst_e: GenerationResult, flank: str) -> None:
    other = "right" if flank == "left" else "left"
    step = 1 if flank == "left" else -1
    expected = pl.back_flank_distance(kst_e)
    for rho in _positions(kst_e, 9):
        position = pl.mesh_position(kst_e, rho, working_flank=flank)  # type: ignore[arg-type]
        for pinion_tooth, wheel_tooth in ((step, 0), (0, step), (2 * step, -step)):
            distance = pl.flank_distance(
                kst_e,
                position,
                other,  # type: ignore[arg-type]
                pinion_tooth=pinion_tooth,
                wheel_tooth=wheel_tooth,
            )
            assert distance == pytest.approx(expected, abs=1e-12)


@pytest.mark.parametrize("flank", FLANKS)
def test_sampled_contours_touch_and_do_not_overlap(kst_e: GenerationResult, flank: str) -> None:
    pinion = ct.tooth_contour(kst_e, "pinion", points=120)
    wheel = ct.tooth_contour(kst_e, "wheel", points=120)
    z_1, z_2 = pinion.number_of_teeth, wheel.number_of_teeth
    wheel_gear = ct.gear_polygon(wheel)
    backlash = pl.back_flank_distance(kst_e)
    other = "right" if flank == "left" else "left"
    for rho in _positions(kst_e, 9):
        position = pl.mesh_position(kst_e, rho, working_flank=flank)  # type: ignore[arg-type]
        place = pl.fixed_axes(position)
        angle_1, angle_2 = place.tooth_centre_angle_deg.pinion, place.tooth_centre_angle_deg.wheel
        # working flanks of a pair on the path: closer than the sampling allows to resolve
        k = position.tooth_pairs_on_path[0]
        a = pl.placed(
            pinion.segment(f"{flank}_involute"), place.axis_mm.pinion, angle_1 + k * 360.0 / z_1
        )
        b = pl.placed(
            wheel.segment(f"{flank}_involute"), place.axis_mm.wheel, angle_2 - k * 360.0 / z_2
        )
        assert float(np.min(ct._distance_to_polyline(a, b))) < 2e-5
        # back flanks: nowhere closer than the backlash
        step = 1 if flank == "left" else -1
        a = pl.placed(
            pinion.segment(f"{other}_involute"), place.axis_mm.pinion, angle_1 + step * 360.0 / z_1
        )
        b = pl.placed(wheel.segment(f"{other}_involute"), place.axis_mm.wheel, angle_2)
        assert float(np.min(ct._distance_to_polyline(a, b))) > backlash - 2e-5
        # no point of the pinion teeth in the mesh lies inside the wheel
        polygon = pl.placed(wheel_gear, place.axis_mm.wheel, angle_2)
        teeth = np.concatenate(
            [
                pl.placed(pinion.as_array(), place.axis_mm.pinion, angle_1 + j * 360.0 / z_1)
                for j in range(-3, 4)
            ]
        )
        inside = PolygonPath(polygon).contains_points(teeth)
        if inside.any():
            closed = np.concatenate((polygon, polygon[:1]))
            near = closed[np.hypot(closed[:, 0], closed[:, 1]) < 0.5 * pinion.tip_diameter_mm + 1.0]
            depth = ct._distance_to_polyline(teeth[inside], near)
            assert float(np.max(depth)) < 2e-5


def test_the_gears_roll_with_the_gear_ratio(kst_e: GenerationResult) -> None:
    z_1 = kst_e.gears.pinion.number_of_teeth
    z_2 = kst_e.gears.wheel.number_of_teeth
    rho_a, rho_e = pl.path_of_contact_limits(kst_e)
    first = pl.mesh_position(kst_e, rho_a, working_flank="left")
    second = pl.mesh_position(kst_e, rho_e, working_flank="left")
    turn_1 = second.tooth_centre_angle_deg.pinion - first.tooth_centre_angle_deg.pinion
    turn_2 = second.tooth_centre_angle_deg.wheel - first.tooth_centre_angle_deg.wheel
    assert turn_1 > 0.0  # left flanks working: the pinion drives counter-clockwise
    assert turn_2 == pytest.approx(-turn_1 * z_1 / z_2, abs=1e-12)


def test_a_pinion_driving_clockwise_works_with_the_right_flanks(kst_e: GenerationResult) -> None:
    flank = pl.working_flank_of_the_driving_pinion("clockwise")
    assert flank == "right"
    assert pl.working_flank_of_the_driving_pinion("counterclockwise") == "left"
    assert pl.pinion_torque_sign("right") == -1.0
    assert pl.pinion_torque_sign("left") == 1.0
    rho_a, rho_e = pl.path_of_contact_limits(kst_e)
    first = pl.mesh_position(kst_e, rho_a, working_flank=flank)
    second = pl.mesh_position(kst_e, rho_e, working_flank=flank)
    # from A to E the pinion turns clockwise (angle falls), the wheel counter-clockwise
    assert second.tooth_centre_angle_deg.pinion < first.tooth_centre_angle_deg.pinion
    assert second.tooth_centre_angle_deg.wheel > first.tooth_centre_angle_deg.wheel
    # the flank force on the pinion, along the line of action away from the wheel flank, turns
    # it counter-clockwise; the driving torque that balances it is clockwise (negative about +z)
    alpha_wt = math.radians(kst_e.pair_geometry.transverse_working_pressure_angle_deg)
    x, y = second.contact_point_mm
    force_on_pinion = (-math.sin(alpha_wt), math.cos(alpha_wt))
    moment_of_the_flank_force = x * force_on_pinion[1] - y * force_on_pinion[0]
    assert moment_of_the_flank_force > 0.0
    assert pl.pinion_torque_sign(flank) * moment_of_the_flank_force < 0.0
    with pytest.raises(InputRangeError):
        pl.working_flank_of_the_driving_pinion("forwards")  # type: ignore[arg-type]
    with pytest.raises(InputRangeError):
        pl.pinion_torque_sign("top")  # type: ignore[arg-type]


def test_right_flanks_are_the_mirror_image(kst_e: GenerationResult) -> None:
    for rho in _positions(kst_e, 7):
        left = pl.mesh_position(kst_e, rho, working_flank="left")
        right = pl.mesh_position(kst_e, rho, working_flank="right")
        assert right.contact_point_mm == (left.contact_point_mm[0], -left.contact_point_mm[1])
        assert right.tooth_centre_angle_deg.pinion == -left.tooth_centre_angle_deg.pinion
        assert right.tooth_centre_angle_deg.wheel == pytest.approx(
            360.0 - left.tooth_centre_angle_deg.wheel, abs=1e-12
        )
        assert right.tooth_pairs_on_path == tuple(sorted(-k for k in left.tooth_pairs_on_path))


def test_wheel_at_rest_is_the_same_relative_position(kst_e: GenerationResult) -> None:
    tooth = ct.tooth_contour(kst_e, "pinion", points=16).as_array()

    def seen_from_the_wheel(place: pl.Placement) -> np.ndarray:
        points = pl.placed(tooth, place.axis_mm.pinion, place.tooth_centre_angle_deg.pinion)
        shifted = points - np.asarray(place.axis_mm.wheel)
        turn = -math.radians(place.tooth_centre_angle_deg.wheel)
        c, s = math.cos(turn), math.sin(turn)
        return np.column_stack(
            (c * shifted[:, 0] - s * shifted[:, 1], s * shifted[:, 0] + c * shifted[:, 1])
        )

    for rho in _positions(kst_e, 7):
        position = pl.mesh_position(kst_e, rho, working_flank="right")
        at_rest = pl.wheel_fixed(position)
        assert at_rest.tooth_centre_angle_deg.wheel == pytest.approx(90.0, abs=1e-12)
        assert at_rest.axis_mm.wheel == (position.centre_distance_mm, 0.0)
        axis = at_rest.axis_mm.pinion
        assert math.hypot(axis[0] - position.centre_distance_mm, axis[1]) == pytest.approx(
            position.centre_distance_mm, abs=1e-12
        )
        np.testing.assert_allclose(
            seen_from_the_wheel(at_rest), seen_from_the_wheel(pl.fixed_axes(position)), atol=1e-11
        )


def test_placed_puts_the_tooth_centre_on_its_angle() -> None:
    points = np.array([[0.0, 10.0], [1.0, 10.0]])
    np.testing.assert_allclose(
        pl.placed(points, (5.0, -2.0), 0.0), [[15.0, -2.0], [15.0, -3.0]], atol=1e-14
    )
    np.testing.assert_allclose(pl.placed(points, (0.0, 0.0), 90.0), points, atol=1e-14)


def test_inputs_outside_the_scope_raise(kst_e: GenerationResult) -> None:
    with pytest.raises(NotSupportedError):
        pl.mesh_position(_generation("helix20_z25_65"), 5.0, working_flank="left")
    limit = kst_e.pair_geometry.centre_distance_mm * math.sin(
        math.radians(kst_e.pair_geometry.transverse_working_pressure_angle_deg)
    )
    for rho in (-1e-9, limit + 1e-6, math.nan, math.inf):
        with pytest.raises(InputRangeError):
            pl.mesh_position(kst_e, rho, working_flank="left")
    with pytest.raises(InputRangeError):
        pl.mesh_position(kst_e, 9.0, working_flank="top")  # type: ignore[arg-type]
    with pytest.raises(InputRangeError):
        pl.mesh_position("kst_e", 9.0, working_flank="left")  # type: ignore[arg-type]
    position = pl.mesh_position(kst_e, 9.0, working_flank="right")
    with pytest.raises(InputRangeError):
        pl.flank_distance(kst_e, position, "top")  # type: ignore[arg-type]
    with pytest.raises(InputRangeError):
        pl.fixed_axes("position")  # type: ignore[arg-type]
    with pytest.raises(InputRangeError):
        pl.wheel_fixed(position, wheel_tooth_centre_angle_deg=math.nan)
    with pytest.raises(InputRangeError):
        pl.placed(np.zeros((3, 3)), (0.0, 0.0), 0.0)


def test_position_round_trips_through_json(kst_e: GenerationResult) -> None:
    position = pl.mesh_position(kst_e, 9.0, working_flank="right")
    assert pl.MeshPosition.model_validate_json(position.model_dump_json()) == position
    place = pl.wheel_fixed(position)
    assert pl.Placement.model_validate_json(place.model_dump_json()) == place


@settings(max_examples=200, deadline=None)
@given(
    fraction=st.floats(min_value=0.0, max_value=1.0),
    flank=st.sampled_from(FLANKS),
    case=st.sampled_from(("kst_e", "fzg_c", "plastic_m05_z20", "small_z8_x05")),
)
def test_contact_holds_for_any_position_between_the_tangent_points(
    fraction: float, flank: str, case: str
) -> None:
    generation = _GENERATIONS[case]
    geometry = generation.pair_geometry
    limit = geometry.centre_distance_mm * math.sin(
        math.radians(geometry.transverse_working_pressure_angle_deg)
    )
    rho = min(fraction * limit, limit)
    position = pl.mesh_position(generation, rho, working_flank=flank)  # type: ignore[arg-type]
    scale = geometry.centre_distance_mm
    assert abs(pl.flank_distance(generation, position, flank)) < 1e-13 * scale  # type: ignore[arg-type]
    assert position.radius_of_curvature_mm.pinion + position.radius_of_curvature_mm.wheel == (
        pytest.approx(limit, abs=1e-13 * scale)
    )
    x1, y1 = _flank_point(generation, "pinion", rho, position.tooth_centre_angle_deg.pinion, flank)
    assert math.hypot(x1 - position.contact_point_mm[0], y1 - position.contact_point_mm[1]) < (
        1e-12 * scale
    )


_GENERATIONS = {
    case: _generation(case) for case in ("kst_e", "fzg_c", "plastic_m05_z20", "small_z8_x05")
}


def test_single_pair_contact_points_lie_one_base_pitch_inside_the_path() -> None:
    generation = _generation("kst_e")
    rho_a, rho_e = pl.path_of_contact_limits(generation)
    rho_b, rho_d = pl.single_contact_points(generation)
    p_bt = generation.pair_geometry.transverse_base_pitch_mm
    assert rho_b == pytest.approx(rho_e - p_bt) and rho_d == pytest.approx(rho_a + p_bt)
    assert rho_a < rho_b < rho_d < rho_e  # eps_alpha = 1,154: B lies before D
    # B is the outer point of single pair tooth contact of the wheel: the pair before it on the
    # path has just left at E, the pair after it has not yet entered at A
    position = pl.mesh_position(generation, rho_b, working_flank="right")
    assert position.tooth_pairs_on_path == (-1, 0) or 0 in position.tooth_pairs_on_path
