"""Evaluate the measurements of the manufactured gears (``70_input/71_Messungen``).

    uv run --all-extras python scripts/measurements.py inventory [--input DIR] [--out DIR]
    uv run --all-extras python scripts/measurements.py gina [--part wheel|pinion] [--me ME ...]
        [--rounds latest|all] [--no-plots]
    uv run --all-extras python scripts/measurements.py contour [--part wheel|pinion] [--me ME ...]
        [--include-coarse] [--magnify 10] [--corner-step 0.01] [--no-plots]
    uv run --all-extras python scripts/measurements.py roughness [--part wheel|pinion] [--me ME ...]

``inventory`` lists every measured part with its files, measurement rounds and anomalies:
``inventory.md`` (one table per part kind), ``inventory.csv`` (one row per file) and
``anomalies.md``.

``gina`` evaluates the Klingelnberg P40 value and curve files. Per part kind it writes the scatter
of every flank, pitch, runout and size value over the latest measurement of each part, core group
and scatter group side by side (``tabelle_streuung.md`` and ``.csv``), the repeatability of parts
measured several times (``wiederholbarkeit.md``), the tolerances the measuring program checked
against with the values that exceed them (``toleranzen_protokoll.md``), the tip relief of the
pinions (``kopfruecknahme_ritzel.md``), the pitch window of the failed teeth
(``fenster_zaehne.md``), the sector quantities Fpz/8 of the program against F_pk and F_pSk of
DIN ISO 1328-1 Anhang D (``teilungssektoren.md``) and, per part, the per-tooth pitch and radial
values of every tooth with that window (``zaehne_<ME>.svg/.png``) and the profile and lead curves
of the measured teeth (``profil_<ME>``, ``flankenlinie_<ME>``, only with ``--curves``: the Klingelnberg sheets in the
appendix show these curves, the user's decision of 2026-10-10).

``contour`` evaluates the P40 contour scans (transverse section of three teeth) against the
nominal tooth of the STplus case (the middle one of the three scanned teeth is the tooth the
file name says): per scan the axis, the involutes, the tip circles, the tip
relief, the base tooth thickness, the angular pitch and the shape of every tip corner (arc or
chamfer); tables ``bericht.md``, ``kanten.csv``, ``kopfruecknahme.csv``, ``zahndicke.csv``,
``teilung.csv``; figures ``ueberlagerung_<ME>_<scan>`` (the measured teeth on the nominal
tooth at true scale, ``--magnify`` exaggerates the deviation normal to the contour),
``ueberlagerung_<part>_<group>`` (one tooth of every part of a group) and
``kopfkante_<ME>_<scan>`` (every tip corner at 1:1 with the fitted arc and chamfer). Coarse
scans (about 400 points) are left out unless ``--include-coarse``.

``roughness`` reads the Hommel-Etamic ASCII exports (three traces per gear and flank): per part
and flank R_a and R_z as the instrument's mean of the traces with the traces themselves and their
spread (``tabelle.md``), the statistics of the core group and the scatter group
(``gruppen.md``) and every parameter raw (``rohdaten.csv``); duplicate exports are dropped. No
figure: the printed protocols go into the appendix (user's decision).

Everything that computes lives in ``gearcore.measurement``; this script reads the folder, calls
the package, draws in the house style (``gearcore.plot_style``) and writes files below
``80_output/messungen`` (gitignored). ``testruns`` (L1) reads the running-test workbook
``70_input/72_Kleingetriebepruefstand_KV3/kst-E_Laufversuche_KV3.xlsx`` through
``gearcore.measurement.test_rig`` and writes the clean run table, the events of the remarks
column verbatim, the crack windows, the loss rates of the re-adjustment history, the temperature
matrix and the anomaly list the user confirms. Further subcommands (``compare``, ``report``)
follow with the later increments of the measurement track.
"""

from __future__ import annotations

import argparse
import csv
import io
import math
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from statistics import median
from typing import Any

from gearcore import contour as ct
from gearcore import data
from gearcore.data import load_measurement_parts
from gearcore.errors import InputRangeError
from gearcore.generation import compute_generation
from gearcore.io.hommel import load_roughness_table
from gearcore.io.p40 import Flank, MkaFile, load_mew, load_mka
from gearcore.io.p40_contour import ContourScan, load_contour_scans
from gearcore.io.ste import load_ste, pair_input_from_ste
from gearcore.measurement import contour_scan as cs
from gearcore.measurement import gina
from gearcore.measurement import report as rp
from gearcore.measurement import roughness as rg
from gearcore.measurement import test_rig as tr
from gearcore.measurement import woehler as wl
from gearcore.measurement.inventory import (
    Inventory,
    Kind,
    MeasuredPart,
    MeasurementFile,
    scan_folder,
)
from gearcore.models.results import GenerationResult
from gearcore.plot_style import LINE_STYLES, MARKERS
from gearcore.plot_style import apply as apply_plot_style
from gearcore.plot_style import decimal_comma, legend_outside, new_figure, save, symbol_label
from gearcore.quantities import quantity

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
    "microscope": "Mikroskop Zahnkopf (JPG)",
}
PART_LABELS = {"wheel": "Kunststoffrad (z = 52)", "pinion": "Stahlritzel (z = 51)"}
LABELS = {"running_in": "Einlauf", "second_8nm_test": "zweiter 8-Nm-Lauf (kst-E_75)"}
GROUP_LABELS = {
    "core": "Laufversuch (Kerngruppe)",
    "scatter": "Fertigungsstreuung",
    "rig_series": "Serie des Prüfstandsritzels",
    "older": "älteres Ritzel",
}
FLANKS: tuple[Flank, ...] = ("links", "rechts")


def _table(columns: list[str], rows: list[list[str]]) -> list[str]:
    return rp.markdown_table(columns, rows)


# ---- inventory ---------------------------------------------------------------------------------


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
            "Label",
            "Chargenlabel",
            "GINA-Runden (Datum)",
            "mew/mka",
            "Konturscans (Zahn)",
            "Rauheit (Flanke)",
            "Anmerkungen",
        ]
        rows: list[list[str]] = []
        for part in parts:
            gina_files = part.of_kind("mew")
            by_round: dict[int, list[MeasurementFile]] = {}
            for f in gina_files:
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
                f"z{f.tooth}"
                + (f"-z{f.second_tooth}" if f.second_tooth is not None else "")
                + (" gelaufen" if f.after_test else "")
                + ("*" if any("coarse" in a for a in f.anomalies) else "")
                for f in sorted(contours, key=lambda f: (f.after_test, f.tooth or 0, f.path))
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
                    f"{len(gina_files)}/{len(part.of_kind('mka'))}",
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


def _cell(value: object) -> str:
    return "" if value is None else str(value)


def inventory_csv(inventory: Inventory) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";", lineterminator="\n")
    writer.writerow(
        [
            "me",
            "part",
            "group",
            "labels",
            "kind",
            "path",
            "variant",
            "measured_on",
            "round",
            "repeat",
            "tooth",
            "flank",
            "trace",
            "points",
            "batch_label",
            "anomalies",
        ]
    )

    def row(part_me: str, part_kind: str, group: str, labels: str, file: MeasurementFile) -> None:
        writer.writerow(
            [
                part_me,
                part_kind,
                group,
                labels,
                file.kind,
                file.path,
                _cell(file.variant),
                _cell(file.measured_on),
                _cell(file.measurement_round),
                _cell(file.repeat),
                _cell(file.tooth),
                _cell(file.flank),
                _cell(file.trace),
                _cell(file.points),
                _cell(file.batch_label),
                "; ".join(file.anomalies),
            ]
        )

    for part in inventory.parts:
        for file in part.files:
            row(part.me, part.part, part.group, "; ".join(part.labels), file)
    for file in inventory.unassigned:
        row(file.me, file.part, "unassigned", "", file)
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


# ---- gina --------------------------------------------------------------------------------------


Triple = tuple[MeasuredPart, MeasurementFile, gina.GinaResult]


def gina_results(
    inventory: Inventory, part_kind: gina.Part, me_filter: Sequence[str] | None = None
) -> list[Triple]:
    """(part, value file, typed result) of every ``.mew`` of the part kind, ordered by date."""
    out: list[Triple] = []
    root = Path(inventory.root)
    for part in inventory.parts:
        if part.part != part_kind or (me_filter and part.me not in me_filter):
            continue
        for file in sorted(part.of_kind("mew"), key=lambda f: (f.measured_on or "", f.path)):
            out.append((part, file, gina.gina_result(load_mew(root / file.path), part=part_kind)))
    return out


def _n(value: float | None, digits: int) -> str:
    return "–" if value is None else rp.german_number(value, digits)


def _digits(unit: str) -> int:
    return 3 if unit == "mm" else 1


def _symbol(name: str | None, fallback: str) -> str:
    """The registry symbol as plain text, or the P40 label marked as the program's own."""
    if name is None:
        return f"{fallback} (Messprogramm)"
    symbol = quantity(name).symbol
    return rp.plain_symbol(symbol) if symbol else fallback


def scatter_markdown(
    part_kind: str, groups: dict[str, Sequence[gina.GinaResult]]
) -> tuple[str, list[str], list[list[str]]]:
    """Scatter per group side by side: the Markdown text, and the CSV columns and rows."""
    lines = [f"# Streuung der GINA-Messwerte, {PART_LABELS[part_kind]}", ""]
    lines.append(
        "Je ME-Nummer die letzte Messung (Datum, dann Variante); Mittel, Standardabweichung "
        "(n − 1), Minimum und Maximum über die Teile der Gruppe. Symbole nach DIN ISO 1328-1 aus "
        "der Registry; Größen des Messprogramms ohne Normeintrag sind so gekennzeichnet "
        "(Fpz/8 ist die gleitende Teilungs-Spannenabweichung des Programms, nicht F_pk; siehe "
        "teilungssektoren.md). Flankenwerte sind die Mittel über die gemessenen Zähne; f_Hβ ist "
        "auf die Zahnbreite b bezogen (Einstellung 179 BZGFL 1: Z), nicht auf L_β."
    )
    lines.append("")
    tables = {
        name: {(r.label, r.flank): r for r in gina.scatter_table(results)}
        for name, results in groups.items()
        if results
    }
    order: list[tuple[str, str]] = []
    for table in tables.values():
        for key in table:
            if key not in order:
                order.append(key)
    columns = ["Größe", "Flanke", "Einheit"]
    for name in tables:
        label = GROUP_LABELS.get(name, name)
        columns += [f"{label}: n", "Mittel", "s", "min (ME)", "max (ME)"]
    rows: list[list[str]] = []
    csv_rows: list[list[str]] = []
    for label, flank in order:
        first = next(t[(label, flank)] for t in tables.values() if (label, flank) in t)
        digits = _digits(first.unit)
        row = [_symbol(first.quantity, label), flank, first.unit]
        csv_row = [label, first.quantity or "", flank, first.unit]
        for table in tables.values():
            entry = table.get((label, flank))
            if entry is None:
                row += ["–"] * 5
                csv_row += [""] * 7
                continue
            row += [
                str(entry.count),
                _n(entry.mean, digits),
                _n(entry.standard_deviation, digits),
                f"{_n(entry.minimum, digits)} ({entry.me_of_minimum})",
                f"{_n(entry.maximum, digits)} ({entry.me_of_maximum})",
            ]
            csv_row += [
                str(entry.count),
                repr(entry.mean),
                repr(entry.standard_deviation),
                repr(entry.minimum),
                entry.me_of_minimum,
                repr(entry.maximum),
                entry.me_of_maximum,
            ]
        rows.append(row)
        csv_rows.append(csv_row)
    lines.extend(_table(columns, rows))
    csv_columns = ["label", "quantity", "flank", "unit"]
    for name in tables:
        csv_columns += [
            f"{name}_{c}" for c in ("n", "mean", "sd", "min", "me_min", "max", "me_max")
        ]
    return "\n".join(lines) + "\n", csv_columns, csv_rows


