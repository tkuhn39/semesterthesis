"""
@module: app.services.model.structured_mesher
@context: Domain layer — FE rolling model, the native structured (mapped) gear-sector mesher.
@role: Build the gear-sector quad mesh directly from the clean transverse boundary
       (`tooth_form.transverse_right_boundary`) — no gmsh, fully deterministic. One pitch =
       a **tooth column** on constant-radius arcs between the exact (mirrored) involute+ρ_F-fillet
       flanks, sitting on a **deep structured rim ring** that reaches the real bore. N pitches are
       rotated and merged into the sector, then swept over the face width to C3D8(R). The FVA
       "Jacobi-Güte" (scaled Jacobian) is computed and enforced (≥ min, default 0.35). Spur gears
       (β = 0); transverse plane, tooth on +y, swept along +z.
"""

import math

import numpy as np
from numpy.typing import NDArray

from app.services.geometry.tooth_form import ToothProfile
from app.services.model.mesh3d import Mesh3D, extrude_to_hex
from app.services.model.tooth_mesh import Mesh2D

Array = NDArray[np.float64]
IntArray = NDArray[np.int64]
DEFAULT_MAX_ELEMENTS = 4_000_000


def scaled_jacobian(mesh: Mesh2D) -> Array:
    """Per-quad scaled Jacobian (the FVA Jacobi-Güte): min over corners of sin(corner angle).

    1.0 is a rectangle; the FVA mesher target is ≥ 0.35. Assumes CCW quads (positive area).
    """
    p = mesh.nodes[mesh.quads]  # (M, 4, 2)
    sj = np.ones(p.shape[0])
    for c in range(4):
        prev, cur, nxt = p[:, (c - 1) % 4], p[:, c], p[:, (c + 1) % 4]
        e1, e2 = nxt - cur, prev - cur
        cross = e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0]
        norm = np.hypot(e1[:, 0], e1[:, 1]) * np.hypot(e2[:, 0], e2[:, 1])
        sj = np.minimum(sj, cross / np.maximum(norm, 1e-30))
    return sj


def _grid_quads(n_rows: int, n_cols: int) -> IntArray:
    """CCW quad connectivity for an ``(n_rows+1) × (n_cols+1)`` row-major node grid."""

    def idx(i: int, j: int) -> int:
        return i * (n_cols + 1) + j

    return np.array(
        [
            [idx(i, j), idx(i, j + 1), idx(i + 1, j + 1), idx(i + 1, j)]
            for i in range(n_rows)
            for j in range(n_cols)
        ],
        dtype=np.int64,
    )


def _ccw(mesh: Mesh2D) -> Mesh2D:
    """Flip quad winding if the mesh came out clockwise (keep positive/CCW area)."""
    if float(mesh.element_areas().mean()) < 0.0:
        mesh.quads = mesh.quads[:, ::-1]
    return mesh


