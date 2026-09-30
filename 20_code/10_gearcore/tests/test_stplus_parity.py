"""Parity of gearcore with the STplus oracle fixtures (ADR-102, ADR-105, ADR-106).

STplus is a numeric oracle only: a mismatch on a fixture with ``trust: unverified`` is reported as
an expected failure, a mismatch elsewhere must either be fixed in gearcore or — when the current
norm deviates from the STplus chain — be recorded in ``expected_differences.yaml``.

STplus computes in single precision (binary32, about seven significant digits): every interface
value of the basic geometry is reproduced by a 32-bit evaluation of the same formulas, while the
64-bit result misses some of them by more than half a printed digit (probe of 2026-09-29, pinned
in ``test_stplus_interface_values_come_from_a_single_precision_chain``). gearcore computes in
binary64 throughout, so the oracle bounds the comparison, not gearcore.
"""

import json
import math
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np
import pytest

from gearcore import parity
from gearcore.data import stplus_case_dirs
from gearcore.errors import InputRangeError, ParseError
from gearcore.involute import compute_basic_gear_geometry
from gearcore.io.ste import load_ste, pair_input_from_ste
from gearcore.models.results import BasicGearGeometry
from gearcore.parity import (
    ARITHMETIC_STEPS,
    COMPARED_FIELDS,
    PROFILE_SHIFT_FIELD,
    ParityRow,
    ParityVerdict,
    binary32_step,
    compare_basic_geometry,
    printed_decimals,
    stplus_names,
)

ALL_FIELDS = (*sorted(COMPARED_FIELDS), PROFILE_SHIFT_FIELD)
HELICAL_RUNS = ("helix20_z25_65", "helix30_z25_40")

# State of increment 1 over the 15 packaged cases; a new fixture or quantity changes these numbers
# deliberately (ADR-106 quotes them).
EXPECTED_VERDICTS = {
    ("listing", "identical"): 253,
    ("listing", "oracle_accuracy"): 1,
    ("interface", "identical"): 178,
    ("interface", "oracle_accuracy"): 11,
}


def _load(case_dir: Path, name: str) -> dict[str, Any] | None:
    path = case_dir / f"{name}.json"
    if not path.is_file():
        return None
    loaded: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return loaded


def _per_gear(numbers: list[float], gear: int) -> float:
    return numbers[gear] if len(numbers) > 1 else numbers[0]


def _describe(row: ParityRow) -> str:
    tolerance = row.print_tolerance + row.arithmetic_tolerance + row.input_tolerance
    return (
        f"{row.gear} {row.field}: gearcore {row.gearcore_value!r} vs STplus {row.origin} "
        f"{row.stplus_token} (difference {row.difference:.2e}, tolerance {tolerance:.2e})"
    )


@pytest.mark.oracle
@pytest.mark.parametrize("field", ALL_FIELDS)
def test_basic_gear_geometry_matches_stplus(case_dir: Path, field: str) -> None:
    rows = [row for row in compare_basic_geometry(case_dir.name) if row.field == field]
    if field != "profile_shift_coefficient":
        has_interface = (case_dir / "interface.json").is_file()
        assert len(rows) == (4 if has_interface else 2), "one row per gear and STplus output"
    mismatches = [_describe(row) for row in rows if row.verdict is ParityVerdict.DIFFERENT]
    if mismatches and rows[0].trust == "unverified":
        pytest.xfail("unverified reference pair: " + "; ".join(mismatches))
    assert not mismatches, "; ".join(mismatches)


@pytest.mark.oracle
def test_the_listing_needs_no_arithmetic_tolerance(case_dir: Path) -> None:
    """The decimals of the listing hide the single precision of STplus: every listing value is
    explained by the print tolerance and, where STplus derived x, the rounding of the printed x."""
    rows = [row for row in compare_basic_geometry(case_dir.name) if row.origin == "listing"]
    beyond = [
        _describe(row)
        for row in rows
        if abs(row.difference) > row.print_tolerance + row.input_tolerance + 1e-9
    ]
    if beyond and rows[0].trust == "unverified":
        pytest.xfail("unverified reference pair: " + "; ".join(beyond))
    assert not beyond, "; ".join(beyond)


