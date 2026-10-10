"""Evaluate the measurements of the manufactured gears (``70_input/71_Messungen``).

    uv run --all-extras python scripts/measurements.py inventory [--input DIR] [--out DIR]

``inventory`` lists every measured part with its files, measurement rounds and anomalies:
``inventory.md`` (one table per part kind), ``inventory.csv`` (one row per file) and
``anomalies.md``. Further subcommands (``gina``, ``contour``, ``roughness``, ``compare``,
``report``) follow with the later increments of the measurement track.

Everything that computes lives in ``gearcore.measurement``; this script reads the folder, calls
the package and writes files below ``80_output/messungen`` (gitignored).
"""

from __future__ import annotations

import argparse
import csv
import io
from collections import Counter
from pathlib import Path

from gearcore.measurement.inventory import Inventory, Kind, MeasurementFile, scan_folder

REPO_ROOT = Path(__file__).resolve().parents[3]
INPUT = REPO_ROOT / "70_input" / "71_Messungen"
OUTPUT = REPO_ROOT / "80_output" / "messungen"

KIND_LABELS: dict[Kind, str] = {
    "mew": "GINA Messwerte (.mew)",
    "mka": "GINA Messkurven (.mka)",
    "messblatt_pdf": "GINA Messblatt (PDF)",
    "contour": "Konturscan (.DAT)",
    "roughness": "Rauheit ASCII (.txt)",
    "roughness_profile": "Rauheit Profil (.hwp)",
    "roughness_pdf": "Rauheit Protokoll (PDF)",
}
PART_LABELS = {"wheel": "Kunststoffrad (z = 52)", "pinion": "Stahlritzel (z = 51)"}
LABELS = {"running_in": "Einlauf", "extra_test": "Zusatzversuch 12 Nm"}
GROUP_LABELS = {
    "core": "Laufversuch (Kerngruppe)",
    "scatter": "Fertigungsstreuung",
    "rig_series": "Serie des Prüfstandsritzels",
    "older": "älteres Ritzel",
}


def _table(columns: list[str], rows: list[list[str]]) -> list[str]:
    lines = ["| " + " | ".join(columns) + " |", "|" + "---|" * len(columns)]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return lines


def inventory_markdown(inventory: Inventory) -> str:
    lines = [f"# Inventar der Messungen unter `{inventory.root}`", ""]
    kinds = Counter(file.kind for part in inventory.parts for file in part.files)
    lines.append(
        f"{len(inventory.parts)} vermessene Teile, "
        f"{sum(kinds.values())} zugeordnete Dateien, {len(inventory.unassigned)} nicht zugeordnete, "
        f"{len(inventory.ignored)} absichtlich übergangene, {len(inventory.unknown)} unbekannte."
    )
    lines.append("")
    lines.extend(
        _table(["Dateiart", "Anzahl"], [[KIND_LABELS[k], str(n)] for k, n in sorted(kinds.items())])
    )
    for part_kind in ("wheel", "pinion"):
        parts = [p for p in inventory.parts if p.part == part_kind]
        if not parts:
            continue
        lines.extend(["", f"## {PART_LABELS[part_kind]}", ""])
        columns = [
            "ME",
            "Gruppe",
            "Chargenlabel",
            "GINA-Runden (Datum)",
            "mew/mka",
            "Konturscans (Zahn)",
            "Rauheit (Flanke)",
            "Anmerkungen",
        ]
        rows: list[list[str]] = []
        for part in parts:
            gina = part.of_kind("mew")
            by_round: dict[int, list[MeasurementFile]] = {}
            for f in gina:
                if f.measurement_round is not None:
                    by_round.setdefault(f.measurement_round, []).append(f)
            rounds = ", ".join(
                f"{r} ({min(f.measured_on or '' for f in fs)}"
                + (f", x{len(fs)}" if len(fs) > 1 else "")
                + ")"
                for r, fs in sorted(by_round.items())
            )
            contours = part.of_kind("contour")
            teeth = ", ".join(
                f"z{f.tooth}" + ("*" if any("coarse" in a for a in f.anomalies) else "")
                for f in sorted(contours, key=lambda f: (f.tooth or 0, f.path))
            )
            roughness = part.of_kind("roughness")
            flanks = ", ".join(sorted({f.flank for f in roughness if f.flank}))
            notes = "; ".join(
                note for file in part.files for note in file.anomalies if "coarse" not in note
            )
            rows.append(
                [
                    part.me,
                    GROUP_LABELS.get(part.group, part.group),
                    ", ".join(LABELS.get(label, label) for label in part.labels) or "",
                    ", ".join(part.batch_labels) or "–",
                    rounds or "–",
                    f"{len(gina)}/{len(part.of_kind('mka'))}",
                    teeth or "–",
                    flanks or "–",
                    notes or "",
                ]
            )
        lines.extend(_table(columns, rows))
        lines.append("")
        lines.append("`*` grober Scan (unter 600 Punkte).")
    if inventory.unassigned:
        lines.extend(["", "## Nicht zugeordnet", ""])
        lines.extend(_table(["ME", "Datei"], [[f.me, f.path] for f in inventory.unassigned]))
    if inventory.unknown:
        lines.extend(["", "## Unbekannte Dateien", ""])
        lines.extend(f"- `{path}`" for path in inventory.unknown)
    return "\n".join(lines) + "\n"