def repeatability_markdown(part_kind: str, results: Sequence[gina.GinaResult]) -> str:
    rows = gina.repeatability(results)
    lines = [f"# Wiederholbarkeit der GINA-Messung, {PART_LABELS[part_kind]}", ""]
    if not rows:
        lines.append("Kein Teil wurde mehr als einmal gemessen.")
        return "\n".join(lines) + "\n"
    lines.append(
        "Spannweite (max − min) eines Werts über alle Messungen desselben Teils (verschiedene "
        "Runden oder Wiederholungen am selben Tag; Dateien in der Reihenfolge Datum, Name)."
    )
    lines.append("")
    by_label: dict[tuple[str, str, str], list[float]] = {}
    for r in rows:
        by_label.setdefault((r.label, r.flank, r.unit), []).append(r.spread)
    lines.extend(["## Spannweite je Größe über alle wiederholten Teile", ""])
    lines.extend(
        _table(
            ["Größe", "Flanke", "Einheit", "Teile", "Spannweite Mittel", "Spannweite max"],
            [
                [
                    label,
                    flank,
                    unit,
                    str(len(values)),
                    _n(sum(values) / len(values), _digits(unit)),
                    _n(max(values), _digits(unit)),
                ]
                for (label, flank, unit), values in by_label.items()
            ],
        )
    )
    lines.extend(["", "## Je Teil", ""])
    lines.extend(
        _table(
            ["ME", "Größe", "Flanke", "Einheit", "n", "Werte", "Spannweite"],
            [
                [
                    r.me,
                    r.label,
                    r.flank,
                    r.unit,
                    str(r.count),
                    ", ".join(_n(v, _digits(r.unit)) for v in r.values),
                    _n(r.spread, _digits(r.unit)),
                ]
                for r in rows
            ],
        )
    )
    return "\n".join(lines) + "\n"


def exceedances(result: gina.GinaResult) -> list[list[str]]:
    """Values whose magnitude lies above the tolerance of the measuring program:
    ``[ME, variant, label, flank, value, tolerance]``."""
    limits = {t.label: t for t in result.tolerances}
    rows: list[list[str]] = []

    def check(label: str, flank: str, value: float | None) -> None:
        tolerance = limits.get(label)
        if tolerance is None or value is None:
            return
        limit = tolerance.left_um
        if flank.startswith("rechts") and tolerance.right_um is not None:
            limit = tolerance.right_um
        if abs(value) > limit:
            rows.append([result.me, result.variant or "", label, flank, _n(value, 1), _n(limit, 1)])

    for label, name in (("fHa", "profile_slope_deviation"), ("fHb", "helix_slope_deviation")):
        deviation = result.deviation(name)
        for flank in FLANKS:
            for tooth in deviation.flank(flank).per_tooth:
                check(label, f"{flank} Zahn {tooth.tooth}", tooth.value_um)
    by_label = {value.label: value for value in result.pitch}
    for label, pitch_label in (
        ("fp", "fp max"),
        ("fu", "fu max"),
        ("Fp", "Fp"),
        ("Fpz/8", "Fpz/8"),
    ):
        value = by_label.get(pitch_label)
        if value is not None:
            check(label, "links", value.left_um)
            check(label, "rechts", value.right_um)
    if "Fr" in by_label:
        check("Fr", "", by_label["Fr"].value_um)
    if "Rs" in by_label:
        check("Rs", "", by_label["Rs"].value_um)
    return rows


def tolerances_markdown(part_kind: str, results: Sequence[gina.GinaResult]) -> str:
    lines = [f"# Toleranzen laut Messprotokoll, {PART_LABELS[part_kind]}", ""]
    lines.append(
        "Werte, gegen die das Messprogramm des P40 geprüft hat (Kopfzeilen der .mew-Dateien). Die "
        "Stufe ist eine Einstellung des Programms, die Norm ist in der Datei nicht genannt; hier wird "
        "keine Qualitätsstufe berechnet. Fpz/8, Fr und Rs sind Größen des Messprogramms ohne "
        "Normeintrag (Fpz/8 = gleitende Teilungs-Spannenabweichung, nicht F_pk; die Norm nennt "
        "keine Toleranz für F_pSk). f_Hβ ist auf die Zahnbreite b bezogen (Einstellung 179 "
        "BZGFL 1: Z, DIN ISO 1328-1 bezieht f_Hβ auf L_β), f_Hα auf den Auswertebereich M1 bis "
        "M2 (Einstellung 180). Überschreitungen: Betrag des Werts über dem Wert des Messprogramms "
        "(Steigungsabweichungen je Zahn, Teilung und Rundlauf je Datei)."
    )
    lines.append("")
    seen: Counter[tuple[str, str | None, float, float | None, int | None]] = Counter()
    for result in results:
        for t in result.tolerances:
            seen[(t.label, t.quantity, t.left_um, t.right_um, t.grade)] += 1
    rows = [
        [
            label,
            _symbol(name, label),
            _n(left, 1),
            _n(right, 1),
            "–" if grade is None else str(grade),
            str(count),
        ]
        for (label, name, left, right, grade), count in sorted(
            seen.items(), key=lambda kv: kv[0][0]
        )
    ]
    lines.extend(
        _table(["Label", "Symbol", "links in µm", "rechts in µm", "Stufe", "Dateien"], rows)
    )
    exceed = [row for result in results for row in exceedances(result)]
    lines.extend(["", "## Überschreitungen", ""])
    if exceed:
        per_label: dict[str, tuple[int, set[str]]] = {}
        for row in exceed:
            count, files = per_label.get(row[2], (0, set()))
            per_label[row[2]] = (count + 1, files | {row[0] + row[1]})
        lines.extend(
            _table(
                ["Label", "Werte über der Toleranz", "Dateien (von " + str(len(results)) + ")"],
                [
                    [label, str(count), str(len(files))]
                    for label, (count, files) in sorted(per_label.items())
                ],
            )
        )
        lines.append("")
        lines.extend(
            _table(["ME", "Variante", "Label", "Flanke", "Wert in µm", "Toleranz in µm"], exceed)
        )
    else:
        lines.append("Keine.")
    return "\n".join(lines) + "\n"


def relief_markdown(results: Sequence[gina.GinaResult]) -> str:
    lines = ["# Kopfrücknahme der Stahlritzel (GINA fKo)", ""]
    lines.append(
        "fKo je Zahn und Flanke in µm (negativ = Material am Kopf abgetragen); Beginn und Ende der "
        "Zone aus den Kopfzeilen 431/432, Länge L_Cαa als Differenz der Krümmungsradien "
        "(Wälzlänge, ISO 21771 Gl. (17))."
    )
    lines.append("")
    rows: list[list[str]] = []
    for r in results:
        if r.tip_relief is None:
            continue
        relief = r.tip_relief
        for flank in FLANKS:
            stats = relief.deviations.flank(flank)
            rows.append(
                [
                    r.me,
                    r.variant or "",
                    r.measured_on,
                    flank,
                    ", ".join(f"Z{t.tooth}: {_n(t.value_um, 1)}" for t in stats.per_tooth),
                    _n(stats.mean_um, 1),
                    _n(relief.start_diameter_mm, 3),
                    _n(relief.end_diameter_mm, 3),
                    _n(relief.tip_relief_length_mm, 3),
                ]
            )
    if not rows:
        lines.append("Keine Rücknahme in den Dateien.")
        return "\n".join(lines) + "\n"
    lines.extend(
        _table(
            [
                "ME",
                "Variante",
                "Datum",
                "Flanke",
                "fKo je Zahn in µm",
                "fKo Mittel in µm",
                "Beginn d in mm",
                "Ende d in mm",
                rp.quantity_label("tip_relief_length"),
            ],
            rows,
        )
    )
    return "\n".join(lines) + "\n"


def window_markdown(
    part_kind: str, tables: Sequence[tuple[gina.GinaResult, MkaFile]], window: tuple[int, int]
) -> str:
    first, last = window
    lines = [f"# Zähne {first} bis {last} (Ausfallfenster), {PART_LABELS[part_kind]}", ""]
    lines.append(
        "Teilungs- und Rundlaufwerte der Zähne im Fenster gegen die übrigen Zähne (alle Zähne aus "
        "der .mka-Tabelle). Spannweite = max − min von F_pi im Fenster (die Teilungs-"
        "Sektorabweichung dieses einen Sektors nach Anhang D.2); Rang 1 = das Fenster hat die "
        "größte Spannweite aller gleich langen Fenster um das Rad. Die beiden letzten Spalten "
        "nennen den Zahn mit dem größten Betrag über das ganze Rad."
    )
    lines.append("")
    rows: list[list[str]] = []
    for result, mka in tables:
        for table in gina.tooth_tables(mka):
            w = gina.window_statistics(table, first, last)
            rows.append(
                [
                    result.me,
                    result.variant or "",
                    table.flank,
                    _n(w.mean_abs_f_pi_inside_um, 1),
                    _n(w.mean_abs_f_pi_outside_um, 1),
                    _n(w.mean_r_i_inside_um, 1),
                    _n(w.mean_r_i_outside_um, 1),
                    _n(w.spread_F_pi_inside_um, 1),
                    f"{w.spread_rank} von {len(table.teeth)}",
                    str(w.tooth_of_max_abs_f_pi),
                    str(w.tooth_of_max_abs_F_pi),
                ]
            )
    lines.extend(
        _table(
            [
                "ME",
                "Variante",
                "Flanke",
                "|f_pi| innen",
                "|f_pi| außen",
                "r_i innen",
                "r_i außen",
                "Spannweite F_pi innen",
                "Rang",
                "Zahn max |f_pi| (Rad)",
                "Zahn max |F_pi| (Rad)",
            ],
            rows,
        )
    )
    lines.extend(["", "Alle Werte in µm."])
    return "\n".join(lines) + "\n"


def sectors_markdown(part_kind: str, tables: Sequence[tuple[gina.GinaResult, MkaFile]]) -> str:
    lines = [f"# Teilungs-Sektorabweichung, {PART_LABELS[part_kind]}", ""]
    lines.append(
        "Aus den Teilungstabellen der .mka je Flanke mit k = z/8 (nächste ganze Zahl): Fpz/8 des "
        "Messprogramms (erster minus letzter Wert von F_pi, größter Betrag über alle z Sektoren von "
        "k Teilungen; nachgerechnet gegen die Datei), F_pk nach DIN ISO 1328-1 Anhang D.2 (größter "
        "minus kleinster Wert innerhalb eines Sektors, größter über alle z Sektoren) und F_pSk nach "
        "Anhang D.4 (erster minus letzter Wert, z/k aufeinanderfolgende Sektoren). Die Toleranz der "
        "Datei (Codes 216/217) gilt für Fpz/8; F_pk kann darüber liegen, wo Fpz/8 es nicht tut."
    )
    lines.append("")
    rows: list[list[str]] = []
    above_program = above_norm = 0
    for result, mka in tables:
        printed = {p.label: p for p in result.pitch}.get("Fpz/8")
        tolerance = {t.label: t for t in result.tolerances}.get("Fpz/8")
        for table in gina.tooth_tables(mka):
            values = gina.sector_values(table)
            file_value = None
            if printed is not None:
                file_value = printed.left_um if table.flank == "links" else printed.right_um
            limit = None
            if tolerance is not None:
                limit = tolerance.left_um if table.flank == "links" else tolerance.right_um
            if limit is not None:
                above_program += values.sliding_span_um > limit
                above_norm += values.F_pk_um > limit
            rows.append(
                [
                    result.me,
                    result.variant or "",
                    table.flank,
                    str(values.k),
                    _n(file_value, 1),
                    _n(values.sliding_span_um, 1),
                    _n(values.F_pk_um, 1),
                    _n(values.F_pSk_um, 1),
                    _n(limit, 1),
                ]
            )
    lines.extend(
        _table(
            [
                "ME",
                "Variante",
                "Flanke",
                "k",
                "Fpz/8 Datei",
                "Fpz/8 nachgerechnet",
                "F_pk (D.2)",
                "F_pSk (D.4)",
                "Toleranz Fpz/8",
            ],
            rows,
        )
    )
    lines.extend(
        [
            "",
            f"Alle Werte in µm. Über der Toleranz des Programms: Fpz/8 in {above_program} von "
            f"{len(rows)} Flanken, F_pk in {above_norm}.",
        ]
    )
    return "\n".join(lines) + "\n"


