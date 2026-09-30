"""Regression tests for the adversarial gate of increment 0 (findings ADV0-xx, 2026-09-28)."""

import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pytest
import yaml
from pydantic import ValidationError

from gearcore.data import stplus_case_dirs
from gearcore.errors import NotSupportedError, ParseError
from gearcore.io.sta import parse_sta
from gearcore.io.ste import pair_input_from_ste, parse_ste
from gearcore.io.stplus_contour import parse_contour
from gearcore.models.common import Pair
from gearcore.models.inputs import GearInput, PairInput, QualitySystem, ToolProfile

BASE = """$ Anfang
$ Geometriedaten
ZAHNBREITE = 14 14
NORMALMODUL = 4.5
ACHSABSTAND = 91.5
EINGRIFFSWINKEL = {alpha}
SCHRAEGUNGSWINKEL = 0
PROFILVERSCHIEBUNG_N = 0.1818
AUFTEILUNG_X1X2 = 0
KOPFKREISDM = 82.45 118.35
ZAEHNEZAHL = 16 24
WERKZEUG_VORVERZ. = Fraes_WKZ Fraes_WKZ
{extra}
$ Fraes_WKZ
KOPFHOEHENFAKTOR = 1.39
KOPFABRUNDUNGSFAKTOR = 0.25
$ Ende
"""


def base(alpha: float = 20, extra: str = "") -> str:
    return BASE.format(alpha=alpha, extra=extra)


def test_adv0_01_tool_pressure_angle_inherits_gear_angle() -> None:
    """Manual §4.16.2: tool angle/module entered only when deviating → None means gear value."""
    for alpha in (17.5, 20.0, 25.0):
        pair = pair_input_from_ste(parse_ste(base(alpha))).pair
        assert pair.gears.pinion.tool.profile_angle_deg is None
        assert pair.normal_pressure_angle_deg == alpha
    assert (
        ToolProfile(
            addendum_factor=1.25,
            tip_radius_factor=0.25,
            protuberance_mm=0.0,
            machining_allowance_mm=0.0,
        ).profile_angle_deg
        is None
    )


def test_adv0_02_x_distribution_modes_are_not_silently_accepted() -> None:
    for mode in (1, 2, 4, 7):
        text = base().replace("AUFTEILUNG_X1X2 = 0", f"AUFTEILUNG_X1X2 = {mode}")
        with pytest.raises(NotSupportedError, match="AUFTEILUNG_X1X2"):
            pair_input_from_ste(parse_ste(text))
    with pytest.raises(NotSupportedError, match="PR.VERSCH.SUMME"):
        pair_input_from_ste(parse_ste(base(extra="PR.VERSCH.SUMME = 0.35")))


@pytest.mark.parametrize(
    "line, error, match",
    [
        ("ZAEHNEZAHL = 51.5 52", NotSupportedError, "not an integer"),
        ("ZAEHNEZAHL = nan 52", ParseError, "non-numeric"),
        ("ZAEHNEZAHL = inf 52", ParseError, "non-numeric"),
        ("ZAEHNEZAHL = 1_0 52", ParseError, "non-numeric"),
        ("NORMALMODUL = 2,5", ParseError, "non-numeric token '2,5'"),
        ("NORMALMODUL = abc", ParseError, "non-numeric"),
    ],
)
def test_adv0_03_09_non_integer_and_malformed_numbers_are_typed_errors(
    line: str, error: type[Exception], match: str
) -> None:
    key = line.split(" =")[0]
    text = "\n".join(f"{line}" if ln.startswith(key + " =") else ln for ln in base().splitlines())
    with pytest.raises(error, match=match):
        pair_input_from_ste(parse_ste(text))


def test_adv0_03_fractional_check_teeth_and_quality_are_parse_errors() -> None:
    with pytest.raises(ParseError, match="MESSZAEHNEZAHL_K"):
        pair_input_from_ste(parse_ste(base(extra="MESSZAEHNEZAHL_K = 5.7 6")))
    with pytest.raises(ParseError, match="QUALITAET"):
        pair_input_from_ste(parse_ste(base(extra="ISO_QUALITAET = 7.9 7")))


