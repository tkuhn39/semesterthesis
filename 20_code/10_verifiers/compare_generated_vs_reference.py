"""
@module: 10_verifiers.compare_generated_vs_reference
@context: Verifier — ADR-019 topology-transplant mesher vs. the ANSA/FVA reference.
@role: Generate the kst-E wheel sector with :func:`template_mesher.generate_sector_2d` (surface
       re-seeded on OUR ToothProfile geometry, interior via the radial/angular map + §11 finish)
       and compare against the parsed reference slice: topology metrics, quality, and overlay
       plots (full sector + dome zoom) written to ``40_backend/80_output/``. Run from ``20_code/``:

           python 10_verifiers/compare_generated_vs_reference.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

CODE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE_ROOT / "40_backend"))

from app.io.ste import gear_stage_from_ste, load_ste  # noqa: E402
from app.services.geometry.gear import GearStage  # noqa: E402
from app.services.geometry.tooth_form import ToothProfile  # noqa: E402
from app.services.model.reference_slice import (  # noqa: E402
    REFERENCE_DECK,
    load_reference_template,
    measure,
    mid_slice,
    parse_part,
)
from app.services.model.template_mesher import generate_sector_2d, scaled_jacobians  # noqa: E402

REPO_ROOT = CODE_ROOT.parent
OUT = CODE_ROOT / "40_backend" / "80_output"
STE = REPO_ROOT / "30_references_and_examples" / "33_STplus" / "kst-E_eingabe.ste"


def _plot_mesh(ax: plt.Axes, pts: np.ndarray, quads: list, color: str, lw: float = 0.4) -> None:
    segs = set()
    for q in quads:
        for k in range(4):
            a, b = q[k], q[(k + 1) % 4]
            segs.add((a, b) if a < b else (b, a))
    idx = np.array(sorted(segs))
    xs = np.stack([pts[idx[:, 0], 0], pts[idx[:, 1], 0], np.full(len(idx), np.nan)], axis=1)
    ys = np.stack([pts[idx[:, 0], 1], pts[idx[:, 1], 1], np.full(len(idx), np.nan)], axis=1)
    ax.plot(xs.ravel(), ys.ravel(), "-", color=color, lw=lw)
    ax.set_aspect("equal")


def main() -> None:
    # --- our geometry (must match the reference part) ---
    stage = GearStage.from_ste(gear_stage_from_ste(load_ste(STE)))
    profile = ToothProfile.from_stage(stage, 1)  # wheel z=52 (plastic side)
    print(
        f"wheel: z={profile.z}, d_f/2={profile.root_diameter_mm / 2:.4f}, "
        f"d_Na/2={profile.d_Na / 2:.4f}"
    )
    assert profile.z == 52

    template = load_reference_template()
    print(
        f"reference: d_f/2={template.meta['surface_r_min_mm']}, "
        f"d_Na/2={template.meta['surface_r_max_mm']}"
    )

    # --- generate on the reference bore so the overlay is 1:1 ---
    mesh = generate_sector_2d(
        profile, bore_radius_mm=float(template.meta["bore_radius_mm"]), finish_iters=12
    )
    print(f"generated: {mesh.meta}")

    # --- topology + quality vs reference ---
    gen_coords = {i: (c[0], c[1]) for i, c in enumerate(mesh.coords)}
    gen_metrics = measure(mesh.quads, gen_coords)
    print(f"generated interior valence: {gen_metrics.interior_valence}")
    print(
        f"generated irregular nodes: {[(v, round(t, 2)) for _, v, _, t in gen_metrics.irregular]}"
    )
    print(
        f"generated min scaled Jacobian {gen_metrics.min_scaled_jacobian:.3f}, "
        f"cells<0.35: {gen_metrics.cells_below_035}"
    )

    deck = REPO_ROOT / REFERENCE_DECK
    nodes, elems = parse_part(deck, "Part_Rad_Vz_1")
    ref_quads, ref_coords = mid_slice(nodes, elems)
    ref_metrics = measure(ref_quads, ref_coords)
    print(
        f"reference min scaled Jacobian {ref_metrics.min_scaled_jacobian:.3f}, "
        f"cells<0.35: {ref_metrics.cells_below_035}"
    )
    assert gen_metrics.interior_valence == ref_metrics.interior_valence, "topology mismatch!"
    assert gen_metrics.n_quads == ref_metrics.n_quads

    # Root-band quality (the thesis-critical fillet region): quads with a node within the
    # boundary-layer band around the root circle.
    pts = mesh.points
    sj = scaled_jacobians(mesh.coords, mesh.quads)
    r_f = profile.root_diameter_mm / 2.0
    radii = np.hypot(pts[:, 0], pts[:, 1])
    band = (radii > r_f - 1.2) & (radii < r_f + 1.2)
    in_band = np.array([band[list(q)].any() for q in mesh.quads])
    print(f"root band: {in_band.sum()} quads, min sj {sj[in_band].min():.3f}")

    # --- reference nodes rotated into the generator frame (bisector on +y) ---
    order = sorted(ref_coords)
    ref_pts = np.array([ref_coords[n] for n in order])
    index = {n: i for i, n in enumerate(order)}
    ref_q = [[index[n] for n in q] for q in ref_quads]
    bis = (float(template.meta["theta_lo_rad"]) + float(template.meta["theta_hi_rad"])) / 2.0
    rot = math.pi / 2.0 - bis
    c, s = math.cos(rot), math.sin(rot)
    ref_pts = ref_pts @ np.array([[c, s], [-s, c]])

    # --- plots ---
    fig, axes = plt.subplots(1, 2, figsize=(22, 13))
    _plot_mesh(axes[0], ref_pts, ref_q, "dimgray")
    axes[0].set_title(f"FVA REFERENCE (ANSA) — {ref_metrics.n_quads} quads")
    _plot_mesh(axes[1], pts, mesh.quads, "tab:blue")
    axes[1].set_title(
        f"GENERATED (topology transplant) — {gen_metrics.n_quads} quads, "
        f"min J {gen_metrics.min_scaled_jacobian:.2f}"
    )
    fig.suptitle("kst-E wheel (z=52) 4-tooth sector: reference vs generated")
    fig.savefig(OUT / "transplant_vs_reference.png", dpi=110, bbox_inches="tight")

    fig2, ax2 = plt.subplots(figsize=(18, 13))
    _plot_mesh(ax2, ref_pts, ref_q, "dimgray", lw=0.9)
    _plot_mesh(ax2, pts, mesh.quads, "tab:blue", lw=0.5)
    r_lo, r_hi = r_f - 1.6, r_f + 0.9
    ax2.set_xlim(-2.4, 2.4)
    ax2.set_ylim(r_lo, r_hi + 1.2)
    ax2.set_title("dome/fan zoom — reference (gray) vs generated (blue)")
    fig2.savefig(OUT / "transplant_dome_zoom.png", dpi=130, bbox_inches="tight")
    print(f"plots: {OUT / 'transplant_vs_reference.png'}, {OUT / 'transplant_dome_zoom.png'}")


if __name__ == "__main__":
    main()