@pytest.mark.oracle
def test_verdict_counts_of_increment_1() -> None:
    cases = stplus_case_dirs()
    assert len(cases) == 15
    rows = [row for case in cases for row in compare_basic_geometry(case.name)]
    counts = Counter((row.origin, row.verdict.value) for row in rows)
    assert dict(counts) == EXPECTED_VERDICTS
    assert len(rows) == sum(EXPECTED_VERDICTS.values()) == 443


def test_parity_rows_separate_the_tolerance_parts() -> None:
    rows = compare_basic_geometry("helix30_z25_40")
    row = next(
        r
        for r in rows
        if r.field == "reference_diameter_mm" and r.gear == "pinion" and r.origin == "interface"
    )
    assert row.stplus_token == "86.60255" and printed_decimals(row.stplus_token) == 5
    assert row.symbol == "d" and row.unit == "mm" and row.trust == "generated"
    assert row.print_tolerance == 0.5e-5 and row.input_tolerance == 0.0
    assert row.arithmetic_tolerance == ARITHMETIC_STEPS * 2.0**-17  # binary32 step in [64, 128)
    assert row.difference == pytest.approx(86.602540378444 - 86.60255, abs=1e-12)
    assert row.verdict is ParityVerdict.ORACLE_ACCURACY
    listing = next(
        r
        for r in rows
        if r.field == "reference_diameter_mm" and r.gear == "pinion" and r.origin == "listing"
    )
    assert listing.verdict is ParityVerdict.IDENTICAL
    assert ParityRow.model_validate_json(row.model_dump_json()) == row


def test_profile_shift_is_an_input_or_a_printed_value() -> None:
    """x given in input.ste is used as it is (no input tolerance); x derived by STplus is taken
    from the print and its rounding is carried by the thickness quantities."""
    given = compare_basic_geometry("helix30_z25_40")
    assert {r.gearcore_value for r in given if r.field == "profile_shift_coefficient"} == {
        0.3,
        -0.1,
    }
    assert all(r.input_tolerance == 0.0 for r in given)

    derived = compare_basic_geometry("kst_b_rerun")  # x from the span measurement
    assert not [r for r in derived if r.field == "profile_shift_coefficient"]
    thickness = [r for r in derived if r.field == "normal_tooth_thickness_mm"]
    assert thickness and all(r.input_tolerance > 0.0 for r in thickness)
    # s_n = m_n (pi/2 + 2 x tan alpha_n): half a unit of the fifth decimal of x, m_n = 2
    interface = next(r for r in thickness if r.origin == "interface")
    assert interface.input_tolerance == pytest.approx(2 * 2.0 * math.tan(math.radians(20)) * 0.5e-5)
    other = [r for r in derived if r.field == "base_diameter_mm"]
    assert all(r.input_tolerance == 0.0 for r in other)


def test_stplus_overrides_a_given_x2_when_the_centre_distance_is_given() -> None:
    """kst-E gives a, x1 and x2; STplus keeps x1 and derives x2 from a (0.31433 instead of
    0.3143). The printed x2 is therefore the input of the wheel, not the value of input.ste."""
    rows = compare_basic_geometry("kst_e_rerun")
    shifts = {(r.gear, r.origin): r for r in rows if r.field == "profile_shift_coefficient"}
    assert set(shifts) == {("pinion", "listing"), ("pinion", "interface")}
    assert shifts[("pinion", "interface")].stplus_token == "0.20340"
    pair = pair_input_from_ste(
        load_ste(stplus_case_dirs()[0].parent / "kst_e_rerun/input.ste")
    ).pair
    assert pair.gears.wheel.profile_shift_coefficient == 0.3143 and pair.centre_distance_mm == 52.0
    interface = _load(stplus_case_dirs()[0].parent / "kst_e_rerun", "interface")
    assert interface is not None
    assert interface["GEOMETRIEDATEN/PROFILVERSCHIEBFAKTOR"]["values"][1] == "0.31433"


Mutation = Callable[[BasicGearGeometry], dict[str, Any]]


def _different_rows(
    monkeypatch: pytest.MonkeyPatch, case: str, mutate: Mutation
) -> list[ParityRow]:
    def mutated(**kwargs: Any) -> BasicGearGeometry:
        result = compute_basic_gear_geometry(**kwargs)
        return result.model_copy(update=mutate(result))

    monkeypatch.setattr(parity, "compute_basic_gear_geometry", mutated)
    return [r for r in compare_basic_geometry(case) if r.verdict is ParityVerdict.DIFFERENT]


