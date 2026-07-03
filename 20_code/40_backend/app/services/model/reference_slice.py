"""
@module: app.services.model.reference_slice
@context: Domain layer — FE rolling model, reference-mesh ground-truth mining.
@role: Parse the ANSA/FVA reference deck (``kst-E_8_DY2-0_WS30_ohne_Radkoerper.inp``), slice the
       mid z-plane of a gear part, recover the exact 2D quad topology, measure it (valence
       histograms, irregular nodes, rim grid, scaled Jacobian) and export the sector topology as a
       reusable :class:`SectorTemplate` for the block mesher (ADR-019 "topology transplant").

Measured ground truth (wheel part, slice z=0): 3024 quads / 3329 nodes, fully conformal manifold,
zero degenerate quads. All interior nodes are valence 4 except exactly ONE fan-convergence node per
tooth gap on the rim-top ring (valence 6 mid-sector, valence 5 at the sector-edge gaps) — the whole
fine→coarse reduction is concentrated there; there is no distributed 4→2 template band.

Parser trap: the rim hexes are written with a different local axis orientation than the tooth
hexes, so the four in-slice nodes of a face are NOT generally in cyclic order in the element
connectivity — they must be re-ordered cyclically around the face centroid, otherwise bowtie quads
with phantom diagonals corrupt every valence/boundary measurement.
"""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from scipy.spatial import cKDTree

from app.services.model.block_mesh import min_scaled_jac

Array = NDArray[np.float64]
Quad = tuple[int, int, int, int]

#: Default reference deck location relative to the repository root.
REFERENCE_DECK = (
    "30_references_and_examples/32_Abaqus/implicit/kst-E_8_DY2-0_WS30_ohne_Radkoerper.inp"
)


# ============================================================================
# Parsing + slicing
# ============================================================================
def parse_part(
    inp_path: str | Path, part_name: str
) -> tuple[dict[int, tuple[float, float, float]], list[list[int]]]:
    """Nodes and C3D8* connectivity of one ``*PART`` section (streamed, flat-file safe)."""
    want = part_name.upper().replace(" ", "")
    nodes: dict[int, tuple[float, float, float]] = {}
    elems: list[list[int]] = []
    mode: str | None = None
    in_part = False
    with open(inp_path, errors="ignore") as f:
        for line in f:
            s = line.strip()
            up = s.upper()
            if up.startswith("*PART"):
                in_part = want in up.replace(" ", "")
                mode = None
                continue
            if up.startswith("*INSTANCE") or up.startswith("*ASSEMBLY"):
                break
            if not in_part:
                continue
            if up.startswith("*NODE"):
                mode = "node"
                continue
            if up.startswith("*ELEMENT"):
                mode = "elem" if "TYPE=C3D8" in up.replace(" ", "") else None
                continue
            if up.startswith("*"):
                mode = None
                continue
            if mode == "node":
                parts = s.split(",")
                if len(parts) >= 4:
                    nodes[int(parts[0])] = (float(parts[1]), float(parts[2]), float(parts[3]))
            elif mode == "elem":
                ints = [int(v) for v in s.replace(",", " ").split()]
                if len(ints) == 9:
                    elems.append(ints[1:])
    return nodes, elems


