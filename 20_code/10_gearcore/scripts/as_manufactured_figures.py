"""Figures of the gears as manufactured against the STplus case (ADR-116 items 54 and 55).

    python scripts/as_manufactured_figures.py            # 80_output/fe/kst_e/geometrie_gemessen
    python scripts/as_manufactured_figures.py --out DIR

Three figures, each as SVG, PDF and PNG (``gearcore.plot_style``):

``kontur_ritzel`` and ``kontur_rad``: above the root and the tip of the tooth in true scale, the
nominal contour of the STplus generation against the contour as manufactured (the medians of
the GINA measurement, ``data/fe/as_manufactured.yaml``, variant "beide": span, tip and root
circle, the pinion's relief, the wheel's profile slope and tip corner radius); below the
deviation of the manufactured contour from the nominal one over the diameter from the root
circle to the tip form point, normal to the nominal contour, plus = material (the deeper root
circle, the fillet, the constant part of the tooth thickness from the measured span, the
profile slope f_Hα of the wheel, the relief of the pinion; the tip corner is shown in true scale
only, since an arc against a chamfer is no flank deviation).

``netz_kopfkappe``: the tip of the middle tooth of the sector mesh on the measured wheel with the
rows of the template (the corner quad on the arc, known limit FE-26) and with the cap of the
tooth tip (``MeshCounts.cap_layers`` 1).
"""

import argparse
import math
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import numpy as np

