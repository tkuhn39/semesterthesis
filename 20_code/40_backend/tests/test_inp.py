"""
@module: tests.test_inp
@context: I/O tests — Abaqus inp keyword editor.
@role: Exact round-trip, keyword/parameter parsing and block editing on a small
       deck, plus structural parsing of the real 113 MB FVA-Workbench inp.
"""

from pathlib import Path

import pytest

from app.io.inp import InpBlock, load_inp, parse_inp

INP = (
    "*HEADING\n"
    "test model\n"
    "*NODE, NSET=ALLNODES\n"
    "1, 0., 0., 0.\n"
    "2, 1., 0., 0.\n"
    "*ELEMENT, TYPE=C3D8R, ELSET=P1\n"
    "1, 1, 2, 3, 4, 5, 6, 7, 8\n"
    "**ANSA comment\n"
    "*STEP, NAME=STEP-1, NLGEOM=YES\n"
    "*STATIC, STABILIZE=0.0002\n"
    "0.1, 1.0\n"
    "*BOUNDARY\n"
    "Rot_Node, 1, 6, 0.\n"
    "*END STEP"
)


def test_round_trip_is_exact() -> None:
    """Parsing then serializing reproduces the deck verbatim."""
    assert parse_inp(INP).to_text() == INP


def test_keyword_and_parameter_parsing() -> None:
    """Keywords (incl. two-word) and parameters are read; comments stay with data."""
    deck = parse_inp(INP)
    assert [b.keyword for b in deck.blocks if b.keyword] == [
        "HEADING",
        "NODE",
        "ELEMENT",
        "STEP",
        "STATIC",
        "BOUNDARY",
        "END STEP",
    ]
    step = deck.first("STEP")
    assert step is not None
    assert step.parameter("NAME") == "STEP-1"
    assert step.parameter("NLGEOM") == "YES"
    assert step.parameter("MISSING") is None
    node = deck.first("NODE")
    assert node is not None and node.parameter("NSET") == "ALLNODES"
    element = deck.first("ELEMENT")
    assert element is not None and "**ANSA comment" in element.data


def test_remove_and_insert() -> None:
    """Blocks can be removed and inserted at a defined position."""
    deck = parse_inp(INP)
    assert deck.remove("BOUNDARY") == 1
    assert deck.first("BOUNDARY") is None
    assert deck.insert_after("STATIC", InpBlock(header="*BOUNDARY", data="Rot, 1, 6, 0."))
    keywords = [b.keyword for b in deck.blocks if b.keyword]
    assert keywords.index("BOUNDARY") == keywords.index("STATIC") + 1


_REAL_INP = (
    Path(__file__).resolve().parents[3]
    / "30_references_and_examples"
    / "32_Abaqus"
    / "implicit"
    / "kst-E_8_WS30_ansa_QS.inp"
)


@pytest.mark.skipif(not _REAL_INP.exists(), reason="real FVA-Workbench inp not present")
def test_parses_real_workbench_inp() -> None:
    """The real 113 MB deck parses; key model blocks and parameters are found."""
    deck = load_inp(_REAL_INP)
    assert deck.first("STEP") is not None
    assert deck.first("STATIC") is not None
    assert len(deck.find("RIGID BODY")) == 2
    assert len(deck.find("CONTACT PAIR")) == 7
    include = deck.first("INCLUDE")
    assert include is not None and include.parameter("INPUT") == "kstE_OF_QS.cof"
