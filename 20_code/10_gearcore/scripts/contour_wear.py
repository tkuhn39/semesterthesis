"""Wear of the wheels after the running test from the contour scans (M5, 2026-10-21).

The three wheels 97340 (16 Nm), 97345 (8 Nm) and 97351 (12 Nm) were scanned again on the P40
after their run (``<ME>_Z<n>_gelaufen.DAT``). A worn flank defeats the free involute fit of
``contour_scan.fit_scan`` (the step of the worked-in tip edge pulls the axis by 1 to 3 mm,
seen 2026-10-21), and a flank fitted with its own involute hides a uniform removal in the
involute angle. Every scan, before and after, is therefore placed in two steps that use only
contour the pinion does not touch:

1. the axis is the centre that puts the tip runs on the tip radius and the root runs on the
   root radius GINA measured on the same part before its run (``axis_from_circles``, robust
   least squares with both radii fixed; with free radii the short arcs of three teeth let the
   centre slide along the tooth centre line);
2. every tooth is turned about that axis until its two root fillets, between the root circle
   and the root form circle, sit on the fillets of the nominal tooth (``fillet_frame``, one
   rotation angle, robust least squares of the signed distance to the nominal outline).

In that frame the signed distance of every point from the nominal outline
(``contour_scan.signed_deviation``, negative where material is missing) is laid over the
radius, per flank. The before-test population (every before-test wheel scan of the folder,
same two steps) gives the reference band (mean and standard deviation per hand); the wheel
97340 also has its own before-test scan of tooth 1. The wear of an after-test flank is its
deviation minus the reference mean: the mean over the active profile, the largest value and
its radius (the step), the radius above which the wear falls below 10 µm (the upper edge of
the step) and the loss within 0,5 mm of the tip. The base tooth thickness of the involute fit
about the fixed axis gives the removal of both flanks together as the check.

Outputs below ``80_output/messungen/konturscan/wheel_gelaufen``: ``verschleiss.csv`` (one row
per flank), ``achse.csv`` (the axis of every scan, with the free fit beside it on the
before-test scans), ``bericht.md``, the figure ``verschleiss_profil`` (three stacked panels,
one per load level, every after-test flank over the radius with the reference band), the
overlays ``ueberlagerung_<ME>_<scan>`` (after-test teeth on the nominal tooth) and
``ueberlagerung_97340_Z1_vorher_nachher``. Nothing here is a norm equation.
"""

from __future__ import annotations

import argparse
import csv
import io
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml
from scipy.optimize import least_squares

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import measurements as ms  # noqa: E402  (the sibling script: paths, generation, GINA, overlay)
from gearcore import data  # noqa: E402
from gearcore import pair as pr  # noqa: E402
from gearcore.errors import InputRangeError  # noqa: E402
from gearcore.io.p40_contour import ContourScan, load_contour_scans  # noqa: E402
from gearcore.measurement import contour_scan as cs  # noqa: E402
from gearcore.measurement.inventory import MeasuredPart, MeasurementFile, scan_folder  # noqa: E402
from gearcore.plot_style import LINE_STYLES  # noqa: E402
from gearcore.plot_style import apply as apply_plot_style  # noqa: E402
from gearcore.plot_style import (  # noqa: E402
    decimal_comma,
    german_number,
    legend_outside,
    new_figure,
    save,
    symbol_label,
)

OUTPUT = ms.OUTPUT / "konturscan" / "wheel_gelaufen"
FAILED_TEETH = Path(data.__file__).resolve().parent / "measurement" / "failed_teeth_user.yaml"
EDGE_CONTACT_RADIUS_MM = 25.80
"""Radius of the wheel node row under the rounded pinion tip edge in the FE series (the global
maximum of the utilisation in 5.3; ``tasche_serie_w1w4_qs_gerechnet/analyse``)."""
STEP_WINDOW_HIGH_MM = 26.5
"""The step of the worked-in tip edge is searched below this radius."""
STEP_EDGE_UM = 10.0
"""Wear that marks the upper edge of the step."""
ONSET_UM = 20.0
"""The worn zone begins at the lowest radius where the wear exceeds this for good."""
TIP_BAND_MM = (0.65, 0.25)
"""The tip loss is the mean wear between r_a − 0,65 and r_a − 0,25 mm, below the tip corner of
0,21 mm (user 2026-10-21: the corner itself is no part of the profile view)."""
PLOT_BELOW_TIP_MM = 0.25
"""The profile view ends this far below the nominal tip radius, where the tip corner begins."""
ACTIVE_MARGIN_MM = 0.1
"""The mean wear is taken over the active profile from r_Ff + this to r_a − this."""
FILLET_ABOVE_ROOT_MM = 0.04
"""Fillet points for the rotation start this far above the GINA root radius."""
FILLET_BELOW_FORM_MM = 0.03
"""... and end this far below the nominal root form radius."""
GRID_STEP_MM = 0.01


@dataclass(frozen=True)
class CircleAxis:
    centre_mm: tuple[float, float]
    tip_radius_mm: float
    root_radius_mm: float
    tip_runs_used: int
    root_runs_used: int
    rms_um: float


@dataclass(frozen=True)
class ToothWear:
    """One tooth of a scan in the frame of the nominal tooth (axis at the origin, the tooth
    centre line on +y) after the rotation on the fillets."""

    me: str
    scan: str
    tooth_label: str
    points_mm: np.ndarray
    theta_rad: float
    fillet_rms_um: float
    fillet_points: int
    s_b_mm: float


