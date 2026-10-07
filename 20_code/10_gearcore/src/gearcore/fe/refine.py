"""Conformal refinement of a sector mesh: integer factors for the directions of the mesh dialog
of the FVA Workbench (elements over the tooth height, at the tooth root, over the tooth
thickness) and a uniform factor for convergence studies.

A chord is the band of topologically parallel edges of a quad mesh: the two opposite edges of
a quad belong to the same chord, and so on through the neighbours. Splitting a chord into n
parts inserts n - 1 rows of nodes through the whole band, so every quad stays a quad, the mesh
stays conformal and the block structure of the template survives. Which chords a factor splits
is decided by the surface edges of the tooth blocks they contain (``seeds``):

    height     edges between the root form circle and the tip circle (involute and tip edge
               break); their chords run across the tooth, so the factor multiplies the number
               of elements over the tooth height on both flanks
    root       edges below the root form circle (fillet and root circle up to the centre line
               of the gap); their chords run into the fine layers along the surface, so the
               factor multiplies the number of elements along the rounding of every gap
    thickness  edges on the tip circle; their chords run down through the tooth, the layers
               below it and the rim to the bore, so the factor multiplies the number of
               elements over the tooth thickness
    uniform    every chord: the series h, h/2, h/3, ... of a convergence study

A chord that several factors select is split into the product of their parts. Every tooth is
treated alike, so the teeth stay congruent and mirror symmetric. New nodes on a surface edge
are moved onto the contour of their tooth (the nearest point of the sampled contour; nodes of
the shoulders onto the root circle), new nodes on the bore onto the bore circle; all other new
nodes lie at the bilinear position in their parent quad. Numbers of elements and nodes grow
with the factors; nothing is coarsened below the density of the template.
"""

import math
from collections import defaultdict
from dataclasses import dataclass, replace

import numpy as np
from numpy.typing import NDArray

from gearcore._safe import integer_input
from gearcore.errors import GeometryInfeasibleError, InputRangeError
from gearcore.fe.sector_mesh import (
    MIN_CORNER_SINE,
    ROOT_ARC_POINTS,
    SectorMesh,
    scaled_jacobians,
)

EQ_EXEMPT = ("chords", "refined", "effective_counts", "middle_tooth")
"""Mesh construction: no equation of a norm."""

Array = NDArray[np.float64]
IntArray = NDArray[np.int64]
Edge = tuple[int, int]

TIP_CIRCLE_TOLERANCE_MM = 1.0e-6
"""Distance below the tip radius within which a surface edge counts as lying on the tip circle."""


@dataclass(frozen=True)
class Refinement:
    """The factors of the mesh dialog, 1 = the density of the template."""

    height: int = 1
    root: int = 1
    thickness: int = 1
    uniform: int = 1

    def __post_init__(self) -> None:
        for name in ("height", "root", "thickness", "uniform"):
            value = integer_input(getattr(self, name), f"refinement factor {name}")
            if value < 1:
                raise InputRangeError(f"refinement factor {name} must be >= 1, got {value}")

    @property
    def is_identity(self) -> bool:
        return self.height == self.root == self.thickness == self.uniform == 1

    def label(self) -> str:
        """Short text for file names: ``h2_r3`` lists the factors above 1, ``base`` none."""
        parts = [
            f"{short}{value}"
            for short, value in (
                ("h", self.height),
                ("r", self.root),
                ("t", self.thickness),
                ("u", self.uniform),
            )
            if value > 1
        ]
        return "_".join(parts) if parts else "base"


def _edge(a: int, b: int) -> Edge:
    return (a, b) if a < b else (b, a)


def chords(quads: IntArray) -> list[set[Edge]]:
    """The chords of a quad mesh: the classes of edges under the relation 'opposite edges of a
    quad', each as a set of (smaller node, larger node) pairs."""
    parent: dict[Edge, Edge] = {}

    def find(e: Edge) -> Edge:
        while parent[e] != e:
            parent[e] = parent[parent[e]]
            e = parent[e]
        return e

    def union(a: Edge, b: Edge) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    for q in quads.tolist():
        e01, e12 = _edge(q[0], q[1]), _edge(q[1], q[2])
        e23, e30 = _edge(q[2], q[3]), _edge(q[3], q[0])
        for e in (e01, e12, e23, e30):
            parent.setdefault(e, e)
        union(e01, e23)
        union(e12, e30)
    groups: dict[Edge, set[Edge]] = defaultdict(set)
    for e in parent:
        groups[find(e)].add(e)
    return list(groups.values())


