"""Regression tests for the adversarial gate of increment 1 (findings ADV1-xx, 2026-09-29).

Findings covered elsewhere: ADV1-12 and ADV1-16/-22/-23/-30 in ``test_rack.py``, ADV1-15/-17/-18/
-20/-34/-45 in ``test_stplus_parity.py``, ADV1-21 in ``test_numeric_precision.py``, ADV1-27 in
``test_notebooks_are_documentation.py``, ADV1-29/-32 in the tightened tolerances and the
properties of ``test_involute.py`` and ``test_properties_involute.py``.
"""

import math
from decimal import Decimal, getcontext

import numpy as np
import pytest
from pydantic import ValidationError

from gearcore import involute as iv
from gearcore import rack
from gearcore._safe import finite_input, finite_result, integer_input, positive_input
from gearcore.data import (
    load_stplus,
    load_worked_example,
    printed_tolerance,
    stplus_input_path,
)
from gearcore.errors import (
    GeometryInfeasibleError,
    InputRangeError,
    NotSupportedError,
    ParseError,
)
from gearcore.io.ste import pair_input_from_ste, parse_ste
from gearcore.models.common import FrozenModel
from gearcore.models.profiles import BasicRackProfile
from gearcore.models.results import BasicGearGeometry
from gearcore.parity import ParityRow
from gearcore.quantities import quantity
from gearcore.trace import equations_of, load_sources

ALPHA = math.radians(20.0)
ULP = math.ulp(1.0)
HUGE_INTEGERS = (10**400, -(10**400), 10**309)
NOT_NUMBERS = ("20", None, True, False, [1.0], 1 + 2j, math.nan, math.inf, -math.inf)


def basic(**overrides: object) -> BasicGearGeometry:
    arguments: dict[str, object] = {
        "number_of_teeth": 17,
        "normal_module_mm": 8.0,
        "normal_pressure_angle_deg": 20.0,
        "helix_angle_deg": 15.8,
        "profile_shift_coefficient": 0.14522,
    }
    arguments.update(overrides)
    return iv.compute_basic_gear_geometry(**arguments)  # type: ignore[arg-type]


# --- ADV1-01: signed thickness at the reference cylinder -----------------------------------------


def test_adv1_01_reference_cylinder_outside_the_teeth_is_reported_not_hidden() -> None:
    """z = 100, alpha_n = 30°, x = -1,5 is a feasible gear (tip thickness 0,4 m, root circle above
    the base circle) whose reference cylinder lies above the tip: s_n < 0 is the value of Eq. (49)
    and carries a warning; rejecting the gear would be wrong."""
    result = basic(number_of_teeth=100, normal_module_mm=1.0, normal_pressure_angle_deg=30.0, helix_angle_deg=0.0,
                   profile_shift_coefficient=-1.5)  # fmt: skip
    assert result.normal_tooth_thickness_mm < 0.0 and result.tooth_thickness_half_angle_deg < 0.0
    assert [w.code for w in result.warnings] == ["no_tooth_at_reference_cylinder"]
    assert result.warnings[0].field == "profile_shift_coefficient"

    alpha_n = math.radians(30.0)
    psi = iv.tooth_thickness_half_angle(100, -1.5, alpha_n)
    eta = iv.space_width_half_angle(100, -1.5, alpha_n)
    d_b = result.base_diameter_mm
    tip, root = 100.0 + 2.0 * (1.0 - 1.5), 100.0 - 2.0 * (1.25 + 1.5)  # d_a, d_f for h_aP* = 1
    assert d_b < root < tip < result.reference_diameter_mm
    for diameter, thickness in ((tip, 0.40), (root, 2.57)):
        alpha_yt = iv.transverse_profile_angle_at(diameter, d_b)
        psi_y = iv.tooth_thickness_half_angle_at(psi, alpha_n, alpha_yt)
        eta_y = iv.space_width_half_angle_at(eta, alpha_n, alpha_yt)
        assert iv.transverse_tooth_thickness_at(diameter, psi_y) == pytest.approx(
            thickness, abs=5e-3
        )
        assert eta_y > 0.0, "teeth and spaces exist over the whole tooth depth"

    wide = basic(number_of_teeth=100, normal_module_mm=1.0, normal_pressure_angle_deg=30.0, helix_angle_deg=0.0,
                 profile_shift_coefficient=2.0)  # fmt: skip
    assert wide.normal_space_width_mm < 0.0
    assert [w.code for w in wide.warnings] == ["no_space_at_reference_cylinder"]
    assert basic().warnings == ()


