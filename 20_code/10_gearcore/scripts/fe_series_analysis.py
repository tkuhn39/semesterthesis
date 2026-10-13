"""Analysis of a computed series folder over the path of contact (``build_fe_decks.py decks``
grid, computed on the full licence, fields extracted): the run itself (jobs, wall times,
broken-off jobs with the chattering nodes), the load history per material step, anisotropy
against plasticity (W1 → W3, W1 → W2, W3 → W4, W2 → W4) at the named points and at the maxima,
the extended contact and the margin of the grid, sharp against rounded pinion edge against a
reference folder at the common positions, the resolution of the grid (sub-grids), and the
design check after Stommel et al. per series from the output folders of ``fe_fatigue.py``.
Writes ``<folder>/analyse/analyse.md`` (German, the thesis-facing text) and the figures in the
house style. Nothing here is a norm equation: tables and figures of extracted results.

    uv run --all-extras python scripts/fe_series_analysis.py --folder DIR
        [--reference DIR [--reference-series NAME]] [--stommel LABEL=DIR ...] [--out DIR]
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from gearcore.errors import InputRangeError
from gearcore.fe import evaluation as ev
from gearcore.plot_style import apply as apply_plot_style
from gearcore.plot_style import legend_beside, legend_outside, new_figure
from gearcore.plot_style import save as save_figure

SHEET = apply_plot_style()

GLOBAL_QUANTITIES: tuple[tuple[str, str, str, float], ...] = (
    # quantity of evaluation.curve, label, unit, scale factor for the table
    ("pinion_rotation_rad", "Ritzeldrehung", "mrad", 1000.0),
    ("u_head_max", "Kopfverschiebung", "µm", 1000.0),
    ("p_max", "Kontaktdruck max", "MPa", 1.0),
    ("s1_max", "σ1 max (Zug, Fuß)", "MPa", 1.0),
    ("s3_min", "|σ3| max (Druck, Fuß)", "MPa", 1.0),
)
"""The global quantities of the path report, their German labels and table units."""
FORCE_THRESHOLD_N = 1.0
"""A tooth half carries load where its normal force exceeds this."""
RUN_LOG_LINE = re.compile(r"^(\S+) (start|end) (\S+)(?: exit (-?\d+), (.*))?$")
MSG_NODE = re.compile(r"NODE WHEEL-1\.(\d+) OF CONTACT PAIR")
MSG_TAIL_LINES = 400
STEP_LABELS = {"LOAD_8NM": "8 Nm", "LOAD_12NM": "12 Nm", "LOAD_16NM": "16 Nm"}
SERIES_LABELS = {
    "W1": "W1 linear-elastisch, isotrop",
    "W2": "W2 elastisch-plastisch, isotrop",
    "W3": "W3 linear-elastisch, anisotrop",
    "W4": "W4 elastisch-plastisch, anisotrop",
}
"""The material steps as a reader of the thesis knows them (ADR-116: W1 to W4)."""
RATE_LABELS = {"QS": "quasistatisch", "DY1": "Dehnrate 3 s$^{-1}$", "DY2": "Dehnrate 60 s$^{-1}$"}
"""The CONVERSE rate cards by their test speed (the cards of the user, ADR-116 item 44)."""
BODY_LABELS = {"ring": "Ringkörper", "pocket": "Taschenkörper"}


def rate_text(series: str) -> str:
    """``'W3_DY1'`` -> ``'Dehnrate 3 s⁻¹'``; the code itself for an unknown rate."""
    rate = rate_of(series)
    return RATE_LABELS.get(rate, rate)


def describe(manifest: Mapping[str, Any]) -> str:
    """What a folder is, for a legend: body, the layer division when borrowed from the pocket
    body, and the pinion tip edge (``'Taschenkörper, Kopfkante r = 0,10 mm'``)."""
    mesh = manifest.get("wheel_mesh", {})
    body = mesh.get("body", "ring")
    shape = str(body.get("shape", "ring")) if isinstance(body, dict) else str(body)
    text = BODY_LABELS.get(shape, shape)
    if shape == "ring" and mesh.get("levels") == "pocket":
        text += " (Schichtung des Taschenkörpers)"
    edge = manifest.get("pinion_surface", {}).get("tip_rounding_mm")
    text += f", Kopfkante r = {_g(float(edge), 2)} mm" if edge else ", Kopfkante scharf"
    return text


COMPARISONS: tuple[tuple[str, str, str], ...] = (
    ("W1", "W3", "Anisotropie (linear)"),
    ("W1", "W2", "Plastizität (isotrop)"),
    ("W3", "W4", "Plastizität (anisotrop)"),
    ("W2", "W4", "Anisotropie (plastisch)"),
)


# --- small helpers --------------------------------------------------------------------------------


def _g(value: float | None, digits: int = 1) -> str:
    """A number with a decimal comma for the German text, '–' for None, '∞' for infinity."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "–"
    if isinstance(value, float) and math.isinf(value):
        return "∞" if value > 0 else "−∞"
    text = f"{value:.{digits}f}"
    return text.replace(".", ",")


def _pct(value: float | None) -> str:
    if value is None:
        return "–"
    percent = value * 100.0
    if abs(percent) < 0.05:
        percent = 0.0  # no "-0,0 %"
    return f"{percent:+.1f} %".replace(".", ",")


def _table(header: Sequence[str], rows: Iterable[Sequence[str]]) -> list[str]:
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return lines


def step_of(series: str) -> str:
    """The material step of a series name ``W3_QS`` → ``W3``."""
    return series.split("_")[0]


def rate_of(series: str) -> str:
    """The rate of a series name ``W3_QS`` → ``QS``; a name without a rate gives ``''``."""
    parts = series.split("_")
    return parts[1] if len(parts) > 1 else ""


# --- the run ---------------------------------------------------------------------------------------


@dataclass(frozen=True)
class JobRun:
    job: str
    series: str
    started: str
    ended: str
    wall_s: float | None
    completed: bool