def mid_slice(
    nodes: dict[int, tuple[float, float, float]], elems: list[list[int]]
) -> tuple[list[Quad], dict[int, tuple[float, float]]]:
    """The 2D quad mesh at the mid z-level (faces of hexes spanning the two middle levels).

    Face nodes are re-ordered cyclically around the face centroid (see module docstring) and
    wound counter-clockwise.
    """
    z_levels = sorted({round(v[2], 6) for v in nodes.values()})
    z0 = z_levels[len(z_levels) // 2]
    z1 = z_levels[len(z_levels) // 2 + 1]
    quads: list[Quad] = []
    for e in elems:
        bot = [n for n in e if abs(round(nodes[n][2], 6) - z0) < 1e-6]
        top = [n for n in e if abs(round(nodes[n][2], 6) - z1) < 1e-6]
        if len(bot) != 4 or len(top) != 4:
            continue
        cx = sum(nodes[n][0] for n in bot) / 4.0
        cy = sum(nodes[n][1] for n in bot) / 4.0
        bot.sort(key=lambda n: math.atan2(nodes[n][1] - cy, nodes[n][0] - cx))
        quads.append((bot[0], bot[1], bot[2], bot[3]))
    coords = {n: (nodes[n][0], nodes[n][1]) for q in quads for n in q}
    return quads, coords


# ============================================================================
# Topology measurement
# ============================================================================
@dataclass(frozen=True)
class SliceMetrics:
    """Pinnable topology/quality numbers of one reference slice."""

    n_quads: int
    n_nodes: int
    interior_valence: dict[int, int]
    boundary_valence: dict[int, int]
    irregular: list[tuple[int, int, float, float]]  # (node id, valence, r, theta_deg)
    rim_rings: int
    rim_cols: int
    min_scaled_jacobian: float
    cells_below_035: int


def _edges_and_neighbours(
    quads: list[Quad],
) -> tuple[Counter[frozenset[int]], dict[int, set[int]]]:
    edge_count: Counter[frozenset[int]] = Counter()
    nbrs: dict[int, set[int]] = defaultdict(set)
    for q in quads:
        for k in range(4):
            a, b = q[k], q[(k + 1) % 4]
            edge_count[frozenset((a, b))] += 1
            nbrs[a].add(b)
            nbrs[b].add(a)
    return edge_count, nbrs


def boundary_node_ids(quads: list[Quad]) -> set[int]:
    """Nodes on edges used by exactly one quad (outer contour + bore + both cut faces)."""
    edge_count, _ = _edges_and_neighbours(quads)
    out: set[int] = set()
    for edge, count in edge_count.items():
        if count == 1:
            out |= set(edge)
    return out


def measure(quads: list[Quad], coords: dict[int, tuple[float, float]]) -> SliceMetrics:
    """Valence histograms, irregular interior nodes, rim grid size and Jacobian quality."""
    _, nbrs = _edges_and_neighbours(quads)
    boundary = boundary_node_ids(quads)
    interior = [n for n in coords if n not in boundary]
    interior_valence = Counter(len(nbrs[n]) for n in interior)
    boundary_valence = Counter(len(nbrs[n]) for n in boundary)
    irregular = sorted(
        (
            (n, len(nbrs[n]), math.hypot(*coords[n]), math.degrees(math.atan2(*coords[n][::-1])))
            for n in interior
            if len(nbrs[n]) != 4
        ),
        key=lambda t: t[3],
    )
    # Rim = the polar body grid. Its column count equals the bore-arc node count; rings are the
    # rounded-radius groups with exactly that many nodes (the dense root/dome arcs never match).
    bore_r = min(math.hypot(*coords[n]) for n in boundary)
    cols = sum(1 for n in boundary if abs(math.hypot(*coords[n]) - bore_r) < 1e-3)
    ring_hist = Counter(round(math.hypot(*coords[n]), 2) for n in coords)
    rim_rings = sum(1 for c in ring_hist.values() if c == cols)
    # Quality via the mesher's own metric (index-based quads over a dense coordinate list).
    index = {n: i for i, n in enumerate(coords)}
    coords3d = [(x, y, 0.0) for x, y in coords.values()]
    idx_quads: list[tuple[int, ...]] = [
        (index[a], index[b], index[c], index[d]) for a, b, c, d in quads
    ]
    worst, n_bad = min_scaled_jac(coords3d, idx_quads)
    return SliceMetrics(
        n_quads=len(quads),
        n_nodes=len(coords),
        interior_valence=dict(sorted(interior_valence.items())),
        boundary_valence=dict(sorted(boundary_valence.items())),
        irregular=irregular,
        rim_rings=rim_rings,
        rim_cols=cols,
        min_scaled_jacobian=worst,
        cells_below_035=n_bad,
    )


# ============================================================================
# Sector template (ADR-019 topology transplant)
# ============================================================================
NODE_KINDS = ("interior", "surface", "bore", "cut")


@dataclass
class SectorTemplate:
    """The reference sector's exact 2D topology with reference node positions.

    ``nodes`` are the slice coordinates (mm, reference frame), ``quads`` index into them
    (CCW). ``kind`` classifies each node (surface = gear outer contour incl. shoulders,
    bore, cut = the two radial Fesselung faces, interior = free for smoothing).
    ``surface_order`` walks the outer contour from the cut-A corner to the cut-B corner.

    ``canon_*`` encode the sector symmetry orbit of every node (see
    :func:`compute_canonical_map`): ``pos_i = R(canon_rot_i · pitch) ∘ M^canon_mirror_i (rep)``
    with M = reflection across the sector bisector. Used to enforce exact tooth-to-tooth
    congruence (and, for symmetric flanks, in-tooth mirror symmetry) after any node placement.
    """

    nodes: Array  # (N, 2)
    quads: NDArray[np.int64]  # (M, 4)
    kind: list[str]
    surface_order: list[int]
    meta: dict[str, float | int | str]
    canon_group: list[int]
    canon_rot: list[int]
    canon_mirror: list[bool]

    def to_json(self, path: str | Path) -> None:
        payload = {
            "nodes": [[round(x, 7), round(y, 7)] for x, y in self.nodes.tolist()],
            "quads": self.quads.tolist(),
            "kind": self.kind,
            "surface_order": self.surface_order,
            "meta": self.meta,
            "canon_group": self.canon_group,
            "canon_rot": self.canon_rot,
            "canon_mirror": [int(m) for m in self.canon_mirror],
        }
        Path(path).write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")

    @classmethod
    def from_json(cls, path: str | Path) -> SectorTemplate:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            nodes=np.asarray(payload["nodes"], dtype=float),
            quads=np.asarray(payload["quads"], dtype=np.int64),
            kind=list(payload["kind"]),
            surface_order=list(payload["surface_order"]),
            meta=dict(payload["meta"]),
            canon_group=list(payload["canon_group"]),
            canon_rot=list(payload["canon_rot"]),
            canon_mirror=[bool(m) for m in payload["canon_mirror"]],
        )


# ============================================================================
# Sector symmetry: canonical node orbits (tooth congruence + mirror symmetry)
# ============================================================================
def _apply_sym(points: Array, bisector: float, pitch: float, rot: int, mirror: bool) -> Array:
    """Apply ``R(rot·pitch) ∘ M^mirror`` about the origin (M = reflection across bisector)."""
    out = np.asarray(points, dtype=float)
    if mirror:
        # Reflection across the line at angle ``bisector``: conjugate rotation of a y-flip.
        c, s = math.cos(2.0 * bisector), math.sin(2.0 * bisector)
        out = out @ np.array([[c, s], [s, -c]])
    ang = rot * pitch
    c, s = math.cos(ang), math.sin(ang)
    return out @ np.array([[c, s], [-s, c]])  # row-vector CCW rotation


def compute_canonical_map(
    nodes: Array, bisector: float, pitch: float, tol: float = 0.005
) -> tuple[list[int], list[int], list[bool]]:
    """Orbit decomposition of the node set under the sector's symmetry candidates.

    Candidate transforms: rotations by k·pitch (k = −5…5) with optional reflection across the
    sector bisector. Two nodes join a group when one maps onto the other within ``tol`` (mm).
    Union-find keeps orbits consistent; each node stores the (rot, mirror) that produces it
    from its group representative. Tooth-to-tooth congruence uses mirror=False members only,
    in-tooth mirror symmetry adds the mirrored members (guarded by ``is_flank_symmetric``).
    """
    n = len(nodes)
    parent = list(range(n))

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    tree = cKDTree(nodes)
    for mirror in (False, True):
        for rot in range(-5, 6):
            if rot == 0 and not mirror:
                continue
            moved = _apply_sym(nodes, bisector, pitch, rot, mirror)
            dist, idx = tree.query(moved)
            for i in range(n):
                if dist[i] < tol:
                    union(i, int(idx[i]))

    group = [find(i) for i in range(n)]
    # Tolerance-collapse guard. Largest genuine orbit: rim-grid columns sit at quarter-pitch
    # angles, so rotations (≤6 in the ±3-pitch sector) plus their mirror images give ≤ 13
    # members (e.g. φ ∈ {±0.25+k} ∪ {∓0.25+k}). Anything bigger means tol merged neighbours.
    sizes = Counter(group)
    if sizes and max(sizes.values()) > 13:
        raise ValueError(
            f"canonical map collapsed (tol too large): group size {max(sizes.values())}"
        )
    # Resolve each node's transform (rep --(rot,mirror)--> node) as a BIJECTION per orbit:
    # in dense regions (tooth tips) members lie only a few µm from each other's transforms,
    # so a naive nearest choice can assign one transform slot twice — leaving another slot
    # empty and silently breaking exact mirror closure. Greedy distance-sorted matching over
    # unused (rot, mirror) slots keeps the assigned transform multiset closed.
    members_by_group: dict[int, list[int]] = defaultdict(list)
    for i in range(n):
        members_by_group[group[i]].append(i)
    transforms = [(rot, mirror) for mirror in (False, True) for rot in range(-5, 6)]
    rot_of = [0] * n
    mir_of = [False] * n
    for rep, members in members_by_group.items():
        if len(members) == 1:
            continue
        candidates: list[tuple[float, int, int, bool]] = []
        for rot, mirror in transforms:
            moved = _apply_sym(nodes[rep : rep + 1], bisector, pitch, rot, mirror)[0]
            for i in members:
                d = float(np.hypot(*(moved - nodes[i])))
                if d < tol:
                    candidates.append((d, i, rot, mirror))
        candidates.sort()
        taken_node: set[int] = set()
        taken_slot: set[tuple[int, bool]] = set()
        for _d, i, rot, mirror in candidates:
            if i in taken_node or (rot, mirror) in taken_slot:
                continue
            taken_node.add(i)
            taken_slot.add((rot, mirror))
            rot_of[i], mir_of[i] = rot, mirror
        unmatched = [i for i in members if i not in taken_node]
        if unmatched:
            raise ValueError(f"orbit transform assignment incomplete: nodes {unmatched[:5]}")
    return group, rot_of, mir_of


def canonicalize_positions(
    nodes: Array,
    group: list[int],
    rot: list[int],
    mirror: list[bool],
    bisector: float,
    pitch: float,
    use_mirror: bool = True,
) -> Array:
    """Enforce exact orbit congruence: every node = transform of its group's mean position.

    With ``use_mirror=False`` (asymmetric flanks) mirrored members form separate subgroups, so
    only pure-rotation congruence (tooth-to-tooth) is enforced — per the flank-symmetry policy
    (DIN 867 §4.2 symmetric basic rack; asymmetry must come from the input data).
    """
    out = np.array(nodes, dtype=float)
    buckets: dict[tuple[int, bool], list[int]] = defaultdict(list)
    for i, g in enumerate(group):
        key = (g, mirror[i] if not use_mirror else False)
        buckets[key].append(i)
    for members in buckets.values():
        canon = np.mean(
            [
                _apply_sym(out[i : i + 1], bisector, pitch, -rot[i], False)[0]
                if not mirror[i]
                else _apply_sym(
                    _apply_sym(out[i : i + 1], bisector, pitch, -rot[i], False),
                    bisector,
                    pitch,
                    0,
                    True,
                )[0]
                for i in members
            ],
            axis=0,
        )
        if use_mirror:
            # Self-mirror orbits (nodes ON a tooth/gap centre line or cut face) never acquire
            # a mirror partner in the orbit — their mirror image is themselves — so the raw
            # off-axis offset (~1 µm in the ANSA data) would survive orbit averaging. Any
            # canonical point within 5 µm of a half-pitch symmetry axis is projected onto it.
            theta_c = math.atan2(canon[1], canon[0])
            j = round((theta_c - bisector) / (pitch / 2.0))
            axis = bisector + j * pitch / 2.0
            normal = np.array([-math.sin(axis), math.cos(axis)])
            off = float(canon @ normal)
            if abs(off) < 0.005:
                canon = canon - off * normal
        for i in members:
            moved = _apply_sym(canon[None, :], bisector, pitch, 0, mirror[i])
            out[i] = _apply_sym(moved, bisector, pitch, rot[i], False)[0]
    return out


def _boundary_loop(quads: list[Quad]) -> list[int]:
    """The single closed boundary loop of the sector slice, as an ordered node cycle."""
    edge_count, _ = _edges_and_neighbours(quads)
    step: dict[int, list[int]] = defaultdict(list)
    for edge, count in edge_count.items():
        if count == 1:
            a, b = tuple(edge)
            step[a].append(b)
            step[b].append(a)
    start = next(iter(step))
    loop = [start]
    prev: int | None = None
    while True:
        options = [n for n in step[loop[-1]] if n != prev]
        prev = loop[-1]
        loop.append(options[0])
        if loop[-1] == start:
            return loop[:-1]


def extract_template(
    quads: list[Quad], coords: dict[int, tuple[float, float]], part_name: str, z_teeth: int = 52
) -> SectorTemplate:
    """Classify boundary nodes and package the slice as a reusable sector template."""
    loop = _boundary_loop(quads)
    boundary = set(loop)
    radius = {n: math.hypot(*coords[n]) for n in coords}
    theta = {n: math.atan2(coords[n][1], coords[n][0]) for n in coords}
    bore_r = min(radius[n] for n in boundary)
    theta_lo = min(theta.values())
    theta_hi = max(theta.values())

    def classify(n: int) -> str:
        if n not in boundary:
            return "interior"
        if abs(theta[n] - theta_lo) < 1e-4 or abs(theta[n] - theta_hi) < 1e-4:
            return "cut"
        if abs(radius[n] - bore_r) < 1e-3:
            return "bore"
        return "surface"

    kind_by_id = {n: classify(n) for n in coords}

    # Outer contour = the loop portion between the two cut faces that is not the bore.
    # Rotate the loop so it starts right after a cut→surface transition.
    surface_run: list[int] = []
    n_loop = len(loop)
    for i in range(n_loop):
        prev_kind = kind_by_id[loop[i - 1]]
        if kind_by_id[loop[i]] == "surface" and prev_kind == "cut":
            j = i
            while kind_by_id[loop[j % n_loop]] == "surface":
                surface_run.append(loop[j % n_loop])
                j += 1
            break

    order = sorted(coords)
    index = {n: i for i, n in enumerate(order)}
    nodes = np.array([coords[n] for n in order], dtype=float)
    quad_idx = np.array(
        [[index[a], index[b], index[c], index[d]] for a, b, c, d in quads], dtype=np.int64
    )
    metrics = measure(quads, coords)
    fan_ring_r = float(np.mean([r for _, _, r, _ in metrics.irregular]))
    meta: dict[str, float | int | str] = {
        "part": part_name,
        "z_teeth": z_teeth,
        "fan_ring_radius_mm": round(fan_ring_r, 6),
        "bore_radius_mm": round(bore_r, 6),
        "theta_lo_rad": round(theta_lo, 9),
        "theta_hi_rad": round(theta_hi, 9),
        "surface_r_min_mm": round(min(radius[n] for n in surface_run), 6),
        "surface_r_max_mm": round(max(radius[n] for n in surface_run), 6),
        "rim_rings": metrics.rim_rings,
        "rim_cols": metrics.rim_cols,
        "n_quads": metrics.n_quads,
        "n_nodes": metrics.n_nodes,
    }
    # Canonicalize: exact tooth-to-tooth congruence + in-tooth mirror symmetry. The raw ANSA
    # sector is already rotation-exact (measured 0.0000 mm) and mirror-symmetric to 2.5 µm;
    # averaging the orbits makes both exact in the committed template.
    pitch = 2.0 * math.pi / z_teeth
    bisector = (theta_lo + theta_hi) / 2.0
    group, rot, mir = compute_canonical_map(nodes, bisector, pitch)
    kinds = [kind_by_id[n] for n in order]
    # Orbits must not mix node classes — except "cut": the cut faces lie on gap centre lines,
    # so cut nodes are legitimately congruent to interior/bore column nodes one pitch over.
    per_group: dict[int, set[str]] = defaultdict(set)
    for i, g in enumerate(group):
        if kinds[i] != "cut":
            per_group[g].add(kinds[i])
    mixed = {g: ks for g, ks in per_group.items() if len(ks) > 1}
    if mixed:
        raise ValueError(f"canonical orbits mix node kinds: {list(mixed.items())[:3]}")
    nodes = canonicalize_positions(nodes, group, rot, mir, bisector, pitch, use_mirror=True)
    return SectorTemplate(
        nodes=nodes,
        quads=quad_idx,
        kind=kinds,
        surface_order=[index[n] for n in surface_run],
        meta=meta,
        canon_group=group,
        canon_rot=rot,
        canon_mirror=mir,
    )


def load_reference_template(part_name: str = "Part_Rad_Vz_1") -> SectorTemplate:
    """The committed reference sector template (regenerate via 10_verifiers)."""
    slug = part_name.lower().replace("part_", "")
    path = Path(__file__).with_name("data") / f"reference_sector_{slug}.json"
    return SectorTemplate.from_json(path)
