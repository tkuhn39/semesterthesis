"""Mesh of a gear sector in the transverse section: teeth between two toothless shoulder pitches.

The topology comes from the packaged template (``sector_template``): the sector is the shoulder
block, the tooth block once per tooth, and the mirrored shoulder block, joined along the gap
centre lines. The geometry comes from the generated tooth contour (``contour.tooth_contour``):

1. Every node of the template is placed by its angle, scaled with the pitch of the gear, and by
   its radius, mapped piecewise linearly between the circles bore, fan ring, root and tip. The
   depths below the root circle scale with the module.
2. The surface nodes of the tooth block are moved onto the contour, piece by piece: the root
   circle with the fillet, the involute, the tip edge break and the tip circle each take the
   nodes the template has on that piece, at the same relative arc lengths. The root form
   point, the tip form point and the tip corner are thereby nodes. A gear without tip edge
   break takes the nodes of edge break and tip circle on its tip circle.
3. The interior of the tooth zone follows: its displacement is the harmonic continuation of
   the displacement of the surface, zero at and below the fan ring, periodic from gap centre to
   gap centre. The thin element layers along the surface thereby keep their thickness.
4. In the tip region the interior nodes are set to the mean of their neighbours. The template
   has a row of cells a few micrometres thin there, below the cells of the tip.
5. The tooth block is made mirror symmetric about its tooth centre line; every tooth of the
   sector is a rotation of it, so the teeth are congruent by construction.

Frame: millimetres, the gear axis at the origin, the bisector of the sector on +y. The teeth are
numbered counter-clockwise, tooth 1 at the clockwise end; the left half of a tooth is the half
counter-clockwise of its centre line (the ``left_*`` segments of ``contour.ToothContour``).

Only spur gears (``NotSupportedError`` otherwise). The first version has the element density of
the reference; factors for a finer root or flank are an extension.
"""

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from gearcore import contour as ct
from gearcore._safe import integer_input, positive_input
from gearcore.contour import Role
from gearcore.errors import GeometryInfeasibleError, InputRangeError, NotSupportedError
from gearcore.fe.sector_template import Block, SectorTemplate, load_sector_template
from gearcore.models.results import GenerationResult

EQ_EXEMPT = ("sector_mesh", "scaled_jacobians")
"""Mesh construction: no equation of a norm."""

Array = NDArray[np.float64]
IntArray = NDArray[np.int64]
BoolArray = NDArray[np.bool_]

LINE_TOLERANCE_MM = 1.0e-3
"""Distance within which a node of the template lies on a grid circle of the rim (the circles
are 0.44 mm apart, the reference holds them to 1e-6 mm)."""
MIN_SURFACE_SPACING_MM = 1.0e-4
"""Smallest distance two neighbouring surface nodes may have after they were moved onto the
contour; closer nodes mean the contour differs too much from the template for this mapping."""
MIN_CORNER_SINE = 0.1
"""Smallest sine of an element corner a mesh may have (the reference has 0.245, in the cells at
the tooth tip). Below it the contour differs too much from the template for this mapping; the
tip of a gear without edge break is the usual place."""
TIP_REGION_DEPTH = 0.45
"""Depth below the tip circle, in modules, of the region whose interior nodes are smoothed."""
CONTOUR_POINTS = 2000
ROOT_ARC_POINTS = 500
"""Points of the root circle between a fillet and the centre line of the gap."""
"""Points per element of the tooth contour the surface nodes are moved onto."""


