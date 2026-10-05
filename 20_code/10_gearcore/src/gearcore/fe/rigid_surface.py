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


def _tooth_profile(contour: ct.ToothContour, pitch: float, max_edge_mm: float) -> Array:
    """One pitch of the profile, counter-clockwise, the tooth centre on +y: from the centre line
    of the gap on the right (clockwise) to the centre line of the gap on the left, without the
    last point."""
    r_f = 0.5 * contour.generated_root_diameter_mm
    half = 0.5 * pitch
    tooth = contour.as_array()
    first = math.atan2(tooth[0, 0], tooth[0, 1])
    last = math.atan2(tooth[-1, 0], tooth[-1, 1])
    if first < -half - ct.JOIN_TOLERANCE or last > half + ct.JOIN_TOLERANCE:
        raise GeometryInfeasibleError(
            "the fillets of neighbouring teeth overlap: no root circle between them"
        )
    raw: list[Array] = []
    if last < half - ct.JOIN_TOLERANCE:
        # root circle from the gap centre line on the right to the right fillet
        angles = np.linspace(half, last, CONTOUR_POINTS)
        raw.append(np.column_stack((r_f * np.sin(angles), r_f * np.cos(angles))))
    for name in reversed(ct.SEGMENTS):  # right fillet ... left fillet: counter-clockwise
        segment = contour.segment(name)[::-1]
        if len(segment):
            raw.append(segment)
    if first > -half + ct.JOIN_TOLERANCE:
        angles = np.linspace(first, -half, CONTOUR_POINTS)
        raw.append(np.column_stack((r_f * np.sin(angles), r_f * np.cos(angles))))
    # every piece runs up to the first point of the next one, so that the corners of the contour
    # are ends of pieces and thereby nodes
    pieces: list[Array] = []
    for index, segment in enumerate(raw):
        piece = segment
        if index + 1 < len(raw):
            corner = raw[index + 1][:1]
            apart = float(np.hypot(*(segment[-1] - corner[0])))
            if apart > ct.JOIN_TOLERANCE * float(np.hypot(*corner[0])):
                piece = np.concatenate((segment, corner))
        if len(piece) >= 2:
            pieces.append(piece)
    return np.concatenate([_divided(piece, max_edge_mm) for piece in pieces])


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
) -> RigidSurface:
    """The swept tooth surface of ``teeth`` teeth of the gear ``role`` on the z-levels
    ``z_levels_mm`` (see ``surface_z_levels``)."""
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
    one = _tooth_profile(contour, pitch, edge)
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
