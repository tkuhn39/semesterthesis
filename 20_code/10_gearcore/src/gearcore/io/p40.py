"""Klingelnberg P40 gear measurement exports (GINA): value files ``.mew`` and curve files ``.mka``.

Grammar as the files of 2025/2026 show it (software ``STI0441_44 5.0.0``, 136 files read):

* line 1 ``HEADER KS.MW.FILE`` (values) or ``HEADER KS.MK.FILE`` (curves); the file is UTF-8 with a
  byte order mark, CRLF line ends;
* a preamble of ``KEY value ! comment`` lines (``TYPE``, ``VERSION``, ``SEPARATOR``, ``UNITS``,
  ``ANGLE``, ``PROFILE``, ``LANGUAGE``, ``UNDEFINED``, ``FILTER …``);
* numbered header lines ``  <code> :<text>`` (codes 1 to 432): the text holds ``:``-separated
  fields, the first field is the label with dot leaders (``ME/Seite/KS/LZ....: 97340-neu``,
  ``Start Messbereich.....da  [mm]..:  50.156      50.156``), the others carry values, both
  numbers and words;
* ``.mew`` only: result lines ``<5-digit code> : <label> : <value>`` with one number each;
  ``-9999.0`` marks "not measured", ``8999.0`` "not available";
* ``.mka`` only: curve blocks (``Flankenlinie:``, ``Profil:``, and ``Verschränkung:`` heads on one
  line) with ``Zahn-Nr.: 44 links / 480  Werte  x= 8.742`` followed by the values, twelve per line,
  ``-2147483.648`` = undefined point; then ``Fußkreisdurchmesser / Höhe :`` and
  ``Kopfkreisdurchmesser / Höhe :`` with one value per measured tooth, the tables
  ``linke Zahnflanke`` / ``rechte Zahnflanke`` (``Zahn-Nr. fp Fp Fr`` for every tooth) and
  ``Teilung:`` (``Z-Nr. Seite PHI X Y Z`` for every tooth and flank).

Deviations are in micrometres, diameters, spans and positions in millimetres, angles in degrees;
the parser keeps the numbers as printed and does not convert. Every line that fits no rule is a
``ParseError``: a value must never be reported as absent because its line was not understood.
Known trap of the export (every file of 2025/2026): the per-tooth tip diameter lines (codes 26711 to
26715, ``Kopf 1`` …) repeat the per-tooth root values of codes 26411 to 26415, while ``Kopf m``,
``Kopf max`` and ``Kopf min`` are tip values; the parser forwards the numbers as printed, the
evaluation takes per-tooth tip diameters from the ``.mka`` line ``Kopfkreisdurchmesser / Höhe``.
This module is grammar only; what a code means is the business of ``gearcore.measurement.gina``.
"""

import math
import re
from pathlib import Path
from typing import Literal

from gearcore.errors import ParseError
from gearcore.models.common import FrozenModel

ENCODING = "utf-8-sig"
"""The files carry a UTF-8 byte order mark; one without the mark decodes the same way."""
FileKind = Literal["MW", "MK"]
Flank = Literal["links", "rechts"]
NOT_MEASURED = -9999.0
"""Result value of a quantity the program did not measure (``Fuß  u 1u :-9999.0``)."""
NOT_AVAILABLE = 8999.0
"""Result value of a statistic the program could not form (``V Fuß : 8999.0``)."""
UNDEFINED_POINT = -2147483.648
"""Curve value of an undefined measuring point (preamble key ``UNDEFINED``)."""

