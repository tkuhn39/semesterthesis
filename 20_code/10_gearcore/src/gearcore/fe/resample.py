"""Resampling of the sector template with given numbers of elements.

The template (``sector_template``) is a structured quad mesh: a few logical rectangles
(patches) meet at the fan node of each gap and at the feature points of the contour. Every
patch side belongs to a class of parallel sides that share one number of elements; the
classes are named after the words of the FVA mesh dialog and listed in ``MeshCounts``. For
other numbers than the template has, every patch is rebuilt as a grid of the new size: the
nodes of a side are placed along the side of the template at the same relative arc lengths
as the template's own nodes (interpolated, so that thin layers stay thin in proportion), and
the interior nodes are interpolated in the index space of the template patch. With the
numbers of the template the result is the template itself.

Classes (template values of the kst-E wheel in brackets):

    height         rows of the head between the root form point and the tip form point (18)
    chamfer        rows of the tip edge break (2)
    root           columns along the rounding of one half gap, root form point to gap centre (40)
    root_layers    layers normal to the root surface; they continue as the outer columns of the
                   head and as the layers of the toothless shoulder above the fan ring (3)
    centre         columns of the head on each side of the tooth centre line below the chamfer,
                   which continue through the dome under the tooth and as the rim columns of
                   half a pitch (2)
    rim_rings      element rings of the rim between the bore and the fan ring (12 when 12 of the
                   template's 25 are kept)
    shoulder       columns of the toothless shoulder pitch (4)

so that elements over the tooth height = height + chamfer, at the tooth root (one gap) =
2 root, over the tooth thickness = 2 (root_layers + centre).

The cap of the tooth tip (``MeshCounts.cap_layers`` > 0, for a tooth whose tip corner is an
arc, ``contour.ProfileModification.tip_edge_radius_mm``): the head of the template is a
logical rectangle whose corner sits on the tip corner, so a tangential arc there gives the
corner quad an angle near 180 degrees (a sliver). With the cap the rows above the tangency
row (the row through the tip form point) are rebuilt as three blocks, see ``TipCap``: the
layers along the surface run from the flank around the arc and along the tip circle to the
tooth centre line, the corner of the block structure moves into the tooth (one node of
valence 3 under the arc end) and every surface node keeps two quads. Without the option the
block is the template's.
"""

import math
from collections import defaultdict
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from gearcore._safe import integer_input
from gearcore.errors import GeometryInfeasibleError, InputRangeError
from gearcore.fe.sector_template import Block

EQ_EXEMPT = ("patches", "resample_block", "resample_template")
"""Mesh construction: no equation of a norm."""

Array = NDArray[np.float64]
IntArray = NDArray[np.int64]
Edge = tuple[int, int]
CLASSES = ("height", "chamfer", "root", "root_layers", "centre", "rim_rings", "shoulder")
LINE_TOLERANCE = 1.0e-9
"""Tolerance in pitches / mm within which a node lies on a line of the template."""


@dataclass(frozen=True)
class MeshCounts:
    """Numbers of elements of the sector mesh in the words of the FVA dialog (see the module
    docstring for what each one controls). ``over_tooth_thickness`` and ``at_tooth_root`` are
    even; ``root_layers`` is below half the thickness."""

    over_tooth_height: int = 18
    at_tip_edge_break: int = 2
    at_tooth_root: int = 80
    over_tooth_thickness: int = 10
    root_layers: int = 3
    rim_rings: int = 12
    shoulder_columns: int = 4
    cap_layers: int = 0
    """Layers of the cap of the tooth tip along the arc of the tip corner and the tip circle
    (0: no cap, the head is the rectangle of the template). The cap takes the first
    ``cap_layers`` columns of the tangency row as its depth, so it needs at least one column
    more over the half thickness."""

    def __post_init__(self) -> None:
        cap = integer_input(self.cap_layers, "cap_layers")
        if cap < 0 or cap >= (
            integer_input(self.over_tooth_thickness, "over_tooth_thickness") >> 1
        ):
            raise InputRangeError(
                f"cap_layers must lie in 0 to over_tooth_thickness / 2 - 1, got {self.cap_layers}"
            )
        for name in (
            "over_tooth_height",
            "at_tip_edge_break",
            "at_tooth_root",
            "over_tooth_thickness",
            "root_layers",
            "rim_rings",
            "shoulder_columns",
        ):
            value = integer_input(getattr(self, name), name)
            if value < 1:
                raise InputRangeError(f"{name} must be >= 1, got {value}")
        if self.at_tooth_root % 2:
            raise InputRangeError(
                f"at_tooth_root counts both halves of a gap and must be even, got {self.at_tooth_root}"
            )
        if self.over_tooth_thickness % 2:
            raise InputRangeError(
                f"over_tooth_thickness must be even, got {self.over_tooth_thickness}"
            )
        if self.centre_columns < 1:
            raise InputRangeError(
                f"root_layers ({self.root_layers}) must leave at least one column on each side of "
                f"the tooth centre: over_tooth_thickness / 2 - root_layers >= 1"
            )

    @property
    def centre_columns(self) -> int:
        return (self.over_tooth_thickness >> 1) - self.root_layers

    @property
    def per_class(self) -> dict[str, int]:
        return {
            "height": self.over_tooth_height,
            "chamfer": self.at_tip_edge_break,
            "root": self.at_tooth_root >> 1,
            "root_layers": self.root_layers,
            "centre": self.centre_columns,
            "rim_rings": self.rim_rings,
            "shoulder": self.shoulder_columns,
        }

    def label(self) -> str:
        return (
            f"h{self.over_tooth_height}_c{self.at_tip_edge_break}_r{self.at_tooth_root}_"
            f"t{self.over_tooth_thickness}_l{self.root_layers}_k{self.rim_rings}_s{self.shoulder_columns}"
            + (f"_cap{self.cap_layers}" if self.cap_layers else "")
        )


