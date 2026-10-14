"""Parameter sweep of the root fillet variants on the plane-strain sector (own solver).

For every variant of ``gearcore.fillet`` the parameters of its source are swept, the sector
(three teeth, the counts of the computed series, bore 16,5 mm) is meshed with the variant, the
wheel load case of the convergence study is applied (Hertz patch at point B of the wheel, 16 Nm,
the isotropic row of the QS card at 80 °C) and the largest tensile principal stress along the
loaded fillet, the largest von Mises stress there, the tip displacement and the strain energy are
recorded beside the geometry of the variant (transition and root diameter, smallest radius of
curvature, smallest distance of the pinion tip corners). The trochoid of the generation is the
reference. The optimum of a kind is the smallest fillet σ1 among the variants whose distance to
the pinion tip corners stays above ``--min-clearance``.

Output: ``sweep.csv``, ``bericht.md``, the figures ``sigma1_ellipse``, ``sigma1_bezier``,
``sigma1_bionic`` (house style, captions in ``bildunterschriften.md``).
"""

from __future__ import annotations

import argparse
import csv
import dataclasses
import json
import sys
import time
from pathlib import Path
from typing import Any

import numpy as np

from gearcore import contour as ct
from gearcore import fillet as fl
from gearcore.errors import GeometryInfeasibleError, InputRangeError, NotSupportedError
from gearcore.fe import convergence as cv
from gearcore.fe import plane_solver as ps
from gearcore.fe import resample as rs
from gearcore.fe import sector_mesh as sm
from gearcore.models.results import GenerationResult
from gearcore.parity import compute_generation_from_data, generation_data
from gearcore.plot_style import apply, german_number, legend_outside, new_figure, save

REPO_ROOT = Path(__file__).resolve().parents[3]
OUTPUT = REPO_ROOT / "80_output" / "fe"
SERIES = OUTPUT / "kst_e" / "series_20layers_bore33_round0p1f12_30perpitch_margin1_qs_gerechnet"

# the isotropic row of the QS card at 80 °C (wheel_mesh_QS.cof, README of the series)
E_MPA = 2282.08
NU = 0.2997
TORQUE_NMM = 16000.0
FACE_WIDTH_MM = 15.0
FORMULATION = "incompatible_modes"

ELLIPSE_GAMMA_DEG = (15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0)
ELLIPSE_AXIS_RATIO = (1.5, 2.0, 2.5, 3.0, 3.5, 4.0)
BEZIER_FACTOR = (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0)
BIONIC_ANGLE_DEG: tuple[float | None, ...] = (None, 15.0, 20.0, 25.0, 30.0, 35.0)
BIONIC_RADIUS_FACTOR = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6)

COLUMNS = (
    "kind",
    "label",
    "param_1",
    "param_2",
    "status",
    "sigma1_fillet_mpa",
    "mises_fillet_mpa",
    "tip_displacement_mm",
    "strain_energy_nmm",
    "transition_d_mm",
    "root_d_mm",
    "min_curvature_radius_mm",
    "tip_corner_distance_mm",
    "corner_sine_min",
    "nodes",
    "seconds",
)


def _counts_of_series(manifest: Path) -> rs.MeshCounts:
    """The transverse counts of the computed series (fallback: the series' generator call)."""
    names = {f.name for f in dataclasses.fields(rs.MeshCounts)}
    given: dict[str, int] = {}
    if manifest.is_file():
        data = json.loads(manifest.read_text(encoding="utf-8"))
        counts = data.get("wheel_mesh", {}).get("counts", {})
        given = {k: int(v) for k, v in counts.items() if k in names}
    if not given:
        given = {
            "over_tooth_height": 18,
            "at_tip_edge_break": 1,
            "at_tooth_root": 60,
            "over_tooth_thickness": 14,
            "rim_rings": 5,
            "root_layers": 4,
            "shoulder_columns": 2,
        }
        given = {k: v for k, v in given.items() if k in names}
    return rs.MeshCounts(**given)


def _solve(
    generation: GenerationResult, counts: rs.MeshCounts, variant: fl.FilletVariant | None
) -> tuple[sm.SectorMesh, cv.Evaluation, float]:
    section = sm.sector_mesh(
        generation,
        "wheel",
        teeth=3,
        rim_rings=5,
        bore_radius_mm=16.5,
        counts=counts,
        fillet=variant,
    )
    load = cv.wheel_load_case(
        generation,
        section,
        torque_wheel_nmm=TORQUE_NMM,
        youngs_modulus_mpa=E_MPA,
        poisson_ratio=NU,
        face_width_mm=FACE_WIDTH_MM,
    )
    solution = ps.solve(
        section.points_mm,
        section.quads,
        d_matrix=ps.plane_strain_matrix(E_MPA, NU),
        fixed=cv.fixed_nodes(section),
        loads_n_per_mm=load.loads_n_per_mm,
        formulation=FORMULATION,
    )
    quality = float(sm.scaled_jacobians(section.points_mm, section.quads).min())
    return section, cv.evaluate(section, solution, load, NU), quality


