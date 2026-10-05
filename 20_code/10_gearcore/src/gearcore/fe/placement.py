"""Position of an external spur gear pair with the working flanks in contact.

Frame: the transverse section in millimetres. The axis of the pinion is the origin, the axis of
the wheel lies at (a_w, 0). An angle is measured about the axis of the gear in question, from +x,
counter-clockwise; the tooth centre angle of a gear is the angle of the centre line of one of its
teeth.

Involute flanks touch on the line of action, the common tangent of the base circles. A flank
point with the radius of curvature rho_y (DIN ISO 21771:2014-08 Eq. (17)) lies at the distance
rho_y from the tangent point of its base circle, and the tangent points T_1 and T_2 lie
a_w sin(alpha_wt) apart (Eq. (87)). The pair is therefore placed by one number, the radius of
curvature rho_1 of the pinion flank at the contact point of the tooth pair that is followed:

    left flanks working (the pinion drives counter-clockwise, its torque is positive about +z;
    the left flank of a tooth is its counter-clockwise side, the ``left_*`` segments of
    ``contour.ToothContour``):

        theta_1 = rho_1 / r_b1 - psi_b1 - alpha_wt
        theta_2 = pi - alpha_wt - psi_b2 + rho_2 / r_b2,   rho_2 = a_w sin(alpha_wt) - rho_1
        contact point = r_b1 (cos alpha_wt, -sin alpha_wt) + rho_1 (sin alpha_wt, cos alpha_wt)

    right flanks working (the pinion drives clockwise, its torque is negative about +z): the
    mirror image in the x axis.

psi_b is the base tooth thickness half angle (Eq. (42)) of the generated tooth, that is with the
generating profile shift coefficient x_E; the whole backlash then lies at the back flanks. The
teeth k of the pinion and -k of the wheel (counted counter-clockwise from the followed teeth)
touch at the same time, their contact points one base pitch apart.

Helical gears are not placed here (``NotSupportedError``).
"""

import math
from dataclasses import dataclass
from typing import Literal

import numpy as np
from numpy.typing import NDArray
from pydantic import Field

from gearcore import involute as iv
from gearcore import pair as pr
from gearcore._safe import finite_input
from gearcore.errors import InputRangeError, NotSupportedError
from gearcore.models.common import FrozenModel, Pair
from gearcore.models.results import GenerationResult
from gearcore.quantities import Q

EQ_EXEMPT = (
    "working_flank_of_the_driving_pinion",
    "pinion_torque_sign",
    "path_of_contact_limits",
    "mesh_position",
    "flank_distance",
    "back_flank_distance",
    "fixed_axes",
    "wheel_fixed",
    "placed",
)
"""Assemblies of traced functions (Eq. (17), (42), (83), (84), (87)) into positions in the plane;
they introduce no equation of their own."""

Array = NDArray[np.float64]
Flank = Literal["left", "right"]
Rotation = Literal["clockwise", "counterclockwise"]

CONTACT_PATH_TOLERANCE = 1.0e-9
"""Relative tolerance, in base pitches, within which a tooth pair counts as lying on the end
points A and E of the path of contact."""


class MeshPosition(FrozenModel):
    """One position of the pair: both gears on fixed axes, the working flanks in contact.

    ``radius_of_curvature_mm`` holds rho_1 and rho_2 of the followed tooth pair at its contact
    point. ``tooth_centre_angle_deg`` is the angle of the centre line of the followed tooth of
    each gear about its own axis: of the pinion in (-180, 180], of the wheel in [0, 360), so that
    neither jumps while the tooth passes through the mesh. ``tooth_pairs_on_path`` lists the k for which pinion tooth k
    and wheel tooth -k touch between the points A and E of the path of contact; outside A to E
    the followed pair itself (k = 0) is not among them.
    """

    centre_distance_mm: float = Q("centre_distance", gt=0.0)
    working_flank: Flank
    radius_of_curvature_mm: Pair[float] = Q("radius_of_curvature")
    tooth_centre_angle_deg: Pair[float] = Field(
        description="angle of the centre line of the followed tooth about the axis of its gear"
    )
    contact_point_mm: tuple[float, float] = Field(
        description="contact point of the followed tooth pair on the line of action"
    )
    tooth_pairs_on_path: tuple[int, ...]


