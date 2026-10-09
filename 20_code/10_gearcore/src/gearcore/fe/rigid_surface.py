"""Rigid tooth surface of a spur gear: the transverse contour of some teeth swept along the face
width, as 4-node surface elements. No volume, no end faces, no cut planes, no material.

It stands for the steel gear of a steel-plastic pair, whose deformation is negligible beside the
one of the plastic gear. All of its nodes follow one reference point on the axis.

Frame as for the sector mesh: millimetres, the gear axis at the origin, the middle of the teeth
on +y, the teeth numbered counter-clockwise. The profile runs counter-clockwise from the centre
line of the gap before tooth 1 to the centre line of the gap after the last tooth; a quad is
(profile node i, i + 1 on a z-level, then i + 1, i on the level above), so its right-hand normal
points out of the gear, towards the mating gear.

Along the profile every element of the contour (fillet, involute, tip flank, tip, root circle)
is divided into equal steps no longer than ``max_edge_mm``; the corners between the elements are
nodes. Along z the surface has the levels of the mating gear where both overlap, and steps of at
most the same size beyond.

``tip_rounding_mm`` replaces the two corners of the tip land by circular arcs tangent to the
tip land and the flank (the deburring of a machined steel edge, a modelling choice of the rigid
surface, not a datum of the gear): a flank node of the plastic gear that sits on the sharp
corner sees two normals and chatters in node-to-surface contact (11 broken-off positions of
the 60-per-pitch study, 2026-10-07); the arc gives it one continuous normal. Zero keeps the
sharp corner of the drawing (FE-17).
"""

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from gearcore import contour as ct
from gearcore._safe import finite_input, integer_input, positive_input
from gearcore.contour import Role
from gearcore.errors import GeometryInfeasibleError, InputRangeError, NotSupportedError
from gearcore.models.results import GenerationResult

EQ_EXEMPT = ("surface_z_levels", "rigid_surface")
"""Mesh construction: no equation of a norm."""

Array = NDArray[np.float64]
IntArray = NDArray[np.int64]

CONTOUR_POINTS = 2000
"""Points per element of the tooth contour the profile is resampled from."""
LEVEL_TOLERANCE = 1.0e-9
"""Relative to the face width: two z-levels closer than this are one."""


@dataclass(frozen=True)
class RigidSurface:
    """Nodes (x, y, z in mm) and quads of a swept tooth surface, 0-based.

    Node ``level * profile_nodes + i`` is profile node ``i`` on the z-level ``level``.
    """

    nodes_mm: Array
    quads: IntArray
    z_levels_mm: Array
    profile_nodes: int
    teeth: int
    number_of_teeth: int
    pitch_angle_rad: float


def _divided(points: Array, max_edge_mm: float) -> Array:
    """The polyline resampled into equal steps of arc length, none longer than ``max_edge_mm``;
    the end point is left out (it is the first point of the next piece)."""
    step = np.hypot(*(points[1:] - points[:-1]).T)
    arc = np.concatenate(([0.0], np.cumsum(step)))
    total = float(arc[-1])
    count = 1
    while total > count * max_edge_mm:
        count += 1
    at = total * np.arange(count, dtype=np.float64) / count
    return np.column_stack((np.interp(at, arc, points[:, 0]), np.interp(at, arc, points[:, 1])))


ROUNDING_FACETS = 4
"""Smallest number of facets along a rounding arc of the tip corners."""


def _arc_lengths_from_the_end(points: Array) -> Array:
    """Arc length of every point of a polyline measured from its last point."""
    steps = np.hypot(*(points[1:] - points[:-1]).T)
    return np.concatenate(([0.0], np.cumsum(steps[::-1])))[::-1]


def _length(points: Array) -> float:
    """Length of a polyline."""
    return float(np.hypot(*(points[1:] - points[:-1]).T).sum())


