"""A CONVERSE orientation file whose teeth carry the fibre orientation of the CT zones of
FVA 856 I instead of the moulding simulation (ADR-119 amendment): the zone map of Bild 18
(preferred direction in the transverse plane) with the eigenvalues of Bild 17 per zone, written
in the format CONVERSE uses for Abaqus (``*DISTRIBUTION`` row per element: the main direction
and a direction in the 1-2 plane, here the wheel axis as the CT's second eigenvector; the field
variables a_11, a_22 per node), everything else of the file (material card, the body below the
teeth) kept as mapped. The teeth of the FE steps W3 and W4 then follow the CT picture of a real
gear, for a comparison with the mapped orientation.

    uv run --all-extras python scripts/ct_orientation.py \\
        --mesh 80_output/fe/kst_e/<folder>/wheel_mesh.inp \\
        --cof 30_references_and_examples/91_Converse/wheel_mesh_QS.cof \\
        --skin 0.2 --out 80_output/fe/kst_e/orientierung_ct

Writes ``<cof stem>_ct.cof`` and ``bericht_<cof stem>.md`` (what was replaced, the zone values
written, and the check: the zone evaluation of ``fibre_orientation`` on the written file
against the values of the report); one call per rate card (QS, DY1, DY2), the orientation
rows of the cards are the same, the material differs.
"""

from __future__ import annotations

import argparse
import math
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

REPO = Path(__file__).resolve().parents[3]
KEEP_ZONES = ("U",)
"""Zones that keep the mapped orientation: below the root circle the report prints no
direction (Bild 18), and the mapped U zone matched its eigenvalues (ADR-119)."""


def zone_values(zone: str) -> tuple[float, float, float]:
    """(angle in degrees, a_11, a_22) of a zone from Bild 18 and Bild 17 of the report."""
    angle = fo.reference_angle(zone)
    if angle is None:
        raise InputRangeError(f"the report prints no direction for the zone {zone}")
    eigen = fb.FVA856_ZONES.get(fo.mirrored(zone))
    if eigen is None:
        raise InputRangeError(f"the report prints no eigenvalues for the zone {zone}")
    return angle, eigen[2], eigen[1]


def ct_rows(
    tooth: fo.Tooth, elements: fo.Elements, connectivity: Mapping[int, Sequence[int]]
) -> tuple[
    dict[int, tuple[float, float, float, float, float, float]],
    dict[int, tuple[float, float]],
    dict[str, int],
]:
    """Distribution rows (label -> e_1 and the second direction) and nodal states of the
    elements of one tooth that get the CT orientation; the count of elements per zone."""
    rows: dict[int, tuple[float, float, float, float, float, float]] = {}
    sums: dict[int, list[float]] = {}
    counts: dict[str, int] = {}
    z_axis = np.cross(tooth.radial, tooth.across)
    for label, zone in zip(elements.labels, elements.zones, strict=True):
        if zone in KEEP_ZONES:
            continue
        angle, a11, a22 = zone_values(zone)
        theta = math.radians(angle)
        e1 = math.cos(theta) * tooth.radial + math.sin(theta) * tooth.across
        rows[int(label)] = (
            float(e1[0]),
            float(e1[1]),
            float(e1[2]),
            float(z_axis[0]),
            float(z_axis[1]),
            float(z_axis[2]),
        )
        counts[zone] = counts.get(zone, 0) + 1
        for node in connectivity[int(label)]:
            acc = sums.setdefault(int(node), [0.0, 0.0, 0.0])
            acc[0] += a11
            acc[1] += a22
            acc[2] += 1.0
    states = {node: (acc[0] / acc[2], acc[1] / acc[2]) for node, acc in sums.items()}
    return rows, states, counts


