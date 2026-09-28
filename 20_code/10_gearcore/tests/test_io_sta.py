import json
from pathlib import Path

import pytest

from gearcore.io.sta import geometry_block, load_sta, parse_sta

SNIPPET = """1      *********************************************************************
       * Stirnradprogramm STplus 11.0F     FZG             Blatt  6 von 16 *
       * Ein Programm der FVA:     Forschungssoftware erstellt von der FZG *
       ******************************************** 14.02.25  16:02:27 *****




       ---------------------------------------------------------------------
       Geometrieberechnung nach DIN 3960 (Maerz 1987)
       ---------------------------------------------------------------------
                                   (Treiber=1)  Ritzel=1        Rad=2
       Normaleingriffswinkel . . . . . . alfa_n            20.00000     Grad
         Betriebseingriffswinkel . . .  alfa_wt            21.46251     Grad
       Zaehnezahl  . . . . . . . . . . . . .  z        51          52   -
         Zaehnezahlverhaeltnis . . . . .  z2/z1             1.020       -
       Profilverschiebungsfaktor (Nennw.)  .  x      0.2034      0.3143 -

       --- Breiten, Durchmesser etc. ---------------------------------------
       Zahnbreite (eine Pfeilhaelfte bei DSV) b      17.000      15.000 mm
         Fase je Zahnende (Kantenbruch)  . . .        0.000       0.000 mm
         Mittenversatz . . . . . . . . . . . .              0.000       mm
       Fuss-Formkreisdurchmesser . . . . . d_Ff      49.081      50.158 mm

       --- Abmasse, Zahndicken etc. ----------------------------------------
       Verzahnungsqualitaet (DIN3961/63,Aug.78)        N 7         N 7  -
       Abmassreihe (DIN 3967, Aug.78)  . . . .         C           C    -
       Toleranzreihe (DIN 3967, Aug.78)  . . .          0           0   -
       Restdicke bei Kantenbruch/Kopfruecknahme       0.672       0.634 mm
         Beruehrkreisdurchm. (oberes Abmass) .       50.988      51.973 mm
       Achsabstandsabmass  . . . . . . . . A_Ae           + 0.015       mm
       Achsabstandsabmass  . . . . . . . . A_Ai           - 0.015       mm
         nach DIN 3964 Toleranzfeld JS  7

       --- Flankenspiele ---------------------------------------------------
       Verdrehfl.spiel(Waelzkr.)/Normalfl.spiel       j_t    /    j_n
         fuer Nennachsabstand u. obere Zahnabm.       0.521  /    0.485 mm
       Flankenspielaenderung durch Abmass  A_Ae       0.012  /    0.011 mm

       --- Werkzeugangaben -------------------------------------------------
       Zahnradfertigung mit Fraeser oder Hobelkamm
       Kopfhoehenfaktor (Wkz_Bezugspr.)  h_aP0*       1.100       1.250 -
       Erz.-Profilversch.faktor  . . . . .  x_E     -0.2030      0.0117 -
1      *********************************************************************
       * Stirnradprogramm STplus 11.0F     FZG             Blatt  9 von 16 *
       * Ein Programm der FVA:     Forschungssoftware erstellt von der FZG *
       ******************************************** 14.02.25  16:02:27 *****




       ---------------------------------------------------------------------
       Besonderheiten der Radpaarung:
       ---------------------------------------------------------------------
       Kopfkantenbruch an Rad 2 durch Werkzeug (alfa_K0 = 45.00 grd)
"""


def test_header_version_sections_and_symbol_lines() -> None:
    report = parse_sta(SNIPPET)
    assert report.version == "11.0F"
    assert report.sections == (
        "Geometrieberechnung nach DIN 3960 (Maerz 1987)",
        "Besonderheiten der Radpaarung:",
    )
    alpha = report.get("alfa_wt")
    assert alpha.numbers == (21.46251,) and alpha.unit == "Grad" and alpha.subsection is None
    z = report.get("z")
    assert z.numbers == (51.0, 52.0) and z.unit == "-"
    x = report.get("x")
    assert x.numbers == (0.2034, 0.3143) and x.label == "Profilverschiebungsfaktor (Nennw.) ."
    d_ff = report.get("d_Ff")
    assert d_ff.numbers == (49.081, 50.158) and d_ff.subsection == "Breiten, Durchmesser etc."


def test_label_only_lines_are_kept_by_label_key() -> None:
    report = parse_sta(SNIPPET)
    rest = report.get("Restdicke bei Kantenbruch/Kopfruecknahme")
    assert rest.symbol is None and rest.numbers == (0.672, 0.634)
    fase = report.get("Fase je Zahnende (Kantenbruch)")
    assert fase.numbers == (0.0, 0.0)
    versatz = report.get("Mittenversatz")
    assert versatz.numbers == (0.0,)
    contact = report.get("Beruehrkreisdurchm. (oberes Abmass)")
    assert contact.numbers == (50.988, 51.973)


def test_special_shapes_sign_quality_series_backlash() -> None:
    report = parse_sta(SNIPPET)
    assert report.get("A_Ae", section="Geometrie").numbers == (0.015,)
    assert report.get("A_Ai").numbers == (-0.015,)
    quality = report.get("Verzahnungsqualitaet (DIN3961/63,Aug.78)")
    assert quality.tokens == ("N", "7", "N", "7") and quality.numbers == (7.0, 7.0)
    series = report.get("Abmassreihe (DIN 3967, Aug.78)")
    assert series.tokens == ("C", "C") and series.numbers == ()
    backlash = report.get("fuer Nennachsabstand u. obere Zahnabm.")
    assert backlash.tokens == ("0.521", "/", "0.485") and backlash.numbers == (0.521, 0.485)
    delta = report.get_all("A_Ae")
    assert [v.subsection for v in delta] == ["Abmasse, Zahndicken etc.", "Flankenspiele"]
    assert delta[1].numbers == (0.012, 0.011)


def test_tool_block_and_negative_values() -> None:
    report = parse_sta(SNIPPET)
    assert report.get("h_aP0*").numbers == (1.1, 1.25)
    assert report.get("x_E").numbers == (-0.203, 0.0117)
    with pytest.raises(KeyError):
        report.get("Zahnradfertigung mit Fraeser oder Hobelkamm")


def test_geometry_block_filter() -> None:
    report = parse_sta(SNIPPET)
    block = geometry_block(report)
    assert {v.section for v in block} == {"Geometrieberechnung nach DIN 3960 (Maerz 1987)"}
    assert "x_E" in {v.symbol for v in block}


def test_packaged_fixture_reports_parse_and_match_geometry_json(case_dir: Path) -> None:
    report = load_sta(case_dir / "report.sta.txt")
    meta = json.loads((case_dir / "meta.json").read_text(encoding="utf-8"))
    assert report.version == meta["stplus_version"]
    stored = json.loads((case_dir / "geometry.json").read_text(encoding="utf-8"))
    for key in ("z", "m_n", "d_b", "d_f", "d_Ff", "x_E"):
        assert key in stored, f"{case_dir.name}: {key} missing in geometry.json"
        assert tuple(stored[key]["numbers"]) == report.get(key, section="Geometrie").numbers
