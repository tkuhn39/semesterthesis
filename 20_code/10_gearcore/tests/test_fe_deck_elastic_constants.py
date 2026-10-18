"""The step W3 with the engineering constants of FVA 856 I Tabelle 4 instead of the
field-dependent elastic block of the CONVERSE card (ADR-116 item 51): the transcribed table,
the stability restrictions of the Abaqus material guide, the block replacement in the model
piece and the folder written by ``build_fe_decks.py decks --elastic-constants``."""

import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType

import pytest

from gearcore import data
from gearcore.errors import InputRangeError, ParseError
from gearcore.fe import deck as dk

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"

TABLE4_80C_QS = (4156.0, 1444.0, 1369.0, 0.423, 0.386, 0.495, 683.0, 585.0, 469.0)
TABLE4_80C_DY2 = (6193.0, 2931.0, 2861.0, 0.404, 0.380, 0.489, 1241.0, 1124.0, 974.0)

MODEL_PIECE = """*DISTRIBUTION TABLE, NAME=DIS_TAB_COORD
 COORD3D, COORD3D
*MATERIAL,\tNAME=PA46_GF30_QS_cond_aniso
*ELASTIC,TYPE=ENGINEERING CONSTANTS,DEPENDENCIES=2
 5130., 3000., 2900., 0.40, 0.39, 0.45, 1200., 1100.,
 1000., 23., 0.5, 0.25
 4000., 2500., 2400., 0.41, 0.39, 0.46, 900., 850.,
 800., 80., 0.5, 0.25
** a comment inside the block
 3900., 3900., 3900., 0.30, 0.30, 0.30, 1500., 1500.,
 1500., 80., 0.3333, 0.3333
*DENSITY
 1.4e-9, 23.
*EXPANSION,TYPE=ORTHO,ZERO=23,DEPENDENCIES=2
 2.0e-5, 6.0e-5, 6.0e-5, 80., 0.5, 0.25
*INITIAL CONDITIONS, TYPE=FIELD, VARIABLE=1
WHEEL-1.1, 0.6
*INITIAL CONDITIONS, TYPE=FIELD, VARIABLE=2
WHEEL-1.1, 0.1
"""