def _row(kind: str, label: str, p1: float | None, p2: float | None) -> dict[str, Any]:
    return dict.fromkeys(COLUMNS, "") | {
        "kind": kind,
        "label": label,
        "param_1": "" if p1 is None else p1,
        "param_2": "" if p2 is None else p2,
    }


def _evaluate_variant(
    generation: GenerationResult,
    counts: rs.MeshCounts,
    kind: str,
    variant: fl.FilletVariant | None,
    p1: float | None,
    p2: float | None,
) -> dict[str, Any]:
    label = "trochoid" if variant is None else variant.label()
    row = _row(kind, label, p1, p2)
    start = time.perf_counter()
    try:
        if variant is None:
            contour = ct.tooth_contour(generation, "wheel")
            geometry: dict[str, float] = {
                "transition_d_mm": contour.root_form_diameter_mm,
                "root_d_mm": contour.generated_root_diameter_mm,
                "min_curvature_radius_mm": fl.polyline_min_curvature_radius(
                    contour.segment("left_fillet")
                ),
            }
        else:
            built = fl.apply(generation, "wheel", variant)
            contour = built.contour
            geometry = {
                "transition_d_mm": built.transition_diameter_mm,
                "root_d_mm": built.root_diameter_mm,
                "min_curvature_radius_mm": built.min_curvature_radius_mm,
            }
        distance, _ = fl.mating_tip_clearance(generation, contour, samples=120)
        row.update(geometry)
        row["tip_corner_distance_mm"] = distance
        section, result, quality = _solve(generation, counts, variant)
    except (GeometryInfeasibleError, InputRangeError, NotSupportedError) as error:
        row["status"] = f"nicht baubar: {error}"
        row["seconds"] = time.perf_counter() - start
        return row
    row.update(
        {
            "status": "ok",
            "sigma1_fillet_mpa": result.root_sigma1_max_mpa,
            "mises_fillet_mpa": result.root_von_mises_max_mpa,
            "tip_displacement_mm": result.tip_centre_magnitude_mm,
            "strain_energy_nmm": result.strain_energy_nmm,
            "corner_sine_min": quality,
            "nodes": len(section.points_mm),
            "seconds": time.perf_counter() - start,
        }
    )
    return row


def _variants() -> list[tuple[str, fl.FilletVariant | None, float | None, float | None]]:
    items: list[tuple[str, fl.FilletVariant | None, float | None, float | None]] = [
        ("trochoid", None, None, None)
    ]
    for gamma in ELLIPSE_GAMMA_DEG:
        for ratio in ELLIPSE_AXIS_RATIO:
            items.append(
                (
                    "ellipse",
                    fl.FilletVariant(kind="ellipse", inclination_deg=gamma, axis_ratio=ratio),
                    gamma,
                    ratio,
                )
            )
    for f in BEZIER_FACTOR:
        items.append(("bezier", fl.FilletVariant(kind="bezier", control_factor=f), f, None))
    for phi in BIONIC_ANGLE_DEG:
        for r in BIONIC_RADIUS_FACTOR:
            items.append(
                (
                    "bionic",
                    fl.FilletVariant(kind="bionic", root_angle_deg=phi, root_radius_factor=r),
                    phi,
                    r,
                )
            )
    return items


def _optimum(rows: list[dict[str, Any]], kind: str, min_clearance: float) -> dict[str, Any] | None:
    ok = [
        r
        for r in rows
        if r["kind"] == kind
        and r["status"] == "ok"
        and r["tip_corner_distance_mm"] >= min_clearance
    ]
    return min(ok, key=lambda r: r["sigma1_fillet_mpa"]) if ok else None


