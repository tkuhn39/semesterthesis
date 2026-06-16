"""
@module: tests.test_ste
@context: I/O tests.
@role: Parse a STplus `.ste` snippet (sections, comments, raw tokens) and extract
       the typed gear-stage geometry.
"""

from app.io.ste import gear_stage_from_ste, parse_ste

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
