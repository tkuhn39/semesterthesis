"""
@module: app.services.model.template_mesher
@context: Domain layer — FE rolling model, reference-topology gear-sector mesher (ADR-019).
@role: Generate the FVA/STIRAK-identical block-structured 2D gear sector for any spur gear by
       **topology transplant**: the exact reference sector connectivity (mined once from the
       ANSA/FVA deck by :mod:`app.services.model.reference_slice`) is re-used verbatim, and only
       the node positions are derived from the target geometry — angular scaling about the sector
       bisector, a piecewise radial feature map (bore → fan ring → root circle → usable tip), and
       re-projection of the tooth-zone surface nodes onto the real :class:`ToothProfile` boundary.
       The MESHING_SPEC §11 optimization finish (frozen connectivity, boundary fixed) then lifts
       interior quality. Structure is reference-identical by construction: 3024 quads per 4-tooth
       sector, all interior nodes valence 4 except one fan-convergence node per tooth gap.

Frame convention: the sector bisector (the middle tooth gap centre) lies on +y; four teeth at
±0.5/±1.5 angular pitches, gaps at 0/±1/±2 pitches, radial cut faces (Fesselung) at ±3 pitches.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.spatial import cKDTree

from app.services.geometry.tooth_form import ToothProfile
from app.services.model.block_mesh import Coords, QuadList, optimize_finish, resample
from app.services.model.reference_slice import (
    SectorTemplate,
    canonicalize_positions,
    load_reference_template,
)
from app.services.model.refine import chords_with_surface_edges, split_edges

Array = NDArray[np.float64]

#: Template layout (in angular-pitch units from the bisector): tooth centres and gap centres.
TOOTH_CENTRES = (-1.5, -0.5, 0.5, 1.5)
GAP_CENTRES = (-2.0, -1.0, 0.0, 1.0, 2.0)
CUT_POSITION = 3.0  # radial Fesselung faces
#: Surface nodes within this many pitches of the bisector lie on the tooth/gap contour and are
#: re-projected onto the analytic boundary; beyond it is the (scaled) reference shoulder shape.
TOOTH_ZONE = 2.02


@dataclass
class SectorMesh2D:
    """A generated 2D gear sector: reference topology, target geometry."""

    coords: Coords  # (x, y, 0.0) — block_mesh convention
    quads: QuadList
    kind: list[str]  # per node: interior | surface | bore | cut
    meta: dict[str, float | int | str]

    @property
    def points(self) -> Array:
        return np.asarray([(c[0], c[1]) for c in self.coords], dtype=float)


def scaled_jacobians(coords: Coords, quads: QuadList) -> Array:
    """Per-quad scaled Jacobian (min corner sine), vectorized. CCW quads assumed."""
    pts = np.asarray([(c[0], c[1]) for c in coords], dtype=float)
    q = np.asarray(quads, dtype=np.int64)
    corners = pts[q]  # (M, 4, 2)
    sj = np.full(len(q), np.inf)
    for k in range(4):
        p = corners[:, k]
        e1 = corners[:, (k + 1) % 4] - p
        e2 = corners[:, (k - 1) % 4] - p
        cross = e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0]
        denom = np.maximum(np.hypot(*e1.T) * np.hypot(*e2.T), 1e-30)
        sj = np.minimum(sj, cross / denom)
    return sj


def _rotate(points: Array, angle: float) -> Array:
    """Rotate (N,2) points CCW by ``angle`` about the origin."""
    c, s = math.cos(angle), math.sin(angle)
    return points @ np.array([[c, s], [-s, c]])


def _project_to_contour(points: Array, cloud: Array, breaks: NDArray[np.int64]) -> Array:
    """Exact foot-point projection onto the sampled contour polyline.

    Nearest-sample quantization (~µm) breaks the fp-exact tooth congruence of refined meshes,
    so after the KD lookup the point is projected onto the two polyline segments adjacent to
    the nearest sample (segments never bridge contour parts, given by ``breaks``).
    """
    part_of = np.searchsorted(breaks, np.arange(len(cloud)), side="right")
    _, idx = cKDTree(cloud).query(points)
    out = np.empty_like(points)
    for k, (p, i) in enumerate(zip(points, idx, strict=True)):
        best = cloud[i]
        best_d = float(np.hypot(*(p - best)))
        for j in (int(i) - 1, int(i)):
            if j < 0 or j + 1 >= len(cloud) or part_of[j] != part_of[j + 1]:
                continue
            a, b = cloud[j], cloud[j + 1]
            ab = b - a
            denom = float(ab @ ab)
            if denom <= 0.0:
                continue
            t = float(np.clip((p - a) @ ab / denom, 0.0, 1.0))
            foot = a + t * ab
            d = float(np.hypot(*(p - foot)))
            if d < best_d:
                best, best_d = foot, d
        out[k] = best
    return out


def _tooth_contour_cloud(
    profile: ToothProfile,
    samples_per_flank: int = 4000,
    fillet: object | None = None,
) -> tuple[Array, NDArray[np.int64]]:
    """Dense point polyline of the 4-tooth outer contour (flanks, tip arcs, root arcs).

    Built in the sector frame (bisector on +y). Used as the projection target for the
    tooth-zone surface nodes, so the mesh boundary lies exactly on the real as-cut geometry.
    With a ``fillet`` strategy (see :mod:`app.services.geometry.root_fillet`) the boundary
    starts at the gap centre and the root arcs collapse automatically (w_root = π/z).
    Returns (samples, part break offsets) for exact segment projection.
    """
    pitch = 2.0 * math.pi / profile.z
    if fillet is not None:
        from app.services.geometry.root_fillet import fillet_boundary

        raw = fillet_boundary(profile, fillet, flank_points=1200, to_tip_circle=True)  # type: ignore[arg-type]
    else:
        raw = profile.transverse_right_boundary(
            fillet_points=900, flank_points=1200, to_tip_circle=True
        )
    boundary = np.asarray([(p[0], p[1]) for p in raw])
    right = resample(boundary, np.linspace(0.0, 1.0, samples_per_flank))
    left = right * np.array([-1.0, 1.0])
    w_root = math.atan2(right[0, 0], right[0, 1])  # fillet bottom, angle off the tooth centre
    w_tip = math.atan2(right[-1, 0], right[-1, 1])
    r_f = float(np.hypot(*right[0]))
    r_tip = float(np.hypot(*right[-1]))

    def root_arc(theta_lo: float, theta_hi: float) -> Array:
        arc = np.linspace(theta_lo, theta_hi, 600)
        return np.column_stack([r_f * np.cos(arc), r_f * np.sin(arc)])

    parts: list[Array] = []
    for centre in TOOTH_CENTRES:
        theta_c = math.pi / 2.0 + centre * pitch
        # The tooth-frame +y axis moves onto theta_c; the right flank (+x) sits at theta < theta_c.
        parts.append(_rotate(right, centre * pitch))
        parts.append(_rotate(left, centre * pitch))
        tip = np.linspace(theta_c - w_tip, theta_c + w_tip, 400)
        parts.append(np.column_stack([r_tip * np.cos(tip), r_tip * np.sin(tip)]))
    # Root arcs: across the three inner gaps, plus extensions past the outermost teeth so the
    # whole tooth zone (|phi| <= TOOTH_ZONE pitches) has a projection target.
    for lo_centre, hi_centre in zip(TOOTH_CENTRES, TOOTH_CENTRES[1:], strict=False):
        parts.append(
            root_arc(
                math.pi / 2.0 + lo_centre * pitch + w_root,
                math.pi / 2.0 + hi_centre * pitch - w_root,
            )
        )
    parts.append(
        root_arc(
            math.pi / 2.0 - TOOTH_ZONE * pitch,
            math.pi / 2.0 + TOOTH_CENTRES[0] * pitch - w_root,
        )
    )
    parts.append(
        root_arc(
            math.pi / 2.0 + TOOTH_CENTRES[-1] * pitch + w_root,
            math.pi / 2.0 + TOOTH_ZONE * pitch,
        )
    )
    breaks = np.cumsum([len(p) for p in parts], dtype=np.int64)
    return np.vstack(parts), breaks


def generate_sector_2d(
    profile: ToothProfile,
    *,
    bore_radius_mm: float | None = None,
    finish_iters: int = 40,
    lift_below: float = 0.4,
    refine_root: int = 1,
    refine_flank: int = 1,
    refine_thickness: int = 1,
    fillet: object | None = None,
    mirror_symmetric: bool | None = None,
    template: SectorTemplate | None = None,
) -> SectorMesh2D:
    """Transplant the reference sector topology onto ``profile``'s geometry (see module doc).

    ``refine_root`` / ``refine_flank`` / ``refine_thickness`` are FVA-style density factors
    (1 = reference density, 2/3 = split every chord of that band into 2/3 strips — conformal,
    structure-preserving; the selection is radius-based and therefore identical on every tooth
    and both flanks). Root = along the fillet rounding ("Elemente am Zahnfuß"), flank = up the
    involute ("Elemente über Zahnhöhe"), thickness = across the tooth, seeded at the tip-land
    edges ("Elemente über Zahndicke" — the chords run down through the whole tooth).
    ``fillet`` selects an optimized root-fillet strategy (root_fillet module); ``None`` = the
    standard tool-generated ρ_F fillet. Run :func:`root_fillet.mating_tip_clearance` before
    using an optimized fillet in a deck.
    """
    if profile.has_undercut:
        logging.getLogger(__name__).warning(
            "gear z=%d x_E=%.3f is undercut (x_E,min=%.3f, DIN 3960 3.6.06): the closed-form "
            "d_Ff/fillet geometry is invalid — mesh with care",
            profile.z,
            profile.x_e,
            profile.undercut_min_generation_shift,
        )
    tpl = template if template is not None else load_reference_template()
    meta = tpl.meta
    pitch_ref = 2.0 * math.pi / int(meta["z_teeth"])
    pitch_new = 2.0 * math.pi / profile.z
    bis_ref = (float(meta["theta_lo_rad"]) + float(meta["theta_hi_rad"])) / 2.0

    # Piecewise radial feature map: bore → fan ring → root bottom → tip circle. The root knot
    # follows the ACTUAL contour bottom (optimized fillets may dig deeper than d_f), otherwise
    # the surface projection would cross the mapped boundary-layer rows and invert cells.
    cloud, cloud_breaks = _tooth_contour_cloud(profile, fillet=fillet)
    r_root_new = float(np.hypot(cloud[:, 0], cloud[:, 1]).min())
    r_f_ref = float(meta["surface_r_min_mm"])
    r_na_ref = float(meta["surface_r_max_mm"])
    scale = r_root_new / r_f_ref
    bore_new = (
        bore_radius_mm if bore_radius_mm is not None else float(meta["bore_radius_mm"]) * scale
    )
    # The reference contour runs to the real tip circle d_a (its tip includes the chamfer), so
    # the outermost radial knot must be d_a — using d_Na would squeeze the whole flank band.
    r_tip_new = (profile.d_a if profile.d_a is not None else profile.d_Na) / 2.0
    knots_ref = np.array(
        [float(meta["bore_radius_mm"]), float(meta["fan_ring_radius_mm"]), r_f_ref, r_na_ref]
    )
    knots_new = np.array(
        [
            bore_new,
            float(meta["fan_ring_radius_mm"]) * scale,
            r_root_new,
            r_tip_new,
        ]
    )
    if not (np.all(np.diff(knots_ref) > 0) and np.all(np.diff(knots_new) > 0)):
        raise ValueError(f"radial feature knots must be increasing: {knots_new}")

    xy = tpl.nodes
    r_ref = np.hypot(xy[:, 0], xy[:, 1])
    phi_frac = (np.arctan2(xy[:, 1], xy[:, 0]) - bis_ref) / pitch_ref  # -3 … +3
    theta = math.pi / 2.0 + phi_frac * pitch_new
    r_new = np.interp(r_ref, knots_ref, knots_new)
    pts = np.column_stack([r_new * np.cos(theta), r_new * np.sin(theta)])

    kinds = np.asarray(tpl.kind)
    # Exact constraints: bore radius, radial cut faces, and the real tooth contour.
    bore_mask = kinds == "bore"
    pts[bore_mask] *= (bore_new / np.hypot(*pts[bore_mask].T))[:, None]
    cut_mask = kinds == "cut"
    cut_theta = math.pi / 2.0 + np.sign(phi_frac[cut_mask]) * CUT_POSITION * pitch_new
    pts[cut_mask] = np.column_stack(
        [r_new[cut_mask] * np.cos(cut_theta), r_new[cut_mask] * np.sin(cut_theta)]
    )
    project_mask = (kinds == "surface") & (np.abs(phi_frac) <= TOOTH_ZONE)
    pts[project_mask] = _project_to_contour(pts[project_mask], cloud, cloud_breaks)

    # Exact tooth-to-tooth congruence (and in-tooth mirror symmetry when the flank parameters
    # are symmetric) — enforced after placement and re-enforced after every lift pass.
    # Flank-symmetry policy: micro-geometry (or future per-flank macro data) may break the
    # in-tooth mirror; teeth stay rotation-congruent either way. None = derive from profile.
    symmetric = profile.is_flank_symmetric() if mirror_symmetric is None else mirror_symmetric

    def canon(p: Array) -> Array:
        return canonicalize_positions(
            p,
            tpl.canon_group,
            tpl.canon_rot,
            tpl.canon_mirror,
            math.pi / 2.0,
            pitch_new,
            use_mirror=symmetric,
        )

    pts = canon(pts)
    coords: Coords = [(float(x), float(y), 0.0) for x, y in pts]
    quads: QuadList = [tuple(int(v) for v in q) for q in tpl.quads]
    if finish_iters > 0:
        # Selective §11 finish: free only interior nodes touching sub-quality cells (the tip
        # caps), so the reference-identical dome/fan/rim layout stays untouched elsewhere. The
        # lift set is closed over the symmetry orbits and lifted positions are orbit-averaged,
        # so all teeth stay exactly congruent (and mirror-symmetric when applicable).
        sj0 = scaled_jacobians(coords, quads)
        seed = {n for q, s in zip(quads, sj0, strict=True) if s < lift_below for n in q}
        lift_groups = {tpl.canon_group[n] for n in seed}
        lift_nodes = {i for i in range(len(coords)) if tpl.canon_group[i] in lift_groups}
        fixed = {i for i in range(len(coords)) if tpl.kind[i] != "interior" or i not in lift_nodes}
        if len(fixed) < len(coords):
            coords = optimize_finish(coords, quads, fixed, iters=finish_iters)
            pts = canon(np.asarray([(c[0], c[1]) for c in coords], dtype=float))
            coords = [(float(x), float(y), 0.0) for x, y in pts]

    # Parametric density (conformal chord splits). Selection bands: root = fillet + root arc
    # (below d_Ff), flank = involute (d_Ff … d_Na, excluding the tip chamfer/cap). Parent nodes
    # are exactly canonical and the bands are rotation/mirror-equivariant, so the inserted
    # nodes inherit exact tooth congruence; new surface nodes are re-projected on the contour.
    kinds_out = list(tpl.kind)
    r_split = profile.d_Ff / 2.0 + 0.02
    r_flank_hi = profile.d_Na / 2.0 - 0.02

    def tooth_zone_nodes(p: Array) -> set[int]:
        phi_now = (np.arctan2(p[:, 1], p[:, 0]) - math.pi / 2.0) / pitch_new
        return {int(i) for i in np.where(np.abs(phi_now) <= TOOTH_ZONE)[0]}

    bands = (
        (refine_root, 0.0, r_split),
        (refine_flank, r_split, r_flank_hi),
        # thickness: seeded ONLY at the flat tip land (r ≈ d_a/2) — those chords run
        # tangentially down through the whole tooth, adding elements over the tooth
        # THICKNESS. Chamfer edges (d_Na … d_a) are deliberately excluded: their chords
        # cut the 45° corner cells into slivers (measured: SJ 0.22 on kst-E gear 2).
        (refine_thickness, r_tip_new - 0.02, r_tip_new + 0.05),
    )
    if any(factor > 1 for factor, _, _ in bands):
        for factor, r_lo, r_hi in bands:
            if factor <= 1:
                continue
            edges = chords_with_surface_edges(
                quads, pts, kinds_out, r_lo, r_hi, seed_nodes=tooth_zone_nodes(pts)
            )
            pts, quads, kinds_out, new_surface = split_edges(
                pts, quads, kinds_out, edges, parts=factor
            )
            in_zone = tooth_zone_nodes(pts)
            reproject = [i for i in new_surface if i in in_zone]
            if reproject:
                pts[reproject] = _project_to_contour(pts[reproject], cloud, cloud_breaks)
        coords = [(float(x), float(y), 0.0) for x, y in pts]

    # Effective per-tooth element counts along the contour ("effektive Werte" of the FVA
    # mesh-fineness dialog): surface edges of the MIDDLE tooth counted per band — flank =
    # one flank (Zahnhöhe), root = one full gap rounding (Zahnfuß), thickness = the tip land
    # (Zahndicke). Counted on the final mesh, so density factors are included.
    def band_count(r_lo: float, r_hi: float, phi_lo: float, phi_hi: float) -> int:
        edges_seen: set[tuple[int, int]] = set()
        for q in quads:
            for a, b in ((q[0], q[1]), (q[1], q[2]), (q[2], q[3]), (q[3], q[0])):
                if kinds_out[a] != "surface" or kinds_out[b] != "surface":
                    continue
                key = (a, b) if a < b else (b, a)
                if key in edges_seen:
                    continue
                mid = 0.5 * (pts[a] + pts[b])
                r = float(np.hypot(mid[0], mid[1]))
                phi = (math.atan2(mid[1], mid[0]) - math.pi / 2.0) / pitch_new
                if r_lo <= r <= r_hi and phi_lo <= phi <= phi_hi:
                    edges_seen.add(key)
        return len(edges_seen)

    sj = scaled_jacobians(coords, quads)
    out_meta: dict[str, float | int | str] = {
        "z_teeth": profile.z,
        "bore_radius_mm": float(bore_new),
        "n_quads": len(quads),
        "n_nodes": len(coords),
        "min_scaled_jacobian": float(sj.min()),
        "cells_below_035": int((sj < 0.35).sum()),
        "refine_root": refine_root,
        "refine_flank": refine_flank,
        "refine_thickness": refine_thickness,
        "elements_root": band_count(0.0, r_split, 0.1, 0.9),  # the gap right of the tooth
        "elements_flank": band_count(r_split, r_flank_hi, 0.0, 0.5),  # one flank
        "elements_thickness": band_count(r_flank_hi, r_tip_new + 0.05, -0.5, 0.5),  # tip land
        "template_part": str(meta["part"]),
    }
    return SectorMesh2D(coords=coords, quads=quads, kind=kinds_out, meta=out_meta)