def test_adv1_01_limit_of_the_profile_shift_for_a_positive_reference_thickness() -> None:
    limit = math.pi / (4.0 * math.tan(math.radians(25.0)))  # 1.684
    inside = basic(normal_pressure_angle_deg=25.0, profile_shift_coefficient=-limit + 1e-9)
    outside = basic(normal_pressure_angle_deg=25.0, profile_shift_coefficient=-limit - 1e-9)
    assert inside.normal_tooth_thickness_mm > 0.0 and inside.warnings == ()
    assert outside.normal_tooth_thickness_mm < 0.0 and len(outside.warnings) == 1
    assert 1.68 < limit < 1.69 < 2.0, "inside the verified range of x for alpha_n > 21.4 deg"


# --- ADV1-02, -03, -43: numbers outside the representable range ------------------------------------


@pytest.mark.parametrize("huge", HUGE_INTEGERS)
def test_adv1_02_huge_integers_are_input_errors(huge: int) -> None:
    calls = (
        lambda: iv.transverse_module(huge, 0.0),
        lambda: rack.rack_pitch(huge),
        lambda: iv.inv_inverse(huge),
        lambda: iv.reference_diameter(huge, 1.0, 0.0),
        lambda: iv.tooth_thickness_half_angle(huge, 0.0, ALPHA),
        lambda: rack.check_module(huge),
        lambda: basic(number_of_teeth=huge),
        lambda: basic(normal_module_mm=huge),
    )
    for call in calls:
        with pytest.raises((InputRangeError, NotSupportedError)):
            call()


def test_adv1_03_overflow_is_an_input_error_not_inf() -> None:
    calls = (
        lambda: iv.reference_diameter(2**53, 1e300, 0.0),
        lambda: iv.transverse_module(1e308, math.radians(89.99)),
        lambda: rack.rack_pitch(1e308),
        lambda: iv.normal_tooth_thickness(1.0, 1e308, ALPHA),
        lambda: iv.normal_space_width(1.0, -1e308, ALPHA),
        lambda: iv.transverse_tooth_thickness(1e308, 2.0, ALPHA, 0.0),
        lambda: iv.transverse_tooth_thickness_at(1e308, 1e10),
        lambda: iv.transverse_space_width_at(1e308, -1e10),
        lambda: iv.tooth_thickness_half_angle(17, 1e308, ALPHA),
        lambda: iv.space_width_half_angle(17, 1e308, ALPHA),
        lambda: iv.helix_angle_at(1e308, 1e-308, 0.5),
        lambda: iv.radius_of_curvature(1e308, 1.0),
        lambda: rack.din3972_tool_addendum_mm("IV", 1.5e308),
    )
    for index, call in enumerate(calls):
        with pytest.raises(InputRangeError):
            pytest.fail(f"call {index} returned {call()!r}")