def _nearest_on_polyline(points: Array, polyline: Array) -> Array:
    """The nearest point of the (open) polyline to each of ``points``."""
    a = polyline[:-1]
    d = polyline[1:] - a
    length2 = np.maximum(np.einsum("ij,ij->i", d, d), 1.0e-300)
    result = np.empty_like(points)
    for k, p in enumerate(points):
        t = np.clip(((p - a) * d).sum(axis=1) / length2, 0.0, 1.0)
        foot = a + t[:, None] * d
        distance2 = ((foot - p) ** 2).sum(axis=1)
        result[k] = foot[int(np.argmin(distance2))]
    return result


def _with_root_arcs(outline: Array, section: SectorMesh) -> Array:
    """The tooth outline (tooth centre on +y, from the start of one fillet to the end of the
    other) extended by the arcs of the root circle to the centre lines of both gaps, so that
    every surface node of a tooth block has its place on it."""
    if outline.ndim != 2 or outline.shape[1] != 2 or len(outline) < 2:
        raise InputRangeError("the tooth outline must be an array of points (n, 2)")
    r_f = section.root_radius_mm
    half = 0.5 * section.pitch_angle_rad
    first = math.atan2(outline[0, 0], outline[0, 1])  # from +y towards +x
    last = math.atan2(outline[-1, 0], outline[-1, 1])
    if not -half <= first < last <= half:
        raise GeometryInfeasibleError("the tooth outline does not fit into one pitch")
    before = np.linspace(-half, first, ROOT_ARC_POINTS)[:-1]
    after = np.linspace(last, half, ROOT_ARC_POINTS)[1:]
    return np.concatenate(
        (
            np.column_stack((r_f * np.sin(before), r_f * np.cos(before))),
            outline,
            np.column_stack((r_f * np.sin(after), r_f * np.cos(after))),
        )
    )


def _turned(points: Array, angle: float) -> Array:
    c, s = math.cos(angle), math.sin(angle)
    return np.column_stack(
        (c * points[:, 0] - s * points[:, 1], s * points[:, 0] + c * points[:, 1])
    )


def _owners(quads: IntArray) -> dict[Edge, int]:
    """One quad per edge (the last one that holds it)."""
    owner: dict[Edge, int] = {}
    for q, quad in enumerate(quads.tolist()):
        for k in range(4):
            owner[_edge(quad[k], quad[(k + 1) % 4])] = q
    return owner


def _band(section: SectorMesh, a: int, b: int, radius: Array) -> str:
    """The band of a surface edge of a tooth block: ``thickness`` on the tip circle, ``root``
    below the root form circle, ``height`` between."""
    if min(radius[a], radius[b]) > section.tip_radius_mm - TIP_CIRCLE_TOLERANCE_MM:
        return "thickness"
    if 0.5 * (radius[a] + radius[b]) < section.root_form_radius_mm:
        return "root"
    return "height"


def _seeds(section: SectorMesh, refinement: Refinement) -> dict[Edge, int]:
    """The band factor of every surface edge of the tooth blocks that is above 1."""
    radius = np.hypot(section.points_mm[:, 0], section.points_mm[:, 1])
    owner = _owners(section.quads)
    path = section.surface_path
    factors: dict[Edge, int] = {}
    for a, b in zip(path[:-1].tolist(), path[1:].tolist(), strict=True):
        e = _edge(a, b)
        if section.quad_tooth[owner[e]] > 0:
            factor = getattr(refinement, _band(section, a, b, radius))
            if factor > 1:
                factors[e] = int(factor)
    return factors


def _edge_factors(quads: IntArray, seeds: dict[Edge, int], uniform: int) -> dict[Edge, int]:
    """The parts every edge is split into: the uniform factor times the largest band factor
    of the seeds in its chord."""
    result: dict[Edge, int] = {}
    for chord in chords(quads):
        band = max((seeds.get(e, 1) for e in chord), default=1)
        factor = uniform * band
        if factor > 1:
            for e in chord:
                result[e] = factor
    return result


