"""Transverse tooth contour of a generated external gear, spur and helical.

The contour is assembled from the generated elements of ``gearcore.generation`` and
``gearcore.trochoid``: the fillet of the tool tip rounding from the root circle to the root form
circle, the involute (DIN ISO 21771:2014-08 §4.3, §4.7 with x_E) from the root form circle to the
tip form circle, the tip: the edge break involute of the tool (DIN 3960:1987-03 A.3.1) or a
chamfer given by h_K and s_aK (DIN ISO 21771 §6.1.2, Bild 24) up to the tip circle, and the tip
circle. One tooth is centred on the +Y axis and runs from the root circle on the left flank over
the tip to the root circle on the right flank, as the STplus contour export does (manual §6.4.2;
``io/stplus_contour.py``); the whole gear is the tooth repeated z times with the root circle
between the teeth.

Coordinates are millimetres in the transverse section; they name no quantity of the registry.
``compare`` measures the normal distance of reference points from the contour (point to
polyline), per region, so that a contour of STplus or of another program can be checked against
this one at the level of micrometres.
"""

import math
from typing import Literal, Self

import numpy as np
from numpy.typing import NDArray
from pydantic import Field, model_validator

from gearcore import generation as gn
from gearcore import involute as iv
from gearcore import pair as pr
from gearcore import trochoid as tr
from gearcore._safe import EPS, finite_input, integer_input, positive_input
from gearcore.errors import GeometryInfeasibleError, InputRangeError
from gearcore.models.common import FrozenModel
from gearcore.models.inputs import PairInput
from gearcore.models.results import GearGeneration, GenerationResult
from gearcore.quantities import Q
from gearcore.trace import eq

SOURCE = "ISO21771:2014"
OLD = "DIN3960:1987"

EQ_EXEMPT = ("tooth_contour", "gear_polygon", "compare", "distances", "stplus_contour")
"""Orchestrators of traced functions (sampling, assembly, measurement) and the fixture loader."""

Array = NDArray[np.float64]
Role = Literal["pinion", "wheel"]
Region = Literal["fillet", "involute", "tip"]

SEGMENTS = (
    "left_fillet",
    "left_involute",
    "left_tip_flank",
    "tip",
    "right_tip_flank",
    "right_involute",
    "right_fillet",
)
DEFAULT_POINTS = 200
"""Points per fillet and per involute flank; the tip flank and the tip arc take a quarter."""


class ContourSegment(FrozenModel):
    """Index range [start, end) of one element of the contour in ``ToothContour.points``."""

    name: str
    start: int = Field(ge=0)
    end: int = Field(ge=0)


class ToothContour(FrozenModel):
    """One tooth of a generated gear in the transverse section.

    ``points`` run from the point where the left fillet leaves the root circle, over the tip, to
    the point where the right fillet meets the root circle; x to the right, y outwards, the tooth
    centre on +y (mm). ``segments`` name the elements. The landmark diameters are those of the
    generation. Between two teeth the gear has the root circle (see ``gear_polygon``).
    """

    number_of_teeth: int = Q("number_of_teeth", strict=True)
    generated_root_diameter_mm: float = Q("generated_root_diameter", gt=0.0)
    root_form_diameter_mm: float = Q("root_form_diameter", gt=0.0)
    tip_form_diameter_mm: float = Q("tip_form_diameter", gt=0.0)
    tip_diameter_mm: float = Q("tip_diameter", gt=0.0)
    undercut: bool
    points: tuple[tuple[float, float], ...] = Field(min_length=3)
    segments: tuple[ContourSegment, ...]

    @model_validator(mode="after")
    def _segments_cover_the_points(self) -> Self:
        expected = 0
        for entry in self.segments:
            if entry.start != expected or entry.end < entry.start:
                raise ValueError(f"segment {entry.name!r} does not follow the one before it")
            expected = entry.end
        if expected != len(self.points):
            raise ValueError(
                f"segments end at {expected}, the contour has {len(self.points)} points"
            )
        return self

    def as_array(self) -> Array:
        return np.asarray(self.points, dtype=np.float64)

    def segment(self, name: str) -> Array:
        for entry in self.segments:
            if entry.name == name:
                return self.as_array()[entry.start : entry.end]
        raise InputRangeError(f"unknown contour segment {name!r}; known: {SEGMENTS}")