def tooth_column_2d(
    profile: ToothProfile,
    *,
    height_elements: int = 20,
    root_elements: int = 14,
    thickness_elements: int = 6,
    samples: int = 400,
) -> tuple[Mesh2D, float]:
    """Structured quad mesh of one tooth column d_f → d_Na. Returns (mesh, root half-angle θ_df).

    A transfinite (Coons) patch between the two mirrored clean boundaries (involute flank + rounded
    ρ_F root fillet) and the root/tip edges — this follows the fillet curvature smoothly (constant-
    radius arcs skew there). The rows are uniform within the fillet (``root_elements`` over d_f →
    d_Ff, the critical section) and within the flank (``height_elements`` over d_Ff → d_Na), so the
    root is refined without degenerate cells. The bottom row sits on d_f and is what the rim meets.
    """
    boundary = profile.transverse_right_boundary(fillet_points=samples, flank_points=samples)
    pts = np.array([[p[0], p[1]] for p in boundary])
    r = np.hypot(pts[:, 0], pts[:, 1])
    n_v, n_u = root_elements + height_elements, thickness_elements
    r_ff = min(max(profile.d_Ff / 2.0, r[0] + 1e-6), r[-1] - 1e-6)  # fillet/flank split radius
    r_lvl = np.concatenate(
        [
            np.linspace(r[0], r_ff, root_elements + 1),  # fillet rows (critical root section)
            np.linspace(r_ff, r[-1], height_elements + 1)[1:],  # flank rows (skip shared junction)
        ]
    )
    right = np.column_stack([np.interp(r_lvl, r, pts[:, 0]), np.interp(r_lvl, r, pts[:, 1])])
    left = right * np.array([-1.0, 1.0])  # mirror flank
    th_df, th_tip = math.atan2(right[0, 0], right[0, 1]), math.atan2(right[-1, 0], right[-1, 1])
    c00, c10, c01, c11 = left[0], right[0], left[-1], right[-1]
    uu = np.linspace(0.0, 1.0, n_u + 1)
    a_b, a_t = -th_df + uu * 2.0 * th_df, -th_tip + uu * 2.0 * th_tip
    bottom = np.column_stack([r_lvl[0] * np.sin(a_b), r_lvl[0] * np.cos(a_b)])  # root edge at d_f
    top = np.column_stack([r_lvl[-1] * np.sin(a_t), r_lvl[-1] * np.cos(a_t)])  # tip edge at d_Na
    nodes = np.empty(((n_v + 1) * (n_u + 1), 2))
    for i in range(n_v + 1):
        v = i / n_v
        for j in range(n_u + 1):
            u = j / n_u
            ruled = (1.0 - u) * left[i] + u * right[i] + (1.0 - v) * bottom[j] + v * top[j]
            corners = (
                (1.0 - u) * (1.0 - v) * c00
                + u * (1.0 - v) * c10
                + (1.0 - u) * v * c01
                + u * v * c11
            )
            nodes[i * (n_u + 1) + j] = ruled - corners
    return _ccw(Mesh2D(nodes, _grid_quads(n_v, n_u))), float(th_df)


def rim_ring_2d(
    profile: ToothProfile,
    *,
    bore_radius_mm: float,
    tooth_half_angle: float,
    rim_elements: int = 10,
    thickness_elements: int = 6,
    gap_elements: int = 3,
) -> Mesh2D:
    """Structured annular rim block over one pitch, bore → d_f.

    The top row (at d_f) carries the tooth-bottom nodes in its centre (``thickness_elements`` cells
    across ±``tooth_half_angle``) and ``gap_elements`` cells each side out to the half pitch (the
    gap floor); the bottom row (bore) is evenly spaced over the full pitch. Rows interpolate so the
    top-centre nodes coincide with the tooth column's bottom row for a clean merge.
    """
    pitch_half = math.pi / profile.z
    r_df = profile.root_diameter_mm / 2.0
    left = np.linspace(-pitch_half, -tooth_half_angle, gap_elements + 1)
    centre = np.linspace(-tooth_half_angle, tooth_half_angle, thickness_elements + 1)
    right = np.linspace(tooth_half_angle, pitch_half, gap_elements + 1)
    top_ang = np.concatenate([left[:-1], centre, right[1:]])
    n_col = top_ang.size - 1
    bot_ang = np.linspace(-pitch_half, pitch_half, top_ang.size)
    radii = np.linspace(bore_radius_mm, r_df, rim_elements + 1)
    nodes = np.empty(((rim_elements + 1) * top_ang.size, 2))
    for i in range(rim_elements + 1):
        frac = i / rim_elements
        ang = (1.0 - frac) * bot_ang + frac * top_ang
        nodes[i * top_ang.size : (i + 1) * top_ang.size] = np.column_stack(
            [radii[i] * np.sin(ang), radii[i] * np.cos(ang)]
        )
    return _ccw(Mesh2D(nodes, _grid_quads(rim_elements, n_col)))


def _rotate(nodes: Array, angle: float) -> Array:
    c, s = math.cos(angle), math.sin(angle)
    return nodes @ np.array([[c, s], [-s, c]])


