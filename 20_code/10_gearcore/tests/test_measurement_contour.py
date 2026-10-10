"""Contour scans: the nominal geometry of the scan, a synthetic three-tooth scan of the kst-E
wheel (axis offset, rotation, noise, the STplus chamfer at the tip) recovered to the micrometre,
the regression of the pinion scan 86481 Z01 against the evaluation of 2026-10-10, the tooth
frames and the signed deviation from the nominal outline."""

import math

import numpy as np
import pytest

from gearcore import contour as ct
from gearcore import data
from gearcore.data import measurement_fixture
from gearcore.errors import InputRangeError
from gearcore.generation import compute_generation
from gearcore.io.p40_contour import load_contour_scans
from gearcore.io.ste import load_ste, pair_input_from_ste
from gearcore.measurement import contour_scan as cs
from gearcore.models.results import GenerationResult


@pytest.fixture(scope="module")
def generation() -> GenerationResult:
    return compute_generation(pair_input_from_ste(load_ste(data.stplus_input_path("kst_e"))).pair)


def test_scan_geometry_of_both_gears(generation: GenerationResult) -> None:
    pinion = cs.scan_geometry(generation, "pinion")
    assert pinion.number_of_teeth == 51
    assert pinion.r_b == pytest.approx(23.9622, abs=5.0e-5)
    assert pinion.r_a == pytest.approx(26.447, abs=5.0e-4)
    assert pinion.r_ff == pytest.approx(24.5405, abs=5.0e-5)
    assert pinion.base_tooth_thickness_nominal_mm == pytest.approx(2.3295, abs=5.0e-5)
    assert pinion.base_tooth_thickness_generated_mm == pytest.approx(2.0515, abs=5.0e-5)
    wheel = cs.scan_geometry(generation, "wheel")
    assert wheel.number_of_teeth == 52 and wheel.r_a == pytest.approx(27.011, abs=5.0e-4)
    assert wheel.base_tooth_thickness_generated_mm == pytest.approx(2.2124, abs=5.0e-5)
    assert wheel.pitch_angle_rad == pytest.approx(2.0 * math.pi / 52)
    with pytest.raises(InputRangeError):
        cs.scan_geometry(generation, "gear")  # type: ignore[arg-type]
    assert cs.nominal_base_tooth_thickness(
        51, 1.0, math.radians(20.0), 0.0, 0.2034
    ) == pytest.approx(2.3295, abs=5.0e-5)


def _synthetic_scan(
    generation: GenerationResult, offset: tuple[float, float], rotation_deg: float, noise_um: float
) -> np.ndarray:
    """Three teeth of the nominal wheel around +y, the scan running from +x to −x, moved by
    ``offset``, rotated by ``rotation_deg`` and disturbed by ``noise_um``."""
    polygon = ct.gear_polygon(ct.tooth_contour(generation, "wheel", points=120), arc_points=12)
    phi = np.arctan2(polygon[:, 0], polygon[:, 1])
    pitch = 2.0 * math.pi / 52
    keep = np.abs(phi) < 1.5 * pitch
    points = polygon[keep]
    order = np.argsort(-phi[keep])
    points = points[order]
    angle = math.radians(rotation_deg)
    c, s = math.cos(angle), math.sin(angle)
    rotated = np.column_stack(
        (c * points[:, 0] - s * points[:, 1], s * points[:, 0] + c * points[:, 1])
    )
    rng = np.random.default_rng(7)
    return np.asarray(
        rotated + np.asarray(offset) + 1.0e-3 * noise_um * rng.standard_normal(rotated.shape)
    )