def test_adv0_04_single_value_semantics_per_gear_keys() -> None:
    """Manual §3.2: a lone value on a per-gear key belongs to gear 1; gear 2 is 'not given'."""
    with pytest.raises(ParseError, match="ZAHNBREITE missing"):
        pair_input_from_ste(parse_ste(base().replace("ZAHNBREITE = 14 14", "ZAHNBREITE = 14")))
    with pytest.raises(ParseError, match="ZAHNBREITE missing"):
        pair_input_from_ste(parse_ste(base().replace("ZAHNBREITE = 14 14", "ZAHNBREITE = 14 %")))
    result = pair_input_from_ste(parse_ste(base(extra="KOPFKANTENBRUCH = 0.3")))
    assert result.pair.gears.pinion.tip_chamfer_radial_mm == 0.3
    assert result.pair.gears.wheel.tip_chamfer_radial_mm == 0.0
    assert any("KOPFKANTENBRUCH not given" in n for n in result.notes)
    q = pair_input_from_ste(parse_ste(base(extra="ISO_QUALITAET = 7"))).pair
    assert (q.gears.pinion.quality_grade, q.gears.wheel.quality_grade) == (7, None)
    assert q.gears.pinion.quality_system is QualitySystem.ISO1328


def test_adv0_04_pair_keys_accept_one_value_or_two_equal_values() -> None:
    ok = pair_input_from_ste(
        parse_ste(base().replace("EINGRIFFSWINKEL = 20", "EINGRIFFSWINKEL = 20 20"))
    )
    assert ok.pair.normal_pressure_angle_deg == 20.0
    with pytest.raises(NotSupportedError, match="different values per gear"):
        pair_input_from_ste(
            parse_ste(base().replace("SCHRAEGUNGSWINKEL = 0", "SCHRAEGUNGSWINKEL = 20 -20"))
        )
    with pytest.raises(ParseError, match="placeholder"):
        pair_input_from_ste(
            parse_ste(base().replace("SCHRAEGUNGSWINKEL = 0", "SCHRAEGUNGSWINKEL = % 20"))
        )


def test_adv0_05_fixture_hash_matches_input(case_dir: Path) -> None:
    meta = json.loads((case_dir / "meta.json").read_text(encoding="utf-8"))
    text = (case_dir / "input.ste").read_text(encoding="latin-1")
    assert (
        hashlib.sha256(text.encode("latin-1", errors="replace")).hexdigest() == meta["ste_sha256"]
    )
    assert meta["trust"] in {"verified", "unverified", "generated"}
    assert meta["typed_import"]["ok"] is True, meta["typed_import"]


def test_adv0_06_every_oracle_case_is_packaged() -> None:
    cases_file = Path(__file__).resolve().parents[1] / "scripts" / "oracle_cases.yaml"
    expected = {c["name"] for c in yaml.safe_load(cases_file.read_text(encoding="utf-8"))["cases"]}
    packaged = {d.name for d in stplus_case_dirs()}
    assert packaged == expected, f"missing: {expected - packaged}, extra: {packaged - expected}"
    assert len(packaged) >= 15


def test_adv0_08_module_lower_bound_is_inclusive() -> None:
    gear = GearInput(
        number_of_teeth=20,
        profile_shift_coefficient=0.0,
        face_width_mm=5.0,
        tip_chamfer_radial_mm=0.0,
        tool=ToolProfile(
            addendum_factor=1.25,
            tip_radius_factor=0.25,
            protuberance_mm=0.0,
            machining_allowance_mm=0.0,
        ),
    )
    pair = PairInput(
        normal_module_mm=0.05,
        normal_pressure_angle_deg=20.0,
        helix_angle_deg=0.0,
        gears=Pair(pinion=gear, wheel=gear),
    )
    assert pair.normal_module_mm == 0.05
    with pytest.raises(ValidationError):
        PairInput(
            normal_module_mm=0.0499,
            normal_pressure_angle_deg=20.0,
            helix_angle_deg=0.0,
            gears=Pair(pinion=gear, wheel=gear),
        )


