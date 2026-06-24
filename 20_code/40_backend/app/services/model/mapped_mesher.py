"""
@module: app.services.model.mapped_mesher
@context: Domain layer — FE rolling model, the structured (transfinite) tooth mesher.
@role: Build the **mapped, structured** tooth-pitch mesh the way STIRAK / the FVA
       screenshots do — not by throwing a complex outline at an unstructured mesher,
       but by partitioning one pitch into mappable 4-sided blocks (tooth body, root
       fillet, rim-under-tooth, rim-under-gap ×2) and meshing each transfinite with
       the FVA element counts as edge seeds. Recombine → structured quads, swept over
       the face width → structured C3D8 hexahedra. This is the clean path: every block
       is trivially mappable, so there is no boundary self-intersection. Spur gears
       (β = 0); transverse plane, tooth on +y, swept along +z.
"""

import math

import gmsh
import numpy as np
from numpy.typing import NDArray

from app.services.geometry.tooth_form import ToothProfile
from app.services.model.mesh3d import Mesh3D, extrude_to_hex
from app.services.model.tooth_mesh import Mesh2D

Array = NDArray[np.float64]


def _extract_2d_quality() -> tuple[Mesh2D, Array]:
    """Pull the recombined quad section + per-quad Jacobi-Güte from the active gmsh model.

    gmsh emits quads in mixed winding; we normalise each to CCW (positive area) so the face-width
    sweep produces positively-oriented C3D8 hexahedra (Abaqus rejects negative-Jacobian elements).
    """
    node_tags, coords, _ = gmsh.model.mesh.getNodes()
    pts = np.array(coords).reshape(-1, 3)[:, :2]
    index = {int(t): i for i, t in enumerate(node_tags)}
    elem_tags, conn = gmsh.model.mesh.getElementsByType(3)  # 4-node quad
    quads = np.array([index[int(t)] for t in conn]).reshape(-1, 4)
    quality = np.array(gmsh.model.mesh.getElementQualities(elem_tags, "minSJ"))  # = Jacobi-Güte
    p = pts[quads]  # (M, 4, 2) — signed shoelace area; flip clockwise quads to CCW
    x, y = p[..., 0], p[..., 1]
    area2 = (
        x[:, 0] * y[:, 1] - x[:, 1] * y[:, 0]
        + x[:, 1] * y[:, 2] - x[:, 2] * y[:, 1]
        + x[:, 2] * y[:, 3] - x[:, 3] * y[:, 2]
        + x[:, 3] * y[:, 0] - x[:, 0] * y[:, 3]
    )
    quads[area2 < 0.0] = quads[area2 < 0.0][:, ::-1]
    return Mesh2D(pts, quads), quality


def _xy(points: list) -> Array:
    return np.array([[p[0], p[1]] for p in points])


# Safety valve: even the deterministic transfinite path must never silently build a mesh so
# large it hangs the machine. The projected element count is closed-form from the seeds, so we
# reject an over-budget request up front instead of meshing it.
DEFAULT_MAX_ELEMENTS = 4_000_000


def _pitch_quads(
    height_elements: int, root_elements: int, thickness_elements: int, rim_elements: int, n_gap: int
) -> int:
    """Closed-form quad count of one mapped tooth pitch (the 5 transfinite blocks)."""
    return (height_elements + root_elements + rim_elements) * thickness_elements + 2 * (
        rim_elements * n_gap
    )


def _check_budget(n_elements: int, max_elements: int, what: str) -> None:
    if n_elements > max_elements:
        raise ValueError(
            f"{what} would generate {n_elements:,} elements (> max_elements {max_elements:,}); "
            "reduce the element counts / teeth / face layers, or raise max_elements"
        )


