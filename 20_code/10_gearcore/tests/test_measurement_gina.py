"""Typed GINA results: code decoding against the labels, pinned values of the fixtures, the
tip relief of the pinion, per-tooth tables, the three sector quantities (F_pk, F_pSk and the
program's Fpz/8), window statistics, curve abscissae and signs checked against the printed
slope deviations, scatter, repeatability and the choice of the latest measurement."""

import math

import numpy as np
import pytest

from gearcore import involute as iv
from gearcore.data import measurement_fixture
from gearcore.errors import InputRangeError, NotSupportedError, ParseError
from gearcore.io.p40 import MewFile, MkaFile, load_mew, load_mka, parse_mew
from gearcore.measurement import gina


@pytest.fixture(scope="module")
def wheel_mew() -> MewFile:
    return load_mew(measurement_fixture("wheel_97340-neu.mew"))


@pytest.fixture(scope="module")
def wheel() -> gina.GinaResult:
    return gina.gina_result(load_mew(measurement_fixture("wheel_97340-neu.mew")), part="wheel")


@pytest.fixture(scope="module")
def wheel_mka() -> MkaFile:
    return load_mka(measurement_fixture("wheel_97340-neu_trimmed.mka"))


@pytest.fixture(scope="module")
def pinion() -> gina.GinaResult:
    return gina.gina_result(load_mew(measurement_fixture("pinion_95911-neu.mew")), part="pinion")


def test_decode_code_and_the_labels_of_every_flank_deviation(wheel_mew: MewFile) -> None:
    teeth = gina.measured_teeth(wheel_mew)
    assert teeth == (1, 12, 22, 33, 44)
    checked = 0
    for value in wheel_mew.values:
        try:
            key = gina.decode_code(value.code)
        except InputRangeError:
            continue
        tooth = teeth[key.slot - 1] if key.statistic == "tooth" else None
        assert value.label in gina.expected_labels(key, tooth), value
        checked += 1
    assert (
        checked == 132
    )  # 6 measurands x (10 per tooth + 2 mean + 2 var + 4 max/min + 4 positions)
    key = gina.decode_code(10112)
    assert (key.quantity, key.statistic, key.flank, key.slot) == (
        "helix_slope_deviation",
        "tooth",
        "links",
        2,
    )
    assert gina.decode_code(20440).statistic == "mean" and gina.decode_code(20440).flank == "rechts"
    assert gina.decode_code(10100).statistic == "min" and gina.decode_code(10100).flank == "rechts"
    assert gina.decode_code(21611).quantity == "tip_relief"
    assert gina.decode_code(10211).position == "f" and gina.decode_code(20311).position == "o"
    for code in (31610, 26430, 10110, 10136, 9999, 100000):
        with pytest.raises(InputRangeError):
            gina.decode_code(code)
    with pytest.raises(InputRangeError):
        gina.expected_labels(gina.decode_code(10111), None)


def test_wheel_result_pins_the_values_of_the_file(wheel: gina.GinaResult) -> None:
    assert (wheel.me, wheel.variant, wheel.part) == ("97340", "-neu", "wheel")
    assert (wheel.measured_on, wheel.measured_at) == ("2026-05-09", "10:15:53")
    assert wheel.number_of_teeth == 52 and wheel.measured_teeth == (1, 12, 22, 33, 44)
    assert wheel.grade == 7 and wheel.unmapped == ()
    assert wheel.profile_evaluation_length_mm == 5.552
    assert wheel.helix_evaluation_length_mm == pytest.approx(13.5)
    assert wheel.evaluation_diameters_mm == (50.3, 54.022)
    helix = wheel.deviation("helix_slope_deviation")
    assert helix.symbol == "f_H_beta"
    assert helix.left.mean_um == 7.2 and helix.right.mean_um == -7.3
    assert helix.left.per_tooth[1] == gina.ToothValue(tooth=12, value_um=55.9)
    assert helix.left.variation_um == 73.6 and helix.right.min_um == -33.1
    assert {(p.flank, p.position, p.tooth) for p in helix.at_positions} == {
        ("links", "f", 1),
        ("rechts", "f", 1),
        ("links", "k", 1),
        ("rechts", "k", 1),
    }
    assert wheel.deviation("total_profile_deviation").right.per_tooth[3].value_um == 24.1
    assert wheel.pitch_value("Fp").left_um == 31.6 and wheel.pitch_value("Fr").value_um == 30.1
    assert wheel.pitch_value("Fpz/8").quantity is None  # the program's own sliding pitch span
    assert wheel.pitch_value("Fpz/8").left_um == 16.7
    assert wheel.pitch_value("Rs").quantity is None and wheel.pitch_value("Rs").value_um == 17.6
    assert wheel.size("Kopf").mean_mm == 54.048 and wheel.size("Kopf").per_tooth_mm == ()
    root = wheel.size("Fuß")
    assert root.quantity is None and root.mean_mm == 49.5 and len(root.per_tooth_mm) == 5
    assert root.per_tooth_mm[0].tooth == 1 and 49.4 < root.per_tooth_mm[0].value_mm < 49.6
    assert wheel.size("WK").mean_mm == 16.972 and wheel.size("MdK").max_mm == 54.548
    tolerances = {t.label: t for t in wheel.tolerances}
    assert tolerances["fHa"].left_um == 7.0
    assert tolerances["fHa"].quantity == "profile_slope_tolerance"
    assert tolerances["Fp"].left_um == 32.0 and tolerances["Fp"].grade == 7
    assert tolerances["Fr"].quantity is None and tolerances["Fr"].right_um is None
    assert tolerances["Fpz/8"].quantity is None and tolerances["Fpz/8"].left_um == 22.0
    assert wheel.tip_relief is None
    conventions = dict(wheel.sign_conventions)
    assert set(conventions) == {161, 165, 178, 179, 180, 181, 182}
    assert conventions[178].endswith("1: DIN") and "BZGFL: 1: Z" in conventions[179]
    with pytest.raises(InputRangeError):
        wheel.deviation("runout")