def read_run_log(folder: Path, series_of_job: Mapping[str, str]) -> tuple[JobRun, ...]:
    """Start, end and wall time of every job from ``run_log.txt`` (the runner's log)."""
    path = folder / "run_log.txt"
    if not path.is_file():
        return ()
    raw_bytes = path.read_bytes()
    # the runner's Tee-Object writes UTF-16 with a byte-order mark on Windows PowerShell
    text = (
        raw_bytes.decode("utf-16", errors="replace")
        if raw_bytes[:2] in (b"\xff\xfe", b"\xfe\xff")
        else raw_bytes.decode("utf-8", errors="replace")
    )
    starts: dict[str, str] = {}
    runs: list[JobRun] = []
    for raw in text.splitlines():
        match = RUN_LOG_LINE.match(raw.strip())
        if match is None:
            continue
        stamp, what, job, _code, outcome = match.groups()
        if what == "start":
            starts[job] = stamp
            continue
        started = starts.get(job, "")
        wall = None
        if started:
            try:
                wall = (
                    datetime.fromisoformat(stamp) - datetime.fromisoformat(started)
                ).total_seconds()
            except ValueError:
                wall = None
        runs.append(
            JobRun(
                job=job,
                series=series_of_job.get(job, ""),
                started=started,
                ended=stamp,
                wall_s=wall,
                completed=(outcome or "").strip() == "completed",
            )
        )
    return tuple(runs)


def chattering_nodes(
    msg_path: Path, mesh_nodes: Mapping[int, tuple[float, float, float]]
) -> list[str]:
    """The contact nodes the last attempts of a broken-off job name most often, with their
    position (r, z) from the mesh: the chattering of FE-19."""
    if not msg_path.is_file():
        return []
    tail = msg_path.read_text(encoding="utf-8", errors="replace").splitlines()[-MSG_TAIL_LINES:]
    counts: dict[int, int] = {}
    for line in tail:
        for found in MSG_NODE.findall(line):
            label = int(found)
            counts[label] = counts.get(label, 0) + 1
    out = []
    for label, count in sorted(counts.items(), key=lambda kv: -kv[1])[:4]:
        xyz = mesh_nodes.get(label)
        where = (
            f"r {_g(math.hypot(xyz[0], xyz[1]), 3)} mm, z {_g(xyz[2], 2)} mm"
            if xyz is not None
            else "?"
        )
        out.append(f"Knoten {label} ({where}, {count} Nennungen)")
    return out


def read_mesh_nodes(path: Path) -> dict[int, tuple[float, float, float]]:
    """Node label → coordinates of an Abaqus mesh file (``*NODE`` blocks)."""
    nodes: dict[int, tuple[float, float, float]] = {}
    inside = False
    for line in path.read_text(encoding="ascii", errors="replace").splitlines():
        if line.startswith("*"):
            inside = line.upper().startswith("*NODE")
            continue
        if inside and line[:1].strip():
            parts = line.split(",")
            nodes[int(parts[0])] = (float(parts[1]), float(parts[2]), float(parts[3]))
    return nodes


# --- curves and comparisons -------------------------------------------------------------------------


def values_at_points(points: Sequence[ev.PathPoint], step: str, quantity: str) -> dict[str, float]:
    """Value of a quantity at the named points A to E (complete steps only), by the curve of
    ``evaluation`` over the named points alone."""
    labelled = [p for p in points if p.label]
    label_of = {p.from_a_mm: p.label for p in labelled}
    return {label_of[x]: v for x, v in ev.curve(labelled, step, quantity) if x in label_of}


def relative(a: float | None, b: float | None) -> float | None:
    """b / a − 1, None without both values or with a zero reference."""
    if a is None or b is None or a == 0.0:
        return None
    return b / a - 1.0


def contact_window(points: Sequence[ev.PathPoint], step: str) -> dict[str, tuple[float, float]]:
    """Per tooth half: the first and the last position along the path where its normal force
    exceeds ``FORCE_THRESHOLD_N`` (the extended contact; the ends of the grid tell whether the
    margin carries load)."""
    halves = sorted(
        {f"{t.tooth}_{t.side}" for p in points for s in p.summaries.values() for t in s.teeth}
    )
    out: dict[str, tuple[float, float]] = {}
    for half in halves:
        force = ev.curve(points, step, f"force:{half}")
        loaded = [x for x, v in force if v > FORCE_THRESHOLD_N]
        if loaded:
            out[half] = (min(loaded), max(loaded))
    return out


def middle_tooth_half(windows: Mapping[str, tuple[float, float]], path_mm: float) -> str | None:
    """The tooth half whose loaded window lies around the theoretical path of contact: the
    evaluated middle tooth of the sector (its neighbours carry their regular contact one pitch
    before and after)."""
    if not windows:
        return None
    return min(windows, key=lambda h: abs(0.5 * (windows[h][0] + windows[h][1]) - 0.5 * path_mm))


def shift_within_pitch(shift_mm: float, pitch_mm: float) -> float:
    """A location shift reduced by whole pitches: the maximum of a periodic curve that moves to
    the same point of the neighbouring tooth has not moved."""
    if pitch_mm <= 0.0:
        return shift_mm
    reduced = math.fmod(shift_mm, pitch_mm)
    if abs(reduced) > 0.5 * pitch_mm:
        reduced -= math.copysign(pitch_mm, reduced)
    return reduced


def is_full_grid(points: Sequence[ev.PathPoint], steps_per_pitch: int, pitch_mm: float) -> bool:
    """Whether the points fill their span at the grid's step (a selection of named points,
    as in the pilots, does not)."""
    if len(points) < 2 or steps_per_pitch < 1 or pitch_mm <= 0.0:
        return False
    xs = [p.from_a_mm for p in points]
    expected = (max(xs) - min(xs)) * steps_per_pitch / pitch_mm + 1.0
    return len(points) >= 0.9 * expected


