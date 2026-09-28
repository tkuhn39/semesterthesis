from pathlib import Path

import pytest

from gearcore.errors import NotSupportedError, ParseError
from gearcore.io.ste import (
    known_keys_from_sty,
    load_ste,
    pair_input_from_ste,
    parse_ste,
    tool_from_section,
)
from gearcore.models.inputs import MaterialKind

MINIMAL = """$ Anfang

$ Geometriedaten
ZAHNBREITE = 17 15
NORMALMODUL = 1
ACHSABSTAND = 52.0
EINGRIFFSWINKEL = 20 20
SCHRAEGUNGSWINKEL = 0 0
ZAHNWEITE = 17.090 17.180
MESSZAEHNEZAHL_K = 6 6
PROFILVERSCHIEBUNG_N = 0.2034 0.3143
KOPFKREISDM = 52.894 54.022
ZAEHNEZAHL = 51 52
WERKZEUG_VORVERZ. = WKZ_Profil_B_Ritzel WKZ_Profil_B_Rad
OBERES_ZAHNW_ABMASS = -278 -207
UNTERES_ZAHNW_ABMASS = -278 -207

$ WKZ_Profil_B_Rad
KOPFHOEHENFAKTOR = 1.25
FUSSHOEHENFAKTOR = 1.0
FUSSFORMHOEHENFAKTOR = 0.8456
KOPFABRUNDUNGSFAKTOR = 0.2
WKZ_NORMALMODUL = 1
WKZ_EINGRIFFSWINKEL = 20
KANTENBRECHWINKEL = 45.0

$ WKZ_Profil_B_Ritzel
KOPFHOEHENFAKTOR = 1.1     # comment after value
FUSSHOEHENFAKTOR = 1.0
KOPFABRUNDUNGSFAKTOR = 0.20
WKZ_NORMALMODUL = 1
WKZ_EINGRIFFSWINKEL = 20

$ Tragfaehigkeit_Allgem
#DREHMOMENT = % 100
DREHMOMENT = % 10
WERKSTOFF = 16MnCr5 WST_PA66
ANTEIL_DREHMOMENT = 1.6756 ANTEIL_LASTSPIELE = 0.0036

$ WST_PA66
WERKSTOFFBEZEICHNUNG = PA66
ELASTIZITAETSMODUL = 2300
QUERKONTRAKTIONSZAHL = 0.5
DIN3990/87_SIGMA_HLIM = 70
DIN3990/87_SIGMA_FLIM = 35

$ 16MnCr5
WERKSTOFFBEZEICHNUNG = 16MnCr5
ELASTIZITAETSMODUL = 210000.
QUERKONTRAKTIONSZAHL = .3
WAERMEBEHANDLUNG = einsatzgehaertet
DICHTE_RADKRANZMATERIAL = 7.85E-6
DIN3990/87_SIGMA_HLIM = 1460
DIN3990/87_SIGMA_FE = 860

$ Ende
"""


def test_raw_layer_keeps_tokens_placeholders_and_multi_pairs() -> None:
    ste = parse_ste(MINIMAL)
    assert [s.name for s in ste.sections][:2] == ["Anfang", "Geometriedaten"]
    geo = ste.section("geometriedaten")
    assert geo is not None
    assert geo.get("zaehnezahl") is not None and geo.get("ZAEHNEZAHL").values == ("51", "52")  # type: ignore[union-attr]
    load = ste.section("Tragfaehigkeit_Allgem")
    assert load is not None
    torque = load.get("DREHMOMENT")
    assert torque is not None and torque.values == ("%", "10") and torque.number(0) is None
    assert torque.number(1) == 10.0
    assert load.get("ANTEIL_DREHMOMENT").values == ("1.6756",)  # type: ignore[union-attr]
    assert load.get("ANTEIL_LASTSPIELE").values == ("0.0036",)  # type: ignore[union-attr]
    ritzel = ste.section("WKZ_Profil_B_Ritzel")
    assert ritzel is not None and ritzel.get("KOPFHOEHENFAKTOR").number(0) == 1.1  # type: ignore[union-attr]


