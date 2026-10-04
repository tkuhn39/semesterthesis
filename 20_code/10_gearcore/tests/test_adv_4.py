"""Regression tests for the findings of the adversarial gate of increment 4
(``gate_reports/increment_4.md``): G4A = equations against the norm pages, G4B = resolution,
contracts and importer."""

import math

import pytest
from test_inspection import ALPHA, PROBES, inspect, kst_b, plain_pair

from gearcore import generation as gn
from gearcore import inspection as ins
from gearcore import involute as iv
from gearcore import pair as pr
from gearcore.errors import GeometryInfeasibleError, InputRangeError, NotSupportedError
from gearcore.io.ste import pair_input_from_ste, parse_ste
from gearcore.models.common import Pair
from gearcore.models.inputs import BallMeasurement, DimensionKind, SpanMeasurement
from gearcore.stplus_program import with_stplus_inspection_choices
from gearcore.trace import equations_of


def codes(warnings: tuple) -> list[str]:
    return [warning.code for warning in warnings]


def test_g4a01_constant_chord_only_where_its_end_points_lie_on_the_flank() -> None:
    # standard gear: the end points lie on the involute (checked with the tooth thickness there)
    gear = inspect(plain_pair((20, 41), (0.0, 0.0), allowance=None)).gears.pinion
    assert gear.constant_chord_mm is not None and gear.height_above_constant_chord_mm is not None
    d, d_a = 40.0, 44.0
    radial = 0.5 * d + 0.5 * (d_a - d) - gear.height_above_constant_chord_mm
    half = 0.5 * gear.constant_chord_mm.nominal
    d_b = iv.base_diameter(20, 2.0, ALPHA, 0.0)
    alpha_P = iv.transverse_profile_angle_at(2.0 * math.hypot(radial, half), d_b)
    psi_P = iv.tooth_thickness_half_angle(20, 0.0, ALPHA) + iv.inv(ALPHA) - iv.inv(alpha_P)
    assert math.atan2(half, radial) == pytest.approx(psi_P, abs=1e-13)
    # a tip circle below those points: no constant chord, and the result says why
    short = plain_pair((20, 41), (0.0, 0.0), allowance=None)
    pinion = short.gears.pinion.model_copy(update={"tip_diameter_mm": 40.8})
    short = short.model_copy(update={"gears": Pair(pinion=pinion, wheel=short.gears.wheel)})
    cut = inspect(short).gears.pinion
    assert cut.constant_chord_mm is None and cut.height_above_constant_chord_mm is None
    assert "constant_chord_outside_usable_flank" in codes(cut.warnings)


def test_g4a03_g4a05_citation_and_guard() -> None:
    references = [str(ref) for ref in equations_of(ins.diametral_two_roller_dimension)]
    assert any("(35)" in ref and "p.21" in ref for ref in references)
    assert any("(37)" in ref and "p.22" in ref for ref in references)
    with pytest.raises(GeometryInfeasibleError, match="no chord of a tooth"):
        ins.chordal_height(12.0, 10.0, 5.0, 0.0)


def test_g4b01_inspection_result_carries_what_the_resolution_reported() -> None:
    result = inspect(kst_b(tooth_thickness_allowance_um=(-85.0, -125.0)))
    assert result.gears.wheel.tooth_thickness_tolerance_um == 0.0
    assert "upper_allowance_from_inspection_dimension" in codes(result.warnings)


def test_g4b02_an_input_dimension_must_touch_the_flank_it_determines() -> None:
    absurd = ins.span_measurement(20, 2.0, 0.3, ALPHA, 0.0, 40)
    pair = plain_pair(
        profile_shift_coefficient=None,
        span=SpanMeasurement(
            kind=DimensionKind.NOMINAL, span_measurement_mm=absurd, number_of_teeth_spanned=40
        ),
    )
    with pytest.raises(GeometryInfeasibleError, match="no measurement of the gear"):
        gn.compute_generation(pair)
    # the same for a ball that touches above the tip form circle
    d_b = iv.base_diameter(20, 2.0, ALPHA, 0.0)
    eta = iv.space_width_half_angle(20, 0.3, ALPHA)
    d_K = ins.ball_centre_circle_diameter(
        d_b, ins.ball_centre_profile_angle(9.0, 20, 2.0, ALPHA, eta, ALPHA)
    )
    balls = BallMeasurement(
        kind=DimensionKind.NOMINAL,
        diametral_two_ball_dimension_mm=ins.diametral_two_ball_dimension(d_K, 9.0, 20),
        measuring_ball_diameter_mm=9.0,
    )
    with pytest.raises(GeometryInfeasibleError, match="no measurement of the gear"):
        gn.compute_generation(plain_pair(profile_shift_coefficient=None, ball_dimension=balls))
    # a k asked for the output is treated like a ball asked for the output
    with pytest.raises(GeometryInfeasibleError, match="usable range is 2 to 4"):
        inspect(plain_pair(number_of_teeth_spanned=1000))
    assert inspect(plain_pair(number_of_teeth_spanned=4)).gears.pinion.number_of_teeth_spanned == 4


def test_g4b03_no_table_ball_is_said_with_what_to_do() -> None:
    with pytest.raises(GeometryInfeasibleError, match="give measuring_ball_diameter_mm"):
        inspect(plain_pair(m_n=28.0))
    given = inspect(plain_pair(m_n=28.0, measuring_ball_diameter_mm=52.0)).gears.pinion
    assert given.measuring_ball_diameter_mm == 52.0 and given.span_measurement_mm is not None