def test_pinion_result_carries_the_tip_relief(pinion: gina.GinaResult) -> None:
    assert pinion.number_of_teeth == 51 and pinion.measured_teeth == (1, 18, 35)
    assert pinion.grade == 6 and pinion.unmapped == ()
    assert pinion.measured_at == "08:21:31"
    relief = pinion.tip_relief
    assert relief is not None
    assert (relief.start_diameter_mm, relief.end_diameter_mm) == (51.946, 52.88)
    assert relief.deviations.left.mean_um == -23.1 and relief.deviations.right.mean_um == -23.6
    assert [t.value_um for t in relief.deviations.left.per_tooth] == [-23.2, -22.8, -23.2]
    d_b = iv.base_diameter(51, 1.0, math.radians(20.0), 0.0)
    expected = iv.radius_of_curvature(52.88, d_b) - iv.radius_of_curvature(51.946, d_b)
    assert relief.tip_relief_length_mm == pytest.approx(expected)
    assert relief.tip_relief_length_mm == pytest.approx(1.1548, abs=5.0e-4)
    assert pinion.size("Kopf").mean_mm == 52.883 and pinion.size("Fuß").mean_mm == 48.38
    with pytest.raises(InputRangeError):
        gina.tip_relief_length(52.88, 51.946, d_b)


def test_changed_labels_settings_zones_and_tolerances_are_refused(wheel_mew: MewFile) -> None:
    text = measurement_fixture("wheel_97340-neu.mew").read_text(encoding="utf-8-sig")
    with pytest.raises(ParseError, match="labelled"):
        gina.gina_result(
            parse_mew(text.replace("10130 : fHbm links", "10130 : fHbm rechts")), part="wheel"
        )
    with pytest.raises(NotSupportedError):
        gina.gina_result(parse_mew(text.replace(":LVORZ: 1: DIN", ":LVORZ: 0: VDI")), part="wheel")
    with pytest.raises(NotSupportedError):
        gina.gina_result(parse_mew(text.replace(":BZGFL: 1: Z", ":BZGFL: 0: L")), part="wheel")
    with pytest.raises(ParseError, match="asymmetric"):
        gina.gina_result(parse_mew(text.replace("FHAL:7 : -7", "FHAL:7 : -8")), part="wheel")
    with pytest.raises(ParseError, match="grades differ"):
        gina.gina_result(
            parse_mew(text.replace("links          : 22 : 7", "links          : 22 : 6")),
            part="wheel",
        )
    with pytest.raises(InputRangeError):
        gina.gina_result(wheel_mew, part="gear")  # type: ignore[arg-type]
    pinion_text = measurement_fixture("pinion_95911-neu.mew").read_text(encoding="utf-8-sig")
    without_zone = "\n".join(
        line for line in pinion_text.splitlines() if not line.lstrip().startswith("431 :")
    )
    with pytest.raises(ParseError, match="relief zone"):
        gina.gina_result(parse_mew(without_zone), part="pinion")


