"""The root fillet variants of the wheel against the trochoid of the generation at the named
points A to E, on the pocket body (ADR-116 items 52 and 53; C8 of the thesis plan).

    uv run --all-extras python scripts/fe_fillet_comparison.py \\
        --baseline 80_output/fe/kst_e/pilot_20layers_bore33_pocket_round0p1f12_qsdy1dy2_AtoE_gerechnet \\
        --variant 80_output/fe/kst_e/pilot_..._pocket_fillet_ellipse_g30_ab3_..._AtoE_gerechnet \\
        --variant 80_output/fe/kst_e/pilot_..._pocket_fillet_bezier_f1_..._AtoE_gerechnet \\
        --sweep 80_output/fe/kst_e/fussrundung_sweep/bericht.md \\
        --out 80_output/fe/kst_e/vergleich_fussrundung_AtoE

A variant folder names its contour in the manifest (``wheel_mesh.fillet``); the baseline has
none. Baseline and variants must share the body, the pinion tip edge, the load steps and the
positions (by their distance from A); anything else is refused. Values are the maxima over the
tooth width as in the path report; the effect of a variant is its value against the baseline's
at the same point, load step, material step and rate. The plane-strain sweep (``bericht.md``)
gives the prediction of the own solver for W1 at 16 Nm at B, against which the 3D result is
checked. A label the legend table does not know is printed as the manifest names it.
"""

from __future__ import annotations

import argparse
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import fe_series_analysis as fsa  # noqa: E402

from gearcore.errors import InputRangeError  # noqa: E402
from gearcore.fe import evaluation as ev  # noqa: E402
from gearcore.plot_style import decimal_comma, legend_outside, new_figure  # noqa: E402
from gearcore.plot_style import save as save_figure  # noqa: E402

POINTS = ("A", "B", "C", "D", "E")
MATERIALS = ("W1", "W2", "W3", "W4")
RATE_ORDER = {"QS": 0, "DY1": 1, "DY2": 2}
BASELINE_LABEL = "trochoid"
VARIANT_NAMES: dict[str, str] = {
    BASELINE_LABEL: "Trochoide der Erzeugung (Grundlinie)",
    "ellipse_g30_ab3": "Ellipse nach Frühe, $\\gamma$ 30°, $a/b$ 3,0",
    "ellipse_g25_ab2": "Ellipse, $\\gamma$ 25°, $a/b$ 2,0 (Optimum der ebenen Studie)",
    "bezier_f1": "Bézier nach Patent, $f$ 1,0",
    "bezier_f2.5": "Bézier, $f$ 2,5 (Optimum der ebenen Studie)",
    "bionic_phiauto_r0.3": (
        "bionisch nach Patent, $\\varphi$ nach Anspruch 5, $r$ 0,3 $S_\\mathrm{L}$"
    ),
    "bionic_phi35_r0.2": (
        "bionisch, $\\varphi$ 35°, $r$ 0,2 $S_\\mathrm{L}$ (Optimum der ebenen Studie)"
    ),
}
"""Legend words of the variants (the folder label is the key), symbols in mathtext so that
they are italic and the Greek letters have a glyph; markdown gets ``plain_name``."""
PLAIN_SYMBOLS = (
    ("$\\gamma$", "γ"),
    ("$\\varphi$", "φ"),
    ("$S_\\mathrm{L}$", "S_L"),
    ("$a/b$", "a/b"),
    ("$f$", "f"),
    ("$r$", "r"),
)
VARIANT_SHORT: dict[str, str] = {
    "ellipse_g30_ab3": "Ellipse\n30°, 3,0",
    "ellipse_g25_ab2": "Ellipse\n25°, 2,0",
    "bezier_f1": "Bézier\nf 1,0",
    "bezier_f2.5": "Bézier\nf 2,5",
    "bionic_phiauto_r0.3": "bionisch\nPatent, 0,3",
    "bionic_phi35_r0.2": "bionisch\n35°, 0,2",
}
"""Tick labels of the overview figure."""
QUANTITIES = fsa.GLOBAL_QUANTITIES
SHORT_LABELS = {
    "pinion_rotation_rad": "Drehung",
    "u_head_max": "Kopfverschiebung",
    "p_max": "Kontaktdruck",
    "s1_max": r"$\sigma_{\mathrm{1}}$ max",
    "s3_min": r"|$\sigma_{\mathrm{3}}$| max",
}
FIGURE_QUANTITIES = (("s1_max", "sigma1"), ("pinion_rotation_rad", "drehung"))
"""The quantities drawn per load step and rate (file key after the quantity)."""
SWEEP_ROW = re.compile(r"^\|\s*(\w+)\s*\|\s*([\w.]+)\s*\|(.*)\|\s*$")
SHARED_KEYS = (
    "material_steps",
    "nlgeom_of_step",
    "contact",
    "enforcement",
    "iteration_limits",
    "line_search",
    "torques_wheel_nm",
)
"""Manifest keys a variant folder must share with the baseline (solver settings, rates, loads)."""
SHARED_MESH_KEYS = ("layers", "element_type_of_step", "bore_radius_mm", "counts", "levels", "teeth")
"""Keys of ``wheel_mesh`` that pin the template; the node count differs with the contour."""