def test_adv1_43_input_helpers() -> None:
    assert finite_input(3, "x") == 3.0 and isinstance(finite_input(3, "x"), float)
    assert finite_input(np.float64(1.5), "x") == 1.5 and finite_input(np.int64(2), "x") == 2.0
    assert finite_input(np.float32(0.1), "x") == float(np.float32(0.1)), "exact conversion"
    assert finite_input(-0.0, "x") == 0.0
    for bad in NOT_NUMBERS:
        with pytest.raises(InputRangeError, match="x must be"):
            finite_input(bad, "x")  # type: ignore[arg-type]
    with pytest.raises(InputRangeError, match="exceeds the range"):
        finite_input(10**400, "x")
    assert positive_input(1e-300, "m") == 1e-300
    for bad in (0.0, -0.0, -1.0, 0):
        with pytest.raises(InputRangeError, match="m must be > 0"):
            positive_input(bad, "m")
    assert integer_input(17, "z") == 17 and integer_input(np.int64(17), "z") == 17
    assert isinstance(integer_input(np.int64(17), "z"), int)
    for bad in (17.0, 17.5, True, "17", None, np.float64(17.0)):
        with pytest.raises(InputRangeError, match="z must be an integer"):
            integer_input(bad, "z")  # type: ignore[arg-type]
    with pytest.raises(InputRangeError, match="2\\^53"):
        integer_input(2**53 + 1, "z")
    assert finite_result(1.0, "y") == 1.0
    for bad in (math.inf, -math.inf, math.nan):
        with pytest.raises(InputRangeError, match="y: the result is not a finite number"):
            finite_result(bad, "y")


def test_adv1_42_numpy_integers_are_numbers_of_teeth() -> None:
    assert iv.reference_diameter(np.int64(17), 2.0, 0.0) == 34.0
    assert basic(number_of_teeth=np.int32(17)) == basic()
    with pytest.raises(NotSupportedError, match="internal"):
        iv.reference_diameter(np.int64(-17), 2.0, 0.0)


# --- ADV1-04, -06, -07, -24: guards of the rack functions -------------------------------------------


def test_adv1_04_root_form_height_guards() -> None:
    for bad in NOT_NUMBERS:
        with pytest.raises(InputRangeError):
            rack.root_form_height_factor(
                dedendum_factor=bad,  # type: ignore[arg-type]
                fillet_radius_factor=0.38,
                profile_angle_rad=ALPHA,
            )
        with pytest.raises(InputRangeError):
            rack.root_form_height_factor(
                dedendum_factor=1.25,
                fillet_radius_factor=bad,  # type: ignore[arg-type]
                profile_angle_rad=ALPHA,
            )
    with pytest.raises(InputRangeError, match=">= 0"):
        rack.root_form_height_factor(
            dedendum_factor=1.25, fillet_radius_factor=-0.1, profile_angle_rad=ALPHA
        )
    with pytest.raises(InputRangeError, match="> 0"):
        rack.root_form_height_factor(
            dedendum_factor=0.0, fillet_radius_factor=0.1, profile_angle_rad=ALPHA
        )
    with pytest.raises(GeometryInfeasibleError, match="reaches the datum line"):
        rack.root_form_height_factor(
            dedendum_factor=1.25, fillet_radius_factor=5.0, profile_angle_rad=ALPHA
        )


def test_adv1_06_din867_rack_guards() -> None:
    for bad in (*NOT_NUMBERS, -0.1, 1.5):
        with pytest.raises(InputRangeError, match="fillet radius factor"):
            rack.din867_basic_rack(bottom_clearance_factor=0.25, fillet_radius_factor=bad)  # type: ignore[arg-type]
    for bad in (*NOT_NUMBERS, 0.0, -0.1, 1.5):
        with pytest.raises(InputRangeError, match="clearance factor"):
            rack.din867_basic_rack(bottom_clearance_factor=bad, fillet_radius_factor=0.1)  # type: ignore[arg-type]
    profile = rack.din867_basic_rack(
        bottom_clearance_factor=0.30000000000000004, fillet_radius_factor=0.1
    )
    assert "0.30000000000000004" in profile.name, "the name shows the value, not six digits of it"


