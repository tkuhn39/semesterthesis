"""How STplus 11.1F chooses the number of teeth spanned and the measuring ball (found 2026-10-04).

The manual is silent on both. The rules of ``gearcore.stplus_program`` were found by experiment
(switch points bisected to 0,0005 mm, then random gears); the packaged evidence
(``stplus_program/inspection_choices.json``) holds what the listings of 540 random gears print,
and every gear of it has to follow the rules. They are rules of the program, kept with the
heritage of STplus (ADR-109): the norm chooses differently, and gearcore applies them only where
a caller asks.
"""

import math
import re
from typing import Any

import pytest
from scipy.optimize import brentq

from gearcore import generation as gn
from gearcore import inspection as ins
from gearcore import involute as iv
from gearcore.data import data_path, load_stplus, stplus_case_dirs
from gearcore.errors import GearCoreError, GeometryInfeasibleError, InputRangeError
from gearcore.io.ste import load_ste, pair_input_from_ste
from gearcore.parity import compute_generation_from_data, generation_data
from gearcore.stplus_program import (
    stplus_ideal_measuring_ball_diameter,
    stplus_inspection_choices,
    stplus_inspection_evidence,
    stplus_measuring_ball_diameter,
    stplus_measuring_ball_diameters,
    stplus_number_of_teeth_spanned,
    with_stplus_inspection_choices,
)

ALPHA = math.radians(20.0)
PROBES = data_path("stplus_program", "probes")


def evidence_gears() -> list[dict[str, Any]]:
    return [gear for group in stplus_inspection_evidence()["groups"] for gear in group["gears"]]


def test_evidence_is_labelled_and_broad() -> None:
    evidence = stplus_inspection_evidence()
    assert (evidence["program"], evidence["version"]) == ("STplus", "11.1F")
    assert [
        (group["name"], group["seed"], len(group["gears"])) for group in evidence["groups"]
    ] == [
        ("general", 11, 300),
        ("few teeth, small modules", 5, 120),
        ("many teeth, large helix angles", 7, 120),
    ]
    gears = evidence_gears()
    assert min(g["z"] for g in gears) == 7 and max(g["z"] for g in gears) > 200
    assert {g["beta_deg"] for g in gears} >= {0.0, 15.0, 30.0, 45.0}
    assert {g["alpha_n_deg"] for g in gears} == {17.5, 20.0, 22.5, 25.0}
    assert min(g["m_n"] for g in gears) == 0.3 and max(g["m_n"] for g in gears) == 20.0


def test_table_of_the_program_is_not_din_3977_table_1() -> None:
    table = stplus_measuring_ball_diameters()
    assert len(table) == 44 and (table[0], table[-1]) == (1.0, 110.0)
    assert list(table) == sorted(set(table))
    norm = ins.standard_measuring_ball_diameters()
    within = [d for d in norm if d >= 1.0]
    assert sorted(set(within) - set(table)) == [1.4, 3.25, 3.75, 4.25, 5.25, 30.0, 35.0]
    assert sorted(set(table) - set(norm)) == [32.0, 36.0, 60.0, 70.0, 80.0, 90.0, 100.0, 110.0]
    # every ball a listing of the evidence names is one of the table
    assert {gear["D_M"] for gear in evidence_gears()} <= set(table)


def _usable_range(gear: dict[str, Any]) -> tuple[int, int]:
    alpha_n, beta = math.radians(gear["alpha_n_deg"]), math.radians(gear["beta_deg"])
    z, m_n, x_E = int(gear["z"]), gear["m_n"], gear["x_E"]
    # (a root form circle on the base circle is printed with three decimals and may fall below it)
    d_Ff = max(gear["d_Ff"], iv.base_diameter(z, m_n, alpha_n, beta))
    return (
        ins.min_number_of_teeth_spanned(z, m_n, x_E, alpha_n, beta, d_Ff),
        ins.max_number_of_teeth_spanned(z, m_n, x_E, alpha_n, beta, gear["d_Fa"]),
    )


