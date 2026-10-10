"""Which measurement files exist for which part: the inventory of ``70_input/71_Messungen``.

The folder is the user's; its layout (verified 2026-10-10) is encoded in ``FOLDER_RULES``: one
rule per kind of file with the folder pattern, the part the folder belongs to and the file-name
grammar that yields the ME number and the variant (``97340-neu.mew``), the tooth (``97341_z36.DAT``)
or the flank and trace (``F4092_97340_neu_li.txt``). What the files cannot say comes from
``data/measurement/parts.yaml`` (the user's groups, drawings, known anomalies).

Measurement rounds are the measuring campaigns of a part kind, assigned by the date in the file
header, not by the suffix of the name: the suffixes ``-neu``, ``_neu``, ``-neu1`` of the GINA
files are inconsistent, the dates cluster (8 to 13 May, 27 May, 10 June 2026 for the wheels).
Dates lying at most ``ROUND_GAP_DAYS`` apart form one round; the round number counts per part
kind from 1, so a wheel first measured on 10 June is in round 3. Two GINA files of one part in
one round are repeat measurements; ``repeat`` numbers them by date and name.

Anomalies are stated, never repaired: a scan with two blocks, a misnamed file, a coarse scan,
an ME number that occurs in one kind of file only, a roughness twin that differs from its
original. The scan reads the headers of the GINA and roughness files (dates, ME numbers) and the
point count of the contour scans; it writes nothing.
"""

import datetime as dt
import re
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any, Literal

from gearcore.data import load_measurement_parts
from gearcore.errors import InputRangeError, ParseError
from gearcore.io.hommel import load_roughness_table
from gearcore.io.p40 import load_mew, load_mka
from gearcore.io.p40_contour import load_contour_scans
from gearcore.models.common import FrozenModel

Part = Literal["wheel", "pinion"]
Kind = Literal[
    "mew", "mka", "messblatt_pdf", "contour", "roughness", "roughness_profile", "roughness_pdf"
]
Flank = Literal["li", "re"]

ROUND_GAP_DAYS = 5
"""Header dates at most this many days apart belong to the same measurement round."""
COARSE_SCAN_POINTS = 600
"""A contour scan with fewer points is coarse (about 0,05 mm spacing instead of 0,01 mm)."""
ME = r"(?P<me>\d{5})"
_PART_OF_FOLDER = {"Kunststoffrad": "wheel", "Stahlritzel": "pinion"}
_DATE = re.compile(r"^(\d{2})\.(\d{2})\.(\d{2})$")

FOLDER_RULES: tuple[tuple[Kind, re.Pattern[str]], ...] = (
    (
        "mew",
        re.compile(
            rf"^GINA/(?P<part>Kunststoffrad|Stahlritzel)/[^/]*_messwerte/{ME}(?P<variant>[-_][A-Za-z0-9]+)?\.mew$"
        ),
    ),
    (
        "mka",
        re.compile(
            rf"^GINA/(?P<part>Kunststoffrad|Stahlritzel)/[^/]*_messkurven/{ME}(?P<variant>[-_][A-Za-z0-9]+)?\.mka$"
        ),
    ),
    (
        "messblatt_pdf",
        re.compile(
            rf"^GINA/(?P<part>Kunststoffrad|Stahlritzel)/[^/]*_messblatt/{ME}(?P<variant>[-_][A-Za-z0-9]+)?\.pdf$"
        ),
    ),
    (
        "contour",
        re.compile(
            rf"^Konturscan/(?P<part>Kunststoffrad|Stahlritzel)/(?:[^/]+/)*{ME}(?P<sep>[-_])(?P<z>[Zz]?)(?P<tooth>\d{{1,2}})\.DAT$"
        ),
    ),
    (
        "roughness",
        re.compile(
            rf"^Rauheit/(?P<part>Kunststoffrad|Stahlritzel)/ASCII_Export/F\d+_{ME}_(?P<neu>neu_)?(?P<flank>li|re)\.txt$"
        ),
    ),
    (
        "roughness_profile",
        re.compile(
            rf"^Rauheit/(?P<part>Kunststoffrad|Stahlritzel)/HWP_Profil_Export/F\d+_{ME}_(?:neu_)?(?P<flank>li|re)_Messung-(?P<trace>\d)\.hwp$"
        ),
    ),
    (
        "roughness_pdf",
        re.compile(
            rf"^Rauheit/(?P<part>Kunststoffrad|Stahlritzel)/PDF/{ME}-(?P<label>.+?)-(?P<flank>li|re)-neu_?\.pdf$"
        ),
    ),
)
"""Kind and file-name grammar per folder, paths relative to the input root with ``/``."""