def test_adv1_07_max_fillet_radius_guards() -> None:
    with pytest.raises(InputRangeError, match="c_P\\* must be >= 0"):
        rack.max_fillet_radius_factor(
            bottom_clearance_factor=-0.1, dedendum_factor=0.9, profile_angle_rad=ALPHA
        )
    for dedendum in (0.0, -1.0):
        with pytest.raises(InputRangeError, match="h_fP\\* must be > 0"):
            rack.max_fillet_radius_factor(
                bottom_clearance_factor=0.25, dedendum_factor=dedendum, profile_angle_rad=ALPHA
            )
    for angle in (0.0, -ALPHA, math.pi / 2.0, 2.0, math.nan):
        with pytest.raises(InputRangeError, match="profile angle"):
            rack.max_fillet_radius_factor(
                bottom_clearance_factor=0.25, dedendum_factor=1.25, profile_angle_rad=angle
            )
    assert (
        rack.max_fillet_radius_factor(
            bottom_clearance_factor=0.0, dedendum_factor=1.0, profile_angle_rad=ALPHA
        )
        == 0.0
    )


def test_adv1_24_machining_allowance_checks_the_angle_for_every_profile() -> None:
    for profile in ("I", "II", "III", "IV"):
        for bad in (math.nan, None, True, -ALPHA, 0.0, 2.0):
            with pytest.raises(InputRangeError, match="profile angle"):
                rack.din3972_machining_allowance_mm(profile, 2.0, bad)  # type: ignore[arg-type]
        for bad in (0.0, -2.0, math.nan, "2"):
            with pytest.raises(InputRangeError, match="module"):
                rack.din3972_machining_allowance_mm(profile, bad)  # type: ignore[arg-type]


# --- ADV1-05, -26: orchestrator -------------------------------------------------------------------


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"normal_pressure_angle_deg": "20"}, "pressure angle"),
        ({"normal_pressure_angle_deg": None}, "pressure angle"),
        ({"normal_pressure_angle_deg": True}, "pressure angle"),
        ({"normal_pressure_angle_deg": 0.0}, "pressure angle"),
        ({"normal_pressure_angle_deg": 9.999}, "pressure angle"),
        ({"normal_pressure_angle_deg": 30.001}, "pressure angle"),
        ({"normal_pressure_angle_deg": 89.9}, "pressure angle"),
        ({"helix_angle_deg": 45.001}, "helix angle"),
        ({"helix_angle_deg": -89.0}, "helix angle"),
        ({"helix_angle_deg": "0"}, "helix angle"),
        ({"normal_module_mm": 1e308}, "normal module"),
        ({"normal_module_mm": 0.0499}, "normal module"),
        ({"normal_module_mm": 100.1}, "normal module"),
        ({"normal_module_mm": -1.0}, "normal module"),
        ({"profile_shift_coefficient": 2.0000001}, "profile shift"),
        ({"profile_shift_coefficient": -2.0000001}, "profile shift"),
        ({"profile_shift_coefficient": math.nan}, "profile shift"),
        ({"number_of_teeth": 1}, "number of teeth"),
        ({"number_of_teeth": 4}, "number of teeth"),
        ({"number_of_teeth": 1001}, "number of teeth"),
        ({"number_of_teeth": 17.0}, "number of teeth"),
        ({"number_of_teeth": True}, "number of teeth"),
        ({"number_of_teeth": "17"}, "number of teeth"),
        ({"number_of_teeth": 0}, "number of teeth"),
    ],
)
def test_adv1_05_26_orchestrator_rejects_inputs_outside_the_verified_ranges(
    overrides: dict[str, object], message: str
) -> None:
    with pytest.raises(InputRangeError, match=message):
        basic(**overrides)


def test_adv1_26_limits_of_the_verified_ranges_are_accepted() -> None:
    for overrides in (
        {"number_of_teeth": 5},
        {"number_of_teeth": 1000},
        {"normal_module_mm": 0.05},
        {"normal_module_mm": 100.0},
        {"normal_pressure_angle_deg": 10.0},
        {"normal_pressure_angle_deg": 30.0},
        {"helix_angle_deg": 45.0},
        {"helix_angle_deg": -45.0},
        {"profile_shift_coefficient": 2.0},
        {"profile_shift_coefficient": -2.0},
    ):
        result = basic(**overrides)
        assert result.base_diameter_mm < result.reference_diameter_mm
    with pytest.raises(NotSupportedError, match="internal"):
        basic(number_of_teeth=-17)


