"""Root fillet variants (``gearcore.fillet``): the constructions of the sources on the kst-E
wheel, their continuity, the contour assembly, the clearance to the pinion tip and the mesh."""

from __future__ import annotations

import math

import numpy as np
import pytest

from gearcore import contour as ct
from gearcore import fillet as fl
from gearcore.errors import GeometryInfeasibleError, InputRangeError
from gearcore.fe import sector_mesh as sm
from gearcore.models.results import GenerationResult
from gearcore.parity import compute_generation_from_data, generation_data


@pytest.fixture(scope="module")
def kst_e() -> GenerationResult:
    data = generation_data("kst_e")
    result = compute_generation_from_data(data, data.values)
    assert isinstance(result, GenerationResult)
    return result


VARIANTS = [
    fl.FilletVariant(kind="ellipse"),
    fl.FilletVariant(kind="bezier"),
    fl.FilletVariant(kind="bionic"),
]


def _angle_between(u: np.ndarray, v: np.ndarray) -> float:
    cosine = float(np.dot(u, v) / (np.linalg.norm(u) * np.linalg.norm(v)))
    return math.degrees(math.acos(max(-1.0, min(1.0, cosine))))


# ---------------------------------------------------------------------------- equations


def test_ellipse_slopes_follow_fruehe() -> None:
    gamma, alpha, s_half, z = math.radians(30.0), math.radians(11.0), math.radians(2.3), 52
    assert fl.ellipse_slope_at_root_form(gamma, alpha, s_half) == pytest.approx(
        -math.tan(gamma - alpha + s_half)
    )
    assert fl.ellipse_slope_at_root(gamma, z) == pytest.approx(
        math.tan(0.5 * math.pi - math.pi / z - gamma)
    )
    assert fl.ellipse_slope_at_root(gamma, z) > 0.0
    with pytest.raises(GeometryInfeasibleError):
        fl.ellipse_slope_at_root(math.radians(89.0), z)
    with pytest.raises(InputRangeError):
        fl.ellipse_x_of_slope(0.0, 1.0, 3.0)


def test_ellipse_point_of_slope_lies_on_the_ellipse_with_that_slope() -> None:
    a, ratio, m = 0.45, 3.0, -0.35
    x, y = fl.ellipse_x_of_slope(m, a, ratio), fl.ellipse_y_of_slope(m, a, ratio)
    b = a / ratio
    assert x**2 / a**2 + y**2 / b**2 == pytest.approx(1.0)
    slope = -(b**2 / a**2) * x / y  # dy/dx of the upper half
    assert slope == pytest.approx(m)
    assert x > 0.0  # a negative slope sits on the right of the apex


def test_bezier_control_distance_is_the_patent_formula() -> None:
    assert fl.bezier_control_distance(2.0, 0.0) == pytest.approx(0.5)
    assert fl.bezier_control_distance(2.0, 3.0) == pytest.approx(1.1)
    with pytest.raises(InputRangeError):
        fl.bezier_control_distance(2.0, 3.5)


def test_bezier_points_interpolate_the_end_points() -> None:
    p = [np.array(v, dtype=float) for v in ((0.0, 0.0), (1.0, 2.0), (3.0, 2.0), (4.0, 0.0))]
    curve = fl.bezier_points(p[0], p[1], p[2], p[3], np.array([0.0, 0.5, 1.0]))
    assert curve[0] == pytest.approx(p[0])
    assert curve[-1] == pytest.approx(p[3])
    assert curve[1] == pytest.approx([2.0, 1.5])


def test_bionic_tangent_function_meets_its_three_conditions() -> None:
    x_P, y_P, m_P, phi = 0.6, 25.6, 2.5, math.radians(24.0)
    a, b, c = fl.bionic_tangent_function(x_P, y_P, m_P, phi)
    assert a * b == pytest.approx(math.tan(phi))  # slope on the centre line
    assert a * b / math.cos(b * x_P) ** 2 == pytest.approx(m_P)  # slope at P
    assert a * math.tan(b * x_P) + c == pytest.approx(y_P)  # through P
    with pytest.raises(GeometryInfeasibleError):
        fl.bionic_tangent_function(x_P, y_P, 0.3, phi)