def test_keys_are_truncated_to_24_characters() -> None:
    ste = parse_ste("$ Anfang\n$ X\nABCDEFGHIJKLMNOPQRSTUVWXYZ = 1\n$ Ende\n")
    assert ste.find("ABCDEFGHIJKLMNOPQRSTUVWX") is not None


@pytest.mark.parametrize(
    "text, message",
    [
        ("$ X\nA = 1\n$ Ende\n", "missing '\\$ Anfang'"),
        ("$ Anfang\n$ X\nA = 1\n", "missing '\\$ Ende'"),
        ("A = 1\n$ Anfang\n$ Ende\n", "entry before the first"),
        ("$ Anfang\n$ X\nno equals here\n$ Ende\n", "expected 'KEY = value'"),
    ],
)
def test_structural_errors_are_parse_errors(text: str, message: str) -> None:
    with pytest.raises(ParseError, match=message):
        parse_ste(text)


def test_typed_extraction_maps_geometry_tools_and_materials() -> None:
    ste = parse_ste(MINIMAL)
    result = pair_input_from_ste(
        ste, material_kinds={"16MnCr5": MaterialKind.STEEL, "WST_PA66": MaterialKind.PLASTIC}
    )
    p = result.pair
    assert (p.gears.pinion.teeth, p.gears.wheel.teeth) == (51, 52)
    assert p.center_distance_mm == 52.0 and p.normal_module_mm == 1.0
    assert p.gears.wheel.tool.edge_break_angle_deg == 45.0
    assert p.gears.wheel.tool.root_form_height_factor == 0.8456
    assert p.gears.pinion.tool.edge_break_angle_deg is None
    assert p.gears.pinion.span_allowance_um == (-278.0, -278.0)
    assert p.gears.pinion.span_teeth == 6
    # ZAHNWEITE is given together with x: x wins, the span is only an inspection value
    assert p.gears.pinion.span is None
    assert any("ZAHNWEITE 17.09 ignored for x" in n for n in result.notes)
    assert (
        p.gears.pinion.material is not None and p.gears.pinion.material.kind is MaterialKind.STEEL
    )
    kinds = {m.name: m.kind for m in result.materials}
    assert kinds == {"16MnCr5": MaterialKind.STEEL, "WST_PA66": MaterialKind.PLASTIC}
    steel = next(m for m in result.materials if m.name == "16MnCr5")
    assert steel.steel is not None and steel.steel.density_kg_m3 == pytest.approx(7850.0)
    assert steel.strength is not None and steel.strength.sigma_FE_MPa == 860.0
    plastic = next(m for m in result.materials if m.name == "WST_PA66")
    assert (
        plastic.steel is None
        and plastic.strength is not None
        and plastic.strength.sigma_Flim_MPa == 35.0
    )
    assert result.unmapped_keys == ()


def test_material_without_stated_kind_is_reported_not_guessed() -> None:
    result = pair_input_from_ste(parse_ste(MINIMAL))
    assert result.materials == ()
    assert any("kind (steel/plastic) not stated" in n for n in result.notes)
    assert result.pair.gears.pinion.material is None


def test_internal_gear_and_second_tool_are_explicit_extension_points() -> None:
    with pytest.raises(NotSupportedError, match="internal gear"):
        pair_input_from_ste(parse_ste(MINIMAL.replace("ZAEHNEZAHL = 51 52", "ZAEHNEZAHL = 51 -52")))
    text = MINIMAL.replace(
        "WERKZEUG_VORVERZ. = WKZ_Profil_B_Ritzel WKZ_Profil_B_Rad",
        "WERKZEUG_VORVERZ. = WKZ_Profil_B_Ritzel WKZ_Profil_B_Rad\nWERKZEUG_FERTIGVERZ. = WKZ_Profil_B_Ritzel",
    )
    with pytest.raises(NotSupportedError, match="second tool"):
        pair_input_from_ste(parse_ste(text))