def test_adv1_26_result_contract_is_bounded_like_the_inputs() -> None:
    valid = basic().model_dump()
    for field, value in (
        ("number_of_teeth", True),
        ("number_of_teeth", "17"),
        ("number_of_teeth", 17.0),
        ("number_of_teeth", 1001),
        ("normal_pressure_angle_deg", 0.0),
        ("helix_angle_deg", 89.0),
        ("normal_module_mm", 1e308),
        ("base_diameter_mm", -1.0),
        ("transverse_pressure_angle_deg", 90.0),
    ):
        with pytest.raises(ValidationError):
            BasicGearGeometry(**{**valid, field: value})


# --- ADV1-08, -09, -10, -33, -36, -41: tables and citations ----------------------------------------


def test_adv1_08_tabulated_modules_tolerate_float_noise() -> None:
    noisy = 0.07 * 100  # 7.000000000000001
    assert noisy != 7.0 and rack.module_series(noisy) == "II"
    finding = rack.check_module(noisy)
    assert finding is not None and finding.code == "module_series_ii"
    tool = rack.din3972_tool("I", noisy)
    assert tool.normal_module_mm == 7.0 and tool.tip_radius_factor == 1.4 / 7.0
    assert rack.module_series(11 * 0.25) == "II" and rack.module_series(0.1 + 0.2 + 0.7) == "I"
    assert rack.check_module(2.0000000001) is None, "5e-11 relative is float noise of module 2"
    off = rack.check_module(2.00001)
    assert off is not None and off.code == "module_not_in_iso54" and "2.00001" in off.message
    with pytest.raises(InputRangeError, match="module 2.00001 has no tabulated"):
        rack.din3972_tool("I", 2.00001)
    rack.din3972_tool_addendum_mm("III", 0.08 * 100)  # 8.000000000000002 is module 8


def test_adv1_09_module_checks_reject_non_positive_modules() -> None:
    for function in (rack.module_series, rack.check_module):
        for bad in (0.0, -2.0, -0.0, math.nan, math.inf, None, "2", True):
            with pytest.raises(InputRangeError, match="module m must be"):
                function(bad)  # type: ignore[arg-type]


def test_adv1_10_36_citations() -> None:
    references = {(r.eq, r.section, r.page) for r in equations_of(rack.check_module)}
    assert references == {("Table 1", "3", 2), ("3", "3", 1)}
    assert {(r.eq, r.page) for r in equations_of(rack.module_series)} == {("Table 1", 2)}
    iso53_eq3 = next(
        r
        for r in equations_of(rack.max_fillet_radius_factor)
        if (r.source, r.eq) == ("ISO53:1998", "(3)")
    )
    assert iso53_eq3.note is not None and "0,396" in iso53_eq3.note
    assert rack.iso53_basic_rack("D").bottom_clearance_factor > 0.396, (
        "type D needs DIN 867 Eq. (8)"
    )
    clearance = {(r.source, r.eq, r.page) for r in equations_of(rack.check_basic_rack)}
    assert ("DIN867:1986", "4.4", 2) in clearance


def test_adv1_33_norm_tables_are_immutable() -> None:
    for table, key in (
        (rack.DIN3972_TIP_ROUNDING_MM, 1.0),
        (rack.NORM_PRINTED_FILLETS, (0.25, 0.38)),
        (rack._ISO53_TYPES, "A"),
    ):
        with pytest.raises(TypeError):
            table[key] = 0.5  # type: ignore[index]
    assert rack.din3972_tool("I", 1.0).tip_radius_factor == 0.08
    for series in (rack.ISO54_SERIES_I, rack.ISO54_SERIES_II, rack.ISO54_AVOID):
        assert isinstance(series, tuple)


def test_adv1_41_names_show_the_tabulated_module() -> None:
    assert rack.din3972_tool("II", 0.07 * 100).name == "DIN 3972 Bezugsprofil II x 7.0"


# --- ADV1-11, -35: symbol map ---------------------------------------------------------------------


