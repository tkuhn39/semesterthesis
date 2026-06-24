"""
@module: app.services.model.block_mesh
@context: Domain layer — FE rolling model, block-structured (FVA/STIRAK) gear-sector mesher.
@role: Build the reference-style block-structured tooth mesh per ``MESHING_SPEC.md`` on the proven
       scaffold pipeline (TFI/Coons blocks + a shared-node registry for conformity, no tolerance
       merge, no paving/advancing-front/gmsh). The transfinite pipeline (``dist``, ``coons``,
       ``NodeRegistry``, ``grid_quads``, ``extrude``, ``write_inp``) is taken verbatim from the
       binding scaffold and stays unchanged; this module adds the gear blocks (B3 fillet band,
       B4 tooth core, B1 rim, B2 fine→coarse 2:1 templates), the 4-tooth + 2-toothless sector, and
       the section-11 node-relocation finish (optimization-based, frozen connectivity, fixed
       boundary/feature/cut nodes) that lifts the 2:1 valence-3 nodes to det(J) ≥ 0.35.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict

import numpy as np
from numpy.typing import NDArray

from app.services.geometry.tooth_form import ToothProfile

Array = NDArray[np.float64]
Coords = list[tuple[float, float, float]]
QuadList = list[tuple[int, ...]]


# ============================================================================
# Proven scaffold pipeline (verbatim from gear_mesh_scaffold.py — DO NOT change the logic)
# ============================================================================
def dist(n: int, mode: str = "uniform", t0: float = 0.5, strength: float = 2.0) -> Array:
    """``n`` parameter values in [0,1]. mode: uniform | start | end | both | toward(t0)."""
    u = np.linspace(0.0, 1.0, n)
    if mode == "uniform":
        return u
    if mode == "both":
        return 0.5 * (1 - np.cos(np.pi * u))
    if mode == "start":
        return u**strength
    if mode == "end":
        return 1 - (1 - u) ** strength
    if mode == "toward":
        return _cluster_toward(u, t0, strength)
    raise ValueError(mode)


def _cluster_toward(u: Array, t0: float, strength: float) -> Array:
    """Monotone reparametrisation [0,1]→[0,1] clustering nodes toward t0 (e.g. the 30° point)."""
    out = np.empty_like(u)
    m = u <= t0
    out[m] = t0 * (1 - (1 - u[m] / max(t0, 1e-9)) ** strength)
    out[~m] = t0 + (1 - t0) * ((u[~m] - t0) / max(1 - t0, 1e-9)) ** strength
    return out


def coons(bottom: Array, top: Array, left: Array, right: Array) -> Array:
    """Transfinite (Coons) patch from 4 boundary curves. Returns node grid (ni, nj, 2)."""
    ni, nj = len(bottom), len(left)
    assert len(top) == ni and len(right) == nj
    p00, p10, p01, p11 = bottom[0], bottom[-1], top[0], top[-1]
    g = np.empty((ni, nj, 2))
    for i in range(ni):
        u = i / (ni - 1)
        for j in range(nj):
            v = j / (nj - 1)
            g[i, j] = (
                (1 - v) * bottom[i]
                + v * top[i]
                + (1 - u) * left[j]
                + u * right[j]
                - ((1 - u) * (1 - v) * p00 + u * (1 - v) * p10 + (1 - u) * v * p01 + u * v * p11)
            )
    return g


class NodeRegistry:
    """Global shared-node dictionary → conformity by construction (no tolerance merge)."""

    def __init__(self, tol: float = 1e-7) -> None:
        self.q = 1.0 / tol
        self.bykey: dict[tuple[int, int, int], int] = {}
        self.coords: Coords = []

    def key(self, x: float, y: float, z: float = 0.0) -> tuple[int, int, int]:
        return (round(x * self.q), round(y * self.q), round(z * self.q))

    def add(self, x: float, y: float, z: float = 0.0) -> int:
        k = self.key(x, y, z)
        idx = self.bykey.get(k)
        if idx is None:
            idx = len(self.coords)
            self.bykey[k] = idx
            self.coords.append((x, y, z))
        return idx

    def grid_ids(self, grid: Array, z: float = 0.0) -> NDArray[np.int64]:
        ni, nj, _ = grid.shape
        ids = np.empty((ni, nj), dtype=np.int64)
        for i in range(ni):
            for j in range(nj):
                ids[i, j] = self.add(float(grid[i, j, 0]), float(grid[i, j, 1]), z)
        return ids


def _signed_area(coords: Coords, q: tuple[int, ...]) -> float:
    a = 0.0
    for k in range(4):
        x1, y1 = coords[q[k]][0], coords[q[k]][1]
        x2, y2 = coords[q[(k + 1) % 4]][0], coords[q[(k + 1) % 4]][1]
        a += x1 * y2 - x2 * y1
    return a


def grid_quads(ids: NDArray[np.int64], coords: Coords) -> QuadList:
    """CCW quad connectivity from a node-ID grid (flips winding to positive area)."""
    ni, nj = ids.shape
    quads: QuadList = []
    for i in range(ni - 1):
        for j in range(nj - 1):
            q = (int(ids[i, j]), int(ids[i + 1, j]), int(ids[i + 1, j + 1]), int(ids[i, j + 1]))
            if _signed_area(coords, q) < 0:
                q = (q[0], q[3], q[2], q[1])
            quads.append(q)
    return quads


def quad_min_jac_ok(coords: Coords, quads: QuadList) -> int:
    """Count of degenerate/flipped quads (signed area ≤ 0)."""
    return sum(1 for q in quads if _signed_area(coords, q) <= 0)


def extrude(coords2d: Coords, quads: QuadList, b: float, n_breite: int) -> tuple[Coords, QuadList]:
    """Extrude 2D quads → 3D hexes (C3D8) over depth ``b`` with ``n_breite`` layers."""
    zs = np.linspace(0.0, b, n_breite + 1)
    npts = len(coords2d)
    coords3d = [(x, y, float(z)) for z in zs for (x, y, _z) in coords2d]
    hexes: QuadList = []
    for layer in range(n_breite):
        o0, o1 = layer * npts, (layer + 1) * npts
        for a, bb, cc, d in quads:
            hexes.append((a + o0, bb + o0, cc + o0, d + o0, a + o1, bb + o1, cc + o1, d + o1))
    return coords3d, hexes


def write_inp(
    path: str,
    coords: Coords,
    elems: QuadList,
    etype: str = "C3D8I",
    nsets: dict[str, list[int]] | None = None,
    elset_name: str = "ALL",
) -> None:
    nsets = nsets or {}
    with open(path, "w") as f:
        f.write("*HEADING\n block-structured gear sector (MESHING_SPEC.md)\n*NODE\n")
        for i, (x, y, z) in enumerate(coords, 1):
            f.write(f"{i}, {x:.9g}, {y:.9g}, {z:.9g}\n")
        f.write(f"*ELEMENT, TYPE={etype}, ELSET={elset_name}\n")
        for e, nodes in enumerate(elems, 1):
            f.write(f"{e}, " + ", ".join(str(n + 1) for n in nodes) + "\n")
        for name, ids in nsets.items():
            f.write(f"*NSET, NSET={name}\n")
            ids1 = [i + 1 for i in sorted(set(ids))]
            for k in range(0, len(ids1), 10):
                f.write(", ".join(str(v) for v in ids1[k : k + 10]) + "\n")
        f.write(f"*SOLID SECTION, ELSET={elset_name}, MATERIAL=STEEL\n")
        f.write("*MATERIAL, NAME=STEEL\n*ELASTIC\n210000., 0.3\n")


def arc(
    r: float,
    a0: float,
    a1: float,
    n: int,
    tmode: str = "uniform",
    t0: float = 0.5,
    strength: float = 2.0,
) -> Array:
    t = dist(n, tmode, t0, strength)
    ang = a0 + (a1 - a0) * t
    return np.column_stack([r * np.sin(ang), r * np.cos(ang)])


def radial(
    a: float,
    r0: float,
    r1: float,
    n: int,
    tmode: str = "uniform",
    t0: float = 0.5,
    strength: float = 2.0,
) -> Array:
    t = dist(n, tmode, t0, strength)
    rr = r0 + (r1 - r0) * t
    return np.column_stack([rr * np.sin(a), rr * np.cos(a)])


# ============================================================================
# Gear geometry blocks (MESHING_SPEC.md sections 2/5) — added on the scaffold
# ============================================================================
def resample(curve: Array, params: Array) -> Array:
    """Interpolate an (m,2) curve at arc-length fractions ``params`` (0..1)."""
    seg = np.hypot(np.diff(curve[:, 0]), np.diff(curve[:, 1]))
    s = np.concatenate([[0.0], np.cumsum(seg)])
    s /= s[-1]
    return np.column_stack([np.interp(params, s, curve[:, 0]), np.interp(params, s, curve[:, 1])])


def arc_between(p0: Array, p1: Array, n: int, tmode: str = "uniform", t0: float = 0.5) -> Array:
    """Arc on the circle through p0,p1 (same radius), n nodes, exact endpoints."""
    r0, r1 = math.hypot(p0[0], p0[1]), math.hypot(p1[0], p1[1])
    a0, a1 = math.atan2(p0[0], p0[1]), math.atan2(p1[0], p1[1])
    t = dist(n, tmode, t0)
    out = np.column_stack(
        [
            (r0 + (r1 - r0) * t) * np.sin(a0 + (a1 - a0) * t),
            (r0 + (r1 - r0) * t) * np.cos(a0 + (a1 - a0) * t),
        ]
    )
    out[0], out[-1] = p0, p1
    return out


def profile_curves(profile: ToothProfile) -> tuple[Array, Array, int]:
    """Left/right tooth boundary (fillet+flank) as (n,2), and the fillet/flank split index."""
    b = profile.transverse_right_boundary(fillet_points=60, flank_points=80)
    right = np.array([[q[0], q[1]] for q in b])
    left = right * np.array([-1.0, 1.0])
    r = np.hypot(right[:, 0], right[:, 1])
    nfil = int(np.argmin(np.abs(r - profile.d_Ff / 2.0)))
    return left, right, nfil


def tangent30_param(fillet: Array) -> float:
    """Arc-length fraction of the 30°-tangent point (DIN 3990 / ISO 6336-3 root section)."""
    tan = np.diff(fillet, axis=0)
    ang = np.degrees(np.arctan2(np.abs(tan[:, 0]), np.abs(tan[:, 1])))  # 90=horizontal, 0=vertical
    seg = np.hypot(tan[:, 0], tan[:, 1])
    s = np.concatenate([[0.0], np.cumsum(seg)])
    s /= s[-1]
    i = int(np.argmin(np.abs(ang - 30.0)))
    return float((s[i] + s[i + 1]) / 2)


def tooth_blocks(
    profile: ToothProfile, n_flanke: int, n_fuss: int, n_dicke: int
) -> dict[str, Array]:
    """B3 fillet band (n_fuss over the rounding, densified to the 30° point) + B4 core, sharing the
    d_Ff edge. Curve seeding only — no offset marching (MESHING_SPEC section 5)."""
    left, right, nfil = profile_curves(profile)
    fil_r, fla_r = right[: nfil + 1], right[nfil:]
    fil_l, fla_l = left[: nfil + 1], left[nfil:]
    t0 = tangent30_param(fil_r)
    d_fuss = dist(n_fuss + 1, "toward", t0, 2.5)
    b3_left, b3_right = resample(fil_l, d_fuss), resample(fil_r, d_fuss)
    b3 = coons(
        arc_between(b3_left[0], b3_right[0], n_dicke + 1),
        arc_between(b3_left[-1], b3_right[-1], n_dicke + 1),
        b3_left,
        b3_right,
    )
    b4_left = resample(fla_l, dist(n_flanke + 1))
    b4_right = resample(fla_r, dist(n_flanke + 1))
    b4 = coons(b3[:, -1, :], arc_between(b4_left[-1], b4_right[-1], n_dicke + 1), b4_left, b4_right)
    return {"B3": b3, "B4": b4}


def transition_band(reg: NodeRegistry, top_xy: Array, r_bot: float) -> tuple[Array, QuadList]:
    """Spec B2 'reine Quad-Template' 2:1 fine→coarse band (N segments → N/2), N%4==0.

    Validated 6-quad / 3-interior template per 4→2 unit. Shared top nodes resolve through the
    registry by identical coordinates (no tolerance merge). Returns (bottom row (N/2+1,2), quads).
    """
    n = len(top_xy) - 1
    assert n % 4 == 0, f"transition needs N%4==0, got {n}"
    ang = [math.atan2(c[0], c[1]) for c in top_xy]
    r_top = float(np.mean([math.hypot(c[0], c[1]) for c in top_xy]))
    r_mid = 0.5 * (r_top + r_bot)
    top = [reg.add(float(c[0]), float(c[1])) for c in top_xy]

    def node(r: float, a: float) -> int:
        return reg.add(r * math.sin(a), r * math.cos(a))

    bot = [node(r_bot, ang[2 * j]) for j in range(n // 2 + 1)]
    bot_xy = np.array(
        [[r_bot * math.sin(ang[2 * j]), r_bot * math.cos(ang[2 * j])] for j in range(n // 2 + 1)]
    )
    quads: QuadList = []
    for u in range(n // 4):
        t = top[4 * u : 4 * u + 5]
        b0, b1, b2 = bot[2 * u], bot[2 * u + 1], bot[2 * u + 2]
        i0 = node(r_mid, ang[4 * u + 1])
        ic = node(r_mid, ang[4 * u + 2])
        i1 = node(r_mid, ang[4 * u + 3])
        for q in (
            [t[0], t[1], i0, b0],
            [t[1], t[2], ic, i0],
            [t[2], t[3], i1, ic],
            [t[3], t[4], b2, i1],
            [b0, i0, ic, b1],
            [b1, ic, i1, b2],
        ):
            qt = tuple(q)
            quads.append(qt if _signed_area(reg.coords, qt) > 0 else (qt[0], qt[3], qt[2], qt[1]))
    return bot_xy, quads


# ============================================================================
# Quality + section-11 node-relocation finish
# ============================================================================
def min_scaled_jac(coords: Coords, quads: QuadList) -> tuple[float, int]:
    """FVA Jacobi-Güte: (min over quads of min-corner-sine, count of cells < 0.35). CCW assumed."""
    c = np.array(coords)
    worst, nbad = 1.0, 0
    for q in quads:
        p = c[list(q), :2]
        sj = 1.0
        for k in range(4):
            e1, e2 = p[(k + 1) % 4] - p[k], p[(k - 1) % 4] - p[k]
            cr = e1[0] * e2[1] - e1[1] * e2[0]
            sj = min(sj, cr / max(math.hypot(e1[0], e1[1]) * math.hypot(e2[0], e2[1]), 1e-30))
        worst = min(worst, sj)
        nbad += sj < 0.35
    return worst, nbad


def boundary_nodes(quads: QuadList) -> set[int]:
    """Node indices on the mesh boundary (edges used by exactly one quad) — the tooth surface,
    gap floor, bore and both cut lines; held fixed by the section-11 finish."""
    ec: Counter[frozenset[int]] = Counter()
    for q in quads:
        for k in range(4):
            ec[frozenset((q[k], q[(k + 1) % 4]))] += 1
    bnd: set[int] = set()
    for e, c in ec.items():
        if c == 1:
            bnd |= set(e)
    return bnd


_OPT_DIRS = np.array(
    [[math.cos(t), math.sin(t)] for t in np.linspace(0.0, 2.0 * math.pi, 8, endpoint=False)]
)


def optimize_finish(
    coords: Coords,
    quads: QuadList,
    fixed: set[int],
    iters: int = 80,
) -> Coords:
    """MESHING_SPEC section 11 finish: lexicographic (worst element first) node relocation on a
    **frozen** connectivity, with boundary/feature/cut nodes held fixed (rules 1–4). Never naive
    Laplace: each move maximises (min incident scaled Jacobian, then mean) and never lowers it.
    """
    pts = np.array([(c[0], c[1]) for c in coords], dtype=float)
    inc: dict[int, QuadList] = defaultdict(list)
    nbr: dict[int, set[int]] = defaultdict(set)
    for q in quads:
        for k in range(4):
            inc[q[k]].append(q)
            nbr[q[k]].update((q[(k + 1) % 4], q[(k - 1) % 4]))
    free = [i for i in range(len(pts)) if i not in fixed and inc[i]]
    nb = {i: np.fromiter(nbr[i], int) for i in free}

    def qsj(p4: Array) -> float:
        sj = 1.0
        for k in range(4):
            e1, e2 = p4[(k + 1) % 4] - p4[k], p4[(k - 1) % 4] - p4[k]
            cr = e1[0] * e2[1] - e1[1] * e2[0]
            sj = min(sj, cr / max(math.hypot(e1[0], e1[1]) * math.hypot(e2[0], e2[1]), 1e-30))
        return sj

    for it in range(iters):
        step = 0.5 * (1 - it / iters) + 0.05
        for i in free:
            qs = inc[i]

            def obj(pos: Array, _qs: QuadList = qs, _i: int = i) -> tuple[float, float]:
                old = pts[_i].copy()
                pts[_i] = pos
                sjs = [qsj(pts[list(q)]) for q in _qs]
                pts[_i] = old
                return min(sjs), sum(sjs) / len(sjs)

            h = float(np.mean(np.hypot(*(pts[i] - pts[nb[i]]).T)))
            cen = pts[nb[i]].mean(axis=0)
            best, best_p = obj(pts[i]), pts[i].copy()
            for cand in [cen, *(cen + step * h * _OPT_DIRS), *(pts[i] + step * h * _OPT_DIRS)]:
                val = obj(cand)
                if val > best:
                    best, best_p = val, cand
            pts[i] = best_p
    return [(float(pts[i, 0]), float(pts[i, 1]), 0.0) for i in range(len(pts))]
