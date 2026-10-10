"""Hommel-Etamic roughness exports (EVOVIS): the ASCII table of one measurement series.

Grammar (144 files of 2026 read): UTF-16 LE with byte order mark, tab-separated, decimal comma.
Line 1 is the title of the measuring program (``1.2mm-0.25mm-TKU300_3Mp F4092``), line 2 the
column names (``Merkmalsbeschreibung``, then ``Messung-1.Ra`` … ``Messung-3.A2``, the means
``Xq-Rmax``, ``Xq-Rz``, ``Xq-Ra`` and the data fields ``Datenfeld(MeE-Nr.:)``,
``Datenfeld(Bemerkung:)``, ``Datenfeld(Flanke/Seite:)``), line 3 the units, line 4 the number of
decimals, line 5 empty, then one data row per series (``31.05.2026/15:58:14`` followed by the
values). Some exports lack the ``Bemerkung`` column, so every value is looked up by its column
name, never by position. The parameters keep the instrument's names (``Ra``, ``Rz``, ``Rmax``,
``R∆q`` …); which of them are quantities of a norm is decided in ``gearcore.measurement.roughness``.

The raw profiles (``.hwp``) are binary with a 266-byte header; their record layout is not
confirmed, so they are not read here (extension point, see ``extension_points.md``).
"""

import math
import re
from pathlib import Path

from gearcore.errors import ParseError
from gearcore.models.common import FrozenModel

BOM_UTF16_LE = b"\xff\xfe"
_NUMBER = re.compile(r"^[-+]?\d+(?:,\d+)?$")
_TIMESTAMP = re.compile(r"^\d{2}\.\d{2}\.\d{4}/\d{2}:\d{2}:\d{2}$")
_DATA_FIELD = re.compile(r"^Datenfeld\((.+?):?\)$")


class RoughnessRecord(FrozenModel):
    """One data row: the timestamp, every numeric column and every text column by name."""

    measured_at: str
    numbers: tuple[tuple[str, float], ...]
    texts: tuple[tuple[str, str], ...]

    def value(self, column: str) -> float:
        for name, value in self.numbers:
            if name == column:
                return value
        raise ParseError(f"no numeric column {column!r}")

    def text(self, column: str) -> str:
        for name, value in self.texts:
            if name == column:
                return value
        raise ParseError(f"no text column {column!r}")

    def has(self, column: str) -> bool:
        return any(name == column for name, _ in self.numbers) or any(
            name == column for name, _ in self.texts
        )

    @property
    def me(self) -> str:
        return self.text("MeE-Nr.")

    @property
    def flank(self) -> str:
        return self.text("Flanke/Seite")

    @property
    def remark(self) -> str | None:
        return self.text("Bemerkung") if self.has("Bemerkung") else None


class RoughnessTable(FrozenModel):
    title: str
    columns: tuple[str, ...]
    """Column names of line 2 after the first (``Messung-1.Ra`` …, data fields by their key)."""
    units: tuple[tuple[str, str], ...]
    decimals: tuple[tuple[str, int | None], ...]
    """Printed decimals per numeric column; ``None`` for the text columns (data fields)."""
    records: tuple[RoughnessRecord, ...]
    path: str | None = None

    def unit(self, column: str) -> str:
        for name, unit in self.units:
            if name == column:
                return unit
        raise ParseError(f"no column {column!r}")


def _column_name(raw: str) -> str:
    field = _DATA_FIELD.match(raw.strip())
    return field.group(1) if field else raw.strip()


def _value(token: str, where: str) -> float:
    if not _NUMBER.match(token):
        raise ParseError(f"{where}: non-numeric token {token!r}")
    value = float(token.replace(",", "."))
    if not math.isfinite(value):
        raise ParseError(f"{where}: {token!r} exceeds the number range")
    return value


def parse_roughness_table(data: bytes, *, path: str | None = None) -> RoughnessTable:
    """The export from its bytes (the byte order mark is required: the instrument writes UTF-16)."""
    where = path or "<roughness>"
    if not data.startswith(BOM_UTF16_LE):
        raise ParseError(f"{where}: not a UTF-16 LE export (byte order mark missing)")
    text = data.decode("utf-16")
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    while lines and not lines[-1].strip():
        lines.pop()
    if len(lines) < 6:
        raise ParseError(
            f"{where}: {len(lines)} lines, expected title, names, units, decimals, data"
        )
    title = lines[0].strip()
    raw_names = [cell.strip() for cell in lines[1].split("\t")]
    names = [_column_name(cell) for cell in raw_names]
    text_columns = {_column_name(cell) for cell in raw_names if _DATA_FIELD.match(cell)}
    units = [cell.strip() for cell in lines[2].split("\t")]
    decimals = [cell.strip() for cell in lines[3].split("\t")]
    if names[0] != "Merkmalsbeschreibung":
        raise ParseError(f"{where}: line 2 does not start with 'Merkmalsbeschreibung'")
    # the unit and decimals lines stop before the text columns (data fields carry neither)
    if len(units) > len(names) or len(decimals) > len(names):
        raise ParseError(f"{where}: more units/decimals than the {len(names)} columns")
    units += [""] * (len(names) - len(units))
    decimals += [""] * (len(names) - len(decimals))
    if lines[4].strip():
        raise ParseError(f"{where}: line 5 is not empty")
    columns = tuple(names[1:])
    if len(set(columns)) != len(columns):
        raise ParseError(f"{where}: repeated column names")
    unit_pairs = tuple((name, unit) for name, unit in zip(columns, units[1:], strict=True))
    decimal_pairs: list[tuple[str, int | None]] = []
    for name, cell in zip(columns, decimals[1:], strict=True):
        if name in text_columns:
            decimal_pairs.append((name, None))
            continue
        if not cell.isdigit():
            raise ParseError(f"{where}: decimals of {name!r}: {cell!r}")
        decimal_pairs.append((name, int(cell)))
    records: list[RoughnessRecord] = []
    for number, raw in enumerate(lines[5:], start=6):
        if not raw.strip():
            continue
        cells = raw.split("\t")
        if len(cells) != len(names):
            raise ParseError(f"{where}: line {number}: {len(cells)} cells, expected {len(names)}")
        stamp = cells[0].strip()
        if not _TIMESTAMP.match(stamp):
            raise ParseError(f"{where}: line {number}: not a timestamp: {stamp!r}")
        numbers: list[tuple[str, float]] = []
        texts: list[tuple[str, str]] = []
        for name, cell in zip(columns, cells[1:], strict=True):
            token = cell.strip()
            if name in text_columns:
                texts.append((name, token))
            else:
                numbers.append((name, _value(token, f"{where}: line {number}: {name}")))
        records.append(
            RoughnessRecord(measured_at=stamp, numbers=tuple(numbers), texts=tuple(texts))
        )
    if not records:
        raise ParseError(f"{where}: no data row")
    return RoughnessTable(
        title=title,
        columns=columns,
        units=unit_pairs,
        decimals=tuple(decimal_pairs),
        records=tuple(records),
        path=path,
    )


def load_roughness_table(path: Path) -> RoughnessTable:
    return parse_roughness_table(Path(path).read_bytes(), path=str(path))


__all__ = [
    "BOM_UTF16_LE",
    "RoughnessRecord",
    "RoughnessTable",
    "load_roughness_table",
    "parse_roughness_table",
]