def _figures(rows: list[dict[str, Any]], reference: dict[str, Any], out: Path) -> list[str]:
    apply()
    captions: list[str] = []
    ref = float(reference["sigma1_fillet_mpa"])

    def axes_of(figure_axes: tuple[Any, Any]) -> tuple[Any, Any]:
        figure, axes = figure_axes
        ax = axes.flat[0] if isinstance(axes, np.ndarray) else axes
        return figure, ax

    # ellipse: sigma1 over gamma, one line per axis ratio
    figure, ax = axes_of(new_figure("full", 0.62))
    for ratio in ELLIPSE_AXIS_RATIO:
        pts = [
            (r["param_1"], r["sigma1_fillet_mpa"])
            for r in rows
            if r["kind"] == "ellipse" and r["status"] == "ok" and r["param_2"] == ratio
        ]
        if pts:
            ax.plot(
                [p[0] for p in pts], [p[1] for p in pts], label=f"$a/b$ = {german_number(ratio, 1)}"
            )
    ax.axhline(ref, color="black", linestyle=":", label="Trochoide der Erzeugung")
    ax.set_xlabel("Neigung $\\gamma$ in °")
    ax.set_ylabel("$\\sigma_1$ in MPa")
    legend_outside(figure, ax, where="bottom", ncol=4)
    save(figure, out / "sigma1_ellipse")
    captions.append(
        "**sigma1_ellipse**: Größte Zugspannung $\\sigma_1$ in der belasteten Fußrundung des "
        "ebenen Sektormodells (W1, 16 Nm am Rad, Hertzscher Lastfleck an B) über der Neigung "
        "$\\gamma$ der Zahnfußellipse nach Frühe für die Hauptachsenverhältnisse $a/b$; gepunktet "
        "die Trochoide der Erzeugung. Eigene Berechnung in Anlehnung an [Frü12], Abschnitt 5.4.2."
    )
    # bezier: sigma1 over f
    figure, ax = axes_of(new_figure("half", 0.75))
    pts = [
        (r["param_1"], r["sigma1_fillet_mpa"])
        for r in rows
        if r["kind"] == "bezier" and r["status"] == "ok"
    ]
    ax.plot([p[0] for p in pts], [p[1] for p in pts], label="Bézier-Kontur")
    ax.axhline(ref, color="black", linestyle=":", label="Trochoide der Erzeugung")
    ax.set_xlabel("Faktor $f$ der Kontrollpunkte")
    ax.set_ylabel("$\\sigma_1$ in MPa")
    legend_outside(figure, ax, where="bottom", ncol=2)
    save(figure, out / "sigma1_bezier")
    captions.append(
        "**sigma1_bezier**: $\\sigma_1$ der belasteten Fußrundung über dem Faktor $f$ des "
        "Kontrollpunktabstands $k = (0{,}25 + 0{,}1 f)\\,l$ der Bézier-Kontur nach "
        "DE 10 2013 004 861 B3, Anspruch 8; gepunktet die Trochoide."
    )
    # bionic: sigma1 over phi, one line per radius factor
    figure, ax = axes_of(new_figure("full", 0.62))
    for r_factor in BIONIC_RADIUS_FACTOR:
        pts = [
            (r["param_1"], r["sigma1_fillet_mpa"])
            for r in rows
            if r["kind"] == "bionic"
            and r["status"] == "ok"
            and r["param_2"] == r_factor
            and r["param_1"] != ""
        ]
        if pts:
            pts.sort()
            ax.plot(
                [p[0] for p in pts],
                [p[1] for p in pts],
                label=f"$r$ = {german_number(r_factor, 1)} $S_\\mathrm{{L}}$",
            )
    ax.axhline(ref, color="black", linestyle=":", label="Trochoide der Erzeugung")
    ax.set_xlabel("Winkel $\\varphi$ in der Lückenmitte in °")
    ax.set_ylabel("$\\sigma_1$ in MPa")
    legend_outside(figure, ax, where="bottom", ncol=4)
    save(figure, out / "sigma1_bionic")
    captions.append(
        "**sigma1_bionic**: $\\sigma_1$ der belasteten Fußrundung über dem Winkel $\\varphi$ der "
        "Tangensfunktion in der Lückenmitte für die Kreisradien $r$ als Anteil der Lückenweite "
        "$S_\\mathrm{L}$ am relevanten Durchmesser, bionische Kontur nach DE 10 2008 045 318 B3; "
        "gepunktet die Trochoide. Der Wert nach Anspruch 5 (24,1°) steht in der Tabelle."
    )
    return captions