_HEADER = re.compile(r"^HEADER\s+KS\.(MW|MK)\.FILE\s*$")
_PREAMBLE_KEY = re.compile(r"^([A-Z]+(?: [A-Z]+)*):(?=\s|$)")
_HEADER_LINE = re.compile(r"^\s*(\d{1,3})\s+:(.*)$")
_RESULT_LINE = re.compile(r"^\s*(\d{5})\s*:\s*(.+?)\s*:\s*(\S+)\s*$")
_NUMBER = re.compile(r"^[-+]?(\d+\.?\d*|\.\d+)([eEdD][-+]?\d+)?$")
_DOTS = re.compile(r"\.{2,}")
_SPACES = re.compile(r"\s+")
_CURVE_HEAD = re.compile(
    r"^(?:(?P<block>Verschränkung):\s*)?Zahn-Nr\.:\s*(?P<tooth>\d+)(?P<tag>[a-z]?)\s*"
    r"(?:/(?P<kind>[A-Za-zäöü]+):(?P<index>\d+)\s*)?(?P<flank>links|rechts)\s*/\s*"
    r"(?P<count>\d+)\s+Werte\s+(?P<axis>[xz])=\s*(?P<position>[-+.\d]+)\s*$"
)
_BLOCK_TITLE = re.compile(r"^(?P<title>[A-Za-zäöüÄÖÜß]+):\s*$")
_DIAMETER_HEAD = re.compile(
    r"^(Fußkreisdurchmesser|Kopfkreisdurchmesser)\s*/\s*Höhe\s*:\s*(\S+)\s*$"
)
_TABLE_TITLE = re.compile(r"^\s*(linke|rechte) Zahnflanke\s*$")
_TABLE_HEAD = re.compile(r"^\s*Zahn-Nr\.\s+fp\s+Fp\s+Fr\s*$")
_POSITION_HEAD = re.compile(r"^\s*Z-Nr\.\s+Seite\s+PHI\s+X\s+Y\s+Z\s*$")


def _number(token: str, where: str) -> float:
    if not _NUMBER.match(token):
        raise ParseError(f"{where}: non-numeric token {token!r}")
    value = float(token.replace("d", "e").replace("D", "E"))
    if not math.isfinite(value):
        raise ParseError(f"{where}: {token!r} exceeds the number range")
    return value


def _preamble_entry(line: str, where: str, number: int) -> tuple[str, str]:
    """``KEY value ! comment``: the key is one upper-case word, or several words when a colon
    follows them directly (``FILTER LEAD:    F:S 2``); ``SEPARATOR :`` keeps its colon as the
    value."""
    body = line.split("!", 1)[0].strip()
    keyed = _PREAMBLE_KEY.match(body)
    if keyed is not None:
        return keyed.group(1), body[keyed.end() :].strip()
    key, _, value = body.partition(" ")
    if not key or not key.isalpha() or not key.isupper():
        raise ParseError(f"{where}: line {number}: not a preamble line: {line!r}")
    return key, value.strip()


def _label(text: str) -> str:
    """A label without its dot leaders and with single spaces (``'Zahnbreite ... [mm]'``)."""
    return _SPACES.sub(" ", _DOTS.sub(" ", text)).strip(" .")


class P40HeaderLine(FrozenModel):
    """One numbered header line: ``code``, the label (first field) and the fields after it."""

    code: int
    label: str
    raw: str
    """The text after the label as printed, single spaces (``'10:15:53 / 10:24:32'`` of code 3)."""
    fields: tuple[str, ...]
    """The ``:``-separated fields after the label, stripped, words and numbers as printed."""
    line: int

    def tokens(self) -> tuple[str, ...]:
        return tuple(token for field in self.fields for token in field.split())

    def numbers(self) -> tuple[float, ...]:
        """Every token of the fields that is a number, in order (words are passed over: the
        header mixes ``52  Außenverzahnung`` and ``FHAL:7 : -7 : 0:   5.5516`` on purpose)."""
        return tuple(
            _number(t, f"header code {self.code}") for t in self.tokens() if _NUMBER.match(t)
        )

    def text(self) -> str:
        """The text after the label as printed (``'97340-neu'``, ``'1 : L: + : R: -'``)."""
        return self.raw


