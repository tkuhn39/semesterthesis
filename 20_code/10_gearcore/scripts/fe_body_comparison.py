"""The three wheel bodies at the named points A to E: ring (the weekend series at QS and the
rate pilot at DY1/DY2), ring on the z-levels of the pocket body, and the pocket body of the
drawing, every material step and rate side by side (ADR-116 item 48).

    uv run --all-extras python scripts/fe_body_comparison.py \\
        --ring-qs 80_output/fe/kst_e/series_..._qs_gerechnet \\
        --ring-rates 80_output/fe/kst_e/pilot_..._dy1dy2_AtoE_gerechnet \\
        --levels 80_output/fe/kst_e/pilot_..._pocketlevels_..._AtoE_gerechnet \\
        --pocket 80_output/fe/kst_e/pilot_..._pocket_..._AtoE_gerechnet \\
        --out 80_output/fe/kst_e/vergleich_koerper_AtoE

Positions are matched by their distance from A. Two effects are separated: the layer
division (ring on pocket levels against ring) and the body (pocket against ring on pocket
levels), the latter with the fibre orientation sampled at the same points in both. The
figures show the body effect in percent per material step (one figure per load step and
rate); the layer effect is a number in the tables.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import fe_series_analysis as fsa  # noqa: E402

from gearcore.errors import InputRangeError  # noqa: E402
from gearcore.fe import evaluation as ev  # noqa: E402
from gearcore.plot_style import decimal_comma, legend_outside, new_figure  # noqa: E402
from gearcore.plot_style import save as save_figure  # noqa: E402

REPO = Path(__file__).resolve().parents[3]
BODIES = ("ring", "levels", "pocket")
BODY_LABELS = {
    "ring": "Ringkörper (Schichten 0,75 mm)",
    "levels": "Ringkörper (Schichtung des Taschenkörpers)",
    "pocket": "Taschenkörper nach Zeichnung",
}
POINTS = ("A", "B", "C", "D", "E")
EFFECTS = {
    "layer": ("ring", "levels", "Schichtung: Ringkörper mit Taschen-Schichtung gegen Ringkörper"),
    "body": ("levels", "pocket", "Radkörper: Taschenkörper gegen Ringkörper gleicher Schichtung"),
}
SHORT_LABELS = (
    ("Drehung", "pinion_rotation_rad"),
    ("Kopfverschiebung", "u_head_max"),
    ("Kontaktdruck", "p_max"),
    (r"$\sigma_{\mathrm{1}}$ max", "s1_max"),
    (r"|$\sigma_{\mathrm{3}}$| max", "s3_min"),
)
"""Short axis labels: five stacked panels leave no room for long ones."""


def load_bodies(
    ring_qs: Path, ring_rates: Path | None, levels: Path, pocket: Path
) -> dict[str, dict[str, list[ev.PathPoint]]]:
    """body -> series name -> path points; the ring takes its QS series from the series folder
    and its DY1/DY2 series from the rate pilot."""
    out: dict[str, dict[str, list[ev.PathPoint]]] = {}
    _manifest, ring = fsa._load(ring_qs)
    out["ring"] = {name: points for name, points in ring.items() if fsa.rate_of(name) == "QS"}
    if ring_rates is not None:
        _manifest, rates = fsa._load(ring_rates)
        # the rate pilot supplies DY1/DY2 only; a QS series there never replaces the series'
        out["ring"].update({name: pts for name, pts in rates.items() if fsa.rate_of(name) != "QS"})
    _manifest, out["levels"] = fsa._load(levels)
    _manifest, out["pocket"] = fsa._load(pocket)
    if not out["levels"] or not out["pocket"]:
        raise InputRangeError("the levels and pocket folders need extracted fields")
    return out


def values(
    bodies: Mapping[str, Mapping[str, Sequence[ev.PathPoint]]],
    series: str,
    step: str,
    quantity: str,
) -> dict[str, dict[str, float]]:
    """body -> point label -> value (only bodies that carry the series)."""
    out: dict[str, dict[str, float]] = {}
    for body in BODIES:
        points = bodies[body].get(series)
        if points:
            at = fsa.values_at_points(points, step, quantity)
            if at:
                out[body] = at
    return out


def effect(
    bodies: Mapping[str, Mapping[str, Sequence[ev.PathPoint]]],
    series: str,
    step: str,
    quantity: str,
    which: str,
) -> dict[str, float]:
    """point label -> relative change of ``quantity`` between the two bodies of the effect."""
    first, second, _title = EFFECTS[which]
    per_body = values(bodies, series, step, quantity)
    if first not in per_body or second not in per_body:
        return {}
    out: dict[str, float] = {}
    for point in POINTS:
        rel = fsa.relative(per_body[first].get(point), per_body[second].get(point))
        if rel is not None:
            out[point] = rel
    return out


def figure_effect(
    bodies: Mapping[str, Mapping[str, Sequence[ev.PathPoint]]],
    series_names: Sequence[str],
    step: str,
    which: str,
    stem: Path,
) -> list[Path]:
    """The effect in percent at A to E, one panel per quantity, the material steps of one rate
    as series."""
    figure, axes = new_figure("full", 1.1, rows=len(SHORT_LABELS), sharex=True)
    x = np.arange(len(POINTS))
    for ax, (label, quantity) in zip(axes, SHORT_LABELS, strict=True):
        for series in series_names:
            rel = effect(bodies, series, step, quantity, which)
            if not rel:
                continue
            # markers only: the effect is known at the five points, not between them
            ax.plot(
                x,
                [rel[k] * 100.0 if k in rel else np.nan for k in POINTS],
                linestyle="none",
                label=fsa.SERIES_LABELS.get(fsa.step_of(series), series),
            )
        ax.axhline(0.0, color="0.5", linewidth=0.5)
        ax.set_ylabel(f"{label} in %")
        decimal_comma(ax, which="y")
    axes[-1].set_xticks(x, POINTS)
    axes[-1].set_xlabel("Normpunkt")
    legend_outside(figure, axes[0], where="bottom", ncol=2)
    return save_figure(figure, stem)


def caption_effect(series_names: Sequence[str], step: str, which: str) -> str:
    """The caption of ``figure_effect`` for ``bildunterschriften.md`` (no title in the SVG)."""
    rate = fsa.rate_text(series_names[0]) if series_names else ""
    return (
        f"{EFFECTS[which][2]} an den Normpunkten A bis E, relative Änderung je Werkstoffstufe, "
        f"{fsa.STEP_LABELS.get(step, step)}, {rate}; Größtwerte über die Zahnbreite, Marker ohne "
        "Linie, weil der Verlauf zwischen den Punkten nicht gerechnet ist."
    )


def analyse(
    ring_qs: Path, ring_rates: Path | None, levels: Path, pocket: Path, out: Path
) -> list[str]:
    bodies = load_bodies(ring_qs, ring_rates, levels, pocket)
    manifest = json.loads((pocket / "manifest.json").read_text(encoding="utf-8"))
    steps = [str(s) for s in manifest.get("step_names", []) if s != "SEAT"]
    series_names = sorted(
        {name for body in BODIES for name in bodies[body]},
        key=lambda n: (fsa.rate_of(n), fsa.step_of(n)),
    )
    out.mkdir(parents=True, exist_ok=True)
    doc = ["# Vergleich der Radkörper an den Normpunkten A bis E", ""]
    doc.append(
        "Ring (Wochenendserie QS, Ratenpilot DY1/DY2), Ring auf den z-Schichten des Taschenkörpers "
        "und Taschenkörper nach Zeichnung; Werte an den gemeinsamen Stellungen A bis E, Größtwerte "
        "über die Zahnbreite. Schichteffekt = Ring auf Taschen-Schichten gegen Ring (gleiche "
        "Geometrie, andere Abtastung der Faserorientierung); Körpereffekt = Taschenkörper gegen "
        "Ring auf Taschen-Schichten (gleiche Abtastung, andere Geometrie)."
    )
    doc.append("")
    for body in BODIES:
        names = sorted(bodies[body], key=lambda n: (fsa.rate_of(n), fsa.step_of(n)))
        doc.append(f"- {BODY_LABELS[body]}: Serien {', '.join(names) or '–'}")
    doc.append("")
    lines: list[str] = []
    captions: list[str] = []
    for step in steps:
        doc.extend([f"## {fsa.STEP_LABELS.get(step, step)}", ""])
        rows = []
        for series in series_names:
            for quantity, label, unit, scale in fsa.GLOBAL_QUANTITIES:
                per_body = values(bodies, series, step, quantity)
                if "levels" not in per_body or "pocket" not in per_body:
                    continue
                ring_at = per_body.get("ring", {})
                lev_at = per_body["levels"]
                poc_at = per_body["pocket"]
                for point in POINTS:
                    if point not in lev_at or point not in poc_at:
                        continue
                    ring_v = ring_at.get(point)
                    rows.append(
                        [
                            series,
                            f"{label} in {unit}",
                            point,
                            fsa._g(abs(ring_v) * scale, 2) if ring_v is not None else "–",
                            fsa._g(abs(lev_at[point]) * scale, 2),
                            fsa._g(abs(poc_at[point]) * scale, 2),
                            fsa._pct(fsa.relative(ring_v, lev_at[point])),
                            fsa._pct(fsa.relative(lev_at[point], poc_at[point])),
                            fsa._pct(fsa.relative(ring_v, poc_at[point])),
                        ]
                    )
        doc.extend(
            fsa._table(
                [
                    "Serie",
                    "Größe",
                    "Punkt",
                    "Ring",
                    "Ring auf Taschen-Schichten",
                    "Taschenkörper",
                    "Schichteffekt",
                    "Körpereffekt",
                    "Tasche gegen Ring",
                ],
                rows,
            )
        )
        doc.append("")
        for rate in sorted({fsa.rate_of(n) for n in series_names}):
            names = [n for n in series_names if fsa.rate_of(n) == rate]
            key = f"koerpereffekt_{step}_{rate}"
            pictures = figure_effect(bodies, names, step, "body", out / key)
            lines.append(f"{key}: " + ", ".join(p.name for p in pictures))
            captions.append(f"- `{key}`: {caption_effect(names, step, 'body')}")
    # summary of the two effects: the span per quantity and material step over rates, load
    # steps and points
    doc.extend(["## Zusammenfassung der Effekte", ""])
    doc.append(
        "Spanne der relativen Änderung je Größe und Werkstoffstufe über alle Raten, Lastschritte "
        "und Normpunkte."
    )
    doc.append("")
    rows = []
    for material in ("W1", "W2", "W3", "W4"):
        for quantity, label, _unit, _scale in fsa.GLOBAL_QUANTITIES:
            spans: dict[str, list[float]] = {"layer": [], "body": []}
            for step in steps:
                for series in series_names:
                    if fsa.step_of(series) != material:
                        continue
                    for which in spans:
                        spans[which].extend(effect(bodies, series, step, quantity, which).values())
            rows.append(
                [
                    material,
                    label,
                    *(
                        f"{fsa._pct(min(v))} bis {fsa._pct(max(v))}" if v else "–"
                        for v in (spans["layer"], spans["body"])
                    ),
                ]
            )
    doc.extend(
        fsa._table(["Stufe", "Größe", "Schichteffekt (Spanne)", "Körpereffekt (Spanne)"], rows)
    )
    doc.append("")
    doc.extend(["## Bilder", ""])
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
    parser.add_argument("--ring-qs", type=Path, required=True)
    parser.add_argument("--ring-rates", type=Path, default=None)
    parser.add_argument("--levels", type=Path, required=True)
    parser.add_argument("--pocket", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    for line in analyse(
        args.ring_qs.resolve(),
        args.ring_rates.resolve() if args.ring_rates else None,
        args.levels.resolve(),
        args.pocket.resolve(),
        args.out.resolve(),
    ):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