def test_adv1_11_35_registry_states_what_the_norm_pages_print() -> None:
    rounding = quantity("tool_tip_radius")
    # the equations and the normative Anhang NB of DIN ISO 21771 write rho_aP0, as DIN 867 does
    assert rounding.symbol == "rho_aP0" and rounding.source == "DIN867:1986"
    printed = {(p.symbol, p.source): p.location for p in rounding.also}
    assert "Anhang NB" in printed[("rho_aP0", "ISO21771:2014")]
    assert "Bild 35" in printed[("r_aP0", "ISO21771:2014")], "the figure letters r_aP0"
    assert ("rho_a0", "ISO6336-3:2019") in printed and ("rho_a0", "VDI2736-2:2014") in printed
    assert {p.symbol for p in rounding.replaced} == {"rho_a0", "r_1"}
    angle = quantity("tool_profile_angle")
    assert angle.description == "Profilwinkel des Bezugserzeugungsprofils"
    assert angle.location == "§3.1 symbol list, p. 15"


def test_feedback_stplus_and_older_symbols_are_translated_by_the_registry() -> None:
    """User rule of 2026-09-29: always the newest symbols, with the translation from STplus and
    from the replaced norms recorded with the quantity."""
    expected = {
        "normal_pressure_angle": ("alpha_n", "alfa_n"),
        "transverse_pressure_angle": ("alpha_t", "alfa_t"),
        "centre_distance": ("a_w", "a"),
        "tool_tip_radius": ("rho_aP0", "rho_aP0*"),
        "tool_addendum": ("h_aP0", "h_aP0*"),
        "reference_diameter": ("d", "d"),
    }
    for name, (symbol, stplus_symbol) in expected.items():
        entry = quantity(name)
        assert entry.symbol == symbol and entry.stplus is not None
        assert entry.stplus.symbol == stplus_symbol, name
    centre = quantity("centre_distance")
    assert [(p.symbol, p.source) for p in centre.replaced] == [("a", "DIN3960:1987")]
    old = {p.symbol for p in quantity("tool_addendum").replaced}
    assert old == {"h_aP0", "h_kw"}, "DIN 3960 and DIN 3972"
    assert {p.symbol for p in quantity("pitch").replaced} == {"p", "t_0"}


# --- ADV1-13, -25, -38: base circle and pointed tooth ----------------------------------------------


def test_adv1_13_one_tolerance_at_the_base_circle() -> None:
    d_b = 132.19856920126213
    for d_y in (d_b, math.nextafter(d_b, 0.0), d_b * (1.0 - 0.5e-12)):
        assert iv.transverse_profile_angle_at(d_y, d_b) == 0.0
        assert iv.radius_of_curvature(d_y, d_b) == 0.0
    for d_y in (d_b * (1.0 - 2e-12), d_b * (1.0 - 1e-9), 0.5 * d_b):
        with pytest.raises(GeometryInfeasibleError, match="below the base circle"):
            iv.transverse_profile_angle_at(d_y, d_b)
        with pytest.raises(GeometryInfeasibleError, match="below the base circle"):
            iv.radius_of_curvature(d_y, d_b)
    above = math.nextafter(d_b, math.inf)
    assert iv.transverse_profile_angle_at(above, d_b) > 0.0
    assert iv.radius_of_curvature(above, d_b) > 0.0


def test_adv1_38_radius_of_curvature_does_not_cancel_near_the_base_circle() -> None:
    getcontext().prec = 50
    d_b = 132.19856920126213
    for offset in (1e-10, 1e-8, 1e-6, 1e-3):
        d_y = d_b * (1.0 + offset)
        exact = (Decimal(d_y) ** 2 - Decimal(d_b) ** 2).sqrt() / 2
        assert iv.radius_of_curvature(d_y, d_b) == pytest.approx(float(exact), rel=4 * ULP)