@dataclass(frozen=True)
class SectorMesh:
    """A gear sector in the transverse section.

    ``quads`` are counter-clockwise. ``node_kind`` is ``interior``, ``surface``, ``bore`` or
    ``cut`` (the radial cut planes at both ends). ``quad_tooth`` is the number of the tooth
    block a quad belongs to (1 at the clockwise end, 0 for the shoulders), ``quad_side`` +1 for
    the left half of the tooth, -1 for the right half, 0 for the shoulders, and ``quad_zone`` 1
    above the fan ring (the finely meshed tooth zone) and 0 below (the rim). ``quad_head`` is 1
    for the regular grid of a tooth above the mesh line that joins its two root form points
    (the head: flanks and tip), 0 for the fine layers along the fillets and all else. ``surface_path``
    lists the surface nodes counter-clockwise from one cut plane to the other. The centre line
    of tooth j lies at the angle pi/2 + (j - (teeth + 1) / 2) ``pitch_angle_rad`` from +x.
    """

    points_mm: Array
    quads: IntArray
    node_kind: tuple[str, ...]
    quad_tooth: IntArray
    quad_side: IntArray
    quad_zone: IntArray
    quad_head: IntArray
    surface_path: IntArray
    number_of_teeth: int
    teeth: int
    rim_rings: int
    bore_radius_mm: float
    fan_ring_radius_mm: float
    root_radius_mm: float
    root_form_radius_mm: float
    tip_form_radius_mm: float
    tip_radius_mm: float
    pitch_angle_rad: float


@dataclass(frozen=True)
class _Lists:
    """Node lists of a trimmed template, from the bore outwards."""

    tooth_left: IntArray
    tooth_right: IntArray
    tooth_partner: IntArray
    shoulder_interface: IntArray
    shoulder_cut: IntArray
    tooth_grid: IntArray


def scaled_jacobians(points_mm: Array, quads: IntArray) -> Array:
    """Per quad the smallest sine of its four corner angles (1 for a rectangle, 0 or less for a
    degenerate or inverted quad), for counter-clockwise quads."""
    corners = points_mm[quads]
    worst = np.full(len(quads), np.inf)
    for k in range(4):
        here = corners[:, k]
        ahead = corners[:, (k + 1) % 4] - here
        back = corners[:, (k - 1) % 4] - here
        cross = ahead[:, 0] * back[:, 1] - ahead[:, 1] * back[:, 0]
        length = np.hypot(ahead[:, 0], ahead[:, 1]) * np.hypot(back[:, 0], back[:, 1])
        worst = np.minimum(worst, cross / np.where(length > 0.0, length, 1.0))
    return worst


# --- template with fewer rim rings ------------------------------------------------------------------


def _without_inner_rings(
    block: Block, bore_line_mm: float, lists: tuple[tuple[int, ...], ...]
) -> tuple[Block, tuple[IntArray, ...], IntArray, BoolArray]:
    """The block without the quads inside ``bore_line_mm``; the nodes on that circle become the
    bore. Returns the block, the node lists in the new numbering, the new index of every old
    node (-1 for a removed node) and which of the old quads are kept."""
    centre = block.radius_mm[block.quads].mean(axis=1)
    kept_quads = centre > bore_line_mm
    quads = block.quads[kept_quads]
    used = np.unique(quads)
    index = np.full(len(block.phi), -1, dtype=np.int64)
    index[used] = np.arange(len(used), dtype=np.int64)
    kind = []
    for node in used:
        old = block.kind[int(node)]
        on_bore_line = abs(float(block.radius_mm[node]) - bore_line_mm) < LINE_TOLERANCE_MM
        kind.append("bore" if on_bore_line and old in ("interior", "bore") else old)
    trimmed = Block(
        phi=block.phi[used],
        radius_mm=block.radius_mm[used],
        quads=index[quads],
        kind=tuple(kind),
        surface_order=tuple(int(index[n]) for n in block.surface_order),
    )
    new_lists = tuple(
        np.array([index[n] for n in nodes if index[n] >= 0], dtype=np.int64) for nodes in lists
    )
    return trimmed, new_lists, index, kept_quads


