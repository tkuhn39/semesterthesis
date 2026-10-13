"""The two fibre orientations of the anisotropic steps W3 and W4 at the named points A to E:
the CONVERSE mapping of the CADMOULD result (the weekend series at QS, the rate pilot at
DY1/DY2) against the CT-zone orientation of FVA 856 I placed on the same mesh (the CT pilot),
every rate side by side (ADR-119, FIB-04).

    uv run --all-extras python scripts/fe_orientation_comparison.py \\
        --mapped-qs 80_output/fe/kst_e/series_..._qs_gerechnet \\
        --mapped-rates 80_output/fe/kst_e/pilot_..._dy1dy2_AtoE_gerechnet \\
        --ct 80_output/fe/kst_e/pilot_..._ctorient_..._AtoE_gerechnet \\
        --out 80_output/fe/kst_e/vergleich_orientierung_AtoE

Positions are matched by their distance from A. One effect: the orientation (CT zones
against the mapping, same mesh, same card, same rate), in percent per material step, one
figure per load step and rate; the isotropic steps W1 and W2 do not depend on the
orientation and are left out.
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

import fe_body_comparison as fbc  # noqa: E402
import fe_series_analysis as fsa  # noqa: E402

from gearcore.errors import InputRangeError  # noqa: E402
from gearcore.fe import evaluation as ev  # noqa: E402
from gearcore.plot_style import decimal_comma, legend_outside, new_figure  # noqa: E402
from gearcore.plot_style import save as save_figure  # noqa: E402

SOURCES = ("mapped", "ct")
SOURCE_LABELS = {
    "mapped": "Orientierung aus dem CONVERSE-Mapping des CADMOULD-Ergebnisses",
    "ct": "Orientierung der CT-Zonen (FVA 856 I, Bild 17 und 18)",
}
ANISOTROPIC_STEPS = ("W3", "W4")
EFFECT_TITLE = "Orientierung: CT-Zonen gegen Mapping, gleiches Netz und gleiche Karte"
POINTS = fbc.POINTS
SHORT_LABELS = fbc.SHORT_LABELS


def load_sources(
    mapped_qs: Path, mapped_rates: Path | None, ct: Path
) -> dict[str, dict[str, list[ev.PathPoint]]]:
    """source -> series name -> path points of the anisotropic steps; the mapping takes its QS
    series from the series folder and its DY1/DY2 series from the rate pilot."""
    out: dict[str, dict[str, list[ev.PathPoint]]] = {}
    _manifest, series = fsa._load(mapped_qs)
    out["mapped"] = {
        name: points
        for name, points in series.items()
        if fsa.rate_of(name) == "QS" and fsa.step_of(name) in ANISOTROPIC_STEPS
    }
    if mapped_rates is not None:
        _manifest, rates = fsa._load(mapped_rates)
        out["mapped"].update(
            {
                name: pts
                for name, pts in rates.items()
                if fsa.rate_of(name) != "QS" and fsa.step_of(name) in ANISOTROPIC_STEPS
            }
        )
    _manifest, ct_series = fsa._load(ct)
    out["ct"] = {n: p for n, p in ct_series.items() if fsa.step_of(n) in ANISOTROPIC_STEPS}
    if not out["mapped"] or not out["ct"]:
        raise InputRangeError("both the mapped and the CT folders need extracted W3/W4 fields")
    return out


def values(
    sources: Mapping[str, Mapping[str, Sequence[ev.PathPoint]]],
    series: str,
    step: str,
    quantity: str,
) -> dict[str, dict[str, float]]:
    """source -> point label -> value (only sources that carry the series)."""
    out: dict[str, dict[str, float]] = {}
    for source in SOURCES:
        points = sources[source].get(series)
        if points:
            at = fsa.values_at_points(points, step, quantity)
            if at:
                out[source] = at
    return out


def effect(
    sources: Mapping[str, Mapping[str, Sequence[ev.PathPoint]]],
    series: str,
    step: str,
    quantity: str,
) -> dict[str, float]:
    """point label -> relative change of ``quantity`` from the mapping to the CT zones."""
    per_source = values(sources, series, step, quantity)
    if "mapped" not in per_source or "ct" not in per_source:
        return {}
    out: dict[str, float] = {}
    for point in POINTS:
        rel = fsa.relative(per_source["mapped"].get(point), per_source["ct"].get(point))
        if rel is not None:
            out[point] = rel
    return out


def figure_effect(
    sources: Mapping[str, Mapping[str, Sequence[ev.PathPoint]]],
    series_names: Sequence[str],
    step: str,
    stem: Path,
) -> list[Path]:
    """The orientation effect in percent at A to E, one panel per quantity, the anisotropic
    steps of one rate as series; markers only (nothing is computed between the points)."""
    figure, axes = new_figure("full", 1.1, rows=len(SHORT_LABELS), sharex=True)
    x = np.arange(len(POINTS))
    for ax, (label, quantity) in zip(axes, SHORT_LABELS, strict=True):
        for series in series_names:
            rel = effect(sources, series, step, quantity)
            if not rel:
                continue
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


def caption_effect(series_names: Sequence[str], step: str) -> str:
    """The caption of ``figure_effect`` for ``bildunterschriften.md`` (no title in the SVG)."""
    rate = fsa.rate_text(series_names[0]) if series_names else ""
    return (
        f"{EFFECT_TITLE} an den Normpunkten A bis E, relative Änderung je Werkstoffstufe, "
        f"{fsa.STEP_LABELS.get(step, step)}, {rate}; Größtwerte über die Zahnbreite, Marker ohne "
        "Linie, weil der Verlauf zwischen den Punkten nicht gerechnet ist."
    )


def analyse(mapped_qs: Path, mapped_rates: Path | None, ct: Path, out: Path) -> list[str]:
    sources = load_sources(mapped_qs, mapped_rates, ct)
    manifest = json.loads((ct / "manifest.json").read_text(encoding="utf-8"))
    steps = [str(s) for s in manifest.get("step_names", []) if s != "SEAT"]
    series_names = sorted(
        {name for source in SOURCES for name in sources[source]},
        key=lambda n: (fsa.rate_of(n), fsa.step_of(n)),
    )
    out.mkdir(parents=True, exist_ok=True)
    doc = ["# Vergleich der Faserorientierungen an den Normpunkten A bis E", ""]
    doc.append(
        "Anisotrope Werkstoffstufen W3 und W4 mit der Orientierung aus dem CONVERSE-Mapping "
        "(Wochenendserie QS, Ratenpilot DY1/DY2) und mit der Orientierung der CT-Zonen von "
        "FVA 856 I auf demselben Netz (CT-Pilot); Werte an den gemeinsamen Stellungen A bis E, "
        "Größtwerte über die Zahnbreite. Orientierungseffekt = CT-Zonen gegen Mapping bei gleicher "
        "Karte und Rate. Die CT-Datei trägt je Zone konstante Eigenwerte und ebene Richtungen in "
        "den Zonenwinkeln des Berichts, ohne Gradient über die Randschicht und ohne Streuung über "
        "die Breite (FIB-04); der Körper bleibt der des Mappings."
    )
    doc.append("")
    for source in SOURCES:
        names = sorted(sources[source], key=lambda n: (fsa.rate_of(n), fsa.step_of(n)))
        doc.append(f"- {SOURCE_LABELS[source]}: Serien {', '.join(names) or '–'}")
    doc.append("")
    lines: list[str] = []
    captions: list[str] = []
    for step in steps:
        doc.extend([f"## {fsa.STEP_LABELS.get(step, step)}", ""])
        rows = []
        for series in series_names:
            for quantity, label, unit, scale in fsa.GLOBAL_QUANTITIES:
                per_source = values(sources, series, step, quantity)
                if "mapped" not in per_source or "ct" not in per_source:
                    continue
                for point in POINTS:
                    if point not in per_source["mapped"] or point not in per_source["ct"]:
                        continue
                    mapped_v = per_source["mapped"][point]
                    ct_v = per_source["ct"][point]
                    rows.append(
                        [
                            series,
                            f"{label} in {unit}",
                            point,
                            fsa._g(abs(mapped_v) * scale, 2),
                            fsa._g(abs(ct_v) * scale, 2),
                            fsa._pct(fsa.relative(mapped_v, ct_v)),
                        ]
                    )
        doc.extend(
            fsa._table(
                ["Serie", "Größe", "Punkt", "Mapping", "CT-Zonen", "Orientierungseffekt"], rows
            )
        )
        doc.append("")
        for rate in sorted({fsa.rate_of(n) for n in series_names}):
            names = [n for n in series_names if fsa.rate_of(n) == rate]
            key = f"orientierungseffekt_{step}_{rate}"
            pictures = figure_effect(sources, names, step, out / key)
            lines.append(f"{key}: " + ", ".join(p.name for p in pictures))
            captions.append(f"- `{key}`: {caption_effect(names, step)}")
    doc.extend(["## Zusammenfassung des Effekts", ""])
    doc.append(
        "Spanne der relativen Änderung je Größe und Werkstoffstufe über alle Raten, Lastschritte "
        "und Normpunkte, und die Spanne je Rate."
    )
    doc.append("")
    rows = []
    rates = sorted({fsa.rate_of(n) for n in series_names})
    for material in ANISOTROPIC_STEPS:
        for quantity, label, _unit, _scale in fsa.GLOBAL_QUANTITIES:
            per_rate: dict[str, list[float]] = {rate: [] for rate in rates}
            for step in steps:
                for series in series_names:
                    if fsa.step_of(series) != material:
                        continue
                    per_rate[fsa.rate_of(series)].extend(
                        effect(sources, series, step, quantity).values()
                    )
            everything = [v for vs in per_rate.values() for v in vs]
            rows.append(
                [
                    material,
                    label,
                    f"{fsa._pct(min(everything))} bis {fsa._pct(max(everything))}"
                    if everything
                    else "–",
                    *(
                        f"{fsa._pct(min(v))} bis {fsa._pct(max(v))}" if v else "–"
                        for v in (per_rate[rate] for rate in rates)
                    ),
                ]
            )
    doc.extend(
        fsa._table(["Stufe", "Größe", "Spanne gesamt", *(f"Spanne {r}" for r in rates)], rows)
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
    parser.add_argument("--mapped-qs", type=Path, required=True)
    parser.add_argument("--mapped-rates", type=Path, default=None)
    parser.add_argument("--ct", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    for line in analyse(
        args.mapped_qs.resolve(),
        args.mapped_rates.resolve() if args.mapped_rates else None,
        args.ct.resolve(),
        args.out.resolve(),
    ):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