def variant_name(label: str) -> str:
    """The legend words of a variant; an unknown label is printed as it stands."""
    return VARIANT_NAMES.get(label, label)


def plain_name(label: str) -> str:
    """``variant_name`` without the mathtext of the legend, for the markdown tables."""
    text = variant_name(label)
    for math, plain in PLAIN_SYMBOLS:
        text = text.replace(math, plain)
    return text


def short_name(label: str) -> str:
    return VARIANT_SHORT.get(label, label).replace("\n", " ")


# --- the folders -----------------------------------------------------------------------------------


@dataclass(frozen=True)
class Folder:
    path: Path
    manifest: dict[str, Any]
    series: dict[str, list[ev.PathPoint]]
    fillet: dict[str, Any] | None

    @property
    def label(self) -> str:
        return str(self.fillet["label"]) if self.fillet else BASELINE_LABEL


def load_folder(path: Path) -> Folder:
    if not (path / "manifest.json").is_file():
        raise InputRangeError(f"no manifest.json in {path}")
    manifest, series = fsa._load(path)
    if not any(series.values()):
        raise InputRangeError(f"{path.name}: no extracted fields")
    fillet = manifest.get("wheel_mesh", {}).get("fillet")
    if fillet is not None and not isinstance(fillet, dict):
        raise InputRangeError(f"{path.name}: wheel_mesh.fillet is not a mapping")
    if fillet is not None and not fillet.get("label"):
        raise InputRangeError(f"{path.name}: wheel_mesh.fillet without a label")
    return Folder(path, manifest, series, fillet)


def body_shape(manifest: Mapping[str, Any]) -> str:
    body = manifest.get("wheel_mesh", {}).get("body", "ring")
    return str(body.get("shape", "ring")) if isinstance(body, dict) else str(body)


def tip_edge(manifest: Mapping[str, Any]) -> float | None:
    edge = manifest.get("pinion_surface", {}).get("tip_rounding_mm")
    return float(edge) if isinstance(edge, int | float) else None


def positions_of(manifest: Mapping[str, Any]) -> tuple[tuple[str, float], ...]:
    """(point label, distance from A) of every distinct position, rounded to the nanometre."""
    out = {
        (str(entry.get("point") or ""), round(float(entry["from_A_mm"]), 6))
        for entry in manifest.get("positions", [])
    }
    return tuple(sorted(out, key=lambda item: item[1]))