def _trimmed(template: SectorTemplate, rim_rings: int) -> tuple[Block, Block, _Lists, float]:
    bore_line = template.rim_line_radii_mm[template.rim_rings - rim_rings]
    tooth, (left, right), index, kept_quads = _without_inner_rings(
        template.tooth, bore_line, (template.tooth_left_interface, template.tooth_right_interface)
    )
    kept = np.flatnonzero(index >= 0)
    partner = index[np.array(template.tooth_mirror_partner, dtype=np.int64)[kept]]
    grid = np.array(template.tooth_grid_quads, dtype=np.int64)[kept_quads]
    shoulder, (interface, cut), _, _ = _without_inner_rings(
        template.shoulder, bore_line, (template.shoulder_interface, template.shoulder_cut)
    )
    if not len(left) == len(right) == len(interface) == len(cut) or int(partner.min()) < 0:
        raise GeometryInfeasibleError("sector template: the blocks do not fit after trimming")
    return tooth, shoulder, _Lists(left, right, partner, interface, cut, grid), bore_line


# --- geometry -----------------------------------------------------------------------------------------


def _half_contour(contour: ct.ToothContour, pitch: float) -> list[Array | None]:
    """The left half of the tooth contour with the tooth centre on +y, in four pieces from the
    centre line of the gap to the tooth centre line: root circle with fillet (to the root form
    point), involute (to the tip form point), tip edge break (to the tip corner; None for a
    gear without one) and tip circle."""
    tooth = contour.as_array()
    r_f = 0.5 * contour.generated_root_diameter_mm
    first = math.atan2(tooth[0, 0], tooth[0, 1])  # angle from +y towards +x: negative here
    half = 0.5 * pitch
    if first < -half - ct.JOIN_TOLERANCE:
        raise GeometryInfeasibleError(
            "the fillets of neighbouring teeth overlap: no root circle between them"
        )
    fillet = contour.segment("left_fillet")
    if first > -half + ct.JOIN_TOLERANCE:
        angles = np.linspace(-half, first, ROOT_ARC_POINTS)[:-1]
        fillet = np.concatenate(
            (np.column_stack((r_f * np.sin(angles), r_f * np.cos(angles))), fillet)
        )
    involute = np.concatenate((fillet[-1:], contour.segment("left_involute")))
    edge_break = contour.segment("left_tip_flank")
    corner = edge_break[-1:] if len(edge_break) else involute[-1:]
    tip = contour.segment("tip")
    tip_circle = np.concatenate(
        (corner, tip[tip[:, 0] < 0.0], np.array([[0.0, 0.5 * contour.tip_diameter_mm]]))
    )
    return [
        fillet,
        involute,
        np.concatenate((involute[-1:], edge_break)) if len(edge_break) else None,
        tip_circle,
    ]


def _at_fractions(polyline: Array, fractions: Array) -> Array:
    """The points of the polyline at the given fractions of its arc length."""
    arc = np.concatenate(([0.0], np.cumsum(np.hypot(*(polyline[1:] - polyline[:-1]).T))))
    at = fractions * arc[-1]
    return np.column_stack((np.interp(at, arc, polyline[:, 0]), np.interp(at, arc, polyline[:, 1])))


def _on_half_contour(
    placed: Array, half_contour: list[Array | None], features: tuple[int, ...]
) -> Array:
    """The surface nodes of one half of the template, given from the centre line of the gap to
    the tooth centre line, on the contour: every piece of the contour takes the nodes of its
    piece of the template at the same relative arc lengths. Where the gear lacks a piece (no tip
    edge break), the nodes of that piece go onto the piece before it, so that the node at its
    end, the tip corner of the template, is the corner of the gear."""
    pieces: list[tuple[int, int, Array]] = []
    for start, end, curve in zip(features[:-1], features[1:], half_contour, strict=True):
        if curve is not None:
            pieces.append((start, end, curve))
        elif pieces:
            first, _, before = pieces[-1]
            pieces[-1] = (first, end, before)
        else:
            raise GeometryInfeasibleError("the contour has no fillet for the surface nodes")
    result = placed.copy()
    for start, end, curve in pieces:
        nodes = placed[start : end + 1]
        arc = np.concatenate(([0.0], np.cumsum(np.hypot(*(nodes[1:] - nodes[:-1]).T))))
        result[start : end + 1] = _at_fractions(curve, arc / arc[-1])
    return result