def _merge(nodes: Array, quads: IntArray, tol: float = 1e-6) -> tuple[Array, IntArray]:
    """Deduplicate coincident nodes (rounded to ``tol``) and remap the quad connectivity."""
    keys = np.round(nodes / tol).astype(np.int64)
    _, index, inverse = np.unique(keys, axis=0, return_index=True, return_inverse=True)
    return nodes[index], inverse[quads.reshape(-1)].reshape(quads.shape).astype(np.int64)


def _laplacian_smooth(
    nodes: Array, quads: IntArray, fixed: set[int], iters: int = 40
) -> Array:
    """Laplacian smoothing: move every non-``fixed`` node to its edge-neighbour centroid.

    Lifts the quality of the raw coarsening-fan cells (the transfinite tooth is already smoothed by
    gmsh; the native body is not). Boundary nodes — the d_f interface, the bore and the pitch
    sides — stay fixed, so conformity and the sector merge are preserved.
    """
    pts = np.asarray(nodes, dtype=float).copy()
    nbr: list[set[int]] = [set() for _ in range(len(pts))]
    for q in quads:
        for k in range(4):
            a, b = int(q[k]), int(q[(k + 1) % 4])
            nbr[a].add(b)
            nbr[b].add(a)
    free = [(i, np.fromiter(nbr[i], int)) for i in range(len(pts)) if i not in fixed and nbr[i]]
    for _ in range(iters):
        for i, neigh in free:
            pts[i] = pts[neigh].mean(axis=0)
    return pts


def _angles(top_idx: list[int], nodes: list[list[float]]) -> tuple[list[float], float]:
    """Half-angles (from +y) of `top_idx` nodes and their mean radius."""
    ang = [math.atan2(nodes[i][0], nodes[i][1]) for i in top_idx]
    r = float(np.mean([math.hypot(nodes[i][0], nodes[i][1]) for i in top_idx]))
    return ang, r