def _rounded_corner(
    before: Array, after: Array, radius_mm: float, max_edge_mm: float
) -> tuple[Array, Array, Array]:
    """The corner where ``before`` ends and ``after`` begins (the first point of ``after``)
    replaced by a circular arc of ``radius_mm`` tangent to both pieces: ``before`` and
    ``after`` shortened by the tangent length t = r / tan(phi / 2) (phi the angle between the
    pieces at the corner), and the arc between the two tangent points, sampled so that it gets
    at least ``ROUNDING_FACETS`` facets."""
    corner = after[0]
    scale = float(np.hypot(*corner))
    if float(np.hypot(*(before[-1] - corner))) > ct.JOIN_TOLERANCE * scale:
        before = np.concatenate((before, corner[None, :]))
    d_before = _arc_lengths_from_the_end(before)
    d_after = _arc_lengths_from_the_end(after[::-1])[::-1]
    # directions away from the corner, as chords over half the radius (the pieces are sampled
    # about a micrometre apart; the curvature of a flank or a tip land is negligible over that)
    reach = 0.5 * radius_mm
    k_a = int(np.argmax(d_before <= reach))  # first point of ``before`` within reach
    a = before[max(k_a - 1, 0)] - corner  # the point just outside the reach
    k_b = int(np.argmax(d_after > reach)) if bool(np.any(d_after > reach)) else len(after) - 1
    b = after[k_b] - corner
    if float(np.hypot(*a)) == 0.0 or float(np.hypot(*b)) == 0.0:
        raise GeometryInfeasibleError("a tip corner has a piece of zero length beside it")
    a = a / float(np.hypot(*a))
    b = b / float(np.hypot(*b))
    phi = math.acos(min(1.0, max(-1.0, float(a @ b))))
    if not math.radians(1.0) < phi < math.radians(179.0):
        raise GeometryInfeasibleError(
            f"the tip corner is no corner (angle {math.degrees(phi):.3f} deg between the pieces)"
        )
    tangent = radius_mm / math.tan(0.5 * phi)
    if tangent >= float(d_before[0]) or tangent >= float(d_after[-1]):
        raise GeometryInfeasibleError(
            f"tip rounding {radius_mm:g} mm: the tangent length {tangent:.4f} mm exceeds the "
            f"flank ({d_before[0]:.4f} mm) or the tip land ({d_after[-1]:.4f} mm) beside the corner"
        )
    bisector = a + b
    bisector = bisector / float(np.hypot(*bisector))
    centre = corner + bisector * radius_mm / math.sin(0.5 * phi)
    t_before = corner + a * tangent
    t_after = corner + b * tangent
    kept_before = np.concatenate((before[d_before > tangent], t_before[None, :]))
    kept_after = np.concatenate((t_after[None, :], after[d_after > tangent]))
    theta_1 = math.atan2(*(t_before - centre)[::-1])
    theta_2 = math.atan2(*(t_after - centre)[::-1])
    sweep = math.remainder(theta_2 - theta_1, 2.0 * math.pi)
    count = ROUNDING_FACETS  # no rounding function in the source: the step count by counting
    while abs(sweep) * radius_mm > count * max_edge_mm:
        count += 1
    angles = theta_1 + sweep * np.arange(count + 1, dtype=np.float64) / count
    arc = centre + radius_mm * np.column_stack((np.cos(angles), np.sin(angles)))
    return kept_before, arc, kept_after


