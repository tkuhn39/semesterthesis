"""The measured deviations of a flank on the tooth contour (``contour.ProfileModification``):
tip relief, profile slope, tip corner radius; their reach into the rigid surface and the sector
mesh (variants of the as-manufactured geometry, 2026-10-19)."""

import math

import numpy as np
import pytest
from pydantic import ValidationError

from gearcore import contour as ct
from gearcore import data
from gearcore.errors import GeometryInfeasibleError, InputRangeError, NotSupportedError
from gearcore.fe import rigid_surface as rsf
from gearcore.fe import sector_mesh as sm
from gearcore.fe.resample import MeshCounts
from gearcore.fillet import FilletVariant
from gearcore.generation import compute_generation
from gearcore.io.ste import load_ste, pair_input_from_ste
from gearcore.models.results import GenerationResult

RELIEF = ct.ProfileModification(tip_relief_um=23.6, tip_relief_start_diameter_mm=51.946)
D_M_WHEEL = 51.7279
WHEEL = ct.ProfileModification(
    profile_slope_um=10.25,
    profile_control_diameter_mm=50.3,
    profile_slope_pivot_diameter_mm=D_M_WHEEL,
    tip_edge_radius_mm=0.21,
)


@pytest.fixture(scope="module")
def kst_e() -> GenerationResult:
    return compute_generation(pair_input_from_ste(load_ste(data.stplus_input_path("kst_e"))).pair)