@dataclass(frozen=True)
class FlankCurve:
    me: str
    scan: str
    tooth_label: str
    hand: int
    """−1: right flank (+x, scanned first); +1: left flank."""
    r_mm: np.ndarray
    deviation_um: np.ndarray
    """Signed distance from the nominal outline, negative where material is missing."""


@dataclass(frozen=True)
class Reference:
    hand: int
    r_mm: np.ndarray
    mean_um: np.ndarray
    std_um: np.ndarray
    flanks: int


@dataclass(frozen=True)
class WearRow:
    me: str
    level_Nm: int | None
    scan: str
    tooth_label: str
    hand: int
    wear_mean_um: float
    wear_max_um: float
    wear_max_r_mm: float
    onset_r_mm: float | None
    """Lowest radius above which the wear stays above ``ONSET_UM`` (the lower edge of the
    worn zone, where the pinion tip edge first touches the flank)."""
    step_edge_mm: float | None
    tip_loss_um: float | None
    fractured: bool
    """The tooth is in the user's list of broken or root-fractured teeth: its scan shows
    fracture surfaces, the values stay in the table and out of the figures and summaries."""
    delta_s_b_um: float | None
    """Base tooth thickness of the tooth minus the before-test mean (both flanks together)."""
    fillet_rms_um: float
    corner_arc_mm: float | None
    rms_flank_um: float


# ---- axis and frame ----------------------------------------------------------------------------


def axis_from_circles(
    scan: ContourScan, runs: tuple[cs.Run, ...], tip_radius_mm: float, root_radius_mm: float
) -> CircleAxis:
    """The centre that puts the tip runs on ``tip_radius_mm`` and the root runs on
    ``root_radius_mm`` (soft-L1 loss, scale 20 µm, the roots weighted twice because they do
    not wear); a run whose median residual exceeds 0,1 mm (a broken tooth, a fracture surface
    taken for a root) is dropped and the fit repeated once."""
    xy = scan.as_array()

    def solve(tip_runs: list[cs.Run], root_runs: list[cs.Run]) -> tuple[np.ndarray, float]:
        tips = np.vstack([xy[r.start : r.stop + 1] for r in tip_runs])
        roots = np.vstack([xy[r.start : r.stop + 1] for r in root_runs])

        def residual(p: np.ndarray) -> np.ndarray:
            d_t = np.hypot(tips[:, 0] - p[0], tips[:, 1] - p[1]) - tip_radius_mm
            d_r = np.hypot(roots[:, 0] - p[0], roots[:, 1] - p[1]) - root_radius_mm
            return np.concatenate((d_t, 2.0 * d_r))

        result = least_squares(residual, np.zeros(2), loss="soft_l1", f_scale=0.02)
        return np.asarray(result.x, dtype=float), float(np.sqrt(np.mean(result.fun**2)))

    tip_runs = [r for r in runs if r.kind == "tip"]
    root_runs = [r for r in runs if r.kind == "root"]
    if len(tip_runs) < 2 or len(root_runs) < 1:
        raise InputRangeError(f"{scan.name}: too few tip or root runs for the circle axis")
    p, rms = solve(tip_runs, root_runs)

    def keep(run: cs.Run, radius: float) -> bool:
        pts = xy[run.start : run.stop + 1]
        median = float(np.median(np.hypot(pts[:, 0] - p[0], pts[:, 1] - p[1])))
        return abs(median - radius) <= 0.1

    kept_tips = [r for r in tip_runs if keep(r, tip_radius_mm)]
    kept_roots = [r for r in root_runs if keep(r, root_radius_mm)]
    if len(kept_tips) >= 2 and len(kept_roots) >= 1 and (
        len(kept_tips) < len(tip_runs) or len(kept_roots) < len(root_runs)
    ):
        p, rms = solve(kept_tips, kept_roots)
    else:
        kept_tips, kept_roots = tip_runs, root_runs
    return CircleAxis(
        centre_mm=(float(p[0]), float(p[1])),
        tip_radius_mm=tip_radius_mm,
        root_radius_mm=root_radius_mm,
        tip_runs_used=len(kept_tips),
        root_runs_used=len(kept_roots),
        rms_um=1000.0 * rms,
    )


def evaluate_fixed(
    scan: ContourScan,
    geometry: cs.ScanGeometry,
    settings: cs.FitSettings,
    tip_radius_mm: float,
    root_radius_mm: float,
) -> tuple[cs.ScanEvaluation, CircleAxis]:
    """``contour_scan.evaluate_scan`` with the axis fixed at the circle centre."""
    runs = cs.segment(scan, settings)
    axis = axis_from_circles(scan, runs, tip_radius_mm, root_radius_mm)
    fit = cs.fit_axis(scan, runs, geometry, settings, fixed_centre=axis.centre_mm)
    found: list[cs.CornerFit] = []
    for k in range(len(fit.tip_runs)):
        for side in ("right", "left"):
            result = cs.measure_corner(scan, fit, k, side, settings)
            if result is not None:
                found.append(result)
    points = scan.as_array()
    ev = cs.ScanEvaluation(
        name=scan.name,
        block=scan.block,
        z_mm=scan.z_mm,
        points=len(points),
        coarse=len(points) < settings.coarse_points,
        geometry=geometry,
        settings=settings,
        runs=runs,
        fit=fit,
        reliefs=cs.flank_reliefs(points, fit, geometry, settings),
        teeth=cs.tooth_thicknesses(fit, geometry),
        pitches=cs.angular_pitches(fit),
        corners=tuple(found),
    )
    return ev, axis