class ContourDiff(FrozenModel):
    """Normal distances of reference points from a contour, per region (micrometres).

    Regions by the radius of the reference point: ``fillet`` below the root form circle,
    ``tip`` above the tip form circle, ``involute`` between. ``region_of_max`` names the region
    of the largest distance.
    """

    reference_points: int = Field(ge=1)
    max_um: float = Field(ge=0.0)
    rms_um: float = Field(ge=0.0)
    region_of_max: Region
    fillet_points: int = Field(ge=0)
    fillet_max_um: float = Field(ge=0.0)
    fillet_rms_um: float = Field(ge=0.0)
    involute_points: int = Field(ge=0)
    involute_max_um: float = Field(ge=0.0)
    involute_rms_um: float = Field(ge=0.0)
    tip_points: int = Field(ge=0)
    tip_max_um: float = Field(ge=0.0)
    tip_rms_um: float = Field(ge=0.0)


# --- elements ---------------------------------------------------------------------------------------


def _polar(radius: Array, psi: Array, side: float) -> Array:
    """Cartesian points of a flank at the half angles ``psi`` (+1: right flank, -1: left)."""
    return np.column_stack((side * radius * np.sin(psi), radius * np.cos(psi)))


@eq(
    SOURCE,
    "(40)",
    section="4.7.2",
    page=35,
    note="sampled along the roll length between two circles",
)
@eq(SOURCE, "(17)", section="4.3.8", page=30)
def involute_flank(
    d_b_mm: float, psi_b_rad: float, d_start_mm: float, d_end_mm: float, n: int
) -> tuple[Array, Array]:
    """(radius, psi) of ``n`` involute points from d_start to d_end, evenly spaced in the roll
    length sqrt(d^2 - d_b^2) / 2 (Eq. (17)), psi from Eq. (40) with the base half angle."""
    d_b = positive_input(d_b_mm, "base diameter d_b")
    count = integer_input(n, "number of points")
    if count < 2:
        raise InputRangeError(f"an involute flank needs at least 2 points, got {n!r}")
    start = positive_input(d_start_mm, "start diameter")
    end = positive_input(d_end_mm, "end diameter")
    if not d_b * (1.0 - EPS) <= start < end:
        raise InputRangeError(
            f"involute from {start!r} to {end!r} must run outwards from the base circle {d_b!r}"
        )
    roll = np.linspace(
        iv.radius_of_curvature(max(start, d_b), d_b), iv.radius_of_curvature(end, d_b), count
    )
    radius = np.hypot(0.5 * d_b, roll)
    psi = np.array([tr.involute_half_angle(float(r), d_b, psi_b_rad) for r in radius])
    return radius, psi


@eq(
    SOURCE,
    "Bild 24",
    section="6.1.2",
    page=55,
    note="a chamfer given by h_K and s_aK, drawn as a straight line from the tip form circle to the tip circle",
)
def chamfer_flank(
    r_Fa_mm: float, psi_Fa_rad: float, r_a_mm: float, s_aK_mm: float, n: int
) -> tuple[Array, Array]:
    """(radius, psi) of ``n`` points on the straight chamfer between the involute point at the tip
    form circle and the point of the tip circle where the residual thickness s_aK remains."""
    r_Fa = positive_input(r_Fa_mm, "tip form radius")
    r_a = positive_input(r_a_mm, "tip radius")
    if r_a <= r_Fa:
        raise InputRangeError(
            f"the tip radius {r_a!r} must lie above the tip form radius {r_Fa!r} for a chamfer"
        )
    s_aK = positive_input(s_aK_mm, "residual tip thickness s_aK")
    count = integer_input(n, "number of points")
    if count < 2:
        raise InputRangeError(f"a chamfer needs at least 2 points, got {n!r}")
    psi_Fa = finite_input(psi_Fa_rad, "psi at the tip form circle")
    psi_a = 0.5 * s_aK / r_a
    if psi_a >= psi_Fa:
        raise GeometryInfeasibleError(
            f"the residual tip thickness s_aK = {s_aK!r} exceeds the tooth thickness at the tip form circle"
        )
    start = np.array([r_Fa * math.sin(psi_Fa), r_Fa * math.cos(psi_Fa)])
    end = np.array([r_a * math.sin(psi_a), r_a * math.cos(psi_a)])
    t = np.linspace(0.0, 1.0, count)[:, None]
    line = start + t * (end - start)
    radius = np.hypot(line[:, 0], line[:, 1])
    return radius, np.arctan2(line[:, 0], line[:, 1])


