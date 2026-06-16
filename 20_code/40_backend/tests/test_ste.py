"""
@module: tests.test_ste
@context: I/O tests.
@role: Parse a STplus `.ste` snippet (sections, comments, raw tokens) and extract
       the typed gear-stage geometry.
"""

from pathlib import Path

import pytest

from app.io.ste import gear_stage_from_ste, load_ste, parse_ste

# Real STplus reference input (repo-root references tree), used for parity checks.
_REF_STE = (
    Path(__file__).resolve().parents[3]
    / "30_references_and_examples"
    / "33_STplus"
    / "kst-E_eingabe.ste"
)

STE = """\
$ Anfang

$ Geometriedaten

ZAHNBREITE = 17 15
NORMALMODUL = 1
ACHSABSTAND = 52.0
EINGRIFFSWINKEL = 20 20
SCHRAEGUNGSWINKEL = 0 0
PROFILVERSCHIEBUNG_N = 0.2034 0.3143
KOPFKREISDM = 52.894 54.022
ZAEHNEZAHL = 51 52
WERKSTOFF = 16MnCr5 WST_PA66
#DREHMOMENT = % 100
DREHMOMENT = % 10

$ ENDE
"""


def test_parse_sections_and_comments() -> None:
    """Sections are ordered, comments skipped, raw tokens preserved."""
    ste = parse_ste(STE)
    assert [s.name for s in ste.sections][:2] == ["Anfang", "Geometriedaten"]

    teeth = ste.find("ZAEHNEZAHL")
    assert teeth is not None and teeth.values == ["51", "52"]

    # the commented-out line is ignored, the active one is kept
    torque = ste.find("DREHMOMENT")
    assert torque is not None and torque.values == ["%", "10"]

    # non-numeric tokens survive
    material = ste.find("WERKSTOFF")
    assert material is not None and material.values == ["16MnCr5", "WST_PA66"]


def test_gear_stage_extraction() -> None:
    """Typed gear-stage geometry is extracted as (pinion, wheel)."""
    stage = gear_stage_from_ste(parse_ste(STE))
    assert stage.normal_module_mm == 1.0
    assert stage.teeth == (51, 52)
    assert stage.center_distance_mm == 52.0
    assert stage.pressure_angle_deg == (20.0, 20.0)
    assert stage.face_width_mm == (17.0, 15.0)
    assert stage.profile_shift == (0.2034, 0.3143)
    assert stage.tip_diameter_mm == (52.894, 54.022)


@pytest.mark.skipif(not _REF_STE.exists(), reason="STplus reference .ste not present")
def test_reference_parity_real_ste() -> None:
    """Parser reproduces the real STplus input (matches FVA-Workbench reference)."""
    stage = gear_stage_from_ste(load_ste(_REF_STE))
    assert stage.teeth == (51, 52)
    assert stage.normal_module_mm == 1.0
    assert stage.center_distance_mm == 52.0
    assert stage.pressure_angle_deg == (20.0, 20.0)
    assert stage.helix_angle_deg == (0.0, 0.0)
    assert stage.face_width_mm == (17.0, 15.0)
    assert stage.profile_shift == (0.2034, 0.3143)
    assert stage.tip_diameter_mm == (52.894, 54.022)


# All shipped STplus examples — varied inputs (helical, internal, single-gear,
# missing tip-diameter/center-distance, '%' flags) to prove robustness.
_STE_EXAMPLES = sorted((_REF_STE.parent / "STplus_11-0F" / "work").glob("stbsp*.ste"))
_STE_PARAMS: list[Path | None] = [*_STE_EXAMPLES] if _STE_EXAMPLES else [None]


@pytest.mark.parametrize("path", _STE_PARAMS, ids=lambda p: p.name if p else "none")
def test_extraction_robust_across_stplus_examples(path: Path | None) -> None:
    """Across every real STplus input, extraction yields a sane two-gear stage or
    a clean ValueError (single-gear / non-stage) — never an undefined crash."""
    if path is None:
        pytest.skip("STplus examples not present")
    try:
        stage = gear_stage_from_ste(load_ste(path))
    except ValueError:
        return  # single-gear / non-stage definitions are rejected cleanly
    assert stage.normal_module_mm > 0
    assert stage.teeth[0] != 0 and stage.teeth[1] != 0
    assert stage.face_width_mm[0] > 0