def test_shaper_and_profile_tools_are_flagged() -> None:
    ste = parse_ste("$ Anfang\n$ T\nSR_ZAEHNEZAHL = 30\nKOPFHOEHENFAKTOR = 1.25\n$ Ende\n")
    with pytest.raises(NotSupportedError, match="shaper"):
        tool_from_section(ste.section("T"))  # type: ignore[arg-type]
    ste = parse_ste("$ Anfang\n$ T\nPW_KOPFART = Ellipse\n$ Ende\n")
    with pytest.raises(NotSupportedError, match="profile"):
        tool_from_section(ste.section("T"))  # type: ignore[arg-type]


def test_missing_tool_factors_are_not_defaulted() -> None:
    ste = parse_ste("$ Anfang\n$ T\nKOPFHOEHENFAKTOR = 1.25\n$ Ende\n")
    with pytest.raises(ParseError, match="KOPFABRUNDUNGSFAKTOR"):
        tool_from_section(ste.section("T"))  # type: ignore[arg-type]


def test_span_without_profile_shift_is_accepted() -> None:
    text = (
        "$ Anfang\n$ Geometriedaten\nZAHNBREITE = 22 20\nNORMALMODUL = 2.0\nACHSABSTAND = 91.5\n"
        "EINGRIFFSWINKEL = 20\nSCHRAEGUNGSWINKEL = 0 0\nZAHNWEITE = 27.827 46.21\nMESSZAEHNEZAHL = 5 8\n"
        "KOPFKREISDM = 76.46 112.95\nZAEHNEZAHL = 36 54\nWERKZEUG_VORVERZ. = A B\n"
        "$ A\nKOPFHOEHENFAKTOR = 1.25\nKOPFABRUNDUNGSFAKTOR = 0.25\n"
        "$ B\nKOPFHOEHENFAKTOR = 1.25\nKOPFABRUNDUNGSFAKTOR = 0.394\nKANTENBRECHWINKEL = 45.0\n$ Ende\n"
    )
    p = pair_input_from_ste(parse_ste(text)).pair
    assert p.gears.pinion.profile_shift is None
    assert p.gears.wheel.span is not None and p.gears.wheel.span.span_mm == 46.21


def test_packaged_fixture_inputs_parse(case_dir: Path) -> None:
    ste = load_ste(case_dir / "input.ste")
    assert ste.section("Geometriedaten") is not None


def test_manual_examples_parse_and_report_support(stplus_root: Path) -> None:
    """The eight manual examples: every file parses; unsupported ones say why."""
    outcomes: dict[str, str] = {}
    for path in sorted((stplus_root / "work").glob("*.ste")):
        ste = load_ste(path)
        try:
            pair_input_from_ste(ste)
            outcomes[path.name] = "supported"
        except NotSupportedError as exc:
            outcomes[path.name] = f"not supported: {exc}"
        except ParseError as exc:
            outcomes[path.name] = f"parse: {exc}"
    assert outcomes["eingabe.ste"] == "supported"
    assert outcomes["stbsp07.ste"].startswith("parse")  # no WERKZEUG_VORVERZ. (STplus default hob)
    assert (
        "not supported" in outcomes["stbsp03.ste"] or "parse" in outcomes["stbsp03.ste"]
    )  # planetary


def test_default_sty_register_covers_our_keys(stplus_root: Path) -> None:
    keys = known_keys_from_sty(stplus_root / "bin" / "DEFAULT.STY")
    assert len(keys) > 800
    for key in (
        "ZAEHNEZAHL",
        "NORMALMODUL",
        "KOPFABRUNDUNGSFAKTOR",
        "KANTENBRECHWINKEL",
        "STIRNKOORD_EIN_WKZ",
    ):
        assert key in keys


def test_interface_file_keys_with_special_characters_parse() -> None:
    """STplus .sts interface files use keys such as SEHNE_30GRAD_* and DIN3990/87_SIGMA_HLIM."""
    text = (
        "$ ANFANG\n$ GEOMETRIEDATEN\nSEHNE_30GRAD_*          =          2.0681102276          2.1967811584\n"
        "DIN3990/87_SIGMA_HLIM = 1460\n$ ENDE\n"
    )
    ste = parse_ste(text)
    chord = ste.find("SEHNE_30GRAD_*")
    assert chord is not None and chord.numbers() == (2.0681102276, 2.1967811584)
    assert ste.find("DIN3990/87_SIGMA_HLIM") is not None