IGNORED = re.compile(r"^(Auswertung/.*|.*/Thumbs\.db)$")
"""Files of the folder that are not measurements (the Excel macro, thumbnail caches)."""


class MeasurementFile(FrozenModel):
    path: str
    """Relative to the input root, with ``/``."""
    me: str
    part: Part
    kind: Kind
    variant: str | None = None
    """Suffix after the ME number of a GINA file (``-neu``, ``_neu``, ``-neu1``, ``-neu2``)."""
    measured_on: str | None = None
    """ISO date from the file (GINA header code 2, roughness timestamp)."""
    measurement_round: int | None = None
    """Measuring campaign of the part kind the GINA file belongs to (1, 2, …, by date)."""
    repeat: int | None = None
    """1 for the first GINA file of the part in its round, 2 for a repeat measurement, …"""
    tooth: int | None = None
    flank: Flank | None = None
    trace: int | None = None
    points: int | None = None
    """Contour scans: points of the (first) block."""
    batch_label: str | None = None
    """Roughness report sheets: the ``Prüfteil/Zustand`` label of the file name."""
    anomalies: tuple[str, ...] = ()


class MeasuredPart(FrozenModel):
    me: str
    part: Part
    group: str
    labels: tuple[str, ...]
    """Labels of parts.yaml within the group (``running_in``, ``extra_test``)."""
    material: str
    batch_labels: tuple[str, ...]
    files: tuple[MeasurementFile, ...]

    def of_kind(self, kind: Kind) -> tuple[MeasurementFile, ...]:
        return tuple(file for file in self.files if file.kind == kind)

    @property
    def rounds(self) -> tuple[int, ...]:
        return tuple(
            sorted({f.measurement_round for f in self.files if f.measurement_round is not None})
        )


class Inventory(FrozenModel):
    root: str
    parts: tuple[MeasuredPart, ...]
    unassigned: tuple[MeasurementFile, ...]
    """Files whose ME number is in no group and has no GINA measurement (``97840``)."""
    ignored: tuple[str, ...]
    """Relative paths the rules leave out on purpose (``IGNORED``)."""
    unknown: tuple[str, ...]
    """Relative paths no rule matches: a new kind of file or a misnamed one."""
    anomalies: tuple[str, ...]

    def part(self, me: str) -> MeasuredPart:
        for entry in self.parts:
            if entry.me == me:
                return entry
        raise InputRangeError(f"no measured part with the ME number {me!r}")

    def of_group(self, group: str) -> tuple[MeasuredPart, ...]:
        return tuple(entry for entry in self.parts if entry.group == group)


def classify(relative: str) -> MeasurementFile | None:
    """The file a relative path names, from the folder rules alone (no file is read); ``None`` for
    an ignored file, ``ParseError`` for a path no rule matches."""
    if IGNORED.match(relative):
        return None
    for kind, pattern in FOLDER_RULES:
        match = pattern.match(relative)
        if match is None:
            continue
        groups = match.groupdict()
        part: Part = _PART_OF_FOLDER[groups["part"]]  # type: ignore[assignment]
        anomalies: list[str] = []
        tooth: int | None = None
        flank: Flank | None = None
        trace: int | None = None
        label: str | None = None
        if kind == "contour":
            tooth = int(groups["tooth"])
            if not groups["z"]:
                anomalies.append("file name without the tooth letter z")
            if tooth < 1:
                raise ParseError(f"{relative}: tooth number {tooth}")
        if kind in ("roughness", "roughness_profile", "roughness_pdf"):
            flank = groups["flank"]  # type: ignore[assignment]
        variant = groups.get("variant")
        if kind == "roughness" and groups.get("neu"):
            variant = "_neu"
        if kind == "roughness_profile":
            trace = int(groups["trace"])
        if kind == "roughness_pdf":
            label = groups["label"]
        return MeasurementFile(
            path=relative,
            me=groups["me"],
            part=part,
            kind=kind,
            variant=variant,
            tooth=tooth,
            flank=flank,
            trace=trace,
            batch_label=label,
            anomalies=tuple(anomalies),
        )
    raise ParseError(f"{relative}: no folder rule matches this file")


