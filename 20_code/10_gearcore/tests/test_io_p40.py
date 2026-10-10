"""Grammar of the Klingelnberg P40 exports: value files (.mew) and curve files (.mka)."""

import math
from pathlib import Path

import pytest

from gearcore.data import measurement_fixture
from gearcore.errors import ParseError
from gearcore.io.p40 import (
    NOT_AVAILABLE,
    NOT_MEASURED,
    MewFile,
    MkaFile,
    load_mew,
    load_mka,
    parse_mew,
    parse_mka,
)


@pytest.fixture(scope="module")
def wheel() -> MewFile:
    return load_mew(measurement_fixture("wheel_97340-neu.mew"))


@pytest.fixture(scope="module")
def pinion() -> MewFile:
    return load_mew(measurement_fixture("pinion_95911-neu.mew"))


@pytest.fixture(scope="module")
def curves() -> MkaFile:
    return load_mka(measurement_fixture("wheel_97340-neu_trimmed.mka"))


def test_header_preamble_and_numbered_lines(wheel: MewFile) -> None:
    header = wheel.header
    assert header.file_kind == "MW"
    assert header.preamble_value("TYPE") == "STI"
    assert header.preamble_value("FILTER LEAD") == "F:S 2"
    assert header.preamble_value("SEPARATOR") == ":"
    assert header.text(3) == "10:15:53 / 10:24:32"
    assert header.preamble_value("PROFILE") == "diameter"
    assert header.undefined_point == -2147483.648
    assert header.text(7) == "97340-neu"
    assert header.text(2) == "09.05.26"
    assert header.require(22).label == "Zähnezahl z"
    assert header.number(22) == 52.0
    assert header.require(26).label == "Zahnbreite [mm]"
    assert header.numbers(27) == (54.0219,)
    assert header.numbers(41) == (50.156, 50.156)
    assert header.require(82).fields == ("FHAL", "7", "-7", "0", "5.5516")
    assert header.numbers(82) == (7.0, -7.0, 0.0, 5.5516)
    assert header.numbers(210) == (10.0, 7.0)
    assert header.require(165).fields[-5:] == ("1", "L", "+", "R", "-")
    assert header.text(165).endswith("R_FHB: 1 : L: + : R: -")
    assert header.get(431) is None


def test_result_lines_of_the_wheel(wheel: MewFile) -> None:
    assert len(wheel.values) == 172
    assert wheel.get(10130).label == "fHbm links" and wheel.get(10130).value == 7.2
    assert wheel.by_label("fHb links 12").value == 55.9
    assert wheel.by_label("Fuß  m").value == 49.5 and wheel.get(26430).label == "Fuß m"
    assert wheel.get(26740).value == 54.048
    # trap of the export: the per-tooth tip lines repeat the per-tooth root values (MEAS-07)
    assert [wheel.get(c).value for c in (26711, 26712)] == [
        wheel.get(c).value for c in (26411, 26412)
    ]
    assert wheel.get(31610).value == 30.1 and wheel.get(32810).value == 54.529
    assert wheel.get(34610).value == 16.972 and wheel.get(35210).value == 16.983
    # placeholders are typed, never a number
    assert wheel.get(26450).value is None and wheel.get(26450).placeholder == "not_available"
    assert wheel.get(26511).value is None and wheel.get(26511).placeholder == "not_measured"
    assert NOT_MEASURED == -9999.0 and NOT_AVAILABLE == 8999.0
    assert not wheel.has(21611)


def test_result_lines_of_the_pinion(pinion: MewFile) -> None:
    assert len(pinion.values) == 130
    assert pinion.header.number(22) == 51.0
    assert pinion.header.text(8) == "Stahlritzel mit KR"
    assert pinion.header.numbers(431) == (51.946, 51.946)
    assert pinion.header.numbers(432) == (52.88, 52.88)
    assert pinion.get(21611).label == "fKo links 1" and pinion.get(21611).value == -23.2
    assert pinion.get(21630).value == -23.1 and pinion.get(21640).value == -23.6
    assert pinion.get(26740).value == 52.883 and pinion.get(26430).value == 48.38