def test_adv1_25_pointed_tooth_is_an_explicit_boundary() -> None:
    psi, alpha_t = 0.05, ALPHA
    pointed = iv.inv_inverse(psi + iv.inv(alpha_t))  # psi_y = 0
    assert iv.tooth_thickness_half_angle_at(psi, alpha_t, pointed) == pytest.approx(
        0.0, abs=4 * ULP
    )
    # within EPS beyond the pointed tooth the half angle is zero, never negative
    raw = psi + iv.inv(alpha_t)
    just_beyond = iv.inv_inverse(raw + 0.5e-12)
    assert iv.tooth_thickness_half_angle_at(psi, alpha_t, just_beyond) == 0.0
    beyond = iv.inv_inverse(raw + 1e-11)
    with pytest.raises(GeometryInfeasibleError, match="flanks intersect"):
        iv.tooth_thickness_half_angle_at(psi, alpha_t, beyond)
    with pytest.raises(InputRangeError, match="psi_y must be >= 0"):
        iv.transverse_tooth_thickness_at(100.0, -0.1)
    assert iv.transverse_tooth_thickness_at(100.0, 0.0) == 0.0
    assert iv.transverse_space_width_at(100.0, -0.1) == -10.0, "the space half angle is signed"


# --- ADV1-14, -34: parser and packaged data ---------------------------------------------------------


def test_adv1_14_number_tokens_beyond_the_float_range_are_parse_errors() -> None:
    text = stplus_input_path("undercut_z12_x0").read_text(encoding="latin-1")
    assert "ZAEHNEZAHL = 12 40" in text
    for token in ("1e400", "-1e400", "1D999"):
        broken = parse_ste(text.replace("ZAEHNEZAHL = 12 40", f"ZAEHNEZAHL = {token} 40"))
        with pytest.raises(ParseError, match="exceeds the number range"):
            pair_input_from_ste(broken)
    pair_input_from_ste(parse_ste(text))


def test_adv1_34_packaged_data_is_addressed_by_name_only() -> None:
    for case in ("nope", "fzg_c/../kst_e", "../stplus/kst_e", "", None, 3):
        with pytest.raises(InputRangeError, match="unknown STplus fixture case"):
            load_stplus(case)  # type: ignore[arg-type]
        with pytest.raises(InputRangeError, match="unknown STplus fixture case"):
            stplus_input_path(case)  # type: ignore[arg-type]
    with pytest.raises(InputRangeError, match="unknown STplus document"):
        load_stplus("kst_e", "../meta")
    with pytest.raises(InputRangeError, match="has no document 'interface'"):
        load_stplus("kst_e", "interface")
    for example in ("nope", "../symbol_map", "", None):
        with pytest.raises(InputRangeError, match="unknown worked example"):
            load_worked_example(example)  # type: ignore[arg-type]
    assert printed_tolerance(3) == 0.0005 and printed_tolerance(0) == 0.5
    for bad in (-1, 16, 2.0, True, "3"):
        with pytest.raises(InputRangeError):
            printed_tolerance(bad)  # type: ignore[arg-type]


# --- ADV1-31: metadata of the new contracts ----------------------------------------------------------


@pytest.mark.parametrize("model", [BasicGearGeometry, BasicRackProfile])
def test_adv1_31_new_contracts_carry_symbol_unit_and_a_registered_source(
    model: type[FrozenModel],
) -> None:
    """The metadata comes from the quantity registry; see also ``test_quantities.py``."""
    sources = load_sources()
    physical = 0
    for name, info in model.model_fields.items():
        extra = info.json_schema_extra
        if not isinstance(extra, dict):
            assert name in {"name", "source", "warnings"}, (
                f"{model.__name__}.{name} has no metadata"
            )
            continue
        physical += 1
        assert extra["symbol"] and extra["unit"] and extra["designation"]
        assert extra["source"] in sources and extra["status"] == "verified"
        if "equation" in extra:
            assert str(extra["equation"]).split(" ")[0] in sources
    assert physical >= 5
    schema = model.model_json_schema()
    assert all("description" in prop for prop in schema["properties"].values() if "symbol" in prop)


def test_adv1_31_parity_rows_name_their_unit() -> None:
    assert {"unit", "symbol", "field"} <= set(ParityRow.model_fields)