class Placement(FrozenModel):
    """Rigid position of both gears in the plane: axis and tooth centre angle of each gear."""

    axis_mm: Pair[tuple[float, float]]
    tooth_centre_angle_deg: Pair[float]


@dataclass(frozen=True)
class _Mesh:
    """What the position depends on (millimetres, radians); index 0 pinion, 1 wheel."""

    a_w: float
    alpha_wt: float
    r_b: tuple[float, float]
    psi_b: tuple[float, float]
    pitch_angle: tuple[float, float]
    p_bt: float
    t1_t2: float
    rho_a1: float
    rho_e1: float


def _mesh(generation: GenerationResult) -> _Mesh:
    if not isinstance(generation, GenerationResult):
        raise InputRangeError(
            f"a GenerationResult of compute_generation is required, got {type(generation).__name__}"
        )
    pair = generation.inputs
    if pair.helix_angle_deg != 0.0:
        raise NotSupportedError(
            f"helix angle {pair.helix_angle_deg!r} deg: only spur gear pairs are placed"
        )
    geometry = generation.pair_geometry
    m_n = pair.normal_module_mm
    alpha_n = math.radians(pair.normal_pressure_angle_deg)
    alpha_t = iv.transverse_pressure_angle(alpha_n, 0.0)
    d_b: list[float] = []
    psi_b: list[float] = []
    pitch_angle: list[float] = []
    for gear in (generation.gears.pinion, generation.gears.wheel):
        z = gear.number_of_teeth
        d_b.append(iv.base_diameter(z, m_n, alpha_n, 0.0))
        psi_b.append(
            iv.base_tooth_thickness_half_angle(
                iv.tooth_thickness_half_angle(
                    z, gear.generating_profile_shift_coefficient, alpha_n
                ),
                alpha_t,
            )
        )
        pitch_angle.append(2.0 * math.pi / z)
    a_w = geometry.centre_distance_mm
    alpha_wt = math.radians(geometry.transverse_working_pressure_angle_deg)
    t1_t2 = pr.length_between_tangent_points(a_w, alpha_wt)
    active_tip = geometry.active_tip_diameter_mm
    rho_e1 = pr.radius_of_curvature_at_active_tip(active_tip.pinion, d_b[0])
    rho_a2 = pr.radius_of_curvature_at_active_tip(active_tip.wheel, d_b[1])
    return _Mesh(
        a_w=a_w,
        alpha_wt=alpha_wt,
        r_b=(0.5 * d_b[0], 0.5 * d_b[1]),
        psi_b=(psi_b[0], psi_b[1]),
        pitch_angle=(pitch_angle[0], pitch_angle[1]),
        p_bt=geometry.transverse_base_pitch_mm,
        t1_t2=t1_t2,
        rho_a1=t1_t2 - rho_a2,
        rho_e1=rho_e1,
    )


def _flank(flank: str) -> Flank:
    if flank == "left":
        return "left"
    if flank == "right":
        return "right"
    raise InputRangeError(f"flank must be 'left' or 'right', got {flank!r}")


def _wrapped(angle: float) -> float:
    """The angle in (-pi, pi]: the range of the pinion teeth in the mesh, which lie about 0."""
    return math.atan2(math.sin(angle), math.cos(angle))


def _wrapped_about_pi(angle: float) -> float:
    """The angle in [0, 2 pi): the range of the wheel teeth in the mesh, which lie about pi, so
    that the angle of a tooth does not jump while it passes through the mesh."""
    return math.pi + _wrapped(angle - math.pi)


def working_flank_of_the_driving_pinion(rotation: Rotation) -> Flank:
    """The flanks that carry the load when the pinion drives and turns in ``rotation``.

    The sense is the one seen in the frame of this module (x to the right, y upwards, the pinion
    on the left): counter-clockwise is positive about +z. A pinion driving clockwise pushes with
    the right flanks of its teeth (their clockwise side); the wheel then turns counter-clockwise.
    """
    if rotation == "clockwise":
        return "right"
    if rotation == "counterclockwise":
        return "left"
    raise InputRangeError(f"rotation must be 'clockwise' or 'counterclockwise', got {rotation!r}")