def common_positions(
    a: Sequence[ev.PathPoint], b: Sequence[ev.PathPoint], tolerance_mm: float = 1.0e-6
) -> list[tuple[ev.PathPoint, ev.PathPoint]]:
    """Pairs of points of two folders at the same position along the path."""
    by_x = sorted(b, key=lambda p: p.from_a_mm)
    pairs = []
    for point in a:
        for other in by_x:
            if abs(other.from_a_mm - point.from_a_mm) < tolerance_mm:
                pairs.append((point, other))
                break
    return pairs


def edge_tooth_force(points: Sequence[ev.PathPoint], step: str) -> tuple[tuple[float, float], ...]:
    """The largest normal force of a tooth half other than the main one at every position: the
    load the outgoing (or incoming) tooth still carries at the edge contact."""
    out = []
    for point in points:
        summary = point.summaries.get(step)
        if summary is None or not summary.complete:
            continue
        forces = sorted((t.force or 0.0) for t in summary.teeth)
        out.append((point.from_a_mm, forces[-2] if len(forces) >= 2 else 0.0))
    return tuple(out)


# --- the Stommel outputs ----------------------------------------------------------------------------


MIDDLE_FILLETS = ("fillet T2_T3", "fillet T3_T4")
"""The zones of the two fillets of the middle tooth of the five-tooth sector (the evaluated
tooth; the outer teeth and their heads carry the sector boundary, FE-20)."""


@dataclass(frozen=True)
class StommelSummary:
    label: str
    step: str
    nodes: int
    fillet_nodes: int
    fillet_above_cyclic: int
    fillet_above_static: int
    critical_node: int
    critical_zone: str
    critical_r_mm: float
    critical_z_mm: float
    a_B_V: float
    a_stat_at_critical: float
    N_predicted: float
    life_flag: str
    fillet_a_stat_max: float
    fillet_a_stat_node: int
    global_node: int
    global_zone: str
    global_a_B_V: float


def read_stommel(label: str, folder: Path) -> list[StommelSummary]:
    """The node tables ``knoten_<step>.csv`` of one ``fe_fatigue.py stommel`` output folder:
    the critical node of the two fillets of the middle tooth (the largest a_B,V there), and the
    global maximum with its zone beside it."""
    out: list[StommelSummary] = []

    def torque_of(path: Path) -> float:
        digits = re.sub(r"[^0-9P]", "", path.stem.removeprefix("knoten_LOAD_"))
        return float(digits.replace("P", ".") or "0")

    for path in sorted(folder.glob("knoten_LOAD_*.csv"), key=torque_of):
        step = path.stem.removeprefix("knoten_")
        with path.open(encoding="utf-8", newline="") as handle:
            header = handle.readline()
            handle.seek(0)
            # the tables of fe_fatigue.py are comma-separated; a semicolon table (the German
            # exports of the measurement scripts) is read as well
            delimiter = ";" if header.count(";") > header.count(",") else ","
            rows = list(csv.DictReader(handle, delimiter=delimiter))
        if not rows:
            continue
        fillet = [r for r in rows if r.get("zone", "") in MIDDLE_FILLETS]
        if not fillet:
            raise InputRangeError(
                f"{path}: no node of the fillet zones {MIDDLE_FILLETS} (the table names zones "
                f"{sorted({r.get('zone', '') for r in rows})[:8]})"
            )
        cyclic = max(fillet, key=lambda r: float(r["a_B_V"]))
        static = max(fillet, key=lambda r: float(r["a_stat"]))
        overall = max(rows, key=lambda r: float(r["a_B_V"]))
        out.append(
            StommelSummary(
                label=label,
                step=step,
                nodes=len(rows),
                fillet_nodes=len(fillet),
                fillet_above_cyclic=sum(1 for r in fillet if float(r["a_B_V"]) > 1.0),
                fillet_above_static=sum(1 for r in fillet if float(r["a_stat"]) > 1.0),
                critical_node=int(cyclic["node"]),
                critical_zone=cyclic.get("zone", ""),
                critical_r_mm=float(cyclic["r_mm"]),
                critical_z_mm=float(cyclic["z_mm"]),
                a_B_V=float(cyclic["a_B_V"]),
                a_stat_at_critical=float(cyclic["a_stat"]),
                N_predicted=float(cyclic["N_predicted"]),
                life_flag=cyclic.get("life_flag", ""),
                fillet_a_stat_max=float(static["a_stat"]),
                fillet_a_stat_node=int(static["node"]),
                global_node=int(overall["node"]),
                global_zone=overall.get("zone", ""),
                global_a_B_V=float(overall["a_B_V"]),
            )
        )
    return out


# --- figures ---------------------------------------------------------------------------------------


def _line_style(full: bool) -> dict[str, str]:
    """The house line for a full grid; markers only for a selection of positions, where the
    course between the points is not computed and a line would suggest maxima that are none
    (user, 2026-10-13)."""
    return {} if full else {"linestyle": "none"}