from gearcore import contour as ct
from gearcore import data
from gearcore import manufactured as mf
from gearcore.contour import Role
from gearcore.errors import InputRangeError
from gearcore.fe import resample as rs
from gearcore.fe import sector_mesh as sm
from gearcore.generation import compute_generation
from gearcore.involute import base_diameter
from gearcore.io.ste import load_ste, pair_input_from_ste
from gearcore.models.results import GenerationResult
from gearcore.plot_style import apply as apply_plot_style
from gearcore.plot_style import (
    decimal_comma,
    figure_size,
    legend_outside,
    new_figure,
    save,
    symbol_label,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
OUTPUT = REPO_ROOT / "80_output" / "fe" / "kst_e" / "geometrie_gemessen"
NOMINAL_LABEL = "Sollkontur (STplus-Erzeugung)"
MEASURED_LABEL = "Kontur wie gefertigt (Mediane der GINA-Messung, Variante beide)"
SERIES_COUNTS = rs.MeshCounts(
    over_tooth_height=18,
    at_tip_edge_break=3,
    at_tooth_root=60,
    over_tooth_thickness=14,
    root_layers=4,
    rim_rings=12,
    shoulder_columns=2,
)
"""The counts of the pocket series with three rows on the tip corner arc."""
CONTOUR_POINTS = 2000
GERMAN_ROLE = {"pinion": "Ritzel", "wheel": "Rad"}


def _polar_left_involute(contour: ct.ToothContour) -> tuple[np.ndarray, np.ndarray]:
    """Radius and polar angle from the tooth centre (positive towards the left flank) of the
    left involute, from the root form point to its end, in the order of increasing radius."""
    points = contour.segment("left_involute")
    radius = np.hypot(points[:, 0], points[:, 1])
    angle = np.arctan2(-points[:, 0], points[:, 1])
    order = np.argsort(radius)
    return radius[order], angle[order]


def flank_deviation(
    nominal: ct.ToothContour, measured: ct.ToothContour, base_radius_mm: float
) -> tuple[np.ndarray, np.ndarray]:
    """The deviation of the measured involute from the nominal one, normal to the flank and in
    µm (plus = material), over the diameter in mm: at equal radius the two flanks differ by the
    polar angle, and two involutes of one base circle turned against each other by that angle
    lie the base-circle arc apart, which is their normal distance."""
    r_nominal, psi_nominal = _polar_left_involute(nominal)
    r_measured, psi_measured = _polar_left_involute(measured)
    low = max(float(r_nominal[0]), float(r_measured[0]))
    high = min(float(r_nominal[-1]), float(r_measured[-1]))
    inside = (r_measured >= low) & (r_measured <= high)
    if not inside.any():
        raise InputRangeError("the involutes of the two contours share no radius")
    radius = r_measured[inside]
    turned = psi_measured[inside] - np.interp(radius, r_nominal, psi_nominal)
    return 2.0 * radius, 1000.0 * base_radius_mm * turned


def _tip_window(contour: ct.ToothContour) -> tuple[float, float, float, float]:
    tip = 0.5 * contour.tip_diameter_mm
    tip_points = contour.segment("tip")
    half = float(np.abs(tip_points[:, 0]).max()) + 0.55
    return -half, half, tip - 0.95, tip + 0.1


def contour_deviation(
    nominal: ct.ToothContour, measured: ct.ToothContour
) -> tuple[np.ndarray, np.ndarray]:
    """The deviation of the manufactured contour from the nominal one along the left half of
    the tooth, from the root circle to the tip form point, normal to the nominal contour and
    in µm (plus = material outside the nominal contour), over the diameter of the manufactured
    point in mm: every manufactured point is projected onto the outward normal of the nearest
    nominal point (the contour runs clockwise around the tooth, so the outward normal is the
    tangent turned by 90° to the left). The root circle, the fillet, the involute and the
    relief are in it; the tip corner (arc or chamfer) is not, it is shown in true scale."""
    from scipy.spatial import cKDTree

    # the nominal flank alone (fillet and involute): the chamfer or arc of the nominal tip
    # corner must not catch the relieved points below it as their nearest neighbours
    nominal_xy = np.concatenate((nominal.segment("left_fillet"), nominal.segment("left_involute")))
    tangent = np.gradient(nominal_xy, axis=0)
    tangent /= np.hypot(tangent[:, 0], tangent[:, 1])[:, None]
    outward = np.column_stack((-tangent[:, 1], tangent[:, 0]))
    # the manufactured flank alone as well, up to the end of the shorter involute
    measured_xy = np.concatenate(
        (measured.segment("left_fillet"), measured.segment("left_involute"))
    )
    radius = np.hypot(measured_xy[:, 0], measured_xy[:, 1])
    limit = min(float(np.hypot(*nominal_xy[-1])), float(radius.max()))
    left = (measured_xy[:, 0] <= 0.0) & (radius <= limit)
    if not left.any():
        raise InputRangeError("the manufactured contour has no left flank below the tip form point")
    points = measured_xy[left]
    _, nearest = cKDTree(nominal_xy).query(points)
    deviation = np.einsum("ij,ij->i", points - nominal_xy[nearest], outward[nearest])
    order = np.argsort(radius[left])
    return 2.0 * radius[left][order], 1000.0 * deviation[order]


def _root_window(contour: ct.ToothContour) -> tuple[float, float, float, float]:
    root = 0.5 * contour.generated_root_diameter_mm
    return -1.5, 1.5, root - 0.1, root + 1.2


def _draw_contours(axis: Any, nominal: ct.ToothContour, measured: ct.ToothContour) -> None:
    nominal_xy, measured_xy = nominal.as_array(), measured.as_array()
    axis.plot(
        nominal_xy[:, 0],
        nominal_xy[:, 1],
        color="#000000",
        linestyle="-",
        marker="",
        linewidth=0.6,
        label=NOMINAL_LABEL,
    )
    axis.plot(
        measured_xy[:, 0],
        measured_xy[:, 1],
        color="C0",
        linestyle="-",
        marker="",
        linewidth=0.9,
        label=MEASURED_LABEL,
    )
    axis.set_aspect("equal")
    axis.set_xlabel(symbol_label("x", "mm"))
    axis.set_ylabel(symbol_label("y", "mm"))
    decimal_comma(axis)


def plot_gear(
    role: Role, nominal: ct.ToothContour, measured: ct.ToothContour, stem: Path
) -> list[Path]:
    """The root (top left) and the tip (top right) of the tooth in true scale, below the
    deviation of the manufactured contour from the nominal one over the diameter."""
    import matplotlib.pyplot as plt

    figure = plt.figure(figsize=figure_size("full", 0.8), layout="constrained")
    grid = figure.add_gridspec(2, 2)
    root = figure.add_subplot(grid[0, 0])
    tip = figure.add_subplot(grid[0, 1])
    deviation = figure.add_subplot(grid[1, :])
    for axis, window in ((root, _root_window(measured)), (tip, _tip_window(measured))):
        _draw_contours(axis, nominal, measured)
        x_low, x_high, y_low, y_high = window
        axis.set_xlim(x_low, x_high)
        axis.set_ylim(y_low, y_high)
    diameter, normal = contour_deviation(nominal, measured)
    deviation.axhline(0.0, color="#000000", linewidth=0.6, label=NOMINAL_LABEL)
    deviation.plot(
        diameter, normal, color="C0", linestyle="-", marker="", linewidth=0.9, label=MEASURED_LABEL
    )
    deviation.set_xlabel(symbol_label("d", "mm"))
    deviation.set_ylabel("Abweichung in µm (plus = Material)")
    decimal_comma(deviation)
    legend_outside(figure, where="bottom", ncol=2)
    written = save(figure, stem, check_overlaps=False)
    plt.close(figure)
    return written


def plot_teeth(
    contours: Mapping[Role, tuple[ct.ToothContour, ct.ToothContour]], stem: Path
) -> list[Path]:
    """The whole tooth of the pinion (left) and of the wheel (right) in true scale, nominal
    against manufactured, one shared legend below; no deviation panel (the user, 2026-10-25:
    the two tooth contours, not halved)."""
    import matplotlib.pyplot as plt

    figure, axes = new_figure("full", 0.52, cols=2)
    for axis, role in zip(axes, ("pinion", "wheel"), strict=True):
        nominal, measured = contours[role]
        _draw_contours(axis, nominal, measured)
    legend_outside(figure, where="bottom", ncol=2)
    written = save(figure, stem, check_overlaps=False)
    plt.close(figure)
    return written


def _tip_mesh_segments(mesh: sm.SectorMesh, tooth: int) -> np.ndarray:
    """Edges of the quads of the sector mesh near the tip of ``tooth``, turned so that the
    tooth centre lies on +y; (n, 2, 2) for a line collection."""
    turn = 0.5 * math.pi - mesh.tooth_centre_angle_rad(tooth)
    rotation = np.array([[math.cos(turn), -math.sin(turn)], [math.sin(turn), math.cos(turn)]])
    xy = mesh.points_mm @ rotation.T
    quads = mesh.quads[mesh.quad_tooth == tooth]
    edges = np.concatenate([quads[:, [k, (k + 1) % 4]] for k in range(4)])
    edges = np.unique(np.sort(edges, axis=1), axis=0)
    segments = xy[edges]
    near = (segments[:, :, 1].min(axis=1) > mesh.tip_radius_mm - 0.5) & (
        np.abs(segments[:, :, 0]).max(axis=1) < 0.9
    )
    return np.asarray(segments[near], dtype=np.float64)


def plot_mesh(measured: mf.ManufacturedResult, stem: Path) -> list[Path]:
    """The tip of the middle tooth of the sector mesh on the measured wheel without and with
    the cap of the tooth tip."""
    import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection

    modification = measured.modification("wheel")
    contour = ct.tooth_contour(
        measured.generation, "wheel", points=CONTOUR_POINTS, modification=modification
    )
    outline = contour.as_array()
    figure, axes = new_figure("full", 0.36, cols=2, sharey=True)
    mesh_label = (
        "Netz (links: Vorlage mit der Blockecke auf dem Bogen, FE-26; rechts: mit Kopfkappe)"
    )
    labels = (mesh_label, mesh_label)
    meshes = []
    for axis, cap_layers, label in zip(axes, (0, 1), labels, strict=True):
        counts = rs.MeshCounts(
            **{k: v for k, v in SERIES_COUNTS.__dict__.items() if k != "cap_layers"},
            cap_layers=cap_layers,
        )
        mesh = sm.sector_mesh(
            measured.generation,
            "wheel",
            teeth=3,
            rim_rings=12,
            bore_radius_mm=16.5,
            counts=counts,
            modification=modification,
        )
        meshes.append(mesh)
        segments = _tip_mesh_segments(mesh, 2)
        axis.add_collection(
            LineCollection(list(segments), colors="#000000", linewidths=0.4, label=label)
        )
        axis.plot(
            outline[:, 0],
            outline[:, 1],
            color="C0",
            linestyle="-",
            marker="",
            linewidth=0.9,
            label="Kontur des gemessenen Rades (Kopfkantenradius 0,21 mm)",
        )
        tip = mesh.tip_radius_mm
        axis.set_aspect("equal")
        axis.set_xlim(-0.75, 0.75)
        axis.set_ylim(tip - 0.45, tip + 0.05)
        axis.set_xlabel(symbol_label("x", "mm"))
        decimal_comma(axis)
    axes[0].set_ylabel(symbol_label("y", "mm"))
    legend_outside(figure, where="bottom", ncol=1)
    written = save(figure, stem, check_overlaps=False)
    plt.close(figure)
    return written


def _generations(case: str, variant: str) -> tuple[GenerationResult, mf.ManufacturedResult]:
    pair = pair_input_from_ste(load_ste(data.stplus_input_path(case))).pair
    return compute_generation(pair), mf.apply(pair, mf.load_variant(case, variant))


def run(out: Path, *, case: str = "kst_e", variant: str = "beide") -> list[Path]:
    """Write the four figures into ``out`` and return the paths."""
    apply_plot_style()
    nominal, measured = _generations(case, variant)
    written: list[Path] = []
    contours: dict[Role, tuple[ct.ToothContour, ct.ToothContour]] = {}
    for role in ("pinion", "wheel"):
        nominal_contour = ct.tooth_contour(nominal, role, points=CONTOUR_POINTS)
        measured_contour = ct.tooth_contour(
            measured.generation,
            role,
            points=CONTOUR_POINTS,
            modification=measured.modification(role),
        )
        contours[role] = (nominal_contour, measured_contour)
        written += plot_gear(
            role, nominal_contour, measured_contour, out / f"kontur_{GERMAN_ROLE[role].lower()}"
        )
    written += plot_teeth(contours, out / "kontur_zaehne")
    written += plot_mesh(measured, out / "netz_kopfkappe")
    return written


def base_radius_mm(generation: GenerationResult, contour: ct.ToothContour) -> float:
    """The base radius of the gear of ``contour`` from the pair input (DIN ISO 21771 Eq. 19)."""
    pair = generation.inputs
    return 0.5 * base_diameter(
        contour.number_of_teeth,
        pair.normal_module_mm,
        math.radians(pair.normal_pressure_angle_deg),
        math.radians(pair.helix_angle_deg),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--case", default="kst_e")
    parser.add_argument("--variant", default="beide")
    parser.add_argument("--out", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    for path in run(args.out, case=args.case, variant=args.variant):
        print(path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
