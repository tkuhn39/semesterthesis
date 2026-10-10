"""Grammar of the Hommel-Etamic roughness exports."""

import pytest

from gearcore.data import measurement_fixture
from gearcore.errors import ParseError
from gearcore.io.hommel import load_roughness_table, parse_roughness_table


def test_export_with_remark_column() -> None:
    table = load_roughness_table(measurement_fixture("roughness_F4092_97340_li.utf16.txt"))
    assert table.title == "1.2mm-0.25mm-TKU300_3Mp F4092"
    assert len(table.columns) == 51 and table.columns[0] == "Messung-1.Ra"
    assert table.columns[-3:] == ("MeE-Nr.", "Bemerkung", "Flanke/Seite")
    assert table.unit("Messung-1.Ra") == "µm" and table.unit("Messung-1.A1") == "µm²/mm"
    assert table.unit("MeE-Nr.") == ""
    (record,) = table.records
    assert record.measured_at == "31.05.2026/15:58:14"
    assert record.me == "97340" and record.flank == "li" and record.remark == "neu"
    assert record.value("Messung-1.Ra") == 0.649 and record.value("Messung-3.Rz") == 9.644
    assert record.value("Xq-Ra") == 1.022
    traces = [record.value(f"Messung-{i}.Ra") for i in (1, 2, 3)]
    assert abs(sum(traces) / 3.0 - record.value("Xq-Ra")) <= 0.001
    with pytest.raises(ParseError):
        record.value("Xq-Rq")


def test_twin_export_without_remark_has_the_same_numbers() -> None:
    first = load_roughness_table(measurement_fixture("roughness_F4092_97340_li.utf16.txt"))
    twin = load_roughness_table(measurement_fixture("roughness_F4092_97340_neu_li.utf16.txt"))
    assert len(twin.columns) == 50 and not twin.records[0].has("Bemerkung")
    assert twin.records[0].remark is None
    assert twin.records[0].numbers == first.records[0].numbers


def _export(
    data_row: str,
    *,
    names: str = "Merkmalsbeschreibung\tMessung-1.Ra\tXq-Ra\tDatenfeld(MeE-Nr.:)\tDatenfeld(Flanke/Seite:)",
) -> bytes:
    text = "\n".join(
        ["title", names, "Einheit\tµm\tµm", "Nachkommastellen\t3\t3", "", data_row, ""]
    )
    return b"\xff\xfe" + text.encode("utf-16-le")


def test_minimal_export() -> None:
    table = parse_roughness_table(_export("01.01.2026/10:00:00\t0,5\t0,5\t12345\tre"))
    record = table.records[0]
    assert record.value("Messung-1.Ra") == 0.5 and record.me == "12345" and record.flank == "re"
    assert table.decimals == (
        ("Messung-1.Ra", 3),
        ("Xq-Ra", 3),
        ("MeE-Nr.", None),
        ("Flanke/Seite", None),
    )


@pytest.mark.parametrize(
    "data, message",
    [
        (b"title\nnames\n", "byte order mark"),
        (_export("01.01.2026/10:00:00\t0.5\t0,5\t12345\tre"), "non-numeric"),
        (_export("2026-01-01\t0,5\t0,5\t12345\tre"), "not a timestamp"),
        (_export("01.01.2026/10:00:00\t0,5\t0,5\t12345"), "cells, expected"),
        (
            _export("01.01.2026/10:00:00\t0,5\t0,5\t12345\tre", names="x\ta\tb\tc\td"),
            "Merkmalsbeschreibung",
        ),
    ],
)
def test_malformed_exports_are_parse_errors(data: bytes, message: str) -> None:
    with pytest.raises(ParseError, match=message):
        parse_roughness_table(data)