def figure_series_comparison(
    by_series: Mapping[str, Sequence[ev.PathPoint]],
    step: str,
    r_b1_mm: float,
    named: Sequence[tuple[float, str]],
    stem: Path,
    title: str,
    steps_per_pitch: int = 0,
    pitch_mm: float = 0.0,
) -> list[Path]:
    """The five global quantities over the path, one line per series; a series that holds a
    selection of positions only (the pilots at A to E) gets markers without a line, because
    the course between its points is not computed (user, 2026-10-13)."""
    fig, axes = new_figure("full", 1.35, rows=5, sharex=True)
    several_rates = len({rate_of(s) for s in by_series}) > 1
    labels = [
        (
            r"Verdrehweg $\varphi_1 \, r_{\mathrm{b1}}$ in µm",
            "pinion_rotation_rad",
            r_b1_mm * 1000.0,
        ),
        ("Kopfverschiebung in µm", "u_head_max", 1000.0),
        ("CPRESS max in MPa", "p_max", 1.0),
        (r"$\sigma_{\mathrm{1}}$ max in MPa", "s1_max", 1.0),
        (r"|$\sigma_{\mathrm{3}}$| max in MPa", "s3_min", 1.0),
    ]
    for ax, (ylabel, quantity, scale) in zip(axes, labels, strict=True):
        for series, points in by_series.items():
            data = ev.curve(points, step, quantity)
            ax.plot(
                [x for x, _ in data],
                [v * scale for _, v in data],
                label=SERIES_LABELS.get(step_of(series), series)
                + (f", {rate_text(series)}" if several_rates else ""),
                **_line_style(is_full_grid(points, steps_per_pitch, pitch_mm)),
            )
        ax.set_ylabel(ylabel)
        for x, _ in named:
            ax.axvline(x, color=SHEET.colour("tum_grau_50"), linewidth=0.6)
    legend_beside(axes[0])
    for x, label in named:
        axes[0].text(x, axes[0].get_ylim()[1], label, ha="center", va="bottom")
    axes[-1].set_xlabel("Wälzweg ab A in mm")
    del title  # the caption goes to bildunterschriften.md, not into the SVG
    pictures = save_figure(fig, stem)
    plt.close(fig)
    return list(pictures)


def figure_reference_comparison(
    series_points: Sequence[ev.PathPoint],
    reference_points: Sequence[ev.PathPoint],
    step: str,
    r_b1_mm: float,
    named: Sequence[tuple[float, str]],
    stem: Path,
    labels: tuple[str, str],
    title: str,
    own_full: bool = True,
    ref_full: bool = True,
) -> list[Path]:
    """Rotation, root stress, contact pressure and the edge-tooth force of the folder against
    the reference folder (sharp against rounded pinion edge); a folder with a selection of
    positions (``own_full`` or ``ref_full`` False) gets markers without a line."""
    fig, axes = new_figure("full", 1.2, rows=4, sharex=True)
    own_style = _line_style(own_full)
    ref_style = _line_style(ref_full)
    rows = [
        (
            r"Verdrehweg $\varphi_1 \, r_{\mathrm{b1}}$ in µm",
            "pinion_rotation_rad",
            r_b1_mm * 1000.0,
        ),
        (r"$\sigma_{\mathrm{1}}$ max in MPa", "s1_max", 1.0),
        ("CPRESS max in MPa", "p_max", 1.0),
    ]
    for ax, (ylabel, quantity, scale) in zip(axes[:3], rows, strict=True):
        for points, label, style in (
            (reference_points, labels[1], ref_style),
            (series_points, labels[0], own_style),
        ):
            data = ev.curve(points, step, quantity)
            ax.plot([x for x, _ in data], [v * scale for _, v in data], label=label, **style)
        ax.set_ylabel(ylabel)
    for points, label, style in (
        (reference_points, labels[1], ref_style),
        (series_points, labels[0], own_style),
    ):
        data = edge_tooth_force(points, step)
        axes[3].plot([x for x, _ in data], [v for _, v in data], label=label, **style)
    axes[3].set_ylabel("Kraft des Nebenzahns in N")
    legend_outside(fig, axes[0], where="bottom")
    for ax in axes:
        for x, _ in named:
            ax.axvline(x, color=SHEET.colour("tum_grau_50"), linewidth=0.6)
    for x, label in named:
        axes[0].text(x, axes[0].get_ylim()[1], label, ha="center", va="bottom")
    axes[-1].set_xlabel("Wälzweg ab A in mm")
    del title  # the caption goes to bildunterschriften.md, not into the SVG
    pictures = save_figure(fig, stem)
    plt.close(fig)
    return list(pictures)


# --- the analysis ----------------------------------------------------------------------------------


def _load(folder: Path) -> tuple[dict[str, Any], dict[str, list[ev.PathPoint]]]:
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    by_series: dict[str, list[ev.PathPoint]] = {}
    for name in ev.series_names(manifest):
        by_series[name] = [p for p in ev.path_points(manifest, folder, name) if p.summaries]
    return manifest, by_series


