"""DIN 867:1986-02, ISO 53:1998, ISO 54:1996, DIN 3972:1952-02 — basic racks, tools, modules.

References are independent of the code under test: values printed in the norms (transcribed from
the rendered pages, kept as strings with their printed digits) and values computed with 45-digit
decimal arithmetic (marked "decimal reference").
"""

import math
from collections.abc import Callable

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from gearcore import rack
from gearcore.errors import GearCoreError, GeometryInfeasibleError, InputRangeError
from gearcore.models.profiles import BasicRackProfile

ALPHA = math.radians(20.0)
ULP = math.ulp(1.0)

# DIN 3972:1952-02, table on page 1, transcribed from the rendered page (strings keep the printed digits)
# m, t_0, h_kw I, h_kw II, h_kw III, p III, h_kw IV, p IV, r2
DIN3972_TABLE: list[tuple[str, str, str, str, str | None, str | None, str, str, str]] = [
    ("1", "3.1416", "1.167", "1.25", "1.50", "0.09", "1.85", "0.21", "0.08"),
    ("1.25", "3.9270", "1.46", "1.56", "1.83", "0.09", "2.21", "0.22", "0.12"),
    ("1.5", "4.7124", "1.75", "1.88", "2.16", "0.10", "2.56", "0.24", "0.20"),
    ("1.75", "5.4978", "2.04", "2.19", "2.49", "0.10", "2.91", "0.25", "0.25"),
    ("2", "6.2832", "2.33", "2.50", "2.82", "0.11", "3.26", "0.26", "0.30"),
    ("2.25", "7.0686", "2.63", "2.81", "3.14", "0.11", "3.60", "0.27", "0.40"),
    ("2.5", "7.8540", "2.92", "3.13", "3.46", "0.12", "3.94", "0.28", "0.50"),
    ("2.75", "8.6394", "3.21", "3.44", "3.79", "0.12", "4.28", "0.29", "0.50"),
    ("3", "9.4248", "3.50", "3.75", "4.11", "0.12", "4.62", "0.30", "0.60"),
    ("3.25", "10.2102", "3.79", "4.06", "4.43", "0.13", "4.95", "0.30", "0.60"),
    ("3.5", "10.9956", "4.08", "4.38", "4.75", "0.13", "5.28", "0.31", "0.70"),
    ("3.75", "11.7810", "4.38", "4.69", "5.08", "0.13", "5.63", "0.32", "0.75"),
    ("4", "12.5664", "4.67", "5.00", "5.40", "0.14", "5.95", "0.33", "0.80"),
    ("4.5", "14.1372", "5.25", "5.63", "6.04", "0.14", "6.60", "0.34", "0.90"),
    ("5", "15.7080", "5.84", "6.25", "6.68", "0.15", "7.28", "0.35", "1.00"),
    ("5.5", "17.2788", "6.42", "6.88", "7.32", "0.15", "7.92", "0.36", "1.10"),
    ("6", "18.8496", "7.00", "7.50", "7.95", "0.16", "8.59", "0.37", "1.20"),
    ("6.5", "20.4204", "7.59", "8.13", "8.59", "0.16", "9.24", "0.38", "1.30"),
    ("7", "21.9911", "8.17", "8.75", "9.23", "0.16", "9.90", "0.39", "1.40"),
    ("8", "25.1327", "9.34", "10.00", "10.5", "0.17", "11.20", "0.41", "1.60"),
    ("9", "28.2743", "10.50", "11.25", None, None, "12.50", "0.43", "1.80"),
    ("10", "31.4159", "11.67", "12.50", None, None, "13.79", "0.44", "2.00"),
    ("11", "34.5575", "12.84", "13.75", None, None, "15.08", "0.46", "2.20"),
    ("12", "37.6991", "14.00", "15.00", None, None, "16.37", "0.47", "2.40"),
    ("13", "40.8407", "15.2", "16.25", None, None, "17.66", "0.48", "2.60"),
    ("14", "43.9823", "16.3", "17.50", None, None, "18.95", "0.49", "2.80"),
    ("15", "47.1239", "17.5", "18.75", None, None, "20.23", "0.51", "3.00"),
    ("16", "50.2655", "18.7", "20.00", None, None, "21.51", "0.52", "3.20"),
]