def _rotate(points: np.ndarray, theta: float) -> np.ndarray:
    """Points about the origin turned so that the polar angle ``theta`` (from +y towards +x)
    lies on +y (as ``contour_scan.tooth_points``)."""
    c, s = math.cos(theta), math.sin(theta)
    return np.asarray(
        np.column_stack((c * points[:, 0] - s * points[:, 1], s * points[:, 0] + c * points[:, 1])),
        dtype=float,
    )


def fillet_frame(
    scan: ContourScan,
    ev: cs.ScanEvaluation,
    tooth: cs.ToothThickness,
    axis: CircleAxis,
    geometry: cs.ScanGeometry,
    outline: np.ndarray,
    me: str,
    label: str,
) -> ToothWear:
    """The tooth from the middle of the root before it to the middle of the root after it,
    turned on its fillets onto the nominal tooth; the involute centre line is the start."""
    runs = ev.runs
    fit = ev.fit
    right = fit.flank_runs[tooth.right_flank]
    left = fit.flank_runs[tooth.right_flank + 1]
    before = [r for r in runs if r.kind == "root" and r.stop < right.start]
    after = [r for r in runs if r.kind == "root" and r.start > left.stop]
    first = (before[-1].start + before[-1].stop) // 2 if before else right.start
    last = (after[0].start + after[0].stop) // 2 if after else left.stop
    xy = scan.as_array()[first : last + 1] - np.asarray(axis.centre_mm, dtype=float)
    r = np.hypot(xy[:, 0], xy[:, 1])
    fillet = (r > axis.root_radius_mm + FILLET_ABOVE_ROOT_MM) & (
        r < geometry.r_ff - FILLET_BELOW_FORM_MM
    )
    if fillet.sum() < 6:
        raise InputRangeError(f"{scan.name} {label}: fewer than 6 fillet points for the rotation")
    pts = xy[fillet]

    def residual(p: np.ndarray) -> np.ndarray:
        return cs.closest_on_outline(_rotate(pts, float(p[0])), outline)[1]

    result = least_squares(
        residual, np.array([tooth.theta_centre_rad]), loss="soft_l1", f_scale=0.02
    )
    theta = float(result.x[0])
    return ToothWear(
        me=me,
        scan=scan.name,
        tooth_label=label,
        points_mm=_rotate(xy, theta),
        theta_rad=theta,
        fillet_rms_um=1000.0 * float(np.sqrt(np.mean(result.fun**2))),
        fillet_points=int(fillet.sum()),
        s_b_mm=tooth.s_b_mm,
    )


def flank_curves(
    tooth: ToothWear, geometry: cs.ScanGeometry, outline: np.ndarray
) -> list[FlankCurve]:
    """The two flanks of the tooth above the root form circle: right (+x) and left (−x)."""
    pts = tooth.points_mm
    r = np.hypot(pts[:, 0], pts[:, 1])
    deviation = cs.signed_deviation(pts, outline)
    out: list[FlankCurve] = []
    for hand, side in ((-1, pts[:, 0] > 0.0), (1, pts[:, 0] < 0.0)):
        ok = side & (r >= geometry.r_ff) & (r <= geometry.r_a + 0.05)
        if ok.sum() < 10:
            continue
        order = np.argsort(r[ok])
        out.append(
            FlankCurve(
                me=tooth.me,
                scan=tooth.scan,
                tooth_label=tooth.tooth_label,
                hand=hand,
                r_mm=np.asarray(r[ok][order], dtype=float),
                deviation_um=np.asarray(deviation[ok][order], dtype=float),
            )
        )
    return out


def _tooth_labels(ev: cs.ScanEvaluation, file: MeasurementFile) -> dict[int, str]:
    """Tooth index of the scan -> label; the middle tooth of a scan is the tooth of the file
    name (as ``measurements._frame_labels``), a file with two named teeth names both."""
    teeth = ev.teeth
    labels: dict[int, str] = {}
    middle = len(teeth) // 2
    for k in range(len(teeth)):
        if file.second_tooth is not None and len(teeth) == 2:
            labels[k] = f"Zahn {file.tooth}" if k == 0 else f"Zahn {file.second_tooth}"
        elif k == middle:
            labels[k] = f"Zahn {file.tooth}" if file.tooth is not None else "Zahn ?"
        elif k < middle:
            labels[k] = "Nachbar +x" if middle - k == 1 else f"Nachbar +x ({middle - k})"
        else:
            labels[k] = "Nachbar −x" if k - middle == 1 else f"Nachbar −x ({k - middle})"
    return labels


# ---- reference and metrics ---------------------------------------------------------------------


def _grid(geometry: cs.ScanGeometry) -> np.ndarray:
    return np.asarray(np.arange(geometry.r_ff, geometry.r_a + GRID_STEP_MM, GRID_STEP_MM), dtype=float)


def _on_grid(curve: FlankCurve, grid: np.ndarray) -> np.ndarray:
    r, index = np.unique(curve.r_mm, return_index=True)
    values = np.interp(grid, r, curve.deviation_um[index], left=np.nan, right=np.nan)
    return np.asarray(values, dtype=float)


def references(curves: list[FlankCurve], grid: np.ndarray) -> dict[int, Reference]:
    out: dict[int, Reference] = {}
    for hand in (-1, 1):
        stack = np.array([_on_grid(c, grid) for c in curves if c.hand == hand])
        if len(stack) == 0:
            continue
        count = np.sum(np.isfinite(stack), axis=0)
        mean = np.full(len(grid), np.nan)
        std = np.full(len(grid), np.nan)
        enough = count >= 3
        if enough.any():
            sub = stack[:, enough]
            mean[enough] = np.nanmean(sub, axis=0)
            std[enough] = np.nanstd(sub, axis=0, ddof=1)
        out[hand] = Reference(hand=hand, r_mm=grid, mean_um=mean, std_um=std, flanks=len(stack))
    return out