class P40Header(FrozenModel):
    """Preamble and numbered header lines shared by ``.mew`` and ``.mka``."""

    file_kind: FileKind
    preamble: tuple[tuple[str, str], ...]
    """``(KEY, value)`` of the preamble, comments after ``!`` dropped."""
    lines: tuple[P40HeaderLine, ...]

    def get(self, code: int) -> P40HeaderLine | None:
        for entry in self.lines:
            if entry.code == code:
                return entry
        return None

    def require(self, code: int) -> P40HeaderLine:
        entry = self.get(code)
        if entry is None:
            raise ParseError(f"header code {code} is missing")
        return entry

    def number(self, code: int, index: int = 0) -> float:
        """The ``index``-th number of header line ``code`` (``number(27)`` = tip diameter)."""
        numbers = self.require(code).numbers()
        if index >= len(numbers):
            raise ParseError(f"header code {code}: no number at position {index + 1}")
        return numbers[index]

    def numbers(self, code: int) -> tuple[float, ...]:
        return self.require(code).numbers()

    def text(self, code: int) -> str:
        return self.require(code).text()

    def preamble_value(self, key: str) -> str | None:
        for name, value in self.preamble:
            if name == key:
                return value
        return None

    @property
    def undefined_point(self) -> float:
        value = self.preamble_value("UNDEFINED")
        return UNDEFINED_POINT if value is None else _number(value, "preamble UNDEFINED")


Placeholder = Literal["not_measured", "not_available"]


class MewValue(FrozenModel):
    """One result line of a ``.mew`` file."""

    code: int
    label: str
    """Label with single spaces (``'fHb links 12'``, ``'Fuß m'``)."""
    value: float | None
    """The number, or ``None`` for a placeholder (see ``placeholder``)."""
    placeholder: Placeholder | None
    line: int


class MewFile(FrozenModel):
    header: P40Header
    values: tuple[MewValue, ...]
    path: str | None = None

    def get(self, code: int) -> MewValue:
        for value in self.values:
            if value.code == code:
                return value
        raise ParseError(f"result code {code} is not in the file")

    def has(self, code: int) -> bool:
        return any(value.code == code for value in self.values)

    def by_label(self, label: str) -> MewValue:
        wanted = _SPACES.sub(" ", label).strip()
        found = [value for value in self.values if value.label == wanted]
        if len(found) != 1:
            raise ParseError(f"label {label!r}: {len(found)} result lines, expected one")
        return found[0]


class MkaCurve(FrozenModel):
    """One measured trace: a lead (``Flankenlinie``) or profile (``Profil``) curve of one tooth
    and flank, or a twist trace (``Verschränkung``) measured at a second position."""

    block: str
    """``'Flankenlinie'``, ``'Profil'`` or ``'Verschränkung'``."""
    tooth: int
    tooth_tag: str
    """Letter after the tooth number of a twist trace (``k``, ``f``, ``u``, ``o``), else ``''``."""
    trace_kind: str | None
    """Of a twist trace: the curve it belongs to (``'Flankenlinie'``, ``'Profil'``)."""
    trace_index: int | None
    flank: Flank
    count: int
    axis: str
    """``'x'`` (lead: roll length of the measuring circle) or ``'z'`` (profile: axial position)."""
    position: float
    values: tuple[float | None, ...]
    """Deviations in µm as printed; ``None`` where the file marks the point undefined."""


class MkaPitchTable(FrozenModel):
    """The ``linke/rechte Zahnflanke`` table: ``(tooth, fp, Fp, Fr)`` per tooth, in µm."""

    flank: Flank
    rows: tuple[tuple[int, float, float, float], ...]


class MkaPosition(FrozenModel):
    """One row of the ``Teilung:`` table: the probe contact of one tooth flank."""

    tooth: int
    side: Literal["L", "R"]
    phi_deg: float
    x_mm: float
    y_mm: float
    z_mm: float