# Cells whose printed value is not the correctly rounded value of the formula printed in the same
# norm. The formula is implemented, every deviating cell is pinned: (m, column) -> formula value.
# All six cells were read again from the page rendered at 400 dpi (2026-09-29).
DIN3972_TABLE_DEVIATIONS: dict[tuple[str, str], float] = {
    ("1.5", "p IV"): 0.23491,  # printed 0,24
    ("2", "h_kw III"): 2.81498,  # printed 2,82
    ("3.5", "h_kw IV"): 5.28598,  # printed 5,28
    ("3.75", "h_kw IV"): 5.61967,  # printed 5,63
    ("4.5", "h_kw IV"): 6.61558,  # printed 6,60
    ("5.5", "h_kw IV"): 7.93410,  # printed 7,92
}
DIN3972_LARGEST_DEVIATION_UNITS = 1.6
"""Largest deviation of a printed cell from the formula, in units of its last printed digit."""

# DIN 867:1986-02 Erläuterungen (p. 3): c_P* -> printed rho_fP* max, and the decimal reference of
# Eq. (7) and Eq. (8). The first printed value is not the rounded formula value (0.26).
DIN867_TABLE: list[tuple[float, str, float, float]] = [
    (0.17, "0.25", 0.25836657197872535, 0.51349488499552064),
    (0.25, "0.38", 0.37995084114518434, 0.47191061582906165),
    (0.3, "0.45", 0.45594100937422121, 0.44592044760002478),
    (0.4, "0.39", 0.60792134583229495, 0.39394011114195105),
]
DIN867_TABLE_DEVIATIONS = {0.17: 0.25836657197872535}


def printed_unit(text: str) -> float:
    """One unit of the last printed digit."""
    decimals = len(text.split(".")[1]) if "." in text else 0
    return float(10.0 ** (-decimals))


def assert_cell(m_text: str, column: str, printed: str, computed: float) -> None:
    """A table cell equals the rounded formula value, or it is one of the pinned deviations."""
    deviation_units = abs(computed - float(printed)) / printed_unit(printed)
    if (m_text, column) in DIN3972_TABLE_DEVIATIONS:
        assert computed == pytest.approx(DIN3972_TABLE_DEVIATIONS[(m_text, column)], abs=5e-6)
        assert 0.5 < deviation_units <= DIN3972_LARGEST_DEVIATION_UNITS, (
            f"m = {m_text}, {column}: pinned deviation changed ({deviation_units:.2f} units)"
        )
    else:
        assert deviation_units <= 0.5 + 1e-9, (
            f"m = {m_text}, {column}: formula {computed!r} vs printed {printed} "
            f"({deviation_units:.2f} units of the last digit)"
        )


# --- ISO 53 -------------------------------------------------------------------------------------


@pytest.mark.eq("ISO53:1998", "Table A.1")
@pytest.mark.parametrize(
    "kind, clearance, dedendum, fillet",
    [
        ("A", 0.25, 1.25, 0.38),
        ("B", 0.25, 1.25, 0.3),
        ("C", 0.25, 1.25, 0.25),
        ("D", 0.4, 1.4, 0.39),
    ],
)
def test_iso53_basic_rack_types(
    kind: str, clearance: float, dedendum: float, fillet: float
) -> None:
    profile = rack.iso53_basic_rack(kind)  # type: ignore[arg-type]
    assert profile.profile_angle_deg == 20.0 and profile.addendum_factor == 1.0
    assert profile.dedendum_factor == dedendum and profile.fillet_radius_factor == fillet
    assert profile.bottom_clearance_factor == clearance, "the printed value, not h_fP* - h_aP*"
    assert profile.source == "ISO53:1998"
    assert BasicRackProfile.model_validate_json(profile.model_dump_json()) == profile


@pytest.mark.eq("ISO53:1998", "Table 2")
def test_iso53_standard_basic_rack_is_type_a() -> None:
    assert rack.iso53_basic_rack() == rack.iso53_basic_rack("A")
    for bad in ("E", "a", "", None, 1, ["A"]):
        with pytest.raises(InputRangeError, match="A, B, C, D"):
            rack.iso53_basic_rack(bad)  # type: ignore[arg-type]


# --- fillet radius bounds -----------------------------------------------------------------------