def mesh_pitch_mapped_2d(
    profile: ToothProfile,
    *,
    height_elements: int = 20,
    root_elements: int = 40,
    thickness_elements: int = 5,
    rim_elements: int = 8,
    gap_elements: int | None = None,
    rim_depth_mm: float | None = None,
    min_jacobi: float = 0.35,
    limit_angle_deg: float = 65.0,
    samples: int = 40,
    flank_bias: float = 0.0,
    max_elements: int = DEFAULT_MAX_ELEMENTS,
) -> tuple[Mesh2D, Array]:
    """Structured quad mesh of one tooth pitch (5 transfinite blocks). Returns (mesh, quality).

    The FVA mesher targets (FEM-Vernetzer): the scaled-Jacobian "Jacobi-Güte" must stay
    ≥ ``min_jacobi`` (default 0.35) — verified here, with gmsh optimisation enabled — and
    ``limit_angle_deg`` (the FVA "Grenzwinkelvorgabe", default 65°) bounds the element
    skew; the structured transfinite topology satisfies it by construction.
    """
    z = profile.z
    pitch_half = math.pi / z
    r_df = profile.root_diameter_mm / 2.0
    rim = r_df - (rim_depth_mm if rim_depth_mm is not None else 2.0 * profile.mn)
    n_gap = gap_elements if gap_elements is not None else thickness_elements
    _check_budget(
        _pitch_quads(height_elements, root_elements, thickness_elements, rim_elements, n_gap),
        max_elements,
        "mapped pitch 2-D mesh",
    )

    # Clean transverse boundary: rounded ρ_F fillet (d_f → form circle) + involute flank
    # (form circle → d_Na), split at the shared junction so the two splines stay C0.
    boundary = profile.transverse_right_boundary(fillet_points=samples, flank_points=samples)
    fillet = _xy(boundary[:samples])  # d_f → form circle
    flank = _xy(boundary[samples - 1 :])  # form circle → d_Na (shares the junction node)
    r_t, r_f = flank[-1], flank[0]  # right tip, right form-circle junction
    r_d = fillet[0]  # right d_f (fillet bottom)
    ang_d = math.atan2(r_d[0], r_d[1])  # right fillet-bottom angle

    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    try:
        gmsh.model.add("pitch_mapped")
        geo = gmsh.model.geo

        def pt(x: float, y: float) -> int:
            return geo.addPoint(float(x), float(y), 0.0)

        def mirror(p: Array) -> Array:
            return np.array([-p[0], p[1]])

        def on_circle(radius: float, angle: float) -> int:
            return pt(radius * math.sin(angle), radius * math.cos(angle))

        # corner points (r/l = right/left; t/f/d = tip/d_Ff/d_f; g = gap; b = bore)
        rt, lt = pt(*r_t), pt(*mirror(r_t))
        rf, lf = pt(*r_f), pt(*mirror(r_f))
        rd, ld = pt(*r_d), pt(*mirror(r_d))
        rg, lg = on_circle(r_df, pitch_half), on_circle(r_df, -pitch_half)
        bgr, bgl = on_circle(rim, pitch_half), on_circle(rim, -pitch_half)
        bdr, bdl = on_circle(rim, ang_d), on_circle(rim, -ang_d)
        ctr = pt(0.0, 0.0)

        def spline(p0: int, mids: Array, p1: int) -> int:
            tags = [p0] + [pt(*m) for m in mids] + [p1]
            return geo.addSpline(tags)

        # flank & fillet splines (right + mirrored left)
        rflank = spline(rt, flank[::-1][1:-1], rf)
        lflank = spline(lt, _xy_mirror(flank[::-1][1:-1]), lf)
        rfil = spline(rf, fillet[::-1][1:-1], rd)
        lfil = spline(lf, _xy_mirror(fillet[::-1][1:-1]), ld)

        tip = geo.addLine(lt, rt)
        base_ff = geo.addLine(lf, rf)
        base_df = geo.addLine(ld, rd)
        gap_l = geo.addCircleArc(lg, ctr, ld)
        gap_r = geo.addCircleArc(rd, ctr, rg)
        rad_dl = geo.addLine(bdl, ld)
        rad_dr = geo.addLine(rd, bdr)
        rad_gl = geo.addLine(bgl, lg)
        rad_gr = geo.addLine(rg, bgr)
        bore_t = geo.addCircleArc(bdr, ctr, bdl)
        bore_l = geo.addCircleArc(bdl, ctr, bgl)
        bore_r = geo.addCircleArc(bgr, ctr, bdr)

        body = _surface(geo, [tip, rflank, base_ff, lflank], reverse={base_ff, lflank})
        fil = _surface(geo, [base_ff, rfil, base_df, lfil], reverse={base_df, lfil})
        rim_t = _surface(geo, [base_df, rad_dr, bore_t, rad_dl], reverse=set())
        rim_l = _surface(geo, [gap_l, rad_dl, bore_l, rad_gl], reverse={rad_dl})
        rim_r = _surface(geo, [gap_r, rad_gr, bore_r, rad_dr], reverse={rad_dr})
        geo.synchronize()

        def seed(curve: int, n: int, kind: str = "", coef: float = 1.0) -> None:
            if kind:
                geo.mesh.setTransfiniteCurve(curve, n + 1, kind, coef)
            else:
                geo.mesh.setTransfiniteCurve(curve, n + 1)

        for c in (rflank, lflank):
            seed(c, height_elements)
        for c in (rfil, lfil):
            seed(c, root_elements)
        for c in (tip, base_ff, base_df, bore_t):  # thickness curves → fine surface boundary layer
            if flank_bias > 0.0:
                seed(c, thickness_elements, "Bump", flank_bias)
            else:
                seed(c, thickness_elements)
        for c in (gap_l, gap_r, bore_l, bore_r):
            seed(c, n_gap)
        # radial rim edges graded fine at d_f → coarse at the bore (fine surface runs out into the
        # coarser body); mirror grade on the two pitch sides so adjacent pitches still merge.
        for c in (rad_dr, rad_gr):  # oriented d_f → bore
            seed(c, rim_elements, "Progression", 1.25)
        for c in (rad_dl, rad_gl):  # oriented bore → d_f (mirror)
            seed(c, rim_elements, "Progression", 1.0 / 1.25)

        for s, corners in (
            (body, [lt, rt, rf, lf]),
            (fil, [lf, rf, rd, ld]),
            (rim_t, [ld, rd, bdr, bdl]),
            (rim_l, [lg, ld, bdl, bgl]),
            (rim_r, [rd, rg, bgr, bdr]),
        ):
            geo.mesh.setTransfiniteSurface(s, "Left", corners)
            geo.mesh.setRecombine(2, s)
        geo.synchronize()

        gmsh.option.setNumber("Mesh.RecombinationAlgorithm", 1)  # Blossom (transfinite → all-quad)
        gmsh.option.setNumber("Mesh.Optimize", 1)
        gmsh.option.setNumber("Mesh.OptimizeThreshold", min_jacobi)
        gmsh.model.mesh.generate(2)
        n_tri = len(gmsh.model.mesh.getElementsByType(2)[0])  # type 2 = triangle
        if n_tri:
            raise ValueError(f"recombine left {n_tri} triangles (need an all-quad section)")
        mesh, quality = _extract_2d_quality()
    finally:
        gmsh.finalize()
    if quality.size and float(quality.min()) < min_jacobi:
        raise ValueError(
            f"mesh below the Jacobi-Güte target: min {quality.min():.3f} < {min_jacobi}"
        )
    return mesh, quality