def test_g4b04_no_backlash_is_reported_with_and_without_a_given_centre_distance() -> None:
    assert "no_backlash_at_upper_allowances" in codes(
        pr.resolve_tooth_thickness(plain_pair(allowance=(30.0, 10.0))).warnings
    )
    assert "no_backlash_at_upper_allowances" not in codes(
        pr.resolve_tooth_thickness(plain_pair()).warnings
    )


def test_g4b05_g4b06_importer_says_what_it_does_not_use() -> None:
    text = (PROBES / "span_of_both_gears" / "input.ste").read_text(encoding="latin-1")
    with_x = text.replace(
        "ZAHNWEITE = 27.827 46.21\n",
        "PROFILVERSCHIEBUNG_N = 0.2 %\nMESSTUECKDM_KUGEL = 4.0 4.0\n",
    )
    assert with_x != text
    notes = pair_input_from_ste(parse_ste(with_x)).notes
    assert sum("MESSZAEHNEZAHL" in note and "without ZAHNWEITE" in note for note in notes) == 2
    assert sum("MESSTUECKDM_KUGEL" in note and "is not used" in note for note in notes) == 2
    spans = pair_input_from_ste(parse_ste(text)).notes
    assert sum("sets the lower allowance equal to the upper one" in note for note in spans) == 2


def test_g4b08_choices_are_validated() -> None:
    generation = gn.compute_generation(plain_pair())
    with pytest.raises(InputRangeError, match="choices must be"):
        with_stplus_inspection_choices(generation, ((3,), (3.5,)))  # type: ignore[arg-type]
    with pytest.raises(InputRangeError):
        with_stplus_inspection_choices(generation, ((3, 3.5), (3.5, 3.5)))  # type: ignore[arg-type]


def test_g4b09_messages_name_what_happened() -> None:
    far = plain_pair(
        profile_shift_coefficient=None,
        span=SpanMeasurement(
            kind=DimensionKind.NOMINAL, span_measurement_mm=25.0, number_of_teeth_spanned=3
        ),
    )
    with pytest.raises(GeometryInfeasibleError, match="follows from the inspection dimension"):
        pr.resolve_tooth_thickness(far)
    pair = kst_b()
    wheel = pair.gears.wheel.model_copy(update={"span": None})
    lone = pair.model_copy(update={"gears": Pair(pinion=pair.gears.pinion, wheel=wheel)})
    with pytest.raises(InputRangeError, match="of neither gear is determined"):
        pr.resolve_tooth_thickness(lone)
    with pytest.raises(InputRangeError, match="not its split between the gears"):
        pr.resolve_tooth_thickness(pair)


# --- G3Z: independent review of the last rounds of increment 3 ------------------------------------

TOOL_PROBE = PROBES / "tool_tip_land_control" / "input.ste"


def test_g3z04_the_placeholder_is_not_given_everywhere() -> None:
    text = TOOL_PROBE.read_text(encoding="latin-1")
    marked = text.replace(
        "WERKZEUG_VORVERZ. = T1 T2\n",
        "WERKZEUG_VORVERZ. = T1 T2\nWERKZEUG_FERTIGVERZ. = % %\nABMASS_TOL_REIHE = % %\n",
    )
    assert marked != text
    pair = pair_input_from_ste(parse_ste(marked)).pair
    assert pair == pair_input_from_ste(parse_ste(text)).pair
    assert pair.gears.pinion.allowance_series is None and pair.gears.wheel.allowance_series is None
    # a tool block that names its keys with the placeholder only is the preset hob, as an empty one
    only_placeholders = text.replace(
        "$ T2\nKOPFHOEHENFAKTOR = 1.6\nKOPFABRUNDUNGSFAKTOR = 0.25\n",
        "$ T2\nKOPFHOEHENFAKTOR = %\nKOPFABRUNDUNGSFAKTOR = %\n",
    )
    empty = text.replace("$ T2\nKOPFHOEHENFAKTOR = 1.6\nKOPFABRUNDUNGSFAKTOR = 0.25\n", "$ T2\n")
    assert only_placeholders != text and empty != text
    assert (
        pair_input_from_ste(parse_ste(only_placeholders)).pair.gears.wheel.tool
        == pair_input_from_ste(parse_ste(empty)).pair.gears.wheel.tool
    )


def test_g3z05_limits_that_leave_no_tool_are_not_supported() -> None:
    text = TOOL_PROBE.read_text(encoding="latin-1")
    narrow = text.replace(
        "$ T1\nKOPFHOEHENFAKTOR = 2.1\n",
        "$ T1\nKOPFHOEHENFAKTOR = 1.6\nFUSSFORMHOEHENFAKTOR = 2.0\nFUSSHOEHENFAKTOR = 2.3\n"
        "KANTENBRECHWINKEL = 45\n",
    ).replace("MIN_WKZ_ZAHNKOPFDICKE* = 0.2", "MIN_LUECKENWEITE_EF0* = 0.2")
    assert "MIN_LUECKENWEITE_EF0*" in narrow and "FUSSHOEHENFAKTOR = 2.3" in narrow
    with pytest.raises(NotSupportedError, match="not probed"):
        pair_input_from_ste(parse_ste(narrow))


def test_g3z06_a_limit_control_holds_for_the_tools_of_both_gears() -> None:
    text = TOOL_PROBE.read_text(encoding="latin-1")
    both = text.replace("$ T2\nKOPFHOEHENFAKTOR = 1.6\n", "$ T2\nKOPFHOEHENFAKTOR = 2.1\n")
    assert both != text
    gears = pair_input_from_ste(parse_ste(both)).pair.gears
    assert gears.pinion.tool.addendum_factor == pytest.approx(1.88312, abs=1e-5)
    assert gears.wheel.tool.addendum_factor == gears.pinion.tool.addendum_factor