@pytest.mark.eq("DIN867:1986", "(7)")
@pytest.mark.eq("DIN867:1986", "(8)")
@pytest.mark.eq("ISO53:1998", "(2)")
@pytest.mark.eq("ISO53:1998", "(3)")
@pytest.mark.parametrize("clearance, printed, eq7, eq8", DIN867_TABLE)
def test_max_fillet_radius_against_din867(
    clearance: float, printed: str, eq7: float, eq8: float
) -> None:
    """The smaller of Eq. (7) and Eq. (8) governs; the table of DIN 867 p. 3 prints two decimals."""
    value = rack.max_fillet_radius_factor(
        bottom_clearance_factor=clearance, dedendum_factor=1.0 + clearance, profile_angle_rad=ALPHA
    )
    assert value == pytest.approx(min(eq7, eq8), rel=4 * ULP)
    deviation_units = abs(value - float(printed)) / printed_unit(printed)
    if clearance in DIN867_TABLE_DEVIATIONS:
        assert 0.5 < deviation_units < 1.0, "DIN 867 prints 0,25 where Eq. (7) gives 0,2584"
    else:
        assert deviation_units <= 0.5


@pytest.mark.eq("DIN867:1986", "(7)")
@pytest.mark.eq("DIN867:1986", "(8)")
def test_bound_switches_at_the_clearance_stated_in_the_norms() -> None:
    """DIN 867 §4.5 / ISO 53 5.9: Eq. (7) governs up to c_P = 0,295 m, then Eq. (8).

    Decimal reference of the switch point: c_P* = 0.29508701278980576.
    """
    switch = 0.29508701278980576

    def bound(clearance: float) -> float:
        return rack.max_fillet_radius_factor(
            bottom_clearance_factor=clearance,
            dedendum_factor=1.0 + clearance,
            profile_angle_rad=ALPHA,
        )

    assert bound(0.29) == pytest.approx(0.44074297572841384, rel=4 * ULP)  # Eq. (7)
    assert bound(0.3) == pytest.approx(0.44592044760002478, rel=4 * ULP)  # Eq. (8)
    assert bound(switch) == pytest.approx(switch / (1.0 - 0.34202014332566873), rel=8 * ULP)
    assert bound(switch - 1e-6) < bound(switch) > bound(switch + 1e-6), "maximum at the switch"
    assert f"{switch:.3f}" == "0.295"


@given(st.floats(0.0, 1.0), st.floats(math.radians(10.0), math.radians(30.0)))
def test_din867_eq_8_equals_iso53_eq_3_for_standard_dedendum(
    clearance: float, alpha: float
) -> None:
    """gearcore evaluates the form of ISO 53 (3); DIN 867 (8) is the independent reference."""
    eq7 = clearance / (1.0 - math.sin(alpha))
    eq8 = (
        (1.0 + math.sin(alpha))
        / math.cos(alpha)
        * ((math.pi / 4.0 - math.tan(alpha)) - clearance * math.tan(alpha))
    )
    if eq8 <= 1e-9:
        with pytest.raises(GeometryInfeasibleError, match="flanks intersect"):
            rack.max_fillet_radius_factor(
                bottom_clearance_factor=clearance,
                dedendum_factor=1.0 + clearance,
                profile_angle_rad=alpha,
            )
        return
    value = rack.max_fillet_radius_factor(
        bottom_clearance_factor=clearance, dedendum_factor=1.0 + clearance, profile_angle_rad=alpha
    )
    assert value == pytest.approx(min(eq7, eq8), rel=1e-13, abs=1e-15)


@pytest.mark.eq("DIN867:1986", "(9)")
def test_root_form_height() -> None:
    """ISO 53 5.9 states h_FfP = 1 m for the fillet radius of Eq. (2); 0,38 is its rounded value."""
    exact = rack.max_fillet_radius_factor(
        bottom_clearance_factor=0.25, dedendum_factor=1.25, profile_angle_rad=ALPHA
    )
    at_the_bound = rack.root_form_height_factor(
        dedendum_factor=1.25, fillet_radius_factor=exact, profile_angle_rad=ALPHA
    )
    assert at_the_bound == pytest.approx(1.0, rel=2 * ULP)
    printed = rack.root_form_height_factor(
        dedendum_factor=1.25, fillet_radius_factor=0.38, profile_angle_rad=ALPHA
    )
    assert printed == pytest.approx(0.99996765446375412, rel=4 * ULP)  # decimal reference