def refined(section: SectorMesh, tooth_outline: Array, refinement: Refinement) -> SectorMesh:
    """The sector mesh with its chords split by ``refinement`` (see the module docstring).

    ``tooth_outline`` is the contour of one tooth with the tooth centre on +y (as
    ``contour.tooth_contour(...).as_array()`` gives it), onto which new surface nodes of the
    tooth blocks are moved; the outline is turned to every tooth of the sector.
    """
    if not isinstance(section, SectorMesh):
        raise InputRangeError(f"a SectorMesh is required, got {type(section).__name__}")
    if not isinstance(refinement, Refinement):
        raise InputRangeError(f"a Refinement is required, got {type(refinement).__name__}")
    outline = _with_root_arcs(np.asarray(tooth_outline, dtype=np.float64), section)
    if refinement.is_identity:
        return section
    factors = _edge_factors(section.quads, _seeds(section, refinement), refinement.uniform)
    if not factors:
        return replace(
            section,
            height_factor=section.height_factor * refinement.height,
            root_factor=section.root_factor * refinement.root,
            thickness_factor=section.thickness_factor * refinement.thickness,
            uniform_factor=section.uniform_factor * refinement.uniform,
        )

    points: list[tuple[float, float]] = [(float(x), float(y)) for x, y in section.points_mm]
    kinds = list(section.node_kind)
    radius = np.hypot(section.points_mm[:, 0], section.points_mm[:, 1])
    path = section.surface_path
    path_edges = {_edge(int(a), int(b)) for a, b in zip(path[:-1], path[1:], strict=True)}
    owner = _owners(section.quads)
    on_bore = {
        n
        for n in range(len(points))
        if kinds[n] in ("bore", "cut") and abs(radius[n] - section.bore_radius_mm) < 1.0e-6
    }
    edge_nodes: dict[tuple[int, int, int], int] = {}
    new_surface: list[int] = []  # (node, tooth) pairs are kept in two lists
    new_surface_tooth: list[int] = []

    def node_on_edge(a: int, b: int, k: int, n: int) -> int:
        """The node at fraction k/n from a to b, shared between the quads of the edge."""
        if k == 0:
            return a
        if k == n:
            return b
        key = (a, b, k) if a < b else (b, a, n - k)
        found = edge_nodes.get(key)
        if found is not None:
            return found
        t = k / n
        x = (1.0 - t) * points[a][0] + t * points[b][0]
        y = (1.0 - t) * points[a][1] + t * points[b][1]
        e = _edge(a, b)
        if kinds[a] == "cut" and kinds[b] == "cut":
            kind = "cut"
        elif e in path_edges:
            kind = "surface"
        elif a in on_bore and b in on_bore:
            kind = "bore"
            scale = section.bore_radius_mm / math.hypot(x, y)
            x, y = x * scale, y * scale
        else:
            kind = "interior"
        index = len(points)
        points.append((x, y))
        kinds.append(kind)
        if kind == "surface":
            new_surface.append(index)
            new_surface_tooth.append(int(section.quad_tooth[owner[e]]))
        edge_nodes[key] = index
        return index

    quads_out: list[tuple[int, int, int, int]] = []
    parents: list[int] = []
    for q, quad in enumerate(section.quads.tolist()):
        nu = factors.get(_edge(quad[0], quad[1]), 1)
        nv = factors.get(_edge(quad[1], quad[2]), 1)
        if nu == 1 and nv == 1:
            quads_out.append((quad[0], quad[1], quad[2], quad[3]))
            parents.append(q)
            continue
        grid = np.empty((nu + 1, nv + 1), dtype=np.int64)
        p0, p1, p2, p3 = (np.array(points[n]) for n in quad)
        for i in range(nu + 1):
            for j in range(nv + 1):
                if j == 0:
                    grid[i, j] = node_on_edge(quad[0], quad[1], i, nu)
                elif j == nv:
                    grid[i, j] = node_on_edge(quad[3], quad[2], i, nu)
                elif i == 0:
                    grid[i, j] = node_on_edge(quad[0], quad[3], j, nv)
                elif i == nu:
                    grid[i, j] = node_on_edge(quad[1], quad[2], j, nv)
                else:
                    u, v = i / nu, j / nv
                    p = (1 - u) * (1 - v) * p0 + u * (1 - v) * p1 + u * v * p2 + (1 - u) * v * p3
                    grid[i, j] = len(points)
                    points.append((float(p[0]), float(p[1])))
                    kinds.append("interior")
        for i in range(nu):
            for j in range(nv):
                corners = grid[i : i + 2, j : j + 2]
                quads_out.append(
                    (int(corners[0, 0]), int(corners[1, 0]), int(corners[1, 1]), int(corners[0, 1]))
                )
                parents.append(q)

    coordinates = np.array(points, dtype=np.float64)
    # new surface nodes onto the contour of their tooth, those of the shoulders onto the root circle
    if new_surface:
        nodes = np.array(new_surface, dtype=np.int64)
        teeth_of = np.array(new_surface_tooth, dtype=np.int64)
        for tooth in np.unique(teeth_of).tolist():
            chosen = nodes[teeth_of == tooth]
            if tooth == 0:
                scale = section.root_radius_mm / np.hypot(*coordinates[chosen].T)
                coordinates[chosen] *= scale[:, None]
            else:
                angle = (tooth - 0.5 * (section.teeth + 1)) * section.pitch_angle_rad
                coordinates[chosen] = _nearest_on_polyline(
                    coordinates[chosen], _turned(outline, angle)
                )

    # the surface path with the new nodes in order
    new_path: list[int] = [int(path[0])]
    for a, b in zip(path[:-1].tolist(), path[1:].tolist(), strict=True):
        n = factors.get(_edge(a, b), 1)
        for k in range(1, n):
            new_path.append(node_on_edge(a, b, k, n))
        new_path.append(b)

    quads_array = np.array(quads_out, dtype=np.int64)
    parent_array = np.array(parents, dtype=np.int64)
    worst = float(scaled_jacobians(coordinates, quads_array).min())
    if worst < MIN_CORNER_SINE:
        raise GeometryInfeasibleError(
            f"refinement {refinement}: the mesh has a degenerate or inverted element (smallest "
            f"corner sine {worst:.3e}, limit {MIN_CORNER_SINE})"
        )
    mesh = replace(
        section,
        points_mm=coordinates,
        quads=quads_array,
        node_kind=tuple(kinds),
        quad_tooth=section.quad_tooth[parent_array],
        quad_side=section.quad_side[parent_array],
        quad_zone=section.quad_zone[parent_array],
        quad_head=section.quad_head[parent_array],
        surface_path=np.array(new_path, dtype=np.int64),
        height_factor=section.height_factor * refinement.height,
        root_factor=section.root_factor * refinement.root,
        thickness_factor=section.thickness_factor * refinement.thickness,
        uniform_factor=section.uniform_factor * refinement.uniform,
    )
    for array in (
        mesh.points_mm,
        mesh.quads,
        mesh.quad_tooth,
        mesh.quad_side,
        mesh.quad_zone,
        mesh.quad_head,
        mesh.surface_path,
    ):
        array.setflags(write=False)
    return mesh