def _report(
    rows: list[dict[str, Any]],
    reference: dict[str, Any],
    counts: rs.MeshCounts,
    min_clearance: float,
    current: dict[str, fl.FilletVariant],
) -> list[str]:
    def fmt(value: Any, digits: int = 2) -> str:
        return german_number(float(value), digits) if value != "" else "–"

    lines = [
        "# Parameterstudie der Fußrundungsvarianten (ebenes Sektormodell, eigener Löser)",
        "",
        f"Sektor 3 Zähne, Bohrungsradius 16,5 mm (Ø 33 mm), Zählung der Serie ({counts.label()}), Formulierung "
        f"{FORMULATION} (Gegenstück von C3D8I), E = {german_number(E_MPA, 1)} MPa, ν = "
        f"{german_number(NU, 4)} (isotrope Zeile der QS-Karte bei 80 °C), {german_number(TORQUE_NMM / 1000, 0)} Nm "
        f"am Rad, Zahnbreite {german_number(FACE_WIDTH_MM, 0)} mm, Hertzscher Lastfleck an B des Rades. "
        f"Zielgröße: größte Zugspannung σ1 entlang der belasteten Fußrundung; Nebenbedingung: "
        f"kleinster Abstand der Ritzelkopfkanten zur Fußrundung ≥ {german_number(min_clearance, 2)} mm.",
        "",
        f"Referenz Trochoide: σ1 {fmt(reference['sigma1_fillet_mpa'])} MPa, von Mises "
        f"{fmt(reference['mises_fillet_mpa'])} MPa, Kopfverschiebung {fmt(reference['tip_displacement_mm'], 4)} mm, "
        f"Abstand der Kopfkanten {fmt(reference['tip_corner_distance_mm'], 3)} mm.",
        "",
        "## Stand in der Kette gegen das Optimum des Sweeps",
        "",
        "| Art | Stand (Literaturwerte) | σ1 | Δ gegen Trochoide | "
        "Optimum des Sweeps | σ1 | Δ gegen Trochoide | Abstand Kopfkante |",
        "|---|---|---|---|---|---|---|---|",
    ]
    ref = float(reference["sigma1_fillet_mpa"])
    by_label = {r["label"]: r for r in rows}
    for kind in ("ellipse", "bezier", "bionic"):
        now = by_label.get(current[kind].label())
        best = _optimum(rows, kind, min_clearance)
        now_s1 = fmt(now["sigma1_fillet_mpa"]) if now and now["status"] == "ok" else "–"
        now_d = (
            f"{german_number(100.0 * (float(now['sigma1_fillet_mpa']) / ref - 1.0), 1)} %"
            if now and now["status"] == "ok"
            else "–"
        )
        if best is None:
            lines.append(
                f"| {kind} | {current[kind].label()} | {now_s1} | {now_d} | keines | – | – | – |"
            )
            continue
        lines.append(
            f"| {kind} | {current[kind].label()} | {now_s1} | {now_d} | {best['label']} | "
            f"{fmt(best['sigma1_fillet_mpa'])} | "
            f"{german_number(100.0 * (float(best['sigma1_fillet_mpa']) / ref - 1.0), 1)} % | "
            f"{fmt(best['tip_corner_distance_mm'], 3)} mm |"
        )
    lines += [
        "",
        "## Alle Varianten",
        "",
        "| Art | Variante | σ1 in MPa | Δ | Mises in MPa | Kopfverschiebung in mm | "
        "Übergang d in mm | Fußkreis d in mm | ρ_min in mm | Abstand Kopfkante in mm | Eckensinus | Status |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        delta = (
            f"{german_number(100.0 * (float(r['sigma1_fillet_mpa']) / ref - 1.0), 1)} %"
            if r["status"] == "ok"
            else "–"
        )
        lines.append(
            f"| {r['kind']} | {r['label']} | {fmt(r['sigma1_fillet_mpa'])} | {delta} | "
            f"{fmt(r['mises_fillet_mpa'])} | {fmt(r['tip_displacement_mm'], 4)} | "
            f"{fmt(r['transition_d_mm'], 3)} | {fmt(r['root_d_mm'], 3)} | "
            f"{fmt(r['min_curvature_radius_mm'], 3)} | {fmt(r['tip_corner_distance_mm'], 3)} | "
            f"{fmt(r['corner_sine_min'], 3)} | {r['status']} |"
        )
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", default="kst_e")
    parser.add_argument("--out", type=Path, default=OUTPUT / "kst_e" / "fussrundung_sweep")
    parser.add_argument("--manifest", type=Path, default=SERIES / "manifest.json")
    parser.add_argument("--min-clearance", type=float, default=0.1)
    parser.add_argument("--no-figures", action="store_true")
    args = parser.parse_args(argv)
    data = generation_data(args.case)
    generation = compute_generation_from_data(data, data.values)
    counts = _counts_of_series(args.manifest)
    out: Path = args.out
    out.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for kind, variant, p1, p2 in _variants():
        row = _evaluate_variant(generation, counts, kind, variant, p1, p2)
        rows.append(row)
        print(
            f"{row['label']:<28} {row['status'][:12]:<12} sigma1 {row['sigma1_fillet_mpa'] or '-'} "
            f"distance {row['tip_corner_distance_mm'] or '-'}",
            flush=True,
        )
    with (out / "sweep.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
    reference = rows[0]
    current = {
        "ellipse": fl.FilletVariant(kind="ellipse"),
        "bezier": fl.FilletVariant(kind="bezier"),
        "bionic": fl.FilletVariant(kind="bionic"),
    }
    lines = _report(rows, reference, counts, args.min_clearance, current)
    (out / "bericht.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if not args.no_figures:
        captions = _figures(rows, reference, out)
        (out / "bildunterschriften.md").write_text(
            "# Bildunterschriften\n\n" + "\n\n".join(captions) + "\n", encoding="utf-8"
        )
    print("\n".join(lines[:16]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