class MkaFile(FrozenModel):
    header: P40Header
    curves: tuple[MkaCurve, ...]
    diameter_height_mm: float | None
    """Axial position of the diameter measurement (``Fußkreisdurchmesser / Höhe : 7.500``)."""
    root_diameters_mm: tuple[float, ...]
    tip_diameters_mm: tuple[float, ...]
    pitch_tables: tuple[MkaPitchTable, ...]
    positions: tuple[MkaPosition, ...]
    path: str | None = None

    def curve(self, block: str, tooth: int, flank: Flank) -> MkaCurve:
        for curve in self.curves:
            if (
                curve.block == block
                and curve.tooth == tooth
                and curve.flank == flank
                and curve.tooth_tag == ""
            ):
                return curve
        raise ParseError(f"no {block} curve of tooth {tooth} {flank}")

    def pitch_table(self, flank: Flank) -> MkaPitchTable:
        for table in self.pitch_tables:
            if table.flank == flank:
                return table
        raise ParseError(f"no pitch table of the {flank} flank")


def _decode(data: bytes, where: str) -> str:
    try:
        return data.decode(ENCODING)
    except UnicodeDecodeError as error:
        raise ParseError(f"{where}: not UTF-8 ({error.reason} at byte {error.start})") from None


def _split_lines(text: str) -> list[str]:
    """Lines of the text; a byte order mark that survived the decoding is dropped."""
    return text.lstrip("﻿").replace("\r\n", "\n").replace("\r", "\n").split("\n")


def parse_header(lines: list[str], *, expected: FileKind, where: str) -> tuple[P40Header, int]:
    """The preamble and the numbered header lines; returns the header and the index of the first
    line after it (the first result line of a ``.mew``, the first block of a ``.mka``)."""
    if not lines or not (match := _HEADER.match(lines[0].strip())):
        raise ParseError(f"{where}: line 1 is not 'HEADER KS.MW.FILE' / 'HEADER KS.MK.FILE'")
    kind = match.group(1)
    if kind != expected:
        raise ParseError(f"{where}: a KS.{kind}.FILE, expected KS.{expected}.FILE")
    preamble: list[tuple[str, str]] = []
    entries: list[P40HeaderLine] = []
    index = 1
    seen_numbered = False
    while index < len(lines):
        raw = lines[index]
        stripped = raw.strip()
        numbered = _HEADER_LINE.match(raw)
        if numbered:
            seen_numbered = True
            code = int(numbered.group(1))
            fields = [f.strip() for f in numbered.group(2).split(":")]
            label = _label(fields[0])
            raw = _SPACES.sub(" ", numbered.group(2).partition(":")[2]).strip()
            if any(entry.code == code for entry in entries):
                raise ParseError(f"{where}: line {index + 1}: header code {code} repeated")
            entries.append(
                P40HeaderLine(
                    code=code, label=label, raw=raw, fields=tuple(fields[1:]), line=index + 1
                )
            )
            index += 1
            continue
        if not stripped:
            index += 1
            continue
        if _RESULT_LINE.match(raw) or _CURVE_HEAD.match(stripped) or _BLOCK_TITLE.match(stripped):
            break
        if seen_numbered:
            raise ParseError(f"{where}: line {index + 1}: not a header line: {stripped!r}")
        preamble.append(_preamble_entry(stripped, where, index + 1))
        index += 1
    if not entries:
        raise ParseError(f"{where}: no numbered header lines")
    header = P40Header(file_kind=expected, preamble=tuple(preamble), lines=tuple(entries))
    return header, index