def inventory_csv(inventory: Inventory) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";", lineterminator="\n")
    writer.writerow(
        [
            "me",
            "part",
            "group",
            "kind",
            "path",
            "variant",
            "measured_on",
            "round",
            "tooth",
            "flank",
            "trace",
            "points",
            "batch_label",
            "anomalies",
        ]
    )
    for part in inventory.parts:
        for file in part.files:
            writer.writerow(
                [
                    part.me,
                    part.part,
                    part.group,
                    file.kind,
                    file.path,
                    file.variant or "",
                    file.measured_on or "",
                    file.measurement_round if file.measurement_round is not None else "",
                    file.tooth if file.tooth is not None else "",
                    file.flank or "",
                    file.trace if file.trace is not None else "",
                    file.points if file.points is not None else "",
                    file.batch_label or "",
                    "; ".join(file.anomalies),
                ]
            )
    for file in inventory.unassigned:
        writer.writerow(
            [
                file.me,
                file.part,
                "unassigned",
                file.kind,
                file.path,
                file.variant or "",
                file.measured_on or "",
                "",
                file.tooth if file.tooth is not None else "",
                file.flank or "",
                file.trace if file.trace is not None else "",
                "",
                file.batch_label or "",
                "; ".join(file.anomalies),
            ]
        )
    return buffer.getvalue()


def anomalies_markdown(inventory: Inventory) -> str:
    lines = ["# Auffälligkeiten der Messdaten", ""]
    lines.extend(f"- {note}" for note in inventory.anomalies)
    if not inventory.anomalies:
        lines.append("Keine.")
    return "\n".join(lines) + "\n"


def run_inventory(input_dir: Path, out: Path) -> list[Path]:
    inventory = scan_folder(input_dir)
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for name, text in (
        ("inventory.md", inventory_markdown(inventory)),
        ("inventory.csv", inventory_csv(inventory)),
        ("anomalies.md", anomalies_markdown(inventory)),
    ):
        path = out / name
        path.write_text(text, encoding="utf-8", newline="\n")
        written.append(path)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)
    inventory = sub.add_parser(
        "inventory", help="list the measured parts, their files and anomalies"
    )
    inventory.add_argument("--input", type=Path, default=INPUT, help="measurement folder")
    inventory.add_argument("--out", type=Path, default=OUTPUT / "inventory")
    args = parser.parse_args()
    if args.command == "inventory":
        for path in run_inventory(args.input, args.out):
            print(path)


if __name__ == "__main__":
    main()