@pytest.fixture(scope="module")
def script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("build_fe_decks", SCRIPTS / "build_fe_decks.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_table4_is_transcribed_with_nine_stable_rows() -> None:
    table = data.load_fva856_table4()
    assert table["source"] == "FVA856-I:2022" and table["table"] == "Tabelle 4"
    assert table["printed_page"] == 23 and table["state"] == "konditioniert"
    assert len(table["rows"]) == 9
    assert data.fva856_table4_row(80.0, "QS") == TABLE4_80C_QS
    assert data.fva856_table4_row(80.0, "dy2") == TABLE4_80C_DY2
    assert data.fva856_table4_row(23.0, "QS")[0] == 6277.0
    assert data.fva856_table4_row(-20.0, "DY2")[8] == 3646.0
    for row in table["rows"]:
        left = dk.orthotropic_stability(row["values"])
        assert 0.0 < left < 1.0
    # the 80 degC QS row by hand: nu_21 = 0,423 * 1444 / 4156, nu_31 = 0,386 * 1369 / 4156,
    # nu_32 = 0,495 * 1369 / 1444
    n21 = 0.423 * 1444.0 / 4156.0
    n31 = 0.386 * 1369.0 / 4156.0
    n32 = 0.495 * 1369.0 / 1444.0
    expected = 1.0 - 0.423 * n21 - 0.495 * n32 - n31 * 0.386 - 2.0 * n21 * n32 * 0.386
    assert dk.orthotropic_stability(TABLE4_80C_QS) == pytest.approx(expected)
    with pytest.raises(InputRangeError, match="no row at 60"):
        data.fva856_table4_row(60.0, "QS")
    with pytest.raises(InputRangeError, match="rows:"):
        data.fva856_table4_row(80.0, "DY3")


def test_stability_restrictions_are_enforced() -> None:
    with pytest.raises(InputRangeError, match="nine engineering constants"):
        dk.orthotropic_stability(TABLE4_80C_QS[:8])
    with pytest.raises(InputRangeError, match="E_2 > 0"):
        dk.orthotropic_stability((4156.0, 0.0, 1369.0, 0.423, 0.386, 0.495, 683.0, 585.0, 469.0))
    with pytest.raises(InputRangeError, match=r"\|nu_12\| <"):
        dk.orthotropic_stability((1000.0, 1000.0, 1000.0, 1.0, 0.3, 0.3, 400.0, 400.0, 400.0))
    with pytest.raises(InputRangeError, match="nu_12 nu_21"):
        # every |nu_ij| below its bound, the determinant condition violated (nearly incompressible
        # and beyond: nu = 0,6 isotropic gives 1 - 3*0,36 - 2*0,216 < 0)
        dk.orthotropic_stability((1000.0, 1000.0, 1000.0, 0.6, 0.6, 0.6, 400.0, 400.0, 400.0))
    # an isotropic set: 1 - 3 nu^2 - 2 nu^3
    assert dk.orthotropic_stability(
        (1000.0, 1000.0, 1000.0, 0.3, 0.3, 0.3, 400.0, 400.0, 400.0)
    ) == pytest.approx(1.0 - 3.0 * 0.09 - 2.0 * 0.027)


def test_replace_elastic_block_keeps_every_other_block() -> None:
    out = dk.replace_elastic_block(MODEL_PIECE, TABLE4_80C_QS, "FVA 856 I Tabelle 4, 80 degC, QS")
    lines = out.splitlines()
    assert lines.count("*ELASTIC, TYPE=ENGINEERING CONSTANTS") == 1
    k = lines.index("*ELASTIC, TYPE=ENGINEERING CONSTANTS")
    assert lines[k - 1].startswith("*MATERIAL")
    assert lines[k + 1] == "** FVA 856 I Tabelle 4, 80 degC, QS"
    first = [float(v) for v in lines[k + 2].split(",")]
    assert first == pytest.approx(list(TABLE4_80C_QS[:8]))
    assert float(lines[k + 3]) == pytest.approx(469.0)
    assert lines[k + 4] == "*DENSITY"
    # nothing of the old block survives, the blocks around it are untouched
    assert "DEPENDENCIES=2" not in "\n".join(lines[k : k + 4])
    assert "5130." not in out and "a comment inside the block" not in out
    assert "*EXPANSION,TYPE=ORTHO,ZERO=23,DEPENDENCIES=2" in out
    assert "WHEEL-1.1, 0.6" in out and "WHEEL-1.1, 0.1" in out
    assert out.startswith("*DISTRIBUTION TABLE, NAME=DIS_TAB_COORD\n COORD3D, COORD3D\n")
    assert out.endswith("WHEEL-1.1, 0.1\n")
    # the replaced piece is a readable card no more (no isotropic row), but its blocks parse
    blocks = [keyword for keyword, _, _ in dk._blocks(out)]
    assert blocks == [
        "DISTRIBUTION TABLE",
        "MATERIAL",
        "ELASTIC",
        "DENSITY",
        "EXPANSION",
        "INITIAL CONDITIONS",
        "INITIAL CONDITIONS",
    ]


def test_replace_elastic_block_wraps_a_long_note() -> None:
    note = "FVA 856 I Tabelle 4 " + "constant in the fibre frame, " * 20
    assert len(note) > dk.LINE_LIMIT
    out = dk.replace_elastic_block(MODEL_PIECE, TABLE4_80C_QS, note)
    lines = out.splitlines()
    assert all(len(line) <= dk.LINE_LIMIT for line in lines)
    comments = [line for line in lines if line.startswith("** ")]
    assert len(comments) >= 2
    assert " ".join(c[3:] for c in comments) == " ".join(note.split())
    k = lines.index("*ELASTIC, TYPE=ENGINEERING CONSTANTS")
    assert lines[k + 1 + len(comments)].startswith("4.156000000000e+03")


def test_replace_elastic_block_refusals() -> None:
    with pytest.raises(ParseError, match="0 \\*ELASTIC blocks"):
        dk.replace_elastic_block("*MATERIAL, NAME=A\n*DENSITY\n1., 23.\n", TABLE4_80C_QS)
    twice = (
        MODEL_PIECE + "*ELASTIC,TYPE=ENGINEERING CONSTANTS\n1., 1., 1., 0.3, 0.3, 0.3, 1., 1.\n1.\n"
    )
    with pytest.raises(ParseError, match="2 \\*ELASTIC blocks"):
        dk.replace_elastic_block(twice, TABLE4_80C_QS)
    with pytest.raises(ParseError, match="unexpected elastic definition"):
        dk.replace_elastic_block("*MATERIAL, NAME=A\n*ELASTIC\n1000., 0.3\n", TABLE4_80C_QS)
    with pytest.raises(InputRangeError, match="nine engineering constants"):
        dk.replace_elastic_block(MODEL_PIECE, TABLE4_80C_QS[:8])
    with pytest.raises(InputRangeError, match="non-empty string"):
        dk.replace_elastic_block("", TABLE4_80C_QS)


def _decks(script: ModuleType, out: Path, cof: Path, **overrides: object) -> list[str]:
    settings: dict[str, object] = {
        "teeth": 1,
        "rim_rings": 12,
        "layers": 2,
        "element_type": "C3D8I",
        "counts": script.LE_COUNTS,
        "bore_radius_mm": None,
        "rotation": "clockwise",
        "material_steps": ["W3"],
        "cofs": [cof],
        "rates": ["QS"],
        "temperature_c": 80.0,
        "torques_wheel_nm": [8.0],
        "positions": ["pilot"],
        "steps_per_pitch": 4,
        "margin": 0.5,
        "seating_arc_mm": 0.01,
        "max_edge_mm": 0.4,
        "out": out,
    }
    settings.update(overrides)
    lines: list[str] = script.decks("kst_e", **settings)
    return lines


def test_decks_with_the_constants_of_table4(script: ModuleType, tmp_path: Path) -> None:
    out = tmp_path / "w3_table4"
    coarse = script.mesh("kst_e", "wheel", 1, 12, 2, "C3D8I", out, script.LE_COUNTS, None)
    synthetic = out / "synthetic_orientation.cof"
    synthetic.write_text(
        script.synthetic_orientation_text(
            len(coarse.solid.hexes),
            len(coarse.solid.nodes_mm),
            script.REFERENCE_COF.read_text(encoding="utf-8", errors="replace"),
        ),
        encoding="ascii",
    )
    lines = _decks(script, out, synthetic, elastic_constants="fva856_table4")
    assert any("replaced by FVA856-I:2022 Tabelle 4 at 80 degC, QS" in line for line in lines)
    elastic_file = out / "wheel_orientation_QS_model_elastic_fva856_table4.inp"
    assert elastic_file.is_file()
    assert not (out / "wheel_orientation_QS_model_elastic.inp").exists()
    piece = elastic_file.read_text(encoding="utf-8")
    assert piece.count("*ELASTIC, TYPE=ENGINEERING CONSTANTS") == 1
    assert "DEPENDENCIES=2" not in piece.split("*DENSITY")[0]
    assert "*PLASTIC" not in piece and "*POTENTIAL" not in piece
    assert "4.156000000000e+03, 1.444000000000e+03" in piece
    position = (out / "pos_001.inp").read_text(encoding="ascii")
    assert "*INCLUDE, INPUT=wheel_orientation_QS_model_elastic_fva856_table4.inp" in position
    assert "elastic constants FVA856-I:2022 Tabelle 4" in position
    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    constants = manifest["elastic_constants"]
    assert constants["source"] == "fva856_table4" and constants["document"] == "FVA856-I:2022"
    assert constants["rows"]["QS"]["values"] == list(TABLE4_80C_QS)
    assert 0.0 < constants["rows"]["QS"]["stability_left_hand_side"] < 1.0
    assert constants["names"] == list(dk.ENGINEERING_CONSTANT_NAMES)
    assert "wheel_orientation_QS_model_elastic_fva856_table4.inp" in manifest["orientation_files"]
    readme = (out / "README.md").read_text(encoding="utf-8")
    assert "FVA856-I:2022 Tabelle 4" in readme and "E_1 4156" in readme
    assert "ADR-116 Punkt 51" in readme
    # a folder without the option keeps the card's block and the plain file name
    plain = tmp_path / "w3_card"
    coarse_plain = script.mesh("kst_e", "wheel", 1, 12, 2, "C3D8I", plain, script.LE_COUNTS, None)
    synthetic_plain = plain / "synthetic_orientation.cof"
    synthetic_plain.write_text(
        script.synthetic_orientation_text(
            len(coarse_plain.solid.hexes),
            len(coarse_plain.solid.nodes_mm),
            script.REFERENCE_COF.read_text(encoding="utf-8", errors="replace"),
        ),
        encoding="ascii",
    )
    _decks(script, plain, synthetic_plain)
    assert (plain / "wheel_orientation_QS_model_elastic.inp").is_file()
    plain_manifest = json.loads((plain / "manifest.json").read_text(encoding="utf-8"))
    assert plain_manifest["elastic_constants"] is None


def test_decks_refuse_the_constants_outside_w3_alone(script: ModuleType, tmp_path: Path) -> None:
    with pytest.raises(InputRangeError, match="W3 alone"):
        _decks(
            script,
            tmp_path / "a",
            script.REFERENCE_COF,
            material_steps=["W1", "W3"],
            elastic_constants="fva856_table4",
        )
    with pytest.raises(InputRangeError, match="W3 alone"):
        _decks(
            script,
            tmp_path / "b",
            script.REFERENCE_COF,
            material_steps=["W1"],
            elastic_constants="fva856_table4",
        )
    with pytest.raises(InputRangeError, match="elastic constants must be one of"):
        _decks(script, tmp_path / "c", script.REFERENCE_COF, elastic_constants="campus")
    with pytest.raises(InputRangeError, match="no row at 60"):
        _decks(
            script,
            tmp_path / "d",
            script.REFERENCE_COF,
            temperature_c=60.0,
            elastic_constants="fva856_table4",
        )