def _coarsen_band(
    top_idx: list[int], nodes: list[list[float]], r_bot: float
) -> tuple[list[list[int]], list[int]]:
    """One annular all-quad 4→2 coarsening band: N top columns → N/2 bottom columns (N % 4 == 0).

    Uses the validated 6-quad / 3-interior-node template per 4→2 unit. Appends bottom + interior
    nodes to ``nodes`` (radii r_bot and mid); returns (quads, bottom_idx) with N/2+1 bottom nodes.
    """
    n = len(top_idx) - 1
    ang, r_top = _angles(top_idx, nodes)
    r_mid = 0.5 * (r_top + r_bot)

    def add(radius: float, a: float) -> int:
        nodes.append([radius * math.sin(a), radius * math.cos(a)])
        return len(nodes) - 1

    bottom = [add(r_bot, ang[2 * j]) for j in range(n // 2 + 1)]  # every other top angle
    quads: list[list[int]] = []
    for u in range(n // 4):
        t = top_idx[4 * u : 4 * u + 5]
        b0, b1, b2 = bottom[2 * u], bottom[2 * u + 1], bottom[2 * u + 2]
        i0 = add(r_mid, ang[4 * u + 1])
        ic = add(r_mid, ang[4 * u + 2])
        i1 = add(r_mid, ang[4 * u + 3])
        quads += [
            [t[0], t[1], i0, b0],
            [t[1], t[2], ic, i0],
            [t[2], t[3], i1, ic],
            [t[3], t[4], b2, i1],
            [b0, i0, ic, b1],
            [b1, ic, i1, b2],
        ]
    return quads, bottom


def _ring_band(
    top_idx: list[int], nodes: list[list[float]], r_bot: float, rows: int, grade: float
) -> tuple[list[list[int]], list[int]]:
    """Transfinite annular ring: sweep ``top_idx`` columns radially to r_bot over ``rows`` rows,
    graded (element size grows ~``grade``× per row toward the bore). Returns (quads, bottom_idx)."""
    n = len(top_idx) - 1
    ang, r_top = _angles(top_idx, nodes)
    w = np.cumsum([grade**k for k in range(rows)])
    radii = [r_top] + [r_top + (r_bot - r_top) * float(wi / w[-1]) for wi in w]
    quads: list[list[int]] = []
    prev = list(top_idx)
    for row in range(1, rows + 1):
        rr = radii[row]
        cur = []
        for a in ang:
            nodes.append([rr * math.sin(a), rr * math.cos(a)])
            cur.append(len(nodes) - 1)
        quads += [[prev[c], prev[c + 1], cur[c + 1], cur[c]] for c in range(n)]
        prev = cur
    return quads, prev


def body_section_2d(
    profile: ToothProfile,
    base_xy: Array,
    *,
    bore_radius_mm: float,
    n_gap: int = 1,
    bore_columns: int = 4,
    rim_rows: int = 8,
    band_aspect: float = 1.5,
    rim_grade: float = 1.2,
) -> tuple[Mesh2D, list[int]]:
    """All-quad gear-body section for one pitch, grown from the tooth base interface ``base_xy``.

    The top row at d_f = gap-floor (``n_gap`` cells each side) + the tooth base; it coarsens
    circumferentially via compact 4→2 bands (the reference fan, each band ≈ ``band_aspect`` × the
    local column width so the fan cells stay near-square) down to ``bore_columns``, then a graded
    transfinite ring carries it to the bore. Requires ``len(base_xy)-1 + 2*n_gap`` divisible by 4.
    Returns (mesh, bore node indices).
    """
    pitch = 2.0 * math.pi / profile.z
    pitch_half = pitch / 2.0
    r_df = profile.root_diameter_mm / 2.0
    nodes: list[list[float]] = [[float(x), float(y)] for x, y in base_xy]
    base_idx = list(range(len(base_xy)))
    th_l = math.atan2(base_xy[0][0], base_xy[0][1])
    th_r = math.atan2(base_xy[-1][0], base_xy[-1][1])

    def gap(a: float) -> int:
        nodes.append([r_df * math.sin(a), r_df * math.cos(a)])
        return len(nodes) - 1

    left = [gap(a) for a in np.linspace(-pitch_half, th_l, n_gap + 1)[:-1]]
    right = [gap(a) for a in np.linspace(th_r, pitch_half, n_gap + 1)[1:]]
    top_idx = left + base_idx + right
    interface = list(top_idx)  # the d_f row stays fixed (shared with the tooth)
    if (len(top_idx) - 1) % 4 != 0:
        raise ValueError(f"body top columns {len(top_idx) - 1} (thickness + 2·n_gap) must be ÷ 4")

    quads: list[list[int]] = []
    r = r_df
    while (len(top_idx) - 1) // 2 >= bore_columns and (len(top_idx) - 1) % 4 == 0:
        n_cols = len(top_idx) - 1
        height = band_aspect * pitch * r / n_cols  # band ≈ square fan cells (compact near the root)
        r = max(r - height, bore_radius_mm + 0.05 * (r_df - bore_radius_mm))
        q, top_idx = _coarsen_band(top_idx, nodes, r)
        quads += q
    q, bore_idx = _ring_band(top_idx, nodes, bore_radius_mm, rim_rows, rim_grade)
    quads += q

    pts = np.array(nodes, float)
    ang_all = np.abs(np.arctan2(pts[:, 0], pts[:, 1]))
    side = {int(i) for i in np.where(np.abs(ang_all - pitch_half) < 1e-4)[0]}
    fixed = set(interface) | set(bore_idx) | side  # smooth only the true body interior
    quad_arr = np.array(quads, dtype=np.int64)
    mesh = _ccw(Mesh2D(_laplacian_smooth(pts, quad_arr, fixed), quad_arr))
    return mesh, bore_idx


def sector_2d(
    profile: ToothProfile,
    *,
    n_teeth: int,
    bore_radius_mm: float,
    height_elements: int = 20,
    root_elements: int = 14,
    thickness_elements: int = 6,
    rim_elements: int = 10,
    gap_elements: int = 3,
    min_jacobi: float = 0.35,
    max_elements: int = DEFAULT_MAX_ELEMENTS,
) -> tuple[Mesh2D, Array]:
    """Structured quad mesh of an ``n_teeth`` gear sector (tooth columns on a deep rim ring).

    Builds one pitch (tooth + rim) once, rotates it into the ``n_teeth`` positions and merges the
    shared radial-cut nodes. Returns (mesh, per-quad scaled Jacobian); raises if the Jacobi-Güte
    falls below ``min_jacobi`` or the element budget is exceeded.
    """
    tooth, theta_df = tooth_column_2d(
        profile,
        height_elements=height_elements,
        root_elements=root_elements,
        thickness_elements=thickness_elements,
    )
    rim = rim_ring_2d(
        profile,
        bore_radius_mm=bore_radius_mm,
        tooth_half_angle=theta_df,
        rim_elements=rim_elements,
        thickness_elements=thickness_elements,
        gap_elements=gap_elements,
    )
    pitch_n = np.vstack([tooth.nodes, rim.nodes])
    pitch_q = np.vstack([tooth.quads, rim.quads + tooth.n_nodes])
    pitch_nodes, pitch_quads = _merge(pitch_n, pitch_q)  # fuse tooth bottom ↔ rim top centre
    n_quads_pitch = pitch_quads.shape[0]
    if n_quads_pitch * n_teeth > max_elements:
        raise ValueError(
            f"sector would generate {n_quads_pitch * n_teeth:,} quads (> {max_elements:,})"
        )

    pitch = 2.0 * math.pi / profile.z
    parts_n: list[Array] = []
    parts_q: list[IntArray] = []
    for k in range(n_teeth):
        theta = (k - (n_teeth - 1) / 2.0) * pitch
        parts_n.append(_rotate(pitch_nodes, theta))
        parts_q.append(pitch_quads + k * pitch_nodes.shape[0])
    nodes, quads = _merge(np.vstack(parts_n), np.vstack(parts_q))  # fuse shared radial-cut edges
    mesh = _ccw(Mesh2D(nodes, quads))
    quality = scaled_jacobian(mesh)
    if quality.size and float(quality.min()) < min_jacobi:
        raise ValueError(
            f"mesh below the Jacobi-Güte target: min {quality.min():.3f} < {min_jacobi}"
        )
    return mesh, quality


def sector_3d(
    profile: ToothProfile,
    *,
    n_teeth: int,
    bore_radius_mm: float,
    face_width_mm: float,
    face_layers: int,
    z_center: bool = True,
    height_elements: int = 20,
    root_elements: int = 14,
    thickness_elements: int = 6,
    rim_elements: int = 10,
    gap_elements: int = 3,
    min_jacobi: float = 0.35,
    max_elements: int = DEFAULT_MAX_ELEMENTS,
) -> Mesh3D:
    """Structured C3D8 mesh of an ``n_teeth`` gear sector swept over the face width.

    ``z_center`` places the sweep symmetric about z = 0 (z ∈ [−b/2, +b/2], as the reference), else
    z ∈ [0, b]. The hex Jacobi-Güte equals the section's (orthogonal sweep), tiled over the layers.
    """
    section, quality = sector_2d(
        profile,
        n_teeth=n_teeth,
        bore_radius_mm=bore_radius_mm,
        height_elements=height_elements,
        root_elements=root_elements,
        thickness_elements=thickness_elements,
        rim_elements=rim_elements,
        gap_elements=gap_elements,
        min_jacobi=min_jacobi,
        max_elements=max_elements // max(face_layers, 1),
    )
    mesh = extrude_to_hex(section, quality, width=face_width_mm, layers=face_layers)
    if z_center:
        mesh.nodes[:, 2] -= face_width_mm / 2.0
    return mesh