def plot_teeth(
    result: gina.GinaResult, mka: MkaFile, window: tuple[int, int] | None, out: Path
) -> list[Path]:
    import matplotlib.pyplot as plt

    tables = gina.tooth_tables(mka)
    figure, axes = new_figure("full", 0.9, rows=3, sharex=True)
    series: tuple[tuple[str, Callable[[gina.ToothTable], tuple[float, ...]]], ...] = (
        ("individual_single_pitch_deviation", lambda t: t.f_pi_um),
        ("individual_cumulative_pitch_deviation", lambda t: t.F_pi_um),
        ("individual_radial_measurement", lambda t: t.r_i_um),
    )
    for axis, (name, pick) in zip(axes, series, strict=True):
        for table in tables:
            axis.plot(table.teeth, pick(table), label=f"Flanke {table.flank}", markersize=2.5)
        axis.set_ylabel(symbol_label(quantity(name).symbol or name, "µm"))
        axis.axhline(0.0, color="#000000", linewidth=0.3)
        if window is not None:
            axis.axvspan(
                window[0] - 0.5,
                window[1] + 0.5,
                color="#cccccc",
                alpha=0.5,
                linewidth=0.0,
                label="Ausfallfenster" if axis is axes[0] else None,
            )
        decimal_comma(axis, which="y")
    axes[-1].set_xlabel("Zahn")
    axes[-1].set_xticks(range(1, result.number_of_teeth + 1, 3))
    name_tag = f"{result.me}{result.variant or ''}"
    legend_outside(figure, axes[0], where="bottom", ncol=3)
    figure.suptitle(f"{name_tag}: Teilung und Rundlauf je Zahn ({result.measured_on})")
    written = save(figure, out / f"zaehne_{name_tag}")
    plt.close(figure)
    return written


def plot_curves(result: gina.GinaResult, mka: MkaFile, block: str, out: Path) -> list[Path]:
    import matplotlib.pyplot as plt

    figure, axes = new_figure("full", 0.5, cols=2, sharey=True)
    for axis, flank in zip(axes, FLANKS, strict=True):
        curves = [
            c for c in mka.curves if c.block == block and c.flank == flank and c.tooth_tag == ""
        ]
        for curve in sorted(curves, key=lambda c: c.tooth):
            x = gina.curve_abscissa(mka, curve)
            y = [float("nan") if v is None else v for v in gina.curve_values_din(curve)]
            axis.plot(x, y, marker="", label=f"Zahn {curve.tooth}")
        axis.set_title(f"Flanke {flank}")
        if block == "Profil":
            axis.set_xlabel(symbol_label("d", "mm"))
            for d in result.evaluation_diameters_mm:
                axis.axvline(d, color="#000000", linewidth=0.3)
        else:
            axis.set_xlabel(symbol_label("b", "mm"))
        decimal_comma(axis)
    axes[0].set_ylabel("Abweichung in µm (Vorzeichen wie die Messwerte)")
    legend_outside(figure, axes[0], where="bottom", ncol=5)
    name_tag = f"{result.me}{result.variant or ''}"
    title, stem = ("Profil", "profil") if block == "Profil" else ("Flankenlinie", "flankenlinie")
    figure.suptitle(f"{name_tag}: {title} der gemessenen Zähne ({result.measured_on})")
    written = save(figure, out / f"{stem}_{name_tag}")
    plt.close(figure)
    return written


def _curve_file(part: MeasuredPart, value_file: MeasurementFile) -> MeasurementFile | None:
    """The ``.mka`` with the same stem as the ``.mew``."""
    stem = Path(value_file.path).stem
    for file in part.of_kind("mka"):
        if Path(file.path).stem == stem:
            return file
    return None


def run_gina(
    input_dir: Path,
    out: Path,
    *,
    parts: Sequence[gina.Part] = ("wheel", "pinion"),
    me_filter: Sequence[str] | None = None,
    rounds: str = "latest",
    plots: bool = True,
    curves: bool = False,
) -> list[Path]:
    if rounds not in ("latest", "all"):
        raise InputRangeError(f"rounds must be 'latest' or 'all', got {rounds!r}")
    inventory = scan_folder(input_dir)
    decisions: dict[str, Any] = load_measurement_parts()
    root = Path(inventory.root)
    written: list[Path] = []
    for part_kind in parts:
        triples = gina_results(inventory, part_kind, me_filter)
        if not triples:
            continue
        folder = out / part_kind
        folder.mkdir(parents=True, exist_ok=True)
        results = [r for _, _, r in triples]
        chosen = gina.latest_per_part(results) if rounds == "latest" else tuple(results)
        group_of = {p.me: p.group for p in inventory.parts if p.part == part_kind}
        groups: dict[str, list[gina.GinaResult]] = {}
        for result in chosen:
            groups.setdefault(group_of[result.me], []).append(result)
        text, csv_columns, csv_rows = scatter_markdown(part_kind, dict(sorted(groups.items())))
        files = [
            ("tabelle_streuung.md", text),
            ("tabelle_streuung.csv", rp.csv_text(csv_columns, csv_rows)),
            ("wiederholbarkeit.md", repeatability_markdown(part_kind, results)),
            ("toleranzen_protokoll.md", tolerances_markdown(part_kind, results)),
        ]
        if part_kind == "pinion":
            files.append(("kopfruecknahme_ritzel.md", relief_markdown(results)))
        window_cfg = decisions.get("failure_window", {}).get(part_kind)
        window = (
            (int(window_cfg["first_tooth"]), int(window_cfg["last_tooth"])) if window_cfg else None
        )
        with_curves: list[tuple[gina.GinaResult, MkaFile]] = []
        for part, file, result in triples:
            if result not in chosen:
                continue
            curve_file = _curve_file(part, file)
            if curve_file is not None:
                with_curves.append((result, load_mka(root / curve_file.path)))
        if window is not None and with_curves:
            files.append(("fenster_zaehne.md", window_markdown(part_kind, with_curves, window)))
        if with_curves:
            files.append(("teilungssektoren.md", sectors_markdown(part_kind, with_curves)))
        for name, content in files:
            path = folder / name
            path.write_text(content, encoding="utf-8", newline="\n")
            written.append(path)
        if not plots:
            continue
        apply_plot_style()
        for result, mka in with_curves:
            written += plot_teeth(result, mka, window, folder)
            if curves:
                written += plot_curves(result, mka, "Profil", folder)
                written += plot_curves(result, mka, "Flankenlinie", folder)
    return written


# ---- contour -----------------------------------------------------------------------------------


ContourItem = tuple[MeasuredPart, MeasurementFile, ContourScan, cs.ScanEvaluation]
SIDE_LABELS = {"right": "rechts (+x)", "left": "links (−x)"}
SHAPE_LABELS = {"arc": "Bogen", "chamfer": "Fase"}


def _generation(case: str) -> GenerationResult:
    return compute_generation(pair_input_from_ste(load_ste(data.stplus_input_path(case))).pair)


@dataclass(frozen=True)
class GinaSize:
    """Tip and root radius of a part from its GINA files of one measurement round."""

    tip_radius_mm: float | None
    root_radius_mm: float | None
    measurement_round: int | None
    files: tuple[str, ...]


GinaSizes = dict[str, GinaSize]
"""ME → the GINA sizes of the part."""


def gina_sizes(
    inventory: Inventory, part_kind: ct.Role, me_filter: Sequence[str] | None = None
) -> GinaSizes:
    """Tip and root radius of every part of the kind from its GINA measurements of the EARLIEST
    measurement round (``Kopf m`` and ``Fuß m`` of the ``.mew`` files of that round, averaged
    over the repeats), the state nearest to the unworn contour scan; the files used are named.
    None where no file of the round holds the size; parts without a GINA file are absent."""
    rounds: dict[str, dict[int, list[tuple[str, float | None, float | None]]]] = {}
    for part, file, result in gina_results(inventory, part_kind, me_filter):
        sizes: list[float | None] = []
        for label in ("Kopf", "Fuß"):
            try:
                sizes.append(0.5 * result.size(label).mean_mm)
            except InputRangeError:
                sizes.append(None)
        key = file.measurement_round if file.measurement_round is not None else 0
        rounds.setdefault(part.me, {}).setdefault(key, []).append((file.path, sizes[0], sizes[1]))
    out: GinaSizes = {}
    for me, by_round in rounds.items():
        earliest = min(by_round)
        entries = by_round[earliest]
        tips = [t for _, t, _ in entries if t is not None]
        roots = [r for _, _, r in entries if r is not None]
        out[me] = GinaSize(
            tip_radius_mm=sum(tips) / len(tips) if tips else None,
            root_radius_mm=sum(roots) / len(roots) if roots else None,
            measurement_round=earliest if earliest else None,
            files=tuple(path for path, _, _ in entries),
        )
    return out


def contour_evaluations(
    inventory: Inventory,
    part_kind: ct.Role,
    geometry: cs.ScanGeometry,
    settings: cs.FitSettings,
    me_filter: Sequence[str] | None = None,
    *,
    include_coarse: bool = False,
    gina: GinaSizes | None = None,
) -> list[ContourItem]:
    """Every contour scan of the part kind evaluated, in the order of the inventory. With
    ``gina`` the axis of every scan of a part with a GINA tip diameter is constrained to that
    tip radius (``contour_scan.constrain_axis``, MEAS-10); parts without one keep the free axis."""
    root = Path(inventory.root)
    out: list[ContourItem] = []
    for part in inventory.parts:
        if part.part != part_kind or (me_filter and part.me not in me_filter):
            continue
        size = (gina or {}).get(part.me)
        tip_radius = size.tip_radius_mm if size is not None else None
        for file in sorted(part.of_kind("contour"), key=lambda f: (f.tooth or 0, f.path)):
            coarse = any("coarse" in note for note in file.anomalies)
            if coarse and not include_coarse:
                continue
            if file.after_test:
                continue  # scans after the running test belong to the wear comparison (M5)
            for scan in load_contour_scans(root / file.path):
                evaluation = cs.evaluate_scan(scan, geometry, settings, tip_radius_mm=tip_radius)
                out.append((part, file, scan, evaluation))
    return out


def _raw(value: float | None) -> str:
    """A number for the CSV as repr, or empty."""
    return "" if value is None else repr(value)


def _hand_label(hand: int) -> str:
    return "links (−x)" if hand > 0 else "rechts (+x)"