@pytest.mark.eq("DIN867:1986", "(4)")
@pytest.mark.eq("DIN867:1986", "(5)")
def test_din867_basic_rack() -> None:
    profile = rack.din867_basic_rack(bottom_clearance_factor=0.25, fillet_radius_factor=0.3)
    assert profile.dedendum_factor == 1.25 and profile.addendum_factor == 1.0
    assert profile.profile_angle_deg == 20.0 and profile.source == "DIN867:1986"
    assert rack.check_basic_rack(profile) == ()
    with pytest.raises(GeometryInfeasibleError, match="exceeds the maximum"):
        rack.din867_basic_rack(bottom_clearance_factor=0.25, fillet_radius_factor=0.4)


@pytest.mark.eq("DIN867:1986", "4.4")
def test_clearance_outside_the_usual_range_is_a_soft_finding() -> None:
    """DIN 867 §4.4: the clearance is 'im allgemeinen' 0,1 m to 0,4 m; Bild 2 runs to 0,5."""
    for clearance in (0.1, 0.3 - 0.2, 0.25, 0.4, 0.1 + 0.3):
        profile = rack.din867_basic_rack(
            bottom_clearance_factor=clearance, fillet_radius_factor=0.1
        )
        assert rack.check_basic_rack(profile) == (), clearance
    for clearance in (0.05, 0.09, 0.41, 0.5):
        profile = rack.din867_basic_rack(
            bottom_clearance_factor=clearance, fillet_radius_factor=0.05
        )
        (finding,) = rack.check_basic_rack(profile)
        assert finding.code == "clearance_outside_usual_range"
        assert finding.field == "bottom_clearance_factor" and repr(clearance) in finding.message


def test_fillet_bound_has_no_slack_except_for_values_printed_by_the_norms() -> None:
    bound = 0.37995084114518434  # decimal reference, c_P* = 0.25
    rack.din867_basic_rack(bottom_clearance_factor=0.25, fillet_radius_factor=bound)
    for fillet in (0.3800001, 0.3801, 0.3849, 0.37996):
        with pytest.raises(GeometryInfeasibleError, match="exceeds the maximum"):
            rack.din867_basic_rack(bottom_clearance_factor=0.25, fillet_radius_factor=fillet)
    for clearance, fillet in rack.NORM_PRINTED_FILLETS:
        profile = rack.din867_basic_rack(
            bottom_clearance_factor=clearance, fillet_radius_factor=fillet
        )
        codes = [finding.code for finding in rack.check_basic_rack(profile)]
        assert codes == ["fillet_radius_rounded_by_norm"]
    with pytest.raises(GeometryInfeasibleError):  # the printed pair is tied to alpha_P = 20 deg
        rack.validate_basic_rack(
            BasicRackProfile(
                name="x",
                source="DIN867:1986",
                profile_angle_deg=19.5,  # bound 0.3753
                addendum_factor=1.0,
                dedendum_factor=1.25,
                bottom_clearance_factor=0.25,
                fillet_radius_factor=0.38,
            )
        )


def test_basic_rack_contract_checks_the_clearance_relation() -> None:
    with pytest.raises(ValidationError, match="must equal"):
        BasicRackProfile(
            name="x",
            source="DIN867:1986",
            profile_angle_deg=20.0,
            addendum_factor=1.0,
            dedendum_factor=1.25,
            bottom_clearance_factor=0.2,
            fillet_radius_factor=0.3,
        )


def test_rack_flanks_must_not_intersect_above_the_root_line() -> None:
    with pytest.raises(GeometryInfeasibleError, match="flanks intersect"):
        rack.max_fillet_radius_factor(
            bottom_clearance_factor=1.2, dedendum_factor=2.2, profile_angle_rad=ALPHA
        )


@pytest.mark.eq("ISO21771:2014", "Bild 35")
@pytest.mark.eq("DIN867:1986", "Anmerkung")
def test_tool_is_the_counterpart_of_the_basic_rack() -> None:
    profile = rack.iso53_basic_rack("D")
    tool = rack.tool_from_basic_rack(profile)
    assert tool.addendum_factor == profile.dedendum_factor == 1.4
    assert tool.tip_radius_factor == profile.fillet_radius_factor == 0.39
    assert tool.profile_angle_deg == 20.0
    assert tool.dedendum_factor is None and tool.machining_allowance_mm == 0.0


# --- DIN 3972 -----------------------------------------------------------------------------------