def parse_mew(text: str, *, path: str | None = None) -> MewFile:
    """A ``.mew`` value file from its text."""
    where = path or "<mew>"
    lines = _split_lines(text)
    header, index = parse_header(lines, expected="MW", where=where)
    values: list[MewValue] = []
    codes: set[int] = set()
    for number, raw in enumerate(lines[index:], start=index + 1):
        if not raw.strip():
            continue
        match = _RESULT_LINE.match(raw)
        if match is None:
            raise ParseError(f"{where}: line {number}: not a result line: {raw.strip()!r}")
        code = int(match.group(1))
        if code in codes:
            raise ParseError(f"{where}: line {number}: result code {code} repeated")
        codes.add(code)
        value = _number(match.group(3), f"{where}: line {number}")
        placeholder: Placeholder | None = None
        if value == NOT_MEASURED:
            placeholder = "not_measured"
        elif value == NOT_AVAILABLE:
            placeholder = "not_available"
        values.append(
            MewValue(
                code=code,
                label=_SPACES.sub(" ", match.group(2)).strip(),
                value=None if placeholder else value,
                placeholder=placeholder,
                line=number,
            )
        )
    if not values:
        raise ParseError(f"{where}: no result lines")
    return MewFile(header=header, values=tuple(values), path=path)


def load_mew(path: Path) -> MewFile:
    return parse_mew(_decode(Path(path).read_bytes(), str(path)), path=str(path))


def _read_values(
    lines: list[str], index: int, count: int, undefined: float, where: str
) -> tuple[tuple[float | None, ...], int]:
    """``count`` curve values from line ``index`` on; returns them and the next line index."""
    values: list[float | None] = []
    while len(values) < count:
        if index >= len(lines):
            raise ParseError(f"{where}: curve ends after {len(values)} of {count} values")
        raw = lines[index].strip()
        index += 1
        if not raw:
            continue
        for token in raw.split():
            value = _number(token, f"{where}: line {index}")
            # the undefined marker is the most negative number the format prints (three decimals);
            # anything at or below it is undefined, whatever the rounding of the file
            values.append(None if value <= undefined + 1.0 else value)
        if len(values) > count:
            raise ParseError(f"{where}: line {index}: curve has more than {count} values")
    return tuple(values), index


def _read_numbers(lines: list[str], index: int, where: str) -> tuple[tuple[float, ...], int]:
    """The numbers of the next non-empty line."""
    while index < len(lines) and not lines[index].strip():
        index += 1
    if index >= len(lines):
        raise ParseError(f"{where}: expected a line of numbers, found the end of the file")
    raw = lines[index].strip()
    return tuple(_number(t, f"{where}: line {index + 1}") for t in raw.split()), index + 1


def parse_mka(text: str, *, path: str | None = None) -> MkaFile:
    """A ``.mka`` curve file from its text."""
    where = path or "<mka>"
    lines = _split_lines(text)
    header, index = parse_header(lines, expected="MK", where=where)
    undefined = header.undefined_point
    curves: list[MkaCurve] = []
    block: str | None = None
    diameter_height: float | None = None
    root: tuple[float, ...] = ()
    tip: tuple[float, ...] = ()
    tables: list[MkaPitchTable] = []
    positions: list[MkaPosition] = []
    while index < len(lines):
        raw = lines[index]
        stripped = raw.strip()
        if not stripped:
            index += 1
            continue
        if (head := _CURVE_HEAD.match(stripped)) is not None:
            title = head.group("block") or block
            if title is None:
                raise ParseError(f"{where}: line {index + 1}: curve without a block title")
            count = int(head.group("count"))
            values, index = _read_values(lines, index + 1, count, undefined, where)
            curves.append(
                MkaCurve(
                    block=title,
                    tooth=int(head.group("tooth")),
                    tooth_tag=head.group("tag") or "",
                    trace_kind=head.group("kind"),
                    trace_index=int(head.group("index")) if head.group("index") else None,
                    flank=head.group("flank"),
                    count=count,
                    axis=head.group("axis"),
                    position=_number(head.group("position"), f"{where}: line {index}"),
                    values=values,
                )
            )
            continue
        if (title := _BLOCK_TITLE.match(stripped)) is not None:
            name = title.group("title")
            if name == "Teilung":
                index = _read_positions(lines, index + 1, positions, where)
                block = None
                continue
            block = name
            index += 1
            continue
        if (diameter := _DIAMETER_HEAD.match(stripped)) is not None:
            height = _number(diameter.group(2), f"{where}: line {index + 1}")
            if diameter_height is not None and height != diameter_height:
                raise ParseError(f"{where}: line {index + 1}: diameters at two heights")
            diameter_height = height
            numbers, index = _read_numbers(lines, index + 1, where)
            if diameter.group(1).startswith("Fuß"):
                root = numbers
            else:
                tip = numbers
            continue
        if (table := _TABLE_TITLE.match(stripped)) is not None:
            flank: Flank = "links" if table.group(1) == "linke" else "rechts"
            index = _read_pitch_table(lines, index + 1, flank, tables, where)
            continue
        raise ParseError(f"{where}: line {index + 1}: not understood: {stripped!r}")
    if not curves:
        raise ParseError(f"{where}: no curves")
    return MkaFile(
        header=header,
        curves=tuple(curves),
        diameter_height_mm=diameter_height,
        root_diameters_mm=root,
        tip_diameters_mm=tip,
        pitch_tables=tuple(tables),
        positions=tuple(positions),
        path=path,
    )