def _half_angles(points: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Radius and tooth thickness half angle of left-flank points (x < 0)."""
    return np.hypot(points[:, 0], points[:, 1]), np.arctan2(-points[:, 0], points[:, 1])


def _normal_deviation_um(base: np.ndarray, modified: np.ndarray, r_b: float) -> np.ndarray:
    """Deviation normal to the flank (plus material positive) of the modified left flank from
    the base one at the radii of the base points: the turn times r_b."""
    r_0, psi_0 = _half_angles(base)
    r_1, psi_1 = _half_angles(modified)
    deviation: np.ndarray = (np.interp(r_0, r_1, psi_1) - psi_0) * r_b * 1.0e3
    return deviation


def test_the_model_asks_for_what_a_modification_needs() -> None:
    with pytest.raises(ValidationError):
        ct.ProfileModification(tip_relief_um=10.0)
    with pytest.raises(ValidationError):
        ct.ProfileModification(profile_slope_um=5.0, profile_control_diameter_mm=50.0)
    with pytest.raises(ValidationError):
        ct.ProfileModification(tip_edge_radius_mm=-0.1)
    empty = ct.ProfileModification()
    assert empty.is_empty and not empty.turns_the_flank
    assert RELIEF.turns_the_flank and not RELIEF.is_empty
    assert ct.ProfileModification(tip_edge_radius_mm=0.2).is_empty is False
    assert ct.ProfileModification(tip_edge_radius_mm=0.2).turns_the_flank is False


def test_tip_relief_removes_material_linearly_to_the_tip(kst_e: GenerationResult) -> None:
    base = ct.tooth_contour(kst_e, "pinion")
    relieved = ct.tooth_contour(kst_e, "pinion", modification=RELIEF)
    r_b = 0.5 * 51.0 * math.cos(math.radians(20.0))
    deviation = _normal_deviation_um(
        base.segment("left_involute"), relieved.segment("left_involute"), r_b
    )
    radius, _ = _half_angles(base.segment("left_involute"))
    assert deviation[-1] == pytest.approx(-23.6, abs=0.02)
    assert np.abs(deviation[radius < 0.5 * 51.946 - 0.01]).max() < 1.0e-9
    # linear in the roll length: half the amount half way along the relief zone
    rho = np.sqrt(radius * radius - r_b * r_b)
    rho_s, rho_a = math.sqrt((0.5 * 51.946) ** 2 - r_b**2), rho[-1]
    half = np.interp(0.5 * (rho_s + rho_a), rho, deviation)
    assert half == pytest.approx(-11.8, abs=0.1)
    # the fillet and the tip circle stay; both flanks carry the relief (mirror symmetry)
    assert np.allclose(base.segment("left_fillet"), relieved.segment("left_fillet"))
    assert relieved.tip_diameter_mm == base.tip_diameter_mm
    # (the join keeps the shared points once: the left segment lacks its first point, the
    # reversed right one its last, so the two are offset by one point)
    left = relieved.segment("left_involute")
    right = relieved.segment("right_involute")[::-1]
    assert np.allclose(left[:-1] * np.array([-1.0, 1.0]), right[1:])
    # empty modifications are the base contour
    assert ct.tooth_contour(kst_e, "pinion", modification=ct.ProfileModification()) == base
    with pytest.raises(InputRangeError):
        ct.tooth_contour(kst_e, "pinion", modification="relief")  # type: ignore[arg-type]
    with pytest.raises(GeometryInfeasibleError):
        ct.tooth_contour(
            kst_e,
            "pinion",
            modification=ct.ProfileModification(
                tip_relief_um=10.0, tip_relief_start_diameter_mm=53.0
            ),
        )


def test_profile_slope_pivots_on_the_measuring_circle_and_turns_the_fillet(
    kst_e: GenerationResult,
) -> None:
    slope = ct.ProfileModification(
        profile_slope_um=10.25,
        profile_control_diameter_mm=50.3,
        profile_slope_pivot_diameter_mm=D_M_WHEEL,
    )
    base = ct.tooth_contour(kst_e, "wheel")
    sloped = ct.tooth_contour(kst_e, "wheel", modification=slope)
    r_b = 0.5 * 52.0 * math.cos(math.radians(20.0))
    base_flank, flank = base.segment("left_involute"), sloped.segment("left_involute")
    deviation = _normal_deviation_um(base_flank, flank, r_b)
    radius, _ = _half_angles(base_flank)
    rho = np.sqrt(radius * radius - r_b * r_b)

    def rho_of(d: float) -> float:
        return math.sqrt((0.5 * d) ** 2 - r_b**2)

    expected = 10.25 * (rho - rho_of(D_M_WHEEL)) / (rho_of(54.022) - rho_of(50.3))
    assert np.allclose(deviation, expected, atol=0.02)
    assert np.interp(0.5 * D_M_WHEEL, radius, deviation) == pytest.approx(0.0, abs=0.02)
    assert deviation[0] < 0.0 < expected[-1]
    # the fillet turned with the first involute point (the root form point, which the join
    # keeps as the last point of the fillet): the contour is continuous there
    r_f, psi_f = _half_angles(base.segment("left_fillet"))
    r_t, psi_t = _half_angles(sloped.segment("left_fillet"))
    rho_Ff = math.sqrt(r_f[-1] ** 2 - r_b**2)
    turn = 10.25 * (rho_Ff - rho_of(D_M_WHEEL)) / (rho_of(54.022) - rho_of(50.3)) * 1.0e-3 / r_b
    assert np.allclose(r_f, r_t) and np.allclose(psi_t - psi_f, turn, atol=1.0e-12)
    # the edge break of the tool follows the turned end of the involute: no step at d_Fa
    joined = sloped.as_array()
    steps = np.hypot(*(joined[1:] - joined[:-1]).T)
    assert float(steps.max()) < 0.05


def test_tip_corner_radius_replaces_the_chamfer_by_a_tangent_arc(kst_e: GenerationResult) -> None:
    base = ct.tooth_contour(kst_e, "wheel")
    rounded = ct.tooth_contour(kst_e, "wheel", modification=WHEEL)
    r_a, r_K = 0.5 * 54.022, 0.21
    arc = rounded.segment("left_tip_flank")
    flank = rounded.segment("left_involute")
    # the involute ends at the tangent point, the arc runs from there to the tip circle
    touch = flank[-1]
    assert rounded.tip_form_diameter_mm == pytest.approx(2.0 * float(np.hypot(*touch)))
    assert rounded.tip_form_diameter_mm < base.tip_form_diameter_mm < base.tip_diameter_mm
    top = arc[-1]
    assert float(np.hypot(*top)) == pytest.approx(r_a, abs=1.0e-9)
    # every arc point lies r_K from a centre on the circle r_a - r_K (the tangent point is
    # interpolated on the sampled flank, hence the tolerance of a few nanometres)
    centre = top * (r_a - r_K) / r_a
    assert np.allclose(np.hypot(*(arc - centre).T), r_K, atol=1.0e-6)
    assert float(np.hypot(*(touch - centre))) == pytest.approx(r_K, abs=1.0e-6)
    # tangent to the flank: the flank's direction at the tangent point is normal to the radius
    direction = flank[-1] - flank[-2]
    direction = direction / np.hypot(*direction)
    assert abs(float(direction @ (touch - centre))) < 2.0e-4
    # the tip land lies between the mirrored arc ends, the tooth is symmetric
    tip = rounded.segment("tip")
    assert tip[-1][0] == pytest.approx(-top[0]) and tip[-1][1] == pytest.approx(top[1])
    whole = rounded.as_array()
    assert np.allclose(whole[::-1] * np.array([-1.0, 1.0]), whole, atol=1.0e-12)
    # the involute segment ends on the tangent point, the arc segment begins after it
    assert np.allclose(rounded.segment("left_involute")[-1], touch)
    assert float(np.hypot(*arc[0])) > float(np.hypot(*touch))
    # a radius the tooth cannot take
    with pytest.raises(GeometryInfeasibleError):
        ct.tooth_contour(
            kst_e, "wheel", modification=ct.ProfileModification(tip_edge_radius_mm=1.5)
        )
    with pytest.raises(GeometryInfeasibleError):
        ct.tip_edge_arc(np.array([[-1.0, 20.0], [-0.9, 21.0], [-0.8, 22.0]]), 27.0, 0.2, 8)
    with pytest.raises(InputRangeError):
        ct.tip_edge_arc(np.array([[-1.0, 20.0], [-0.9, 21.0]]), 27.0, 0.2, 8)


def test_the_rigid_surface_and_the_sector_mesh_take_the_modification(
    kst_e: GenerationResult,
) -> None:
    levels = rsf.surface_z_levels(np.linspace(-7.5, 7.5, 5), 17.0)
    plain = rsf.rigid_surface(kst_e, "pinion", teeth=7, max_edge_mm=0.05, z_levels_mm=levels)
    relieved = rsf.rigid_surface(
        kst_e, "pinion", teeth=7, max_edge_mm=0.05, z_levels_mm=levels, modification=RELIEF
    )
    # the tip corners of the middle tooth moved by the relief, the root did not
    r_b = 0.5 * 51.0 * math.cos(math.radians(20.0))
    profile_0 = plain.nodes_mm[: plain.profile_nodes, :2]
    profile_1 = relieved.nodes_mm[: relieved.profile_nodes, :2]
    r_0, r_1 = np.hypot(*profile_0.T), np.hypot(*profile_1.T)
    assert r_0.max() == pytest.approx(r_1.max()) and r_0.min() == pytest.approx(r_1.min())
    # the tip land of the middle tooth (centred on +y) got wider by twice the relief at the
    # corner, measured along the tip circle: C_a / cos(alpha_a) per corner
    on_tip_0 = profile_0[(r_0 > 0.5 * 52.894 - 1.0e-6) & (np.abs(profile_0[:, 0]) < 1.0)]
    on_tip_1 = profile_1[(r_1 > 0.5 * 52.894 - 1.0e-6) & (np.abs(profile_1[:, 0]) < 1.0)]
    chord_0 = float(on_tip_0[:, 0].max() - on_tip_0[:, 0].min())
    chord_1 = float(on_tip_1[:, 0].max() - on_tip_1[:, 0].min())
    assert chord_1 == pytest.approx(chord_0 - 2.0 * 23.6e-3 / (r_b / 26.447), abs=2.0e-3)
    # the sector mesh resolves the arc with the rows of the tip edge break
    counts = MeshCounts(
        over_tooth_height=12,
        at_tip_edge_break=3,
        at_tooth_root=20,
        over_tooth_thickness=8,
        root_layers=2,
        rim_rings=4,
        shoulder_columns=2,
    )
    mesh = sm.sector_mesh(
        kst_e,
        "wheel",
        teeth=1,
        rim_rings=12,
        bore_radius_mm=16.5,
        counts=counts,
        modification=WHEEL,
    )
    rounded = ct.tooth_contour(kst_e, "wheel", modification=WHEEL)
    r_a, r_K = 0.5 * 54.022, 0.21
    # the surface nodes between the tangent diameter and the tip circle lie on the arc: three
    # rows give two interior nodes per corner, each r_K from the centre of its corner's arc
    surface = mesh.points_mm[mesh.surface_path]
    radius = np.hypot(*surface.T)
    r_touch = 0.5 * rounded.tip_form_diameter_mm
    assert mesh.tip_form_radius_mm == pytest.approx(r_touch)
    on_arc = surface[(radius > r_touch + 1.0e-6) & (radius < r_a - 1.0e-6)]
    assert len(on_arc) == 4
    top = rounded.segment("left_tip_flank")[-1]
    left_centre = top * (r_a - r_K) / r_a
    right_centre = left_centre * np.array([-1.0, 1.0])
    nearest = np.minimum(np.hypot(*(on_arc - left_centre).T), np.hypot(*(on_arc - right_centre).T))
    assert np.allclose(nearest, r_K, atol=1.0e-3)
    with pytest.raises(NotSupportedError):
        sm.sector_mesh(
            kst_e,
            "wheel",
            teeth=1,
            rim_rings=12,
            counts=counts,
            fillet=FilletVariant(kind="bezier"),
            modification=WHEEL,
        )
    with pytest.raises(InputRangeError):
        sm.sector_mesh(kst_e, "wheel", teeth=1, rim_rings=12, modification="x")  # type: ignore[arg-type]