@dataclass(frozen=True)
class EffectiveCounts:
    """Numbers of elements of the mesh in the words of the mesh dialog, counted on one tooth
    (the middle one) and one gap: over the tooth height (one flank from the root form point to
    the tip corner), at the tooth root (one gap from root form point to root form point), over
    the tooth thickness (the tip circle), plus the layers of the first element row along the
    fillet (normal to the surface) and the number of teeth and shoulder pitches."""

    teeth: int
    shoulder_pitches: int
    over_tooth_height: int
    at_tooth_root: int
    over_tooth_thickness: int
    rim_rings: int
    nodes_per_layer: int
    elements_per_layer: int


def effective_counts(section: SectorMesh) -> EffectiveCounts:
    """Count the surface edges of the middle tooth and of the gap on its left (counter-
    clockwise) side per band."""
    if not isinstance(section, SectorMesh):
        raise InputRangeError(f"a SectorMesh is required, got {type(section).__name__}")
    points = section.points_mm
    radius = np.hypot(points[:, 0], points[:, 1])
    owner = _owners(section.quads)
    middle = middle_tooth(section.teeth)
    path = section.surface_path
    height = thickness = 0
    root_left = root_right = 0  # left half of the middle tooth, right half of the next tooth
    for a, b in zip(path[:-1].tolist(), path[1:].tolist(), strict=True):
        q = owner[_edge(a, b)]
        tooth, side = int(section.quad_tooth[q]), int(section.quad_side[q])
        if tooth == 0:
            continue
        band = _band(section, a, b, radius)
        if tooth == middle and band == "thickness":
            thickness += 1
        elif tooth == middle and side == 1 and band == "height":
            height += 1
        elif tooth == middle and side == 1 and band == "root":
            root_left += 1
        elif tooth == middle + 1 and side == -1 and band == "root":
            root_right += 1
    if middle == section.teeth:
        root_right = root_left  # the gap next to the last tooth is bounded by a shoulder
    return EffectiveCounts(
        teeth=section.teeth,
        shoulder_pitches=2,
        over_tooth_height=height,
        at_tooth_root=root_left + root_right,
        over_tooth_thickness=thickness,
        rim_rings=section.rim_rings * section.uniform_factor,
        nodes_per_layer=len(points),
        elements_per_layer=len(section.quads),
    )


def middle_tooth(teeth: int) -> int:
    """The tooth of the main evaluation: the middle one, the lower of the two for an even
    number (teeth counted from 1)."""
    count = integer_input(teeth, "number of teeth of the sector")
    if count < 1:
        raise InputRangeError(f"the sector needs at least one tooth, got {teeth!r}")
    return (count + 1) >> 1  # (teeth + 1) halved and rounded down, in exact integer arithmetic