def test_synthetic_wheel_scan_is_recovered(generation: GenerationResult) -> None:
    geometry = cs.scan_geometry(generation, "wheel")
    scan = _synthetic_scan(generation, (0.15, -0.10), 0.3, 1.0)
    runs = cs.segment(scan)
    assert [r.kind for r in runs].count("tip") == 3 and [r.kind for r in runs].count("flank") >= 6
    _, fit = cs.fit_scan(scan, geometry)
    assert fit.centre_mm[0] == pytest.approx(0.15, abs=3.0e-3)
    assert fit.centre_mm[1] == pytest.approx(-0.10, abs=3.0e-3)
    assert len(fit.tip_radius_mm) == 3
    for radius in fit.tip_radius_mm:
        assert radius == pytest.approx(geometry.r_a, abs=3.0e-3)
    assert fit.rms_flank_um < 3.0
    teeth = cs.tooth_thicknesses(fit, geometry)
    assert len(teeth) == 3
    for tooth in teeth:
        assert tooth.s_b_mm == pytest.approx(geometry.base_tooth_thickness_generated_mm, abs=3.0e-3)
    middle = teeth[1]
    assert middle.theta_centre_rad == pytest.approx(
        -math.radians(0.3), abs=2.0e-4
    )  # θ from +y to +x
    pitches = cs.angular_pitches(fit)
    assert len(pitches) >= 2
    for pitch in pitches:
        assert pitch.pitch_deg == pytest.approx(360.0 / 52, abs=2.0e-3)
    # the 45° chamfer of the STplus tooth reads as a relief that starts h_K below the tip
    h_k = generation.gears.wheel.tip_chamfer_radial_mm
    reliefs = cs.flank_reliefs(scan, fit, geometry)
    assert reliefs and h_k > 0.05
    for relief in reliefs:
        assert relief.relief_start_r_mm == pytest.approx(geometry.r_a - h_k, abs=0.03)
        assert relief.rms_fit_um < 3.0
    # the STplus chamfer is not symmetric about the corner: both breaks fit it to a few µm
    corner = cs.measure_corner(scan, fit, 1, "right")
    assert corner is not None
    assert corner.chamfer_rms_um < 6.0 and corner.arc_rms_um < 6.0
    assert corner.sharp_rms_um > 1.8 * max(corner.chamfer_rms_um, corner.arc_rms_um)
    assert 0.08 < corner.chamfer_length_mm < 0.20 and 0.08 < corner.arc_radius_mm < 0.30
    assert corner.model("chamfer").cut_back > 0.0 and corner.model("arc", 0.0).cut_back == 0.0
    with pytest.raises(InputRangeError):
        cs.measure_corner(scan, fit, 9, "left")
    with pytest.raises(InputRangeError):
        cs.FitSettings(corner_size_step_mm=0.0).sizes()
    assert len(cs.FitSettings(corner_size_step_mm=0.1, corner_size_max_mm=0.3).sizes()) == 4


def test_pinion_86481_z01_reproduces_the_evaluation_of_2026_10_10(
    generation: GenerationResult,
) -> None:
    geometry = cs.scan_geometry(generation, "pinion")
    scan = load_contour_scans(measurement_fixture("contour_86481_Z01.scan.txt"))[0]
    assert scan.block == "B" and scan.z_mm == 87.572 and len(scan.points_mm) == 1088
    ev = cs.evaluate_scan(scan, geometry)
    assert not ev.coarse and ev.points == 1088
    assert ev.fit.centre_mm[0] == pytest.approx(0.0250, abs=5.0e-4)
    assert ev.fit.centre_mm[1] == pytest.approx(-0.0576, abs=5.0e-4)
    assert [round(v, 3) for v in ev.fit.tip_radius_mm] == [26.419, 26.419, 26.419]
    assert ev.fit.rms_flank_um == pytest.approx(0.5, abs=0.15)
    assert ev.fit.rms_tip_um == pytest.approx(3.7, abs=0.2)
    assert [(r.start, r.stop) for r in ev.fit.flank_runs] == [
        (47, 232),
        (292, 491),
        (560, 745),
        (805, 1004),
    ]
    assert ev.fit.flank_hand == (1, -1, 1, -1)
    assert len(ev.teeth) == 1 and ev.teeth[0].s_b_mm == pytest.approx(2.0320, abs=3.0e-4)
    assert [round(p.pitch_deg, 4) for p in ev.pitches] == [7.0664, 7.0657]
    first = ev.reliefs[0]
    assert first.rms_fit_um is not None and first.ramp_start_r_mm is not None
    assert first.relief_start_r_mm == pytest.approx(25.979, abs=5.0e-3)
    assert first.relief_at_tip_um == pytest.approx(18.4, abs=0.3)
    assert first.ramp_start_r_mm == pytest.approx(25.905, abs=5.0e-3)
    assert first.ramp_at_tip_um == pytest.approx(20.1, abs=0.3)
    assert first.ramp_at_nominal_tip_um == pytest.approx(21.1, abs=0.3)
    assert first.ramp_slope_um_per_mm == pytest.approx(15.7, abs=0.3)
    assert len(ev.corners) == 4  # the first tip land has no flank before it in the window
    for corner in ev.corners:
        assert corner.arc_radius_mm <= 0.02 and corner.chamfer_length_mm <= 0.01  # sharp edge
        assert corner.sharp_rms_um <= 1.5 and corner.cut_back_um <= 5.0
        assert 114.0 < corner.interior_angle_deg < 116.0
    assert {c.side for c in ev.corners} == {"left", "right"}