def rewrite(
    text: str,
    rows: Mapping[int, tuple[float, float, float, float, float, float]],
    states: Mapping[int, tuple[float, float]],
) -> tuple[str, int, int]:
    """The orientation file with the distribution rows of ``rows`` and the field variables of
    ``states`` replaced; returns the text and how many element and node rows were replaced."""
    out: list[str] = []
    keyword = ""
    variable = 0
    replaced_elements = 0
    replaced_nodes = 0
    for raw in text.splitlines():
        line = raw.rstrip("\r")
        if line.startswith("**"):
            out.append(line)
            continue
        if line.startswith("*"):
            keyword = line[1:].split(",")[0].strip().upper()
            upper = line.upper()
            variable = int(upper.split("VARIABLE=")[1].split(",")[0]) if "VARIABLE=" in upper else 0
            out.append(line)
            continue
        first = line.split(",")[0].strip()
        if keyword == "DISTRIBUTION" and first:
            label = int(float(first))
            if label in rows:
                values = rows[label]
                out.append(f" {label}, " + ", ".join(f"{v:.6g}" for v in values))
                replaced_elements += 1
                continue
        elif keyword == "INITIAL CONDITIONS" and variable in (1, 2) and first:
            label = int(float(first))
            if label in states:
                out.append(f" {label}, {states[label][variable - 1]:.6g}")
                replaced_nodes += 1
                continue
        out.append(line)
    if replaced_elements != len(rows):
        raise InputRangeError(
            f"{len(rows) - replaced_elements} elements of the CT zones have no row in the file"
        )
    if replaced_nodes != 2 * len(states):
        raise InputRangeError(
            f"{2 * len(states) - replaced_nodes} field variable rows of the CT nodes are missing"
        )
    return "\n".join(out) + "\n", replaced_elements, replaced_nodes