def _gear(generation: GenerationResult, role: Role) -> tuple[PairInput, GearGeneration, float]:
    if not isinstance(generation, GenerationResult):
        raise InputRangeError(
            f"a GenerationResult of compute_generation is required, got {type(generation).__name__}"
        )
    if role not in ("pinion", "wheel"):
        raise InputRangeError(f"role must be 'pinion' or 'wheel', got {role!r}")
    pair = generation.inputs
    gear = generation.gears.pinion if role == "pinion" else generation.gears.wheel
    beta = math.radians(pair.helix_angle_deg if role == "pinion" else -pair.helix_angle_deg)
    return pair, gear, beta


JOIN_TOLERANCE = 1.0e-10
"""Distance, relative to the radius of the point, below which the first point of a contour
element repeats the last point of the element before it. The junction of fillet and involute is
resolved to ``trochoid.GAP_TOLERANCE`` (1e-13 rad) along the circle and to half of ``EPS`` in the
radius (the base band of Eq. (12)); both lie orders below this. Only the first point of an element
is ever compared, and it is the last point of the element before it by construction; sampled
points are never dropped, however fine the sampling (the first involute step from the base circle
is 2e-8 of the radius at 3000 points per flank, 2e-10 at 30 000)."""


def _joined(blocks: list[Array]) -> tuple[Array, list[tuple[int, int]]]:
    """Concatenate the blocks of a polyline; a point that repeats the last point of the block
    before it (``JOIN_TOLERANCE``) is dropped, so that no segment has zero length. Returns the
    points and the [start, end) range of every block (the shared point belongs to the earlier
    block)."""
    pieces: list[Array] = []
    ranges: list[tuple[int, int]] = []
    count = 0
    last: Array | None = None  # the last point placed so far (empty blocks place none)
    for block in blocks:
        piece = block
        if (
            last is not None
            and len(piece)
            and float(np.hypot(*(piece[0] - last))) <= JOIN_TOLERANCE * float(np.hypot(*last))
        ):
            piece = piece[1:]
        if len(piece):
            last = piece[-1]
        pieces.append(piece)
        ranges.append((count, count + len(piece)))
        count += len(piece)
    return np.concatenate(pieces), ranges