def test_tooth_tables_and_the_three_sector_quantities(wheel_mka: MkaFile) -> None:
    left, right = gina.tooth_tables(wheel_mka)
    assert left.me == "97340" and left.flank == "links" and right.flank == "rechts"
    assert len(left.teeth) == 52 and left.teeth[0] == 1 and left.F_pi_um[37] == -15.165
    assert gina.sector_pitches(52) == 7 and gina.sector_pitches(51) == 6
    assert gina.sector_pitches(16) == 2 and gina.sector_pitches(60) == 8
    assert gina.sector_pitches(12) == 2
    # the program's Fpz/8 (file: 16,7 links, 21,7 rechts) is the sliding first-minus-last span
    for table, printed in ((left, 16.7), (right, 21.7)):
        values = gina.sector_values(table)
        assert values.k == 7 and values.sliding_span_um == pytest.approx(printed, abs=0.05)
        assert values.F_pk_um >= values.sliding_span_um >= values.F_pSk_um - 1.0e-9
    assert gina.sector_values(left).F_pk_um == pytest.approx(20.685, abs=1.0e-3)
    assert gina.sector_values(left).F_pSk_um == pytest.approx(16.284, abs=1.0e-3)
    assert gina.sector_values(right).F_pk_um == pytest.approx(21.725, abs=1.0e-3)
    assert gina.sector_values(right).F_pSk_um == pytest.approx(12.992, abs=1.0e-3)
    assert max(left.F_pi_um) - min(left.F_pi_um) == pytest.approx(31.6, abs=0.05)  # Fp of the file
    # hand check on a saw tooth of 8 teeth: F_pk (max minus min inside k + 1 teeth), F_pSk (first
    # minus last over z/k consecutive sectors), the program's span (first minus last, all sectors)
    saw = [0.0, 1.0, 2.0, 3.0, 0.0, 1.0, 2.0, 3.0]
    assert gina.sector_pitch_deviation(saw, 3) == 3.0 and gina.sector_pitch_deviation(saw, 4) == 3.0
    assert gina.pitch_span_deviation(saw, 3) == 3.0 and gina.pitch_span_deviation(saw, 4) == 0.0
    assert gina.sliding_pitch_span_deviation(saw, 3) == 3.0
    assert gina.sliding_pitch_span_deviation(saw, 4) == 0.0
    for function in (
        gina.sector_pitch_deviation,
        gina.pitch_span_deviation,
        gina.sliding_pitch_span_deviation,
    ):
        with pytest.raises(InputRangeError):
            function([0.0, 1.0], 2)
        with pytest.raises(InputRangeError):
            function([0.0, 1.0, 2.0, 3.0], 1)
    with pytest.raises(InputRangeError):
        gina.sector_pitches(8)


def test_window_statistics(wheel_mka: MkaFile) -> None:
    left, _ = gina.tooth_tables(wheel_mka)
    window = gina.window_statistics(left, 36, 40)
    assert window.first_tooth == 36 and window.last_tooth == 40
    inside = [abs(left.f_pi_um[t - 1]) for t in range(36, 41)]
    assert window.mean_abs_f_pi_inside_um == pytest.approx(sum(inside) / 5)
    sector = left.F_pi_um[35:40]
    assert window.spread_F_pi_inside_um == pytest.approx(max(sector) - min(sector))
    assert 1 <= window.spread_rank <= 52
    wrapped = gina.window_statistics(left, 51, 2)
    assert wrapped.mean_r_i_inside_um == pytest.approx(
        sum(left.r_i_um[i] for i in (50, 51, 0, 1)) / 4
    )
    with pytest.raises(InputRangeError):
        gina.window_statistics(left, 0, 5)