def analyse(
    folder: Path,
    out: Path,
    reference: Path | None = None,
    reference_series: str | None = None,
    stommel: Mapping[str, Path] | None = None,
) -> list[str]:
    """Write ``analyse.md`` and the figures; returns the report lines."""
    if not (folder / "manifest.json").is_file():
        raise InputRangeError(f"no manifest.json in {folder}")
    out.mkdir(parents=True, exist_ok=True)
    manifest, by_series = _load(folder)
    names = manifest.get("step_names", [])
    steps = [str(s) for s in names if s != "SEAT"]
    r_b1 = float(manifest["seating_arc_mm"]) / float(manifest["seating_angle_rad"])
    first_series = next(iter(by_series.values()), [])
    named = [(p.from_a_mm, p.label) for p in first_series if p.label]
    grid = manifest.get("grid", {})
    if not isinstance(grid.get("path_of_contact_mm"), int | float) or not isinstance(
        grid.get("transverse_base_pitch_mm"), int | float
    ):
        raise InputRangeError("the manifest's grid names no path of contact or base pitch")
    path_mm = float(grid["path_of_contact_mm"])
    pitch_mm = float(grid["transverse_base_pitch_mm"])
    steps_per_pitch = int(grid.get("steps_per_pitch") or 0)
    lines: list[str] = []
    captions: list[str] = []
    doc: list[str] = [f"# Analyse der Serie {folder.name}", ""]
    doc.append(
        f"Ordner mit {len(manifest.get('positions', []))} Stellungsdateien, Serien "
        f"{', '.join(by_series)}; Gitter {grid.get('steps_per_pitch')} je Teilung, Rand "
        f"{_g(grid.get('margin_pitches'), 2)} Teilungen, Schritte {', '.join(STEP_LABELS.get(s, s) for s in steps)}. "
        "Alle Kurven und Maxima sind Größtwerte über die ganze Zahnbreite (alle Schichten), die "
        "Stellungen abgebrochener Schritte bleiben aus den Kurven heraus."
    )
    incomplete_of = {
        s: sorted(p.job for p in pts if any(not m.complete for m in p.summaries.values()))
        for s, pts in by_series.items()
    }
    doc.append(
        "Stellungen mit extrahierten Feldern je Serie: "
        + ", ".join(
            f"{s} {len(pts)}"
            + (f" (abgebrochen: {', '.join(incomplete_of[s])})" if incomplete_of[s] else "")
            for s, pts in by_series.items()
        )
        + "."
    )
    doc.append("")

    # 1 the run
    series_of_job = {
        str(e["file"]).removesuffix(".inp"): ev.series_of(e, manifest)
        for e in manifest["positions"]
    }
    runs = read_run_log(folder, series_of_job)
    doc.extend(["## 1 Der Lauf", ""])
    if runs:
        rows = []
        for series in by_series:
            own = [r for r in runs if r.series == series]
            walls = [r.wall_s for r in own if r.wall_s is not None and r.completed]
            rows.append(
                [
                    series,
                    str(len(own)),
                    str(sum(1 for r in own if r.completed)),
                    _g(min(walls) / 60.0, 1) if walls else "–",
                    _g(sum(walls) / len(walls) / 60.0, 1) if walls else "–",
                    _g(max(walls) / 60.0, 1) if walls else "–",
                ]
            )
        doc.extend(
            _table(["Serie", "Jobs", "vollständig", "Wand min in min", "Mittel", "max"], rows)
        )
        total = [r.wall_s for r in runs if r.wall_s is not None]
        if total:
            doc.append("")
            doc.append(
                f"Gesamt {_g(sum(total) / 3600.0, 1)} h Rechenzeit, von {runs[0].started} bis "
                f"{runs[-1].ended}."
            )
    broken = [r for r in runs if not r.completed]
    mesh_file = folder / str(manifest.get("wheel_mesh", {}).get("file", "wheel_mesh.inp"))
    mesh_nodes = read_mesh_nodes(mesh_file) if broken and mesh_file.is_file() else {}
    if broken:
        doc.append("")
        doc.append("Abgebrochen:")
        doc.append("")
        for run in broken:
            point = next((p for pts in by_series.values() for p in pts if p.job == run.job), None)
            where = ""
            if point is not None:
                incomplete = [s for s in point.summaries.values() if not s.complete]
                if incomplete:
                    where = (
                        f" im Schritt {incomplete[0].name} bei Schrittzeit "
                        f"{_g(incomplete[0].time, 3)}, Stellung {_g(point.from_a_mm, 3)} mm ab A"
                    )
            nodes = chattering_nodes(folder / f"{run.job}.msg", mesh_nodes)
            doc.append(
                f"- `{run.job}`{where}; flatternde Kontaktknoten der letzten Versuche: "
                + ("; ".join(nodes) if nodes else "keine in der .msg gefunden")
                + " (Muster von FE-19: Penetrationsfehler und Drehkorrektur zu groß, Lösung divergiert)."
            )
    doc.append("")

    # 2 load history and maxima
    doc.extend(["## 2 Lastverlauf je Werkstoffstufe", ""])
    doc.append(
        "Die Kurven je Serie und Schritt liegen als `path_<Serie>_<Schritt>` im Ordner; hier die "
        "Werkstoffstufen einer Rate übereinander (Bilder `vergleich_stufen_<Schritt>[_<Rate>]`) "
        "und die Maxima mit Ort; eine Auswahl von Stellungen steht als Marker ohne Linie."
    )
    doc.append("")
    rates_present = sorted({rate_of(s) for s in by_series})
    for step in steps:
        # one figure per rate: four material steps per figure, never more series than the
        # house cycle has markers
        for rate in rates_present:
            of_rate = {s: pts for s, pts in by_series.items() if rate_of(s) == rate}
            suffix = f"_{rate}" if len(rates_present) > 1 else ""
            pictures = figure_series_comparison(
                of_rate,
                step,
                r_b1,
                named,
                out / f"vergleich_stufen_{step}{suffix}",
                f"{describe(manifest)}, {RATE_LABELS.get(rate, rate)}, "
                f"{STEP_LABELS.get(step, step)}",
                steps_per_pitch=steps_per_pitch,
                pitch_mm=pitch_mm,
            )
            lines.append(f"{step}{suffix}: " + ", ".join(p.name for p in pictures))
            captions.append(
                f"- `vergleich_stufen_{step}{suffix}`: Werkstoffstufen W1 bis W4 über dem Wälzweg, "
                f"{describe(manifest)}, {RATE_LABELS.get(rate, rate)}, {STEP_LABELS.get(step, step)}: "
                "Verdrehweg, Kopfverschiebung, größter Kontaktdruck und die Fußspannungen σ1 und |σ3| "
                "als Größtwerte über die Zahnbreite; senkrechte Linien an den Normpunkten A bis E."
            )
        rows = []
        for quantity, label, unit, scale in GLOBAL_QUANTITIES:
            for series, points in by_series.items():
                peak = ev.extremum(ev.curve(points, step, quantity))
                at = values_at_points(points, step, quantity)
                rows.append(
                    [
                        f"{label} in {unit}",
                        series,
                        _g(peak[1] * scale, 2) if peak else "–",
                        _g(peak[0], 3) if peak else "–",
                        *(
                            _g(at[k] * scale, 2) if k in at else "–"
                            for k in ("A", "B", "C", "D", "E")
                        ),
                    ]
                )
        doc.extend([f"### {STEP_LABELS.get(step, step)}", ""])
        doc.extend(
            _table(["Größe", "Serie", "Maximum", "Ort ab A in mm", "A", "B", "C", "D", "E"], rows)
        )
        doc.append("")

    # 3 anisotropy against plasticity
    doc.extend(["## 3 Anisotropie gegen Plastizität", ""])
    doc.append(
        "Relative Änderung der Maxima und der Werte an den Punkten zwischen den Stufen "
        "(zweite Stufe gegen erste)."
    )
    doc.append("")
    uneven = [f"{s} ({', '.join(jobs)})" for s, jobs in incomplete_of.items() if jobs]
    if uneven:
        doc.append(
            "Abgebrochene Schritte fehlen in den Maxima und Punktwerten ihrer Serie, die "
            f"Maxima dort laufen über weniger Stellungen: {'; '.join(uneven)}."
        )
        doc.append("")
    # the comparisons stay within one rate: W3_DY1 against W1_DY1, never across rates
    rates_in_folder = sorted({rate_of(s) for s in by_series})
    for step in steps:
        rows = []
        for rate in rates_in_folder:
            steps_of_series = {step_of(s): s for s in by_series if rate_of(s) == rate}
            for first, second, what in COMPARISONS:
                if first not in steps_of_series or second not in steps_of_series:
                    continue
                a_points = by_series[steps_of_series[first]]
                b_points = by_series[steps_of_series[second]]
                for quantity, label, _unit, _scale in GLOBAL_QUANTITIES:
                    peak_a = ev.extremum(ev.curve(a_points, step, quantity))
                    peak_b = ev.extremum(ev.curve(b_points, step, quantity))
                    at_a = values_at_points(a_points, step, quantity)
                    at_b = values_at_points(b_points, step, quantity)
                    rows.append(
                        [
                            what,
                            f"{steps_of_series[first]} → {steps_of_series[second]}",
                            label,
                            _pct(
                                relative(
                                    peak_a[1] if peak_a else None, peak_b[1] if peak_b else None
                                )
                            ),
                            *(
                                _pct(relative(at_a.get(k), at_b.get(k)))
                                for k in ("A", "B", "C", "D", "E")
                            ),
                        ]
                    )
        if rows:
            doc.extend([f"### {STEP_LABELS.get(step, step)}", ""])
            doc.extend(
                _table(["Effekt", "Stufen", "Größe", "Maximum", "A", "B", "C", "D", "E"], rows)
            )
            doc.append("")

    # 4 extended contact and the margin
    doc.extend(["## 4 Verlängerter Eingriff und Rand des Gitters", ""])
    doc.append(
        f"Erste und letzte Stellung, an der der mittlere Zahn des Sektors mehr als "
        f"{_g(FORCE_THRESHOLD_N, 0)} N trägt, gegen den theoretischen Eingriff von A (0) bis E "
        f"({_g(path_mm, 3)} mm), in Teilungen ({_g(pitch_mm, 3)} mm); der Rand des Gitters ist "
        f"{_g(grid.get('margin_pitches'), 2)} Teilungen. Die Nachbarzähne tragen am Gitterrand "
        "ihren regulären Eingriff, das sagt nichts über den Rand (FE-21)."
    )
    doc.append("")
    rows = []
    for step in steps:
        for series, points in by_series.items():
            windows = contact_window(points, step)
            half = middle_tooth_half(windows, path_mm)
            if half is None:
                continue
            lo, hi = windows[half]
            rows.append(
                [
                    STEP_LABELS.get(step, step),
                    series,
                    half,
                    _g(lo, 3),
                    _g(hi, 3),
                    _g(-lo / pitch_mm, 2) if pitch_mm else "–",
                    _g((hi - path_mm) / pitch_mm, 2) if pitch_mm else "–",
                ]
            )
    doc.extend(
        _table(
            [
                "Schritt",
                "Serie",
                "Zahnhälfte",
                "trägt ab mm",
                "trägt bis mm",
                "vor A in Teilungen",
                "hinter E in Teilungen",
            ],
            rows,
        )
    )
    doc.append("")

    # 5 sharp against rounded (reference folder)
    if reference is not None:
        ref_manifest, ref_series = _load(reference)
        ref_name = reference_series or next(iter(ref_series))
        if ref_name not in ref_series:
            raise InputRangeError(
                f"{reference.name} has no series {ref_name!r}: {list(ref_series)}"
            )
        own_name = next((s for s in by_series if step_of(s) == step_of(ref_name)), None)
        if own_name is None:
            raise InputRangeError(f"{folder.name} has no series of the step {step_of(ref_name)}")
        ref_edge = ref_manifest.get("pinion_surface", {}).get("tip_rounding_mm")
        own_edge = manifest.get("pinion_surface", {}).get("tip_rounding_mm")

        def edge_text(value: float | None) -> str:
            # a manifest written before the rounding existed names none: sharp as the drawing
            return (
                f"Ritzelkopfkante r = {_g(value, 2)} mm"
                if value is not None
                else "Ritzelkopfkante scharf (keine Rundung im Manifest)"
            )

        labels = (describe(manifest), describe(ref_manifest))
        if labels[0] == labels[1]:
            # the same body and edge in both folders: the folder names tell them apart
            labels = (f"{labels[0]} ({folder.name})", f"{labels[1]} ({reference.name})")
        doc.extend([f"## 5 Vergleich mit {reference.name}", ""])
        pairs = common_positions(by_series[own_name], ref_series[ref_name])
        doc.append(
            f"Dieser Ordner ({describe(manifest)}, Serie {own_name}) gegen den Referenzordner "
            f"{reference.name} ({describe(ref_manifest)}, Serie {ref_name}) an {len(pairs)} "
            f"gemeinsamen Stellungen; {edge_text(own_edge)} gegen {edge_text(ref_edge)}. Bilder "
            "`vergleich_referenz_<Schritt>`; ein Ordner mit einer Auswahl von Stellungen steht "
            "dort als Marker ohne Linie, weil der Verlauf dazwischen nicht gerechnet ist."
        )
        doc.append("")
        for step in steps:
            pictures = figure_reference_comparison(
                by_series[own_name],
                ref_series[ref_name],
                step,
                r_b1,
                named,
                out / f"vergleich_referenz_{step}",
                labels,
                f"{SERIES_LABELS.get(step_of(own_name), own_name)}, {rate_text(own_name)}, "
                f"{STEP_LABELS.get(step, step)}",
                own_full=is_full_grid(by_series[own_name], steps_per_pitch, pitch_mm),
                ref_full=is_full_grid(
                    ref_series[ref_name],
                    # an older reference without a grid block: judged by this folder's grid
                    int(ref_manifest.get("grid", {}).get("steps_per_pitch") or steps_per_pitch),
                    float(ref_manifest.get("grid", {}).get("transverse_base_pitch_mm") or pitch_mm),
                ),
            )
            lines.append(f"{step}: " + ", ".join(p.name for p in pictures))
            captions.append(
                f"- `vergleich_referenz_{step}`: {labels[0]} gegen {labels[1]} über dem Wälzweg, "
                f"{SERIES_LABELS.get(step_of(own_name), own_name)}, {rate_text(own_name)}, "
                f"{STEP_LABELS.get(step, step)}: Verdrehweg, Fußspannung σ1, größter Kontaktdruck und "
                "die Kraft des Nebenzahns; eine Auswahl von Stellungen als Marker ohne Linie."
            )
            rows = []
            for quantity, label, unit, scale in GLOBAL_QUANTITIES:
                own_at = values_at_points([p for p, _ in pairs], step, quantity)
                ref_at = values_at_points([q for _, q in pairs], step, quantity)
                own_peak = ev.extremum(ev.curve([p for p, _ in pairs], step, quantity))
                ref_peak = ev.extremum(ev.curve([q for _, q in pairs], step, quantity))
                rows.append(
                    [
                        f"{label} in {unit}",
                        _g(ref_peak[1] * scale, 2) if ref_peak else "–",
                        _g(own_peak[1] * scale, 2) if own_peak else "–",
                        _pct(
                            relative(
                                ref_peak[1] if ref_peak else None, own_peak[1] if own_peak else None
                            )
                        ),
                        *(
                            _pct(relative(ref_at.get(k), own_at.get(k)))
                            for k in ("A", "B", "C", "D", "E")
                        ),
                    ]
                )
            # the neighbour's load in the edge contact: outside the theoretical path only
            # (inside it the second largest force is the handover share, about half the load)
            own_edge_force = {
                x: v
                for x, v in edge_tooth_force([p for p, _ in pairs], step)
                if not 0.0 <= x <= path_mm
            }
            ref_edge_force = {
                x: v
                for x, v in edge_tooth_force([q for _, q in pairs], step)
                if not 0.0 <= x <= path_mm
            }
            if own_edge_force and ref_edge_force:
                rows.append(
                    [
                        "Kraft des Nebenzahns im Kantenkontakt max in N (vor A, hinter E)",
                        _g(max(ref_edge_force.values()), 1),
                        _g(max(own_edge_force.values()), 1),
                        _pct(relative(max(ref_edge_force.values()), max(own_edge_force.values()))),
                        "",
                        "",
                        "",
                        "",
                        "",
                    ]
                )
            doc.extend([f"### {STEP_LABELS.get(step, step)}", ""])
            doc.extend(
                _table(
                    ["Größe", "Referenz max", "Serie max", "Änderung max", "A", "B", "C", "D", "E"],
                    rows,
                )
            )
            doc.append("")

    # 6 resolution
    base_pitch = grid.get("transverse_base_pitch_mm")
    if not (steps_per_pitch >= 1 and isinstance(base_pitch, int | float)):
        doc.extend(
            ["## 6 Auflösung des Gitters", "", "Kein Gitter im Manifest, keine Teilgitter.", ""]
        )
    elif not any(
        is_full_grid(points, steps_per_pitch, float(base_pitch)) for points in by_series.values()
    ):
        doc.extend(
            [
                "## 6 Auflösung des Gitters",
                "",
                "Die Stellungen sind eine Auswahl aus dem Gitter (die Normpunkte), keine "
                "Teilgitter möglich.",
                "",
            ]
        )
    else:
        base_pitch = float(base_pitch)
        doc.extend(["## 6 Auflösung des Gitters", ""])
        doc.append(
            "Größte Änderung der globalen Maxima und ihr größter Ortsversatz je Teilgitter gegen "
            "das volle Gitter, der Versatz um ganze Teilungen bereinigt (ein Maximum, das auf "
            "denselben Punkt des Nachbarzahns springt, ist nicht gewandert); Zahlen je Größe in "
            "`path_report.md`."
        )
        doc.append("")
        factors = [
            f for f in (1, 2, 3, 5, 6, 10) if steps_per_pitch % f == 0 and steps_per_pitch / f >= 4
        ]
        quantities = [q for q, *_ in GLOBAL_QUANTITIES]
        rows = []
        for series, points in by_series.items():
            for step in steps:
                res = ev.resolution_rows(
                    points,
                    step,
                    quantities,
                    steps_per_pitch,
                    base_pitch,
                    float(grid.get("margin_pitches") or 0.0),
                    factors,
                )
                for sub in sorted({r.steps_per_pitch for r in res}, reverse=True):
                    sub_rows = [r for r in res if r.steps_per_pitch == sub]
                    rows.append(
                        [
                            series,
                            STEP_LABELS.get(step, step),
                            str(sub),
                            str(sub_rows[0].positions) if sub_rows else "–",
                            _pct(max((abs(r.change) for r in sub_rows), default=0.0)),
                            _g(
                                max(
                                    (
                                        abs(shift_within_pitch(r.shift_mm, base_pitch))
                                        for r in sub_rows
                                    ),
                                    default=0.0,
                                ),
                                3,
                            ),
                        ]
                    )
        doc.extend(
            _table(
                [
                    "Serie",
                    "Schritt",
                    "je Teilung",
                    "Stellungen",
                    "Änderung max",
                    "Versatz max in mm",
                ],
                rows,
            )
        )
        doc.append("")

    # 7 Stommel
    if stommel:
        doc.extend(["## 7 Bemessung nach Stommel et al. je Serie", ""])
        doc.append(
            "Aus den Knotentabellen der Ordner von `fe_fatigue.py stommel`, bezogen auf die beiden "
            "Fußrundungen des mittleren Zahns T3 (die Randzähne und ihre Köpfe tragen den Sektorrand, "
            "FE-20): der Knoten der größten zyklischen Auslastung a_B,V je Schritt mit Ort, seiner "
            "statischen Auslastung und der vorhergesagten Lastspielzahl auf der synthetischen "
            "Wöhlerlinie, die Zahl der Fußknoten über 1, die größte statische Auslastung der "
            "Fußrundungen; daneben das globale Maximum von a_B,V mit seiner Zone."
        )
        doc.append("")
        rows = []
        for label, path in stommel.items():
            for s in read_stommel(label, path):
                rows.append(
                    [
                        label,
                        STEP_LABELS.get(s.step, s.step),
                        f"{s.fillet_nodes} von {s.nodes}",
                        str(s.fillet_above_cyclic),
                        str(s.fillet_above_static),
                        f"{s.critical_node} ({s.critical_zone}, r {_g(s.critical_r_mm, 2)}, "
                        f"z {_g(s.critical_z_mm, 2)})",
                        _g(s.a_B_V, 2),
                        _g(s.a_stat_at_critical, 2),
                        (
                            "∞"
                            if math.isinf(s.N_predicted)
                            else f"{s.N_predicted:.3g}".replace(".", ",")
                        )
                        + f" ({s.life_flag})",
                        f"{s.fillet_a_stat_node}: {_g(s.fillet_a_stat_max, 2)}",
                        f"{s.global_node} ({s.global_zone}): {_g(s.global_a_B_V, 2)}",
                    ]
                )
        doc.extend(
            _table(
                [
                    "Serie",
                    "Schritt",
                    "Fußknoten T3",
                    "a_B,V > 1",
                    "a_stat > 1",
                    "kritischer Fußknoten",
                    "a_B,V",
                    "a_stat dort",
                    "N vorhergesagt",
                    "a_stat max Fuß",
                    "globales Maximum a_B,V",
                ],
                rows,
            )
        )
        doc.append("")

    # 8 rates against the reference folder (the pilots DY1/DY2 against the QS series)
    if reference is not None and len(rates_in_folder) >= 1:
        ref_manifest, ref_series = _load(reference)
        pairs_of_step: list[tuple[str, str, str]] = []
        for own_name in by_series:
            ref_name = f"{step_of(own_name)}_QS"
            if rate_of(own_name) != "QS" and ref_name in ref_series:
                pairs_of_step.append((own_name, ref_name, rate_of(own_name)))
        if pairs_of_step:
            doc.extend([f"## 8 Raten gegen QS der Referenz {reference.name}", ""])
            doc.append(
                "Relative Änderung jeder Serie des Ordners gegen die Serie derselben Werkstoffstufe "
                "bei Rate QS im Referenzordner, an den gemeinsamen Stellungen (die Punkte A bis E "
                "und das Maximum über die gemeinsamen Stellungen)."
            )
            doc.append("")
            for step in steps:
                rows = []
                for own_name, ref_name, _rate in pairs_of_step:
                    pairs = common_positions(by_series[own_name], ref_series[ref_name])
                    if not pairs:
                        continue
                    own_pts = [p for p, _ in pairs]
                    ref_pts = [q for _, q in pairs]
                    for quantity, label, _unit, _scale in GLOBAL_QUANTITIES:
                        own_peak = ev.extremum(ev.curve(own_pts, step, quantity))
                        ref_peak = ev.extremum(ev.curve(ref_pts, step, quantity))
                        own_at = values_at_points(own_pts, step, quantity)
                        ref_at = values_at_points(ref_pts, step, quantity)
                        rows.append(
                            [
                                f"{own_name} gegen {ref_name}",
                                label,
                                _pct(
                                    relative(
                                        ref_peak[1] if ref_peak else None,
                                        own_peak[1] if own_peak else None,
                                    )
                                ),
                                *(
                                    _pct(relative(ref_at.get(k), own_at.get(k)))
                                    for k in ("A", "B", "C", "D", "E")
                                ),
                            ]
                        )
                if rows:
                    doc.extend([f"### {STEP_LABELS.get(step, step)}", ""])
                    doc.extend(
                        _table(
                            ["Serie gegen Referenz", "Größe", "Maximum", "A", "B", "C", "D", "E"],
                            rows,
                        )
                    )
                    doc.append("")

    (out / "analyse.md").write_text("\n".join(doc) + "\n", encoding="utf-8")
    (out / "bildunterschriften.md").write_text(
        "\n".join(["# Bildunterschriften", "", *captions, ""]), encoding="utf-8"
    )
    lines.append((out / "analyse.md").as_posix())
    return lines


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--folder", type=Path, required=True, help="computed series folder")
    parser.add_argument(
        "--reference", type=Path, default=None, help="reference folder (e.g. the sharp-edge study)"
    )
    parser.add_argument("--reference-series", default=None, help="series of the reference folder")
    parser.add_argument(
        "--stommel",
        action="append",
        default=[],
        metavar="LABEL=DIR",
        help="output folder of fe_fatigue.py stommel of one series",
    )
    parser.add_argument("--out", type=Path, default=None, help="preset <folder>/analyse")
    args = parser.parse_args()
    stommel: dict[str, Path] = {}
    for item in args.stommel:
        label, _, path = item.partition("=")
        if not label or not path:
            raise InputRangeError(f"--stommel needs LABEL=DIR, got {item!r}")
        stommel[label] = Path(path)
    out = args.out if args.out is not None else args.folder / "analyse"
    for line in analyse(args.folder, out, args.reference, args.reference_series, stommel or None):
        print(line)


if __name__ == "__main__":
    main()