@pytest.mark.eq("DIN867:1986", "(2)")
@pytest.mark.eq("ISO53:1998", "5.2")
@pytest.mark.parametrize("row", DIN3972_TABLE, ids=lambda r: f"m={r[0]}")
def test_rack_pitch_against_the_printed_pitches(
    row: tuple[str, str, str, str, str | None, str | None, str, str, str],
) -> None:
    """DIN 3972 prints t_0 = m·pi with four decimals for 28 modules."""
    m_text, pitch = row[0], row[1]
    assert abs(rack.rack_pitch(float(m_text)) - float(pitch)) <= 0.5 * printed_unit(pitch) + 1e-12


@pytest.mark.eq("DIN3972:1952", "Tabelle")
@pytest.mark.eq("DIN3972:1952", "Erläuterungen")
@pytest.mark.parametrize("row", DIN3972_TABLE, ids=lambda r: f"m={r[0]}")
def test_din3972_formulas_reproduce_the_table(
    row: tuple[str, str, str, str, str | None, str | None, str, str, str],
) -> None:
    m_text, _, h1, h2, h3, p3, h4, p4, r2 = row
    m = float(m_text)
    assert_cell(m_text, "h_kw I", h1, rack.din3972_tool_addendum_mm("I", m))
    assert_cell(m_text, "h_kw II", h2, rack.din3972_tool_addendum_mm("II", m))
    assert_cell(m_text, "h_kw IV", h4, rack.din3972_tool_addendum_mm("IV", m))
    assert_cell(m_text, "p IV", p4, rack.din3972_machining_allowance_mm("IV", m))
    if h3 is None or p3 is None:
        with pytest.raises(InputRangeError, match="up to module 8"):
            rack.din3972_tool_addendum_mm("III", m)
    else:
        assert_cell(m_text, "h_kw III", h3, rack.din3972_tool_addendum_mm("III", m))
        assert_cell(m_text, "p III", p3, rack.din3972_machining_allowance_mm("III", m))
    assert rack.DIN3972_TIP_ROUNDING_MM[m] == float(r2)


def test_din3972_table_is_complete() -> None:
    assert sorted(rack.DIN3972_TIP_ROUNDING_MM) == [float(r[0]) for r in DIN3972_TABLE]
    modules = {row[0] for row in DIN3972_TABLE}
    columns = {"h_kw I", "h_kw II", "h_kw III", "p III", "h_kw IV", "p IV"}
    for m_text, column in DIN3972_TABLE_DEVIATIONS:
        assert m_text in modules and column in columns, f"deviation for an unknown cell {column}"
    assert sum(6 if row[4] is not None else 4 for row in DIN3972_TABLE) == 152
    assert len(DIN3972_TABLE_DEVIATIONS) == 6


@pytest.mark.eq("DIN3972:1952", "Erläuterungen")
def test_din3972_worked_example_and_decimal_references() -> None:
    """DIN 3972 p. 2, example 'Bezugsprofile III, m = 8': p = 0,17."""
    assert f"{rack.din3972_machining_allowance_mm('III', 8.0):.2f}" == "0.17"
    assert rack.din3972_machining_allowance_mm("III", 8.0) == pytest.approx(
        0.17101007166283437, rel=4 * ULP
    )
    assert rack.din3972_machining_allowance_mm("IV", 4.5) == pytest.approx(
        0.33879768927536138, rel=8 * ULP
    )
    assert rack.din3972_tool_addendum_mm("IV", 4.5) == pytest.approx(6.615578174668388, rel=2 * ULP)
    assert rack.din3972_tool_addendum_mm("IV", 5.0) == pytest.approx(7.275985568006018, rel=2 * ULP)
    for finishing in ("I", "II"):
        assert rack.din3972_machining_allowance_mm(finishing, 8.0) == 0.0