def tooth_contour(
    generation: GenerationResult, role: Role, *, points: int = DEFAULT_POINTS
) -> ToothContour:
    """The transverse contour of one tooth of a generated gear.

    ``generation`` is ``compute_generation(pair)``; it carries the pair as validated. The contour
    recomputes the fillet of the tool tip rounding and the involutes from it. A chamfer given by
    h_K needs its residual thickness s_aK (``GearInput.residual_tip_thickness_mm``), else
    ``InputRangeError``: the shape of the chamfer is not known.
    """
    pair, gear, beta = _gear(generation, role)
    count = integer_input(points, "points per segment")
    if count < 8:
        raise InputRangeError(f"points per segment must be >= 8, got {points!r}")
    z = gear.number_of_teeth
    m_n = pair.normal_module_mm
    alpha_n = math.radians(pair.normal_pressure_angle_deg)
    alpha_t = iv.transverse_pressure_angle(alpha_n, beta)
    d = iv.reference_diameter(z, m_n, beta)
    d_b = iv.base_diameter(z, m_n, alpha_n, beta)
    x_E = gear.generating_profile_shift_coefficient
    psi_b = iv.base_tooth_thickness_half_angle(
        iv.tooth_thickness_half_angle(z, x_E, alpha_n), alpha_t
    )

    # fillet: from the root circle to the root form circle
    rounding = tr.tip_rounding(
        z, m_n, alpha_n, beta, gear.tool_addendum_mm, gear.tool_tip_radius_mm, x_E
    )
    if gear.undercut:
        _, theta_end, _ = tr.root_form_diameter_by_intersection(
            rounding, d_b, psi_b, undercut_expected=True
        )
    else:
        theta_end = rounding.flank_parameter_rad
    _, fillet_r, fillet_psi = tr.fillet_curve(rounding, theta_end, count)

    # involute: from the root form circle to the tip form circle
    d_Ff, d_Fa, d_a = gear.root_form_diameter_mm, gear.tip_form_diameter_mm, gear.tip_diameter_mm
    inv_r, inv_psi = involute_flank(d_b, psi_b, d_Ff, d_Fa, count)

    # tip flank: edge break involute of the tool, or a chamfer given by h_K and s_aK, or nothing
    quarter = max(divmod(count, 4)[0], 2)  # a quarter of the points for the tip elements
    if d_Fa < d_a * (1.0 - EPS):
        if gear.tool_edge_break_angle_deg is not None and gear.tool_root_form_height_mm is not None:
            alpha_tK = gn.edge_break_transverse_angle(
                math.radians(gear.tool_edge_break_angle_deg), beta
            )
            d_bK = gn.edge_break_base_diameter(d, alpha_tK)
            s_tK = gn.edge_break_transverse_tooth_thickness(
                m_n, beta, gear.tool_root_form_height_mm, alpha_t, alpha_tK, x_E
            )
            psi_bK = gn.edge_break_base_half_angle(s_tK, d, alpha_tK)
            tip_r, tip_psi = involute_flank(d_bK, psi_bK, d_Fa, d_a, quarter)
        elif gear.residual_tip_thickness_mm is not None:
            tip_r, tip_psi = chamfer_flank(
                0.5 * d_Fa, float(inv_psi[-1]), 0.5 * d_a, gear.residual_tip_thickness_mm, quarter
            )
        else:
            raise InputRangeError(
                f"{role}: the contour needs the shape of the tip chamfer: give the residual tip "
                "thickness s_aK (residual_tip_thickness_mm) with the radial height h_K"
            )
        psi_tip = float(tip_psi[-1])
    else:
        tip_r = tip_psi = np.empty(0)
        psi_tip = float(inv_psi[-1])

    # tip circle from the left tip point to the right tip point
    tip_angle = np.linspace(-psi_tip, psi_tip, quarter)
    tip = np.column_stack((0.5 * d_a * np.sin(tip_angle), 0.5 * d_a * np.cos(tip_angle)))

    left = [
        _polar(fillet_r, fillet_psi, -1.0),
        _polar(inv_r, inv_psi, -1.0),
        _polar(tip_r, tip_psi, -1.0),
    ]
    right = [
        _polar(tip_r, tip_psi, 1.0)[::-1],
        _polar(inv_r, inv_psi, 1.0)[::-1],
        _polar(fillet_r, fillet_psi, 1.0)[::-1],
    ]
    blocks = [*left, tip, *right]
    all_points, ranges = _joined(blocks)
    segments = [
        ContourSegment(name=name, start=start, end=end)
        for name, (start, end) in zip(SEGMENTS, ranges, strict=True)
    ]
    return ToothContour(
        number_of_teeth=z,
        generated_root_diameter_mm=gear.generated_root_diameter_mm,
        root_form_diameter_mm=d_Ff,
        tip_form_diameter_mm=d_Fa,
        tip_diameter_mm=d_a,
        undercut=gear.undercut,
        points=tuple((float(x), float(y)) for x, y in all_points),
        segments=tuple(segments),
    )