def _iso_date(text: str, where: str) -> str:
    match = _DATE.match(text.strip())
    if match is None:
        raise ParseError(f"{where}: date {text!r} is not dd.mm.yy")
    day, month, year = (int(g) for g in match.groups())
    return dt.date(2000 + year, month, day).isoformat()


def rounds_by_date(dates: Sequence[str]) -> dict[str, int]:
    """Round number per ISO date: dates at most ``ROUND_GAP_DAYS`` apart share a round."""
    unique = sorted({dt.date.fromisoformat(d) for d in dates})
    rounds: dict[str, int] = {}
    current = 0
    previous: dt.date | None = None
    for day in unique:
        if previous is None or (day - previous).days > ROUND_GAP_DAYS:
            current += 1
        rounds[day.isoformat()] = current
        previous = day
    return rounds


def _read_details(root: Path, file: MeasurementFile) -> MeasurementFile:
    """The file with what its content adds: date, point count, anomalies of the content."""
    path = root / file.path
    anomalies = list(file.anomalies)
    update: dict[str, Any] = {}
    if file.kind == "mew":
        mew = load_mew(path)
        update["measured_on"] = _iso_date(mew.header.text(2), file.path)
        if mew.header.text(7).split("-")[0].split("_")[0] != file.me:
            anomalies.append(f"header ME {mew.header.text(7)!r} differs from the file name")
    elif file.kind == "mka":
        mka = load_mka(path)
        update["measured_on"] = _iso_date(mka.header.text(2), file.path)
        if mka.header.text(7).split("-")[0].split("_")[0] != file.me:
            anomalies.append(f"header ME {mka.header.text(7)!r} differs from the file name")
    elif file.kind == "contour":
        scans = load_contour_scans(path)
        update["points"] = len(scans[0].points_mm)
        if len(scans) > 1:
            anomalies.append(f"{len(scans)} blocks in one file (repeated scan)")
        if len(scans[0].points_mm) < COARSE_SCAN_POINTS:
            anomalies.append(f"coarse scan ({len(scans[0].points_mm)} points)")
    elif file.kind == "roughness":
        table = load_roughness_table(path)
        record = table.records[0]
        update["measured_on"] = (
            dt.datetime.strptime(record.measured_at, "%d.%m.%Y/%H:%M:%S").date().isoformat()
        )
        if record.me != file.me:
            anomalies.append(f"MeE-Nr. {record.me!r} in the file differs from the file name")
        if record.flank != file.flank:
            anomalies.append(f"flank {record.flank!r} in the file differs from the file name")
        if len(table.records) > 1:
            anomalies.append(f"{len(table.records)} data rows (series exported twice)")
    return _rebuilt(file, {**update, "anomalies": tuple(anomalies)})


def _rebuilt(file: MeasurementFile, update: Mapping[str, Any]) -> MeasurementFile:
    """A new, validated ``MeasurementFile`` (``model_copy`` would skip the validation)."""
    return MeasurementFile(**{**file.model_dump(), **update})


def _group_of(me: str, part: Part, parts: Mapping[str, Any]) -> str:
    groups: dict[str, list[str]] = parts["parts"][part]["groups"]
    for name, members in groups.items():
        if me in members:
            return name
    scatter: str = parts["parts"][part]["scatter_group"]
    return scatter