def _tooth_profile(
    contour: ct.ToothContour, pitch: float, max_edge_mm: float, tip_rounding_mm: float = 0.0
) -> Array:
    """One pitch of the profile, counter-clockwise, the tooth centre on +y: from the centre line
    of the gap on the right (clockwise) to the centre line of the gap on the left, without the
    last point; with ``tip_rounding_mm`` the two corners of the tip land are rounded."""
    r_f = 0.5 * contour.generated_root_diameter_mm
    half = 0.5 * pitch
    tooth = contour.as_array()
    first = math.atan2(tooth[0, 0], tooth[0, 1])
    last = math.atan2(tooth[-1, 0], tooth[-1, 1])
    if first < -half - ct.JOIN_TOLERANCE or last > half + ct.JOIN_TOLERANCE:
        raise GeometryInfeasibleError(
            "the fillets of neighbouring teeth overlap: no root circle between them"
        )
    raw: list[tuple[str, Array, float]] = []  # name, points, largest edge
    if last < half - ct.JOIN_TOLERANCE:
        # root circle from the gap centre line on the right to the right fillet
        angles = np.linspace(half, last, CONTOUR_POINTS)
        raw.append(("root", np.column_stack((r_f * np.sin(angles), r_f * np.cos(angles))), max_edge_mm))
    for name in reversed(ct.SEGMENTS):  # right fillet ... left fillet: counter-clockwise
        segment = contour.segment(name)[::-1]
        if len(segment):
            raw.append((name, segment, max_edge_mm))
    if first > -half + ct.JOIN_TOLERANCE:
        angles = np.linspace(first, -half, CONTOUR_POINTS)
        raw.append(("root", np.column_stack((r_f * np.sin(angles), r_f * np.cos(angles))), max_edge_mm))
    if tip_rounding_mm > 0.0:
        tip = [k for k, (name, _, _) in enumerate(raw) if name == "tip"]
        if len(tip) != 1 or tip[0] == 0 or tip[0] == len(raw) - 1:
            raise GeometryInfeasibleError("tip rounding needs a tip land between two flanks")
        k = tip[0]
        # the corner after the tip land first, so that the index of the tip stays valid
        tip_points, arc_2, after = _rounded_corner(
            raw[k][1], raw[k + 1][1], tip_rounding_mm, max_edge_mm
        )
        before, arc_1, tip_points = _rounded_corner(
            raw[k - 1][1], tip_points, tip_rounding_mm, max_edge_mm
        )
        # the arcs keep at least ROUNDING_FACETS facets when the pieces are divided
        raw[k - 1 : k + 2] = [
            (raw[k - 1][0], before, max_edge_mm),
            ("tip_rounding", arc_1, min(max_edge_mm, _length(arc_1) / ROUNDING_FACETS)),
            ("tip", tip_points, max_edge_mm),
            ("tip_rounding", arc_2, min(max_edge_mm, _length(arc_2) / ROUNDING_FACETS)),
            (raw[k + 1][0], after, max_edge_mm),
        ]
    # every piece runs up to the first point of the next one, so that the corners of the contour
    # are ends of pieces and thereby nodes
    pieces: list[tuple[Array, float]] = []
    for index, (_, segment, edge) in enumerate(raw):
        piece = segment
        if index + 1 < len(raw):
            corner = raw[index + 1][1][:1]
            apart = float(np.hypot(*(segment[-1] - corner[0])))
            if apart > ct.JOIN_TOLERANCE * float(np.hypot(*corner[0])):
                piece = np.concatenate((segment, corner))
        if len(piece) >= 2:
            pieces.append((piece, edge))
    return np.concatenate([_divided(piece, edge) for piece, edge in pieces])


def surface_z_levels(
    mating_levels_mm: Array, face_width_mm: float, *, z_centre_mm: float = 0.0
) -> Array:
    """z-levels of a surface of ``face_width_mm`` about ``z_centre_mm``: the levels of the mating
    gear that lie within it, its two ends, and between them steps no larger than the largest
    step of the mating gear."""
    mating = np.sort(np.asarray(mating_levels_mm, dtype=np.float64).ravel())
    if len(mating) < 2 or not bool(np.all(np.isfinite(mating))):
        raise InputRangeError("the mating gear needs at least two finite z-levels")
    width = positive_input(face_width_mm, "face width")
    centre = finite_input(z_centre_mm, "z of the mid plane")
    low, high = centre - 0.5 * width, centre + 0.5 * width
    tolerance = LEVEL_TOLERANCE * width
    largest = float(np.diff(mating).max())
    inside = [float(z) for z in mating if low + tolerance < z < high - tolerance]
    marks = [low, *inside, high]
    levels = [low]
    for start, end in zip(marks[:-1], marks[1:], strict=True):
        count = 1
        while end - start > count * largest * (1.0 + LEVEL_TOLERANCE):
            count += 1
        levels.extend(start + (end - start) * k / count for k in range(1, count + 1))
    return np.array(levels, dtype=np.float64)