def gear_polygon(contour: ToothContour, *, arc_points: int = 8) -> Array:
    """The whole gear as a closed polygon: the tooth repeated z times, the root circle between
    the teeth (``arc_points`` points per root arc, at least 2). Counter-clockwise order.

    The fillets of a full-radius tool meet on the root circle: there is no arc then, and the
    point two teeth share is placed once. An arc whose points would lie closer than
    ``JOIN_TOLERANCE`` is drawn as one segment."""
    if not isinstance(contour, ToothContour):
        raise InputRangeError(f"a ToothContour is required, got {type(contour).__name__}")
    count = integer_input(arc_points, "points per root arc")
    if count < 2:
        raise InputRangeError(f"a root arc needs at least 2 points, got {arc_points!r}")
    tooth = contour.as_array()
    z = contour.number_of_teeth
    pitch = 2.0 * math.pi / z
    r_f = 0.5 * contour.generated_root_diameter_mm
    first, last = tooth[0], tooth[-1]
    # angles from +Y towards +X of the first and the last point of the tooth
    a_first, a_last = math.atan2(first[0], first[1]), math.atan2(last[0], last[1])
    if a_last <= a_first:
        raise GeometryInfeasibleError(
            "the contour of the tooth must run from the left flank to the right flank"
        )
    span = a_first + pitch - a_last  # angle of the root arc between two teeth
    if span < -JOIN_TOLERANCE:
        raise GeometryInfeasibleError(
            "the fillets of neighbouring teeth overlap: no root circle between them"
        )
    if span > JOIN_TOLERANCE * (count + 1):
        arc_angles = np.linspace(a_last, a_last + span, count + 2)[1:-1]
        arc = np.column_stack((r_f * np.sin(arc_angles), r_f * np.cos(arc_angles)))
        one = np.concatenate((tooth, arc))
    elif span > JOIN_TOLERANCE:
        one = tooth  # an arc too short for its points: one segment to the next tooth
    else:
        one = tooth[:-1]  # full-radius tool: the last point is the first of the next tooth
    pieces = []
    for k in range(z):
        # the tooth runs clockwise (left flank, tip, right flank); the next tooth follows
        # clockwise as well, towards +X, at k pitch angles from +Y
        phi = k * pitch
        c, s = math.cos(phi), math.sin(phi)
        rotated = np.column_stack((one[:, 0] * c + one[:, 1] * s, -one[:, 0] * s + one[:, 1] * c))
        pieces.append(rotated)
    return np.concatenate(pieces)[::-1]  # reversed: counter-clockwise


# --- comparison --------------------------------------------------------------------------------------


def _distance_to_polyline(reference: Array, polyline: Array) -> Array:
    """Shortest distance of every reference point from the polyline (point to segment)."""
    a, b = polyline[:-1], polyline[1:]
    ab = b - a
    length2 = np.einsum("ij,ij->i", ab, ab)
    ap = reference[:, None, :] - a[None, :, :]
    t = np.einsum("pij,ij->pi", ap, ab) / np.where(length2 > 0.0, length2, 1.0)
    t = np.clip(t, 0.0, 1.0)
    closest = a[None, :, :] + t[:, :, None] * ab[None, :, :]
    gaps = np.linalg.norm(reference[:, None, :] - closest, axis=2)
    return np.asarray(np.min(gaps, axis=1), dtype=np.float64)


def _reference(reference: Array) -> Array:
    if isinstance(reference, str | bytes) or not hasattr(reference, "__len__"):
        raise InputRangeError("the reference contour must be an (N, 2) array of x, y in mm")
    try:
        points = np.asarray(reference)
    except ValueError:  # rows of different length
        raise InputRangeError(
            "the reference contour must be an (N, 2) array of x, y in mm"
        ) from None
    if points.ndim != 2 or points.shape[1] != 2 or points.shape[0] < 1:
        raise InputRangeError("the reference contour must be an (N, 2) array of x, y in mm")
    if not (np.issubdtype(points.dtype, np.floating) or np.issubdtype(points.dtype, np.integer)):
        raise InputRangeError("the reference contour must hold real numbers")
    points = points.astype(np.float64)
    if not np.all(np.isfinite(points)):
        raise InputRangeError("the reference contour contains non-finite coordinates")
    return points