def run(mesh: Path, cof: Path, skin_mm: float, out: Path, teeth: Sequence[str] | None) -> list[str]:
    text = mesh.read_text(encoding="ascii", errors="replace")
    nodes = dk.read_node_coordinates(text)
    connectivity = dk.read_element_connectivity(text)
    node_sets, _element_sets = dk.read_sets(text)
    cof_text = cof.read_text(encoding="utf-8", errors="replace")
    orientation = dk.read_distribution(cof_text)
    mapped_states = dk.read_field_variables(cof_text)
    dk.verify_orientation_file(
        cof_text,
        element_labels=tuple(sorted(connectivity)),
        node_labels=dk.read_node_labels(text),
        name=cof.name,
    )
    names = (
        list(teeth)
        if teeth
        else sorted(
            {
                k.split("_")[1]
                for k in node_sets
                if k.startswith("WHEEL_T") and k.endswith("_LEFT_SURF_TIP_NODES")
            },
            key=lambda n: int(n[1:]),
        )
    )
    rows: dict[int, tuple[float, float, float, float, float, float]] = {}
    states: dict[int, tuple[float, float]] = {}
    per_tooth: dict[str, dict[str, int]] = {}
    # every tooth sees only its neighbourhood of two pitches (the full wheel has 744 640 elements)
    labels_all = np.array(sorted(connectivity), dtype=np.int64)
    first_xy = np.array([nodes[connectivity[int(k)][0]][:2] for k in labels_all])
    angle_all = np.arctan2(first_xy[:, 1], first_xy[:, 0])
    for name in names:
        tooth = fo.tooth_geometry(name, nodes, node_sets)
        near = np.abs(fo._wrapped(angle_all, tooth.centre_angle_rad)) <= 2.0 * tooth.half_pitch_rad
        sub = {int(k): connectivity[int(k)] for k in labels_all[near]}
        elements = fo.tooth_elements(
            tooth, nodes, sub, orientation, mapped_states, skin_mm, 2.0 * skin_mm
        )
        tooth_rows, tooth_states, counts = ct_rows(tooth, elements, connectivity)
        rows.update(tooth_rows)
        for node, value in tooth_states.items():
            states[node] = value  # a node between two teeth: the last tooth wins (valley nodes)
        per_tooth[name] = counts
    written, n_elements, n_nodes = rewrite(cof_text, rows, states)
    out.mkdir(parents=True, exist_ok=True)
    target = out / f"{cof.stem}_ct.cof"
    target.write_text(written, encoding="utf-8")
    fit = dk.verify_orientation_file(
        written,
        element_labels=tuple(sorted(connectivity)),
        node_labels=dk.read_node_labels(text),
        name=target.name,
    )
    # the check: the zone evaluation on the written file reproduces the report's values
    new_orientation = dk.read_distribution(written)
    new_states = dk.read_field_variables(written)
    check = fo.tooth_geometry(names[len(names) // 2], nodes, node_sets)
    elements = fo.tooth_elements(
        check, nodes, connectivity, new_orientation, new_states, skin_mm, 2.0 * skin_mm
    )
    results = fo.zone_results(elements, check)
    doc = ["# Orientierungsdatei nach den CT-Zonen von FVA 856 I", ""]
    doc.append(
        "Die Bilder sind die des Abschlussberichts FVA 856 I (Heft 1491, Kapitel 6.2): Bild 16 "
        "(Zonentensor, S. 18), Bild 17 (Zonen mit Eigenwerten, S. 19) und Bild 18 (Zonenkarte mit "
        "Vorzugsrichtung, S. 19); eine Zeichnung der geschriebenen Orientierung liegt in "
        "`auswertung_T3/` (Auswertung mit `fibre_orientation.py` auf dieser Datei)."
    )
    doc.append("")
    doc.append(
        f"Vorlage {cof.name} (Mapping der Spritzgusssimulation), Netz {mesh.name}; die Zähne "
        f"{', '.join(names)} tragen die Zonenkarte Bild 18 des Berichts (Vorzugsrichtung in der "
        "Stirnebene, zweite Achse die Radachse wie der zweite Eigenvektor der CT in Bild 16) mit den "
        f"Eigenwerten λ3, λ2 der Zonen aus Bild 17 als a_11, a_22 der Knoten; Streifen {fo._g(skin_mm, 2)} mm "
        f"wie in der Auswertung; die Zone U unter dem Fußkreis und der Radkörper behalten das Mapping. "
        f"{n_elements} Elementzeilen und {n_nodes} Feldvariablenzeilen ersetzt; die Datei passt zum "
        f"Netz ({fit.elements} Elemente, {fit.nodes} Knoten)."
    )
    doc.append("")
    doc.extend(["## Ersetzte Elemente je Zahn und Zone", ""])
    zones = sorted({z for c in per_tooth.values() for z in c}, key=lambda z: fb.ZONE_ORDER.index(z))
    rows_table = [[name, *(str(per_tooth[name].get(z, 0)) for z in zones)] for name in names]
    doc.extend(fo._table(["Zahn", *zones], rows_table))
    doc.append("")
    doc.extend([f"## Prüfung: Zonenauswertung von {check.name} auf der geschriebenen Datei", ""])
    rows_table = []
    for zone in fb.ZONE_ORDER:
        if zone not in results:
            continue
        r = results[zone]
        ct = fb.FVA856_ZONES.get(fo.mirrored(zone))
        angle = fo.reference_angle(zone)
        rows_table.append(
            [
                zone,
                fo._g(r.eigenvalues[2]),
                fo._g(ct[2]) if ct else "–",
                fo._g(r.anisotropy_index),
                fo._g(ct[3]) if ct else "–",
                fo._angle_text(r),
                fo._g(angle, 1) if angle is not None else "–",
            ]
        )
    doc.extend(
        fo._table(
            ["Zone", "λ3", "λ3 Bild 17", "AI", "AI Bild 17", "Winkel", "Winkel Bild 18"], rows_table
        )
    )
    doc.append("")
    doc.append(
        "Abweichungen in den Übergangszonen und an Zonengrenzen kommen aus den Knotenmitteln "
        "(a_11, a_22 je Knoten als Mittel der angrenzenden Zonen) und aus der Zonenzuordnung der "
        "Auswertung, nicht aus den Elementrahmen."
    )
    doc.append("")
    (out / f"bericht_{cof.stem}.md").write_text("\n".join(doc), encoding="utf-8")
    return [
        f"{target}: {n_elements} elements and {n_nodes} field rows replaced on {len(names)} teeth",
        *(
            f"  {zone:4s} λ3 {results[zone].eigenvalues[2]:.3f} AI {results[zone].anisotropy_index:.3f} "
            f"angle {results[zone].angle_deg:+6.1f}° (report {fo.reference_angle(zone)})"
            for zone in fb.ZONE_ORDER
            if zone in results
        ),
        str(out / f"bericht_{cof.stem}.md"),
    ]


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--mesh", type=Path, required=True)
    parser.add_argument("--cof", type=Path, required=True)
    parser.add_argument("--teeth", nargs="*", default=None, help="teeth to replace (default: all)")
    parser.add_argument("--skin", type=float, default=0.2)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if not args.skin > 0.0:
        raise InputRangeError("--skin must be positive")
    for line in run(
        args.mesh.resolve(), args.cof.resolve(), args.skin, args.out.resolve(), args.teeth
    ):
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