def rigid_surface(
    generation: GenerationResult,
    role: Role,
    *,
    teeth: int,
    max_edge_mm: float,
    z_levels_mm: Array,
    tip_rounding_mm: float = 0.0,
) -> RigidSurface:
    """The swept tooth surface of ``teeth`` teeth of the gear ``role`` on the z-levels
    ``z_levels_mm`` (see ``surface_z_levels``); ``tip_rounding_mm`` > 0 rounds the two corners
    of the tip land (see the module)."""
    if not isinstance(generation, GenerationResult):
        raise InputRangeError(
            f"a GenerationResult of compute_generation is required, got {type(generation).__name__}"
        )
    if generation.inputs.helix_angle_deg != 0.0:
        raise NotSupportedError(
            f"helix angle {generation.inputs.helix_angle_deg!r} deg: only spur gears are swept"
        )
    count = integer_input(teeth, "number of teeth of the surface")
    edge = positive_input(max_edge_mm, "largest edge along the profile")
    rounding = finite_input(tip_rounding_mm, "tip rounding")
    if rounding < 0.0:
        raise InputRangeError(f"the tip rounding must not be negative, got {tip_rounding_mm!r}")
    levels = np.asarray(z_levels_mm, dtype=np.float64).ravel()
    if len(levels) < 2 or not bool(np.all(np.isfinite(levels)) and np.all(np.diff(levels) > 0.0)):
        raise InputRangeError("the z-levels must be at least two rising finite values")
    contour = ct.tooth_contour(generation, role, points=CONTOUR_POINTS)
    z = contour.number_of_teeth
    if not 1 <= count <= z - 1:
        raise InputRangeError(
            f"a surface of a gear with {z} teeth holds 1 to {z - 1} teeth, got {teeth!r}"
        )
    pitch = 2.0 * math.pi / z
    one = _tooth_profile(contour, pitch, edge, rounding)
    pieces = []
    for j in range(count):
        turn = (j - 0.5 * (count - 1)) * pitch  # counter-clockwise from +y
        c, s = math.cos(turn), math.sin(turn)
        pieces.append(
            np.column_stack((c * one[:, 0] - s * one[:, 1], s * one[:, 0] + c * one[:, 1]))
        )
    # the end of the profile: the gap centre line after the last tooth, on the root circle
    end_angle = (0.5 * (count - 1) + 0.5) * pitch
    r_end = float(np.hypot(*one[0]))
    pieces.append(np.array([[-r_end * math.sin(end_angle), r_end * math.cos(end_angle)]]))
    profile = np.concatenate(pieces)
    n = len(profile)
    nodes = np.empty((len(levels) * n, 3), dtype=np.float64)
    nodes[:, :2] = np.tile(profile, (len(levels), 1))
    nodes[:, 2] = np.repeat(levels, n)
    along = np.arange(n - 1, dtype=np.int64)
    quads = np.concatenate(
        [
            np.column_stack(
                (along + k * n, along + 1 + k * n, along + 1 + (k + 1) * n, along + (k + 1) * n)
            )
            for k in range(len(levels) - 1)
        ]
    )
    levels = levels.copy()
    for array in (nodes, quads, levels):
        array.setflags(write=False)
    return RigidSurface(
        nodes_mm=nodes,
        quads=quads,
        z_levels_mm=levels,
        profile_nodes=n,
        teeth=count,
        number_of_teeth=z,
        pitch_angle_rad=pitch,
    )