def _edges(quads: IntArray) -> IntArray:
    """The edges of the quads, each once, as pairs of nodes."""
    pairs = np.concatenate([quads[:, [k, (k + 1) % 4]] for k in range(4)])
    pairs = np.sort(pairs, axis=1)
    return np.unique(pairs, axis=0)


def _harmonic(
    points: Array,
    quads: IntArray,
    fixed: BoolArray,
    values: Array,
    same_as: IntArray,
    *,
    by_length: bool = True,
) -> Array:
    """Continue ``values`` given on the ``fixed`` nodes harmonically to the other nodes.

    With ``by_length`` the mesh graph is weighted with the inverse edge lengths, so the
    continuation is close to linear in the distance; without, every edge counts the same, so a
    free node takes the mean of its neighbours. ``same_as`` names for every node the node whose
    value it shares (itself, or its partner across a periodic interface). ``values`` has one
    column per component; the columns of the free nodes are ignored.
    """
    count = len(points)
    edges = _edges(quads)
    length = np.hypot(*(points[edges[:, 0]] - points[edges[:, 1]]).T)
    # an edge on a periodic interface exists on both of its sides: count it once
    shared = np.sort(same_as[edges], axis=1)
    _, first = np.unique(shared, axis=0, return_index=True)
    a, b = shared[first, 0], shared[first, 1]
    weight = 1.0 / length[first] if by_length else np.ones(len(first))
    laplace = np.zeros((count, count))
    np.add.at(laplace, (a, a), weight)
    np.add.at(laplace, (b, b), weight)
    np.add.at(laplace, (a, b), -weight)
    np.add.at(laplace, (b, a), -weight)
    own = same_as == np.arange(count)
    free = np.flatnonzero(own & ~fixed)
    known = np.flatnonzero(own & fixed)
    result = np.array(values, dtype=np.float64)
    if len(free):
        rhs = -laplace[np.ix_(free, known)] @ result[known]
        result[free] = np.linalg.solve(laplace[np.ix_(free, free)], rhs)
    return np.asarray(result[same_as], dtype=np.float64)