def contour_tables(
    part_kind: str,
    items: Sequence[ContourItem],
    geometry: cs.ScanGeometry,
    gina: GinaSizes | None = None,
) -> dict[str, str]:
    """``bericht.md`` and the CSV tables of one part kind; ``gina`` adds the GINA tip and root
    radii of the parts beside the scan values."""
    gina = gina or {}
    axis_columns = [
        "me",
        "scan",
        "axis",
        "tip_radius_constraint_mm",
        "radial_shift_um",
        "rms_flank_free_um",
        "rms_flank_um",
        "centre_x_mm",
        "centre_y_mm",
        "tip_radius_median_mm",
        "tip_radius_mean_mm",
        "root_radius_median_mm",
        "gina_tip_radius_mm",
        "gina_root_radius_mm",
        "gina_round",
        "gina_files",
    ]
    axis_rows: list[list[str]] = []
    for part, _file, scan, ev in items:
        fit = ev.fit
        size = gina.get(part.me)
        bound = fit.tip_radius_constraint_mm is not None
        axis_rows.append(
            [
                part.me,
                scan.name,
                "gina_tip" if bound else "free",
                _raw(fit.tip_radius_constraint_mm),
                repr(1000.0 * fit.radial_shift_mm) if bound else "",
                _raw(fit.rms_flank_free_um),
                repr(fit.rms_flank_um),
                repr(fit.centre_mm[0]),
                repr(fit.centre_mm[1]),
                _raw(median(fit.tip_radius_mm) if fit.tip_radius_mm else None),
                _raw(
                    sum(fit.tip_radius_mm) / len(fit.tip_radius_mm) if fit.tip_radius_mm else None
                ),
                _raw(median(fit.root_radius_mm) if fit.root_radius_mm else None),
                _raw(size.tip_radius_mm if size is not None else None),
                _raw(size.root_radius_mm if size is not None else None),
                ""
                if size is None or size.measurement_round is None
                else str(size.measurement_round),
                "; ".join(size.files) if size is not None else "",
            ]
        )
    corner_columns = [
        "me",
        "scan",
        "block",
        "z_mm",
        "tooth_file",
        "tip_index",
        "side",
        "tip_radius_mm",
        "interior_angle_deg",
        "points",
        "arc_radius_mm",
        "arc_low_mm",
        "arc_high_mm",
        "arc_rms_um",
        "chamfer_length_mm",
        "chamfer_low_mm",
        "chamfer_high_mm",
        "chamfer_rms_um",
        "sharp_rms_um",
        "better",
        "cut_back_um",
        "tangent_flank_mm",
        "tangent_tip_mm",
    ]
    relief_columns = [
        "me",
        "scan",
        "flank_start",
        "flank_stop",
        "side",
        "rms_fit_um",
        "relief_start_r_mm",
        "relief_at_tip_um",
        "ramp_start_r_mm",
        "ramp_C_a_tip_um",
        "ramp_C_a_nominal_um",
        "ramp_slope_um_per_mm",
        "ramp_rms_um",
    ]
    thickness_columns = [
        "me",
        "scan",
        "tooth",
        "s_b_mm",
        "s_b_minus_generated_um",
        "s_b_minus_nominal_um",
    ]
    pitch_columns = [
        "me",
        "scan",
        "first_flank",
        "second_flank",
        "side",
        "pitch_deg",
        "pitch_minus_nominal_deg",
    ]
    corner_rows: list[list[str]] = []
    relief_rows: list[list[str]] = []
    thickness_rows: list[list[str]] = []
    pitch_rows: list[list[str]] = []
    nominal_pitch = 360.0 / geometry.number_of_teeth
    for part, file, scan, ev in items:
        for c in ev.corners:
            corner_rows.append(
                [
                    part.me,
                    scan.name,
                    scan.block,
                    repr(scan.z_mm),
                    _cell(file.tooth),
                    str(c.tip_index),
                    c.side,
                    repr(c.tip_radius_mm),
                    repr(c.interior_angle_deg),
                    str(c.points_in_window),
                    repr(c.arc_radius_mm),
                    repr(c.arc_radius_low_mm),
                    repr(c.arc_radius_high_mm),
                    repr(c.arc_rms_um),
                    repr(c.chamfer_length_mm),
                    repr(c.chamfer_length_low_mm),
                    repr(c.chamfer_length_high_mm),
                    repr(c.chamfer_rms_um),
                    repr(c.sharp_rms_um),
                    c.better_shape,
                    repr(c.cut_back_um),
                    repr(c.tangent_flank_mm),
                    repr(c.tangent_tip_mm),
                ]
            )
        for r in ev.reliefs:
            relief_rows.append(
                [
                    part.me,
                    scan.name,
                    str(r.run.start),
                    str(r.run.stop),
                    "left" if r.hand > 0 else "right",
                    _raw(r.rms_fit_um),
                    repr(r.relief_start_r_mm),
                    _raw(r.relief_at_tip_um),
                    _raw(r.ramp_start_r_mm),
                    _raw(r.ramp_at_tip_um),
                    _raw(r.ramp_at_nominal_tip_um),
                    _raw(r.ramp_slope_um_per_mm),
                    _raw(r.ramp_rms_um),
                ]
            )
        for t in ev.teeth:
            thickness_rows.append(
                [
                    part.me,
                    scan.name,
                    str(t.tooth),
                    repr(t.s_b_mm),
                    repr(1000.0 * (t.s_b_mm - geometry.base_tooth_thickness_generated_mm)),
                    repr(1000.0 * (t.s_b_mm - geometry.base_tooth_thickness_nominal_mm)),
                ]
            )
        for pitch in ev.pitches:
            pitch_rows.append(
                [
                    part.me,
                    scan.name,
                    str(pitch.first_flank),
                    str(pitch.second_flank),
                    "left" if pitch.hand > 0 else "right",
                    repr(pitch.pitch_deg),
                    repr(pitch.pitch_deg - nominal_pitch),
                ]
            )
    lines = [f"# Konturscans, {PART_LABELS[part_kind]}", ""]
    lines.append(
        f"Nenngeometrie der STplus-Erzeugung (kst-E): z = {geometry.number_of_teeth}, "
        f"r_b = {_n(geometry.r_b, 4)} mm, r_a = {_n(geometry.r_a, 4)} mm, "
        f"r_Ff = {_n(geometry.r_ff, 4)} mm; s_b Nenn {_n(geometry.base_tooth_thickness_nominal_mm, 4)} mm, "
        f"mit Zahndickenabmaß (erzeugt) {_n(geometry.base_tooth_thickness_generated_mm, 4)} mm; "
        f"Teilung 360°/z = {_n(nominal_pitch, 4)}°. Evolventen mit dem Nenn-Grundkreis "
        f"(ein Drehwinkel je Flanke), ein Radius je Kopfkreis; Fit zwischen r_Ff + "
        f"{_n(items[0][3].settings.flank_margin_above_root_form_mm, 2)} mm und "
        f"{_n(items[0][3].settings.flank_margin_below_tip_mm, 2)} mm unter dem Kopfkreis. Achse: aus den "
        "Flanken gefittet und, wo GINA den Kopfkreis desselben Teils gemessen hat, entlang der Zahnmitte so "
        "verschoben, dass der Median der Kopfradien dem GINA-Kopfkreis entspricht (Spalte Achse; ohne "
        "GINA-Messung bleibt die Achse frei; Median, damit ein als Kopfbogen erkannter Lauf, der keiner "
        "ist, die Achse nicht mitzieht; GINA-Werte aus der frühesten Messrunde des Teils, Dateien in "
        "achse.csv). Je Teil stehen d_a und d_f als Median über die Bögen und Lücken "
        "aller Scans. Grund: Der freie Fit mit dem Nenn-Grundkreis nimmt eine reale "
        "Profilwinkelabweichung des Teils als radialen Achsversatz auf (Räder: f_Hα +10 bis +13 µm, Versatz "
        "im Median 52 µm zum Zahn hin, Kopf- und Fußradius der Scans damit rund 50 µm zu klein, s_b rund "
        "28 µm zu dünn; MEAS-10, 2026-10-12); die RMS des gebundenen Fits ist die reale Profilabweichung. "
        "Kanten: tangentialer "
        "Bogen (Radius ρ) und symmetrische Fase (Schenkellänge c) über ein Größenraster, besser = kleinerer RMS; "
        "Band = Größen mit RMS höchstens 10 % über dem Minimum. Rücknahme: Gerade über der Wälzlänge "
        "(linear, ISO 21771), Material fehlt positiv; an einem Rad mit Kopfrundung liest diese "
        "Gerade die Rundung als Rücknahme (der Betrag ist dann kein C_a der Zeichnung)."
    )
    lines.extend(["", "## Je Scan", ""])
    rows: list[list[str]] = []
    for part, _file, scan, ev in items:
        s_b = ", ".join(_n(t.s_b_mm, 4) for t in ev.teeth) or "–"
        reliefs = [
            r.ramp_at_nominal_tip_um for r in ev.reliefs if r.ramp_at_nominal_tip_um is not None
        ]
        arcs = [c.arc_radius_mm for c in ev.corners]
        chamfers = [c.chamfer_length_mm for c in ev.corners]
        better = sum(1 for c in ev.corners if c.better_shape == "chamfer")
        rows.append(
            [
                part.me,
                scan.name,
                scan.block,
                _n(scan.z_mm, 3),
                str(ev.points),
                "ja" if ev.coarse else "nein",
                f"{_n(ev.fit.centre_mm[0], 4)}, {_n(ev.fit.centre_mm[1], 4)}",
                "GINA-Kopfkreis" if ev.fit.tip_radius_constraint_mm is not None else "frei",
                _n(1000.0 * ev.fit.radial_shift_mm, 0)
                if ev.fit.tip_radius_constraint_mm is not None
                else "–",
                ", ".join(_n(v, 4) for v in ev.fit.tip_radius_mm),
                ", ".join(_n(v, 4) for v in ev.fit.root_radius_mm) or "–",
                _n(ev.fit.rms_flank_um, 1),
                _n(ev.fit.rms_flank_free_um, 1) if ev.fit.rms_flank_free_um is not None else "–",
                _n(ev.fit.rms_tip_um, 1),
                s_b,
                _n(sum(p.pitch_deg for p in ev.pitches) / len(ev.pitches), 4)
                if ev.pitches
                else "–",
                _n(sum(reliefs) / len(reliefs), 1) if reliefs else "–",
                _n(sum(arcs) / len(arcs), 3) if arcs else "–",
                _n(sum(chamfers) / len(chamfers), 3) if chamfers else "–",
                f"{better} von {len(ev.corners)}",
            ]
        )
    lines.extend(
        _table(
            [
                "ME",
                "Scan",
                "Block",
                "z in mm",
                "Punkte",
                "grob",
                "Achse x, y in mm",
                "Achse",
                "Versatz radial in µm",
                "Kopfradien in mm",
                "Fußradien in mm",
                "RMS Flanken in µm",
                "RMS Flanken frei in µm",
                "RMS Kopf in µm",
                "s_b je Zahn in mm",
                "Teilung Mittel in °",
                "Gerade am Nenn-Kopfkreis Mittel in µm",
                "ρ Bogen Mittel in mm",
                "c Fase Mittel in mm",
                "Fase besser",
            ],
            rows,
        )
    )
    lines.extend(["", "## Je Teil (alle Scans)", ""])
    by_me: dict[str, list[cs.ScanEvaluation]] = {}
    groups_of: dict[str, str] = {}
    for part, _, _, ev in items:
        by_me.setdefault(part.me, []).append(ev)
        groups_of[part.me] = part.group
    summary: list[list[str]] = []
    for me, evaluations in by_me.items():
        tips = [v for ev in evaluations for v in ev.fit.tip_radius_mm]
        roots = [v for ev in evaluations for v in ev.fit.root_radius_mm]
        shifts = [
            1000.0 * ev.fit.radial_shift_mm
            for ev in evaluations
            if ev.fit.tip_radius_constraint_mm is not None
        ]
        size = gina.get(me)
        g_tip = size.tip_radius_mm if size is not None else None
        g_root = size.root_radius_mm if size is not None else None
        s_bs = [t.s_b_mm for ev in evaluations for t in ev.teeth]
        reliefs = [
            r.ramp_at_nominal_tip_um
            for ev in evaluations
            for r in ev.reliefs
            if r.ramp_at_nominal_tip_um is not None
        ]
        arcs = [c.arc_radius_mm for ev in evaluations for c in ev.corners]
        summary.append(
            [
                me,
                GROUP_LABELS.get(groups_of[me], groups_of[me]),
                str(len(evaluations)),
                f"{len(shifts)} von {len(evaluations)}" if shifts else "frei",
                _n(sum(shifts) / len(shifts), 0) if shifts else "–",
                _n(2.0 * median(tips), 4) if tips else "–",
                _n(2.0 * g_tip, 4) if g_tip is not None else "–",
                _n(2.0 * median(roots), 4) if roots else "–",
                _n(2.0 * g_root, 4) if g_root is not None else "–",
                _n(sum(s_bs) / len(s_bs), 4) if s_bs else "–",
                _n(1000.0 * (sum(s_bs) / len(s_bs) - geometry.base_tooth_thickness_generated_mm), 0)
                if s_bs
                else "–",
                _n(sum(reliefs) / len(reliefs), 1) if reliefs else "–",
                _n(sum(arcs) / len(arcs), 3) if arcs else "–",
                _n(max(arcs), 3) if arcs else "–",
            ]
        )
    lines.extend(
        _table(
            [
                "ME",
                "Gruppe",
                "Scans",
                "Achse an GINA",
                "Versatz radial Mittel in µm",
                "d_a Median in mm",
                "d_a GINA in mm",
                "d_f Median in mm",
                "d_f GINA in mm",
                "s_b Mittel in mm",
                "s_b − erzeugt in µm",
                "Gerade am Nenn-Kopfkreis Mittel in µm",
                "ρ Bogen Mittel in mm",
                "ρ Bogen max in mm",
            ],
            summary,
        )
    )
    return {
        "bericht.md": "\n".join(lines) + "\n",
        "achse.csv": rp.csv_text(axis_columns, axis_rows),
        "kanten.csv": rp.csv_text(corner_columns, corner_rows),
        "kopfruecknahme.csv": rp.csv_text(relief_columns, relief_rows),
        "zahndicke.csv": rp.csv_text(thickness_columns, thickness_rows),
        "teilung.csv": rp.csv_text(pitch_columns, pitch_rows),
    }