def test_bionic_circle_touches_the_tangent_function() -> None:
    a, b, c, r = 0.2437, 1.838, 25.02, 0.38
    x_ue, y_centre = fl.bionic_circle(a, b, c, r, 0.6)
    y_ue = a * math.tan(b * x_ue) + c
    assert math.hypot(x_ue, y_ue - y_centre) == pytest.approx(r)
    slope = a * b / math.cos(b * x_ue) ** 2
    normal = np.array([-slope, 1.0]) / math.hypot(slope, 1.0)
    centre = np.array([x_ue, y_ue]) + r * normal
    assert centre == pytest.approx([0.0, y_centre])


def test_bionic_root_angle_of_claim_5() -> None:
    assert fl.bionic_root_angle(52, math.radians(17.0)) == pytest.approx(
        math.radians(45.0 - 180.0 / 52 - 17.0)
    )
    with pytest.raises(GeometryInfeasibleError):
        fl.bionic_root_angle(4, math.radians(10.0))


# ---------------------------------------------------------------------------- contours


@pytest.mark.parametrize("variant", VARIANTS, ids=[v.kind for v in VARIANTS])
def test_variant_contour_is_continuous_symmetric_and_clear_of_the_pinion(
    kst_e: GenerationResult, variant: fl.FilletVariant
) -> None:
    base = ct.tooth_contour(kst_e, "wheel", points=400)
    result = fl.apply(kst_e, "wheel", variant, points=400)
    contour = result.contour
    z = contour.number_of_teeth
    assert [s.name for s in contour.segments] == list(ct.SEGMENTS)
    left, right = contour.segment("left_fillet"), contour.segment("right_fillet")
    # the joined contour keeps a junction point once: the right fillet lacks its first point
    mirrored = right[::-1] * np.array([-1.0, 1.0])
    assert mirrored == pytest.approx(left[: len(mirrored)])
    # the fillet starts on the centre line of the gap, at a right angle to it
    first = left[0]
    assert math.atan2(first[0], first[1]) == pytest.approx(-math.pi / z, abs=1.0e-9)
    assert _angle_between(left[1] - left[0], first) == pytest.approx(90.0, abs=1.0)
    # tangent-continuous into the involute
    involute = contour.segment("left_involute")
    # the joined contour keeps the transition point in the fillet; the involute continues it
    assert float(np.hypot(*(involute[0] - left[-1]))) < 0.02
    assert float(np.hypot(*involute[0])) > float(np.hypot(*left[-1]))
    assert _angle_between(left[-1] - left[-2], involute[0] - left[-1]) < 0.3
    assert 0.5 * contour.root_form_diameter_mm == pytest.approx(float(np.hypot(*left[-1])))
    # the involute, the tip flank and the tip are the generated ones above the transition
    assert contour.tip_diameter_mm == base.tip_diameter_mm
    assert contour.segment("tip") == pytest.approx(base.segment("tip"))
    assert result.root_diameter_mm == pytest.approx(2.0 * float(np.hypot(*first)))
    assert result.root_diameter_mm < result.transition_diameter_mm
    assert result.min_curvature_radius_mm > 0.0
    clearance, at_radius = fl.mating_tip_clearance(kst_e, contour, samples=120)
    assert clearance > 0.1
    assert (
        0.5 * result.root_diameter_mm <= at_radius <= 0.5 * result.transition_diameter_mm + 1.0e-6
    )


def test_transition_diameters_follow_the_sources(kst_e: GenerationResult) -> None:
    gear = kst_e.gears.wheel
    d_N = kst_e.pair_geometry.sap_diameter_mm.wheel
    d_FR = fl.clearance_circle_diameter(kst_e, "wheel")
    assert d_FR == pytest.approx(
        2.0 * kst_e.pair_geometry.centre_distance_mm - kst_e.pair_geometry.tip_diameter_mm.pinion
    )
    assert fl.transition_diameter(kst_e, "wheel", VARIANTS[0]) == pytest.approx(
        gear.root_form_diameter_mm
    )
    assert fl.transition_diameter(kst_e, "wheel", VARIANTS[1]) == pytest.approx(0.5 * (d_N + d_FR))
    given = fl.FilletVariant(
        kind="bezier", transition_diameter_mm=0.5 * (d_N + gear.root_form_diameter_mm)
    )
    assert fl.transition_diameter(kst_e, "wheel", given) == pytest.approx(
        given.transition_diameter_mm
    )
    with pytest.raises(GeometryInfeasibleError):
        fl.transition_diameter(
            kst_e, "wheel", fl.FilletVariant(kind="bezier", transition_diameter_mm=d_N + 0.5)
        )