@pytest.mark.parametrize(
    "text",
    [
        "TYPE STI\n  7 :ME: 1\n10111 : fHb links 1 : 1.0\n",  # no HEADER line
        "HEADER KS.MK.FILE\nTYPE STI\n  7 :ME: 1\n10111 : fHb links 1 : 1.0\n",  # curves, not values
        "HEADER KS.MW.FILE\nTYPE STI\n  7 :ME: 1\n10111 : fHb links 1 : 1.0\n10111 : fHb links 1 : 2.0\n",
        "HEADER KS.MW.FILE\nTYPE STI\n  7 :ME: 1\n10111 : fHb links 1 : 1,0\n",  # decimal comma
        "HEADER KS.MW.FILE\nTYPE STI\n  7 :ME: 1\n10111 : fHb links 1 : nan\n",
        "HEADER KS.MW.FILE\nTYPE STI\n  7 :ME: 1\nsomething else\n",
        "HEADER KS.MW.FILE\nTYPE STI\n  7 :ME: 1\n  7 :ME: 2\n10111 : fHb links 1 : 1.0\n",
        "HEADER KS.MW.FILE\nTYPE STI\n",  # no numbered header lines
        "HEADER KS.MW.FILE\nTYPE STI\n  7 :ME: 1\n",  # no result lines
    ],
)
def test_malformed_value_files_are_parse_errors(text: str) -> None:
    with pytest.raises(ParseError):
        parse_mew(text)


def test_minimal_value_file() -> None:
    mew = parse_mew(
        "﻿HEADER KS.MW.FILE\r\nTYPE  STI ! x\r\n\r\n  7   :ME....: 1\r\n10111 : fHb links 1  :   -2.9\r\n"
    )
    assert mew.header.text(7) == "1" and mew.get(10111).value == -2.9
    with pytest.raises(ParseError):
        mew.get(99999)
    with pytest.raises(ParseError):
        mew.by_label("fHb")


def test_header_numbers_accept_fortran_exponents() -> None:
    mew = parse_mew("HEADER KS.MW.FILE\n  41 :Start...: 1d5  2.0\n10111 : x : 1.0\n")
    assert mew.header.numbers(41) == (1.0e5, 2.0)


def test_latin_1_bytes_are_refused(tmp_path: Path) -> None:
    path = tmp_path / "latin.mew"
    path.write_bytes("HEADER KS.MW.FILE\n  22 :Zähnezahl: 52\n10111 : x : 1.0\n".encode("latin-1"))
    with pytest.raises(ParseError, match="not UTF-8"):
        load_mew(path)


def test_curve_file(curves: MkaFile) -> None:
    assert curves.header.file_kind == "MK" and curves.header.text(7) == "97340-neu"
    assert [(c.block, c.tooth, c.flank, c.axis) for c in curves.curves] == [
        ("Flankenlinie", 44, "links", "x"),
        ("Flankenlinie", 1, "rechts", "x"),
        ("Profil", 44, "links", "z"),
        ("Profil", 1, "rechts", "z"),
    ]
    lead = curves.curve("Flankenlinie", 44, "links")
    assert lead.count == 480 and len(lead.values) == 480
    assert lead.values[:12] == (None,) * 12 and lead.values[12] == -56.333
    # the x of a lead block is the roll length at the lead measuring circle (header code 46)
    d_v = curves.header.number(46)
    d_b = 52.0 * math.cos(math.radians(20.0))
    assert abs(lead.position - math.sqrt((0.5 * d_v) ** 2 - (0.5 * d_b) ** 2)) < 1.0e-3
    profile = curves.curve("Profil", 44, "links")
    assert profile.position == 7.5 and profile.values[0] == 20.39
    assert curves.diameter_height_mm == 7.5
    assert curves.root_diameters_mm == (49.4891, 49.5206, 49.4804, 49.5151, 49.4966)
    assert len(curves.tip_diameters_mm) == 5
    left, right = curves.pitch_table("links"), curves.pitch_table("rechts")
    assert len(left.rows) == 52 and left.rows[0] == (1, 0.662, 0.662, 0.778)
    assert left.rows[37] == (38, -5.275, -15.165, 4.779) and len(right.rows) == 52
    assert len(curves.positions) == 104
    assert curves.positions[0].tooth == 1 and curves.positions[0].side == "R"
    assert curves.positions[1].side == "L" and curves.positions[-1].tooth == 1
    with pytest.raises(ParseError):
        curves.curve("Profil", 12, "links")