def distances(contour: ToothContour, reference: Array) -> Array:
    """Normal distance of every reference point (N, 2) in mm from the contour, in micrometres
    (point to polyline)."""
    if not isinstance(contour, ToothContour):
        raise InputRangeError(f"a ToothContour is required, got {type(contour).__name__}")
    return 1.0e3 * _distance_to_polyline(_reference(reference), contour.as_array())


REGION_TOLERANCE = 1.0e-6
"""Relative band around a landmark circle within which a reference point counts as on it (the
STplus export prints seven digits; the two tip-circle points of a gear without chamfer lie on
the tip form circle)."""


def compare(contour: ToothContour, reference: Array) -> ContourDiff:
    """Normal distances of the reference points (N, 2) in mm from the contour, in micrometres.

    A reference contour that runs from the left root to the right root like ``ToothContour``
    (the STplus export) is compared point by point; the regions follow from the radius of each
    reference point and the landmark diameters of ``contour`` (``REGION_TOLERANCE``).
    """
    points = _reference(reference)
    if not isinstance(contour, ToothContour):
        raise InputRangeError(f"a ToothContour is required, got {type(contour).__name__}")
    gaps = 1.0e3 * _distance_to_polyline(points, contour.as_array())
    radius = np.hypot(points[:, 0], points[:, 1])
    fillet = radius < 0.5 * contour.root_form_diameter_mm * (1.0 - REGION_TOLERANCE)
    tip = radius > 0.5 * contour.tip_form_diameter_mm * (1.0 + REGION_TOLERANCE)
    involute = ~fillet & ~tip
    regions: dict[Region, NDArray[np.bool_]] = {"fillet": fillet, "involute": involute, "tip": tip}

    def stats(mask: NDArray[np.bool_]) -> tuple[int, float, float]:
        chosen = gaps[mask]
        if chosen.size == 0:
            return 0, 0.0, 0.0
        return int(chosen.size), float(np.max(chosen)), float(np.sqrt(np.mean(chosen**2)))

    index = int(np.argmax(gaps))
    region_of_max: Region = next(name for name, mask in regions.items() if mask[index])
    f_n, f_max, f_rms = stats(fillet)
    i_n, i_max, i_rms = stats(involute)
    t_n, t_max, t_rms = stats(tip)
    return ContourDiff(
        reference_points=int(points.shape[0]),
        max_um=float(np.max(gaps)),
        rms_um=float(np.sqrt(np.mean(gaps**2))),
        region_of_max=region_of_max,
        fillet_points=f_n,
        fillet_max_um=f_max,
        fillet_rms_um=f_rms,
        involute_points=i_n,
        involute_max_um=i_max,
        involute_rms_um=i_rms,
        tip_points=t_n,
        tip_max_um=t_max,
        tip_rms_um=t_rms,
    )


def stplus_contour(case: str, gear: int) -> Array:
    """The transverse contour STplus exported for gear 1 or 2 of a packaged case, as (N, 2)."""
    from gearcore.data import load_stplus

    number = integer_input(gear, "gear number")
    if number not in (1, 2):
        raise InputRangeError(f"gear number must be 1 or 2, got {gear!r}")
    document = load_stplus(case, f"contour_wz{number}")
    return np.asarray(document["points"], dtype=np.float64)


__all__ = [
    "ContourDiff",
    "ContourSegment",
    "ToothContour",
    "chamfer_flank",
    "compare",
    "distances",
    "gear_polygon",
    "involute_flank",
    "stplus_contour",
    "tooth_contour",
]

_ = (pr, gn)  # keep the module references explicit for the traceability of the assembly