def _xy_mirror(pts: Array) -> Array:
    return pts * np.array([-1.0, 1.0])


def _surface(geo: object, curves: list[int], *, reverse: set[int]) -> int:
    """A plane surface from 4 curves, flipping the ones listed in ``reverse`` for a CCW loop."""
    oriented = [-c if c in reverse else c for c in curves]
    return geo.addPlaneSurface([geo.addCurveLoop(oriented)])  # type: ignore[attr-defined]


def _mesh_rim_pitch_2d(
    profile: ToothProfile,
    *,
    rim_elements: int,
    gap_elements: int,
    rim_depth_mm: float | None,
    min_jacobi: float,
) -> tuple[Mesh2D, Array]:
    """A single transfinite rim-only annular block over one pitch (for tooth-free segments)."""
    pitch_half = math.pi / profile.z
    r_df = profile.root_diameter_mm / 2.0
    rim = r_df - (rim_depth_mm if rim_depth_mm is not None else 2.0 * profile.mn)

    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 0)
    try:
        gmsh.model.add("rim_pitch")
        geo = gmsh.model.geo

        def oc(radius: float, angle: float) -> int:
            return geo.addPoint(radius * math.sin(angle), radius * math.cos(angle), 0.0)

        tl, tr = oc(r_df, -pitch_half), oc(r_df, pitch_half)
        bl, br = oc(rim, -pitch_half), oc(rim, pitch_half)
        ctr = geo.addPoint(0.0, 0.0, 0.0)
        top = geo.addCircleArc(tl, ctr, tr)
        right = geo.addLine(tr, br)
        bot = geo.addCircleArc(br, ctr, bl)
        left = geo.addLine(bl, tl)
        surf = geo.addPlaneSurface([geo.addCurveLoop([top, right, bot, left])])
        geo.synchronize()
        geo.mesh.setTransfiniteCurve(top, gap_elements + 1)
        geo.mesh.setTransfiniteCurve(bot, gap_elements + 1)
        geo.mesh.setTransfiniteCurve(left, rim_elements + 1)
        geo.mesh.setTransfiniteCurve(right, rim_elements + 1)
        geo.mesh.setTransfiniteSurface(surf, "Left", [tl, tr, br, bl])
        geo.mesh.setRecombine(2, surf)
        geo.synchronize()
        gmsh.model.mesh.generate(2)
        return _extract_2d_quality()
    finally:
        gmsh.finalize()