def _frame_labels(frames: Sequence[cs.ToothFrame], tooth: int | None) -> list[str]:
    """The middle tooth of a scan is the tooth of the file name (user, 2026-10-11), the others
    are its neighbours on the +x side (scanned first) and the −x side."""
    middle = len(frames) // 2
    named = f"Zahn {tooth}" if tooth is not None else "Zahn ?"
    labels: list[str] = []
    for k in range(len(frames)):
        if k == middle:
            labels.append(named)
        elif k < middle:
            labels.append(f"Nachbar +x ({middle - k})" if middle - k > 1 else "Nachbar +x")
        else:
            labels.append(f"Nachbar −x ({k - middle})" if k - middle > 1 else "Nachbar −x")
    return labels


def plot_overlay(
    frames: Sequence[tuple[str, cs.ToothFrame]],
    outline: Any,
    magnify: float,
    title: str,
    stem: Path,
) -> list[Path]:
    """The measured teeth on the nominal tooth, their deviation magnified normal to it."""
    figure, axes = new_figure("full", 0.72)
    axes.plot(
        outline[:, 0],
        outline[:, 1],
        color="#000000",
        linestyle="-",
        marker="",
        linewidth=0.6,
        label="Sollkontur (STplus-Erzeugung)",
    )
    for label, frame in frames:
        points = cs.overlay_points(frame.as_array(), outline, magnify)
        axes.plot(points[:, 0], points[:, 1], marker="", linewidth=0.9, label=label)
    axes.set_aspect("equal")
    axes.set_xlabel(symbol_label("x", "mm"))
    axes.set_ylabel(symbol_label("y", "mm"))
    axes.set_title(
        f"{title}"
        + chr(10)
        + (
            "Abweichung nicht überhöht"
            if magnify == 1.0
            else f"Abweichung {magnify:g}-fach überhöht normal zur Sollkontur"
        )
    )
    decimal_comma(axes)
    legend_outside(figure, axes, where="bottom", ncol=3)
    written = save(figure, stem)
    import matplotlib.pyplot as plt

    plt.close(figure)
    return written


def plot_corners(evaluation: cs.ScanEvaluation, title: str, stem: Path) -> list[Path]:
    """Every tip corner of a scan at 1:1 in µm with the fitted arc and chamfer."""
    import matplotlib.pyplot as plt
    import numpy as np

    corners = evaluation.corners
    if not corners:
        return []
    cols = min(3, len(corners))
    rows = (len(corners) + cols - 1) // cols
    figure, panels = new_figure(
        "full", 0.3 * rows + 0.1, rows=rows, cols=cols, sharex=True, sharey=True
    )
    axes_list = list(np.atleast_1d(panels).ravel())
    leg = 0.35
    for axis, c in zip(axes_list, corners, strict=False):
        model = c.model()
        window = np.asarray(c.window_points_mm, dtype=float)
        pts = 1000.0 * cs.corner_frame(window, model)
        axis.plot(
            pts[:, 0], pts[:, 1], linestyle="", marker="o", markersize=2.0, label="Messpunkte"
        )
        sharp = 1000.0 * cs.corner_frame(c.model("arc", 0.0).outline(leg), model)
        axis.plot(
            sharp[:, 0],
            sharp[:, 1],
            color="#000000",
            linestyle="-",
            marker="",
            linewidth=0.6,
            label="scharfe Ecke",
        )
        arc = 1000.0 * cs.corner_frame(c.model("arc").outline(leg), model)
        axis.plot(
            arc[:, 0], arc[:, 1], linestyle="-", marker="", linewidth=0.9, label="Bogen (Fit)"
        )
        chamfer = 1000.0 * cs.corner_frame(c.model("chamfer").outline(leg), model)
        axis.plot(
            chamfer[:, 0],
            chamfer[:, 1],
            linestyle="--",
            marker="",
            linewidth=0.9,
            label="Fase (Fit)",
        )
        axis.set_aspect("equal")
        axis.set_xlim(-200.0, 200.0)
        axis.set_ylim(-220.0, 40.0)
        # the panel's name only; the fitted radii, chamfer legs and their RMS stand in the
        # tables and the text (figures carry no titles and no values inside, user 2026-10-17)
        axis.set_title(f"Kopf {c.tip_index} {SIDE_LABELS[c.side]}")
        decimal_comma(axis)
    for axis in axes_list[len(corners) :]:
        axis.set_visible(False)
    for k, axis in enumerate(axes_list[: len(corners)]):
        if k % cols == 0:
            axis.set_ylabel("Längs der Halbierenden in µm")
        if k >= len(corners) - cols:
            axis.set_xlabel("Quer in µm")
    del title  # the part and the tooth name the file and the caption, not the figure
    legend_outside(figure, axes_list[0], where="bottom", ncol=4)
    written = save(figure, stem)
    plt.close(figure)
    return written


