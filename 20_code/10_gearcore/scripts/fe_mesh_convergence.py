"""Mesh convergence study of the wheel sector and its verification in the Abaqus Learning
Edition.

    python scripts/fe_mesh_convergence.py study  --case kst_e --teeth 5 --rim-rings 12
    python scripts/fe_mesh_convergence.py verify --case kst_e

``study`` solves the transverse section of the sector (plane strain, ``gearcore.fe.plane_solver``)
under the load of point B of the wheel (``gearcore.fe.convergence``) for a series of refinements
(``gearcore.fe.refine``): uniform (h, h/2, h/3, ...), and each direction of the mesh dialog on
its own (tooth height, tooth root, tooth thickness), plus the sensitivity of the result to the
width of the load patch and to the position. It writes tables, the extrapolated limits and
pictures to ``80_output/fe/<case>/convergence/``.

``verify`` writes the one-tooth sector (under the 1000 nodes of the Learning Edition) as plane
strain decks with the elements CPE4, CPE4R and CPE4I, runs them, and compares displacements and
integration point stresses of CPE4 with the own solver; the other two show the influence of the
element formulation and the artificial strain energy of the reduced integration.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.collections import PolyCollection

from gearcore import contour as ct
from gearcore import data
from gearcore.fe import abaqus as ab
from gearcore.fe import convergence as cv
from gearcore.fe import placement as pl
from gearcore.fe import plane_solver as ps
from gearcore.fe import refine as rf
from gearcore.fe import resample as rs
from gearcore.fe import sector_mesh as sm
from gearcore.fe import solid as so
from gearcore.generation import compute_generation
from gearcore.io.ste import load_ste, pair_input_from_ste
from gearcore.models.results import GenerationResult
from gearcore.plot_style import apply as apply_plot_style
from gearcore.plot_style import legend_outside, new_figure
from gearcore.plot_style import save as save_figure

SHEET = apply_plot_style()  # house style of every figure (FZG first, then TUM)

REPO_ROOT = Path(__file__).resolve().parents[3]
OUTPUT = REPO_ROOT / "80_output" / "fe"
ABAQUS = Path(r"C:\SIMULIA\Commands\abq2025le.bat")

COLOURS = (
    SHEET.colour("tum_schwarz"),
    SHEET.colour("tum_orange"),
    SHEET.colour("tum_blau_dunkel"),
    SHEET.colour("diag7"),
)
MARKERS = ("o", "s", "^", "D")
STRESS_MAP = "Blues"  # a gradation of the brand colour (TUM)


def _generation(case: str) -> GenerationResult:
    return compute_generation(pair_input_from_ste(load_ste(data.stplus_input_path(case))).pair)


def _number(value: float, digits: int) -> str:
    return f"{value:.{digits}f}".replace(".", ",")


def _style(axes: Axes, xlabel: str, ylabel: str) -> None:
    """Axis labels; grid, spines and sizes come from the house style."""
    axes.set_xlabel(xlabel)
    axes.set_ylabel(ylabel)


# --- study ---------------------------------------------------------------------------------------


def _run(
    generation: GenerationResult,
    base: sm.SectorMesh,
    outline: np.ndarray,
    refinement: rf.Refinement | rs.MeshCounts,
    *,
    torque_nmm: float,
    e_mpa: float,
    nu: float,
    width_mm: float,
    half_width_scale: float = 1.0,
    rho_1_mm: float | None = None,
    formulation: str = ps.FORMULATIONS[0],
) -> tuple[sm.SectorMesh, cv.LoadCase, ps.PlaneSolution, cv.Evaluation, float]:
    """Solve one mesh: the base refined by factors, or the template resampled to counts."""
    start = time.perf_counter()
    if isinstance(refinement, rs.MeshCounts):
        section = sm.sector_mesh(
            generation, "wheel", teeth=base.teeth, rim_rings=base.rim_rings, counts=refinement
        )
    else:
        section = rf.refined(base, outline, refinement)
    load = cv.wheel_load_case(
        generation,
        section,
        torque_wheel_nmm=torque_nmm,
        youngs_modulus_mpa=e_mpa,
        poisson_ratio=nu,
        face_width_mm=width_mm,
        half_width_scale=half_width_scale,
        rho_1_mm=rho_1_mm,
    )
    solution = ps.solve(
        section.points_mm,
        section.quads,
        d_matrix=ps.plane_strain_matrix(e_mpa, nu),
        fixed=cv.fixed_nodes(section),
        loads_n_per_mm=load.loads_n_per_mm,
        formulation=formulation,
    )
    result = cv.evaluate(section, solution, load, nu)
    return section, load, solution, result, time.perf_counter() - start


FORMULATION_TEXT = {
    "selectively_reduced": "Q4 mit 2 × 2 Gaußpunkten und volumetrischem Anteil im Elementmittelpunkt "
    "(Formulierung von CPE4 und C3D8)",
    "incompatible_modes": "Q4 mit inkompatiblen Moden (Gegenstück von CPE4I und C3D8I)",
}


def _row(
    label: str,
    series: str,
    level: int,
    section: sm.SectorMesh,
    load: cv.LoadCase,
    result: cv.Evaluation,
    seconds: float,
) -> dict[str, Any]:
    counts = rf.effective_counts(section)
    return {
        "series": series,
        "level": level,
        "label": label,
        "nodes": result.nodes,
        "elements": result.elements,
        "over_tooth_height": counts.over_tooth_height,
        "at_tooth_root": counts.at_tooth_root,
        "over_tooth_thickness": counts.over_tooth_thickness,
        "rim_rings": counts.rim_rings,
        "half_width_mm": load.half_width_mm,
        "rho_1_mm": load.rho_1_mm,
        "root_sigma1_max_mpa": result.root_sigma1_max_mpa,
        "root_radius_mm": result.root_radius_mm,
        "root_angle_deg": result.root_angle_deg,
        "root_von_mises_max_mpa": result.root_von_mises_max_mpa,
        "tip_centre_um": 1000.0 * result.tip_centre_magnitude_mm,
        "tip_corner_um": 1000.0 * result.tip_corner_magnitude_mm,
        "strain_energy_nmm": result.strain_energy_nmm,
        "seconds": seconds,
    }


def _markdown_table(rows: list[dict[str, Any]]) -> list[str]:
    head = (
        "| Reihe | Stufe | Knoten | Elemente | Zahnhöhe | Zahnfuß | Zahndicke | σ1,max Fuß in MPa | "
        "r in mm | σv,max Fuß in MPa | u Kopfmitte in µm | u Kopfecke in µm | U in N mm/mm |"
    )
    lines = [head, "|" + "---|" * 13]
    for r in rows:
        lines.append(
            f"| {r['label']} | {r['level']} | {r['nodes']} | {r['elements']} | {r['over_tooth_height']} | "
            f"{r['at_tooth_root']} | {r['over_tooth_thickness']} | {_number(float(r['root_sigma1_max_mpa']), 2)} | "
            f"{_number(float(r['root_radius_mm']), 4)} | {_number(float(r['root_von_mises_max_mpa']), 2)} | "
            f"{_number(float(r['tip_centre_um']), 3)} | {_number(float(r['tip_corner_um']), 3)} | "
            f"{_number(float(r['strain_energy_nmm']), 5)} |"
        )
    return lines


def _richardson_lines(name: str, rows: list[dict[str, Any]], key: str, unit: str) -> list[str]:
    h = [1.0 / float(r["level"]) for r in rows]
    values = [float(r[key]) for r in rows]
    result = cv.richardson(h, values)
    lines = [f"**{name}** ({unit}): " + ", ".join(_number(v, 3) for v in values)]
    lines.append(
        "Änderung zur vorigen Stufe: "
        + ", ".join(_number(100.0 * c, 2) + " %" for c in result.successive_change)
    )
    if result.order is not None and result.limit is not None and result.relative_error is not None:
        lines.append(
            f"Ordnung p = {_number(result.order, 2)}, extrapolierter Grenzwert {_number(result.limit, 3)} {unit}; "
            "Fehler der Stufen gegen den Grenzwert: "
            + ", ".join(_number(100.0 * e, 2) + " %" for e in result.relative_error)
        )
    else:
        lines.append("Keine monotone Konvergenz über die letzten drei Stufen: keine Extrapolation.")
    return lines


def _plot_series(
    out: Path,
    name: str,
    series: dict[str, list[dict[str, Any]]],
    key: str,
    ylabel: str,
    limits: dict[str, float | None],
) -> None:
    figure, axes = new_figure("full", 0.62)
    for k, (label, rows) in enumerate(series.items()):
        x = [1.0 / float(r["level"]) for r in rows]
        y = [float(r[key]) for r in rows]
        axes.plot(
            x,
            y,
            color=COLOURS[k],
            linestyle="-",
            marker=MARKERS[k],
            markersize=5,
            linewidth=1.2,
            label=label,
        )
        limit = limits.get(label)
        if limit is not None:
            axes.axhline(limit, color=COLOURS[k], linewidth=0.8, linestyle="--")
            axes.annotate(
                f"Grenzwert {label}: {_number(limit, 2)}",
                (0.02, limit),
                textcoords="offset points",
                xytext=(4, 3),
                color=COLOURS[k],
            )
    axes.set_xlim(0.0, 1.08)
    axes.set_xticks([1.0, 0.5, 1.0 / 3.0, 0.25])
    axes.set_xticklabels(["1", "1/2", "1/3", "1/4"])
    _style(axes, r"relative Elementgröße $h / h_{\mathrm{1}}$ (1 = gestriges Netz)", ylabel)
    legend_outside(figure, axes, where="bottom")
    save_figure(figure, out / Path(name).stem)
    plt.close(figure)


def _plot_fillet(out: Path, results: dict[str, cv.Evaluation]) -> None:
    figure, axes = new_figure("full", 0.62)
    for k, (label, result) in enumerate(results.items()):
        axes.plot(
            result.fillet_arc_mm,
            result.fillet_sigma1_mpa,
            color=COLOURS[k],
            linewidth=1.2,
            marker=MARKERS[k],
            markersize=2.5,
            markevery=max(1, len(result.fillet_arc_mm) // 40),
            label=label,
        )
    _style(
        axes,
        "Bogenlänge ab dem Fußformpunkt in mm",
        r"$\sigma_{\mathrm{1}}$ an der Fußoberfläche in MPa",
    )
    legend_outside(figure, axes, where="bottom")
    save_figure(figure, out / "fillet_stress")
    plt.close(figure)


def _plot_load_case(
    out: Path,
    section: sm.SectorMesh,
    load: cv.LoadCase,
    solution: ps.PlaneSolution,
    result: cv.Evaluation,
) -> None:
    sigma1, _ = ps.principal_stresses(solution.nodal_stress_mpa)
    per_quad = sigma1[section.quads].mean(axis=1)
    points = section.points_mm
    figure, axes = new_figure("full", 0.82)
    quads = list(points[section.quads])
    polygons = PolyCollection(
        quads, array=per_quad, cmap=STRESS_MAP, edgecolors="none", linewidths=0.0
    )
    polygons.set_clim(0.0, max(float(per_quad.max()), 1.0))
    axes.add_collection(polygons)
    axes.add_collection(
        PolyCollection(
            quads, facecolors="none", edgecolors=SHEET.colour("tum_schwarz"), linewidths=0.12
        )
    )
    fixed = cv.fixed_nodes(section)
    axes.plot(
        points[fixed, 0],
        points[fixed, 1],
        ".",
        color=SHEET.colour("diag5"),
        markersize=1.5,
        label="Fesselung",
    )
    loaded = load.loaded_nodes
    f = load.loads_n_per_mm[loaded]
    scale = 0.6 / max(float(np.hypot(f[:, 0], f[:, 1]).max()), 1e-12)
    axes.quiver(
        points[loaded, 0] - scale * f[:, 0],
        points[loaded, 1] - scale * f[:, 1],
        scale * f[:, 0],
        scale * f[:, 1],
        angles="xy",
        scale_units="xy",
        scale=1.0,
        width=0.004,
        color=SHEET.colour("tum_schwarz"),
    )
    axes.plot(
        *points[result.root_node],
        marker="o",
        markersize=5,
        markerfacecolor="none",
        color=SHEET.colour("tum_schwarz"),
    )
    axes.annotate(
        rf"$\sigma_{{1,\mathrm{{max}}}}$ = {_number(result.root_sigma1_max_mpa, 1)} MPa",
        points[result.root_node],
        textcoords="offset points",
        xytext=(8, -12),
    )
    tooth = load.loaded_tooth
    theta = 0.5 * math.pi + (tooth - 0.5 * (section.teeth + 1)) * section.pitch_angle_rad
    centre = (
        np.array([math.cos(theta), math.sin(theta)])
        * 0.5
        * (section.fan_ring_radius_mm + section.tip_radius_mm)
    )
    half = 1.4 * section.pitch_angle_rad * section.tip_radius_mm
    axes.set_xlim(centre[0] - half, centre[0] + half)
    axes.set_ylim(section.fan_ring_radius_mm - 0.6, section.tip_radius_mm + 0.5)
    axes.set_aspect("equal")
    _style(axes, "x in mm", "y in mm")
    bar = figure.colorbar(polygons, ax=axes, shrink=0.8)
    bar.set_label(r"$\sigma_{\mathrm{1}}$ je Element in MPa")
    torque_nm = _number(load.torque_wheel_nmm / 1000.0, 0)
    axes.set_title(
        f"Lastfall Punkt B, {torque_nm} Nm am Rad: $F'$ = {_number(load.force_per_mm, 2)} N/mm, "
        rf"$b_{{\mathrm{{H}}}}$ = {_number(load.half_width_mm, 3)} mm, "
        rf"$p_{{\mathrm{{0}}}}$ = {_number(load.max_pressure_mpa, 1)} MPa",
    )
    legend_outside(figure, axes, where="bottom")
    save_figure(figure, out / "load_case")
    plt.close(figure)


def study(
    case: str,
    teeth: int,
    rim_rings: int,
    torque_nm: float,
    e_mpa: float,
    nu: float,
    levels: int,
    out: Path,
    formulation: str = ps.FORMULATIONS[0],
) -> list[str]:
    generation = _generation(case)
    outline = ct.tooth_contour(generation, "wheel", points=2000).as_array()
    base = sm.sector_mesh(generation, "wheel", teeth=teeth, rim_rings=rim_rings)
    width = 15.0  # face width of the kst-E wheel (the .ste file gives b = 17 / 15 mm)
    torque = 1000.0 * torque_nm
    common: dict[str, Any] = {
        "torque_nmm": torque,
        "e_mpa": e_mpa,
        "nu": nu,
        "width_mm": width,
        "formulation": formulation,
    }
    rows: list[dict[str, Any]] = []
    fillet: dict[str, cv.Evaluation] = {}
    report = [
        f"# Netzkonvergenz des Radsektors {case} ({teeth} Zähne + 2 zahnlose Segmente, {rim_rings} Kranzringe)",
        "",
        f"Last: Punkt B des Rades (äußerer Einzeleingriffspunkt), {_number(torque_nm, 0)} Nm am Rad, "
        f"isotrop E = {_number(e_mpa, 0)} MPa, ν = {_number(nu, 2)}, ebener Dehnungszustand, "
        f"{FORMULATION_TEXT[formulation]}.",
        "Bewertet: größte Hauptspannung σ1 an der Fußoberfläche der belasteten Flanke (Knotenmittel), "
        "Verschiebung des Kopfmittenknotens und der belasteten Kopfecke, Formänderungsenergie U des Sektors.",
        "",
    ]
    series_rows: dict[str, list[dict[str, Any]]] = {
        "gleichmäßig": [],
        "Zahndicke": [],
        "Zahnhöhe": [],
        "Zahnfuß": [],
    }
    plan = [("gleichmäßig", rf.Refinement(uniform=n), n) for n in range(1, levels + 1)]
    plan += [("Zahnhöhe", rf.Refinement(height=n), n) for n in (2, 3)]
    plan += [("Zahnfuß", rf.Refinement(root=n), n) for n in (2, 3)]
    plan += [("Zahndicke", rf.Refinement(thickness=n), n) for n in (2, 3, 4)]
    base_result: cv.Evaluation | None = None
    for series, refinement, level in plan:
        section, load, solution, result, seconds = _run(
            generation, base, outline, refinement, **common
        )
        label = refinement.label()
        rows.append(_row(label, series, level, section, load, result, seconds))
        series_rows[series].append(rows[-1])
        if series == "gleichmäßig":
            fillet[f"gleichmäßig {level}"] = result
            if level == 1:
                base_result = result
                series_rows["Zahndicke"].insert(0, rows[-1])
                series_rows["Zahnhöhe"].insert(0, rows[-1])
                series_rows["Zahnfuß"].insert(0, rows[-1])
                _plot_load_case(out, section, load, solution, result)
        print(
            f"{series} {label}: {result.nodes} nodes, sigma1 {result.root_sigma1_max_mpa:.3f} MPa, "
            f"u_tip {1000 * result.tip_centre_magnitude_mm:.3f} um, U {result.strain_energy_nmm:.5f}, {seconds:.1f} s",
            flush=True,
        )
    assert base_result is not None
    # sensitivity of the base mesh to the load patch and the position
    sensitivity: list[dict[str, Any]] = []
    rho_a, _ = pl.path_of_contact_limits(generation)
    p_bt = generation.pair_geometry.transverse_base_pitch_mm
    for label, scale, rho in (
        ("b_H × 0,5", 0.5, None),
        ("b_H × 2", 2.0, None),
        ("Punkt D", 1.0, rho_a + p_bt),
    ):
        section, load, solution, result, seconds = _run(
            generation,
            base,
            outline,
            rf.Refinement(),
            half_width_scale=scale,
            rho_1_mm=rho,
            **common,
        )
        sensitivity.append(_row(label, "Empfindlichkeit", 1, section, load, result, seconds))
    report.append("## Reihen")
    report.append("")
    report.extend(_markdown_table(rows))
    report.append("")
    report.append("## Empfindlichkeit des Grundnetzes gegen Lastbreite und Stellung")
    report.append("")
    report.extend(_markdown_table(sensitivity))
    report.append("")
    report.append("## Extrapolation (Richardson, letzte drei Stufen)")
    report.append("")
    limits_sigma: dict[str, float | None] = {}
    limits_tip: dict[str, float | None] = {}
    for series in ("gleichmäßig", "Zahndicke"):
        chosen = series_rows[series]
        report.append(f"### Reihe {series}")
        report.append("")
        for name, key, unit, store in (
            ("σ1,max im Zahnfuß", "root_sigma1_max_mpa", "MPa", limits_sigma),
            ("u Kopfmitte", "tip_centre_um", "µm", limits_tip),
            ("u Kopfecke", "tip_corner_um", "µm", None),
            ("Formänderungsenergie U", "strain_energy_nmm", "N mm/mm", None),
        ):
            lines = _richardson_lines(name, chosen, key, unit)
            report.extend(lines)
            report.append("")
            if store is not None:
                fit = cv.richardson(
                    [1.0 / float(r["level"]) for r in chosen], [float(r[key]) for r in chosen]
                )
                store[series] = fit.limit
    for series in ("Zahnhöhe", "Zahnfuß"):
        chosen = series_rows[series]
        report.append(f"### Reihe {series}")
        report.append("")
        for name, key, unit in (
            ("σ1,max im Zahnfuß", "root_sigma1_max_mpa", "MPa"),
            ("u Kopfmitte", "tip_centre_um", "µm"),
        ):
            report.extend(_richardson_lines(name, chosen, key, unit))
            report.append("")
    _plot_series(
        out,
        "convergence_root_stress.png",
        series_rows,
        "root_sigma1_max_mpa",
        r"$\sigma_{1,\mathrm{max}}$ an der Fußoberfläche in MPa",
        limits_sigma,
    )
    _plot_series(
        out,
        "convergence_tip_displacement.png",
        series_rows,
        "tip_centre_um",
        "Verschiebung der Kopfmitte in µm",
        limits_tip,
    )
    _plot_series(
        out,
        "convergence_strain_energy.png",
        series_rows,
        "strain_energy_nmm",
        "Formänderungsenergie U in N mm je mm Breite",
        {},
    )
    _plot_fillet(out, fillet)
    with (out / "convergence.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows + sensitivity)
    (out / "convergence.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    return report


# --- verification in the Learning Edition ------------------------------------------------------


def _deck(
    section: sm.SectorMesh,
    load: cv.LoadCase,
    element: str,
    e_mpa: float,
    nu: float,
    title: str,
    evaluation: tuple[list[int], list[int], list[int]] | None = None,
) -> str:
    """The plane sector under the loads of the load case. Without ``evaluation`` every node
    and element is printed (the check in the Learning Edition); with it (tip nodes, fillet
    nodes, elements touching the fillet) only those sets are printed."""
    lines = [
        "*HEADING",
        title,
        "*NODE, NSET=ALLN",
    ]
    lines.extend(
        f"{k + 1}, {x:.12e}, {y:.12e}" for k, (x, y) in enumerate(section.points_mm.tolist())
    )
    lines.append(f"*ELEMENT, TYPE={element}, ELSET=ALLE")
    lines.extend(
        f"{k + 1}, " + ", ".join(str(n + 1) for n in quad)
        for k, quad in enumerate(section.quads.tolist())
    )
    fixed = np.flatnonzero(cv.fixed_nodes(section))
    lines.append("*NSET, NSET=FESSELUNG")
    labels = [str(n + 1) for n in fixed.tolist()]
    lines.extend(", ".join(labels[k : k + 16]) for k in range(0, len(labels), 16))
    lines.append("*SOLID SECTION, ELSET=ALLE, MATERIAL=PLASTIC")
    lines.append("1.0")
    lines.append("*MATERIAL, NAME=PLASTIC")
    lines.append("*ELASTIC")
    lines.append(f"{e_mpa:.6e}, {nu:.6e}")
    lines.append("*BOUNDARY")
    lines.append("FESSELUNG, 1, 2")
    lines.append("*STEP, NAME=LOAD")
    lines.append("*STATIC")
    lines.append("*CLOAD")
    for n in load.loaded_nodes.tolist():
        fx, fy = load.loads_n_per_mm[n]
        lines.append(f"{n + 1}, 1, {fx:.12e}")
        lines.append(f"{n + 1}, 2, {fy:.12e}")
    if evaluation is None:
        lines.append("*NODE PRINT, NSET=ALLN")
        lines.append("U")
        lines.append("*EL PRINT, ELSET=ALLE, POSITION=INTEGRATION POINT")
        lines.append("S")
        lines.append("*EL PRINT, ELSET=ALLE, POSITION=AVERAGED AT NODES")
        lines.append("S")
    else:
        tip_nodes, fillet_nodes, fillet_elements = evaluation
        lines.extend(_id_lines("NSET", "EVAL_TIP", tip_nodes))
        lines.extend(_id_lines("NSET", "EVAL_FILLET_NODES", fillet_nodes))
        lines.extend(_id_lines("ELSET", "EVAL_FILLET", fillet_elements))
        lines.append("*NODE PRINT, NSET=EVAL_TIP")
        lines.append("U")
        lines.append("*EL PRINT, ELSET=EVAL_FILLET, POSITION=AVERAGED AT NODES")
        lines.append("S")
    lines.append("*ENERGY PRINT")
    lines.append("*END STEP")
    return "\n".join(lines) + "\n"


FLOAT = r"[-+]?(?:\d+\.\d*|\.\d+)(?:E[-+]?\d+)?"
ENERGY_LABELS = {
    "RECOVERABLE STRAIN ENERGY": "ALLSE",
    "ENERGY TO CONTROL SPURIOUS MODES": "ALLAE",
    "TOTAL STRAIN ENERGY": "ALLIE",
    "EXTERNAL WORK": "ALLWK",
}


def _parse_dat(
    text: str,
) -> tuple[
    dict[int, tuple[float, ...]],
    dict[tuple[int, int], tuple[float, ...]],
    dict[int, tuple[float, ...]],
    dict[str, float],
]:
    """Displacements per node, stresses per (element, integration point), stresses averaged
    at the nodes, and the energies of the last summary, from the printed tables."""
    nodes: dict[int, tuple[float, ...]] = {}
    elements: dict[tuple[int, int], tuple[float, ...]] = {}
    nodal: dict[int, tuple[float, ...]] = {}
    energies: dict[str, float] = {}
    mode = ""
    # displacements: 2 (plane) or 3 components; stresses at nodes: 4 (plane) or 6 components
    node_line = re.compile(rf"^\s*(\d+)\s+((?:{FLOAT}\s+){{1,2}}{FLOAT})\s*$")
    nodal_line = re.compile(rf"^\s*(\d+)\s+((?:{FLOAT}\s+){{3,5}}{FLOAT})\s*$")
    element_line = re.compile(rf"^\s*(\d+)\s+(\d+)\s+((?:{FLOAT}\s*)+)$")
    for line in text.splitlines():
        if "NODE" in line and "U1" in line and "U2" in line:
            mode = "node"
            continue
        if "ELEMENT" in line and "PT" in line and "S11" in line:
            mode = "element"
            continue
        if "NODE" in line and "S11" in line:
            mode = "nodal"
            continue
        for label, name in ENERGY_LABELS.items():
            if label in line:
                numbers = re.findall(FLOAT, line)
                if numbers:
                    energies[name] = float(numbers[-1])
        if mode == "node":
            found = node_line.match(line)
            if found:
                nodes[int(found.group(1))] = tuple(
                    float(v) for v in re.findall(FLOAT, found.group(2))
                )
        elif mode == "element":
            found = element_line.match(line)
            if found:
                values = tuple(float(v) for v in re.findall(FLOAT, found.group(3)))
                elements[(int(found.group(1)), int(found.group(2)))] = values
        elif mode == "nodal":
            found = nodal_line.match(line)
            if found:
                nodal[int(found.group(1))] = tuple(
                    float(v) for v in re.findall(FLOAT, found.group(2))
                )
    return nodes, elements, nodal, energies


def _run_abaqus(folder: Path, job: str) -> None:
    command = f'"{ABAQUS}" job={job} input={job}.inp interactive ask_delete=OFF'
    completed = subprocess.run(
        command, cwd=folder, shell=True, capture_output=True, text=True, timeout=1200
    )
    (folder / f"{job}.console.txt").write_text(
        completed.stdout + completed.stderr, encoding="utf-8"
    )
    if not (folder / f"{job}.dat").exists():
        raise RuntimeError(
            f"Abaqus wrote no {job}.dat: {completed.stdout[-2000:]} {completed.stderr[-2000:]}"
        )


def verify(case: str, e_mpa: float, nu: float, torque_nm: float, out: Path) -> list[str]:
    generation = _generation(case)
    base = sm.sector_mesh(generation, "wheel", teeth=1, rim_rings=12)
    load = cv.wheel_load_case(
        generation,
        base,
        torque_wheel_nmm=1000.0 * torque_nm,
        youngs_modulus_mpa=e_mpa,
        poisson_ratio=nu,
        face_width_mm=15.0,
    )
    d = ps.plane_strain_matrix(e_mpa, nu)
    own: dict[str, tuple[ps.PlaneSolution, cv.Evaluation]] = {}
    for formulation in ps.FORMULATIONS:
        solution = ps.solve(
            base.points_mm,
            base.quads,
            d_matrix=d,
            fixed=cv.fixed_nodes(base),
            loads_n_per_mm=load.loads_n_per_mm,
            formulation=formulation,
        )
        own[formulation] = (solution, cv.evaluate(base, solution, load, nu))
    counterpart = {
        "CPE4": "selectively_reduced",
        "CPE4R": "selectively_reduced",
        "CPE4I": "incompatible_modes",
    }
    result = own["selectively_reduced"][1]
    fillet_elements = np.flatnonzero(np.isin(base.quads, result.fillet_nodes).any(axis=1))
    report = [
        f"# Prüfung des ebenen Lösers in der Abaqus Learning Edition 2025 ({case}, 1 Zahn + "
        "2 zahnlose Segmente, 12 Kranzringe)",
        "",
        f"{len(base.points_mm)} Knoten, {len(base.quads)} Elemente, Lastfall wie in der Studie "
        f"({_number(torque_nm, 0)} Nm am Rad, Punkt B), ebener Dehnungszustand, Dicke 1 mm. "
        "Abweichungen relativ zum größten Betrag der Größe; die .dat-Datei druckt 4 bis 5 Stellen. "
        "CPE4 und CPE4R werden mit der selektiv reduzierten Formulierung des eigenen Lösers verglichen, "
        "CPE4I mit der Formulierung mit inkompatiblen Moden.",
        "",
        "| Element | u Kopfmitte in µm | σ1,max Fuß (Knotenmittel) in MPa | σ1,max Fuß (Gaußpunkte) in MPa | "
        "ALLSE in N mm | ALLAE in N mm | Abw. u | Abw. S Gaußpunkte | Abw. σ1 Fußknoten |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    report_rows = []
    for element in ("CPE4", "CPE4R", "CPE4I"):
        solution, result = own[counterpart[element]]
        u_max = float(np.hypot(*solution.displacements_mm.T).max())
        own_fillet_sigma1 = result.fillet_sigma1_mpa
        job = f"le_{element.lower()}"
        (out / f"{job}.inp").write_text(
            _deck(base, load, element, e_mpa, nu, f"gearcore convergence check {case} {element}"),
            encoding="utf-8",
        )
        _run_abaqus(out, job)
        nodes, elements, nodal, energies = _parse_dat(
            (out / f"{job}.dat").read_text(encoding="utf-8", errors="replace")
        )
        # the .dat file leaves out the nodes whose displacements are all zero: the fixed ones
        missing = {k for k in range(len(base.points_mm)) if k + 1 not in nodes}
        fixed = set(np.flatnonzero(cv.fixed_nodes(base)).tolist())
        if not missing <= fixed or len(nodal) != len(base.points_mm):
            raise RuntimeError(
                f"{job}: {len(nodes)} displacements and {len(nodal)} nodal stresses read for "
                f"{len(base.points_mm)} nodes; {len(missing - fixed)} free nodes are missing"
            )
        u_abaqus = np.array([nodes.get(k + 1, (0.0, 0.0)) for k in range(len(base.points_mm))])
        u_diff = float(np.hypot(*(u_abaqus - solution.displacements_mm).T).max()) / u_max
        tip = 1000.0 * float(np.hypot(*u_abaqus[result.tip_centre_node]))
        # sigma1 at the integration points of the elements along the fillet
        points_per_element = max(pt for _, pt in elements)
        stress = np.array(
            [
                [elements[(e + 1, pt)][:4] for pt in range(1, points_per_element + 1)]
                for e in fillet_elements.tolist()
            ]
        )  # (m, pts, 4): S11, S22, S33, S12
        plane = stress[..., [0, 1, 3]]
        sigma1_gauss, _ = ps.principal_stresses(plane)
        averaged = np.array([nodal[int(n) + 1][:4] for n in result.fillet_nodes])[:, [0, 1, 3]]
        sigma1_nodal, _ = ps.principal_stresses(averaged)
        s_diff = sigma_diff = "–"
        if element != "CPE4R":
            own_gauss = solution.gauss_stress_mpa[fillet_elements][
                :, [0, 1, 3, 2], :
            ]  # Abaqus point order
            s_diff = _number(
                float(np.abs(plane - own_gauss).max()) / float(np.abs(own_gauss).max()), 6
            )
            sigma_diff = _number(
                float(np.abs(sigma1_nodal - own_fillet_sigma1).max())
                / float(np.abs(own_fillet_sigma1).max()),
                6,
            )
        report_rows.append(
            f"| {element} | {_number(tip, 3)} | {_number(float(sigma1_nodal.max()), 2)} | "
            f"{_number(float(sigma1_gauss.max()), 2)} | {_number(energies.get('ALLSE', math.nan), 5)} | "
            f"{_number(energies.get('ALLAE', 0.0), 6)} | {_number(u_diff, 7)} | {s_diff} | {sigma_diff} |"
        )
        print(
            f"{element}: tip {tip:.3f} um, sigma1 nodal {sigma1_nodal.max():.2f} MPa, gauss {sigma1_gauss.max():.2f}, "
            f"ALLSE {energies.get('ALLSE')}, ALLAE {energies.get('ALLAE')}, u diff {u_diff:.2e}, S diff {s_diff}, "
            f"sigma1 diff {sigma_diff}",
            flush=True,
        )
    report.extend(report_rows)
    for formulation, (solution, result) in own.items():
        own_gauss_sigma1, _ = ps.principal_stresses(solution.gauss_stress_mpa[fillet_elements])
        report.append(
            f"| eigener Löser, {FORMULATION_TEXT[formulation]} | "
            f"{_number(1000.0 * result.tip_centre_magnitude_mm, 3)} | "
            f"{_number(result.root_sigma1_max_mpa, 2)} | {_number(float(own_gauss_sigma1.max()), 2)} | "
            f"{_number(solution.strain_energy_nmm, 5)} | – | – | – | – |"
        )
    report.append("")
    report.append(
        "σ1,max Fuß (Gaußpunkte): Größtwert an den Integrationspunkten der Elemente entlang der Fußoberfläche "
        "der belasteten Flanke; Knotenmittel: aus den auf die Knoten extrapolierten und gemittelten Spannungen "
        "(Abaqus POSITION=AVERAGED AT NODES über alle Elemente), wie in der Studie."
    )
    (out / "verification.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    return report


# --- decks for the full licence and the comparison of their results ------------------------------

FULL_LICENCE_2D = (
    ("base", rf.Refinement()),
    ("t2", rf.Refinement(thickness=2)),
    ("t3", rf.Refinement(thickness=3)),
    ("t4", rf.Refinement(thickness=4)),
    ("u2", rf.Refinement(uniform=2)),
)
FULL_LICENCE_ELEMENTS_2D = ("CPE4R", "CPE4", "CPE4I")
FULL_LICENCE_LAYERS = (20, 40, 80)
FULL_LICENCE_ELEMENTS_3D = ("C3D8R", "C3D8I")
COUNTERPART = {
    "CPE4": "selectively_reduced",
    "CPE4R": "selectively_reduced",
    "CPE4I": "incompatible_modes",
    "C3D8": "selectively_reduced",
    "C3D8R": "selectively_reduced",
    "C3D8I": "incompatible_modes",
}


def _id_lines(keyword: str, name: str, ids: list[int]) -> list[str]:
    labels = [str(i + 1) for i in ids]
    lines = [f"*{keyword}, {keyword}={name}"]
    lines.extend(", ".join(labels[k : k + 16]) for k in range(0, len(labels), 16))
    return lines


def _evaluation_sets(
    section: sm.SectorMesh, result: cv.Evaluation
) -> tuple[list[int], list[int], list[int]]:
    """Tip nodes (centre, corner), fillet nodes and the elements touching the fillet, 0-based."""
    fillet_nodes = [int(n) for n in result.fillet_nodes]
    touching = np.flatnonzero(np.isin(section.quads, result.fillet_nodes).any(axis=1))
    return (
        [result.tip_centre_node, result.tip_corner_node],
        fillet_nodes,
        [int(q) for q in touching],
    )


def _deck_3d(
    solid: so.SolidMesh,
    sets: so.GearSets,
    load: cv.LoadCase,
    element: str,
    e_mpa: float,
    nu: float,
    title: str,
    evaluation: tuple[list[int], list[int], list[int]],
) -> str:
    """The swept sector under the loads of the plane load case, spread over the face width
    (trapezoidal weights of the z-levels), the bore and the cut planes fixed; prints the tip
    displacements and the stresses averaged at the nodes of the loaded fillet on every level."""
    n = len(solid.section.points_mm)
    m = len(solid.section.quads)
    levels = len(solid.z_levels_mm)
    layers = levels - 1
    tip_nodes, fillet_nodes, fillet_elements = evaluation
    text = ab.mesh_text(solid, sets, element_type=element, title=title)
    lines = [text.rstrip("\n")]
    lines.extend(
        _id_lines("NSET", "EVAL_TIP", [k * n + i for k in range(levels) for i in tip_nodes])
    )
    lines.extend(
        _id_lines(
            "NSET", "EVAL_FILLET_NODES", [k * n + i for k in range(levels) for i in fillet_nodes]
        )
    )
    lines.extend(
        _id_lines(
            "ELSET", "EVAL_FILLET", [k * m + q for k in range(layers) for q in fillet_elements]
        )
    )
    lines.append(f"*SOLID SECTION, ELSET={sets.prefix}, MATERIAL=PLASTIC")
    lines.append("*MATERIAL, NAME=PLASTIC")
    lines.append("*ELASTIC")
    lines.append(f"{e_mpa:.6e}, {nu:.6e}")
    lines.append("*BOUNDARY")
    lines.append(f"{sets.prefix}_FESSELUNG, 1, 3")
    lines.append("*STEP, NAME=LOAD")
    lines.append("*STATIC")
    lines.append("*CLOAD")
    dz = float(solid.z_levels_mm[1] - solid.z_levels_mm[0])
    weights = np.full(levels, dz)
    weights[0] = weights[-1] = 0.5 * dz
    for k in range(levels):
        for i in load.loaded_nodes.tolist():
            fx, fy = load.loads_n_per_mm[i] * weights[k]
            lines.append(f"{k * n + i + 1}, 1, {fx:.12e}")
            lines.append(f"{k * n + i + 1}, 2, {fy:.12e}")
    lines.append("*NODE PRINT, NSET=EVAL_TIP")
    lines.append("U")
    lines.append("*EL PRINT, ELSET=EVAL_FILLET, POSITION=AVERAGED AT NODES")
    lines.append("S")
    lines.append("*ENERGY PRINT")
    lines.append("*END STEP")
    return "\n".join(lines) + "\n"


def decks(
    case: str, teeth: int, rim_rings: int, torque_nm: float, e_mpa: float, nu: float, out: Path
) -> list[str]:
    """Write the decks for the full licence: the plane sector at five refinements with three
    element types, and the swept sector at 20, 40 and 80 layers with two element types; a batch
    file, a manifest for ``compare`` and the instructions."""
    generation = _generation(case)
    outline = ct.tooth_contour(generation, "wheel", points=2000).as_array()
    base = sm.sector_mesh(generation, "wheel", teeth=teeth, rim_rings=rim_rings)
    gear = generation.inputs.gears.wheel
    torque = 1000.0 * torque_nm
    common: dict[str, Any] = {
        "torque_nmm": torque,
        "e_mpa": e_mpa,
        "nu": nu,
        "width_mm": gear.face_width_mm,
    }
    jobs: list[dict[str, Any]] = []
    report = []
    for label, refinement in FULL_LICENCE_2D:
        own: dict[str, dict[str, float]] = {}
        section = load = result = None
        for formulation in ps.FORMULATIONS:
            section, load, _, result, _ = _run(
                generation, base, outline, refinement, formulation=formulation, **common
            )
            own[formulation] = {
                "sigma1_mpa": result.root_sigma1_max_mpa,
                "tip_centre_um": 1000.0 * result.tip_centre_magnitude_mm,
                "tip_corner_um": 1000.0 * result.tip_corner_magnitude_mm,
            }
        assert section is not None and load is not None and result is not None
        evaluation = _evaluation_sets(section, result)
        for element in FULL_LICENCE_ELEMENTS_2D:
            name = f"plane_{label}_{element.lower()}"
            (out / f"{name}.inp").write_text(
                _deck(
                    section,
                    load,
                    element,
                    e_mpa,
                    nu,
                    f"gearcore {case} plane {label} {element}",
                    evaluation,
                ),
                encoding="utf-8",
            )
            jobs.append(
                {
                    "name": name,
                    "kind": "plane",
                    "label": label,
                    "level": max(refinement.thickness, refinement.uniform),
                    "element": element,
                    "nodes": len(section.points_mm),
                    "tip_nodes": evaluation[0],
                    "fillet_nodes": evaluation[1],
                    "own": own,
                }
            )
        report.append(
            f"plane {label}: {len(section.points_mm)} nodes, {len(section.quads)} elements"
        )
    # swept sector at the template density
    section, load, _, result, _ = _run(generation, base, outline, rf.Refinement(), **common)
    evaluation = _evaluation_sets(section, result)
    for layers in FULL_LICENCE_LAYERS:
        solid = so.extrude(section, face_width_mm=gear.face_width_mm, layers=layers)
        sets = so.gear_sets(solid, "WHEEL")
        for element in FULL_LICENCE_ELEMENTS_3D:
            name = f"solid_{layers}layers_{element.lower()}"
            (out / f"{name}.inp").write_text(
                _deck_3d(
                    solid,
                    sets,
                    load,
                    element,
                    e_mpa,
                    nu,
                    f"gearcore {case} solid {layers} layers {element}",
                    evaluation,
                ),
                encoding="utf-8",
            )
            jobs.append(
                {
                    "name": name,
                    "kind": "solid",
                    "label": f"{layers} layers",
                    "level": layers,
                    "element": element,
                    "nodes": len(solid.nodes_mm),
                    "nodes_per_level": len(section.points_mm),
                    "levels": layers + 1,
                    "tip_nodes": evaluation[0],
                    "fillet_nodes": evaluation[1],
                    "own": {},
                }
            )
        report.append(
            f"solid {layers} layers: {len(solid.nodes_mm)} nodes, {len(solid.hexes)} elements"
        )
    (out / "manifest.json").write_text(json.dumps(jobs, indent=1), encoding="utf-8")
    (out / "run_all.bat").write_text(
        "@echo off\r\n"
        "rem Alle Decks nacheinander mit der Abaqus-Vollversion rechnen\r\n"
        "rem (aus der Abaqus-Eingabeaufforderung in diesem Ordner starten).\r\n"
        "rem Ohne Parameter wird der Starter 'abaqus' benutzt; ein anderer Starter wird als\r\n"
        "rem Parameter uebergeben, zum Beispiel:  run_all.bat abq2025\r\n"
        'if "%~1"=="" (set ABQ=abaqus) else (set ABQ=%~1)\r\n'
        "echo Starter: %ABQ%\r\n"
        "call %ABQ% information=release\r\n"
        "for %%f in (plane_*.inp solid_*.inp) do (\r\n"
        "  echo === %%~nf ===\r\n"
        "  call %ABQ% job=%%~nf input=%%f cpus=4 interactive ask_delete=OFF\r\n"
        ")\r\n"
        "echo fertig\r\n",
        encoding="ascii",
    )
    (out / "README.md").write_text(
        "\n".join(
            [
                "# Konvergenzdecks für die Abaqus-Vollversion",
                "",
                f"Radsektor {case}, {teeth} Zähne + 2 zahnlose Segmente, {rim_rings} Kranzringe, Last an Punkt B "
                f"({_number(torque_nm, 0)} Nm am Rad) als Knotenlasten, isotrop E = {_number(e_mpa, 0)} MPa, "
                f"ν = {_number(nu, 2)}, Bohrung und Schnittebenen fest.",
                "",
                "`plane_*`: ebener Dehnungszustand, Stufen base (gestriges Netz), t2/t3/t4 (Zahndicke ×2/×3/×4), "
                "u2 (gleichmäßig ×2), je mit CPE4R, CPE4 und CPE4I. `solid_*`: Volumennetz mit 20, 40 und 80 "
                "Schichten, je mit C3D8R und C3D8I (bis 301 000 Knoten, linear statisch).",
                "",
                "## Ablauf",
                "",
                "1. Diesen Ordner auf den Rechner mit der Vollversion kopieren.",
                "2. Dort die Abaqus-Eingabeaufforderung öffnen (Startmenü: Abaqus Command) und in den Ordner wechseln.",
                "3. Prüfen, welcher Starter die Vollversion aufruft: `abaqus information=release` eingeben. "
                "Die Ausgabe muss die Vollversion 2025 nennen (nicht Learning Edition, nicht Student "
                "Edition). Die Starter liegen in `C:\\SIMULIA\\Commands` (`dir C:\\SIMULIA\\Commands` "
                "zeigt sie, zum Beispiel `abaqus.bat`, `abq2025.bat`; auf dem Rechner hier heißt die "
                "Learning Edition `abq2025le.bat`).",
                "4. `run_all.bat` starten, wenn `abaqus` die Vollversion ist; sonst den passenden Starter "
                "als Parameter angeben: `run_all.bat abq2025` (der Name ohne `.bat`). Die Stapeldatei "
                "zeigt zuerst die Version des gewählten Starters an. Jedes Deck rechnet für sich "
                "(`interactive`); die ebenen Decks brauchen Sekunden, die Volumendecks Minuten.",
                "5. Die `.dat`-Dateien (und zur Kontrolle die `.sta`-Dateien) in denselben Ordner auf diesem Rechner "
                "zurückkopieren. Bricht ein Volumendeck ab, bitte auch die `.msg`-Datei mitgeben.",
                "6. Hier auswerten: `python scripts/fe_mesh_convergence.py compare --case "
                + case
                + "` schreibt "
                "`comparison.md` mit den Abaqus-Werten neben denen des eigenen Lösers.",
                "",
                "Ausgewertet werden die Verschiebung der Kopfmitte und der belasteten Kopfecke (Knotenmenge "
                "EVAL_TIP) und die Hauptspannung an den Knoten der belasteten Fußoberfläche (Elementmenge "
                "EVAL_FILLET, an den Knoten gemittelt), beim Volumennetz auf jeder Schicht.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    report.append(f"{len(jobs)} decks, run_all.bat, manifest.json and README.md written")
    return report


def _principal_max(components: np.ndarray) -> np.ndarray:
    """Largest principal stress from (…, 3) plane or (…, 6) Abaqus components."""
    if components.shape[-1] == 3:
        return ps.principal_stresses(components)[0]
    s11, s22, s33, s12, s13, s23 = (components[..., k] for k in range(6))
    tensor = np.empty(components.shape[:-1] + (3, 3))
    tensor[..., 0, 0], tensor[..., 1, 1], tensor[..., 2, 2] = s11, s22, s33
    tensor[..., 0, 1] = tensor[..., 1, 0] = s12
    tensor[..., 0, 2] = tensor[..., 2, 0] = s13
    tensor[..., 1, 2] = tensor[..., 2, 1] = s23
    return np.linalg.eigvalsh(tensor)[..., -1]


def compare(out: Path) -> list[str]:
    """Read the ``.dat`` files of the decks written by ``decks`` and put their results beside
    the own solver."""
    jobs = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    lines = ["# Vergleich der Abaqus-Vollversion mit dem eigenen Löser", ""]
    plane_rows: list[tuple[str, str, int, float, float, float, float, float]] = []
    solid_rows: list[str] = []
    missing: list[str] = []
    for job in jobs:
        path = out / f"{job['name']}.dat"
        if not path.exists():
            missing.append(str(job["name"]))
            continue
        nodes, _, nodal, energies = _parse_dat(path.read_text(encoding="utf-8", errors="replace"))
        tip_nodes = [int(i) for i in job["tip_nodes"]]
        fillet = [int(i) for i in job["fillet_nodes"]]
        if job["kind"] == "plane":
            u_tip = 1000.0 * math.hypot(*nodes.get(tip_nodes[0] + 1, (0.0, 0.0))[:2])
            sigma1 = float(
                _principal_max(np.array([nodal[i + 1][:4] for i in fillet])[:, [0, 1, 3]]).max()
            )
            own = job["own"][COUNTERPART[str(job["element"])]]
            plane_rows.append(
                (
                    str(job["label"]),
                    str(job["element"]),
                    int(job["nodes"]),
                    u_tip,
                    float(own["tip_centre_um"]),
                    sigma1,
                    float(own["sigma1_mpa"]),
                    energies.get("ALLAE", 0.0),
                )
            )
        else:
            n, levels = int(job["nodes_per_level"]), int(job["levels"])
            middle = (levels - 1) // 2
            per_level_u = []
            per_level_sigma = []
            for k in range(levels):
                per_level_u.append(
                    1000.0 * math.hypot(*nodes.get(k * n + tip_nodes[0] + 1, (0.0, 0.0, 0.0)))
                )
                stress = np.array(
                    [nodal[k * n + i + 1][:6] for i in fillet if (k * n + i + 1) in nodal]
                )
                per_level_sigma.append(
                    float(_principal_max(stress).max()) if len(stress) else math.nan
                )
            solid_rows.append(
                f"| {job['label']} | {job['element']} | {job['nodes']} | {_number(per_level_u[middle], 3)} | "
                f"{_number(per_level_u[0], 3)} | {_number(per_level_sigma[middle], 2)} | "
                f"{_number(max(per_level_sigma), 2)} | {_number(per_level_sigma[0], 2)} | "
                f"{_number(energies.get('ALLSE', math.nan), 4)} | {_number(energies.get('ALLAE', 0.0), 6)} |"
            )
    if plane_rows:
        lines.append("## Ebene Decks")
        lines.append("")
        lines.append(
            "| Stufe | Element | Knoten | u Kopfmitte Abaqus in µm | eigener Löser | σ1,max Fuß Abaqus in MPa | "
            "eigener Löser | ALLAE in N mm |"
        )
        lines.append("|---|---|---|---|---|---|---|---|")
        for label, element, count, u_abq, u_own, s_abq, s_own, allae in plane_rows:
            lines.append(
                f"| {label} | {element} | {count} | {_number(u_abq, 3)} | {_number(u_own, 3)} | "
                f"{_number(s_abq, 2)} | {_number(s_own, 2)} | {_number(allae, 6)} |"
            )
        lines.append("")
        lines.append(
            "Der eigene Löser steht je Zeile in der Formulierung des Elements (CPE4 und CPE4R: selektiv "
            "reduziert; CPE4I: inkompatible Moden)."
        )
        lines.append("")
        for element in FULL_LICENCE_ELEMENTS_2D:
            series = [
                (label, s_abq)
                for label, el, _, _, _, s_abq, _, _ in plane_rows
                if el == element and label in ("base", "t2", "t3", "t4")
            ]
            if len(series) >= 3:
                h = [1.0 / (1 if label == "base" else int(label[1:])) for label, _ in series]
                richardson = cv.richardson(h, [s for _, s in series])
                limit = (
                    "keine monotone Konvergenz"
                    if richardson.limit is None
                    else (
                        f"Grenzwert {_number(richardson.limit, 2)} MPa, Ordnung {_number(richardson.order or 0.0, 2)}"
                    )
                )
                lines.append(
                    f"Reihe Zahndicke mit {element}: σ1 = "
                    + ", ".join(_number(s, 2) for _, s in series)
                    + f" MPa; {limit}."
                )
        lines.append("")
    if solid_rows:
        lines.append("## Volumendecks (Schichten über die Zahnbreite)")
        lines.append("")
        lines.append(
            "| Schichten | Element | Knoten | u Kopfmitte Radmitte in µm | u Kopfmitte Stirnfläche | "
            "σ1,max Fuß Radmitte in MPa | σ1,max Fuß größte Schicht | σ1,max Fuß Stirnfläche | "
            "ALLSE in N mm | ALLAE in N mm |"
        )
        lines.append("|---|---|---|---|---|---|---|---|---|---|")
        lines.extend(solid_rows)
        lines.append("")
    if missing:
        lines.append("Noch ohne `.dat`-Datei: " + ", ".join(missing))
    (out / "comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return lines


# --- recommendation of the numbers of elements for a gearing ---------------------------------

REDUCTION = (
    ("over_tooth_height", (12, 9, 6)),
    ("at_tip_edge_break", (1,)),
    ("at_tooth_root", (60, 40, 20)),
    ("rim_rings", (8, 6, 4)),
    ("shoulder_columns", (3, 2)),
)
"""The other numbers, coarsened one at a time from the template downwards after the ladder."""
REDUCTION_NAMES = {
    "over_tooth_height": "Zahnhöhe",
    "at_tip_edge_break": "Kopfkantenbruch",
    "at_tooth_root": "Zahnfuß",
    "rim_rings": "Kranzringe",
    "shoulder_columns": "Spalten zahnfreies Segment",
}
LADDER = ((10, 3), (14, 4), (20, 6), (26, 8), (32, 10), (40, 12))
"""(elements over the tooth thickness, layers normal to the root surface), both growing in
proportion (element size 1, 3/4, 1/2, 3/8, 3/10, 1/4 of the template): the direction the
convergence study found to matter; height, root and rim keep the numbers of the template."""


def recommend(
    case: str,
    teeth: int,
    rim_rings: int,
    torque_nm: float,
    e_mpa: float,
    nu: float,
    formulation: str,
    tolerance_stress: float,
    tolerance_displacement: float,
    max_nodes_per_layer: int | None,
    layers: int,
    out: Path,
) -> list[str]:
    """Run the ladder of meshes for the gearing, extrapolate, and name the coarsest mesh whose
    root surface stress and tip displacement lie within the tolerances of the extrapolated
    limits (and within the node budget, if one is given)."""
    generation = _generation(case)
    gear = generation.inputs.gears.wheel
    base = sm.sector_mesh(generation, "wheel", teeth=teeth, rim_rings=rim_rings)
    outline = ct.tooth_contour(generation, "wheel", points=2000).as_array()
    rows: list[dict[str, Any]] = []
    for thickness, root_layers in LADDER:
        counts = rs.MeshCounts(over_tooth_thickness=thickness, root_layers=root_layers)
        section, load, _, result, seconds = _run(
            generation,
            base,
            outline,
            counts,
            torque_nmm=1000.0 * torque_nm,
            e_mpa=e_mpa,
            nu=nu,
            width_mm=gear.face_width_mm,
            formulation=formulation,
        )
        rows.append(_row(counts.label(), "Leiter", root_layers, section, load, result, seconds))
        rows[-1]["counts"] = counts
        if thickness == LADDER[0][0]:
            # the flank must resolve the contact of the mating gear: at least three elements
            # per Hertz half width along the active flank (the template has exactly that)
            points = section.points_mm
            radius = np.hypot(points[:, 0], points[:, 1])
            flank_length = sum(
                float(np.hypot(*(points[b] - points[a])))
                for a, b, tooth, side, band in cv._surface_edges_of(section)
                if tooth == load.loaded_tooth
                and side == load.loaded_side
                and band == "height"
                and 0.5 * (radius[a] + radius[b]) < section.tip_form_radius_mm  # involute only
            )
            half_width = load.half_width_mm
            floor_height = math.ceil(flank_length / (half_width / 3.0))
        print(
            f"thickness {thickness}, root layers {root_layers}: {result.nodes} nodes, sigma1 "
            f"{result.root_sigma1_max_mpa:.2f} MPa, u_tip {1000 * result.tip_centre_magnitude_mm:.2f} um",
            flush=True,
        )
    h = [3.0 / float(r["level"]) for r in rows]
    sigma = cv.richardson_fit(h, [float(r["root_sigma1_max_mpa"]) for r in rows])
    tip = cv.richardson_fit(h, [float(r["tip_centre_um"]) for r in rows])
    report = [
        f"# Empfehlung der Netzfeinheit für {case} ({teeth} Zähne + 2, {rim_rings} Kranzringe, "
        f"{FORMULATION_TEXT[formulation]})",
        "",
        f"Toleranz σ1 {_number(100 * tolerance_stress, 1)} %, Kopfverschiebung "
        f"{_number(100 * tolerance_displacement, 1)} %"
        + (f", höchstens {max_nodes_per_layer} Knoten je Schicht" if max_nodes_per_layer else "")
        + f"; Knotenzahl des Volumennetzes für {layers} Schichten.",
        "",
        "| Zahndicke | Fußschichten | Knoten je Schicht | Knoten Volumen | σ1,max Fuß in MPa | Fehler | "
        "u Kopfmitte in µm | Fehler |",
        "|---|---|---|---|---|---|---|---|",
    ]
    chosen: rs.MeshCounts | None = None
    for k, r in enumerate(rows):
        counts = r["counts"]
        assert isinstance(counts, rs.MeshCounts)
        e_sigma = sigma.relative_error[k] if sigma.relative_error else math.nan
        e_tip = tip.relative_error[k] if tip.relative_error else math.nan
        nodes = int(r["nodes"])
        within = (
            abs(e_sigma) <= tolerance_stress
            and abs(e_tip) <= tolerance_displacement
            and (max_nodes_per_layer is None or nodes <= max_nodes_per_layer)
        )
        if within and chosen is None:
            chosen = counts
        report.append(
            f"| {counts.over_tooth_thickness} | {counts.root_layers} | {nodes} | {nodes * (layers + 1)} | "
            f"{_number(float(r['root_sigma1_max_mpa']), 2)} | {_number(100 * e_sigma, 2)} % | "
            f"{_number(float(r['tip_centre_um']), 2)} | {_number(100 * e_tip, 2)} % |"
            + (" ← Empfehlung" if counts is chosen else "")
        )
    report.append("")
    if sigma.limit is not None and tip.limit is not None:
        report.append(
            f"Grenzwerte (Ausgleich f = f₀ + C hᵖ über alle Stufen): σ1 = {_number(sigma.limit, 2)} MPa "
            f"(Ordnung {_number(sigma.order or 0.0, 2)}), u = {_number(tip.limit, 2)} µm "
            f"(Ordnung {_number(tip.order or 0.0, 2)})."
        )
    else:
        report.append(
            "Der Ausgleich über die Stufen liefert keinen Grenzwert: keine Empfehlung möglich."
        )
    reduced = chosen
    if chosen is not None and sigma.limit is not None and tip.limit is not None:
        # second phase: coarsen the other numbers one at a time, from the template downwards,
        # as long as both quantities stay within the tolerances of the limits found above
        report.append("")
        report.append(
            "## Reduktion der übrigen Anzahlen (eine nach der anderen, gegen die Grenzwerte oben)"
        )
        report.append("")
        report.append("| Größe | Wert | Knoten je Schicht | σ1 Fehler | u Fehler | angenommen |")
        report.append("|---|---|---|---|---|---|")
        assert reduced is not None
        for name, values in REDUCTION:
            for value in values:
                if name == "over_tooth_height" and value < floor_height:
                    report.append(
                        f"| Zahnhöhe | {value} | – | – | – | nein: die Flanke braucht mindestens "
                        f"{floor_height} Elemente, drei je Hertzscher Halbbreite "
                        f"({_number(half_width, 3)} mm) für den Kontakt |"
                    )
                    break
                candidate = replace(reduced, **{name: value})
                section, load, _, result, _ = _run(
                    generation,
                    base,
                    outline,
                    candidate,
                    torque_nmm=1000.0 * torque_nm,
                    e_mpa=e_mpa,
                    nu=nu,
                    width_mm=gear.face_width_mm,
                    formulation=formulation,
                )
                e_s = (result.root_sigma1_max_mpa - sigma.limit) / abs(sigma.limit)
                e_u = (1000.0 * result.tip_centre_magnitude_mm - tip.limit) / abs(tip.limit)
                accepted = abs(e_s) <= tolerance_stress and abs(e_u) <= tolerance_displacement
                report.append(
                    f"| {REDUCTION_NAMES[name]} | {value} | {result.nodes} | {_number(100 * e_s, 2)} % | "
                    f"{_number(100 * e_u, 2)} % | {'ja' if accepted else 'nein'} |"
                )
                print(
                    f"reduce {name} -> {value}: {result.nodes} nodes, accepted {accepted}",
                    flush=True,
                )
                if not accepted:
                    break
                reduced = candidate
    if reduced is not None:
        final_section, _, _, final_result, _ = _run(
            generation,
            base,
            outline,
            reduced,
            torque_nmm=1000.0 * torque_nm,
            e_mpa=e_mpa,
            nu=nu,
            width_mm=gear.face_width_mm,
            formulation=formulation,
        )
        report.append("")
        report.append(
            f"**Empfehlung:** Zahnhöhe {reduced.over_tooth_height} + {reduced.at_tip_edge_break}, "
            f"Zahnfuß {reduced.at_tooth_root}, Zahndicke {reduced.over_tooth_thickness}, Fußschichten "
            f"{reduced.root_layers}, Kranzringe {reduced.rim_rings}, Spalten im zahnfreien Segment "
            f"{reduced.shoulder_columns}: {final_result.nodes} Knoten je Schicht, "
            f"{final_result.nodes * (layers + 1)} Knoten bei {layers} Schichten. Elementtyp für das "
            "Kunststoffrad: C3D8I (inkompatible Moden); C3D8R liest die Oberflächenspannung am Fuß "
            "um rund 23 %, C3D8 um 15 % zu niedrig (Studie 2026-10-06). Aufruf: "
            f"`build_fe_decks.py mesh --over-tooth-height {reduced.over_tooth_height} "
            f"--at-tip-edge-break {reduced.at_tip_edge_break} --at-tooth-root {reduced.at_tooth_root} "
            f"--over-tooth-thickness {reduced.over_tooth_thickness} --root-layers {reduced.root_layers} "
            f"--rings {reduced.rim_rings} --shoulder-columns {reduced.shoulder_columns} "
            "--element-type C3D8I`."
        )
        del final_section
    else:
        report.append("")
        report.append("Keine Stufe der Leiter erfüllt die Toleranzen innerhalb des Budgets.")
    with (out / "recommendation.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = [k for k in rows[0] if k != "counts"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows({k: r[k] for k in fields} for r in rows)
    (out / "recommendation.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    return report


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # the report holds Greek letters
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    commands = parser.add_subparsers(dest="command", required=True)
    study_parser = commands.add_parser("study")
    study_parser.add_argument("--case", default="kst_e")
    study_parser.add_argument("--teeth", type=int, default=5)
    study_parser.add_argument("--rim-rings", type=int, default=12)
    study_parser.add_argument("--torque", type=float, default=16.0, help="N m at the wheel")
    study_parser.add_argument(
        "--youngs-modulus",
        type=float,
        default=2282.0,
        help="MPa (isotropic row of the card at 80 °C)",
    )
    study_parser.add_argument("--poisson-ratio", type=float, default=0.30)
    study_parser.add_argument("--levels", type=int, default=3, help="uniform levels h, h/2, ...")
    study_parser.add_argument(
        "--formulation",
        choices=ps.FORMULATIONS,
        default=ps.FORMULATIONS[0],
        help="element formulation of the own solver (CPE4/C3D8 or CPE4I/C3D8I counterpart)",
    )
    study_parser.add_argument("--out", type=Path, default=None)
    verify_parser = commands.add_parser("verify")
    verify_parser.add_argument("--case", default="kst_e")
    verify_parser.add_argument("--torque", type=float, default=16.0)
    verify_parser.add_argument("--youngs-modulus", type=float, default=2282.0)
    verify_parser.add_argument("--poisson-ratio", type=float, default=0.30)
    verify_parser.add_argument("--out", type=Path, default=None)
    decks_parser = commands.add_parser("decks", help="decks for the full licence")
    decks_parser.add_argument("--case", default="kst_e")
    decks_parser.add_argument("--teeth", type=int, default=5)
    decks_parser.add_argument("--rim-rings", type=int, default=12)
    decks_parser.add_argument("--torque", type=float, default=16.0)
    decks_parser.add_argument("--youngs-modulus", type=float, default=2282.0)
    decks_parser.add_argument("--poisson-ratio", type=float, default=0.30)
    decks_parser.add_argument("--out", type=Path, default=None)
    compare_parser = commands.add_parser("compare", help="read the .dat files of the decks")
    compare_parser.add_argument("--case", default="kst_e")
    compare_parser.add_argument("--out", type=Path, default=None)
    recommend_parser = commands.add_parser(
        "recommend", help="coarsest mesh within the tolerances for a gearing"
    )
    recommend_parser.add_argument("--case", default="kst_e")
    recommend_parser.add_argument("--teeth", type=int, default=5)
    recommend_parser.add_argument("--rim-rings", type=int, default=12)
    recommend_parser.add_argument("--torque", type=float, default=16.0)
    recommend_parser.add_argument("--youngs-modulus", type=float, default=2282.0)
    recommend_parser.add_argument("--poisson-ratio", type=float, default=0.30)
    recommend_parser.add_argument(
        "--formulation", choices=ps.FORMULATIONS, default="incompatible_modes"
    )
    recommend_parser.add_argument("--tolerance-stress", type=float, default=0.02)
    recommend_parser.add_argument("--tolerance-displacement", type=float, default=0.01)
    recommend_parser.add_argument("--max-nodes-per-layer", type=int, default=None)
    recommend_parser.add_argument("--layers", type=int, default=80)
    recommend_parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()
    folder = "convergence"
    if args.command == "study" and args.formulation != ps.FORMULATIONS[0]:
        folder += f"_{args.formulation}"
    if args.command in ("decks", "compare"):
        folder = "full_licence"
    if args.command == "recommend":
        folder = "recommendation"
    out = args.out if args.out is not None else OUTPUT / args.case / folder
    out.mkdir(parents=True, exist_ok=True)
    if args.command == "recommend":
        lines = recommend(
            args.case,
            args.teeth,
            args.rim_rings,
            args.torque,
            args.youngs_modulus,
            args.poisson_ratio,
            args.formulation,
            args.tolerance_stress,
            args.tolerance_displacement,
            args.max_nodes_per_layer,
            args.layers,
            out,
        )
    elif args.command == "decks":
        lines = decks(
            args.case,
            args.teeth,
            args.rim_rings,
            args.torque,
            args.youngs_modulus,
            args.poisson_ratio,
            out,
        )
    elif args.command == "compare":
        lines = compare(out)
    elif args.command == "study":
        lines = study(
            args.case,
            args.teeth,
            args.rim_rings,
            args.torque,
            args.youngs_modulus,
            args.poisson_ratio,
            args.levels,
            out,
            args.formulation,
        )
    else:
        lines = verify(args.case, args.youngs_modulus, args.poisson_ratio, args.torque, out)
    print("\n".join(lines))
    print(f"written to {out}")


if __name__ == "__main__":
    main()