def test_number_of_teeth_spanned_of_every_gear_of_the_evidence() -> None:
    gears = evidence_gears()
    norm_differs = 0
    for gear in gears:
        k_min, k_max = _usable_range(gear)
        assert stplus_number_of_teeth_spanned(k_min, k_max) == int(gear["k"]), gear
        alpha_n, beta = math.radians(gear["alpha_n_deg"]), math.radians(gear["beta_deg"])
        z, m_n, x_E = int(gear["z"]), gear["m_n"], gear["x_E"]
        d_v = ins.v_circle_diameter(iv.reference_diameter(z, m_n, beta), x_E, m_n)
        if d_v > iv.base_diameter(z, m_n, alpha_n, beta):
            by_norm = ins.number_of_teeth_spanned(z, m_n, x_E, alpha_n, beta, d_v)
            norm_differs += by_norm != int(gear["k"])
    # DIN 21773 Eq. (9) names another k for a good part of the gears
    assert 100 < norm_differs < len(gears)


def test_number_of_teeth_spanned_rule() -> None:
    # the middle of the usable range, rounded up to the next number, at most k_max
    assert [stplus_number_of_teeth_spanned(2, k_max) for k_max in (2, 3, 4, 5, 6)] == [
        2,
        3,
        4,
        4,
        5,
    ]
    assert stplus_number_of_teeth_spanned(5, 7) == 7 and stplus_number_of_teeth_spanned(4, 7) == 6
    assert stplus_number_of_teeth_spanned(1, 5) == 4
    with pytest.raises(GeometryInfeasibleError, match="no such gear"):
        stplus_number_of_teeth_spanned(1, 1)
    with pytest.raises(InputRangeError):
        stplus_number_of_teeth_spanned(2.0, 5)  # type: ignore[arg-type]


def test_measuring_ball_of_every_gear_of_the_evidence() -> None:
    by_tip = by_flank = 0
    for gear in evidence_gears():
        alpha_n, beta = math.radians(gear["alpha_n_deg"]), math.radians(gear["beta_deg"])
        arguments = (int(gear["z"]), gear["m_n"], gear["x_E"], alpha_n, beta)
        chosen = stplus_measuring_ball_diameter(*arguments, gear["d_a"], gear["d_Ff"], gear["d_Fa"])
        assert chosen == gear["D_M"], gear
        ideal = stplus_ideal_measuring_ball_diameter(
            *arguments, 0.5 * (gear["d_Ff"] + gear["d_Fa"])
        )
        table = stplus_measuring_ball_diameters()
        first_above = next((i for i, value in enumerate(table) if value > ideal), len(table))
        on_flank = table[first_above - 2] if first_above >= 2 else table[first_above]
        by_flank += chosen == on_flank
        by_tip += chosen != on_flank
    # both conditions decide: the tip circle on most gears, the middle of the flank on the rest
    assert by_tip > 200 and by_flank > 150