def rates_without_files(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """The rate cards of the manifest without their file paths (name, temperature, modulus,
    Poisson's ratio, test speed, strain rate, orientation pieces)."""
    rates = manifest.get("rates")
    if not isinstance(rates, dict):
        return {}
    return {
        str(rate): {k: v for k, v in card.items() if k != "file"}
        if isinstance(card, dict)
        else card
        for rate, card in rates.items()
    }


def check_compatible(baseline: Folder, variant: Folder) -> None:
    """Refuse folders that differ in anything but the root fillet."""
    if baseline.fillet is not None:
        raise InputRangeError(
            f"{baseline.path.name}: the baseline carries the fillet variant "
            f"{baseline.label!r}; the baseline is the trochoid of the generation"
        )
    if variant.fillet is None:
        raise InputRangeError(f"{variant.path.name}: no wheel_mesh.fillet in the manifest")
    b, v = baseline.manifest, variant.manifest
    if body_shape(b) != body_shape(v):
        raise InputRangeError(
            f"{variant.path.name}: body {body_shape(v)!r} against the baseline's {body_shape(b)!r}"
        )
    if tip_edge(b) != tip_edge(v):
        raise InputRangeError(
            f"{variant.path.name}: pinion tip edge {tip_edge(v)!r} against the baseline's "
            f"{tip_edge(b)!r}"
        )
    if list(b.get("step_names", [])) != list(v.get("step_names", [])):
        raise InputRangeError(f"{variant.path.name}: other load steps than the baseline")
    if positions_of(b) != positions_of(v):
        raise InputRangeError(f"{variant.path.name}: other positions than the baseline")
    # the same template, solver settings and rates; the orientation files and the material
    # card differ by design (the user's mapping on each variant mesh), so the rates are
    # compared without their file names
    if rates_without_files(b) != rates_without_files(v):
        raise InputRangeError(
            f"{variant.path.name}: the rates (material data, speeds) differ from the baseline's"
        )
    for key in SHARED_KEYS:
        if b.get(key) != v.get(key):
            raise InputRangeError(
                f"{variant.path.name}: {key} {v.get(key)!r} against the baseline's {b.get(key)!r}"
            )
    for key in SHARED_MESH_KEYS:
        if mesh_setting(b, key) != mesh_setting(v, key):
            raise InputRangeError(
                f"{variant.path.name}: wheel_mesh.{key} differs from the baseline's"
            )


def mesh_setting(manifest: Mapping[str, Any], key: str) -> Any:
    """A template setting of ``wheel_mesh``; a manifest written before the layer division
    became an option (2026-10-12) carries no ``levels`` key and means the generator's default
    ``equal``."""
    value = manifest.get("wheel_mesh", {}).get(key)
    if key == "levels" and value is None:
        return "equal"
    return value


# --- the effect ------------------------------------------------------------------------------------


def effect(
    baseline: Folder, variant: Folder, series: str, step: str, quantity: str
) -> dict[str, float]:
    """point label -> value of the variant against the baseline's (b / a − 1)."""
    base_points = baseline.series.get(series)
    var_points = variant.series.get(series)
    if not base_points or not var_points:
        return {}
    base_at = fsa.values_at_points(base_points, step, quantity)
    var_at = fsa.values_at_points(var_points, step, quantity)
    out: dict[str, float] = {}
    for point in POINTS:
        rel = fsa.relative(base_at.get(point), var_at.get(point))
        if rel is not None:
            out[point] = rel
    return out


def s1_location(
    points: Sequence[ev.PathPoint], step: str, point: str
) -> tuple[str, float, float, float] | None:
    """(fillet, σ1, r, z) of the largest tensile stress at the named point, complete steps only."""
    for item in points:
        if item.label != point:
            continue
        summary = item.summaries.get(step)
        if summary is None or not summary.complete or summary.s1_max_fillet is None:
            return None
        fillet = summary.s1_max_fillet
        return fillet.name, fillet.s1_max, fillet.s1_layer.r_s1, fillet.s1_layer.z
    return None


def peak_point(baseline: Folder, series: str, step: str, quantity: str = "s1_max") -> str:
    """The named point where the baseline's quantity is largest (the point of the comparison)."""
    points = baseline.series.get(series)
    if not points:
        raise InputRangeError(f"the baseline has no series {series}")
    at = fsa.values_at_points(points, step, quantity)
    if not at:
        raise InputRangeError(f"the baseline has no complete {step} in {series}")
    return max(at, key=lambda k: at[k])


def series_sorted(names: Sequence[str]) -> list[str]:
    return sorted(set(names), key=lambda n: (RATE_ORDER.get(fsa.rate_of(n), 9), fsa.step_of(n)))


# --- the plane-strain sweep --------------------------------------------------------------------------


@dataclass(frozen=True)
class SweepRow:
    kind: str
    label: str
    s1_mpa: float
    delta: float
    transition_mm: float
    root_mm: float
    rho_min_mm: float
    clearance_mm: float


def _number(text: str) -> float:
    cleaned = text.strip().replace("−", "-").replace("%", "").replace(",", ".").strip()
    return float(cleaned)


def read_sweep(path: Path) -> dict[str, SweepRow]:
    """The rows of the sweep report's variant table (``bericht.md``) by label: σ1 of the plane
    model, its change against the trochoid, and the contour numbers. Rows that were not
    constructible are left out."""
    rows: dict[str, SweepRow] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        match = SWEEP_ROW.match(raw)
        if match is None:
            continue
        kind, label, rest = match.groups()
        cells = [c.strip() for c in rest.split("|")]
        # σ1 | Δ | Mises | head | transition | root | rho | clearance | corner sine | status
        if len(cells) != 10 or cells[-1] != "ok":
            continue  # the summary table (8 cells) and the rows that were not constructible
        try:
            rows[label] = SweepRow(
                kind=kind,
                label=label,
                s1_mpa=_number(cells[0]),
                delta=_number(cells[1]) / 100.0,
                transition_mm=_number(cells[4]),
                root_mm=_number(cells[5]),
                rho_min_mm=_number(cells[6]),
                clearance_mm=_number(cells[7]),
            )
        except ValueError as error:
            raise InputRangeError(f"{path}: row {label!r} of the sweep report: {error}") from error
    if not rows:
        raise InputRangeError(f"{path}: no variant rows of the sweep report")
    return rows


# --- figures ---------------------------------------------------------------------------------------


def figure_effect(
    baseline: Folder,
    variants: Sequence[Folder],
    rate: str,
    step: str,
    quantity: str,
    stem: Path,
) -> list[Path]:
    """The effect in percent at A to E, one panel per material step, the variants as markers
    without a line (the course between the points is not computed)."""
    figure, axes = new_figure("full", 0.95, rows=len(MATERIALS), sharex=True)
    x = np.arange(len(POINTS))
    for ax, material in zip(axes, MATERIALS, strict=True):
        series = f"{material}_{rate}"
        for variant in variants:
            rel = effect(baseline, variant, series, step, quantity)
            # a variant without this series plots nothing but keeps its colour and marker
            ax.plot(
                x,
                [rel[k] * 100.0 if k in rel else np.nan for k in POINTS],
                linestyle="none",
                label=variant_name(variant.label),
            )
        ax.axhline(0.0, color="0.5", linewidth=0.5)
        ax.set_ylabel(f"{material}: Δ{SHORT_LABELS[quantity]} in %")
        decimal_comma(ax, which="y")
    axes[-1].set_xticks(x, POINTS)
    axes[-1].set_xlabel("Normpunkt")
    legend_outside(figure, axes[0], where="bottom", ncol=2)
    return save_figure(figure, stem)


def figure_overview(
    baseline: Folder,
    variants: Sequence[Folder],
    rate: str,
    step: str,
    point: str,
    stem: Path,
    sweep: Mapping[str, SweepRow] | None = None,
) -> list[Path]:
    """Δσ1 at one point for every variant (x) and material step (markers); the plane-strain
    prediction as its own marker row when the sweep is given."""
    figure, ax = new_figure("full", 0.55)
    x = np.arange(len(variants))
    for material in MATERIALS:
        series = f"{material}_{rate}"
        values = [effect(baseline, v, series, step, "s1_max").get(point, np.nan) for v in variants]
        # a material step without values plots nothing but keeps its colour and marker
        ax.plot(
            x,
            [v * 100.0 for v in values],
            linestyle="none",
            label=fsa.SERIES_LABELS.get(material, material),
        )
    if sweep is not None:
        values = [sweep[v.label].delta * 100.0 if v.label in sweep else np.nan for v in variants]
        if not all(np.isnan(values)):
            ax.plot(x, values, linestyle="none", label="ebenes Sektormodell, W1, 16 Nm an B")
    ax.axhline(0.0, color="0.5", linewidth=0.5)
    ax.set_xticks(x, [VARIANT_SHORT.get(v.label, v.label) for v in variants])
    ax.set_ylabel(r"$\Delta\sigma_{\mathrm{1}}$ max in %")
    decimal_comma(ax, which="y")
    legend_outside(figure, ax, where="bottom", ncol=2)
    return save_figure(figure, stem)


def figure_rates(
    baseline: Folder,
    variants: Sequence[Folder],
    rates: Sequence[str],
    step: str,
    point: str,
    stem: Path,
) -> list[Path]:
    """Δσ1 at one point for every variant (x), one panel per material step, the three rate cards
    as markers (user 2026-10-20: the overview over the material steps doubles the effect figure,
    the rates were missing)."""
    figure, axes = new_figure("full", 0.95, rows=len(MATERIALS), sharex=True)
    x = np.arange(len(variants))
    for ax, material in zip(axes, MATERIALS, strict=True):
        for rate in rates:
            series = f"{material}_{rate}"
            values = [effect(baseline, v, series, step, "s1_max").get(point, np.nan) for v in variants]
            ax.plot(
                x,
                [v * 100.0 for v in values],
                linestyle="none",
                label=fsa.RATE_LABELS.get(rate, rate),
            )
        ax.axhline(0.0, color="0.5", linewidth=0.5)
        ax.set_ylabel(rf"{material}: $\Delta\sigma_{{\mathrm{{1}}}}$ in %")
        decimal_comma(ax, which="y")
    axes[-1].set_xticks(x, [VARIANT_SHORT.get(v.label, v.label) for v in variants])
    legend_outside(figure, axes[0], where="bottom", ncol=3)
    return save_figure(figure, stem)


def caption_rates(step: str, point: str) -> str:
    return (
        f"Änderung der größten Zugspannung σ1 der Fußrundung gegen die Trochoide am Normpunkt "
        f"{point} je Variante, Werkstoffstufe (W1 bis W4 von oben nach unten) und Dehnratenkarte, "
        f"Taschenkörper, {fsa.STEP_LABELS.get(step, step)}; Marker ohne Linie."
    )


def caption_effect(rate: str, step: str, quantity: str) -> str:
    label = next(lbl for q, lbl, _u, _s in QUANTITIES if q == quantity)
    return (
        f"{label}: Fußrundungsvarianten gegen die Trochoide der Erzeugung an den Normpunkten A "
        "bis E, relative Änderung je Werkstoffstufe (W1 bis W4 von oben nach unten), "
        f"Taschenkörper, {fsa.STEP_LABELS.get(step, step)}, {fsa.RATE_LABELS.get(rate, rate)}; "
        "Größtwerte über die Zahnbreite, Marker ohne Linie, weil der Verlauf zwischen den "
        "Punkten nicht gerechnet ist."
    )


def caption_overview(rate: str, step: str, point: str, with_sweep: bool) -> str:
    text = (
        f"Änderung der größten Zugspannung σ1 der Fußrundung gegen die Trochoide am Normpunkt "
        f"{point} je Variante und Werkstoffstufe, Taschenkörper, {fsa.STEP_LABELS.get(step, step)}, "
        f"{fsa.RATE_LABELS.get(rate, rate)}"
    )
    if with_sweep:
        text += (
            "; zum Vergleich die Vorhersage des ebenen Sektormodells (eigener Löser, W1, 16 Nm, "
            "Lastfleck an B)"
        )
    return text + "."


# --- the analysis ----------------------------------------------------------------------------------


def _geometry_table(
    baseline: Folder, variants: Sequence[Folder], sweep: Mapping[str, SweepRow] | None
) -> list[str]:
    rows: list[list[str]] = []
    if sweep is not None and BASELINE_LABEL in sweep:
        t = sweep[BASELINE_LABEL]
        rows.append(
            [
                plain_name(BASELINE_LABEL),
                baseline.path.name,
                fsa._g(t.transition_mm, 3),
                fsa._g(t.root_mm, 3),
                fsa._g(t.rho_min_mm, 3),
                fsa._g(t.clearance_mm, 3),
            ]
        )
    else:
        rows.append([plain_name(BASELINE_LABEL), baseline.path.name, "–", "–", "–", "–"])
    for variant in variants:
        f = variant.fillet or {}
        numbers = []
        for key in (
            "transition_diameter_mm",
            "root_diameter_mm",
            "min_curvature_radius_mm",
            "clearance_mm",
        ):
            value = f.get(key)
            if not isinstance(value, int | float):
                raise InputRangeError(
                    f"{variant.path.name}: wheel_mesh.fillet.{key} missing in the manifest"
                )
            numbers.append(fsa._g(float(value), 3))
        rows.append([plain_name(variant.label), variant.path.name, *numbers])
    return fsa._table(
        [
            "Kontur",
            "Ordner",
            "Übergang d in mm",
            "Fußkreis d in mm",
            "ρ_min in mm",
            "Abstand Ritzelkopfkante in mm",
        ],
        rows,
    )


def _run_tables(folders: Sequence[Folder]) -> list[str]:
    doc: list[str] = []
    rows: list[list[str]] = []
    means: dict[str, dict[str, str]] = {}
    for folder in folders:
        series_of_job = {
            str(e["file"]).removesuffix(".inp"): ev.series_of(e, folder.manifest)
            for e in folder.manifest["positions"]
        }
        runs = fsa.read_run_log(folder.path, series_of_job)
        if not runs:
            rows.append([plain_name(folder.label), "–", "–", "–", "–", "–"])
            continue
        walls = [r.wall_s for r in runs if r.wall_s is not None and r.completed]
        starts = [r.started for r in runs if r.started]
        rows.append(
            [
                plain_name(folder.label),
                str(len(runs)),
                str(sum(1 for r in runs if r.completed)),
                min(starts).replace("T", " ") if starts else "–",
                max(r.ended for r in runs).replace("T", " "),
                fsa._g(sum(walls) / 3600.0, 1) if walls else "–",
            ]
        )
        means[folder.label] = {}
        for material in MATERIALS:
            own = [
                r.wall_s
                for r in runs
                if r.completed and r.wall_s is not None and fsa.step_of(r.series) == material
            ]
            means[folder.label][material] = fsa._g(sum(own) / len(own) / 60.0, 1) if own else "–"
    doc.extend(
        fsa._table(
            ["Kontur", "Jobs", "vollständig", "erster Start", "letztes Ende", "Wand in h"], rows
        )
    )
    doc.append("")
    doc.append("Mittlere Wandzeit je Job in Minuten, je Werkstoffstufe über die drei Raten:")
    doc.append("")
    doc.extend(
        fsa._table(
            ["Kontur", *MATERIALS],
            [[plain_name(lbl), *(means[lbl][m] for m in MATERIALS)] for lbl in means],
        )
    )
    return doc


def _span(values: Sequence[float]) -> str:
    return f"{fsa._pct(min(values))} bis {fsa._pct(max(values))}" if values else "–"


def analyse(
    baseline_path: Path,
    variant_paths: Sequence[Path],
    out: Path,
    sweep_path: Path | None = None,
) -> list[str]:
    baseline = load_folder(baseline_path)
    variants = [load_folder(p) for p in variant_paths]
    if not variants:
        raise InputRangeError("at least one variant folder is needed")
    for variant in variants:
        check_compatible(baseline, variant)
    labels = [v.label for v in variants]
    if len(set(labels)) != len(labels):
        raise InputRangeError(f"variant labels repeat: {labels}")
    sweep = read_sweep(sweep_path) if sweep_path is not None else None
    steps = [str(s) for s in baseline.manifest.get("step_names", []) if s != "SEAT"]
    series_names = series_sorted(list(baseline.series) + [n for v in variants for n in v.series])
    rates = sorted({fsa.rate_of(n) for n in series_names}, key=lambda r: RATE_ORDER.get(r, 9))
    if not steps:
        raise InputRangeError(f"{baseline.path.name}: the manifest names no load step")
    last_step = steps[-1]
    reference_series = f"W1_{rates[0]}"
    peak = peak_point(baseline, reference_series, last_step)
    out.mkdir(parents=True, exist_ok=True)

    doc = ["# Fußrundungsvarianten gegen die Trochoide an den Normpunkten A bis E", ""]
    doc.append(
        f"Taschenkörper, Ritzelkante r = {fsa._g(tip_edge(baseline.manifest), 2)} mm, Stellungen "
        f"A bis E, Schritte {', '.join(fsa.STEP_LABELS.get(s, s) for s in steps)}, Serien "
        f"{', '.join(series_names)}. Grundlinie ist die Trochoide der Erzeugung "
        f"(`{baseline.path.name}`); jede Variante ersetzt die Fußrundung zwischen dem "
        "Übergangsdurchmesser und der Lückenmitte, Netzvorlage, Ritzel, Lastschritte und "
        "Stellungen sind dieselben. Alle Werte sind Größtwerte über die Zahnbreite; die "
        "Änderung ist Wert der Variante gegen Wert der Grundlinie an derselben Stellung, "
        f"Stufe, Rate und Last. Der Normpunkt der größten Fußspannung der Grundlinie "
        f"({reference_series}, {fsa.STEP_LABELS.get(last_step, last_step)}) ist {peak}; "
        "die Zusammenfassung bezieht sich auf ihn."
    )
    doc.append("")
    doc.extend(["## 1 Konturen", ""])
    doc.extend(_geometry_table(baseline, variants, sweep))
    doc.append("")
    doc.extend(["## 2 Der Lauf", ""])
    doc.extend(_run_tables([baseline, *variants]))
    doc.append("")

    # 3 summary
    doc.extend(["## 3 Zusammenfassung", ""])
    doc.extend(
        [
            f"### 3.1 Änderungen am Normpunkt {peak}, {fsa.STEP_LABELS.get(last_step, last_step)}, "
            f"{fsa.RATE_LABELS.get(rates[0], rates[0])}",
            "",
        ]
    )
    rows: list[list[str]] = []
    for variant in variants:
        for material in MATERIALS:
            series = f"{material}_{rates[0]}"
            s1 = effect(baseline, variant, series, last_step, "s1_max")
            s3 = effect(baseline, variant, series, last_step, "s3_min")
            rot = effect(baseline, variant, series, last_step, "pinion_rotation_rad")
            head = effect(baseline, variant, series, last_step, "u_head_max")
            press = effect(baseline, variant, series, last_step, "p_max")
            if not s1:
                continue
            all_s1 = [
                r
                for step in steps
                for rate in rates
                for r in effect(baseline, variant, f"{material}_{rate}", step, "s1_max").values()
            ]
            rows.append(
                [
                    plain_name(variant.label),
                    material,
                    fsa._pct(s1.get(peak)),
                    _span(list(s1.values())),
                    _span(all_s1),
                    fsa._pct(s3.get(peak)),
                    fsa._pct(rot.get(peak)),
                    fsa._pct(head.get(peak)),
                    _span(list(press.values())),
                ]
            )
    doc.extend(
        fsa._table(
            [
                "Kontur",
                "Stufe",
                f"Δσ1 an {peak}",
                "Δσ1 über A bis E",
                "Δσ1 über alle Raten, Lasten, Punkte",
                f"Δ|σ3| an {peak}",
                f"ΔDrehung an {peak}",
                f"ΔKopfweg an {peak}",
                "ΔCPRESS über A bis E",
            ],
            rows,
        )
    )
    doc.append("")
    doc.extend(
        [
            f"### 3.2 Δσ1 an {peak} über die Dehnraten, {fsa.STEP_LABELS.get(last_step, last_step)}",
            "",
        ]
    )
    rows = []
    for variant in variants:
        for material in MATERIALS:
            cells = [
                fsa._pct(
                    effect(baseline, variant, f"{material}_{rate}", last_step, "s1_max").get(peak)
                )
                for rate in rates
            ]
            if all(c == "–" for c in cells):
                continue
            rows.append([plain_name(variant.label), material, *cells])
    doc.extend(fsa._table(["Kontur", "Stufe", *rates], rows))
    doc.append("")
    doc.extend(
        [
            f"### 3.3 Δσ1 an {peak} über die Lastschritte, {fsa.RATE_LABELS.get(rates[0], rates[0])}",
            "",
        ]
    )
    rows = []
    for variant in variants:
        for material in MATERIALS:
            cells = [
                fsa._pct(
                    effect(baseline, variant, f"{material}_{rates[0]}", step, "s1_max").get(peak)
                )
                for step in steps
            ]
            if all(c == "–" for c in cells):
                continue
            rows.append([plain_name(variant.label), material, *cells])
    doc.extend(fsa._table(["Kontur", "Stufe", *(fsa.STEP_LABELS.get(s, s) for s in steps)], rows))
    doc.append("")
    if sweep is not None:
        doc.extend(["### 3.4 Ebenes Sektormodell gegen das 3D-Modell (W1, 16 Nm)", ""])
        doc.append(
            "Die ebene Studie trägt das ganze Moment auf einem Zahn mit einem Lastfleck an B "
            "und ist ein relatives Maß; das 3D-Modell steht an B und am Punkt der größten "
            f"Fußspannung {peak} mit Kontakt und Lastaufteilung."
        )
        doc.append("")
        rows = []
        for variant in variants:
            series = f"W1_{rates[0]}"
            s1 = effect(baseline, variant, series, last_step, "s1_max")
            pred = sweep.get(variant.label)
            rows.append(
                [
                    plain_name(variant.label),
                    fsa._pct(pred.delta) if pred else "–",
                    fsa._pct(s1.get("B")),
                    fsa._pct(s1.get(peak)),
                ]
            )
        doc.extend(
            fsa._table(
                ["Kontur", "eben, σ1 an B", "3D, σ1 max an B", f"3D, σ1 max an {peak}"], rows
            )
        )
        doc.append("")
    doc.extend(
        [
            f"### 3.5 Ort der größten Zugspannung an {peak}, "
            f"{fsa.STEP_LABELS.get(last_step, last_step)}",
            "",
        ]
    )
    doc.append(
        "Fußrundung (Lücke zwischen den Zähnen), Radius und Breitenlage des Knotens der größten "
        "Zugspannung über alle Schichten; die Grundlinie zuerst, dann jede Variante."
    )
    doc.append("")
    rows = []
    for series in series_names:
        for folder in (baseline, *variants):
            points = folder.series.get(series)
            if not points:
                continue
            where = s1_location(points, last_step, peak)
            if where is None:
                continue
            fillet_name, s1_value, r_value, z_value = where
            rows.append(
                [
                    series,
                    plain_name(folder.label),
                    fillet_name.replace("_", "/"),
                    fsa._g(s1_value, 2),
                    fsa._g(r_value, 3),
                    fsa._g(z_value, 2),
                ]
            )
    doc.extend(
        fsa._table(["Serie", "Kontur", "Fußrundung", "σ1 in MPa", "r in mm", "z in mm"], rows)
    )
    doc.append("")
    doc.extend(
        [
            f"### 3.6 Ort der größten Zugspannung an A bis E, {reference_series}, "
            f"{fsa.STEP_LABELS.get(last_step, last_step)}",
            "",
        ]
    )
    doc.append(
        "Dieselben Angaben über die fünf Normpunkte für die erste Serie; der Fußkreisradius "
        "jeder Kontur steht in Abschnitt 1 (Fußkreis d / 2)."
    )
    doc.append("")
    rows = []
    for point in POINTS:
        for folder in (baseline, *variants):
            points = folder.series.get(reference_series)
            if not points:
                continue
            where = s1_location(points, last_step, point)
            if where is None:
                continue
            fillet_name, s1_value, r_value, z_value = where
            rows.append(
                [
                    point,
                    plain_name(folder.label),
                    fillet_name.replace("_", "/"),
                    fsa._g(s1_value, 2),
                    fsa._g(r_value, 3),
                    fsa._g(z_value, 2),
                ]
            )
    doc.extend(
        fsa._table(["Punkt", "Kontur", "Fußrundung", "σ1 in MPa", "r in mm", "z in mm"], rows)
    )
    doc.append("")

    # 4 every value
    doc.extend(["## 4 Werte je Lastschritt", ""])
    doc.append(
        "Je Größe die Grundlinie als Wert und jede Variante als relative Änderung; Serien in "
        "der Reihenfolge der Raten."
    )
    doc.append("")
    for step in steps:
        doc.extend([f"### {fsa.STEP_LABELS.get(step, step)}", ""])
        for quantity, label, unit, scale in QUANTITIES:
            rows = []
            for series in series_names:
                base_points = baseline.series.get(series)
                if not base_points:
                    continue
                base_at = fsa.values_at_points(base_points, step, quantity)
                effects = [effect(baseline, v, series, step, quantity) for v in variants]
                for point in POINTS:
                    if point not in base_at:
                        continue
                    rows.append(
                        [
                            series,
                            point,
                            fsa._g(abs(base_at[point]) * scale, 2),
                            *(fsa._pct(e.get(point)) for e in effects),
                        ]
                    )
            if not rows:
                continue
            doc.extend([f"#### {label} in {unit}", ""])
            doc.extend(
                fsa._table(
                    ["Serie", "Punkt", "Trochoide", *(short_name(v.label) for v in variants)],
                    rows,
                )
            )
            doc.append("")

    # figures
    lines: list[str] = []
    captions: list[str] = []
    for step in steps:
        for rate in rates:
            for quantity, key in FIGURE_QUANTITIES:
                stem = out / f"fusseffekt_{key}_{step}_{rate}"
                pictures = figure_effect(baseline, variants, rate, step, quantity, stem)
                lines.append(f"{stem.name}: " + ", ".join(p.name for p in pictures))
                captions.append(f"- `{stem.name}`: {caption_effect(rate, step, quantity)}")
            with_sweep = sweep is not None and step == last_step and rate == rates[0]
            stem = out / f"fusseffekt_uebersicht_{step}_{rate}"
            pictures = figure_overview(
                baseline, variants, rate, step, peak, stem, sweep if with_sweep else None
            )
            lines.append(f"{stem.name}: " + ", ".join(p.name for p in pictures))
            captions.append(f"- `{stem.name}`: {caption_overview(rate, step, peak, with_sweep)}")
    if len(rates) > 1:
        stem = out / f"fusseffekt_raten_{last_step}"
        pictures = figure_rates(baseline, variants, rates, last_step, peak, stem)
        lines.append(f"{stem.name}: " + ", ".join(p.name for p in pictures))
        captions.append(f"- `{stem.name}`: {caption_rates(last_step, peak)}")
    doc.extend(["## 5 Bilder", ""])
    doc.extend(f"- {line}" for line in lines)
    doc.append("")
    (out / "analyse.md").write_text("\n".join(doc), encoding="utf-8")
    (out / "bildunterschriften.md").write_text(
        "\n".join(["# Bildunterschriften", "", *captions, ""]), encoding="utf-8"
    )
    lines.append(str(out / "analyse.md"))
    return lines


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument(
        "--variant", type=Path, action="append", required=True, help="one variant folder each"
    )
    parser.add_argument("--sweep", type=Path, default=None, help="bericht.md of the sweep")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    for line in analyse(
        args.baseline.resolve(),
        [p.resolve() for p in args.variant],
        args.out.resolve(),
        args.sweep.resolve() if args.sweep else None,
    ):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