@dataclass(frozen=True)
class Patch:
    """One logical rectangle of a block: node ids ``grid[i, j]`` with i along the first
    direction (``i_class`` elements) and j along the second (``j_class`` elements); the cell
    (i, j), (i+1, j), (i+1, j+1), (i, j+1) is counter-clockwise."""

    grid: IntArray
    i_class: str
    j_class: str


# --- block structure ------------------------------------------------------------------------


def _edge(a: int, b: int) -> Edge:
    return (a, b) if a < b else (b, a)


class _Topology:
    """Incidence of a quad mesh: quads of every edge and node, boundary, cyclic neighbours."""

    def __init__(self, quads: IntArray) -> None:
        self.quads = quads
        self.quads_of_edge: dict[Edge, list[int]] = defaultdict(list)
        self.quads_of_node: dict[int, list[int]] = defaultdict(list)
        for q, quad in enumerate(quads.tolist()):
            for k in range(4):
                self.quads_of_edge[_edge(quad[k], quad[(k + 1) % 4])].append(q)
                self.quads_of_node[quad[k]].append(q)
        self.boundary_edges = {e for e, qs in self.quads_of_edge.items() if len(qs) == 1}
        self.boundary_nodes = {a for e in self.boundary_edges for a in e}

    def valence(self, node: int) -> int:
        return len(self.quads_of_node[node])

    def neighbours(self, node: int, quads: set[int] | None = None) -> list[int]:
        """Neighbours of a node through the given quads (all quads by default), in cyclic
        order for an interior node, along the fan for a boundary node."""
        pairs = []
        for q in self.quads_of_node[node]:
            if quads is not None and q not in quads:
                continue
            quad = self.quads[q].tolist()
            i = quad.index(node)
            pairs.append((quad[(i - 1) % 4], quad[(i + 1) % 4]))
        order = [pairs[0][0], pairs[0][1]]
        used = {0}
        while len(used) < len(pairs):
            found = False
            for k, (previous, following) in enumerate(pairs):
                if k in used:
                    continue
                if previous == order[-1]:
                    order.append(following)
                    used.add(k)
                    found = True
                    break
                if following == order[0]:
                    order.insert(0, previous)
                    used.add(k)
                    found = True
                    break
            if not found:
                raise GeometryInfeasibleError("the template is not a manifold quad mesh")
        if len(order) > 1 and order[0] == order[-1]:
            order.pop()
        return order

    def straight_on(self, previous: int, node: int, quads: set[int] | None = None) -> int | None:
        """The neighbour of ``node`` opposite to ``previous``: the one that shares no quad with
        ``previous``; None at a corner or an irregular node."""
        candidates = [
            n
            for n in self.neighbours(node, quads)
            if n != previous
            and not any(
                (quads is None or q in quads) and previous in self.quads[q]
                for q in self.quads_of_node[n]
            )
        ]
        return candidates[0] if len(candidates) == 1 else None


def _trace(topology: _Topology, start: int, first: int) -> list[Edge]:
    """Edges of the straight walk from ``start`` through ``first`` to the boundary or an
    irregular node."""
    edges = [_edge(start, first)]
    previous, current = start, first
    while current not in topology.boundary_nodes and topology.valence(current) == 4:
        following = topology.straight_on(previous, current)
        if following is None:
            break
        edges.append(_edge(current, following))
        previous, current = current, following
    return edges