def test_ideal_ball_of_the_program_is_exact_on_spur_gears_only() -> None:
    """On a spur gear the ball of the formula touches on the circle it is asked for; on a
    helical gear it does not (the program mixes the virtual and the real gear)."""

    def contact(z: int, m_n: float, x: float, beta: float, D_M: float) -> float:
        d_b = iv.base_diameter(z, m_n, ALPHA, beta)
        alpha_t = iv.transverse_pressure_angle(ALPHA, beta)
        eta = iv.space_width_half_angle(z, x, ALPHA)
        alpha_Kt = ins.ball_centre_profile_angle(D_M, z, m_n, ALPHA, eta, alpha_t)
        alpha_Mt = ins.ball_contact_profile_angle(
            alpha_Kt, D_M, d_b, iv.base_helix_angle(beta, ALPHA)
        )
        return ins.ball_measuring_circle_diameter(d_b, alpha_Mt)

    for z, m_n, x, d_y in (
        (12, 2.0, -0.0446, 24.4535),
        (40, 3.0, 0.2, 121.5),
        (25, 1.0, 0.0, 25.3),
    ):
        ball = stplus_ideal_measuring_ball_diameter(z, m_n, x, ALPHA, 0.0, d_y)
        assert contact(z, m_n, x, 0.0, ball) == pytest.approx(d_y, abs=1e-9)
    beta = math.radians(30.0)
    d = iv.reference_diameter(40, 3.0, beta)
    ball = stplus_ideal_measuring_ball_diameter(40, 3.0, -0.0527, ALPHA, beta, d - 1.1241)
    assert ball == pytest.approx(6.0, abs=1e-3)  # the switch 5 -> 5,5 mm of the experiment
    assert contact(40, 3.0, -0.0527, beta, ball) - (d - 1.1241) == pytest.approx(2.834, abs=2e-3)
    exact = brentq(lambda D: contact(40, 3.0, -0.0527, beta, D) - (d - 1.1241), 4.0, 6.0)
    assert exact == pytest.approx(4.695, abs=0.005)
    # many teeth at a large helix angle: the bracket is negative, the program takes its amount
    many = stplus_ideal_measuring_ball_diameter(
        121, 10.0, 0.1619, math.radians(25.0), math.radians(40.0), 1583.6665
    )
    assert many == pytest.approx(57.53, abs=0.01)
    with pytest.raises(GeometryInfeasibleError, match="virtual spur gear"):
        stplus_ideal_measuring_ball_diameter(20, 2.0, 0.0, ALPHA, 0.0, 30.0)


def test_switch_points_found_by_bisection() -> None:
    """z 12, m_n 2, x_E -0,0446, d_Ff 22,651 (probe family ``measuring_ball_of_the_program``):
    the ball changes where the ball two table values further up touches on the middle of the
    form circles; z 40, m_n 2, x_E -0,0584, d_Ff 76,467: where the two-ball dimension of the
    smaller ball equals the tip diameter."""

    def chosen(z: int, x_E: float, d_a: float, d_Ff: float) -> float:
        return stplus_measuring_ball_diameter(z, 2.0, x_E, ALPHA, 0.0, d_a, d_Ff, d_a)

    for d_a, below, above in (
        (25.0699, 2.75, 3.0),
        (26.2559, 3.0, 3.5),
        (27.2668, 3.5, 4.0),
        (28.1566, 4.0, 4.5),
    ):
        assert chosen(12, -0.0446, d_a - 0.002, 22.651) == below
        assert chosen(12, -0.0446, d_a + 0.002, 22.651) == above
    for d_a, below, above in ((80.7955, 2.5, 2.75), (81.8892, 2.75, 3.0), (82.9060, 3.0, 3.5)):
        assert chosen(40, -0.0584, d_a - 0.002, 76.467) == below
        assert chosen(40, -0.0584, d_a + 0.002, 76.467) == above


def test_given_ball_and_the_ends_of_the_table() -> None:
    arguments = (12, 2.0, -0.0446, ALPHA, 0.0, 27.4, 22.651, 27.4)
    # probes measuring_ball_given_above_the_tip / _below_the_tip
    assert stplus_measuring_ball_diameter(*arguments, given_mm=3.25) == 3.25
    assert stplus_measuring_ball_diameter(*arguments, given_mm=3.4) == 3.4  # no table value
    assert stplus_measuring_ball_diameter(*arguments, given_mm=3.0) == 4.0
    assert stplus_measuring_ball_diameter(*arguments) == 4.0
    # a module below the table: the smallest ball, 1 mm (m_n 0,2: five modules)
    d = 20 * 0.2
    small = stplus_measuring_ball_diameter(20, 0.2, 0.0, ALPHA, 0.0, d + 0.4, d - 0.3, d + 0.4)
    assert small == 1.0
    # beyond the table the program prints D_M = 0
    with pytest.raises(GeometryInfeasibleError, match="prints D_M = 0"):
        stplus_measuring_ball_diameter(30, 80.0, 0.0, ALPHA, 0.0, 2560.0, 2270.0, 2560.0)
    with pytest.raises(InputRangeError):
        stplus_measuring_ball_diameter(12, 2.0, 0.0, ALPHA, 0.0, 27.4, 27.4, 22.651)
    with pytest.raises(GearCoreError):
        stplus_measuring_ball_diameter(12, 2.0, 0.0, ALPHA, 0.0, 27.4, 22.651, 27.4, given_mm=-1.0)