def _tooth_block_polar(
    tooth: Block,
    lists: _Lists,
    radius_0: Array,
    half_contour: list[Array | None],
    features: tuple[int, ...],
    pitch: float,
    fan_ref_mm: float,
    tip_region_ref_mm: float,
) -> tuple[Array, Array]:
    """Radius and angle from the tooth centre line (rad, counter-clockwise) of the nodes of the
    tooth block on the gear. Interior nodes of the template outside ``tip_region_ref_mm`` are
    smoothed."""
    angle_0 = tooth.phi * pitch
    kind = np.array(tooth.kind)
    surface = kind == "surface"
    # tooth centre on +y: counter-clockwise of it lies -x
    placed = np.column_stack((-radius_0 * np.sin(angle_0), radius_0 * np.cos(angle_0)))
    order = np.array(tooth.surface_order, dtype=np.int64)
    on_contour = placed.copy()
    # the left half of the surface from the centre line of its gap to the tooth centre line;
    # the right half is its mirror image
    left_half = order[::-1][: features[-1] + 1]
    on_contour[left_half] = _on_half_contour(placed[left_half], half_contour, features)
    on_contour[lists.tooth_partner[left_half]] = on_contour[left_half] * np.array([-1.0, 1.0])
    target = on_contour[surface]
    spacing = np.hypot(*(on_contour[order[1:]] - on_contour[order[:-1]]).T)
    if float(spacing.min()) < MIN_SURFACE_SPACING_MM:
        raise GeometryInfeasibleError(
            f"surface nodes of the template fall together on the contour (smallest spacing "
            f"{float(spacing.min()):.3e} mm): the contour differs too much from the template"
        )
    moved = np.zeros((len(radius_0), 2))
    target_radius = np.hypot(target[:, 0], target[:, 1])
    target_angle = np.arctan2(-target[:, 0], target[:, 1])
    moved[surface, 0] = target_radius - radius_0[surface]
    moved[surface, 1] = radius_0[surface] * (target_angle - angle_0[surface])
    fixed = surface | (tooth.radius_mm <= fan_ref_mm + LINE_TOLERANCE_MM)
    same_as = np.arange(len(radius_0), dtype=np.int64)
    same_as[lists.tooth_right] = lists.tooth_left
    moved = _harmonic(placed, tooth.quads, fixed, moved, same_as)
    radius = radius_0 + moved[:, 0]
    angle = angle_0 + moved[:, 1] / radius_0
    # tip region: every interior node at the mean of its neighbours. The template has a row of
    # cells a few micrometres thin below the tip cells there; this spreads the rows evenly.
    in_tip_region = (kind == "interior") & (tooth.radius_mm > tip_region_ref_mm)
    if in_tip_region.any():
        here = np.column_stack((-radius * np.sin(angle), radius * np.cos(angle)))
        here = _harmonic(
            here, tooth.quads, ~in_tip_region, here, np.arange(len(radius)), by_length=False
        )
        radius = np.hypot(here[:, 0], here[:, 1])
        angle = np.arctan2(-here[:, 0], here[:, 1])
    # mirror symmetry about the tooth centre line; the lines of symmetry exactly
    partner = lists.tooth_partner
    radius = 0.5 * (radius + radius[partner])
    angle = 0.5 * (angle - angle[partner])
    angle[partner == np.arange(len(angle))] = 0.0
    angle[lists.tooth_left] = -0.5 * pitch
    angle[lists.tooth_right] = 0.5 * pitch
    return radius, angle


def _shoulder_block_radius(
    shoulder: Block,
    lists: _Lists,
    radius_0: Array,
    interface_radius: Array,
    pitch: float,
    fan_ref_mm: float,
    root_mm: float,
) -> Array:
    """Radius of the nodes of the shoulder block on the gear: the interface as the tooth block
    has it, the surface on the root circle, the tooth zone between following harmonically."""
    kind = np.array(shoulder.kind)
    surface = kind == "surface"
    angle = shoulder.phi * pitch
    placed = np.column_stack((-radius_0 * np.sin(angle), radius_0 * np.cos(angle)))
    moved = np.zeros((len(radius_0), 1))
    moved[surface, 0] = root_mm - radius_0[surface]
    interface = lists.shoulder_interface
    moved[interface, 0] = interface_radius - radius_0[interface]
    fixed = surface | (kind == "cut") | (shoulder.radius_mm <= fan_ref_mm + LINE_TOLERANCE_MM)
    fixed[interface] = True
    same_as = np.arange(len(radius_0), dtype=np.int64)
    moved = _harmonic(placed, shoulder.quads, fixed, moved, same_as)
    return radius_0 + moved[:, 0]


# --- the sector ------------------------------------------------------------------------------------------


