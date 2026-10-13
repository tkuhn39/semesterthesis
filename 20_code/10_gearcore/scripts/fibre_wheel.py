"""The fibre orientation of the whole wheel (the closed 52-tooth mesh mapped in CONVERSE,
ADR-116 item 49): the zones of every tooth evaluated as ``fibre_orientation.py`` does for one
tooth, the scatter from tooth to tooth around the wheel, and the transverse section of the
whole wheel with the fibre direction of every element (ADR-119 amendment).

    uv run --all-extras python scripts/fibre_wheel.py \\
        --mesh 80_output/fe/kst_e/vollrad_52teeth_ring/wheel_mesh.inp \\
        --cof 30_references_and_examples/91_Converse/wheel-52_mesh_QS.cof \\
        --out 80_output/fe/faserorientierung_vollrad/ring

Writes ``zaehne.csv`` (zone results per tooth, written right after the evaluation),
``bericht.md`` (the scatter per zone, the teeth with the largest and smallest anisotropy,
tooth 27 against the sector's tooth 3 when a sector evaluation is given with
``--sector-zonen``), and the figures ``umfang`` (AI of the main zones over the tooth number)
and ``vollrad`` (the section at mid-width).
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import fibre_orientation as fo  # noqa: E402

from gearcore.errors import InputRangeError  # noqa: E402
from gearcore.fe import deck as dk  # noqa: E402
from gearcore.fe import fibre as fb  # noqa: E402
from gearcore.plot_style import (  # noqa: E402
    DEGREE_COLOURMAP,
    MARKERS,
    decimal_comma,
    legend_outside,
    new_figure,
)
from gearcore.plot_style import save as save_figure  # noqa: E402

REPO = Path(__file__).resolve().parents[3]
MAIN_ZONES = ("LT", "LF", "LFU", "LFO", "S", "RFO", "RFU", "RF", "RT", "M", "U")
PLOT_ZONES = ("LF", "RF", "LFU", "RFU", "LFO", "RFO", "LT", "M", "U")


def teeth_of(node_sets: Mapping[str, Sequence[int]]) -> list[str]:
    names = {
        k.split("_")[1]
        for k in node_sets
        if k.startswith("WHEEL_T") and k.endswith("_LEFT_SURF_TIP_NODES")
    }
    return sorted(names, key=lambda n: int(n[1:]))


def evaluate_wheel(
    mesh: Path, cof: Path, skin_mm: float, below_mm: float
) -> tuple[dict[str, dict[str, fb.ZoneResult]], Mapping[int, tuple[float, float, float]]]:
    """Zone results of every tooth and the node coordinates of the mesh."""
    text = mesh.read_text(encoding="ascii", errors="replace")
    nodes = dk.read_node_coordinates(text)
    connectivity = dk.read_element_connectivity(text)
    node_sets, _ = dk.read_sets(text)
    cof_text = cof.read_text(encoding="utf-8", errors="replace")
    orientation = dk.read_distribution(cof_text)
    states = dk.read_field_variables(cof_text)
    dk.verify_orientation_file(
        cof_text,
        element_labels=tuple(sorted(connectivity)),
        node_labels=dk.read_node_labels(text),
        name=cof.name,
    )
    # centroid angles of every element once, so each tooth sees only its neighbourhood
    labels = np.array(sorted(connectivity), dtype=np.int64)
    first = np.array([nodes[connectivity[int(k)][0]][:2] for k in labels])
    angle = np.arctan2(first[:, 1], first[:, 0])
    results: dict[str, dict[str, fb.ZoneResult]] = {}
    for name in teeth_of(node_sets):
        tooth = fo.tooth_geometry(name, nodes, node_sets)
        near = np.abs(fo._wrapped(angle, tooth.centre_angle_rad)) <= 2.0 * tooth.half_pitch_rad
        sub = {int(k): connectivity[int(k)] for k in labels[near]}
        elements = fo.tooth_elements(tooth, nodes, sub, orientation, states, skin_mm, below_mm)
        results[name] = fo.zone_results(elements, tooth)
        shown = ", ".join(
            f"{zone} {results[name][zone].anisotropy_index:.2f}"
            for zone in ("LF", "M")
            if zone in results[name]
        )
        print(f"{name}: {elements.labels.size} elements, AI {shown}", flush=True)
    if not results:
        raise InputRangeError("the mesh has no tooth sets")
    return results, nodes


def write_csv(out: Path, results: Mapping[str, Mapping[str, fb.ZoneResult]]) -> None:
    with (out / "zaehne.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(
            [
                "tooth",
                "zone",
                "elements",
                "lambda_1",
                "lambda_2",
                "lambda_3",
                "AI",
                "angle_deg",
                "in_plane",
                "tilt_deg",
                "a11_mean",
            ]
        )
        for n, zones in results.items():
            for zone in fb.ZONE_ORDER:
                r = zones.get(zone)
                if r is not None:
                    writer.writerow(
                        [
                            n,
                            zone,
                            r.elements,
                            *(f"{v:.6f}" for v in r.eigenvalues),
                            f"{r.anisotropy_index:.6f}",
                            f"{r.angle_deg:.3f}",
                            f"{r.in_plane:.4f}",
                            f"{r.tilt_deg:.3f}",
                            f"{r.a11_mean:.6f}",
                        ]
                    )


def figure_circumference(
    results: Mapping[str, Mapping[str, fb.ZoneResult]], stem: Path
) -> list[Path]:
    """AI of the main zones over the tooth number."""
    names = list(results)
    x = np.arange(1, len(names) + 1)
    figure, axes = new_figure("full", 0.55)
    for k, zone in enumerate(PLOT_ZONES):
        values = [
            results[n][zone].anisotropy_index if zone in results[n] else np.nan for n in names
        ]
        axes.plot(x, values, marker=MARKERS[k % len(MARKERS)], label=zone)
    axes.set_xlabel("Zahn")
    axes.set_ylabel("AI")
    axes.set_ylim(0.0, 1.0)
    axes.set_xticks(x[::3])
    decimal_comma(axes, which="y")
    legend_outside(figure, axes, where="bottom", ncol=5)
    return save_figure(figure, stem)


def figure_wheel_section(
    mesh: Path, cof: Path, nodes: Mapping[int, tuple[float, float, float]], stem: Path
) -> list[Path]:
    """The transverse section of the whole wheel at the element layer nearest z = 0: the
    fibre direction of every element as a line coloured by a_11."""
    from matplotlib.collections import LineCollection
    from matplotlib.colors import Normalize

    text = mesh.read_text(encoding="ascii", errors="replace")
    connectivity = dk.read_element_connectivity(text)
    cof_text = cof.read_text(encoding="utf-8", errors="replace")
    orientation = dk.read_distribution(cof_text)
    states = dk.read_field_variables(cof_text)
    labels = np.array(sorted(connectivity), dtype=np.int64)
    corners = np.array([[nodes[n] for n in connectivity[int(k)]] for k in labels])
    centroids = corners.mean(axis=1)
    z = centroids[:, 2]
    level = min(sorted(set(np.round(z, 4))), key=lambda v: abs(v))
    mask = np.isclose(z, level, atol=1e-4)
    e1 = np.array([orientation[int(k)][0] for k in labels[mask]])
    e1 /= np.linalg.norm(e1, axis=1)[:, np.newaxis]
    a11 = np.array(
        [np.mean([states[int(n)][0] for n in connectivity[int(k)]]) for k in labels[mask]]
    )
    # element size in the plane: the area of the bottom face by the 2D cross product
    u = corners[mask][:, 1, :2] - corners[mask][:, 0, :2]
    v = corners[mask][:, 3, :2] - corners[mask][:, 0, :2]
    size = np.sqrt(np.abs(u[:, 0] * v[:, 1] - u[:, 1] * v[:, 0]))
    half = 0.45 * size
    px, py = centroids[mask, 0], centroids[mask, 1]
    segments = np.stack(
        [
            np.column_stack([px - half * e1[:, 0], py - half * e1[:, 1]]),
            np.column_stack([px + half * e1[:, 0], py + half * e1[:, 1]]),
        ],
        axis=1,
    )
    order = np.argsort(a11)
    written: list[Path] = []
    limit = float(np.hypot(px, py).max()) + 1.0
    # the whole wheel and a window of about five teeth around +y (tooth 27 and its neighbours)
    for suffix, aspect, width, xlim, ylim in (
        ("", 1.0, 0.6, (-limit, limit), (-limit, limit)),
        ("_ausschnitt", 0.8, 0.8, (-9.0, 9.0), (14.0, 28.4)),
    ):
        figure, axes = new_figure("full", aspect)
        collection = LineCollection(
            segments[order].tolist(),
            cmap=DEGREE_COLOURMAP,
            norm=Normalize(1.0 / 3.0, 1.0),
            linewidths=width,
        )
        collection.set_array(a11[order])
        axes.add_collection(collection)
        bar = figure.colorbar(collection, ax=axes, pad=0.02, shrink=0.8)
        bar.set_label("Orientierungsgrad $a_{11}$")
        axes.set_aspect("equal")
        axes.set_xlim(*xlim)
        axes.set_ylim(*ylim)
        axes.set_xlabel("$x$ in mm")
        axes.set_ylabel("$y$ in mm")
        decimal_comma(axes)
        written.extend(save_figure(figure, Path(str(stem) + suffix)))
    return written


def write_report(
    out: Path,
    results: Mapping[str, Mapping[str, fb.ZoneResult]],
    inputs: Mapping[str, str],
    sector: Mapping[str, tuple[float, float, float]] | None,
    pictures: Mapping[str, Sequence[Path]],
) -> list[str]:
    names = list(results)
    doc = ["# Faserorientierung über dem Umfang des ganzen Rads", ""]
    doc.append(
        f"Mapping {inputs['cof']} auf {inputs['mesh']} (Vollrad, {len(names)} Zähne); je Zahn die "
        f"Zonen wie in der Auswertung eines Zahns (Streifen {inputs['skin']} mm, ADR-119). Zahn 27 "
        "liegt auf +y wie Zahn 3 des Fünfzahn-Sektors."
    )
    doc.append("")
    doc.extend(["## 1 Streuung der Zonen über dem Umfang", ""])
    rows = []
    summary: list[str] = []
    for zone in MAIN_ZONES:
        present = [n for n in names if zone in results[n]]
        ai = np.array([results[n][zone].anisotropy_index for n in present])
        l3 = np.array([results[n][zone].eigenvalues[2] for n in present])
        if ai.size == 0:
            continue
        lo = present[int(np.argmin(ai))]
        hi = present[int(np.argmax(ai))]
        ct = fb.FVA856_ZONES.get(fo.mirrored(zone))
        spread = float(ai.std(ddof=1)) if ai.size > 1 else 0.0
        t27 = results.get("T27", {}).get(zone)
        rows.append(
            [
                zone,
                fo._g(float(ai.mean())),
                fo._g(spread),
                f"{fo._g(float(ai.min()))} ({lo})",
                f"{fo._g(float(ai.max()))} ({hi})",
                fo._g(float(l3.mean())),
                fo._g(ct[3]) if ct else "–",
                fo._g(t27.anisotropy_index) if t27 is not None else "–",
                fo._g(sector[zone][1]) if sector and zone in sector else "–",
            ]
        )
        summary.append(
            f"{zone}: AI {ai.mean():.2f} ± {spread:.2f} ({ai.min():.2f} {lo} .. {ai.max():.2f} {hi})"
        )
    doc.extend(
        fo._table(
            [
                "Zone",
                "AI Mittel",
                "AI Std",
                "AI min (Zahn)",
                "AI max (Zahn)",
                "λ3 Mittel",
                "AI CT Bild 17",
                "AI Zahn 27",
                "AI Zahn 3 des Sektors",
            ],
            rows,
        )
    )
    doc.append("")
    doc.extend(["## 2 Vorzugsrichtung der Flanken- und Fußzonen über dem Umfang", ""])
    rows = []
    for zone in ("LF", "RF", "LFU", "RFU", "LFO", "RFO"):
        angles = np.array([results[n][zone].angle_deg for n in names if zone in results[n]])
        planes = np.array([results[n][zone].in_plane for n in names if zone in results[n]])
        rows.append(
            [
                zone,
                fo._g(float(np.median(angles)), 1),
                fo._g(float(angles.min()), 1),
                fo._g(float(angles.max()), 1),
                fo._g(float(np.median(planes))),
                fo._g(float(np.mean(planes < 0.5)) * 100.0, 0) + " %",
            ]
        )
    doc.extend(
        fo._table(
            [
                "Zone",
                "Winkel Median in °",
                "min",
                "max",
                "Anteil in der Ebene (Median)",
                "Zähne mit axialer Hauptachse",
            ],
            rows,
        )
    )
    doc.append("")
    doc.extend(["## 3 Bilder", ""])
    for key, paths in pictures.items():
        doc.append(f"- {key}: " + ", ".join(p.name for p in paths))
    doc.append("")
    (out / "bericht.md").write_text("\n".join(doc), encoding="utf-8")
    captions = [
        "# Bildunterschriften",
        "",
        "- `umfang`: Anisotropie-Index der Zonen (Zonen nach Bild 17 von FVA 856 I) über dem "
        f"Umfang des Rads, je Zahn aus dem Zonentensor über die ganze Zahnbreite; Mapping "
        f"{inputs['cof']} auf das Vollrad.",
        "- `vollrad`: Faserrichtung je Element in der Stirnebene bei Zahnmitte über das ganze Rad, "
        "Linienrichtung = Hauptachse der Faserorientierung, Farbe = Orientierungsgrad a_11 des "
        "Elements.",
        "- `vollrad_ausschnitt`: derselbe Schnitt als Ausschnitt um Zahn 27 (fünf Zähne auf +y).",
        "",
    ]
    (out / "bildunterschriften.md").write_text("\n".join(captions), encoding="utf-8")
    return summary


def read_sector_zones(path: Path) -> dict[str, tuple[float, float, float]]:
    """zone -> (λ3, AI, angle) of a ``zonen.csv`` of ``fibre_orientation.py``."""
    out: dict[str, tuple[float, float, float]] = {}
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            out[row["zone"]] = (float(row["lambda_3"]), float(row["AI"]), float(row["angle_deg"]))
    return out


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--mesh", type=Path, required=True)
    parser.add_argument("--cof", type=Path, required=True)
    parser.add_argument("--skin", type=float, default=0.2)
    parser.add_argument("--below", type=float, default=1.0)
    parser.add_argument(
        "--sector-zonen",
        type=Path,
        default=None,
        help="zonen.csv of the sector evaluation (tooth 3) for the comparison with tooth 27",
    )
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    mesh, cof, out = args.mesh.resolve(), args.cof.resolve(), args.out.resolve()
    results, nodes = evaluate_wheel(mesh, cof, args.skin, args.below)
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out, results)
    pictures = {
        "umfang": figure_circumference(results, out / "umfang"),
        "vollrad": figure_wheel_section(mesh, cof, nodes, out / "vollrad"),
    }
    sector = read_sector_zones(args.sector_zonen.resolve()) if args.sector_zonen else None
    inputs = {
        "mesh": str(mesh.relative_to(REPO)) if mesh.is_relative_to(REPO) else str(mesh),
        "cof": str(cof.relative_to(REPO)) if cof.is_relative_to(REPO) else str(cof),
        "skin": fo._g(args.skin, 2),
    }
    for line in write_report(out, results, inputs, sector, pictures):
        print(line)
    print(out / "bericht.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