@pytest.mark.parametrize("case", HELICAL_RUNS)
def test_a_sign_error_of_the_base_helix_angle_is_detected(
    monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    rows = _different_rows(
        monkeypatch, case, lambda g: {"base_helix_angle_deg": -g.base_helix_angle_deg}
    )
    assert {(r.field, r.origin) for r in rows} == {("base_helix_angle_deg", "interface")}
    assert {r.gear for r in rows} == {"pinion", "wheel"}


@pytest.mark.parametrize("case", HELICAL_RUNS)
def test_a_relative_error_of_five_in_ten_million_is_detected(
    monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    rows = _different_rows(
        monkeypatch, case, lambda g: {"base_diameter_mm": g.base_diameter_mm * (1.0 + 5.0e-7)}
    )
    # detection limit of the oracle: two binary32 steps (up to 2.4e-7 relative) plus half a digit
    assert {(r.field, r.origin) for r in rows} == {("base_diameter_mm", "interface")}


def test_a_wrong_pi_in_the_tooth_thickness_is_detected(monkeypatch: pytest.MonkeyPatch) -> None:
    def truncated_pi(g: BasicGearGeometry) -> dict[str, Any]:
        correct = g.normal_module_mm * (math.pi / 2.0)
        wrong = g.normal_module_mm * (3.14159 / 2.0)
        return {"normal_tooth_thickness_mm": g.normal_tooth_thickness_mm - correct + wrong}

    rows = _different_rows(monkeypatch, "helix30_z25_40", truncated_pi)
    assert {(r.field, r.origin) for r in rows} == {("normal_tooth_thickness_mm", "interface")}


def test_printed_decimals_accepts_fixed_point_tokens_only() -> None:
    assert printed_decimals("86.60255") == 5 and printed_decimals(" -0.3000 ") == 4
    assert printed_decimals("25") == 0 and printed_decimals("+4.350") == 3
    for token in ("1.5E-03", "0.12345E+02", "1e5", "", ".5", "abc", "1.2.3", "nan"):
        with pytest.raises(ParseError, match="fixed-point"):
            printed_decimals(token)


def test_binary32_step() -> None:
    assert binary32_step(1.0) == 2.0**-23 and binary32_step(86.60255) == 2.0**-17
    assert binary32_step(-345.85779) == 2.0**-15 and binary32_step(0.0) == 2.0**-149
    for value in (0.3, 1.0, 86.60255, 345.85779, 1e-3):
        assert binary32_step(value) == float(np.spacing(np.float32(value)))
    with pytest.raises(InputRangeError):
        binary32_step(math.nan)


def test_unknown_cases_are_typed_errors() -> None:
    for case in ("nope", "fzg_c/../kst_e", "../stplus/kst_e", "", "kst_e/"):
        with pytest.raises(InputRangeError, match="unknown STplus fixture case"):
            compare_basic_geometry(case)


def _r32(value: float) -> float:
    """Round a binary64 value to the nearest binary32 number (deterministic on every platform)."""
    return float(np.float32(value))


def _single_precision_chain(
    z: int, m_n: float, alpha_deg: float, beta_deg: float
) -> dict[str, float]:
    """The basic geometry with every operation rounded to binary32; test evidence only."""
    rad = _r32(_r32(math.pi) / 180.0)
    alpha = _r32(_r32(alpha_deg) * rad)
    beta = _r32(_r32(abs(beta_deg)) * rad)
    cos_beta = _r32(math.cos(beta))
    m_t = _r32(_r32(m_n) / cos_beta)
    d = _r32(z * m_t)
    alpha_t = _r32(math.atan(_r32(_r32(math.tan(alpha)) / cos_beta)))
    beta_b = _r32(math.asin(_r32(_r32(math.sin(beta)) * _r32(math.cos(alpha)))))
    return {
        "transverse_pressure_angle_deg": _r32(alpha_t / rad),
        "base_helix_angle_deg": _r32(beta_b / rad),
        "transverse_module_mm": m_t,
        "reference_diameter_mm": d,
        "base_diameter_mm": _r32(d * _r32(math.cos(alpha_t))),
    }


def _double_precision_chain(
    z: int, m_n: float, alpha_deg: float, beta_deg: float
) -> dict[str, float]:
    result = compute_basic_gear_geometry(
        number_of_teeth=z,
        normal_module_mm=m_n,
        normal_pressure_angle_deg=alpha_deg,
        helix_angle_deg=abs(beta_deg),
        profile_shift_coefficient=0.0,
    )
    return {field: getattr(result, field) for field in _single_precision_chain(z, m_n, 20.0, 0.0)}


def _printed_interface_values(case_dir: Path) -> list[tuple[str, int, float, float, float]]:
    """(field, gear, printed, binary32 value, binary64 value) of the five basic quantities."""
    interface = _load(case_dir, "interface")
    assert interface is not None
    pair = pair_input_from_ste(load_ste(case_dir / "input.ste")).pair
    values = []
    for gear, gear_input in enumerate(pair.gears.as_tuple()):
        args = (
            gear_input.number_of_teeth,
            pair.normal_module_mm,
            pair.normal_pressure_angle_deg,
            pair.helix_angle_deg,
        )
        single, double = _single_precision_chain(*args), _double_precision_chain(*args)
        for field in single:
            numbers = interface[f"GEOMETRIEDATEN/{stplus_names(field)[1]}"]["numbers"]
            if gear < len(numbers):
                values.append((field, gear, abs(numbers[gear]), single[field], double[field]))
    return values


@pytest.mark.oracle
def test_stplus_interface_values_come_from_a_single_precision_chain(case_dir: Path) -> None:
    if not (case_dir / "interface.json").is_file():
        pytest.skip("supplied listing without interface file")
    for field, gear, printed, single, _ in _printed_interface_values(case_dir):
        assert f"{single:.5f}" == f"{printed:.5f}", (
            f"{case_dir.name} gear {gear + 1} {field}: 32-bit chain {single!r} vs STplus {printed!r}"
        )


@pytest.mark.oracle
def test_evidence_for_single_precision_as_quoted_in_adr_106() -> None:
    runs = [case for case in stplus_case_dirs() if (case / "interface.json").is_file()]
    values = [(case.name, *row) for case in runs for row in _printed_interface_values(case)]
    single_hits = [v for v in values if f"{v[4]:.5f}" == f"{v[3]:.5f}"]
    double_hits = [v for v in values if f"{v[5]:.5f}" == f"{v[3]:.5f}"]
    stored_hits = [v for v in values if f"{_r32(v[5]):.5f}" == f"{v[3]:.5f}"]
    assert len(runs) == 11 and len(values) == 99
    assert (len(double_hits), len(stored_hits), len(single_hits)) == (93, 95, 99)
    missed = {v[0] for v in values if v not in double_hits}
    assert missed == set(HELICAL_RUNS), "binary64 misses values of the helical runs only"
    helical = [v for v in values if v[0] in HELICAL_RUNS]
    assert len(helical) == 18, "the 81 values of the nine spur runs are insensitive (beta = 0)"
    worst_steps = max(
        abs(v[3] - v[5]) / binary32_step(v[5]) for v in values if v not in double_hits
    )
    assert 1.4 < worst_steps < ARITHMETIC_STEPS


def test_single_precision_is_visible_in_the_helical_reference_diameter() -> None:
    """d = 25 * 3 / cos(30 deg) = 86.6025404 mm; STplus prints 86.60255 (one binary32 step above)."""
    exact = compute_basic_gear_geometry(
        number_of_teeth=25,
        normal_module_mm=3.0,
        normal_pressure_angle_deg=20.0,
        helix_angle_deg=30.0,
        profile_shift_coefficient=0.0,
    ).reference_diameter_mm
    assert exact == pytest.approx(50.0 * math.sqrt(3.0), rel=4 * math.ulp(1.0))
    single = _single_precision_chain(25, 3.0, 20.0, 30.0)["reference_diameter_mm"]
    assert f"{exact:.5f}" == "86.60254" and f"{single:.5f}" == "86.60255"
    assert abs(single - exact) <= ARITHMETIC_STEPS * binary32_step(exact)


def test_the_interface_file_is_used_where_it_exists(case_dir: Path) -> None:
    meta = _load(case_dir, "meta")
    assert meta is not None
    has_interface = (case_dir / "interface.json").is_file()
    assert has_interface == (meta["origin"] == "run"), (
        f"{case_dir.name}: own runs carry the interface file, supplied listings do not"
    )