def test_adv0_10_missing_width_is_a_parse_error_not_zero() -> None:
    with pytest.raises(ParseError, match="ZAHNBREITE"):
        pair_input_from_ste(parse_ste(base().replace("ZAHNBREITE = 14 14", "ZAHNBREITE =")))


def test_adv0_11_check_teeth_do_not_define_the_span_measurement() -> None:
    text = (
        base()
        .replace("PROFILVERSCHIEBUNG_N = 0.1818\n", "")
        .replace("AUFTEILUNG_X1X2 = 0", "ZAHNWEITE = 33.174 31.692\nMESSZAEHNEZAHL_K = 4 4")
    )
    with pytest.raises(ParseError, match="ZAHNWEITE given without MESSZAEHNEZAHL"):
        pair_input_from_ste(parse_ste(text))


def test_adv0_12_series_letters_are_markers_not_symbols() -> None:
    text = """       ---------------------------------------------------------------------
       Geometrieberechnung nach DIN 3960 (Maerz 1987)
       ---------------------------------------------------------------------
       Abmassreihe (DIN 3967, Aug.78)  . . . .         a           a    -
       Abmassreihe (DIN 3967, Aug.78)  . . . .         cd          cd   -
       Achsabstand . . . . . . . . . . . . .  a            52.000       mm
       Zaehnezahl  . . . . . . . . . . . . .  z        51          52   -
"""
    report = parse_sta(text)
    series = report.get_all("Abmassreihe (DIN 3967, Aug.78)")
    assert [s.tokens for s in series] == [("a", "a"), ("cd", "cd")]
    assert all(s.symbol is None and s.numbers == () for s in series)
    assert report.get("a").numbers == (52.0,)
    assert report.get("z").numbers == (51.0, 52.0)


def test_adv0_13_14_axial_pitch_symbol_and_two_token_units() -> None:
    text = """       ---------------------------------------------------------------------
       Geometrieberechnung nach DIN 3960 (Maerz 1987)
       ---------------------------------------------------------------------
       Axialteilung  . . . . . . . . . . .  p_x            45.927       mm
       Tauchschm., Oeltemperatur . . . . theta_oil            60.0         Grad C
       Verzahnungsverlustleistung  . . .  P_VzP           177.9         W
       Flankenhaerte . . . . . . . . . . . . .      750.        750.    HV
"""
    report = parse_sta(text)
    assert report.get("p_x").numbers == (45.927,)
    oil = report.get("Tauchschm., Oeltemperatur theta_oil")
    assert oil.unit == "Grad C" and oil.numbers == (60.0,)
    assert report.get("P_VzP").unit == "W" and report.get("P_VzP").numbers == (177.9,)
    assert report.get("Flankenhaerte").numbers == (750.0, 750.0)


def test_adv0_16_bare_pair_rejects_non_finite() -> None:
    with pytest.raises(ValidationError, match="finite"):
        Pair.same(math.nan)
    with pytest.raises(ValidationError, match="finite"):
        Pair(pinion=1.0, wheel=math.inf)


def test_adv0_18_duplicate_keys_and_blocks_are_not_first_wins() -> None:
    ste = parse_ste("$ Anfang\n$ X\nNORMALMODUL = 1\nNORMALMODUL = 2\n$ Ende\n")
    section = ste.section("X")
    assert section is not None
    with pytest.raises(ParseError, match="appears 2 times"):
        section.get("NORMALMODUL")
    assert [e.values for e in section.get_all("NORMALMODUL")] == [("1",), ("2",)]
    with pytest.raises(ParseError, match="appears twice"):
        parse_ste("$ Anfang\n$ Geometriedaten\nA = 1\n$ Geometriedaten\nA = 2\n$ Ende\n")


def test_adv0_19_only_crlf_and_lf_split_lines() -> None:
    text = "$ Anfang\n$ X\nA = 1 # note\x85more   text\r\nB = 2\n$ Ende\n"
    ste = parse_ste(text)
    section = ste.section("X")
    assert section is not None
    assert section.get("A") is not None and section.get("B") is not None