def scan_folder(root: Path, parts: Mapping[str, Any] | None = None) -> Inventory:
    """The inventory of the measurement folder (reads the headers, writes nothing)."""
    base = Path(root)
    if not base.is_dir():
        raise InputRangeError(f"measurement folder not found: {base}")
    decisions = load_measurement_parts() if parts is None else parts
    files: list[MeasurementFile] = []
    ignored: list[str] = []
    unknown: list[str] = []
    for path in sorted(p for p in base.rglob("*") if p.is_file()):
        relative = PurePosixPath(path.relative_to(base).as_posix()).as_posix()
        try:
            classified = classify(relative)
        except ParseError:
            unknown.append(relative)
            continue
        if classified is None:
            ignored.append(relative)
            continue
        files.append(_read_details(base, classified))
    # rounds per part from the GINA dates
    for part in ("wheel", "pinion"):
        dates = [
            f.measured_on
            for f in files
            if f.part == part and f.kind in ("mew", "mka") and f.measured_on
        ]
        rounds = rounds_by_date(dates)
        files = [
            _rebuilt(f, {"measurement_round": rounds[f.measured_on]})
            if f.part == part and f.kind in ("mew", "mka") and f.measured_on
            else f
            for f in files
        ]
    files = _with_repeats(files)
    anomalies: list[str] = []
    by_me: dict[tuple[str, Part], list[MeasurementFile]] = {}
    for file in files:
        by_me.setdefault((file.me, file.part), []).append(file)
        for note in file.anomalies:
            anomalies.append(f"{file.path}: {note}")
    anomalies.extend(_twin_anomalies(base, files))
    measured: list[MeasuredPart] = []
    unassigned: list[MeasurementFile] = []
    for (me, part), own in sorted(by_me.items()):
        kinds = {f.kind for f in own}
        has_gina = "mew" in kinds or "mka" in kinds
        group = _group_of(me, part, decisions)
        known = any(me in members for members in decisions["parts"][part]["groups"].values())
        if not has_gina and not known and "contour" not in kinds:
            unassigned.extend(own)
            anomalies.append(
                f"{me} ({part}): {sorted(kinds)} only, no GINA measurement and not in parts.yaml"
            )
            continue
        if len(kinds) == 1:
            anomalies.append(f"{me} ({part}): only {next(iter(kinds))} files")
        batch = tuple(sorted({f.batch_label for f in own if f.batch_label}))
        part_labels: dict[str, list[str]] = decisions["parts"][part].get("labels", {})
        measured.append(
            MeasuredPart(
                me=me,
                part=part,
                group=group,
                labels=tuple(name for name, members in part_labels.items() if me in members),
                material=str(decisions["parts"][part]["material"]),
                batch_labels=batch,
                files=tuple(own),
            )
        )
    for entry in decisions.get("known_anomalies", []):
        anomalies.append(f"{entry['me']}: {entry['note']} (parts.yaml)")
    return Inventory(
        root=base.as_posix(),
        parts=tuple(measured),
        unassigned=tuple(unassigned),
        ignored=tuple(ignored),
        unknown=tuple(unknown),
        anomalies=tuple(dict.fromkeys(anomalies)),
    )


def _with_repeats(files: Sequence[MeasurementFile]) -> list[MeasurementFile]:
    """GINA files of one part and kind within one round numbered by date and name."""
    order: dict[tuple[str, str, str, int | None], list[MeasurementFile]] = {}
    for file in files:
        if file.kind in ("mew", "mka"):
            order.setdefault((file.me, file.part, file.kind, file.measurement_round), []).append(
                file
            )
    repeats: dict[str, int] = {}
    for group in order.values():
        for number, file in enumerate(
            sorted(group, key=lambda f: (f.measured_on or "", f.path)), 1
        ):
            repeats[file.path] = number
    return [_rebuilt(f, {"repeat": repeats[f.path]}) if f.path in repeats else f for f in files]


def _twin_anomalies(root: Path, files: Sequence[MeasurementFile]) -> list[str]:
    """Roughness exports exist twice (``_li`` and ``_neu_li``); they must carry the same numbers."""
    notes: list[str] = []
    by_key: dict[tuple[str, str, str | None], list[MeasurementFile]] = {}
    for file in files:
        if file.kind == "roughness":
            by_key.setdefault((file.me, file.part, file.flank), []).append(file)
    for (me, _, flank), twins in sorted(by_key.items()):
        if len(twins) < 2:
            continue
        tables = [load_roughness_table(root / twin.path) for twin in twins]
        first = tables[0].records[0].numbers
        for twin, table in zip(twins[1:], tables[1:], strict=True):
            if table.records[0].numbers != first:
                notes.append(f"{me} {flank}: {twin.path} differs from {twins[0].path}")
    return notes


__all__ = [
    "COARSE_SCAN_POINTS",
    "FOLDER_RULES",
    "IGNORED",
    "ROUND_GAP_DAYS",
    "Inventory",
    "Kind",
    "MeasuredPart",
    "MeasurementFile",
    "Part",
    "classify",
    "rounds_by_date",
    "scan_folder",
]