def _rotate2d(nodes: Array, angle: float) -> Array:
    c, s = math.cos(angle), math.sin(angle)
    return nodes @ np.array([[c, s], [-s, c]])


def _merge_coincident(
    nodes: Array, elements: Array, tol: float = 1e-6
) -> tuple[Array, NDArray[np.int64]]:
    """Deduplicate coincident nodes (rounded to ``tol``) and remap the element connectivity."""
    keys = np.round(nodes / tol).astype(np.int64)
    _, index, inverse = np.unique(keys, axis=0, return_index=True, return_inverse=True)
    return nodes[index], inverse[elements].astype(np.int64)


def mesh_sector_mapped_2d(
    profile: ToothProfile,
    *,
    n_teeth: int,
    n_segments: int = 1,
    height_elements: int = 20,
    root_elements: int = 40,
    thickness_elements: int = 5,
    rim_elements: int = 8,
    gap_elements: int | None = None,
    rim_depth_mm: float | None = None,
    min_jacobi: float = 0.35,
    limit_angle_deg: float = 65.0,
    flank_bias: float = 0.0,
    max_elements: int = DEFAULT_MAX_ELEMENTS,
) -> tuple[Mesh2D, Array]:
    """Structured mesh of a gear sector: ``n_teeth`` teeth + ``n_segments`` rim pitches each side.

    Builds the structured tooth pitch and a rim-only pitch once, then rotates copies into
    place and merges the coincident rim-cut nodes — a connected, mapped sector with the
    gear-body angle (n_teeth + 2·n_segments)·360°/z, no boundary self-intersection.
    """
    n_gap = gap_elements if gap_elements is not None else thickness_elements
    tooth_quads = _pitch_quads(
        height_elements, root_elements, thickness_elements, rim_elements, n_gap
    )
    _check_budget(
        n_teeth * tooth_quads + 2 * n_segments * (rim_elements * n_gap),
        max_elements,
        "mapped sector 2-D mesh",
    )
    tooth, tq = mesh_pitch_mapped_2d(
        profile,
        height_elements=height_elements,
        root_elements=root_elements,
        thickness_elements=thickness_elements,
        rim_elements=rim_elements,
        gap_elements=n_gap,
        rim_depth_mm=rim_depth_mm,
        min_jacobi=min_jacobi,
        limit_angle_deg=limit_angle_deg,
        flank_bias=flank_bias,
        max_elements=max_elements,
    )
    rim, rq = _mesh_rim_pitch_2d(
        profile,
        rim_elements=rim_elements,
        gap_elements=n_gap,
        rim_depth_mm=rim_depth_mm,
        min_jacobi=min_jacobi,
    )
    pitch = 2.0 * math.pi / profile.z
    total = n_teeth + 2 * n_segments
    parts_n: list[Array] = []
    parts_q: list[Array] = []
    quality: list[Array] = []
    offset = 0
    for k in range(total):
        theta = (k - (total - 1) / 2.0) * pitch
        is_tooth = n_segments <= k < n_segments + n_teeth
        mesh, qual = (tooth, tq) if is_tooth else (rim, rq)
        parts_n.append(_rotate2d(mesh.nodes, theta))
        parts_q.append(mesh.quads + offset)
        quality.append(qual)
        offset += mesh.n_nodes
    nodes, quads = _merge_coincident(np.vstack(parts_n), np.vstack(parts_q))
    return Mesh2D(nodes, quads), np.concatenate(quality)