def test_tooth_frames_and_signed_deviation(generation: GenerationResult) -> None:
    geometry = cs.scan_geometry(generation, "pinion")
    scan = load_contour_scans(measurement_fixture("contour_86481_Z01.scan.txt"))[0]
    ev = cs.evaluate_scan(scan, geometry, corners=False)
    assert ev.corners == ()
    frames = cs.tooth_frames(scan, ev)
    assert len(frames) == 1
    frame = frames[0]
    points = frame.as_array()
    assert (
        frame.first_index < ev.fit.flank_runs[1].start
        and frame.last_index > ev.fit.flank_runs[2].stop
    )
    # the tooth centre lies on +y: the tooth is symmetric in x within the thickness deviation
    assert abs(points[:, 0].max() + points[:, 0].min()) < 0.02
    outline = cs.nominal_outline(generation, "pinion")
    assert outline[0, 0] > 0.0 and outline[-1, 0] < 0.0  # from the right gap to the left gap
    assert np.hypot(outline[:, 0], outline[:, 1]).max() == pytest.approx(geometry.r_a, abs=1.0e-6)
    deviation = cs.signed_deviation(points, outline)
    r = np.hypot(points[:, 0], points[:, 1])
    involute = (r > geometry.r_ff + 0.3) & (r < geometry.r_a - 0.7)
    # the pinion is thinner than the generated nominal tooth: material missing on both flanks
    assert deviation[involute].mean() == pytest.approx(-9.8, abs=1.0)
    assert deviation[involute].max() < 0.0
    magnified = cs.overlay_points(points, outline, 10.0)
    normals = cs.outward_normals(points)
    assert np.allclose(np.hypot(normals[:, 0], normals[:, 1]), 1.0)
    assert (normals[involute] @ np.array([0.0, 1.0])).mean() > 0.0  # outward is away from the axis
    moved = np.hypot(*(magnified - points).T)
    assert np.allclose(moved, 9.0 * np.abs(deviation) / 1000.0, atol=1.0e-9)
    inside = deviation[involute] / 1000.0
    assert np.allclose(
        cs.signed_deviation(magnified, outline)[involute] / 1000.0, 10.0 * inside, rtol=0.1
    )
    assert np.allclose(cs.overlay_points(points, outline, 1.0), points)
    with pytest.raises(InputRangeError):
        cs.overlay_points(points, outline, 0.5)
    with pytest.raises(InputRangeError):
        cs.tooth_points(scan, ev.fit, 0.0, 5, 2)


def _corner_points(shape: str, size: float, noise_um: float) -> tuple[np.ndarray, cs.CornerModel]:
    """Dense points of a broken corner with an interior angle of 115° and the sharp start model."""
    a = np.array([math.cos(math.radians(200.0)), math.sin(math.radians(200.0))])
    b = np.array([math.cos(math.radians(315.0)), math.sin(math.radians(315.0))])
    model = cs.CornerModel(corner=np.zeros(2), a=a, b=b, size=size, shape=shape)  # type: ignore[arg-type]
    t = model.tangent_length
    legs = np.linspace(t + 0.002, 0.40, 80)
    outline = model.outline(0.40, arc_points=120)
    points = np.vstack(
        (model.corner + legs[:, None] * a, outline[1:-1], model.corner + legs[:, None] * b)
    )
    rng = np.random.default_rng(3)
    points = points + 1.0e-3 * noise_um * rng.standard_normal(points.shape)
    start = cs.CornerModel(corner=np.array([0.004, -0.003]), a=a, b=b, size=0.0)
    return points, start


def test_arc_and_chamfer_are_told_apart() -> None:
    settings = cs.FitSettings(corner_size_step_mm=0.01, corner_size_max_mm=0.3)
    points, start = _corner_points("arc", 0.2, 0.5)
    arc, chamfer = cs.fit_corner_shapes(points, start, settings)
    assert arc.shape == "arc" and chamfer.shape == "chamfer"
    assert arc.rms_um < 1.0 and chamfer.rms_um > 3.0 * arc.rms_um
    assert arc.size_mm == pytest.approx(0.2, abs=0.01)
    assert arc.size_low_mm <= 0.2 <= arc.size_high_mm
    assert len(arc.rms_curve) == 31 and arc.rms_curve[0][0] == 0.0
    points, start = _corner_points("chamfer", 0.15, 0.5)
    arc, chamfer = cs.fit_corner_shapes(points, start, settings)
    assert chamfer.rms_um < 1.0 and arc.rms_um > 3.0 * chamfer.rms_um
    assert chamfer.size_mm == pytest.approx(0.15, abs=0.01)
    model = cs.CornerModel(corner=np.zeros(2), a=start.a, b=start.b, size=0.15, shape="chamfer")
    assert model.cut_back == pytest.approx(0.15 * math.cos(math.radians(57.5)))
    assert model.tangent_length == 0.15
    assert model.interior_angle == pytest.approx(math.radians(115.0))
    assert np.allclose(model.distance(model.outline(0.3)), 0.0, atol=1.0e-9)
    frame = cs.corner_frame(model.outline(0.3), model)
    assert frame[0, 1] < 0.0 and abs(frame[len(frame) // 2, 0]) < 0.16