def pinion_torque_sign(working_flank: Flank) -> float:
    """Sign about +z of the torque on the pinion that presses the working flanks together:
    +1 for the left flanks (counter-clockwise), -1 for the right flanks (clockwise). The
    reaction that holds the wheel has the same sign, because the flank force turns both gears
    in opposite senses."""
    return 1.0 if _flank(working_flank) == "left" else -1.0


def path_of_contact_limits(generation: GenerationResult) -> tuple[float, float]:
    """Radius of curvature of the pinion flank at the start A and the end E of the path of
    contact (mm): rho_A1 = T_1 T_2 - rho_A2 (Eq. (87), (83)) and rho_E1 (Eq. (84))."""
    mesh = _mesh(generation)
    return mesh.rho_a1, mesh.rho_e1


def mesh_position(
    generation: GenerationResult, rho_1_mm: float, *, working_flank: Flank
) -> MeshPosition:
    """The position in which the followed tooth pair touches where the pinion flank has the
    radius of curvature ``rho_1_mm``.

    ``rho_1_mm`` may lie outside A to E by up to the tangent points (0 to T_1 T_2): the gears are
    then where the rolling motion carries them, and another tooth pair is the one in contact.
    """
    mesh = _mesh(generation)
    side = _flank(working_flank)
    rho_1 = finite_input(rho_1_mm, "radius of curvature rho_1")
    if not 0.0 <= rho_1 <= mesh.t1_t2:
        raise InputRangeError(
            f"rho_1 = {rho_1!r} mm lies outside the tangent points (0 to {mesh.t1_t2!r} mm)"
        )
    rho_2 = mesh.t1_t2 - rho_1
    theta_1 = rho_1 / mesh.r_b[0] - mesh.psi_b[0] - mesh.alpha_wt
    theta_2 = math.pi - mesh.alpha_wt - mesh.psi_b[1] + rho_2 / mesh.r_b[1]
    sin_a, cos_a = math.sin(mesh.alpha_wt), math.cos(mesh.alpha_wt)
    x = mesh.r_b[0] * cos_a + rho_1 * sin_a
    y = -mesh.r_b[0] * sin_a + rho_1 * cos_a
    mirror = 1.0 if side == "left" else -1.0
    # pinion tooth k and wheel tooth -k touch at rho_1 + k p_bt (left) or rho_1 - k p_bt (right);
    # no more teeth than the pinion has can lie between the tangent points
    slack = CONTACT_PATH_TOLERANCE * mesh.p_bt
    sign = 1 if side == "left" else -1
    teeth = generation.gears.pinion.number_of_teeth
    pairs = sorted(
        sign * k
        for k in range(-teeth, teeth + 1)
        if mesh.rho_a1 - slack <= rho_1 + k * mesh.p_bt <= mesh.rho_e1 + slack
    )
    return MeshPosition(
        centre_distance_mm=mesh.a_w,
        working_flank=side,
        radius_of_curvature_mm=Pair(pinion=rho_1, wheel=rho_2),
        tooth_centre_angle_deg=Pair(
            pinion=math.degrees(_wrapped(mirror * theta_1)),
            wheel=math.degrees(_wrapped_about_pi(mirror * theta_2)),
        ),
        contact_point_mm=(x, mirror * y),
        tooth_pairs_on_path=tuple(pairs),
    )


