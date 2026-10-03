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
from gearcore.data import (
    has_stplus,
    load_expected_differences,
    load_norm_deviations,
    load_stplus,
    stplus_case_dirs,
)
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
    compare_generation,
    compare_pair_geometry,
    compute_pair_from_data,
    pair_data,
    printed_decimals,
    stplus_names,
)

ALL_FIELDS = (*sorted(COMPARED_FIELDS), PROFILE_SHIFT_FIELD)
HELICAL_RUNS = ("helix15_b_unequal", "helix20_z25_65", "helix30_z25_40")

# State over the 18 packaged cases (15 of increment 1, three added by the gate of increment 2);
# a new fixture or quantity changes these numbers deliberately (ADR-106 quotes them).
EXPECTED_VERDICTS = {
    ("listing", "identical"): 306,
    ("listing", "oracle_accuracy"): 1,
    ("interface", "identical"): 225,
    ("interface", "oracle_accuracy"): 17,
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
    assert len(cases) == 18
    rows = [row for case in cases for row in compare_basic_geometry(case.name)]
    counts = Counter((row.origin, row.verdict.value) for row in rows)
    assert dict(counts) == EXPECTED_VERDICTS
    assert len(rows) == sum(EXPECTED_VERDICTS.values()) == 549


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
    imported = pair_input_from_ste(load_ste(stplus_case_dirs()[0].parent / "kst_e_rerun/input.ste"))
    pair = imported.pair
    # gearcore admits only two of a_w, x_1, x_2 (ADR-107): the importer says that it drops x_2
    assert pair.gears.wheel.profile_shift_coefficient is None and pair.centre_distance_mm == 52.0
    assert pair.gears.wheel.span is None, "the span of the file is an inspection dimension"
    assert any("x_2 = 0.3143 of the file is not passed on" in note for note in imported.notes)
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
    assert len(runs) == 14 and len(values) == 126
    assert (len(double_hits), len(stored_hits), len(single_hits)) == (117, 120, 126)
    missed = Counter(v[0] for v in values if v not in double_hits)
    # the helical runs, and one base diameter of a spur run (d_b2 = 126.8585038 mm, printed
    # 126.85851): most spur values are insensitive, not all
    assert missed == {
        "helix15_b_unequal": 2,
        "helix20_z25_65": 4,
        "helix30_z25_40": 2,
        "a_x2_only_z18_45": 1,
    }
    helical = [v for v in values if v[0] in HELICAL_RUNS]
    assert len(helical) == 27
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


# --- pair geometry (increment 2) ------------------------------------------------------------------

# no value differs: the common tooth depth follows the tip form circles like STplus (ADR-112)
EXPECTED_PAIR_VERDICTS = {"identical": 786, "oracle_accuracy": 69}
# tip form diameter below the tip diameter: an edge break flank of the tool at the wheel (kst),
# a tip chamfer given as an input on both gears (chamfer_hk)
CHAMFERED_CASES = {
    "kst_b",
    "kst_b_rerun",
    "kst_c",
    "kst_c_rerun",
    "kst_e",
    "kst_e_rerun",
    "chamfer_hk_z20_34",
}


def _pair_rows() -> list[ParityRow]:
    return [row for case in stplus_case_dirs() for row in compare_pair_geometry(case.name)]


@pytest.mark.oracle
def test_verdict_counts_of_the_pair_geometry() -> None:
    rows = _pair_rows()
    counts = Counter(row.verdict.value for row in rows)
    assert dict(counts) == EXPECTED_PAIR_VERDICTS
    assert len(rows) == 855
    by_origin = Counter((row.origin, row.verdict.value) for row in rows)
    assert by_origin == {
        ("listing", "identical"): 470,
        ("listing", "oracle_accuracy"): 10,
        ("interface", "identical"): 316,
        ("interface", "oracle_accuracy"): 59,
    }
    assert {row.field for row in rows} == set(parity.PAIR_FIELDS)
    # every case contributes, the supplied listings without interface file with the listing only
    per_case = Counter(row.case for row in rows)
    assert len(per_case) == 18 and min(per_case.values()) >= 26


@pytest.mark.eq("ISO21771:2014", "(59)")
@pytest.mark.oracle
def test_common_tooth_depth_follows_the_tip_form_circles() -> None:
    """User decision ADR-112: h_w is Eq. (59) evaluated with the tip form circles, as STplus prints
    it. With the tip circles, by the letter of both norms, the value is larger by the radial
    amounts of the chamfers; the result names that value."""
    from gearcore.pair import common_tooth_depth

    record = load_norm_deviations()["common_tooth_depth_with_tip_form_circles"]
    assert record["field"] == "common_tooth_depth_mm"
    assert (record["norm"]["eq"], record["old_norm"]["eq"]) == ("(59)", "(4.2.08)")
    assert load_expected_differences() == {}, "no value differs from STplus without explanation"
    chamfered: set[str] = set()
    for path in stplus_case_dirs():
        data = pair_data(path.name)
        ours = compute_pair_from_data(data, data.values)
        form, tip = ours.tip_form_diameter_mm, ours.tip_diameter_mm
        chamfer = 0.5 * (tip.pinion - form.pinion) + 0.5 * (tip.wheel - form.wheel)
        by_norm = common_tooth_depth(tip.pinion, tip.wheel, ours.centre_distance_mm)
        assert by_norm - ours.common_tooth_depth_mm == pytest.approx(chamfer, abs=1e-12)
        noted = [w for w in ours.warnings if w.code == "common_tooth_depth_with_tip_form_circles"]
        assert bool(noted) == (chamfer > 0.0), path.name
        rows = [r for r in compare_pair_geometry(path.name) if r.field == "common_tooth_depth_mm"]
        assert rows and all(row.verdict is not ParityVerdict.DIFFERENT for row in rows), path.name
        if not noted:
            continue
        chamfered.add(path.name)
        assert repr(by_norm) in noted[0].message
        # the value of the tip circles is not what STplus prints
        for row in rows:
            tolerance = row.print_tolerance + row.arithmetic_tolerance + row.input_tolerance
            assert abs(by_norm - row.stplus_value) > 10.0 * tolerance, path.name
    assert chamfered == CHAMFERED_CASES
    example = record["example"]
    data = pair_data(example["case"])
    ours = compute_pair_from_data(data, data.values)
    assert ours.common_tooth_depth_mm == pytest.approx(example["gearcore_value"], abs=1e-12)
    assert common_tooth_depth(
        ours.tip_diameter_mm.pinion, ours.tip_diameter_mm.wheel, ours.centre_distance_mm
    ) == pytest.approx(example["norm_value"], abs=1e-12)
    row = next(
        r
        for r in compare_pair_geometry(example["case"])
        if r.field == "common_tooth_depth_mm" and r.origin == "interface"
    )
    assert row.stplus_value == example["stplus_value"]


def test_pair_data_says_which_inputs_come_from_an_stplus_output() -> None:
    """Only what STplus derived itself is taken from its output, and only that has a rounding."""
    given = pair_data("helix20_z25_65")  # a and x_1 in the input, tip diameters chosen by STplus
    assert set(given.printed) == {"d_a1", "d_a2", "d_Ff1", "d_Ff2"}
    assert "x_2" not in given.values and given.values["x_1"] == 0.25
    spans = pair_data("kst_b_rerun")  # x from span measurements, tool breaks the wheel tip
    assert set(spans.printed) == {"x_1", "d_Fa2", "d_Ff1", "d_Ff2"}
    assert spans.values["d_a1"] == 76.46 and spans.values["d_Fa2"] == 112.37595
    shifts = pair_data("undercut_z12_x0")  # x_1 and x_2 in the input, no centre distance
    assert "a_w" not in shifts.values and shifts.values["x_2"] == 0.0
    rows = compare_pair_geometry("helix20_z25_65")
    fields = {(row.field, row.gear) for row in rows}
    assert ("profile_shift_coefficient", "wheel") in fields, "x_2 follows from a_w: a result"
    assert ("profile_shift_coefficient", "pinion") not in fields, "x_1 was an input"
    assert not [row for row in rows if row.field == "centre_distance_mm"]
    assert [
        row for row in compare_pair_geometry("undercut_z12_x0") if row.field == "centre_distance_mm"
    ]


def test_pair_tolerances_follow_from_the_error_propagation() -> None:
    rows = {(r.field, r.gear, r.origin): r for r in compare_pair_geometry("fzg_c")}
    depth = rows[("common_tooth_depth_mm", "pinion", "interface")]
    # h_w = (82,45 + 118,35) / 2 - 91,5: the accuracy is that of the operands near 100 mm
    assert depth.gearcore_value == pytest.approx(8.9, abs=1e-12) and depth.stplus_token == "8.89999"
    assert depth.arithmetic_tolerance > ARITHMETIC_STEPS * binary32_step(91.5)
    assert depth.verdict is ParityVerdict.ORACLE_ACCURACY
    pitch = rows[("normal_pitch_mm", "pinion", "interface")]
    assert pitch.input_tolerance == 0.0 and pitch.verdict is ParityVerdict.IDENTICAL
    # a value that depends on a printed root form diameter carries its rounding
    limited = {(r.field, r.gear, r.origin): r for r in compare_pair_geometry("undercut_z12_x0")}
    start = limited[("sap_diameter_mm", "pinion", "interface")]
    assert start.input_tolerance == pytest.approx(0.5e-5, rel=1e-6)


@pytest.mark.parametrize(
    "field, relative_error",
    [
        ("transverse_working_pressure_angle_deg", 1e-5),
        ("working_pitch_diameter_mm", 1e-5),
        ("sap_diameter_mm", 1e-5),
        ("length_of_path_of_contact_mm", 2e-5),
        ("transverse_contact_ratio", 2e-5),
        ("overlap_ratio", 2e-5),
        ("sliding_factor_at_tip", 1e-4),
        ("specific_sliding_at_end_points", 1e-4),
    ],
)
def test_pair_comparison_detects_relative_errors(
    monkeypatch: pytest.MonkeyPatch, field: str, relative_error: float
) -> None:
    """Detection limit of the pair comparison on helix20_z25_65 (interface file, five decimals):
    a relative error of 1e-5 in diameters and angles, 2e-5 in the path of contact and the contact
    ratios, 1e-4 in the sliding quantities is reported as ``different``."""
    original = parity.compute_pair_from_data

    def mutated(d: Any, values: dict[str, float]) -> Any:
        # every computation carries the error, so the error propagation sees the same defect
        result = original(d, values)
        value = getattr(result, field)
        scaled = (
            value.model_copy(update={"pinion": value.pinion * (1.0 + relative_error)})
            if hasattr(value, "pinion")
            else value * (1.0 + relative_error)
        )
        return result.model_copy(update={field: scaled})

    monkeypatch.setattr(parity, "compute_pair_from_data", mutated)
    rows = [row for row in compare_pair_geometry("helix20_z25_65") if row.field == field]
    wrong = [row for row in rows if row.origin == "interface" and row.gear == "pinion"]
    assert wrong and all(row.verdict is ParityVerdict.DIFFERENT for row in wrong), field


# --- tool-based generation (increment 3) ------------------------------------------------------------

EXPECTED_GENERATION_VERDICTS = {"identical": 364, "oracle_accuracy": 169}
EXPECTED_GENERATION_BY_ORIGIN = {
    ("listing", "identical"): 234,
    ("listing", "oracle_accuracy"): 66,
    ("interface", "identical"): 130,
    ("interface", "oracle_accuracy"): 103,
}
UNDERCUT_GEARS = {
    ("fzg_c", "pinion"),
    ("undercut_z12_x0", "pinion"),
    ("neg_shift_z17_xm08", "pinion"),
    ("small_z8_x05", "pinion"),
}
EDGE_BREAK_GEARS = {"kst_b", "kst_b_rerun", "kst_c", "kst_c_rerun", "kst_e", "kst_e_rerun"}
"""Cases whose wheel gets its tip chamfer from the edge break flank of the tool."""
ANGLE_WITHOUT_FLANK = {"helix20_z25_65"}
"""Cases whose tool states an edge break angle but has no edge break flank (its dedendum is its
root form height, the preset 1,3 of STplus): the chamfer height of zero is an input there."""


def _generation_rows() -> list[ParityRow]:
    return [row for case in stplus_case_dirs() for row in compare_generation(case.name)]


@pytest.mark.oracle
def test_verdict_counts_of_the_generation() -> None:
    rows = _generation_rows()
    assert dict(Counter(row.verdict.value for row in rows)) == EXPECTED_GENERATION_VERDICTS
    assert len(rows) == 533
    assert Counter((row.origin, row.verdict.value) for row in rows) == EXPECTED_GENERATION_BY_ORIGIN
    assert {row.field for row in rows} == set(parity.GENERATION_FIELDS) | set(
        parity.GENERATION_PAIR_FIELDS
    )
    per_case = Counter(row.case for row in rows)
    assert len(per_case) == 18 and min(per_case.values()) >= 16
    # the chamfer generated by the tool is compared (d_Fa, h_K, s_aK), a chamfer given as an input
    # is not; the listing prints s_aK without a symbol, so it is compared with the interface only
    with_chamfer = {row.case for row in rows if row.field == "tip_chamfer_radial_mm"}
    assert with_chamfer == EDGE_BREAK_GEARS and not with_chamfer & ANGLE_WITHOUT_FLANK
    assert {
        row.case
        for row in rows
        if row.field == "tip_chamfer_radial_mm" and row.gearcore_value > 0.0
    } == EDGE_BREAK_GEARS
    residual = {row.case for row in rows if row.field == "residual_tip_thickness_mm"}
    assert residual == {case for case in EDGE_BREAK_GEARS if case.endswith("_rerun")}
    assert all(
        row.gear == "wheel"
        for row in rows
        if row.field in ("tip_chamfer_radial_mm", "residual_tip_thickness_mm")
    )


@pytest.mark.eq("ISO21771:2014", "(128)")
@pytest.mark.oracle
def test_stplus_root_form_diameter_is_a_numerical_junction() -> None:
    """Evidence for ``parity.FORM_CIRCLE_ACCURACY_MM``: STplus prints as root form diameter the
    radius of a dedicated (doubled) vertex of its contour export, which deviates from the tangent
    point of Eq. (128), or from the exact intersection of an undercut gear, by micrometres while
    its curves agree with gearcore's within 0,6 um (``test_contour``)."""
    from gearcore.contour import stplus_contour
    from gearcore.parity import compute_generation_from_data, generation_data

    largest = 0.0
    checked = 0
    for path in stplus_case_dirs():
        case = path.name
        data = generation_data(case)
        result = compute_generation_from_data(data, data.values)
        listing = load_stplus(case, "geometry")
        interface = load_stplus(case, "interface") if has_stplus(case, "interface") else None
        for index, gear in enumerate(result.gears.as_tuple()):
            printed = (
                interface["GEOMETRIEDATEN/FUSSFORMKREISDURCHM"]["numbers"][index]
                if interface is not None
                else listing["d_Ff"]["numbers"][index]
            )
            deviation = abs(gear.root_form_diameter_mm - printed)
            largest = max(largest, deviation)
            assert deviation <= parity.FORM_CIRCLE_ACCURACY_MM, (case, index, deviation)
            checked += 1
            if not has_stplus(case, f"contour_wz{index + 1}"):
                continue
            points = stplus_contour(case, index + 1)
            diameters = 2.0 * np.hypot(points[:, 0], points[:, 1])
            nearest = int(np.argmin(np.abs(diameters - printed)))
            assert abs(diameters[nearest] - printed) < 5.0e-5, (case, index)
            neighbours = [
                abs(diameters[k] - diameters[nearest])
                for k in (nearest - 1, nearest + 1)
                if 0 <= k < len(diameters)
            ]
            assert min(neighbours) < 2.0e-5, (case, index, "the junction is a doubled vertex")
    assert checked == 36
    assert 0.006 < largest < parity.FORM_CIRCLE_ACCURACY_MM  # fzg_c pinion, 6,4 um


@pytest.mark.oracle
def test_undercut_gears_of_the_fixtures() -> None:
    from gearcore.parity import compute_generation_from_data, generation_data

    found = set()
    for path in stplus_case_dirs():
        data = generation_data(path.name)
        result = compute_generation_from_data(data, data.values)
        for role, gear in zip(("pinion", "wheel"), result.gears.as_tuple(), strict=True):
            if gear.undercut:
                found.add((path.name, role))
                assert (
                    gear.generating_profile_shift_coefficient
                    < gear.min_generating_profile_shift_coefficient
                )
    assert found == UNDERCUT_GEARS


@pytest.mark.oracle
def test_stplus_prints_the_transverse_allowance() -> None:
    """A_ste / OBERES_ZAHNDICKENABM of STplus is E_sns / cos(beta): the spur runs of the same DIN
    3967 band print the normal value, the helical runs the value divided by cos(beta)
    (registry note of ``tooth_thickness_allowance``)."""
    from gearcore.parity import generation_data

    spur = load_stplus("fzg_c", "interface")["GEOMETRIEDATEN/OBERES_ZAHNDICKENABM"]["numbers"]
    helical = load_stplus("helix30_z25_40", "interface")
    printed = helical["GEOMETRIEDATEN/OBERES_ZAHNDICKENABM"]["numbers"]
    beta = generation_data("helix30_z25_40").pair.helix_angle_deg
    assert spur == [-0.085, -0.085]  # d = 72 and 108 mm, series c25: -0,085 mm
    assert beta == 30.0 and printed[0] == pytest.approx(
        -0.085 / math.cos(math.radians(30.0)), abs=5.0e-4
    )
    # with the normal allowance the generating profile shift coefficient of STplus is reproduced
    rows = [
        r
        for r in compare_generation("helix30_z25_40")
        if r.field == "generating_profile_shift_coefficient"
    ]
    assert rows and all(r.verdict is ParityVerdict.IDENTICAL for r in rows)


@pytest.mark.oracle
def test_stplus_residual_thickness_without_a_chamfer_is_the_tip_tooth_thickness() -> None:
    """RESTDICKE equals ZAHNDICKE_KOPF (s_an, Eq. (48) at d_a) where there is no chamfer, and
    s_a - 2 (0,7 h_K) for a chamfer given by h_K (STplus default of the tangential amount, manual
    p. 19); with a tool edge break it is s_aK of DIN 3960 Eq. (A.3.05), compared in the rows."""
    from gearcore.parity import compute_generation_from_data, generation_data
    from gearcore.stplus_program import stplus_default

    factor = stplus_default("tip_chamfer_tangential").value
    checked = {"none": 0, "given": 0}
    for path in stplus_case_dirs():
        if not has_stplus(path.name, "interface"):
            continue
        data = generation_data(path.name)
        result = compute_generation_from_data(data, data.values)
        table = load_stplus(path.name, "interface")
        rest = table["GEOMETRIEDATEN/RESTDICKE"]["numbers"]
        tip = table["GEOMETRIEDATEN/ZAHNDICKE_KOPF"]["numbers"]
        for index, gear in enumerate(result.gears.as_tuple()):
            assert tip[index] == pytest.approx(gear.normal_tip_tooth_thickness_mm, abs=3.0e-5), (
                path.name
            )
            if (
                gear.tool_edge_break_angle_deg is not None
                and gear.tip_form_diameter_mm < gear.tip_diameter_mm
            ):
                continue
            if gear.tip_chamfer_radial_mm > 0.0:
                expected = (
                    gear.transverse_tip_tooth_thickness_mm
                    - 2.0 * factor * gear.tip_chamfer_radial_mm
                )
                checked["given"] += 1
            else:
                expected = gear.normal_tip_tooth_thickness_mm
                checked["none"] += 1
            assert rest[index] == pytest.approx(expected, abs=3.0e-5), (path.name, index)
    assert checked["given"] == 2 and checked["none"] >= 20


@pytest.mark.eq("ISO21771:2014", "(60)")
@pytest.mark.oracle
def test_tip_clearance_equation_against_stplus() -> None:
    """Eq. (60) with the generated root diameter STplus prints: c = a - d_a / 2 - d_fE(mate) / 2."""
    from gearcore.data import has_stplus, load_stplus
    from gearcore.pair import tip_clearance

    checked = 0
    for path in stplus_case_dirs():
        if not has_stplus(path.name, "interface"):
            continue
        table = load_stplus(path.name, "interface")

        def numbers(key: str, source: dict[str, Any] = table) -> list[float]:
            return [float(v) for v in source[f"GEOMETRIEDATEN/{key}"]["numbers"]]

        (a_w,) = numbers("ACHSABSTAND")
        tips, roots, printed = (
            numbers("KOPFKREISDURCHM"),
            numbers("FUSSKREISDURCHM"),
            numbers("KOPFSPIEL"),
        )
        for gear in (0, 1):
            ours = tip_clearance(a_w, tips[gear], roots[1 - gear])
            assert ours == pytest.approx(printed[gear], abs=3e-5), (path.name, gear)
            checked += 1
    assert checked == 28
