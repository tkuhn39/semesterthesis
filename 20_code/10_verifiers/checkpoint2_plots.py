"""
@module: 10_verifiers.checkpoint2_plots
@context: Verifier — checkpoint 2 evidence plots (plan v2: canonicalization, density, fillets).
@role: Produce the review plots for the user: exact tooth congruence + mirror symmetry, the
       FVA-style density levels, the root/flank convergence curves from the native 2D solver,
       and the optimized root-fillet strategies (contours, mesh, quick-FE stress ranking).
       Output goes to ``40_backend/80_output/cp2_*.png``. Run from ``20_code/``:

           python 10_verifiers/checkpoint2_plots.py
"""

from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.spatial import cKDTree

CODE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CODE_ROOT / "40_backend"))

from app.io.ste import gear_stage_from_ste, load_ste  # noqa: E402
from app.services.geometry.gear import GearStage  # noqa: E402
from app.services.geometry.root_fillet import (  # noqa: E402
    BezierFillet,
    BionicFillet,
    EllipticFillet,
    fillet_boundary,
    mating_tip_clearance,
)
from app.services.geometry.tooth_form import ToothProfile  # noqa: E402
from app.services.model.plane_fe import density_convergence, root_tensile_stress  # noqa: E402
from app.services.model.reference_slice import load_reference_template  # noqa: E402
from app.services.model.template_mesher import generate_sector_2d, scaled_jacobians  # noqa: E402

OUT = CODE_ROOT / "40_backend" / "80_output"
STE = CODE_ROOT.parent / "30_references_and_examples" / "33_STplus" / "kst-E_eingabe.ste"


