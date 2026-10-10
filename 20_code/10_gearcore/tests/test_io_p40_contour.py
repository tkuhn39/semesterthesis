"""Grammar of the P40 contour scans."""

from pathlib import Path

import pytest

from gearcore.data import measurement_fixture
from gearcore.errors import ParseError
from gearcore.io.p40_contour import load_contour_scans, parse_contour_scans


def test_complete_scan_of_the_steel_pinion() -> None:
    (scan,) = load_contour_scans(measurement_fixture("contour_86481_Z01.scan.txt"))
    assert scan.name == "contour_86481_Z01.scan" and scan.block == "B"
    assert scan.z_mm == 87.572 and len(scan.points_mm) == 1088
    assert scan.points_mm[0] == (3.418, 26.143) and scan.points_mm[-1] == (-3.611, 25.909)
    xy = scan.as_array()
    assert xy.shape == (1088, 2) and xy.dtype.kind == "f"


def test_a_file_with_two_blocks_gives_two_scans() -> None:
    scans = load_contour_scans(measurement_fixture("contour_97341_z36_two_blocks.scan.txt"))
    assert [s.block for s in scans] == ["A", "B"]
    assert [s.name for s in scans] == [
        "contour_97341_z36_two_blocks.scan[A]",
        "contour_97341_z36_two_blocks.scan[B]",
    ]
    assert [len(s.points_mm) for s in scans] == [60, 60]
    assert [s.z_mm for s in scans] == [88.366, 88.398]


def _rows(n: int, z: str = "1.0") -> str:
    return "".join(f"{i}; {0.01 * i:.3f}; 26.0; {z};\n" for i in range(1, n + 1))


@pytest.mark.parametrize(
    "text, message",
    [
        ("[A]\n" + _rows(5), "only 5 points"),
        ("[A]\n" + _rows(10) + "12; 0.1; 26.0; 1.0;\n", "index 12, expected 11"),
        ("[A]\n" + _rows(9) + "10; 0.1; 26.0; 2.0;\n", "not a plane section"),
        (_rows(10), "before the first block tag"),
        ("[X]\n" + _rows(10), "unknown block tag"),
        ("[A]\n" + _rows(10) + "11; a; 26.0; 1.0;\n", "not a point line"),
        ("", "no block tag"),
    ],
)
def test_malformed_scans_are_parse_errors(text: str, message: str) -> None:
    with pytest.raises(ParseError, match=message):
        parse_contour_scans(text, name="x")


def test_non_ascii_bytes_are_refused(tmp_path: Path) -> None:
    path = tmp_path / "scan.DAT"
    path.write_bytes(b"[A]\n" + _rows(10).encode() + "ü".encode())
    with pytest.raises(ParseError, match="not ASCII"):
        load_contour_scans(path)
