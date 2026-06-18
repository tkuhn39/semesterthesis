"""
@module: tests.test_rie
@context: I/O-layer tests — RIKOR (FVA 30) `.rie` input parser.
@role: The native `.rie` parser reads the RIKOR keyword-block input (multi-pair
       lines, repeated shaft-station rows) into the typed `RikorInput`, and parses
       every bundled standard-test example without loss.
"""

from pathlib import Path

import pytest

from app.io.rie import RikorInput, _tokenize, load_rie, parse_rie

_EXAMPLES = (
    Path(__file__).resolve().parents[3]
    / "30_references_and_examples"
    / "35_Rikor"
    / "RIKOR_exec"
    / "work"
    / "Beispiele"
)
_EX001 = _EXAMPLES / "001_eine_stufe" / "1_Eingabe" / "rikor.rie"


def test_tokenize_multi_pair_line() -> None:
    """A line with several ``KEY = value`` pairs splits into ordered items."""
    row = _tokenize("UK = 0 DA = 108 TUAKA = -5975")
    assert row is not None
    assert row.get("UK") == ["0"]
    assert row.get("DA") == ["108"]
    assert row.get("TUAKA") == ["-5975"]
    assert row.has("UK", "DA")


def test_tokenize_strips_inline_comment_and_normalizes_equals() -> None:
    assert _tokenize("KA=1.5  # design factor").get("KA") == ["1.5"]  # type: ignore[union-attr]
    assert _tokenize("# whole line") is None
    assert _tokenize("S_ABW_BLV_TOPO      = 1").get("S_ABW_BLV_TOPO") == ["1"]  # type: ignore[union-attr]


def test_parse_rie_groups_repeated_blocks() -> None:
    """Repeated ``$`` blocks (LAGER, Welle) each become a section."""
    text = "$LAGER\nIW_I = 1\n##\n$LAGER\nIW_I = 2\n$ Welle\nIW = 1\nUK = 0 DA = 50\n"
    rie = parse_rie(text)
    assert len(rie.named("LAGER")) == 2
    assert rie.named("LAGER")[1].scalar("IW_I") == "2"
    assert rie.first_named("Welle").scalar("IW") == "1"  # type: ignore[union-attr]


@pytest.mark.skipif(not _EX001.exists(), reason="RIKOR example 001 not present")
def test_rikor_input_from_example_001() -> None:
    """The single-stage example maps to a complete typed model."""
    ri = RikorInput.load(_EX001)
    # config
    assert ri.config.application_factor == 1.5
    assert ri.config.contact_positions == 12
    assert ri.config.lubricant == "ISO-VG-220"
    # shafts: drive (11 stations, torque) + driven (8 stations)
    assert [s.index for s in ri.shafts] == [1, 2]
    drive = ri.shafts[0]
    assert len(drive.stations) == 11
    assert drive.applied_torque_nm == -5975.0
    assert drive.stations[0].outer_diameter_mm == 108.0
    assert drive.stations[-1].position_mm == 789.0
    # bearings: two per shaft, with the fixed (Festlager) flagged
    assert len(ri.bearings) == 4
    assert ri.bearings_on(1)[0].fixed_axial is True
    assert ri.bearings_on(1)[0].position_mm == 334.5
    assert ri.bearings[0].radial_stiffness_n_per_um == 1e7
    # gears
    pinion = ri.gear_on(1)
    wheel = ri.gear_on(2)
    assert pinion is not None and wheel is not None
    assert (pinion.teeth, wheel.teeth) == (14, 59)
    assert pinion.normal_module_mm == 8.0
    assert pinion.profile_shift == 0.4713
    assert pinion.helix_angle_deg == -11.0
    assert wheel.helix_angle_deg == 11.0
    assert pinion.face_width_mm == 137.0 and wheel.face_width_mm == 127.0
    assert pinion.tip_diameter_mm == 137.97
    assert pinion.material == "18CrNiMo7-6"
    # stage + correction
    assert ri.stage is not None
    assert ri.stage.face_steps == 50
    assert ri.stage.f_hbeta_max_um == 50.0
    assert ri.corrections[0].crowning_um == 7.0


@pytest.mark.skipif(not _EXAMPLES.exists(), reason="RIKOR examples not present")
def test_all_bundled_examples_parse() -> None:
    """Every bundled `.rie` standard-test parses without error."""
    files = sorted(_EXAMPLES.glob("*/1_Eingabe/rikor.rie"))
    assert files, "expected bundled RIKOR examples"
    for rie in files:
        model = RikorInput.from_rie(load_rie(rie))
        assert model.shafts, f"{rie.parent.parent.name}: no shafts parsed"