def test_malformed_curve_files_are_parse_errors() -> None:
    head = "HEADER KS.MK.FILE\nTYPE STI\n  7 :ME: 1\n"
    with pytest.raises(ParseError, match="curve ends"):
        parse_mka(head + "Profil:\nZahn-Nr.: 1 links / 24  Werte  z= 7.5\n 1.0 2.0 3.0\n")
    with pytest.raises(ParseError, match="more than"):
        parse_mka(head + "Profil:\nZahn-Nr.: 1 links / 2  Werte  z= 7.5\n 1.0 2.0 3.0\n")
    with pytest.raises(ParseError, match="without a block title"):
        parse_mka(head + "Zahn-Nr.: 1 links / 2  Werte  z= 7.5\n 1.0 2.0\n")
    with pytest.raises(ParseError, match="not understood"):
        parse_mka(head + "Profil:\nZahn-Nr.: 1 links / 2  Werte  z= 7.5\n 1.0 2.0\nunexpected\n")
    with pytest.raises(ParseError, match="no curves"):
        parse_mka(head + "Profil:\n")
    with pytest.raises(ParseError, match="count 1"):
        parse_mka(
            head + "Profil:\nZahn-Nr.: 1 links / 2  Werte  z= 7.5\n 1.0 2.0\n"
            "        linke Zahnflanke\n        Zahn-Nr.  fp  Fp  Fr\n\n  2  0.1 0.2 0.3\n"
        )


def test_minimal_curve_file_with_undefined_points() -> None:
    text = (
        "HEADER KS.MK.FILE\nUNDEFINED -2147483.648 ! Undefined\n  7 :ME: 1\n"
        "Flankenlinie:\nZahn-Nr.: 3 rechts / 4  Werte  x= 8.742\n -2147483.648 1.5\n 2.5 .25\n"
        "Verschränkung: Zahn-Nr.: 1k /Flankenlinie:3 links / 2  Werte  x= 10.263\n 1.0 2.0\n"
        "Fußkreisdurchmesser / Höhe :     7.500\n   49.5 49.6\n"
        "Kopfkreisdurchmesser / Höhe :     7.500\n   54.0 54.1\n"
        "        linke Zahnflanke\n        Zahn-Nr.  fp  Fp  Fr\n\n  1  0.1 0.2 0.3\n  2  -0.1 0.1 -0.3\n\n"
        "Teilung:\nZ-Nr. Seite PHI X Y Z\n  1   R  0.0000  .1198  25.5249  87.2302\n"
    )
    mka = parse_mka(text)
    assert mka.curve("Flankenlinie", 3, "rechts").values == (None, 1.5, 2.5, 0.25)
    rounded = parse_mka(text.replace("-2147483.648 1.5", "-2147483.65 1.5"))
    assert rounded.curve("Flankenlinie", 3, "rechts").values[0] is None
    twist = mka.curves[1]
    assert twist.block == "Verschränkung" and twist.tooth == 1 and twist.tooth_tag == "k"
    assert twist.trace_kind == "Flankenlinie" and twist.trace_index == 3
    assert mka.root_diameters_mm == (49.5, 49.6) and mka.tip_diameters_mm == (54.0, 54.1)
    assert mka.pitch_table("links").rows == ((1, 0.1, 0.2, 0.3), (2, -0.1, 0.1, -0.3))
    assert mka.positions[0].x_mm == 0.1198


def test_twist_traces_of_a_real_curve_file(measurements_root: Path) -> None:
    path = next((measurements_root / "GINA").rglob("97340-neu.mka"))
    mka = load_mka(path)
    twists = [c for c in mka.curves if c.block == "Verschränkung"]
    assert len(twists) == 8 and {c.tooth_tag for c in twists} == {"f", "k", "u", "o"}
    assert {(c.trace_kind, c.trace_index) for c in twists} == {
        ("Flankenlinie", 1),
        ("Flankenlinie", 3),
        ("Profil", 1),
        ("Profil", 3),
    }
    assert all(c.count == 480 and len(c.values) == 480 for c in mka.curves)
    assert len([c for c in mka.curves if c.block == "Flankenlinie"]) == 10