def _read_pitch_table(
    lines: list[str], index: int, flank: Flank, tables: list[MkaPitchTable], where: str
) -> int:
    while index < len(lines) and not lines[index].strip():
        index += 1
    if index >= len(lines) or not _TABLE_HEAD.match(lines[index]):
        raise ParseError(f"{where}: line {index + 1}: expected 'Zahn-Nr. fp Fp Fr'")
    index += 1
    rows: list[tuple[int, float, float, float]] = []
    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped:
            if rows:
                break
            index += 1
            continue
        tokens = stripped.split()
        if len(tokens) != 4 or not tokens[0].isdigit():
            break
        numbers = [_number(t, f"{where}: line {index + 1}") for t in tokens[1:]]
        rows.append((int(tokens[0]), numbers[0], numbers[1], numbers[2]))
        index += 1
    if not rows:
        raise ParseError(f"{where}: line {index + 1}: empty pitch table of the {flank} flank")
    expected = list(range(1, len(rows) + 1))
    if [row[0] for row in rows] != expected:
        raise ParseError(f"{where}: pitch table of the {flank} flank does not count 1..{len(rows)}")
    tables.append(MkaPitchTable(flank=flank, rows=tuple(rows)))
    return index


def _read_positions(lines: list[str], index: int, out: list[MkaPosition], where: str) -> int:
    while index < len(lines) and not lines[index].strip():
        index += 1
    if index >= len(lines) or not _POSITION_HEAD.match(lines[index]):
        raise ParseError(f"{where}: line {index + 1}: expected 'Z-Nr. Seite PHI X Y Z'")
    index += 1
    while index < len(lines):
        stripped = lines[index].strip()
        if not stripped:
            index += 1
            continue
        tokens = stripped.split()
        if len(tokens) != 6 or not tokens[0].isdigit() or tokens[1] not in ("L", "R"):
            raise ParseError(f"{where}: line {index + 1}: not a position row: {stripped!r}")
        numbers = [_number(t, f"{where}: line {index + 1}") for t in tokens[2:]]
        out.append(
            MkaPosition(
                tooth=int(tokens[0]),
                side=tokens[1],
                phi_deg=numbers[0],
                x_mm=numbers[1],
                y_mm=numbers[2],
                z_mm=numbers[3],
            )
        )
        index += 1
    if not out:
        raise ParseError(f"{where}: empty 'Teilung:' table")
    return index


def load_mka(path: Path) -> MkaFile:
    return parse_mka(_decode(Path(path).read_bytes(), str(path)), path=str(path))


__all__ = [
    "ENCODING",
    "NOT_AVAILABLE",
    "NOT_MEASURED",
    "UNDEFINED_POINT",
    "Flank",
    "MewFile",
    "MewValue",
    "MkaCurve",
    "MkaFile",
    "MkaPitchTable",
    "MkaPosition",
    "P40Header",
    "P40HeaderLine",
    "load_mew",
    "load_mka",
    "parse_header",
    "parse_mew",
    "parse_mka",
]