def _plot_mesh(ax, pts, quads, color="steelblue", lw=0.5):
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
    stage = GearStage.from_ste(gear_stage_from_ste(load_ste(STE)))
    wheel = ToothProfile.from_stage(stage, 1)
    pinion = ToothProfile.from_stage(stage, 0)
    bore = float(load_reference_template().meta["bore_radius_mm"])
    pitch = 2.0 * math.pi / wheel.z

    mesh = generate_sector_2d(wheel, bore_radius_mm=bore)
    pts = mesh.points
    phi = (np.arctan2(pts[:, 1], pts[:, 0]) - math.pi / 2.0) / pitch

    # --- 1) tooth congruence + mirror symmetry -------------------------------
    base_idx = (phi >= 0.001) & (phi <= 0.999)
    base = pts[base_idx]
    tree = cKDTree(base)
    worst_rot = 0.0
    fig, axes = plt.subplots(1, 2, figsize=(19, 9))
    colors = ["tab:blue", "tab:orange", "tab:green", "tab:red"]
    for i, k in enumerate((-2, -1, 0, 1)):
        seg = pts[(phi >= k + 0.001) & (phi <= k + 0.999)]
        ang = -k * pitch
        c, s = math.cos(ang), math.sin(ang)
        moved = seg @ np.array([[c, s], [-s, c]])
        d, _ = tree.query(moved)
        worst_rot = max(worst_rot, float(d.max()))
        axes[0].plot(moved[:, 0], moved[:, 1], ".", ms=1.2, color=colors[i], label=f"Zahn {i + 1}")
    axes[0].set_aspect("equal")
    axes[0].legend(markerscale=8)
    axes[0].set_title(f"alle 4 Zähne aufeinander rotiert — max. Abweichung {worst_rot:.2e} mm")
    axis = math.pi / 2.0 + 0.5 * pitch
    normal = np.array([-math.sin(axis), math.cos(axis)])
    mirrored = base - 2.0 * np.outer(base @ normal, normal)
    d, _ = tree.query(mirrored)
    tip = base[np.hypot(base[:, 0], base[:, 1]) > wheel.d_Na / 2.0 - 0.9]
    tip_m = mirrored[np.hypot(base[:, 0], base[:, 1]) > wheel.d_Na / 2.0 - 0.9]
    axes[1].plot(tip[:, 0], tip[:, 1], "o", ms=3, color="dimgray", label="Zahnkopf")
    axes[1].plot(tip_m[:, 0], tip_m[:, 1], "x", ms=3, color="tab:red", label="gespiegelt")
    axes[1].set_aspect("equal")
    axes[1].legend()
    axes[1].set_title(f"Spiegelsymmetrie Basiszahn — max. Abweichung {float(d.max()):.2e} mm")
    fig.suptitle("Checkpoint 2 — exakte Zahn-Kongruenz und Symmetrie (kst-E Rad)")
    fig.savefig(OUT / "cp2_tooth_congruence.png", dpi=110, bbox_inches="tight")
    print(f"congruence: rot {worst_rot:.2e} mm, mirror {float(d.max()):.2e} mm")

    # --- 2) density levels ----------------------------------------------------
    fig, axes = plt.subplots(1, 3, figsize=(21, 8))
    for ax, (rr, rf) in zip(axes, ((1, 1), (2, 1), (2, 2)), strict=True):
        m = generate_sector_2d(wheel, bore_radius_mm=bore, refine_root=rr, refine_flank=rf)
        sj = scaled_jacobians(m.coords, m.quads)
        _plot_mesh(ax, m.points, m.quads)
        ax.set_xlim(-3.2, 3.2)
        ax.set_ylim(22.8, 27.3)
        ax.set_title(
            f"Fuß x{rr} / Flanke x{rf} — {len(m.quads)} Quads, "
            f"min J {sj.min():.2f}, <0.35: {(sj < 0.35).sum()}"
        )
    fig.suptitle("Checkpoint 2 — parametrische Netzfeinheit (konforme Chord-Splits)")
    fig.savefig(OUT / "cp2_density_levels.png", dpi=110, bbox_inches="tight")
    print("density plot done")

    # --- 3) convergence curves -------------------------------------------------
    fig, ax = plt.subplots(figsize=(10, 6))
    for target, color in (("root", "tab:blue"), ("flank", "tab:orange")):
        t0 = time.perf_counter()
        conv = density_convergence(wheel, target=target, levels=(1, 2, 3), bore_radius_mm=bore)
        dt = time.perf_counter() - t0
        ax.plot(conv.levels, conv.sigma_mpa, "o-", color=color, label=f"{target} ({dt:.1f} s)")
        print(f"convergence {target}: {conv.sigma_mpa} -> level {conv.converged_level}")
    ax.set_xlabel("Feinheitsstufe (1 = Referenzdichte)")
    ax.set_ylabel("max. Zugspannung Fußrundung [MPa]")
    ax.set_xticks([1, 2, 3])
    span = ax.get_ylim()
    mid = sum(span) / 2
    ax.set_ylim(mid - max(8.0, (span[1] - span[0])), mid + max(8.0, (span[1] - span[0])))
    ax.grid(alpha=0.3)
    ax.legend()
    ax.set_title("Checkpoint 2 — Konvergenz-Schnelltest (nativer 2D-Löser, Kopflast 100 N)")
    fig.savefig(OUT / "cp2_convergence.png", dpi=110, bbox_inches="tight")

    # --- 4) fillet strategies ---------------------------------------------------
    strategies = {
        "Standard (ρ_F)": None,
        "Ellipse e_f=−0.2": EllipticFillet(e_f=-0.2),
        "Bézier Be=0.57": BezierFillet(be=0.57),
        "Bionisch b_f=0.35": BionicFillet(),
    }
    fig, axes = plt.subplots(1, 2, figsize=(19, 8))
    sigmas: dict[str, float] = {}
    clearances: dict[str, float] = {}
    for name, strat in strategies.items():
        if strat is None:
            contour = np.array([(p[0], p[1]) for p in wheel.transverse_right_boundary()])
        else:
            contour = np.array([(p[0], p[1]) for p in fillet_boundary(wheel, strat)])
        axes[0].plot(contour[:, 0], contour[:, 1], "-", lw=1.6, label=name)
        fil = contour[np.hypot(contour[:, 0], contour[:, 1]) < wheel.d_Ff / 2.0 + 1e-6]
        clearances[name] = mating_tip_clearance(
            wheel,
            fil,
            mating_tip_radius_mm=(pinion.d_a or pinion.d_Na) / 2.0,
            mating_teeth=pinion.z,
            mating_half_tip_rad=pinion.half_thickness_angle((pinion.d_a or pinion.d_Na) / 2.0),
            centre_distance_mm=52.0,
        )
        m = generate_sector_2d(wheel, bore_radius_mm=bore, fillet=strat)
        sigmas[name] = root_tensile_stress(m, wheel).sigma_max_mpa
    axes[0].set_aspect("equal")
    axes[0].set_xlim(-0.1, 1.8)
    axes[0].set_ylim(24.4, 25.5)
    axes[0].legend(fontsize=9)
    axes[0].set_title("Fußkurven-Strategien (rechte Flanke, Lücken-Zoom)")
    names = list(sigmas)
    values = [sigmas[n] for n in names]
    ref = sigmas["Standard (ρ_F)"]
    bars = axes[1].bar(range(len(names)), values, color=["gray"] + ["tab:blue"] * 3)
    for i, (n, v) in enumerate(zip(names, values, strict=True)):
        delta = (v / ref - 1.0) * 100.0
        axes[1].text(
            i,
            v + 2,
            f"{v:.0f} MPa\n({delta:+.1f} %)\nFreigang {clearances[n]:.2f} mm",
            ha="center",
            fontsize=9,
        )
    axes[1].set_xticks(range(len(names)), names, fontsize=9)
    axes[1].set_ylim(0, max(values) * 1.25)
    axes[1].set_ylabel("max. Zugspannung Fußrundung [MPa]")
    axes[1].set_title("2D-Schnell-FE: Fußspannung je Strategie (gleiche Last)")
    fig.suptitle("Checkpoint 2 — optimierte Zahnfußgeometrien")
    fig.savefig(OUT / "cp2_fillets.png", dpi=110, bbox_inches="tight")
    print(f"fillet sigmas: { {k: round(v, 1) for k, v in sigmas.items()} }")

    # --- 5) mesh on the Bézier fillet -------------------------------------------
    m = generate_sector_2d(wheel, bore_radius_mm=bore, fillet=BezierFillet(be=0.57))
    sj = scaled_jacobians(m.coords, m.quads)
    fig, ax = plt.subplots(figsize=(14, 10))
    _plot_mesh(ax, m.points, m.quads)
    ax.set_xlim(-3.0, 3.0)
    ax.set_ylim(23.2, 27.3)
    ax.set_title(
        f"Mesh auf Bézier-Fußkurve (Be=0.57) — Topologie unverändert, "
        f"min J {sj.min():.2f}, <0.35: {(sj < 0.35).sum()}"
    )
    fig.savefig(OUT / "cp2_fillet_mesh.png", dpi=120, bbox_inches="tight")
    print("all checkpoint-2 plots saved")


if __name__ == "__main__":
    main()
