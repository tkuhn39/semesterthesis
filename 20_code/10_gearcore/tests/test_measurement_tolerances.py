"""Flank tolerances of DIN ISO 1328-1:2018 against a hand calculation for the kst-E gears, the
rounding rules, the ranges, and the statement the thesis makes: the GINA header values are those
of DIN 3962 (Teil 1 S. 2 and 3, Teil 2 S. 1), not the classes of DIN ISO 1328-1."""

import pytest

from gearcore.errors import InputRangeError
from gearcore.measurement import tolerances as tl

WHEEL = {"d_mm": 52.0, "m_n_mm": 1.0, "b_mm": 15.0}
PINION = {"d_mm": 51.0, "m_n_mm": 1.0, "b_mm": 15.0}


def test_rounding_rules_of_5_2_3() -> None:
    assert tl.rounded(10.904) == 11.0
    assert tl.rounded(33.54) == 34.0
    assert tl.rounded(10.0) == 10.0  # not above 10: to 0,5
    assert tl.rounded(8.904) == 9.0
    assert tl.rounded(7.709) == 7.5
    assert tl.rounded(6.295) == 6.5
    assert tl.rounded(4.452) == 4.5
    assert tl.rounded(4.44) == 4.4


def test_step_factor_and_ranges() -> None:
    assert tl.step_factor(5) == 1.0
    assert tl.step_factor(7) == pytest.approx(2.0)
    assert tl.step_factor(6) == pytest.approx(2.0**0.5)
    with pytest.raises(InputRangeError):
        tl.step_factor(12)
    with pytest.raises(InputRangeError):
        tl.single_pitch_tolerance(4.0, 1.0, 7)
    with pytest.raises(InputRangeError):
        tl.helix_slope_tolerance(52.0, 3.0, 7)


def test_wheel_class_7_by_hand() -> None:
    """d 52, m_n 1, b 15: f_pT 5,452·2 = 10,904 → 11; F_pT 16,770·2 = 33,54 → 34; f_HαT 4,452·2
    → 9,0; f_HβT 5,716·2 = 11,43 → 11; F_rT 0,9·33,54 = 30,2 → 30; f_uT √2·10,904 = 15,4 → 15."""
    t = tl.flank_tolerances(**WHEEL, accuracy_class=7)
    assert t.single_pitch_tolerance == 11.0
    assert t.total_cumulative_pitch_tolerance == 34.0
    assert t.profile_slope_tolerance == 9.0
    assert t.profile_form_tolerance == 11.0
    assert t.total_profile_tolerance == 14.0
    assert t.helix_slope_tolerance == 11.0
    assert t.helix_form_tolerance == 12.0
    assert t.total_helix_tolerance == 17.0
    assert t.runout_tolerance == 30.0
    assert t.adjacent_pitch_difference_tolerance == 15.0
    assert tl.single_pitch_tolerance(52.0, 1.0, 7) == pytest.approx(10.904)
    assert tl.total_cumulative_pitch_tolerance(52.0, 1.0, 7) == pytest.approx(33.5406, abs=1e-3)


def test_wheel_class_10_of_the_drawing() -> None:
    """The drawing of the wheel demands Q10 after DIN ISO 1328-1:2018-03 (kap3_1)."""
    t = tl.flank_tolerances(**WHEEL, accuracy_class=10)
    assert (t.single_pitch_tolerance, t.total_cumulative_pitch_tolerance) == (31.0, 95.0)
    assert (t.profile_slope_tolerance, t.helix_slope_tolerance) == (25.0, 32.0)
    assert (t.runout_tolerance, t.adjacent_pitch_difference_tolerance) == (85.0, 44.0)


def test_pinion_class_6_by_hand() -> None:
    t = tl.flank_tolerances(**PINION, accuracy_class=6)
    assert t.single_pitch_tolerance == 7.5
    assert t.total_cumulative_pitch_tolerance == 24.0
    assert t.profile_slope_tolerance == 6.5
    assert t.helix_slope_tolerance == 8.0
    assert t.runout_tolerance == 21.0
    assert t.adjacent_pitch_difference_tolerance == 11.0


def test_gina_headers_are_din_3962_not_iso_1328() -> None:
    """The P40 headers of the user's files (wheel grade 7: fp 10, fu 12, Fp 32, Fr 22, fHa 7,
    fHb 11 µm; pinion grade 6: 7, 9, 25, 16, 5, 8 µm) are the table values of DIN 3962 Teil 1
    (S. 3 and S. 2, Normalmodul 1 bis 2 mm, d über 50 bis 125 mm) and Teil 2 (S. 1, b bis 20 mm),
    read on 2026-10-25; the classes of DIN ISO 1328-1 differ in every pitch and runout value."""
    gina_wheel = {"fp": 10.0, "fu": 12.0, "Fp": 32.0, "Fr": 22.0, "fHa": 7.0, "fHb": 11.0}
    iso_wheel = tl.flank_tolerances(**WHEEL, accuracy_class=7)
    assert iso_wheel.single_pitch_tolerance != gina_wheel["fp"]
    assert iso_wheel.total_cumulative_pitch_tolerance != gina_wheel["Fp"]
    assert iso_wheel.runout_tolerance != gina_wheel["Fr"]
    assert iso_wheel.adjacent_pitch_difference_tolerance != gina_wheel["fu"]
    assert iso_wheel.profile_slope_tolerance != gina_wheel["fHa"]
    assert iso_wheel.helix_slope_tolerance == gina_wheel["fHb"]  # the one coincidence
    gina_pinion = {"fp": 7.0, "fu": 9.0, "Fp": 25.0, "Fr": 16.0, "fHa": 5.0, "fHb": 8.0}
    iso_pinion = tl.flank_tolerances(**PINION, accuracy_class=6)
    assert iso_pinion.single_pitch_tolerance != gina_pinion["fp"]
    assert iso_pinion.total_cumulative_pitch_tolerance != gina_pinion["Fp"]
    assert iso_pinion.runout_tolerance != gina_pinion["Fr"]
    assert iso_pinion.value("helix_slope_tolerance") == gina_pinion["fHb"]
    with pytest.raises(InputRangeError):
        iso_pinion.value("accuracy_class")