def test_curve_abscissae_and_din_signs_reproduce_the_printed_slopes(
    wheel: gina.GinaResult, wheel_mka: MkaFile
) -> None:
    header = wheel_mka.header
    profile = gina.curve_abscissa(wheel_mka, wheel_mka.curve("Profil", 44, "links"))
    assert len(profile) == 480 and profile[0] == pytest.approx(50.156)
    assert profile[-1] == pytest.approx(54.2)
    lead = gina.curve_abscissa(wheel_mka, wheel_mka.curve("Flankenlinie", 1, "rechts"))
    assert lead[0] == 0.0 and lead[-1] == pytest.approx(15.0)
    d_b = iv.base_diameter(52, 1.0, math.radians(20.0), 0.0)
    rho = [iv.radius_of_curvature(d, d_b) for d in profile]
    steps = [rho[i + 1] - rho[i] for i in range(len(rho) - 1)]
    assert max(steps) - min(steps) < 1.0e-9  # evenly spaced in roll length, hence not in diameter
    assert profile[1] - profile[0] < profile[-1] - profile[-2]  # d grows faster at the tip
    # the slope of every curve over its evaluation range, with the DIN sign, is the printed value
    d_1, d_2, L_alpha = header.number(42), header.number(43), header.number(45)
    b_1, b_2, b = header.number(62), header.number(63), header.number(26)
    checked = 0
    for curve in wheel_mka.curves:
        if curve.tooth_tag != "" or curve.block not in ("Profil", "Flankenlinie"):
            continue
        y = np.array([np.nan if v is None else v for v in gina.curve_values_din(curve)])
        if curve.block == "Profil":
            d = np.array(gina.curve_abscissa(wheel_mka, curve))
            x = np.array([iv.radius_of_curvature(value, d_b) for value in d])
            mask = (d >= d_1) & (d <= d_2) & np.isfinite(y)
            printed = wheel.deviation("profile_slope_deviation")
            reference_length = L_alpha
            assert gina.din_sign(curve) == (-1.0 if curve.flank == "links" else 1.0)
        else:
            x = np.array(gina.curve_abscissa(wheel_mka, curve))
            mask = (x >= b_1) & (x <= b_2) & np.isfinite(y)
            printed = wheel.deviation("helix_slope_deviation")
            reference_length = b  # BZGFL 1: Z, the face width, not L_beta
            assert gina.din_sign(curve) == -1.0
        slope = float(np.polyfit(x[mask], y[mask], 1)[0])
        expected = next(
            t.value_um for t in printed.flank(curve.flank).per_tooth if t.tooth == curve.tooth
        )
        where = (curve.block, curve.tooth, curve.flank)
        assert slope * reference_length == pytest.approx(expected, abs=0.15), where
        checked += 1
    assert checked == 4
    # the tip rounding of the wheel removes material: negative at the tip end with the DIN sign
    tip = [
        v for v in gina.curve_values_din(wheel_mka.curve("Profil", 44, "links")) if v is not None
    ]
    assert tip[-1] < -10.0
    with pytest.raises(InputRangeError):
        odd = wheel_mka.curve("Profil", 44, "links").model_copy(update={"block": "Kopf"})
        gina.curve_abscissa(wheel_mka, odd)


def test_scatter_repeatability_and_latest(wheel: gina.GinaResult, pinion: gina.GinaResult) -> None:
    rows = gina.scatter_table([wheel])
    by_key = {(r.label, r.flank): r for r in rows}
    assert by_key[("fHb", "links")].mean == 7.2 and by_key[("fHb", "links")].count == 1
    assert by_key[("Fr", "")].quantity == "runout" and by_key[("WK", "")].unit == "mm"
    assert by_key[("Fpz/8", "links")].quantity is None
    twin = wheel.model_copy(update={"variant": "-neu1", "measured_on": "2026-05-10"})
    rows = gina.scatter_table([wheel, twin])
    assert {r.count for r in rows} == {2} and all(r.standard_deviation == 0.0 for r in rows)
    repeats = gina.repeatability([wheel, twin, pinion])
    assert {r.me for r in repeats} == {"97340"} and all(r.spread == 0.0 for r in repeats)
    latest = gina.latest_per_part([wheel, twin, pinion])
    assert [r.me for r in latest] == ["95911", "97340"] and latest[1].variant == "-neu1"
    # same day: the later time of day wins, whatever the variant string
    earlier = wheel.model_copy(update={"variant": "_neu", "measured_at": "08:54:58"})
    assert gina.latest_per_part([earlier, wheel])[0].variant == "-neu"
    assert gina.latest_per_part([wheel, earlier])[0].variant == "-neu"
    with pytest.raises(InputRangeError):
        gina.scatter_table([])


def test_standard_deviation_is_the_sample_one(wheel: gina.GinaResult) -> None:
    values = [1.0, 2.0, 4.0]
    results = []
    for index, value in enumerate(values):
        pitch = tuple(
            p.model_copy(update={"value_um": value}) if p.label == "Fr" else p for p in wheel.pitch
        )
        results.append(wheel.model_copy(update={"me": f"9734{index}", "pitch": pitch}))
    row = next(r for r in gina.scatter_table(results) if r.label == "Fr")
    mean = 7.0 / 3.0
    assert row.mean == pytest.approx(mean)
    assert row.standard_deviation == pytest.approx(
        math.sqrt(sum((v - mean) ** 2 for v in values) / 2.0)
    )
    assert (row.me_of_minimum, row.me_of_maximum) == ("97340", "97342")
