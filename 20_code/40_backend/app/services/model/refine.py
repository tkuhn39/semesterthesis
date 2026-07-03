"""
@module: app.services.model.refine
@context: Domain layer — FE rolling model, parametric mesh-density control (plan v2 workstream B).
@role: FVA-style mesh-density parameters on the transplanted reference topology via **conformal
       chord splits**. A chord is the band of topologically parallel edges (the opposite-edge
       relation inside each quad, propagated across shared edges). Splitting a chord inserts a
       full row of nodes through the whole band: the mesh stays all-quad and conformal, no
       valence changes, so the reference block structure — dome fan, single irregular node per
       gap, tooth congruence, mirror symmetry — survives refinement by construction.

Density groups follow the FVA convergence presets: chords whose surface edges lie on the root
fillet region refine the root (n_fuss direction along the rounding), chords with involute-flank
surface edges refine the flank (n_flanke). Selection is purely geometric (radius bands), hence
rotation- and mirror-equivariant: all teeth refine identically.
"""

from __future__ import annotations

from collections import defaultdict

import numpy as np
from numpy.typing import NDArray

Array = NDArray[np.float64]
Quad = tuple[int, ...]
Edge = tuple[int, int]


def _edge(a: int, b: int) -> Edge:
    return (a, b) if a < b else (b, a)


def chords(quads: list[Quad]) -> list[set[Edge]]:
    """All chords (equivalence classes of edges under the in-quad opposite-edge relation)."""
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

    for q in quads:
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


def chords_with_surface_edges(
    quads: list[Quad],
    pts: Array,
    kind: list[str],
    r_lo: float,
    r_hi: float,
    seed_nodes: set[int] | None = None,
) -> set[Edge]:
    """Union of all chord edges whose chord contains a surface edge in the radius band.

    ``r_lo/r_hi`` bound the mid-point radius of the seed surface edge (both end nodes must be
    ``surface`` and, when given, inside ``seed_nodes`` — used to exclude the shoulder surface,
    which shares the root-band radii but must keep the reference density). Returns the flat
    edge set ready for :func:`split_edges`.
    """
    selected: set[Edge] = set()
    for chord in chords(quads):
        for a, b in chord:
            if kind[a] != "surface" or kind[b] != "surface":
                continue
            if seed_nodes is not None and (a not in seed_nodes or b not in seed_nodes):
                continue
            mid = 0.5 * (pts[a] + pts[b])
            r = float(np.hypot(mid[0], mid[1]))
            if r_lo <= r <= r_hi:
                selected |= chord
                break
    return selected


def split_edges(
    pts: Array,
    quads: list[Quad],
    kind: list[str],
    edges: set[Edge],
    parts: int = 2,
) -> tuple[Array, list[Quad], list[str], list[int]]:
    """Split every quad along its marked edge pairs into ``parts`` strips (conformal).

    Each quad is re-emitted from a local bilinear (nu+1)×(nv+1) node grid where nu/nv = ``parts``
    when the u/v edge pair is marked, else 1. Edge nodes are shared through an orientation-aware
    registry, so neighbouring quads stay conformal; marked edge pairs are complete by chord
    construction (a quad has either both or neither edge of a chord).

    Returns (points, quads, kinds, new_surface_node_ids) — the latter for re-projection of new
    surface nodes onto the analytic contour.
    """
    if parts < 2:
        return pts, quads, kind, []
    points: list[tuple[float, float]] = [(float(x), float(y)) for x, y in pts]
    kinds = list(kind)
    edge_nodes: dict[tuple[int, int, int], int] = {}
    new_surface: list[int] = []

    def node_on_edge(a: int, b: int, k: int, n: int) -> int:
        """Node at fraction k/n from a to b, shared via the (min,max,oriented-k) key."""
        if k == 0:
            return a
        if k == n:
            return b
        key = (a, b, k) if a < b else (b, a, n - k)
        idx = edge_nodes.get(key)
        if idx is None:
            t = k / n
            x = (1 - t) * points[a][0] + t * points[b][0]
            y = (1 - t) * points[a][1] + t * points[b][1]
            idx = len(points)
            points.append((x, y))
            child = kinds[a] if kinds[a] == kinds[b] else "interior"
            kinds.append(child)
            if child == "surface":
                new_surface.append(idx)
            edge_nodes[key] = idx
        return idx

    out: list[Quad] = []
    for q in quads:
        u_marked = _edge(q[0], q[1]) in edges  # implies the opposite (q2,q3) edge too
        v_marked = _edge(q[1], q[2]) in edges
        nu = parts if u_marked else 1
        nv = parts if v_marked else 1
        if nu == 1 and nv == 1:
            out.append(q)
            continue
        # Local grid: corner order q0 --u--> q1, q1 --v--> q2 (bilinear interior).
        grid = np.empty((nu + 1, nv + 1), dtype=int)
        for i in range(nu + 1):
            for j in range(nv + 1):
                if i in (0, nu) and j in (0, nv):
                    grid[i, j] = q[{(0, 0): 0, (nu, 0): 1, (nu, nv): 2, (0, nv): 3}[(i, j)]]
                elif j == 0:
                    grid[i, j] = node_on_edge(q[0], q[1], i, nu)
                elif j == nv:
                    grid[i, j] = node_on_edge(q[3], q[2], i, nu)
                elif i == 0:
                    grid[i, j] = node_on_edge(q[0], q[3], j, nv)
                elif i == nu:
                    grid[i, j] = node_on_edge(q[1], q[2], j, nv)
                else:
                    u, v = i / nu, j / nv
                    p0, p1 = np.array(points[q[0]]), np.array(points[q[1]])
                    p2, p3 = np.array(points[q[2]]), np.array(points[q[3]])
                    p = (1 - u) * (1 - v) * p0 + u * (1 - v) * p1 + u * v * p2 + (1 - u) * v * p3
                    grid[i, j] = len(points)
                    points.append((float(p[0]), float(p[1])))
                    kinds.append("interior")
        for i in range(nu):
            for j in range(nv):
                out.append(
                    (
                        int(grid[i, j]),
                        int(grid[i + 1, j]),
                        int(grid[i + 1, j + 1]),
                        int(grid[i, j + 1]),
                    )
                )
    return np.asarray(points, dtype=float), out, kinds, new_surface