def patches(block: Block, forced: tuple[int, ...]) -> list[IntArray]:
    """The logical rectangles of a block as grids of node ids. Separatrices run from every
    irregular node (interior valence other than 4, boundary valence other than 2) and from
    the ``forced`` boundary nodes (feature points) into the mesh."""
    quads = block.quads
    topology = _Topology(quads)
    singular = [
        v
        for v in range(len(block.phi))
        if (v in topology.boundary_nodes and topology.valence(v) != 2)
        or (v not in topology.boundary_nodes and topology.valence(v) != 4)
    ]
    separatrix = set(topology.boundary_edges)
    for v in list(singular) + list(forced):
        for w in topology.neighbours(v):
            if _edge(v, w) not in topology.boundary_edges:
                separatrix |= set(_trace(topology, v, w))
    parent = list(range(len(quads)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for e, qs in topology.quads_of_edge.items():
        if e not in separatrix and len(qs) == 2:
            a, b = find(qs[0]), find(qs[1])
            if a != b:
                parent[max(a, b)] = min(a, b)
    members: dict[int, list[int]] = defaultdict(list)
    for q in range(len(quads)):
        members[find(q)].append(q)
    grids = []
    for qs in members.values():
        grids.append(_grid(topology, set(qs)))
    return grids


def _grid(topology: _Topology, quads: set[int]) -> IntArray:
    """The node grid of one logical rectangle given by its quads."""
    count: dict[int, int] = defaultdict(int)
    for q in quads:
        for v in topology.quads[q].tolist():
            count[v] += 1
    corners = [v for v, c in count.items() if c == 1]
    if len(corners) != 4:
        raise GeometryInfeasibleError(
            f"a patch of the template has {len(corners)} corners instead of 4"
        )
    c0 = min(corners)
    q0 = next(q for q in topology.quads_of_node[c0] if q in quads)
    quad = topology.quads[q0].tolist()
    k = quad.index(c0)
    a, b = quad[(k + 1) % 4], quad[(k - 1) % 4]

    def walk(start: int, first: int) -> list[int]:
        chain = [start, first]
        while True:
            following = topology.straight_on(chain[-2], chain[-1], quads)
            if following is None:
                return chain
            chain.append(following)

    row = walk(c0, a)
    column = walk(c0, b)
    ni, nj = len(row) - 1, len(column) - 1
    grid = np.full((ni + 1, nj + 1), -1, dtype=np.int64)
    grid[:, 0] = row
    grid[0, :] = column
    for i in range(1, ni + 1):
        node = int(grid[i, 0])
        along = set(row[max(i - 1, 0) : i + 2]) - {node}  # the side neighbours of the node
        inward = [n for n in topology.neighbours(node, quads) if n not in along]
        if len(inward) != 1:
            raise GeometryInfeasibleError("a patch of the template is not a logical rectangle")
        chain = walk(node, inward[0])
        if len(chain) != nj + 1:
            raise GeometryInfeasibleError("a patch of the template is not a logical rectangle")
        grid[i, :] = chain
    if ni * nj != len(quads) or len(set(grid.ravel().tolist())) != (ni + 1) * (nj + 1):
        raise GeometryInfeasibleError("a patch of the template is not a logical rectangle")
    return grid


# --- classes of the patch sides -----------------------------------------------------------------


@dataclass(frozen=True)
class _Seeds:
    """Which nodes name a class: a side whose nodes are all in a seed set (and has at least
    one edge) belongs to that class."""

    sets: dict[str, set[int]]


def _classify(grids: list[IntArray], seeds: _Seeds) -> list[Patch]:
    """Union the parallel sides of all patches and name every class by its seeds."""
    parent: dict[tuple[int, str], tuple[int, str]] = {}

    def find(x: tuple[int, str]) -> tuple[int, str]:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: tuple[int, str], b: tuple[int, str]) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    by_side: dict[frozenset[int], tuple[int, str]] = {}
    for p, grid in enumerate(grids):
        parent[(p, "i")] = (p, "i")
        parent[(p, "j")] = (p, "j")
        # the sides along i (rows j = 0 and j = nj) carry the i count, the sides along j the j count
        for chain, direction in (
            (grid[:, 0], "i"),
            (grid[:, -1], "i"),
            (grid[0, :], "j"),
            (grid[-1, :], "j"),
        ):
            key = frozenset(chain.tolist())
            other = by_side.get(key)
            if other is not None:
                union(other, (p, direction))
            else:
                by_side[key] = (p, direction)
    names: dict[tuple[int, str], str] = {}
    for key, member in by_side.items():
        root = find(member)
        for name, nodes in seeds.sets.items():
            if len(key) >= 2 and key <= nodes:
                if names.get(root, name) != name:
                    raise GeometryInfeasibleError(
                        f"the sides of the template mix the classes {names[root]} and {name}"
                    )
                names[root] = name
    result = []
    for p, grid in enumerate(grids):
        i_name, j_name = names.get(find((p, "i"))), names.get(find((p, "j")))
        if i_name is None or j_name is None:
            raise GeometryInfeasibleError("a side class of the template has no name")
        result.append(Patch(grid=grid, i_class=i_name, j_class=j_name))
    return result


# --- resampling -----------------------------------------------------------------------------------


def _cartesian(block: Block, pitch: float) -> Array:
    """Nodes of a block in the plane of the reference gear (tooth centre on +y)."""
    angle = block.phi * pitch
    return np.column_stack((-block.radius_mm * np.sin(angle), block.radius_mm * np.cos(angle)))


def _fractions(points: Array) -> Array:
    """Cumulative arc length fractions 0 ... 1 of a chain of points."""
    steps = np.hypot(*(points[1:] - points[:-1]).T)
    arc = np.concatenate(([0.0], np.cumsum(steps)))
    return (
        np.asarray(arc / arc[-1], dtype=np.float64)
        if arc[-1] > 0.0
        else np.linspace(0.0, 1.0, len(points))
    )


def _index_map(points: Array, count: int) -> Array:
    """Template index coordinates (0 ... n) of ``count + 1`` new nodes along a chain of n + 1
    template nodes, at the same relative arc lengths as the template's distribution: the
    new node m takes the arc fraction of the template at index n m / count, interpolated."""
    n = len(points) - 1
    fractions = _fractions(points)
    target = np.interp(np.linspace(0.0, n, count + 1), np.arange(n + 1), fractions)
    return np.asarray(np.interp(target, fractions, np.arange(n + 1)), dtype=np.float64)


def _at_index(points: Array, u: Array) -> Array:
    """Points of a chain at fractional template indices (linear between the nodes)."""
    n = len(points) - 1
    return np.column_stack(
        (np.interp(u, np.arange(n + 1), points[:, 0]), np.interp(u, np.arange(n + 1), points[:, 1]))
    )


def _bilinear(grid_points: Array, u: float, v: float) -> Array:
    """Point of a grid of points (ni + 1, nj + 1, 2) at fractional indices."""
    ni, nj = grid_points.shape[0] - 1, grid_points.shape[1] - 1
    i0 = min(int(u), ni - 1) if u >= 0.0 else 0
    j0 = min(int(v), nj - 1) if v >= 0.0 else 0
    s, t = u - i0, v - j0
    p00, p10 = grid_points[i0, j0], grid_points[i0 + 1, j0]
    p01, p11 = grid_points[i0, j0 + 1], grid_points[i0 + 1, j0 + 1]
    return np.asarray((1 - s) * (1 - t) * p00 + s * (1 - t) * p10 + (1 - s) * t * p01 + s * t * p11)


class _Resampler:
    """Builds the new nodes of a block patch by patch, sharing corners and side nodes."""

    def __init__(self, block: Block, pitch: float, counts: dict[str, int]) -> None:
        self.block = block
        self.points = _cartesian(block, pitch)
        self.counts = counts
        self.new_points: list[tuple[float, float]] = []
        self.new_kind: list[str] = []
        self.corner_of: dict[int, int] = {}
        self.side_nodes: dict[tuple[int, int], list[int]] = {}
        self.quads: list[tuple[int, int, int, int]] = []
        self.quad_patch: list[int] = []
        self.on_surface: set[Edge] = set()

    def _add(self, point: Array, kind: str) -> int:
        self.new_points.append((float(point[0]), float(point[1])))
        self.new_kind.append(kind)
        return len(self.new_points) - 1

    def corner(self, node: int) -> int:
        if node not in self.corner_of:
            self.corner_of[node] = self._add(self.points[node], self.block.kind[node])
        return self.corner_of[node]

    def side(self, chain: IntArray, count: int) -> list[int]:
        """New nodes along a side of the template (chain of node ids), shared between the
        patches that have it; the direction of the chain is respected."""
        a, b = int(chain[0]), int(chain[-1])
        if (b, a) in self.side_nodes:
            return self.side_nodes[(b, a)][::-1]
        if (a, b) in self.side_nodes:
            return self.side_nodes[(a, b)]
        points = self.points[chain]
        kinds = {self.block.kind[int(n)] for n in chain.tolist()[1:-1]} or {
            self.block.kind[a] if self.block.kind[a] == self.block.kind[b] else "interior"
        }
        kind = kinds.pop() if len(kinds) == 1 else "interior"
        positions = _at_index(points, _index_map(points, count))
        nodes = [self.corner(a)]
        nodes.extend(self._add(positions[m], kind) for m in range(1, count))
        nodes.append(self.corner(b))
        self.side_nodes[(a, b)] = nodes
        return nodes

    def patch(self, number: int, patch: Patch) -> None:
        grid = patch.grid
        ni_new, nj_new = self.counts[patch.i_class], self.counts[patch.j_class]
        grid_points = self.points[grid]  # (ni + 1, nj + 1, 2)
        new = np.full((ni_new + 1, nj_new + 1), -1, dtype=np.int64)
        new[:, 0] = self.side(grid[:, 0], ni_new)
        new[:, -1] = self.side(grid[:, -1], ni_new)
        new[0, :] = self.side(grid[0, :], nj_new)
        new[-1, :] = self.side(grid[-1, :], nj_new)
        u0, u1 = _index_map(grid_points[:, 0], ni_new), _index_map(grid_points[:, -1], ni_new)
        v0, v1 = _index_map(grid_points[0, :], nj_new), _index_map(grid_points[-1, :], nj_new)
        for m in range(1, ni_new):
            for k in range(1, nj_new):
                s, t = m / ni_new, k / nj_new
                u = (1 - t) * u0[m] + t * u1[m]
                v = (1 - s) * v0[k] + s * v1[k]
                new[m, k] = self._add(_bilinear(grid_points, float(u), float(v)), "interior")
        for m in range(ni_new):
            for k in range(nj_new):
                cell = new[m : m + 2, k : k + 2]
                self.quads.append(
                    (int(cell[0, 0]), int(cell[1, 0]), int(cell[1, 1]), int(cell[0, 1]))
                )
                self.quad_patch.append(number)


@dataclass(frozen=True)
class ResampledBlock:
    """A block with new counts, with what the template lists need: node ids on the named
    lines (by phi) and the quads of the patches by class pair."""

    block: Block
    quad_classes: tuple[tuple[str, str], ...]


def _surface_order(block_quads: IntArray, kinds: list[str], start: int) -> list[int]:
    """The surface nodes in the order of the boundary walk from ``start``."""
    topology = _Topology(block_quads)
    surface_edges = [
        e
        for e in topology.boundary_edges
        if kinds[e[0]] in ("surface", "cut")
        and kinds[e[1]] in ("surface", "cut")
        and not (kinds[e[0]] == "cut" and kinds[e[1]] == "cut")
    ]
    neighbours: dict[int, list[int]] = defaultdict(list)
    for a, b in surface_edges:
        neighbours[a].append(b)
        neighbours[b].append(a)
    order = [start]
    previous = -1
    while True:
        following = [n for n in neighbours[order[-1]] if n != previous]
        if not following:
            break
        previous = order[-1]
        order.append(following[0])
        if len(order) > len(kinds):
            raise GeometryInfeasibleError("the surface of the block does not end")
    return order


def resample_block(
    block: Block,
    pitch: float,
    forced: tuple[int, ...],
    seeds: _Seeds,
    counts: dict[str, int],
    surface_start: int,
) -> tuple[Block, list[Patch], tuple[tuple[str, str], ...], dict[int, int]]:
    """A block with the counts of ``counts`` per class. Returns the block, the patches of the
    template, the class pair of every new quad, and the new ids of the template's corners."""
    classified = _classify(patches(block, forced), seeds)
    resampler = _Resampler(block, pitch, counts)
    for number, patch in enumerate(classified):
        resampler.patch(number, patch)
    points = np.array(resampler.new_points, dtype=np.float64)
    radius = np.hypot(points[:, 0], points[:, 1])
    phi = np.arctan2(-points[:, 0], points[:, 1]) / pitch
    quads = np.array(resampler.quads, dtype=np.int64)
    kinds = list(resampler.new_kind)
    start = resampler.corner_of[surface_start]
    order = _surface_order(quads, kinds, start)
    new_block = Block(
        phi=np.asarray(phi, dtype=np.float64),
        radius_mm=np.asarray(radius, dtype=np.float64),
        quads=quads,
        kind=tuple(kinds),
        surface_order=tuple(order),
    )
    classes = tuple((classified[p].i_class, classified[p].j_class) for p in resampler.quad_patch)
    return new_block, classified, classes, dict(resampler.corner_of)


# --- the cap of the tooth tip ----------------------------------------------------------------------


@dataclass(frozen=True)
class TipCap:
    """The cap of the tooth tip of the clockwise half of the tooth block (0-based node ids).

    Above the tangency row (the row of the head grid through the tip form point) the head is
    not the rectangle of the template but three blocks. ``corner_grid[a, b]`` lies under the
    arc of the tip corner: a = 0 on the arc from the tip form point (b = 0) to the arc end
    (b = chamfer), a = cap_layers on the diagonal; its side b = 0 is the tangency row from
    the tip form point inwards. ``land_grid[a, b]`` lies under the tip circle: a = 0 on the
    circle from the arc end (b = 0) to the tooth centre (b = land), a = cap_layers on the
    inner row. ``core_grid[c, b]`` lies between the tangency row (c = 0, from the foot of the
    diagonal, b = 0, to the centre line, b = land) and the inner row (c = chamfer). Shared
    sides: the diagonal ``corner_grid[-1, :]`` = ``core_grid[:, 0]``, the ray under the arc
    end ``corner_grid[:, -1]`` = ``land_grid[:, 0]``, the inner row ``land_grid[-1, :]`` =
    ``core_grid[-1, :]``. The inner corner (arc end ray meets the inner row) has valence 3;
    every other node of the cap is regular. The counter-clockwise half is the mirror image
    through the partner list of the block.
    """

    corner_grid: IntArray
    land_grid: IntArray
    core_grid: IntArray

    @property
    def cap_layers(self) -> int:
        return int(self.corner_grid.shape[0]) - 1

    @property
    def tangency_row(self) -> IntArray:
        """The nodes of the tangency row from the tip form point to the tooth centre line."""
        return np.concatenate((self.corner_grid[:, 0], self.core_grid[0, 1:]))

    @property
    def nodes(self) -> IntArray:
        return np.unique(
            np.concatenate(
                (self.corner_grid.ravel(), self.land_grid.ravel(), self.core_grid.ravel())
            )
        )


def _coons(bottom: Array, top: Array, left: Array, right: Array, s: Array, t: Array) -> Array:
    """Points of a logical rectangle from its four sides (transfinite interpolation):
    ``bottom`` = P[0, :], ``top`` = P[-1, :], ``left`` = P[:, 0], ``right`` = P[:, -1]; ``s``
    and ``t`` are the blending fractions 0 ... 1 along the first and the second index."""
    s_col, t_row = s[:, None, None], t[None, :, None]
    points = (
        (1.0 - s_col) * bottom[None, :, :]
        + s_col * top[None, :, :]
        + (1.0 - t_row) * left[:, None, :]
        + t_row * right[:, None, :]
        - (
            (1.0 - s_col) * (1.0 - t_row) * bottom[0]
            + (1.0 - s_col) * t_row * bottom[-1]
            + s_col * (1.0 - t_row) * top[0]
            + s_col * t_row * top[-1]
        )
    )
    return np.asarray(points, dtype=np.float64)


def cap_inner_points(
    arc_end: Array, tip_centre: Array, tangency_centre: Array, chamfer: int, layers: int
) -> tuple[Array, Array]:
    """The inner corner and the inner centre of the cap: the centre line between the tangency
    row and the tip is divided evenly into the chamfer rows of the core and the layers of the
    land block, and the inner corner lies radially under the arc end at the depth of those
    layers."""
    inner_centre = tangency_centre + (chamfer / (chamfer + layers)) * (tip_centre - tangency_centre)
    inner_centre = np.array([0.0, float(inner_centre[1])])
    depth = float(np.hypot(*(tip_centre - inner_centre)))
    inner_corner = arc_end * (1.0 - depth / float(np.hypot(*arc_end)))
    return inner_corner, inner_centre


def cap_points(
    row: Array, arc: Array, land: Array, inner_corner: Array, inner_centre: Array, layers: int
) -> tuple[Array, Array, Array]:
    """The points of the three cap blocks of one half (``TipCap``) from the given lines: the
    tangency row from the tip form point to the tooth centre line, the arc from the tip form
    point to its end, the tip circle from the arc end to the tooth centre, the inner corner
    and the inner centre. The layers of the corner and land blocks take the spacing of the
    first ``layers`` columns of the tangency row; the rest is transfinite interpolation."""
    chamfer, count = len(arc) - 1, len(land) - 1
    steps = np.hypot(*(row[1 : layers + 1] - row[:layers]).T)
    depth = np.concatenate(([0.0], np.cumsum(steps)))
    fractions = depth / depth[-1]
    even_chamfer = np.linspace(0.0, 1.0, chamfer + 1)
    even_count = np.linspace(0.0, 1.0, count + 1)
    foot = row[layers]
    diagonal = foot + even_chamfer[:, None] * (inner_corner - foot)
    ray = arc[-1] + fractions[:, None] * (inner_corner - arc[-1])
    corner = _coons(arc, diagonal, row[: layers + 1], ray, fractions, even_chamfer)
    inner_row = inner_corner + even_count[:, None] * (inner_centre - inner_corner)
    centre_side = land[-1] + fractions[:, None] * (inner_centre - land[-1])
    land_block = _coons(land, inner_row, ray, centre_side, fractions, even_count)
    core_centre = row[-1] + even_chamfer[:, None] * (inner_centre - row[-1])
    core = _coons(row[layers:], inner_row, diagonal, core_centre, even_chamfer, even_count)
    return corner, land_block, core


def _head_rows(block: Block, features: tuple[int, ...], columns: int) -> IntArray:
    """The head grid of the clockwise half as rows of node ids: row i runs from the flank node
    i above the root form point inwards to the tooth centre line (``columns`` steps); the last
    row is the tip circle from the tip corner to the tooth centre."""
    order = list(block.surface_order)
    _, form, _, corner, centre = features
    topology = _Topology(block.quads)
    on_surface = set(order)
    rows = []
    for i in range(corner - form):
        start = order[form + i]
        inward = [n for n in topology.neighbours(start) if n not in on_surface]
        if len(inward) != 1:
            raise GeometryInfeasibleError("the head of the tooth block is not a regular grid")
        chain = [start, inward[0]]
        while len(chain) <= columns:
            following = topology.straight_on(chain[-2], chain[-1])
            if following is None:
                raise GeometryInfeasibleError("the head of the tooth block is not a regular grid")
            chain.append(following)
        rows.append(chain)
    rows.append(order[corner : centre + 1])
    grid = np.array(rows, dtype=np.int64)
    if np.abs(block.phi[grid[:, -1]]).max() > 1.0e-7:
        raise GeometryInfeasibleError(
            "the head rows of the tooth block do not end on its centre line"
        )
    return grid


def _with_tip_cap(
    block: Block, features: tuple[int, ...], grid_flags: IntArray, counts: MeshCounts, pitch: float
) -> tuple[Block, IntArray, tuple[int, ...], TipCap]:
    """The tooth block with the cap of the tooth tip (see ``TipCap``): the quads above the
    tangency row are replaced on both halves, mirror symmetric. Returns the block, the head
    flags of its quads, the surface features and the cap of the clockwise half."""
    gap, form, tip_form, corner, centre = features
    layers = counts.cap_layers
    columns = counts.over_tooth_thickness >> 1
    chamfer = corner - tip_form
    count = columns - layers
    tangency = tip_form - form
    rows = _head_rows(block, features, columns)
    partner = _partners(block)
    mirrored_rows = partner[rows]
    points = _cartesian(block, pitch)

    above = set(rows[tangency:].ravel().tolist()) | set(mirrored_rows[tangency:].ravel().tolist())
    keep_quad = np.array(
        [not all(n in above for n in quad) for quad in block.quads.tolist()], dtype=np.bool_
    )
    doomed = (
        set(rows[tangency + 1 :, 1:columns].ravel().tolist())
        | set(mirrored_rows[tangency + 1 :, 1:columns].ravel().tolist())
        | set(rows[tangency + 1 : tangency + chamfer, columns].tolist())
    )

    new_xy: list[tuple[float, float]] = []
    new_kind: list[str] = []
    mirror_of: dict[int, int] = {int(n): int(partner[n]) for n in rows.ravel().tolist()}
    base = len(block.phi)

    def create(xy: Array, kind: str) -> int:
        node = base + len(new_xy)
        new_xy.append((float(xy[0]), float(xy[1])))
        new_kind.append(kind)
        if abs(float(xy[0])) == 0.0:
            mirror_of[node] = node
        else:
            new_xy.append((-float(xy[0]), float(xy[1])))
            new_kind.append(kind)
            mirror_of[node] = node + 1
            mirror_of[node + 1] = node
        return node

    row = rows[tangency]
    arc = rows[tangency : tangency + chamfer + 1, 0]
    old_land = points[rows[-1]]
    land_xy = _at_index(old_land, _index_map(old_land, count))
    land_xy[0], land_xy[-1] = old_land[0], old_land[-1]
    inner_corner, inner_centre = cap_inner_points(
        points[arc[-1]], old_land[-1], points[row[-1]], chamfer, layers
    )
    corner_xy, land_block_xy, core_xy = cap_points(
        points[row], points[arc], land_xy, inner_corner, inner_centre, layers
    )
    corner_ids = np.full((layers + 1, chamfer + 1), -1, dtype=np.int64)
    land_ids = np.full((layers + 1, count + 1), -1, dtype=np.int64)
    core_ids = np.full((chamfer + 1, count + 1), -1, dtype=np.int64)
    corner_ids[0, :] = arc
    corner_ids[:, 0] = row[: layers + 1]
    core_ids[0, :] = row[layers:]
    land_ids[0, 0], land_ids[0, count] = arc[-1], rows[-1, -1]
    for b in range(1, count):
        land_ids[0, b] = create(land_xy[b], "surface")
    for a in range(1, layers + 1):
        corner_ids[a, chamfer] = create(corner_xy[a, chamfer], "interior")
    land_ids[:, 0] = corner_ids[:, chamfer]
    for c in range(1, chamfer):
        corner_ids[layers, c] = create(corner_xy[layers, c], "interior")
    core_ids[:, 0] = corner_ids[layers, :]
    for a in range(1, layers):
        for b in range(1, chamfer):
            corner_ids[a, b] = create(corner_xy[a, b], "interior")
    for a in range(1, layers + 1):
        land_ids[a, count] = create(np.array([0.0, float(land_block_xy[a, count, 1])]), "interior")
    for b in range(1, count):
        land_ids[layers, b] = create(land_block_xy[layers, b], "interior")
    core_ids[chamfer, :] = land_ids[layers, :]
    for a in range(1, layers):
        for b in range(1, count):
            land_ids[a, b] = create(land_block_xy[a, b], "interior")
    for c in range(1, chamfer):
        core_ids[c, count] = create(np.array([0.0, float(core_xy[c, count, 1])]), "interior")
    for c in range(1, chamfer):
        for b in range(1, count):
            core_ids[c, b] = create(core_xy[c, b], "interior")
    if (corner_ids < 0).any() or (land_ids < 0).any() or (core_ids < 0).any():
        raise GeometryInfeasibleError("the cap of the tooth tip is incomplete")

    all_xy = np.concatenate((points, np.array(new_xy, dtype=np.float64).reshape(-1, 2)))
    mirror = np.vectorize(lambda n: mirror_of[int(n)], otypes=[np.int64])
    new_quads: list[tuple[int, int, int, int]] = []
    for grid in (corner_ids, land_ids, core_ids):
        for ids in (grid, mirror(grid)):
            rows_of_ids: list[list[int]] = ids.tolist()
            cells = [
                (row[j], below[j], below[j + 1], row[j + 1])
                for row, below in zip(rows_of_ids[:-1], rows_of_ids[1:], strict=True)
                for j in range(len(row) - 1)
            ]
            first = all_xy[list(cells[0])]
            area = 0.0
            for k in range(4):
                area += first[k, 0] * first[(k + 1) % 4, 1] - first[(k + 1) % 4, 0] * first[k, 1]
            new_quads.extend(cells if area > 0.0 else [cell[::-1] for cell in cells])

    kept = np.array([n for n in range(len(all_xy)) if n not in doomed], dtype=np.int64)
    index = np.full(len(all_xy), -1, dtype=np.int64)
    index[kept] = np.arange(len(kept), dtype=np.int64)
    quads = np.concatenate(
        (index[block.quads[keep_quad]], index[np.array(new_quads, dtype=np.int64)])
    )
    if int(quads.min()) < 0:
        raise GeometryInfeasibleError("a quad of the cap names a removed node")
    kinds = list(block.kind) + new_kind
    xy = all_xy[kept]
    radius = np.hypot(xy[:, 0], xy[:, 1])
    phi = np.arctan2(-xy[:, 0], xy[:, 1]) / pitch
    new_kinds = [kinds[int(n)] for n in kept.tolist()]
    order = _surface_order(quads, new_kinds, int(index[block.surface_order[gap]]))
    new_block = Block(
        phi=np.asarray(phi, dtype=np.float64),
        radius_mm=np.asarray(radius, dtype=np.float64),
        quads=quads,
        kind=tuple(new_kinds),
        surface_order=tuple(order),
    )
    old_order = block.surface_order
    new_features = tuple(
        order.index(int(index[n]))
        for n in (
            old_order[gap],
            old_order[form],
            old_order[tip_form],
            old_order[corner],
            rows[-1, -1],
        )
    )
    if new_features[:4] != (gap, form, tip_form, corner) or new_features[4] != corner + count:
        raise GeometryInfeasibleError("the surface of the cap is not in the order of the template")
    flags = np.concatenate((grid_flags[keep_quad], np.ones(len(new_quads), dtype=np.int64)))
    cap = TipCap(
        corner_grid=index[corner_ids], land_grid=index[land_ids], core_grid=index[core_ids]
    )
    return new_block, flags, new_features, cap


# --- the template --------------------------------------------------------------------------------


@dataclass(frozen=True)
class ResampledTemplate:
    """The trimmed blocks of the template with new counts and the lists ``sector_mesh``
    needs (all 0-based, as ``sector_template`` has them). ``tip_cap`` is the cap of the tooth
    tip when ``counts.cap_layers`` asks for one."""

    tooth: Block
    shoulder: Block
    tooth_left_interface: IntArray
    tooth_right_interface: IntArray
    tooth_partner: IntArray
    tooth_grid: IntArray
    tooth_surface_features: tuple[int, ...]
    shoulder_interface: IntArray
    shoulder_cut: IntArray
    tip_cap: TipCap | None = None


def _on_line(block: Block, phi: float) -> IntArray:
    """Nodes on the line phi = const, from the bore outwards."""
    nodes = np.flatnonzero(np.abs(block.phi - phi) < 1.0e-6)
    return np.asarray(nodes[np.argsort(block.radius_mm[nodes])], dtype=np.int64)


def _partners(block: Block) -> IntArray:
    """For every node the node at the mirrored place (phi -> -phi)."""
    mirrored = np.column_stack((-block.phi, block.radius_mm))
    original = np.column_stack((block.phi, block.radius_mm))
    partner = np.full(len(block.phi), -1, dtype=np.int64)
    order = np.lexsort((original[:, 1], original[:, 0]))
    keys = original[order]
    for node, (p, r) in enumerate(mirrored):
        lower = p - 1.0e-7
        k = int(np.searchsorted(keys[:, 0], lower))
        while k < len(keys) and keys[k, 0] <= p + 1.0e-7:
            if abs(keys[k, 1] - r) < 1.0e-6:
                partner[node] = order[k]
                break
            k += 1
    if int(partner.min()) < 0:
        raise GeometryInfeasibleError("the resampled tooth block is not mirror symmetric")
    return partner


def resample_template(
    tooth: Block,
    shoulder: Block,
    tooth_left: IntArray,
    tooth_right: IntArray,
    shoulder_interface: IntArray,
    shoulder_cut: IntArray,
    features: tuple[int, ...],
    rim_rings: int,
    number_of_teeth: int,
    counts: MeshCounts,
) -> ResampledTemplate:
    """The trimmed tooth and shoulder blocks with the numbers of ``counts``.

    ``tooth_left`` / ``tooth_right`` and ``shoulder_interface`` / ``shoulder_cut`` are the node
    lists of the trimmed blocks from the bore outwards (the node at index ``rim_rings`` lies on
    the fan ring), ``features`` the positions of the feature points in the surface order of
    the tooth block.
    """
    if not isinstance(counts, MeshCounts):
        raise InputRangeError(f"a MeshCounts is required, got {type(counts).__name__}")
    pitch = 2.0 * math.pi / number_of_teeth
    per_class = counts.per_class
    order = np.array(tooth.surface_order, dtype=np.int64)
    gap, form, tip_form, corner, centre = features
    last = len(order) - 1
    seeds = _Seeds(
        {
            "root": set(order[: form + 1].tolist()) | set(order[last - form :].tolist()),
            "height": set(order[form : tip_form + 1].tolist())
            | set(order[last - tip_form : last - form + 1].tolist()),
            "chamfer": set(order[tip_form : corner + 1].tolist())
            | set(order[last - corner : last - tip_form + 1].tolist()),
            "root_layers": set(tooth_left[rim_rings:].tolist())
            | set(tooth_right[rim_rings:].tolist()),
            "rim_rings": set(tooth_left[: rim_rings + 1].tolist())
            | set(tooth_right[: rim_rings + 1].tolist()),
            "centre": {n for n, kind in enumerate(tooth.kind) if kind == "bore"},
        }
    )
    mirrored_form, mirrored_tip_form = last - form, last - tip_form
    forced = (
        int(order[form]),
        int(order[tip_form]),
        int(order[centre]),
        int(order[mirrored_form]),
        int(order[mirrored_tip_form]),
        int(tooth_left[rim_rings]),
        int(tooth_right[rim_rings]),
    )
    new_tooth, _, classes, corners = resample_block(
        tooth, pitch, forced, seeds, per_class, int(order[gap])
    )
    new_order = list(new_tooth.surface_order)
    new_features = tuple(
        new_order.index(corners[int(order[k])]) for k in (gap, form, tip_form, corner, centre)
    )
    grid = np.array(
        [1 if "height" in pair or "chamfer" in pair else 0 for pair in classes], dtype=np.int64
    )
    cap: TipCap | None = None
    if counts.cap_layers:
        new_tooth, grid, new_features, cap = _with_tip_cap(
            new_tooth, new_features, grid, counts, pitch
        )

    bore_corner = int(shoulder_cut[0])
    top_corner = int(shoulder_cut[-1])
    shoulder_seeds = _Seeds(
        {
            "shoulder": {n for n, kind in enumerate(shoulder.kind) if kind in ("bore", "surface")}
            | {bore_corner, top_corner},
            "root_layers": set(shoulder_interface[rim_rings:].tolist()),
            "rim_rings": set(shoulder_interface[: rim_rings + 1].tolist()),
        }
    )
    new_shoulder, _, _, _ = resample_block(
        shoulder,
        pitch,
        (int(shoulder_interface[rim_rings]), int(shoulder_cut[rim_rings])),
        shoulder_seeds,
        per_class,
        top_corner,
    )
    return ResampledTemplate(
        tooth=new_tooth,
        shoulder=new_shoulder,
        tooth_left_interface=_on_line(new_tooth, -0.5),
        tooth_right_interface=_on_line(new_tooth, 0.5),
        tooth_partner=_partners(new_tooth),
        tooth_grid=grid,
        tooth_surface_features=new_features,
        shoulder_interface=_on_line(new_shoulder, 0.0),
        shoulder_cut=_on_line(new_shoulder, -1.0),
        tip_cap=cap,
    )