def test_adv0_21_contour_radii_match_root_and_tip_circles(case_dir: Path) -> None:
    geometry = json.loads((case_dir / "geometry.json").read_text(encoding="utf-8"))
    for gear in (1, 2):
        path = case_dir / f"contour_wz{gear}.json"
        if not path.is_file():
            continue
        pts = np.asarray(json.loads(path.read_text(encoding="utf-8"))["points"], dtype=float)
        radii = np.hypot(pts[:, 0], pts[:, 1])
        d_f = geometry["d_f"]["numbers"][gear - 1]
        d_a = geometry["d_a"]["numbers"][gear - 1]
        assert abs(radii.min() - d_f / 2) < 0.01, f"{case_dir.name} gear {gear}: r_min vs d_f/2"
        assert abs(radii.max() - d_a / 2) < 0.01, f"{case_dir.name} gear {gear}: r_max vs d_a/2"
        assert abs(math.hypot(*pts[0]) - d_f / 2) < 0.01  # starts at the root circle


def test_adv0_22_contour_requires_exactly_two_columns() -> None:
    with pytest.raises(ParseError, match="exactly two"):
        parse_contour("1.0 2.0\n3.0 4.0 extra\n5.0 6.0\n")
    with pytest.raises(ParseError):
        parse_contour("1,5;2,5\n1,6;2,6\n1,7;2,7\n")


def test_adv0_23_quality_systems_are_kept_apart() -> None:
    with pytest.raises(ParseError, match="ambiguous"):
        pair_input_from_ste(parse_ste(base(extra="DIN_QUALITAET = 7 7\nISO_QUALITAET = 6 6")))
    din = pair_input_from_ste(parse_ste(base(extra="DIN_QUALITAET = 7 7"))).pair
    assert din.gears.wheel.quality_system is QualitySystem.DIN3962
    with pytest.raises(ValidationError, match="together"):
        GearInput(
            number_of_teeth=20,
            profile_shift_coefficient=0.0,
            face_width_mm=5.0,
            tip_chamfer_radial_mm=0.0,
            quality_grade=7,
            tool=ToolProfile(
                addendum_factor=1.25,
                tip_radius_factor=0.25,
                protuberance_mm=0.0,
                machining_allowance_mm=0.0,
            ),
        )


def test_adv0_26_27_28_value_with_equals_sign_and_placeholder_helix() -> None:
    ste = parse_ste("$ Anfang\n$ Allgemeine_Daten\nBENUTZERTEXT1 = Fall=Test\n$ Ende\n")
    section = ste.section("Allgemeine_Daten")
    assert section is not None
    entry = section.get("BENUTZERTEXT1")
    assert entry is not None and entry.values == ("Fall=Test",)
    assert section.get("FALL") is None
    spectrum = parse_ste(
        "$ Anfang\n$ T\nANTEIL_DREHMOMENT = 1.6 ANTEIL_LASTSPIELE = 0.0036\n$ Ende\n"
    ).section("T")
    assert spectrum is not None
    assert spectrum.get("ANTEIL_DREHMOMENT").values == ("1.6",)  # type: ignore[union-attr]
    assert spectrum.get("ANTEIL_LASTSPIELE").values == ("0.0036",)  # type: ignore[union-attr]


def test_adv0_32_strict_integers_and_stripped_names() -> None:
    tool = ToolProfile(
        addendum_factor=1.25,
        tip_radius_factor=0.25,
        protuberance_mm=0.0,
        machining_allowance_mm=0.0,
    )
    with pytest.raises(ValidationError):
        GearInput(
            number_of_teeth="24",
            profile_shift_coefficient=0.0,
            tip_chamfer_radial_mm=0.0,
            face_width_mm=5.0,
            tool=tool,
        )  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        GearInput(
            number_of_teeth=24.0,
            profile_shift_coefficient=0.0,
            tip_chamfer_radial_mm=0.0,
            face_width_mm=5.0,
            tool=tool,
        )  # type: ignore[arg-type]
    from gearcore.models.inputs import MaterialKind, MaterialRef

    with pytest.raises(ValidationError):
        MaterialRef(kind=MaterialKind.STEEL, name="   ")