def flank_distance(
    generation: GenerationResult,
    position: MeshPosition,
    flank: Flank,
    *,
    pinion_tooth: int = 0,
    wheel_tooth: int = 0,
) -> float:
    """Distance of the involutes of two facing flanks along their line of action (mm).

    Positive: open; zero: in contact; negative: the flanks would overlap. ``pinion_tooth`` and
    ``wheel_tooth`` count the teeth counter-clockwise from the followed ones. The value holds
    for the involutes as curves; whether the point of the smallest distance lies on the usable
    flanks is not checked.
    """
    mesh = _mesh(generation)
    if not isinstance(position, MeshPosition):
        raise InputRangeError(f"a MeshPosition is required, got {type(position).__name__}")
    side = 1.0 if _flank(flank) == "left" else -1.0
    inv_wt = iv.inv(mesh.alpha_wt)
    theta_1 = _wrapped(
        math.radians(position.tooth_centre_angle_deg.pinion) + pinion_tooth * mesh.pitch_angle[0]
    )
    theta_2 = _wrapped(
        math.radians(position.tooth_centre_angle_deg.wheel)
        + wheel_tooth * mesh.pitch_angle[1]
        - math.pi
    )
    overlap = mesh.r_b[0] * (side * theta_1 + mesh.psi_b[0] - inv_wt) + mesh.r_b[1] * (
        side * theta_2 + mesh.psi_b[1] - inv_wt
    )
    return -overlap


def back_flank_distance(generation: GenerationResult) -> float:
    """Distance of the back flanks along their line of action while the working flanks touch
    (mm): one base pitch less the base tooth thicknesses on the working pitch circles' involutes,
    p_bt - 2 r_b1 (psi_b1 - inv alpha_wt) - 2 r_b2 (psi_b2 - inv alpha_wt). It does not depend
    on the position."""
    mesh = _mesh(generation)
    inv_wt = iv.inv(mesh.alpha_wt)
    return mesh.p_bt - 2.0 * (
        mesh.r_b[0] * (mesh.psi_b[0] - inv_wt) + mesh.r_b[1] * (mesh.psi_b[1] - inv_wt)
    )


def fixed_axes(position: MeshPosition) -> Placement:
    """Both gears on their axes: pinion at the origin, wheel at (a_w, 0)."""
    if not isinstance(position, MeshPosition):
        raise InputRangeError(f"a MeshPosition is required, got {type(position).__name__}")
    return Placement(
        axis_mm=Pair(pinion=(0.0, 0.0), wheel=(position.centre_distance_mm, 0.0)),
        tooth_centre_angle_deg=position.tooth_centre_angle_deg,
    )


def wheel_fixed(position: MeshPosition, *, wheel_tooth_centre_angle_deg: float = 90.0) -> Placement:
    """The same relative position with the wheel at rest: its axis at (a_w, 0), its followed
    tooth at ``wheel_tooth_centre_angle_deg``; the pinion is carried around the wheel axis."""
    if not isinstance(position, MeshPosition):
        raise InputRangeError(f"a MeshPosition is required, got {type(position).__name__}")
    target = finite_input(wheel_tooth_centre_angle_deg, "tooth centre angle of the wheel")
    turn = math.radians(target - position.tooth_centre_angle_deg.wheel)
    a_w = position.centre_distance_mm
    # the pinion axis (0, 0) turned by ``turn`` about the wheel axis (a_w, 0)
    axis_1 = (a_w - a_w * math.cos(turn), -a_w * math.sin(turn))
    return Placement(
        axis_mm=Pair(pinion=axis_1, wheel=(a_w, 0.0)),
        tooth_centre_angle_deg=Pair(
            pinion=math.degrees(
                _wrapped(math.radians(position.tooth_centre_angle_deg.pinion) + turn)
            ),
            wheel=math.degrees(_wrapped_about_pi(math.radians(target))),
        ),
    )


def placed(points: Array, axis_mm: tuple[float, float], tooth_centre_angle_deg: float) -> Array:
    """Points of a tooth given with its centre line on +y (``contour.ToothContour``), turned so
    that the centre line has ``tooth_centre_angle_deg`` and moved to the axis ``axis_mm``."""
    xy = np.asarray(points, dtype=np.float64)
    if xy.ndim != 2 or xy.shape[1] != 2:
        raise InputRangeError("the points must be an (N, 2) array of x, y in mm")
    turn = math.radians(finite_input(tooth_centre_angle_deg, "tooth centre angle")) - 0.5 * math.pi
    c, s = math.cos(turn), math.sin(turn)
    return np.column_stack(
        (
            axis_mm[0] + c * xy[:, 0] - s * xy[:, 1],
            axis_mm[1] + s * xy[:, 0] + c * xy[:, 1],
        )
    )