@pytest.mark.parametrize("case", [folder.name for folder in stplus_case_dirs()])
def test_choices_of_every_packaged_listing(case: str) -> None:
    """With the form circles gearcore generates, the rules name the k and the D_M the listing
    prints: nothing of the comparison of the inspection dimensions is taken from the listing."""
    data = generation_data(case)
    k, D_M = stplus_inspection_choices(compute_generation_from_data(data, data.values))
    listing = load_stplus(case, "geometry")
    assert list(k) == [int(value) for value in listing["k"]["numbers"][:2]]
    assert list(D_M) == listing["D_M"]["numbers"][:2]


def _printed(listing: str, label: str) -> list[float]:
    """The numbers at the end of the first row of a listing that begins with ``label``."""
    for line in listing.splitlines():
        if re.match(rf"^\s*{label}", line) and "=" not in line:
            values: list[float] = []
            for token in reversed(line.split()):
                if re.fullmatch(r"-?\d+(\.\d+)?", token):
                    values.insert(0, float(token))
                elif values:
                    break
            if values:
                return values
    raise AssertionError(label)


def test_choices_of_the_probes() -> None:
    """Probes of 2026-10-04: the span of gear 2 over the k of the program (7, the input said 8),
    and the balls that follow the tip circle or replace a given ball below it."""
    pair = pair_input_from_ste(
        load_ste(PROBES / "span_with_upper_allowance_of_gear_one" / "input.ste")
    ).pair
    assert stplus_inspection_choices(gn.compute_generation(pair))[0] == (5, 7)

    for name, given, expected in (
        ("measuring_ball_of_the_program", None, 3.5),
        ("measuring_ball_of_the_program_larger_tip", None, 4.0),
        ("measuring_ball_given_above_the_tip", 3.25, 3.25),
        ("measuring_ball_given_below_the_tip", 3.0, 4.0),
    ):
        listing = (PROBES / name / "report.sta.txt").read_text(encoding="latin-1")
        chosen = stplus_measuring_ball_diameter(
            12,
            2.0,
            _printed(listing, r"Erz\.-Profilversch\.faktor")[0],
            ALPHA,
            0.0,
            _printed(listing, r"Kopfkreisdurchmesser  ")[0],
            _printed(listing, r"Fuss-Formkreisdurchmesser")[0],
            _printed(listing, r"Kopf-Formkreisdurchmesser")[0],
            given_mm=given,
        )
        assert chosen == expected == _printed(listing, r"Messtueckdurchmesser")[0], name
    # stated as inputs, the choices give the dimensions of the listing; nothing else changes
    generation = gn.compute_generation(pair)
    as_stplus = ins.compute_inspection(with_stplus_inspection_choices(generation)).gears.wheel
    by_norm = ins.compute_inspection(generation).gears.wheel
    assert (as_stplus.number_of_teeth_spanned, by_norm.number_of_teeth_spanned) == (7, 8)
    assert as_stplus.profile_shift_coefficient == by_norm.profile_shift_coefficient
    assert as_stplus.span_measurement_mm is not None and by_norm.span_measurement_mm is not None
    assert by_norm.span_measurement_mm.upper == pytest.approx(46.21, abs=1e-9)
    assert as_stplus.span_measurement_mm.upper == pytest.approx(
        46.21 - math.pi * 2.0 * math.cos(ALPHA), abs=1e-9
    )
    with pytest.raises(InputRangeError, match="GenerationResult"):
        stplus_inspection_choices(pair)  # type: ignore[arg-type]
    # gearcore itself chooses by the norm: the next larger value of DIN 3977 above the ideal ball
    pair = pair_input_from_ste(
        load_ste(PROBES / "measuring_ball_of_the_program" / "input.ste")
    ).pair
    ours = ins.compute_inspection(gn.compute_generation(pair)).gears
    assert ours.pinion.measuring_ball_diameter_mm == 3.75