def sector_mesh(
    generation: GenerationResult,
    role: Role,
    *,
    teeth: int,
    rim_rings: int,
    bore_radius_mm: float | None = None,
    template: SectorTemplate | None = None,
) -> SectorMesh:
    """The transverse mesh of ``teeth`` teeth of the gear ``role`` between two shoulder pitches.

    ``rim_rings`` is the number of element rings of the rim below the fan ring (the template
    has 25); fewer rings leave a larger bore. Without ``bore_radius_mm`` the rings keep the
    thickness of the template, scaled with the module.
    """
    if not isinstance(generation, GenerationResult):
        raise InputRangeError(
            f"a GenerationResult of compute_generation is required, got {type(generation).__name__}"
        )
    pair = generation.inputs
    if pair.helix_angle_deg != 0.0:
        raise NotSupportedError(
            f"helix angle {pair.helix_angle_deg!r} deg: only spur gears are meshed"
        )
    tpl = template if template is not None else load_sector_template()
    count = integer_input(teeth, "number of teeth of the sector")
    rings = integer_input(rim_rings, "number of rim rings")
    contour = ct.tooth_contour(generation, role, points=CONTOUR_POINTS)
    z = contour.number_of_teeth
    if not 1 <= count <= z - 2:
        raise InputRangeError(
            f"a sector of a gear with {z} teeth holds 1 to {z - 2} teeth, got {teeth!r}"
        )
    if not 1 <= rings <= tpl.rim_rings:
        raise InputRangeError(f"rim rings must lie in 1 to {tpl.rim_rings}, got {rim_rings!r}")
    pitch = 2.0 * math.pi / z
    tooth, shoulder, lists, bore_line = _trimmed(tpl, rings)

    # circles of the gear the template is mapped onto
    depth_scale = pair.normal_module_mm / tpl.normal_module_mm
    root = 0.5 * contour.generated_root_diameter_mm
    tip = 0.5 * contour.tip_diameter_mm
    fan = root - (tpl.root_radius_mm - tpl.fan_ring_radius_mm) * depth_scale
    if bore_radius_mm is None:
        bore = fan - (tpl.fan_ring_radius_mm - bore_line) * depth_scale
    else:
        bore = positive_input(bore_radius_mm, "bore radius")
    if not 0.0 < bore < fan < root < tip:
        raise GeometryInfeasibleError(
            f"the circles of the sector must grow outwards: bore {bore!r}, fan ring {fan!r}, "
            f"root {root!r}, tip {tip!r} mm"
        )
    knots_ref = np.array([bore_line, tpl.fan_ring_radius_mm, tpl.root_radius_mm, tpl.tip_radius_mm])
    knots = np.array([bore, fan, root, tip])

    tooth_radius_0 = np.interp(tooth.radius_mm, knots_ref, knots)
    tooth_radius, tooth_angle = _tooth_block_polar(
        tooth,
        lists,
        tooth_radius_0,
        _half_contour(contour, pitch),
        tpl.tooth_surface_features,
        pitch,
        tpl.fan_ring_radius_mm,
        tpl.tip_radius_mm - TIP_REGION_DEPTH * tpl.normal_module_mm,
    )
    shoulder_radius = _shoulder_block_radius(
        shoulder,
        lists,
        np.interp(shoulder.radius_mm, knots_ref, knots),
        tooth_radius[lists.tooth_left],
        pitch,
        tpl.fan_ring_radius_mm,
        root,
    )
    for radius, kind in ((tooth_radius, tooth.kind), (shoulder_radius, shoulder.kind)):
        radius[np.array(kind) == "bore"] = bore
    shoulder_radius[lists.shoulder_cut[0]] = bore  # the corner of cut plane and bore

    # assembly, counter-clockwise: shoulder, the tooth blocks, mirrored shoulder
    first_centre = -0.5 * (count - 1)
    radii: list[Array] = []
    angles: list[Array] = []  # from the bisector of the sector, counter-clockwise
    kinds: list[str] = []
    quads: list[IntArray] = []
    quad_tooth: list[IntArray] = []
    quad_side: list[IntArray] = []
    quad_zone: list[IntArray] = []
    quad_head: list[IntArray] = []
    surface: list[int] = []
    total = 0

    def add(
        block: Block,
        radius: Array,
        angle: Array,
        joined: IntArray,
        joined_to: IntArray,
        block_quads: IntArray,
        number: int,
        local_angle: Array,
        path: tuple[int, ...],
        head: IntArray,
    ) -> IntArray:
        """Append a block; its nodes ``joined`` are the existing nodes ``joined_to``. Returns
        the numbers of its nodes in the sector."""
        nonlocal total
        numbers = np.full(len(radius), -1, dtype=np.int64)
        numbers[joined] = joined_to
        new = np.flatnonzero(numbers < 0)
        numbers[new] = total + np.arange(len(new), dtype=np.int64)
        total += len(new)
        radii.append(radius[new])
        angles.append(angle[new])
        kinds.extend(block.kind[int(n)] for n in new)
        quads.append(numbers[block_quads])
        centre_radius = block.radius_mm[block_quads].mean(axis=1)
        centre_angle = local_angle[block_quads].mean(axis=1)
        quad_tooth.append(np.full(len(block_quads), number, dtype=np.int64))
        side = np.where(centre_angle > 0.0, 1, -1) if number else np.zeros(len(block_quads))
        quad_side.append(np.asarray(side, dtype=np.int64))
        quad_zone.append((centre_radius > tpl.fan_ring_radius_mm).astype(np.int64))
        quad_head.append(head)
        for node in path:
            if not surface or surface[-1] != int(numbers[node]):
                surface.append(int(numbers[node]))
        return numbers

    empty = np.empty(0, dtype=np.int64)
    no_head = np.zeros(len(shoulder.quads), dtype=np.int64)
    interface_angle = (first_centre - 0.5) * pitch
    numbers = add(
        shoulder,
        shoulder_radius,
        interface_angle + shoulder.phi * pitch,
        empty,
        empty,
        shoulder.quads,
        0,
        shoulder.phi,
        shoulder.surface_order,
        no_head,
    )
    open_interface = numbers[lists.shoulder_interface]
    for j in range(count):
        numbers = add(
            tooth,
            tooth_radius,
            (first_centre + j) * pitch + tooth_angle,
            lists.tooth_left,
            open_interface,
            tooth.quads,
            j + 1,
            tooth_angle,
            tooth.surface_order,
            lists.tooth_grid,
        )
        open_interface = numbers[lists.tooth_right]
    add(
        shoulder,
        shoulder_radius,
        (first_centre + count - 0.5) * pitch - shoulder.phi * pitch,
        lists.shoulder_interface,
        open_interface,
        shoulder.quads[:, ::-1],
        0,
        shoulder.phi,
        shoulder.surface_order[::-1],
        no_head,
    )

    radius_all = np.concatenate(radii)
    angle_all = 0.5 * math.pi + np.concatenate(angles)
    points = np.column_stack((radius_all * np.cos(angle_all), radius_all * np.sin(angle_all)))
    all_quads = np.concatenate(quads)
    worst = float(scaled_jacobians(points, all_quads).min())
    if worst < MIN_CORNER_SINE:
        raise GeometryInfeasibleError(
            f"the mesh has a degenerate or inverted element (smallest corner sine {worst:.3e}, "
            f"limit {MIN_CORNER_SINE}): the contour differs too much from the template for this "
            "mapping"
        )
    mesh = SectorMesh(
        points_mm=points,
        quads=all_quads,
        node_kind=tuple(kinds),
        quad_tooth=np.concatenate(quad_tooth),
        quad_side=np.concatenate(quad_side),
        quad_zone=np.concatenate(quad_zone),
        quad_head=np.concatenate(quad_head),
        surface_path=np.array(surface, dtype=np.int64),
        number_of_teeth=z,
        teeth=count,
        rim_rings=rings,
        bore_radius_mm=bore,
        fan_ring_radius_mm=fan,
        root_radius_mm=root,
        root_form_radius_mm=0.5 * contour.root_form_diameter_mm,
        tip_form_radius_mm=0.5 * contour.tip_form_diameter_mm,
        tip_radius_mm=tip,
        pitch_angle_rad=pitch,
    )
    for array in (
        mesh.points_mm,
        mesh.quads,
        mesh.quad_tooth,
        mesh.quad_side,
        mesh.quad_zone,
        mesh.quad_head,
    ):
        array.setflags(write=False)
    mesh.surface_path.setflags(write=False)
    return mesh