def test_standard_contour_clears_the_pinion_more_than_the_filled_variants(
    kst_e: GenerationResult,
) -> None:
    base = ct.tooth_contour(kst_e, "wheel")
    reference, _ = fl.mating_tip_clearance(kst_e, base, samples=120)
    assert reference > 0.4
    bezier = fl.apply(kst_e, "wheel", VARIANTS[1]).contour
    filled, _ = fl.mating_tip_clearance(kst_e, bezier, samples=120)
    assert 0.0 < filled < reference


def test_apply_refuses_wrong_input(kst_e: GenerationResult) -> None:
    with pytest.raises(InputRangeError):
        fl.apply(kst_e, "wheel", "ellipse")  # type: ignore[arg-type]
    with pytest.raises(InputRangeError):
        fl.apply(kst_e, "wheel", VARIANTS[0], points=4)
    with pytest.raises(InputRangeError):
        fl.mating_tip_clearance(kst_e, ct.tooth_contour(kst_e, "wheel"), samples=5)


def test_labels_name_kind_and_parameters() -> None:
    assert VARIANTS[0].label() == "ellipse_g30_ab3"
    assert VARIANTS[1].label() == "bezier_f1"
    assert VARIANTS[2].label() == "bionic_phiauto_r0.3"
    assert fl.FilletVariant(kind="bionic", root_angle_deg=20.0).label() == "bionic_phi20_r0.3"


def test_ellipse_arc_refuses_limits_outside_the_ellipse() -> None:
    with pytest.raises(GeometryInfeasibleError):
        fl.ellipse_arc(1.0, 3.0, -1.5, 0.5, 8)
    arc = fl.ellipse_arc(1.0, 3.0, -1.0, 1.0, 5)
    assert arc[0] == pytest.approx([-1.0, 0.0])
    assert arc[-1] == pytest.approx([1.0, 0.0])


def test_clearance_is_the_euclidean_distance_to_the_fillet(kst_e: GenerationResult) -> None:
    contour = fl.apply(kst_e, "wheel", VARIANTS[1]).contour
    distance, at_radius = fl.mating_tip_clearance(kst_e, contour, samples=120)
    # the Bézier contour starts 0,05 mm below the start of the active profile: the corner
    # passes the transition closer than the radial gap at the gap centre suggests
    assert 0.1 < distance < 0.3
    assert at_radius > 0.5 * contour.generated_root_diameter_mm


def test_polyline_min_curvature_radius_of_a_circle() -> None:
    theta = np.linspace(0.0, math.pi, 200)
    circle = np.column_stack((2.0 * np.cos(theta), 2.0 * np.sin(theta)))
    assert fl.polyline_min_curvature_radius(circle) == pytest.approx(2.0, rel=1.0e-3)
    assert math.isinf(
        fl.polyline_min_curvature_radius(np.array([[0.0, 0.0], [1.0, 0.0], [2.0, 0.0]]))
    )


# ---------------------------------------------------------------------------- mesh


@pytest.mark.parametrize("variant", VARIANTS, ids=[v.kind for v in VARIANTS])
def test_sector_mesh_maps_the_template_onto_the_variant(
    kst_e: GenerationResult, variant: fl.FilletVariant
) -> None:
    mesh = sm.sector_mesh(kst_e, "wheel", teeth=1, rim_rings=3, fillet=variant)
    expected = fl.apply(kst_e, "wheel", variant, points=sm.CONTOUR_POINTS)
    assert mesh.root_radius_mm == pytest.approx(0.5 * expected.root_diameter_mm)
    quality = sm.scaled_jacobians(mesh.points_mm, mesh.quads)
    assert float(quality.min()) >= sm.MIN_CORNER_SINE


def test_sector_mesh_without_variant_is_unchanged(kst_e: GenerationResult) -> None:
    plain = sm.sector_mesh(kst_e, "wheel", teeth=1, rim_rings=3)
    assert plain.root_radius_mm == pytest.approx(0.5 * kst_e.gears.wheel.generated_root_diameter_mm)