def wear_row(
    curve: FlankCurve,
    ref: Reference,
    grid: np.ndarray,
    geometry: cs.ScanGeometry,
    level: int | None,
    delta_s_b_um: float | None,
    fillet_rms_um: float,
    corner_arc_mm: float | None,
    rms_flank_um: float,
    fractured: bool = False,
) -> WearRow:
    wear = ref.mean_um - _on_grid(curve, grid)  # material missing counts positive
    active = (grid >= geometry.r_ff + ACTIVE_MARGIN_MM) & (grid <= geometry.r_a - ACTIVE_MARGIN_MM)
    ok = np.isfinite(wear)
    mean = float(np.mean(wear[active & ok])) if (active & ok).any() else math.nan
    window = (grid <= STEP_WINDOW_HIGH_MM) & ok
    peak = math.nan
    peak_r = math.nan
    edge: float | None = None
    if window.any():
        k_max = int(np.flatnonzero(window)[np.argmax(wear[window])])
        peak = float(wear[k_max])
        peak_r = float(grid[k_max])
        above = np.flatnonzero((grid > grid[k_max]) & ok & (wear < STEP_EDGE_UM))
        if len(above):
            edge = float(grid[above[0]])
    near_tip = (grid > geometry.r_a - TIP_BAND_MM[0]) & (grid < geometry.r_a - TIP_BAND_MM[1]) & ok
    tip_loss = float(np.mean(wear[near_tip])) if near_tip.any() else None
    onset: float | None = None
    below = np.flatnonzero(ok & (wear < ONSET_UM) & (grid < STEP_WINDOW_HIGH_MM))
    worn = np.flatnonzero(ok & (wear >= ONSET_UM))
    if len(worn) and (not len(below) or below[-1] < worn[-1]):
        # the last point below the threshold before the worn zone that reaches the step window
        last_below = below[below < worn[-1]]
        onset = float(grid[last_below[-1] + 1]) if len(last_below) else float(grid[worn[0]])
    return WearRow(
        me=curve.me,
        level_Nm=level,
        scan=curve.scan,
        tooth_label=curve.tooth_label,
        hand=curve.hand,
        wear_mean_um=mean,
        wear_max_um=peak,
        wear_max_r_mm=peak_r,
        onset_r_mm=onset,
        step_edge_mm=edge,
        tip_loss_um=tip_loss,
        fractured=fractured,
        delta_s_b_um=delta_s_b_um,
        fillet_rms_um=fillet_rms_um,
        corner_arc_mm=corner_arc_mm,
        rms_flank_um=rms_flank_um,
    )


def _hand_label(hand: int) -> str:
    return "rechts (+x)" if hand < 0 else "links (−x)"


def _tooth_sort(label: str) -> tuple[int, str]:
    number = _tooth_number(label)
    return (number if number is not None else 999, label)


def _short_hand(hand: int) -> str:
    """The right flank (+x) of every after-test scan is the loaded one (6.2), the left flank
    the unloaded one; the figure names them so (user 2026-10-21)."""
    return "belastet" if hand < 0 else "unbelastet"


def _n(value: float | None, digits: int) -> str:
    return "–" if value is None or not math.isfinite(value) else german_number(value, digits)


def _corner_arc(ev: cs.ScanEvaluation, flank_index: int, hand: int) -> float | None:
    k_tip = ev.fit.flank_tip[flank_index]
    side = "right" if hand < 0 else "left"
    for corner in ev.corners:
        if corner.tip_index == k_tip and corner.side == side:
            return float(corner.arc_radius_mm) if corner.better_shape == "arc" else None
    return None


def _levels() -> dict[str, tuple[int, str]]:
    raw = yaml.safe_load(FAILED_TEETH.read_text(encoding="utf-8")) or {}
    wheels = raw.get("wheels") or {}
    out: dict[str, tuple[int, str]] = {}
    for me, entry in wheels.items():
        if isinstance(entry, dict) and "level_Nm" in entry:
            out[str(me)] = (int(entry["level_Nm"]), str(entry.get("run", "")))
    return out


def _fractured() -> dict[str, set[int]]:
    """ME -> teeth broken off or fractured at the root in the user's inspection list."""
    raw = yaml.safe_load(FAILED_TEETH.read_text(encoding="utf-8")) or {}
    wheels = raw.get("wheels") or {}
    out: dict[str, set[int]] = {}
    for me, entry in wheels.items():
        if isinstance(entry, dict):
            teeth = set(entry.get("broken_off") or []) | set(entry.get("root_fracture") or [])
            out[str(me)] = {int(n) for n in teeth}
    return out


def _is_fractured(me: str, label: str) -> bool:
    number = _tooth_number(label)
    return number is not None and number in _fractured().get(me, set())


def _tooth_number(label: str) -> int | None:
    parts = label.split()
    return int(parts[1]) if len(parts) == 2 and parts[0] == "Zahn" and parts[1].isdigit() else None


# ---- plots -------------------------------------------------------------------------------------