@pytest.mark.eq("DIN3972:1952", "Tabelle")
def test_din3972_tool_uses_the_tabulated_rounding_not_a_formula() -> None:
    tool = rack.din3972_tool("II", 1.0)
    assert tool.addendum_factor == 1.25
    assert tool.tip_radius_factor == 0.08  # r1 = r2 = 0,08 mm at m = 1, not 0.2·m
    assert tool.machining_allowance_mm == 0.0
    rough = rack.din3972_tool("IV", 5.0)
    assert rough.tip_radius_factor == 0.2 and rough.normal_module_mm == 5.0
    assert rough.machining_allowance_mm == pytest.approx(0.35090773101948599, rel=4 * ULP)
    with pytest.raises(InputRangeError, match="no tabulated tip rounding"):
        rack.din3972_tool("I", 0.5)
    for bad in ("V", "i", "", None, 1):
        with pytest.raises(InputRangeError, match="I, II, III or IV"):
            rack.din3972_tool_addendum_mm(bad, 2.0)  # type: ignore[arg-type]


# --- ISO 54 -------------------------------------------------------------------------------------


@pytest.mark.eq("ISO54:1996", "Table 1")
@pytest.mark.eq("ISO54:1996", "3")
def test_module_series_of_iso54() -> None:
    assert rack.module_series(2.5) == "I" and rack.module_series(4.5) == "II"
    assert rack.module_series(0.5) is None and rack.module_series(2.4) is None
    assert len(rack.ISO54_SERIES_I) == 18 and len(rack.ISO54_SERIES_II) == 18
    assert not set(rack.ISO54_SERIES_I) & set(rack.ISO54_SERIES_II)
    assert min(rack.ISO54_SERIES_I) == 1.0 and max(rack.ISO54_SERIES_I) == 50.0
    assert rack.check_module(8.0) is None
    second = rack.check_module(6.5)
    assert second is not None and second.code == "module_series_ii" and "avoided" in second.message
    other = rack.check_module(7.0)
    assert other is not None and other.code == "module_series_ii"
    assert "avoided" not in other.message
    outside = rack.check_module(0.5)
    assert outside is not None and outside.code == "module_not_in_iso54"


# --- properties of the guards -------------------------------------------------------------------

anything = st.one_of(
    st.floats(allow_nan=True, allow_infinity=True),
    st.integers(-(10**400), 10**400),
    st.booleans(),
    st.none(),
    st.text(max_size=3),
)


@given(anything, anything, anything)
def test_rack_functions_return_finite_numbers_or_typed_errors(
    a: object, b: object, c: object
) -> None:
    calls: tuple[Callable[[], float], ...] = (
        lambda: rack.rack_pitch(a),  # type: ignore[arg-type]
        lambda: rack.max_fillet_radius_factor(
            bottom_clearance_factor=a,  # type: ignore[arg-type]
            dedendum_factor=b,  # type: ignore[arg-type]
            profile_angle_rad=c,  # type: ignore[arg-type]
        ),
        lambda: rack.root_form_height_factor(
            dedendum_factor=a,  # type: ignore[arg-type]
            fillet_radius_factor=b,  # type: ignore[arg-type]
            profile_angle_rad=c,  # type: ignore[arg-type]
        ),
        lambda: rack.din3972_tool_addendum_mm("IV", a),  # type: ignore[arg-type]
        lambda: rack.din3972_machining_allowance_mm("III", a, b),  # type: ignore[arg-type]
        lambda: rack.din3972_machining_allowance_mm("I", a, b),  # type: ignore[arg-type]
    )
    for call in calls:
        try:
            value = call()
        except GearCoreError:
            continue
        assert isinstance(value, float) and math.isfinite(value) and value >= 0.0


@given(anything, anything)
def test_rack_constructors_return_valid_racks_or_typed_errors(a: object, b: object) -> None:
    try:
        profile = rack.din867_basic_rack(bottom_clearance_factor=a, fillet_radius_factor=b)  # type: ignore[arg-type]
    except GearCoreError:
        return
    assert 0.0 < profile.bottom_clearance_factor <= 1.0
    limit = rack.max_fillet_radius_factor(
        bottom_clearance_factor=profile.bottom_clearance_factor,
        dedendum_factor=profile.dedendum_factor,
        profile_angle_rad=ALPHA,
    )
    printed = (
        profile.bottom_clearance_factor,
        profile.fillet_radius_factor,
    ) in rack.NORM_PRINTED_FILLETS
    assert profile.fillet_radius_factor <= limit + 1e-12 or printed


@given(anything)
def test_module_checks_return_findings_or_typed_errors(a: object) -> None:
    for call in (rack.module_series, rack.check_module):
        try:
            call(a)  # type: ignore[arg-type]
        except GearCoreError:
            continue
        assert isinstance(a, int | float) and not isinstance(a, bool) and a > 0