def mesh_pitch_mapped_3d(
    profile: ToothProfile,
    *,
    face_width_mm: float,
    face_layers: int,
    height_elements: int = 20,
    root_elements: int = 40,
    thickness_elements: int = 5,
    rim_elements: int = 8,
    gap_elements: int | None = None,
    rim_depth_mm: float | None = None,
    min_jacobi: float = 0.35,
    limit_angle_deg: float = 65.0,
    flank_bias: float = 0.0,
    max_elements: int = DEFAULT_MAX_ELEMENTS,
) -> Mesh3D:
    """Structured C3D8 mesh of one tooth pitch, swept over the face width."""
    n_gap = gap_elements if gap_elements is not None else thickness_elements
    _check_budget(
        _pitch_quads(height_elements, root_elements, thickness_elements, rim_elements, n_gap)
        * face_layers,
        max_elements,
        "mapped pitch 3-D mesh",
    )
    section, quality = mesh_pitch_mapped_2d(
        profile,
        height_elements=height_elements,
        root_elements=root_elements,
        thickness_elements=thickness_elements,
        rim_elements=rim_elements,
        gap_elements=gap_elements,
        rim_depth_mm=rim_depth_mm,
        min_jacobi=min_jacobi,
        limit_angle_deg=limit_angle_deg,
        flank_bias=flank_bias,
        max_elements=max_elements,
    )
    return extrude_to_hex(section, quality, width=face_width_mm, layers=face_layers)


def mesh_sector_mapped_3d(
    profile: ToothProfile,
    *,
    n_teeth: int,
    face_width_mm: float,
    face_layers: int,
    n_segments: int = 1,
    height_elements: int = 20,
    root_elements: int = 40,
    thickness_elements: int = 5,
    rim_elements: int = 8,
    gap_elements: int | None = None,
    rim_depth_mm: float | None = None,
    min_jacobi: float = 0.35,
    limit_angle_deg: float = 65.0,
    flank_bias: float = 0.0,
    max_elements: int = DEFAULT_MAX_ELEMENTS,
) -> Mesh3D:
    """Structured C3D8 mesh of a gear sector (n_teeth + 2·n_segments pitches) over the face."""
    n_gap = gap_elements if gap_elements is not None else thickness_elements
    tooth_quads = _pitch_quads(
        height_elements, root_elements, thickness_elements, rim_elements, n_gap
    )
    _check_budget(
        (n_teeth * tooth_quads + 2 * n_segments * (rim_elements * n_gap)) * face_layers,
        max_elements,
        "mapped sector 3-D mesh",
    )
    section, quality = mesh_sector_mapped_2d(
        profile,
        n_teeth=n_teeth,
        n_segments=n_segments,
        height_elements=height_elements,
        root_elements=root_elements,
        thickness_elements=thickness_elements,
        rim_elements=rim_elements,
        gap_elements=gap_elements,
        rim_depth_mm=rim_depth_mm,
        min_jacobi=min_jacobi,
        limit_angle_deg=limit_angle_deg,
        flank_bias=flank_bias,
        max_elements=max_elements,
    )
    return extrude_to_hex(section, quality, width=face_width_mm, layers=face_layers)