def run_contour(
    input_dir: Path,
    out: Path,
    *,
    case: str = "kst_e",
    parts: Sequence[ct.Role] = ("wheel", "pinion"),
    me_filter: Sequence[str] | None = None,
    include_coarse: bool = False,
    magnify: float = 1.0,
    corner_step_mm: float = 0.01,
    corner_max_mm: float = 0.3,
    plots: bool = True,
) -> list[Path]:
    inventory = scan_folder(input_dir)
    generation = _generation(case)
    settings = cs.FitSettings(corner_size_step_mm=corner_step_mm, corner_size_max_mm=corner_max_mm)
    written: list[Path] = []
    for part_kind in parts:
        geometry = cs.scan_geometry(generation, part_kind)
        gina = gina_sizes(inventory, part_kind, me_filter)
        items = contour_evaluations(
            inventory,
            part_kind,
            geometry,
            settings,
            me_filter,
            include_coarse=include_coarse,
            gina=gina,
        )
        if not items:
            continue
        folder = out / part_kind
        folder.mkdir(parents=True, exist_ok=True)
        for name, text in contour_tables(part_kind, items, geometry, gina).items():
            path = folder / name
            path.write_text(text, encoding="utf-8", newline="\n")
            written.append(path)
        if not plots:
            continue
        apply_plot_style()
        outline = cs.nominal_outline(generation, part_kind)
        first_of_group: dict[str, list[tuple[str, cs.ToothFrame]]] = {}
        seen: set[str] = set()
        for part, file, scan, ev in items:
            frames = cs.tooth_frames(scan, ev)
            tag = f"{part.me}_{scan.name}"
            tooth = f"Zahn {file.tooth}" if file.tooth is not None else "Zahn ?"
            written += plot_overlay(
                [
                    (label, f)
                    for label, f in zip(_frame_labels(frames, file.tooth), frames, strict=True)
                ],
                outline,
                magnify,
                f"{part.me} {tooth}, z = {_n(scan.z_mm, 2)} mm",
                folder / f"ueberlagerung_{tag}",
            )
            written += plot_corners(ev, f"{part.me} {tooth}", folder / f"kopfkante_{tag}")
            if frames and part.me not in seen:
                seen.add(part.me)
                middle = frames[len(frames) // 2]
                first_of_group.setdefault(part.group, []).append((f"{part.me} {tooth}", middle))
        for group, frames_of_group in first_of_group.items():
            written += plot_overlay(
                frames_of_group,
                outline,
                magnify,
                f"{PART_LABELS[part_kind]}, {GROUP_LABELS.get(group, group)}",
                folder / f"ueberlagerung_{part_kind}_{group}",
            )
    return written


# ---- roughness ---------------------------------------------------------------------------------


def roughness_tables(
    part_kind: str,
    items: Sequence[tuple[MeasuredPart, rg.RoughnessMeasurement]],
    dropped: int,
) -> dict[str, str]:
    """``tabelle.md``, ``gruppen.md`` and ``rohdaten.csv`` of one part kind."""
    ra_label = rp.quantity_label("arithmetic_mean_roughness")
    rz_label = rp.quantity_label("mean_peak_to_valley_roughness")
    lines = [f"# Rauheit der Zahnflanken, {PART_LABELS[part_kind]}", ""]
    lines.append(
        "Hommel-Etamic-Exporte, je Teil und Flanke drei Spuren; R_a und R_z als Mittel der drei "
        "Spuren, wie das Gerät es druckt (Xq) und gegen die Spuren geprüft. Die gedruckten Protokolle "
        "(PDF) gehören in den Anhang; Kenngrößen jenseits von R_a und R_z laufen nur in rohdaten.csv "
        f"mit, ohne Normeintrag (MEAS-05). {dropped} doppelte Exporte (_neu_) mit gleichen Zahlen "
        "wurden ausgelassen."
    )
    lines.append("")
    rows: list[list[str]] = []
    for part, m in items:
        rows.append(
            [
                part.me,
                GROUP_LABELS.get(part.group, part.group),
                ", ".join(part.batch_labels) or "–",
                m.flank,
                m.measured_on,
                _n(m.R_a_um, 3),
                ", ".join(_n(v, 3) for v in m.R_a_traces_um),
                _n(rg.trace_spread(m, "Ra"), 3),
                _n(m.R_z_um, 3),
                ", ".join(_n(v, 3) for v in m.R_z_traces_um),
                _n(rg.trace_spread(m, "Rz"), 3),
                m.remark or "",
            ]
        )
    lines.extend(
        _table(
            [
                "ME",
                "Gruppe",
                "Chargenlabel",
                "Flanke",
                "Datum",
                ra_label,
                "Spuren R_a in µm",
                "Spannweite R_a in µm",
                rz_label,
                "Spuren R_z in µm",
                "Spannweite R_z in µm",
                "Bemerkung",
            ],
            rows,
        )
    )
    groups: dict[str, list[rg.RoughnessMeasurement]] = {}
    for part, m in items:
        groups.setdefault(part.group, []).append(m)
    group_lines = [f"# Rauheit nach Gruppen, {PART_LABELS[part_kind]}", ""]
    group_lines.append(
        "Mittel, Standardabweichung (n − 1), Minimum und Maximum von R_a und R_z (Mittel der drei "
        "Spuren) über die Teile der Gruppe je Flanke; Spurenspannweite = Mittel über die Teile der "
        "Spannweite der drei Spuren eines Teils (Streuung entlang einer Flanke)."
    )
    group_lines.append("")
    group_rows: list[list[str]] = []
    for group in sorted(groups):
        for stat in rg.statistics(groups[group]):
            group_rows.append(
                [
                    GROUP_LABELS.get(group, group),
                    rp.plain_symbol(quantity(stat.quantity).symbol or stat.parameter)
                    if stat.quantity
                    else stat.parameter,
                    stat.flank,
                    str(stat.count),
                    _n(stat.mean_um, 3),
                    _n(stat.standard_deviation_um, 3),
                    f"{_n(stat.minimum_um, 3)} ({stat.me_of_minimum})",
                    f"{_n(stat.maximum_um, 3)} ({stat.me_of_maximum})",
                    _n(stat.mean_trace_spread_um, 3),
                ]
            )
    group_lines.extend(
        _table(
            [
                "Gruppe",
                "Größe",
                "Flanke",
                "n",
                "Mittel in µm",
                "s in µm",
                "min (ME)",
                "max (ME)",
                "Spurenspannweite Mittel in µm",
            ],
            group_rows,
        )
    )
    columns = ["me", "group", "flank", "measured_on", "measured_at", "remark", "program"]
    raw_names = [name for name, _ in items[0][1].raw]
    csv_rows: list[list[str]] = []
    for part, m in items:
        values = dict(m.raw)
        csv_rows.append(
            [part.me, part.group, m.flank, m.measured_on, m.measured_at, m.remark or "", m.program]
            + [_raw(values.get(name)) for name in raw_names]
        )
    return {
        "tabelle.md": "\n".join(lines) + "\n",
        "gruppen.md": "\n".join(group_lines) + "\n",
        "rohdaten.csv": rp.csv_text(columns + raw_names, csv_rows),
    }


def run_roughness(
    input_dir: Path,
    out: Path,
    *,
    parts: Sequence[str] = ("wheel", "pinion"),
    me_filter: Sequence[str] | None = None,
) -> list[Path]:
    inventory = scan_folder(input_dir)
    root = Path(inventory.root)
    written: list[Path] = []
    for part_kind in parts:
        measurements: list[rg.RoughnessMeasurement] = []
        part_of: dict[str, MeasuredPart] = {}
        for part in inventory.parts:
            if part.part != part_kind or (me_filter and part.me not in me_filter):
                continue
            part_of[part.me] = part
            for file in sorted(part.of_kind("roughness"), key=lambda f: f.path):
                measurements.extend(
                    rg.roughness_measurements(load_roughness_table(root / file.path))
                )
        if not measurements:
            continue
        kept, dropped = rg.dedupe(measurements)
        items = sorted(
            ((part_of[m.me], m) for m in kept), key=lambda pair: (pair[1].me, pair[1].flank)
        )
        folder = out / part_kind
        folder.mkdir(parents=True, exist_ok=True)
        for name, text in roughness_tables(part_kind, items, len(dropped)).items():
            path = folder / name
            path.write_text(text, encoding="utf-8", newline="\n")
            written.append(path)
    return written


# ---- running tests (L1) ------------------------------------------------------------------------

TESTRUNS = REPO_ROOT / "70_input" / "72_Kleingetriebepruefstand_KV3" / "kst-E_Laufversuche_KV3.xlsx"
FLAG_LABELS = {
    "estimated_cycles": "Lastspielzahl geschätzt (Drehzahlsensor)",
    "cycles_with_text": "Lastspielzahl mit Zusatztext",
    "stepped": "Stufenlauf",
    "dry_room_temperature": "Trockenlauf bei Raumtemperatur",
    "oil_45C": "Öl unter 60 °C",
    "lubrication_deficit_possible": "Schmierungsdefizit möglich (Notiz Spalte U)",
    "planned_only": "nur geplant",
    "no_cycles": "ohne Lastspielzahl",
    "duplicate_rows": "mehrere Zeilen je Kennung",
    "id_typo": "Kennung abweichend geschrieben",
    "wheel_torque_from_pinion": "Radmoment aus dem Ritzelmoment (Spalte Q leer)",
}
RUN_COLUMNS = [
    "Lauf", "Zeilen", "Datum", "Prüfstand", "Werkstoff", "Ritzel", "Rad", "Stufe in Nm",
    "Radmoment in Nm", "Ritzelmoment Soll in Nm", "Drehzahl Rad in 1/min",
    "Drehzahl Ritzel in 1/min", "Öltemperatur in °C", "Lastwechsel", "Lastwechsel (Spalte S)",
    "Lastwechsel Rad (× 51/52)", "Versagensart (Spalte J)", "Kriterium", "letzte Kontrolle ohne Anriss",
    "erste Kontrolle mit Anriss", "Kennzeichen",
]
EVENT_COLUMNS = [
    "Lauf", "Nr.", "Lastwechsel", "Momente in Nm", "nachgespannt auf Nm", "TA in °C", "TP in °C",
    "Verlust in Nm", "über Lastwechsel", "Befund", "Text",
]


def _cycles_text(value: int | None) -> str:
    return "" if value is None else f"{value:,}".replace(",", " ")


def _opt(value: float | None, digits: int) -> str:
    return "" if value is None else rp.german_number(value, digits)


def _run_row(run: tr.TestRun) -> list[str]:
    lower, upper = run.crack_window
    return [
        run.run_id, " ".join(str(r) for r in run.rows), run.date or "", run.rig,
        run.material or "", run.pinion_me or "", run.wheel_me or "",
        "" if run.level_Nm is None else str(run.level_Nm),
        _opt(run.wheel_torque_Nm, 2), _opt(run.target_pinion_torque_Nm, 2),
        _opt(run.speed_wheel_rpm, 0), _opt(run.speed_pinion_rpm, 0),
        run.oil_temperature_raw or "", _cycles_text(run.cycles), run.cycles_raw or "",
        _opt(run.cycles_wheel, 0),
        (run.failure_mode or "").replace("\n", " "),
        run.criterion + (" (bestätigt)" if run.criterion_confirmed else " (Vorschlag)"),
        _cycles_text(lower), _cycles_text(upper),
        "; ".join(
            ([", ".join(FLAG_LABELS.get(f, f) for f in run.flags)] if run.flags else [])
            + ([run.user_note] if run.user_note else [])
        ),
    ]


def _overview(title: str, runs: Sequence[tr.TestRun]) -> list[str]:
    columns = [
        "Lauf", "Datum", "Werkstoff", "Rad", "Stufe in Nm", "Radmoment in Nm",
        "Drehzahl Rad in 1/min", "Öl in °C", "Lastwechsel", "Versagensart",
        "Kriterium", "ohne Anriss bis", "Anriss ab", "Kennzeichen und Vermerke",
    ]
    rows: list[list[str]] = []
    for run in runs:
        r = _run_row(run)
        rows.append([r[0], r[2], r[4], r[6], r[7], r[8], r[10], r[12], r[13], r[16], r[17],
                     r[18], r[19], r[20]])
    return [f"## {title}", "", *_table(columns, rows), ""]


def _event_row(run: tr.TestRun, number: int, event: tr.RemarkEvent) -> list[str]:
    after = "" if event.torque_after_Nm is None else (
        f"{rp.german_number(event.torque_after_Nm[0], 1)} bis "
        f"{rp.german_number(event.torque_after_Nm[1], 1)}"
    )
    return [
        run.run_id, str(number), _cycles_text(event.cycles),
        " ".join(rp.german_number(t, 1) for t in event.torques_Nm), after,
        _opt(event.aggregate_temperature_C, 0), _opt(event.gearing_temperature_C, 0),
        _opt(event.loss_Nm, 1), _cycles_text(event.loss_over_cycles),
        ", ".join(tr.OBSERVATION_LABELS[o] for o in event.observations),
        event.text.replace("|", "/").replace("\n", " "),
    ]


def testruns_tables(book: tr.Workbook) -> dict[str, str]:
    runs = [r for r in book.runs if "planned_only" not in r.flags]
    planned = [r.run_id for r in book.runs if "planned_only" in r.flags]
    core = [r for r in runs if r.rig == "KV3" and (r.material or "").startswith("PA46")]
    other_2026 = [r for r in runs if r.rig == "KV3" and r not in core]
    kv4 = [r for r in runs if r.rig == "KV4"]
    lines = [
        "# Laufversuche aus `kst-E_Laufversuche_KV3.xlsx`", "",
        f"Quelle: `{book.path}`, Blatt Tabelle1. Stufe = Radmoment (Spalte Q) auf ganze Nm "
        "gerundet; 2023 benennt die Stufen nach dem Ritzelmoment (16 Nm = 16,3 Nm am Rad), 2026 "
        "nach dem Radmoment (15,7 Nm am Ritzel). Drehzahl: auf KV3 steht in Spalte R die "
        "Ritzeldrehzahl (3058 = 2999 am Rad, 3000 entspräche 3058,8), auf KV4 die Raddrehzahl "
        "(Nutzer, 18.10.2026). Das Kriterium ist ein Vorschlag aus den Spalten J, T und U und "
        "wird je Lauf bestätigt. Öltemperatur = Messstelle vor der Prüfverzahnung.", "",
    ]
    lines += _overview("PA46-GF30, KV3 (2026)", core)
    lines += _overview("POM und PEEK, KV3 (2026)", other_2026)
    lines += _overview("POM und PEEK, KV4 (2023, MA-0296)", kv4)
    if planned:
        lines += ["Nur geplante Zeilen ohne Datum und Lastspielzahl: " + ", ".join(planned), ""]
    ev_rows: list[list[str]] = []
    ev_lines = [
        "# Ereignisse aus Spalte T (wörtlich, zur Bestätigung)", "",
        "Befund: Schlagworte des Segments; ein Nachspannen ohne Befund ist keine Aussage zum "
        "Anriss. TA Aggregat, TP Messstelle vor der Prüfverzahnung, ein einzelner Wert ist TP.", "",
    ]
    for run in core + other_2026 + kv4:
        if not run.events:
            continue
        ev_lines += [
            f"## {run.run_id} (Rad {run.wheel_me or '?'}, {run.material or '?'}, "
            f"Stufe {run.level_Nm or '?'} Nm)", "",
        ]
        table_rows: list[list[str]] = []
        for n, e in enumerate(run.events, start=1):
            row = _event_row(run, n, e)
            ev_rows.append(row)
            table_rows.append(row[1:])
        ev_lines += [*_table(EVENT_COLUMNS[1:], table_rows), ""]
    cw_lines = [
        "# Anrissfenster (erster makroskopischer Anriss nach Stommel et al.)", "",
        "Untere Schranke: letzte Kontrolle, die keinen Anriss nennt; obere Schranke: erste "
        "Kontrolle mit Anriss oder ersten Anzeichen. Läufe ohne Zeile tragen keine Rissnotiz. "
        "Die Zeilen von 2023 (KV4) folgen der Lesart der Schlagworte und sind vom Nutzer am "
        "Text zu prüfen; ein Nachspannen ohne Befund ist keine Aussage.", "",
    ]
    cw_rows: list[list[str]] = []
    for run in core + kv4 + other_2026:
        lower, upper = run.crack_window
        if lower is None and upper is None:
            continue
        quoted = upper if upper is not None else lower
        quote = next((e.text for e in run.events if e.cycles == quoted), "")
        cw_rows.append([
            run.run_id, run.material or "", str(run.level_Nm or ""), _cycles_text(lower),
            _cycles_text(upper), _cycles_text(run.cycles),
            quote[:140].replace("|", "/").replace("\n", " "),
        ])
    cw_lines += _table(
        ["Lauf", "Werkstoff", "Stufe in Nm", "ohne Anriss bis", "Anriss ab", "Ende", "Zitat"],
        cw_rows,
    )
    lr_lines = [
        "# Nachspannhistorie der PA46-GF30-Läufe: Momentverlust je Intervall", "",
        "Verlust aus der Notiz (ca. x Nm Verlust über n) oder aus dem Moment nach dem vorherigen "
        "Nachspannen minus dem Moment vor diesem Halt. TA Aggregat, TP Messstelle vor der "
        "Prüfverzahnung.", "",
    ]
    for run in core:
        intervals = tr.loss_intervals(run)
        if not intervals:
            continue
        lr_lines += [f"## {run.run_id} (Rad {run.wheel_me}, {run.level_Nm} Nm)", ""]
        lr_lines += _table(
            ["von", "bis", "Verlust in Nm", "Nm je Mio. Lastwechsel", "TA in °C", "TP in °C"],
            [[_cycles_text(a), _cycles_text(b), rp.german_number(loss, 1),
              rp.german_number(rate, 2), _opt(ta, 0), _opt(tp, 0)]
             for a, b, loss, rate, ta, tp in intervals],
        )
        lr_lines.append("")
    tm_lines = ["# Temperaturmatrix (Stufenläufe, Zahnflankentemperatur nach 2 h)", ""]
    for run in book.runs:
        if not run.stages:
            continue
        tm_lines += [f"## {run.run_id} (Rad {run.wheel_me})", ""]
        tm_lines += _table(
            ["Zeile", "Datum", "Ritzelmoment Soll in Nm", "Radmoment in Nm",
             "Drehzahl Rad in 1/min", "Lastwechsel", "Flankentemperatur nach 2 h in °C",
             "Bemerkung"],
            [[str(s.row), s.date or "", _opt(s.target_pinion_torque_Nm, 1),
              _opt(s.wheel_torque_Nm, 2), _opt(s.speed_wheel_rpm, 0), s.cycles_raw or "",
              _opt(s.flank_temperature_2h_C, 1),
              (s.remark or "").replace("|", "/").replace("\n", " ")[:110]]
             for s in run.stages],
        )
        tm_lines.append("")
    an_lines = ["# Anomalien und Annahmen (zur Bestätigung)", "",
                *[f"- {a}" for a in book.anomalies], ""]
    return {
        "laufversuche.md": "\n".join(lines) + "\n",
        "laufversuche.csv": rp.csv_text(RUN_COLUMNS, [_run_row(r) for r in book.runs]),
        "ereignisse.md": "\n".join(ev_lines) + "\n",
        "ereignisse.csv": rp.csv_text(EVENT_COLUMNS, ev_rows),
        "anrissfenster.md": "\n".join(cw_lines) + "\n",
        "verlustraten.md": "\n".join(lr_lines) + "\n",
        "temperaturmatrix.md": "\n".join(tm_lines) + "\n",
        "anomalien.md": "\n".join(an_lines) + "\n",
    }


def run_testruns(path: Path, out: Path, *, confirmations: Path | None = tr.CONFIRMATIONS) -> list[Path]:
    book = tr.load_workbook(path)
    if confirmations is not None and confirmations.is_file():
        book = tr.apply_confirmations(book, confirmations)
    out.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for name, text in testruns_tables(book).items():
        target = out / name
        target.write_text(text, encoding="utf-8", newline="\n")
        written.append(target)
    return written


# ---- Wöhler lines (L2, L3) and the temperature matrix (L4) -------------------------------------

REFERENCE_SPEED_RPM = {"KV3": 3000.0, "KV4": 2250.0}
"""Wheel speed of the campaign; runs at another speed stay out of the comparison lines."""
PROBABILITY_TICKS = (1, 2, 5, 10, 20, 50, 80, 90, 99)
GREY = "0.45"


def _colours() -> list[str]:
    import matplotlib as mpl

    return [str(c) for c in mpl.rcParams["axes.prop_cycle"].by_key()["color"]]


def _close(figure: Any) -> None:
    import matplotlib.pyplot as plt

    plt.close(figure)


def _g(value: float | None, digits: int) -> str:
    return "" if value is None else rp.german_number(value, digits)


def _slug(material: str, campaign: str) -> str:
    return (material + "_" + campaign).lower().replace("-", "").replace(" ", "_")


def _point_groups(points: Sequence[wl.TestPoint]) -> dict[tuple[str, bool, str], list[wl.TestPoint]]:
    groups: dict[tuple[str, bool, str], list[wl.TestPoint]] = {}
    for p in points:
        if p.runout:
            key = (">", False, "Durchläufer")
        elif p.stepped:
            key = (MARKERS[1], False, "Stufenlauf, nicht in der Regression")
        elif p.estimated:
            key = (MARKERS[3], False, "Versagensgeräusch, Lastspielzahl geschätzt")
        elif p.criterion.startswith("Versagensgeräusch"):
            key = (MARKERS[0], False, "Versagensgeräusch")
        else:
            key = (MARKERS[0], True, "Totalausfall")
        groups.setdefault(key, []).append(p)
    return groups


def _draw_points(axes: Any, points: Sequence[wl.TestPoint], colour: str, prefix: str) -> None:
    for (marker, filled, suffix), group in _point_groups(points).items():
        axes.plot(
            [p.cycles for p in group], [p.load_Nm for p in group], linestyle="none",
            marker=marker, color=colour, markerfacecolor=colour if filled else "white",
            label=f"{prefix}: {suffix} (n = {len(group)})",
        )


def _draw_line(axes: Any, fit: wl.LineFit, probability: int, colour: str, style: Any, label: str) -> None:
    loads = [fit.load_min + i * (fit.load_max - fit.load_min) / 60.0 for i in range(61)]
    axes.plot([fit.cycles(load, probability) for load in loads], loads, color=colour,
              linestyle=style, marker="none", label=label)


def _axes_woehler(axes: Any, y_max: float) -> None:
    axes.set_xscale("log")
    axes.set_xlim(1.0e4, 1.0e8)
    axes.set_ylim(6.0, y_max)
    axes.set_xlabel("Lastwechselzahl $N_{\\mathrm{L}}$")
    axes.set_ylabel("Raddrehmoment $T_{\\mathrm{2}}$ in Nm")
    decimal_comma(axes, which="y")


def woehler_figure(result: wl.WoehlerResult, out: Path) -> list[Path]:
    """T_2 over N_L: the points by criterion, the semi-logarithmic lines for 50, 10 and 1 %, the
    double-logarithmic 50 % line and the 10 % values of VDI 2736 Blatt 4 per level."""
    figure, axes = new_figure("full", 0.62)
    colours = _colours()
    _draw_points(axes, result.points, colours[0], f"{result.material}, {result.campaign}")
    s = result.semilog
    _draw_line(axes, s, 50, colours[0], LINE_STYLES[0],
               f"50 % halblogarithmisch: lg $N_{{\\mathrm{{L}}}}$ = {_g(s.intercept, 3)} − "
               f"{_g(s.slope, 4)} · $T_{{\\mathrm{{2}}}}$, $s_{{\\lg N}}$ = {_g(s.s_used, 3)} (n = {s.n})")
    _draw_line(axes, s, 10, colours[0], LINE_STYLES[1], "10 % nach DIN 50100 (u = −1,282)")
    _draw_line(axes, s, 1, colours[0], LINE_STYLES[2], "1 % (u = −2,33, außerhalb des Bereichs der Norm)")
    ll = result.loglog
    _draw_line(axes, ll, 50, colours[1], LINE_STYLES[3],
               f"50 % doppeltlogarithmisch: k = {_g(ll.slope, 2)}, lg C = {_g(ll.intercept, 2)}")
    if result.vdi_s_bar is not None:
        load_of = {lvl.level_Nm: lvl.load_Nm for lvl in result.levels}
        xs = [v.N_i_10 for v in result.vdi if v.N_i_10 is not None]
        ys = [load_of[v.level_Nm] for v in result.vdi if v.N_i_10 is not None]
        axes.plot(xs, ys, linestyle="none", marker=MARKERS[5], color=colours[1],
                  markerfacecolor="white",
                  label=f"10 % nach VDI 2736 Blatt 4 je Horizont (s̄ = {_g(result.vdi_s_bar, 4)})")
    _axes_woehler(axes, 18.0)
    axes.set_yticks([lvl.level_Nm for lvl in result.levels])
    legend_outside(figure, axes, where="bottom", ncol=1)
    paths = save(figure, out / f"woehler_T2_{_slug(result.material, result.campaign)}")
    _close(figure)
    return paths


def comparison_figure(
    groups: Sequence[tuple[str, Sequence[wl.TestPoint]]], main: wl.WoehlerResult, out: Path,
) -> list[Path]:
    """The materials beside each other: points per material and campaign, the 50 % line of the
    main material only."""
    figure, axes = new_figure("full", 0.62)
    colours = _colours()
    for index, (label, points) in enumerate(groups):
        colour = colours[index % len(colours)]
        marker = MARKERS[index % len(MARKERS)]
        filled = "KV3" in label
        axes.plot([p.cycles for p in points], [p.load_Nm for p in points], linestyle="none",
                  marker=marker, color=colour, markerfacecolor=colour if filled else "white",
                  label=f"{label} (n = {len(points)})")
    _draw_line(axes, main.semilog, 50, colours[0], LINE_STYLES[0],
               f"{main.material}, {main.campaign}: 50 %-Linie halblogarithmisch")
    _axes_woehler(axes, 20.0)
    axes.set_yticks([8, 10, 12, 14, 16, 18])
    legend_outside(figure, axes, where="bottom", ncol=1)
    paths = save(figure, out / "woehler_T2_vergleich_werkstoffe")
    _close(figure)
    return paths


def net_figures(result: wl.WoehlerResult, out: Path) -> list[Path]:
    """Gauss and Weibull nets of the normalised cycles with both probability estimates."""
    from statistics import NormalDist

    paths: list[Path] = []
    values = [value for _, value in wl.normalised_cycles(result.semilog, result.admitted)]
    n = len(values)
    colours = _colours()
    for kind in ("gauss", "weibull"):
        def transform(p: float) -> float:
            return NormalDist().inv_cdf(p) if kind == "gauss" else math.log(-math.log(1.0 - p))

        figure, axes = new_figure("full", 0.62)
        for index, (estimator, name) in enumerate((("rossow", "Rossow (3j − 1)/(3n + 1)"),
                                                   ("rank", "j/(n + 1)"))):
            probabilities = [wl.rossow(j, n) if estimator == "rossow" else wl.rank_estimate(j, n)
                             for j in range(1, n + 1)]
            axes.plot(values, [transform(p) for p in probabilities], linestyle="none",
                      marker=MARKERS[index], color=colours[index],
                      markerfacecolor=colours[index] if index == 0 else "white",
                      label=f"Punkte, $P_{{\\mathrm{{A}}}}$ nach {name}")
            fit = next(f for f in result.nets if f.kind == kind and f.estimator == estimator)
            grid = [min(values) * (max(values) / min(values)) ** (i / 40.0) for i in range(41)]
            ratio = "$N_{\\mathrm{L,10\\%}}/N_{\\mathrm{L,50\\%}}$"
            if kind == "gauss":
                ys = [(math.log10(x) - fit.intercept) / fit.slope for x in grid]
                label = (f"Gerade, {name}: $s_{{\\lg N}}$ = {_g(fit.parameter, 3)}, "
                         f"{ratio} = {_g(fit.factor_10, 2)}, R² = {_g(fit.r_squared, 3)}")
            else:
                ys = [(math.log(x) - fit.intercept) / fit.slope for x in grid]
                label = (f"Gerade, {name}: $k_{{\\mathrm{{W}}}}$ = {_g(fit.parameter, 2)}, "
                         f"$\\eta$ = {_g(fit.scale, 3)}, "
                         f"{ratio} = {_g(fit.factor_10, 2)}, R² = {_g(fit.r_squared, 3)}")
            axes.plot(grid, ys, color=colours[index], linestyle=LINE_STYLES[index], marker="none",
                      label=label)
        axes.set_xscale("log")
        axes.set_yticks([transform(p / 100.0) for p in PROBABILITY_TICKS],
                        [str(p) for p in PROBABILITY_TICKS])
        axes.set_xlabel("bezogene Lastwechselzahl $N_{\\mathrm{L}} / N_{\\mathrm{L,50\\%}}$")
        axes.set_ylabel("Ausfallwahrscheinlichkeit $P_{\\mathrm{A}}$ in %")
        axes.grid(True, which="major", linewidth=0.4, color="0.85")
        legend_outside(figure, axes, where="bottom", ncol=1)
        decimal_comma(axes, which="x")
        paths += save(figure, out / f"netz_{kind}_{_slug(result.material, result.campaign)}")
        _close(figure)
    return paths


def temperature_figure(run: tr.TestRun, out: Path) -> tuple[list[Path], list[str]]:
    """L4: the flank temperature after two hours per wheel torque and wheel speed of the run-in
    matrix as bars, the 80 °C reference as a line; the table beside it."""
    cells: dict[tuple[int, int], float] = {}
    for stage in run.stages:
        if stage.flank_temperature_2h_C is None or stage.wheel_torque_Nm is None \
                or stage.speed_wheel_rpm is None:
            continue
        cells[(round(stage.wheel_torque_Nm), int(round(stage.speed_wheel_rpm / 10.0)) * 10)] = \
            stage.flank_temperature_2h_C
    if not cells:
        raise InputRangeError(f"{run.run_id}: no flank temperatures in the stages")
    levels = sorted({level for level, _ in cells})
    speeds = sorted({speed for _, speed in cells})
    figure, axes = new_figure("full", 0.5)
    colours = _colours()
    width = 0.8 / len(speeds)
    for index, speed in enumerate(speeds):
        xs = [i + (index - (len(speeds) - 1) / 2.0) * width for i in range(len(levels))]
        heights = [cells.get((level, speed), 0.0) for level in levels]
        axes.bar(xs, heights, width=width * 0.92, color=colours[index],
                 label=f"{speed} 1/min am Rad: " + " / ".join(_g(h, 1) for h in heights) + " °C")
    axes.axhline(80.0, color=GREY, linestyle=(0, (1, 2)), linewidth=1.0,
                 label="Bezugstemperatur 80 °C der Werkstoffkarten")
    axes.set_xticks(list(range(len(levels))), [str(level) for level in levels])
    axes.set_xlabel("Raddrehmoment $T_{\\mathrm{2}}$ in Nm")
    axes.set_ylabel("Zahnflankentemperatur nach 2 h in °C")
    axes.set_ylim(0.0, 95.0)
    legend_outside(figure, axes, where="bottom", ncol=1)
    decimal_comma(axes, which="y")
    paths = save(figure, out / f"temperatur_matrix_{run.wheel_me or run.run_id}")
    _close(figure)
    lines = [f"## Temperaturmatrix {run.run_id} (Rad {run.wheel_me}, Öl {run.oil_temperature_raw} °C)", ""]
    lines += _table(
        ["Raddrehmoment in Nm"] + [f"{speed} 1/min am Rad" for speed in speeds],
        [[str(level)] + [_g(cells.get((level, speed)), 1) for speed in speeds] for level in levels],
    )
    return paths, lines


def _fit_lines(fit: wl.LineFit, label: str) -> list[str]:
    if fit.kind == "semilog":
        form = (f"lg N_L = {_g(fit.intercept, 4)} − {_g(fit.slope, 5)} · T_2 "
                f"(a_c = {_g(fit.intercept, 4)}, b_c = {_g(fit.slope, 5)} 1/Nm)")
    else:
        form = f"lg N_L = {_g(fit.intercept, 4)} − {_g(fit.slope, 3)} · lg T_2 (lg C, k)"
    return [
        f"- {label}: {form}; n = {fit.n}; s_lgN = {_g(fit.s_lgN, 4)}, korrigiert "
        f"{_g(fit.s_lgN_corr, 4)}, verwendet {_g(fit.s_used, 4)} (Untergrenze {_g(wl.SCATTER_FLOOR, 2)}); "
        f"gültig von {_g(fit.load_min, 2)} bis {_g(fit.load_max, 2)} Nm",
    ]


def woehler_tables(result: wl.WoehlerResult, excluded: Sequence[str]) -> dict[str, str]:
    lines = [
        f"# Wöhlerlinie {result.material}, {result.campaign} (Bruchlinie nach Prüfstandskriterium)", "",
        "Regression mit lg N_L als abhängiger Größe im Zeitfestigkeitsbereich; Streuung gepoolt "
        "nach DIN 50100 (Perlenschnur, Gl. (36), (38), (39)); Linien nach Gl. (67) mit u = −1,282 "
        "(10 %) und −2,33 (1 %, Hasl); Untergrenze s_lgN = 0,10 (Hasl S. 118). Keine Durchläufer "
        "in der Regression; Stufenläufe nur als Marker.", "",
    ]
    lines += _fit_lines(result.semilog, "halblogarithmisch (Hasl Gl. (51), Darstellung VDI 2736 Blatt 2)")
    lines += _fit_lines(result.loglog, "doppeltlogarithmisch (DIN 50100 Gl. (30), Basquin)")
    if result.all_failures is not None:
        lines += _fit_lines(result.all_failures, "halblogarithmisch mit allen Ausfällen (ohne Regel 10.2.1)")
    if excluded:
        lines += ["", "Nicht in der Auswertung: " + ", ".join(excluded)]
    lines += ["", "## Horizonte", ""]
    vdi_of = {v.level_Nm: v for v in result.vdi}
    rows: list[list[str]] = []
    for lvl in result.levels:
        v = vdi_of[lvl.level_Nm]
        rows.append([
            str(lvl.level_Nm), _g(lvl.load_Nm, 2), str(lvl.n),
            " / ".join(f"{c:,}".replace(",", " ") for c in lvl.cycles_measured),
            f"{lvl.N_50:.3e}", f"{lvl.N_10:.3e}", f"{lvl.N_1:.3e}",
            f"{v.N_i_50:.3e}", _g(v.s_i, 4) if v.s_i is not None else "–",
            f"{v.N_i_10:.3e}" if v.N_i_10 is not None else "–",
        ])
    lines += _table(
        ["Stufe in Nm", "Radmoment in Nm", "n", "Lastwechsel gemessen", "N_50 % DIN", "N_10 % DIN",
         "N_1 % DIN", "N_i,50 % VDI", "s_i VDI", "N_i,10 % VDI"], rows,
    )
    lines += ["", f"VDI 2736 Blatt 4: s̄ = {_g(result.vdi_s_bar, 5)} über die Horizonte mit "
              "Wiederholung; N_i,10 % = 10^((1 − 1,28 s̄) L_i,50 %).", ""]
    lines += ["## Netze (bezogene Lastwechselzahlen N_L / N_L,50 % der halblogarithmischen Linie)", ""]
    net_rows = [[
        "Gauß" if f.kind == "gauss" else "Weibull", f.estimator, str(f.n),
        _g(f.parameter, 4), _g(f.scale, 4), _g(f.factor_10, 3), _g(f.factor_1, 3), _g(f.r_squared, 4),
    ] for f in result.nets]
    lines += _table(["Netz", "P_A nach", "n", "s_lgN bzw. k", "10^μ bzw. η", "N_10/N_50", "N_1/N_50", "R²"],
                    net_rows)
    lines += ["", "Illenberger (PEEK, Grübchen, Tabelle 7-2): k = 3,46, N_10/N_50 = 0,58, N_1/N_50 = 0,30.", ""]
    columns = ["Lauf", "Rad", "Stufe in Nm", "Radmoment in Nm", "Lastwechsel", "Kriterium",
               "geschätzt", "Durchläufer", "Stufenlauf", "in der Regression"]
    admitted = {p.run_id for p in result.admitted}
    point_rows = [[
        p.run_id, p.wheel or "", str(p.level_Nm), _g(p.load_Nm, 2), str(p.cycles), p.criterion,
        "ja" if p.estimated else "", "ja" if p.runout else "", "ja" if p.stepped else "",
        "ja" if p.run_id in admitted else "nein",
    ] for p in result.points]
    return {"woehler.md": "\n".join(lines) + "\n", "punkte.csv": rp.csv_text(columns, point_rows)}


def _comparison_groups(book: tr.Workbook) -> tuple[list[tuple[str, list[wl.TestPoint]]], list[str]]:
    """(label, points) per material and campaign at the reference speed; the excluded runs."""
    runs = list(book.runs)
    speed_of = {run.run_id: run.speed_wheel_rpm for run in runs}
    groups: list[tuple[str, list[wl.TestPoint]]] = []
    excluded: list[str] = []
    for material, rig in (("PA46-GF30", "KV3"), ("POM", "KV3"), ("PEEK", "KV3"),
                          ("POM", "KV4"), ("PEEK", "KV4")):
        points = wl.points_from_runs(runs, material=material, rig=rig)
        kept: list[wl.TestPoint] = []
        for p in points:
            speed = speed_of.get(p.run_id)
            if not p.stepped and (speed is None or abs(speed - REFERENCE_SPEED_RPM[rig]) > 5.0):
                excluded.append(f"{p.run_id} ({material}, {rig}, Drehzahl {_g(speed, 0) or '?'} 1/min am Rad)")
                continue
            kept.append(p)
        if kept:
            groups.append((f"{material}, {kept[0].campaign}", kept))
    return groups, excluded


def run_woehler(
    path: Path, out: Path, *, confirmations: Path | None = tr.CONFIRMATIONS, plots: bool = True,
) -> list[Path]:
    apply_plot_style()
    book = tr.load_workbook(path)
    if confirmations is not None and confirmations.is_file():
        book = tr.apply_confirmations(book, confirmations)
    groups, excluded = _comparison_groups(book)
    main_label, main_points = groups[0]
    result = wl.evaluate(main_points)
    out.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    own_excluded = [e for e in excluded if e.split("(", 1)[-1].startswith(result.material)]
    for name, text in woehler_tables(result, own_excluded).items():
        target = out / name
        target.write_text(text, encoding="utf-8", newline="\n")
        written.append(target)
    lines = ["# Vergleichswerkstoffe (Punkte bei Referenzdrehzahl; Linien nur, wo drei Ausfälle "
             "auf zwei Horizonten liegen)", ""]
    for label, points in groups[1:]:
        lines.append(f"## {label} (n = {len(points)})")
        lines.append("")
        try:
            other = wl.evaluate(points)
            lines += _fit_lines(other.semilog, "halblogarithmisch")
            lines += _fit_lines(other.loglog, "doppeltlogarithmisch")
        except InputRangeError as error:
            lines.append(f"- keine Linie: {error}")
        lines += ["", *_table(
            ["Lauf", "Rad", "Stufe in Nm", "Lastwechsel", "Kriterium"],
            [[p.run_id, p.wheel or "", str(p.level_Nm), str(p.cycles), p.criterion] for p in points],
        ), ""]
    if excluded:
        lines += ["Ausgeschlossen (andere Drehzahl): " + ", ".join(excluded), ""]
    matrix_lines: list[str] = []
    matrix_run = next((run for run in book.runs if run.stages), None)
    if plots:
        written += woehler_figure(result, out)
        written += comparison_figure(groups, result, out)
        written += net_figures(result, out)
        if matrix_run is not None:
            figure_paths, matrix_lines = temperature_figure(matrix_run, out)
            written += figure_paths
    target = out / "vergleich.md"
    target.write_text("\n".join(lines + matrix_lines) + "\n", encoding="utf-8", newline="\n")
    written.append(target)
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
    gina_parser = sub.add_parser("gina", help="evaluate the P40 value and curve files")
    gina_parser.add_argument("--input", type=Path, default=INPUT, help="measurement folder")
    gina_parser.add_argument("--out", type=Path, default=OUTPUT / "gina")
    gina_parser.add_argument("--part", choices=("wheel", "pinion"), action="append")
    gina_parser.add_argument("--me", action="append", help="ME numbers to evaluate")
    gina_parser.add_argument("--rounds", choices=("latest", "all"), default="latest")
    gina_parser.add_argument("--no-plots", action="store_true")
    contour_parser = sub.add_parser("contour", help="evaluate the P40 contour scans")
    contour_parser.add_argument("--input", type=Path, default=INPUT, help="measurement folder")
    contour_parser.add_argument("--out", type=Path, default=OUTPUT / "konturscan")
    contour_parser.add_argument("--case", default="kst_e", help="packaged STplus case")
    contour_parser.add_argument("--part", choices=("wheel", "pinion"), action="append")
    contour_parser.add_argument("--me", action="append", help="ME numbers to evaluate")
    contour_parser.add_argument("--include-coarse", action="store_true")
    contour_parser.add_argument(
        "--magnify", type=float, default=1.0, help="of the overlays (1 = true scale)"
    )
    contour_parser.add_argument("--corner-step", type=float, default=0.01, help="mm")
    contour_parser.add_argument("--corner-max", type=float, default=0.3, help="mm")
    contour_parser.add_argument("--no-plots", action="store_true")
    roughness_parser = sub.add_parser("roughness", help="evaluate the Hommel roughness exports")
    roughness_parser.add_argument("--input", type=Path, default=INPUT, help="measurement folder")
    roughness_parser.add_argument("--out", type=Path, default=OUTPUT / "rauheit")
    roughness_parser.add_argument("--part", choices=("wheel", "pinion"), action="append")
    roughness_parser.add_argument("--me", action="append", help="ME numbers to evaluate")
    testruns_parser = sub.add_parser("testruns", help="read the running-test workbook (L1)")
    testruns_parser.add_argument("--input", type=Path, default=TESTRUNS, help="workbook")
    testruns_parser.add_argument("--out", type=Path, default=OUTPUT / "laufversuche")
    woehler_parser = sub.add_parser("woehler", help="Wöhler lines of the running tests (L2 to L4)")
    woehler_parser.add_argument("--input", type=Path, default=TESTRUNS, help="workbook")
    woehler_parser.add_argument("--out", type=Path, default=OUTPUT / "woehler")
    woehler_parser.add_argument("--no-plots", action="store_true")
    gina_parser.add_argument(
        "--curves",
        action="store_true",
        help="also draw the profile and lead curves (the Klingelnberg sheets show them)",
    )
    args = parser.parse_args()
    if args.command == "inventory":
        for path in run_inventory(args.input, args.out):
            print(path)
    elif args.command == "gina":
        for path in run_gina(
            args.input,
            args.out,
            parts=tuple(args.part) if args.part else ("wheel", "pinion"),
            me_filter=args.me,
            rounds=args.rounds,
            plots=not args.no_plots,
            curves=args.curves,
        ):
            print(path)
    elif args.command == "testruns":
        for path in run_testruns(args.input, args.out):
            print(path)
    elif args.command == "woehler":
        for path in run_woehler(args.input, args.out, plots=not args.no_plots):
            print(path)
    elif args.command == "contour":
        for path in run_contour(
            args.input,
            args.out,
            case=args.case,
            parts=tuple(args.part) if args.part else ("wheel", "pinion"),
            me_filter=args.me,
            include_coarse=args.include_coarse,
            magnify=args.magnify,
            corner_step_mm=args.corner_step,
            corner_max_mm=args.corner_max,
            plots=not args.no_plots,
        ):
            print(path)
    elif args.command == "roughness":
        for path in run_roughness(
            args.input,
            args.out,
            parts=tuple(args.part) if args.part else ("wheel", "pinion"),
            me_filter=args.me,
        ):
            print(path)


if __name__ == "__main__":
    main()