def plot_profiles(
    panels: list[tuple[str, list[FlankCurve]]],
    refs: dict[int, Reference],
    geometry: cs.ScanGeometry,
    marks: dict[str, float],
    stem: Path,
) -> list[Path]:
    """One panel per load level: every after-test flank over the radius as its deviation from
    the nominal tooth, the band of the before-test population behind it; solid lines right
    flanks, dashed left flanks, one colour per tooth."""
    figure, axes = new_figure("full", 1.1, rows=len(panels), sharex=True)
    axes = np.atleast_1d(axes)
    low, high = 0.0, 0.0
    r_end = geometry.r_a - PLOT_BELOW_TIP_MM
    all_teeth = sorted(
        {c.tooth_label for _, cs_ in panels for c in cs_ if not c.tooth_label.startswith("Nachbar")},
        key=_tooth_sort,
    )
    for axis, (title, all_curves) in zip(axes, panels, strict=True):
        curves = [c for c in all_curves if not c.tooth_label.startswith("Nachbar")]
        for hand, shade in ((-1, "#8c8c8c"), (1, "#c8c8c8")):
            ref = refs.get(hand)
            if ref is None:
                continue
            ok = np.isfinite(ref.mean_um) & (ref.r_mm <= r_end)
            axis.fill_between(
                ref.r_mm[ok],
                (ref.mean_um - ref.std_um)[ok],
                (ref.mean_um + ref.std_um)[ok],
                color=shade,
                alpha=0.6,
                linewidth=0.0,
                label=f"vor dem Lauf {_short_hand(hand)}, Mittel ± s ({ref.flanks} Flanken)",
            )
        for curve in curves:
            k = all_teeth.index(curve.tooth_label)
            keep = curve.r_mm <= r_end
            axis.plot(
                curve.r_mm[keep],
                curve.deviation_um[keep],
                marker="",
                linewidth=0.9,
                linestyle=LINE_STYLES[k % len(LINE_STYLES)],
                color=f"C{k % 10}" if curve.hand < 0 else "0.55",
                label=f"{curve.tooth_label} {_short_hand(curve.hand)}",
            )
            low = min(low, float(np.nanmin(curve.deviation_um[keep])))
            high = max(high, float(np.nanmax(curve.deviation_um[keep])))
        for style, (label, value) in zip((":", "-.", "--"), marks.items(), strict=True):
            axis.axvline(
                value,
                color="#000000",
                linewidth=0.6,
                linestyle=style,
                label=f"{label} {german_number(value, 2)} mm",
            )
        axis.set_title(title)
        decimal_comma(axis)
    axes[len(axes) // 2].set_ylabel("Abweichung von der Sollkontur in µm")
    axes[-1].set_xlabel(symbol_label("r", "mm"))
    for axis in axes:
        axis.set_ylim(min(-50.0, 1.1 * low), max(50.0, 1.1 * high))
        axis.set_xlim(geometry.r_ff - 0.05, r_end + 0.05)
    legend_outside(figure, where="bottom", ncol=2)
    written = save(figure, stem, check_overlaps=False)
    import matplotlib.pyplot as plt

    plt.close(figure)
    return written


def plot_contours(
    panels: list[tuple[str, list[ToothWear]]],
    before: ToothWear | None,
    outline: np.ndarray,
    stem: Path,
) -> list[Path]:
    """One panel per wheel: the scanned teeth after the run on the nominal tooth, the deviation
    not magnified, one dash pattern per tooth; the before-test scan of the same tooth in grey
    where one exists (97340 tooth 1)."""
    figure, axes = new_figure("full", 0.5, cols=len(panels), sharey=True)
    axes = np.atleast_1d(axes)
    all_teeth = sorted(
        {t.tooth_label for _, ts in panels for t in ts if not t.tooth_label.startswith("Nachbar")},
        key=_tooth_sort,
    )
    for axis, (title, teeth) in zip(axes, panels, strict=True):
        axis.plot(
            outline[:, 0], outline[:, 1], color="#000000", linestyle="-", marker="",
            linewidth=0.6, label="Sollkontur (STplus-Erzeugung)",
        )
        if before is not None and before.me == title.split(",")[0]:
            pts = before.points_mm
            axis.plot(
                pts[:, 0], pts[:, 1], color="0.55", linestyle="-", marker="", linewidth=0.9,
                label=f"{before.tooth_label} vor dem Lauf",
            )
        named = [
            t for t in teeth
            if not t.tooth_label.startswith("Nachbar") and not _is_fractured(t.me, t.tooth_label)
        ]
        named.sort(key=lambda t: _tooth_sort(t.tooth_label))
        for tooth in named:
            k = all_teeth.index(tooth.tooth_label)
            pts = tooth.points_mm
            axis.plot(
                pts[:, 0], pts[:, 1], marker="", linewidth=0.9,
                linestyle=LINE_STYLES[k % len(LINE_STYLES)], color=f"C{k % 10}",
                label=f"{tooth.tooth_label} nach dem Lauf",
            )
        axis.set_aspect("equal")
        axis.set_xlim(-1.7, 1.7)
        axis.set_ylim(24.4, 27.3)
        axis.set_title(title)
        axis.set_xlabel(symbol_label("x", "mm"))
        decimal_comma(axis)
    axes[0].set_ylabel(symbol_label("y", "mm"))
    legend_outside(figure, where="bottom", ncol=3)
    written = save(figure, stem, check_overlaps=False)
    import matplotlib.pyplot as plt

    plt.close(figure)
    return written


# ---- the run -----------------------------------------------------------------------------------


AfterItem = tuple[MeasuredPart, MeasurementFile, ContourScan, cs.ScanEvaluation, CircleAxis]
AxisRow = tuple[str, str, bool, CircleAxis, float, tuple[float, float] | None]


def run(input_dir: Path, out: Path, *, case: str = "kst_e", magnify: float = 1.0) -> list[Path]:
    inventory = scan_folder(input_dir)
    generation = ms._generation(case)
    geometry = cs.scan_geometry(generation, "wheel")
    settings = cs.DEFAULT_SETTINGS
    grid = _grid(geometry)
    levels = _levels()
    fractured = _fractured()
    root = Path(inventory.root)
    out.mkdir(parents=True, exist_ok=True)
    apply_plot_style()
    outline = cs.nominal_outline(generation, "wheel")
    gina = ms.gina_sizes(inventory, "wheel", None)
    pg = generation.pair_geometry
    r_nf2 = 0.5 * pr.sap_diameter(
        pg.centre_distance_mm,
        math.radians(pg.transverse_working_pressure_angle_deg),
        pg.tip_form_diameter_mm.pinion,
        2.0 * cs.scan_geometry(generation, "pinion").r_b,
        2.0 * geometry.r_b,
    )
    r_w2 = 0.5 * pg.working_pitch_diameter_mm.wheel
    marks = {
        "Fußnutzkreis Rechnung": r_nf2,
        "Kantenkontakt FE": EDGE_CONTACT_RADIUS_MM,
        "Wälzkreis": r_w2,
    }

    before_curves: list[FlankCurve] = []
    before_sb: list[float] = []
    before_arcs: list[float] = []
    before_fillet_rms: list[float] = []
    before_tooth_97340: ToothWear | None = None
    after: list[AfterItem] = []
    axis_rows: list[AxisRow] = []
    notes: list[str] = []
    for part in inventory.parts:
        if part.part != "wheel":
            continue
        size = gina.get(part.me)
        if size is None or size.tip_radius_mm is None or size.root_radius_mm is None:
            notes.append(f"{part.me}: keine GINA-Kopf- und Fußkreise, Scans übergangen")
            continue
        for file in sorted(part.of_kind("contour"), key=lambda f: (f.tooth or 0, f.path)):
            if any("coarse" in note for note in file.anomalies):
                continue
            for scan in load_contour_scans(root / file.path):
                try:
                    ev, axis = evaluate_fixed(
                        scan, geometry, settings, size.tip_radius_mm, size.root_radius_mm
                    )
                except InputRangeError as error:
                    notes.append(f"{part.me} {scan.name}: nicht auswertbar ({error})")
                    continue
                free_centre: tuple[float, float] | None = None
                if not file.after_test:
                    try:
                        free_centre = cs.fit_scan(scan, geometry, settings, None)[1].centre_mm
                    except InputRangeError:
                        free_centre = None
                axis_rows.append(
                    (part.me, scan.name, file.after_test, axis, ev.fit.rms_flank_um, free_centre)
                )
                if file.after_test:
                    after.append((part, file, scan, ev, axis))
                    continue
                labels = _tooth_labels(ev, file)
                for k, tooth in enumerate(ev.teeth):
                    try:
                        frame = fillet_frame(
                            scan, ev, tooth, axis, geometry, outline, part.me, labels[k]
                        )
                    except InputRangeError as error:
                        notes.append(f"{part.me} {scan.name}: {error}")
                        continue
                    before_curves += flank_curves(frame, geometry, outline)
                    before_sb.append(tooth.s_b_mm)
                    before_fillet_rms.append(frame.fillet_rms_um)
                    if part.me == "97340" and file.tooth == 1 and k == len(ev.teeth) // 2:
                        before_tooth_97340 = frame
                before_arcs += [c.arc_radius_mm for c in ev.corners if c.better_shape == "arc"]
    refs = references(before_curves, grid)
    sb_mean = float(np.mean(before_sb)) if before_sb else None
    sb_std = float(np.std(before_sb, ddof=1)) if len(before_sb) > 1 else None
    arc_mean = float(np.mean(before_arcs)) if before_arcs else None

    rows: list[WearRow] = []
    panels: dict[str, list[FlankCurve]] = {}
    tooth_panels: dict[str, list[ToothWear]] = {}
    written: list[Path] = []
    for part, file, scan, ev, axis in after:
        labels = _tooth_labels(ev, file)
        level = levels.get(part.me, (None, ""))[0]
        frames: list[ToothWear] = []
        for k, tooth in enumerate(ev.teeth):
            try:
                frame = fillet_frame(scan, ev, tooth, axis, geometry, outline, part.me, labels[k])
            except InputRangeError as error:
                notes.append(f"{part.me} {scan.name}: {error}")
                continue
            frames.append(frame)
            tooth_panels.setdefault(part.me, []).append(frame)
            delta_sb = None if sb_mean is None else 1000.0 * (tooth.s_b_mm - sb_mean)
            number = _tooth_number(labels[k])
            broken = number is not None and number in fractured.get(part.me, set())
            for curve in flank_curves(frame, geometry, outline):
                ref = refs.get(curve.hand)
                if ref is None:
                    continue
                flank_index = tooth.right_flank if curve.hand < 0 else tooth.right_flank + 1
                rows.append(
                    wear_row(
                        curve,
                        ref,
                        grid,
                        geometry,
                        level,
                        delta_sb,
                        frame.fillet_rms_um,
                        _corner_arc(ev, flank_index, curve.hand),
                        ev.fit.rms_flank_um,
                        fractured=broken,
                    )
                )
                if not broken:
                    panels.setdefault(part.me, []).append(curve)
        tooth_name = f"Zahn {file.tooth}" if file.tooth is not None else "Zahn ?"
        if frames:
            written += ms.plot_overlay(
                [(f.tooth_label, _as_frame(f)) for f in frames],
                outline,
                magnify,
                "",
                out / f"ueberlagerung_{part.me}_{scan.name}",
            )
            if before_tooth_97340 is not None and part.me == "97340" and file.tooth == 1:
                middle = frames[len(frames) // 2]
                written += ms.plot_overlay(
                    [
                        ("vor dem Lauf", _as_frame(before_tooth_97340)),
                        ("nach dem Lauf", _as_frame(middle)),
                    ],
                    outline,
                    magnify,
                    "",
                    out / f"ueberlagerung_{part.me}_Z1_vorher_nachher",
                )

    order = sorted(panels, key=lambda me: levels.get(me, (0, ""))[0])
    titled = [(f"{me}, {levels[me][0]} Nm" if me in levels else me, panels[me]) for me in order]
    if titled:
        written += plot_profiles(titled, refs, geometry, marks, out / "verschleiss_profil")
        written += plot_contours(
            [(f"{me}, {levels[me][0]} Nm" if me in levels else me, tooth_panels[me]) for me in order],
            before_tooth_97340,
            outline,
            out / "verschleiss_kontur",
        )

    written += _tables(
        out, rows, axis_rows, refs, geometry, marks, sb_mean, sb_std, len(before_sb), arc_mean,
        len(before_arcs), before_fillet_rms, notes,
    )
    return written


def _as_frame(tooth: ToothWear) -> cs.ToothFrame:
    return cs.ToothFrame(
        tooth=0,
        theta_centre_rad=tooth.theta_rad,
        first_index=0,
        last_index=len(tooth.points_mm) - 1,
        points_mm=tuple((float(p[0]), float(p[1])) for p in tooth.points_mm),
    )


def _tables(
    out: Path,
    rows: list[WearRow],
    axis_rows: list[AxisRow],
    refs: dict[int, Reference],
    geometry: cs.ScanGeometry,
    marks: dict[str, float],
    sb_mean: float | None,
    sb_std: float | None,
    sb_count: int,
    arc_mean: float | None,
    arc_count: int,
    before_fillet_rms: list[float],
    notes: list[str],
) -> list[Path]:
    written: list[Path] = []
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        ["me", "level_Nm", "scan", "tooth", "hand", "fractured", "wear_mean_um", "wear_max_um",
         "wear_max_r_mm", "onset_r_mm", "step_edge_mm", "tip_loss_um", "delta_s_b_um",
         "fillet_rms_um", "corner_arc_mm", "rms_flank_um"]
    )
    for row in rows:
        writer.writerow(
            [row.me, "" if row.level_Nm is None else row.level_Nm, row.scan, row.tooth_label,
             _hand_label(row.hand), int(row.fractured), repr(row.wear_mean_um),
             repr(row.wear_max_um), repr(row.wear_max_r_mm),
             "" if row.onset_r_mm is None else repr(row.onset_r_mm),
             "" if row.step_edge_mm is None else repr(row.step_edge_mm),
             "" if row.tip_loss_um is None else repr(row.tip_loss_um),
             "" if row.delta_s_b_um is None else repr(row.delta_s_b_um), repr(row.fillet_rms_um),
             "" if row.corner_arc_mm is None else repr(row.corner_arc_mm), repr(row.rms_flank_um)]
        )
    (out / "verschleiss.csv").write_text(buffer.getvalue(), encoding="utf-8", newline="\n")
    written.append(out / "verschleiss.csv")

    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        ["me", "scan", "after_test", "centre_x_mm", "centre_y_mm", "tip_radius_gina_mm",
         "root_radius_gina_mm", "tip_runs", "root_runs", "rms_circle_um", "rms_flank_um",
         "free_centre_x_mm", "free_centre_y_mm", "free_minus_circle_um"]
    )
    gaps: list[float] = []
    for me, name, is_after, axis, rms_flank, free_centre in axis_rows:
        gap = None
        if free_centre is not None:
            gap = 1000.0 * math.hypot(
                free_centre[0] - axis.centre_mm[0], free_centre[1] - axis.centre_mm[1]
            )
            if not is_after:
                gaps.append(gap)
        writer.writerow(
            [me, name, int(is_after), repr(axis.centre_mm[0]), repr(axis.centre_mm[1]),
             repr(axis.tip_radius_mm), repr(axis.root_radius_mm), axis.tip_runs_used,
             axis.root_runs_used, repr(axis.rms_um), repr(rms_flank),
             "" if free_centre is None else repr(free_centre[0]),
             "" if free_centre is None else repr(free_centre[1]),
             "" if gap is None else repr(gap)]
        )
    (out / "achse.csv").write_text(buffer.getvalue(), encoding="utf-8", newline="\n")
    written.append(out / "achse.csv")

    fillet_median = float(np.median(before_fillet_rms)) if before_fillet_rms else None
    lines = [
        "# Verschleiß der gelaufenen Räder aus den Konturscans (M5)",
        "",
        f"Nenngeometrie (kst-E): r_b = {_n(geometry.r_b, 4)} mm, r_Ff = {_n(geometry.r_ff, 4)} mm, "
        f"r_a = {_n(geometry.r_a, 4)} mm. Achse je Scan: Mittelpunkt zu den GINA-Kopf- und "
        "Fußkreisen des Teils (achse.csv); Zahn je Scan auf seinen Fußrundungen auf den Sollzahn "
        "gedreht; Abweichung von der Sollkontur normal, negativ = Material fehlt. Referenz: alle "
        "Vorher-Scans der Räder des Ordners, "
        + ", ".join(f"{_hand_label(h)} {r.flanks} Flanken" for h, r in sorted(refs.items()))
        + f"; Grundzahndicke vorher {_n(sb_mean, 4)} ± {_n(sb_std, 4)} mm ({sb_count} Zähne), "
        f"Kopfrundung vorher im Mittel {_n(arc_mean, 3)} mm ({arc_count} Ecken); RMS der "
        f"Fußrundungen um den Sollzahn vorher im Median {_n(fillet_median, 1)} µm.",
        "",
        "Achse: an den Vorher-Scans liegt der Kreis-Mittelpunkt im Median "
        f"{_n(float(np.median(gaps)) if gaps else None, 0)} µm (größte Abweichung "
        f"{_n(float(np.max(gaps)) if gaps else None, 0)} µm) neben der frei gefitteten Achse.",
        "",
        "Verschleiß = Referenzmittel − Abweichung (Material fehlt positiv). Mittel über das aktive "
        f"Profil r_Ff + {_n(ACTIVE_MARGIN_MM, 1)} bis r_a − {_n(ACTIVE_MARGIN_MM, 1)} mm; Maximum "
        f"unterhalb r = {_n(STEP_WINDOW_HIGH_MM, 1)} mm mit seinem Radius; obere Kante: erster "
        f"Gitterpunkt darüber mit Verschleiß < {_n(STEP_EDGE_UM, 0)} µm; Kopfabtrag: Mittel zwischen "
        f"r_a − {_n(TIP_BAND_MM[0], 2)} und r_a − {_n(TIP_BAND_MM[1], 2)} mm, unter der Kopfrundung; "
        f"Δs_b: Grundzahndicke des Zahns gegen das "
        f"Vorher-Mittel (beide Flanken zusammen); Beginn der Zone: kleinster Radius, ab dem der "
        f"Verschleiß {_n(ONSET_UM, 0)} µm übersteigt. Marken: "
        + ", ".join(f"{label} r = {_n(value, 3)} mm" for label, value in marks.items())
        + ".",
        "",
        "| ME | Stufe in Nm | Scan | Zahn | Flanke | Verschleiß Mittel in µm | Maximum in µm | "
        "r des Maximums in mm | Beginn der Zone in mm | obere Kante in mm | Kopfabtrag in µm | "
        "Δs_b in µm | RMS Fußrundung in µm | Kopfrundung in mm | RMS Flanken in µm |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for row in sorted(rows, key=lambda r: (r.level_Nm or 0, r.scan, r.tooth_label, r.hand)):
        tooth = row.tooth_label + (" (gebrochen)" if row.fractured else "")
        lines.append(
            f"| {row.me} | {row.level_Nm if row.level_Nm is not None else '–'} | {row.scan} | "
            f"{tooth} | {_hand_label(row.hand)} | {_n(row.wear_mean_um, 0)} | "
            f"{_n(row.wear_max_um, 0)} | {_n(row.wear_max_r_mm, 2)} | {_n(row.onset_r_mm, 2)} | "
            f"{_n(row.step_edge_mm, 2)} | {_n(row.tip_loss_um, 0)} | {_n(row.delta_s_b_um, 0)} | "
            f"{_n(row.fillet_rms_um, 1)} | {_n(row.corner_arc_mm, 2)} | {_n(row.rms_flank_um, 1)} |"
        )
    lines += ["", "## Je Rad (unversehrte, im Dateinamen benannte Zähne, belastete Flanke = rechts (+x))", "",
              "| ME | Stufe in Nm | Zähne | Verschleiß Mittel in µm | Maximum in µm | "
              "r des Maximums in mm | Beginn der Zone in mm | Kopfabtrag in µm | "
              "unbelastete Flanke Mittel in µm | Δs_b in µm |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    for me in sorted({r.me for r in rows}, key=lambda m: next((r.level_Nm or 0 for r in rows if r.me == m), 0)):
        named = [r for r in rows if r.me == me and not r.fractured and not r.tooth_label.startswith("Nachbar")]
        loaded = [r for r in named if r.hand < 0]
        free = [r for r in named if r.hand > 0]
        if not loaded:
            continue
        level = loaded[0].level_Nm

        def span(values: list[float], digits: int) -> str:
            return f"{_n(min(values), digits)} bis {_n(max(values), digits)}" if values else "–"

        lines.append(
            f"| {me} | {level if level is not None else '–'} | "
            + ", ".join(r.tooth_label for r in loaded)
            + f" | {span([r.wear_mean_um for r in loaded], 0)} | {span([r.wear_max_um for r in loaded], 0)} | "
            f"{span([r.wear_max_r_mm for r in loaded], 2)} | "
            f"{span([r.onset_r_mm for r in loaded if r.onset_r_mm is not None], 2)} | "
            f"{span([r.tip_loss_um for r in loaded if r.tip_loss_um is not None], 0)} | "
            f"{span([r.wear_mean_um for r in free], 0)} | "
            f"{span([r.delta_s_b_um for r in loaded if r.delta_s_b_um is not None], 0)} |"
        )
    if notes:
        lines += ["", "## Hinweise", ""] + [f"- {note}" for note in notes]
    (out / "bericht.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    written.append(out / "bericht.md")
    return written


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--input", type=Path, default=ms.INPUT)
    parser.add_argument("--out", type=Path, default=OUTPUT)
    parser.add_argument("--case", default="kst_e")
    parser.add_argument("--magnify", type=float, default=1.0)
    args = parser.parse_args(argv)
    for path in run(args.input, args.out, case=args.case, magnify=args.magnify):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
