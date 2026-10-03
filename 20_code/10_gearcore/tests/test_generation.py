"""DIN ISO 21771:2014-08 §4.6, §4.7, §7 and DIN 3960:1987-03 Anhang A.3.1 — tool-based generation.

References independent of the code under test: values computed with 45-digit decimal arithmetic
(formulas typed from the norm pages; generator ``scripts/decimal_reference_generation.py``), the
values printed in ISO/TR 6336-30:2022 Annex A example 1 (``test_worked_examples.py``), the STplus
fixtures (``test_stplus_parity.py``), and invariants.
"""

import math

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from gearcore import generation as gn
from gearcore import involute as iv
from gearcore import pair as pr
from gearcore import trochoid as tr
from gearcore.errors import GeometryInfeasibleError, InputRangeError, NotSupportedError
from gearcore.models.common import Pair
from gearcore.models.inputs import GearInput, GearKind, PairInput, ToolProfile
from gearcore.models.results import GearGeneration, GenerationResult
from gearcore.rack import din3972_tool, iso53_basic_rack, tool_from_basic_rack

SRC = "ISO21771:2014"
OLD = "DIN3960:1987"
CLOSE = 1.0e-12

# Decimal references. S: spur, z = 17, m_n = 8, x = 0,3, d_a = 158, tool 1,4 / 0,39, allowances
# -80 / -130 um. H: ISO/TR 6336-30 example 1 pinion (beta = 15,8, x_E = 0,117 79 as given).
# K: kst-C wheel (z = 36, m_n = 3, x_E = 0,221 05, d_a = 114,69, tool 1,25 / 0,33, edge break
# 45 deg from h_FfP0* = 0,6973). L: helical with an edge break (z = 25, m_n = 5, beta = 20).
CASES: dict[str, dict[str, object]] = {
    "S": {"z": 17, "m_n": 8.0, "alpha_n": 20.0, "beta": 0.0, "x": 0.3, "d_a": 158.0, "h": 1.4, "rho": 0.39,
          "E": (-80.0, -130.0)},
    "H": {"z": 17, "m_n": 8.0, "alpha_n": 20.0, "beta": 15.8, "x": 0.11779, "d_a": 159.66, "h": 1.4, "rho": 0.39,
          "E": (0.0, 0.0)},
    "K": {"z": 36, "m_n": 3.0, "alpha_n": 20.0, "beta": 0.0, "x": 0.22105, "d_a": 114.69, "h": 1.25, "rho": 0.33,
          "E": (0.0, 0.0), "h_FfP0": 0.6973, "alpha_kP": 45.0},
    "L": {"z": 25, "m_n": 5.0, "alpha_n": 20.0, "beta": 20.0, "x": 0.2184, "d_a": 145.522, "h": 1.25, "rho": 0.3,
          "E": (0.0, 0.0), "h_FfP0": 0.8, "alpha_kP": 45.0},
}  # fmt: skip
REFERENCE: dict[str, dict[str, float]] = {
    "S": {
        "x_Es": 0.28626261290272687,
        "x_Ei": 0.2776767459669312,
        "h_FaP0": 9.147102847176086,
        "d_fE": 118.18020180644363,
        "d_fEi": 118.0428279354709,
        "x_Emin": 0.14907673915266745,
        "d_Ff": 127.95923396532015,
        "d_Ff_printed_130": 127.95923396532015,
        "s_at": 3.3475971493447774,
        "s_an": 3.3475971493447774,
        "h": 19.909899096778187,
        "h_a": 11.0,
        "h_f": 8.909899096778185,
    },
    "H": {
        "x_Es": 0.11779,
        "x_Ei": 0.11779,
        "h_FaP0": 9.147102847176086,
        "d_fE": 120.82475306644808,
        "d_fEi": 120.82475306644808,
        "x_Emin": 0.03764821105895895,
        "d_Ff": 132.24824127231219,
        "d_Ff_printed_130": 132.2427120311143,
        "s_at": 5.130766484499637,
        "s_an": 4.8871635806267,
        "h": 19.417623466775957,
        "h_a": 9.159943466775958,
        "h_f": 10.25768,
    },
    "K": {
        "x_Es": 0.22105,
        "x_Ei": 0.22105,
        "h_FaP0": 3.098599941892412,
        "d_fE": 101.8263,
        "d_fEi": 101.8263,
        "x_Emin": -1.072733364631727,
        "d_Ff": 103.99378642005807,
        "d_Ff_printed_130": 103.99378642005807,
        "s_at": 2.4252736102191137,
        "s_an": 2.4252736102191137,
        "h": 6.43185,
        "h_a": 3.345,
        "h_f": 3.08685,
        "d_Fa": 113.86279923496024,
        "h_K": 0.413600382519885,
        "s_aK": 1.9308055530395543,
    },
    "L": {
        "x_Es": 0.2184,
        "x_Ei": 0.2184,
        "h_FaP0": 5.263030214988503,
        "d_fE": 122.70622155948902,
        "d_fEi": 122.70622155948902,
        "x_Emin": -0.6827055949155179,
        "d_Ff": 126.52668568501169,
        "d_Ff_printed_130": 126.49539784948162,
        "s_at": 3.4616620600398753,
        "s_an": 3.2160961832546477,
        "h": 11.407889220255491,
        "h_a": 6.249889220255491,
        "h_f": 5.158,
        "d_Fa": 144.04102894824587,
        "h_K": 0.7404855258770601,
        "s_aK": 2.5187212546095212,
    },
}


def _setup(name: str) -> dict[str, float]:
    c = CASES[name]
    alpha_n, beta = math.radians(c["alpha_n"]), math.radians(c["beta"])
    alpha_t = iv.transverse_pressure_angle(alpha_n, beta)
    d = iv.reference_diameter(c["z"], c["m_n"], beta)
    d_b = iv.base_diameter(c["z"], c["m_n"], alpha_n, beta)
    x_E = gn.generating_profile_shift_coefficient(c["x"], c["m_n"], alpha_n, c["E"][0])
    return {
        **c,
        "alpha_n": alpha_n,
        "beta": beta,
        "alpha_t": alpha_t,
        "d": d,
        "d_b": d_b,
        "x_E": x_E,
    }


def _close(value: float, reference: float) -> None:
    assert abs(value - reference) <= CLOSE * max(1.0, abs(reference)), (value, reference)


# --- single equations against the decimal reference ---------------------------------------------


@pytest.mark.eq(SRC, "(123)")
@pytest.mark.eq(SRC, "(124)")
@pytest.mark.parametrize("name", list(CASES))
def test_generating_profile_shift_coefficient(name: str) -> None:
    c, ref = CASES[name], REFERENCE[name]
    alpha_n = math.radians(c["alpha_n"])
    _close(
        gn.generating_profile_shift_coefficient(c["x"], c["m_n"], alpha_n, c["E"][0]), ref["x_Es"]
    )
    _close(
        gn.generating_profile_shift_coefficient(c["x"], c["m_n"], alpha_n, c["E"][1]), ref["x_Ei"]
    )


@pytest.mark.eq(SRC, "(118)")
@pytest.mark.eq(SRC, "(119)")
def test_tooth_thickness_limits() -> None:
    s_n = iv.normal_tooth_thickness(8.0, 0.3, math.radians(20.0))
    assert gn.tooth_thickness_limit(s_n, -80.0) == pytest.approx(s_n - 0.080, abs=1e-15)
    assert gn.tooth_thickness_limit(s_n, 0.0) == s_n
    # the limit equals the normal tooth thickness of Eq. (49) at x_E
    x_Es = gn.generating_profile_shift_coefficient(0.3, 8.0, math.radians(20.0), -80.0)
    assert gn.tooth_thickness_limit(s_n, -80.0) == pytest.approx(
        iv.normal_tooth_thickness(8.0, x_Es, math.radians(20.0)), abs=1e-12
    )


@pytest.mark.eq(SRC, "(120)")
@pytest.mark.eq(SRC, "(121)")
def test_pre_machining_generating_profile_shift_coefficient() -> None:
    alpha_n = math.radians(20.0)
    # DIN 3972 profile III leaves p = 0,25 m^(1/3) sin(alpha) per flank; the pre-machining tool
    # set by q / sin(alpha_n) further out leaves the root of the finishing profile II
    tool = din3972_tool("III", 4.0)
    x_EV = gn.pre_machining_generating_profile_shift_coefficient(
        0.1, 4.0, alpha_n, tool.machining_allowance_mm
    )
    assert x_EV == pytest.approx(0.1 + 0.25 * math.cbrt(4.0) / 4.0, abs=1e-14)
    d = iv.reference_diameter(20, 4.0, 0.0)
    root_iii = gn.generated_root_diameter(d, x_EV, 4.0, tool.addendum_factor * 4.0)
    root_ii = gn.generated_root_diameter(d, 0.1, 4.0, din3972_tool("II", 4.0).addendum_factor * 4.0)
    assert root_iii == pytest.approx(root_ii, abs=1e-12)
    assert gn.pre_machining_generating_profile_shift_coefficient(0.1, 4.0, alpha_n, 0.0) == 0.1
    with pytest.raises(InputRangeError):
        gn.pre_machining_generating_profile_shift_coefficient(0.1, 4.0, alpha_n, -0.01)


@pytest.mark.eq(SRC, "(128)")
@pytest.mark.eq("FVA604-I:2012", "(4.36)")
@pytest.mark.parametrize("name", list(CASES))
def test_tool_tip_form_height(name: str) -> None:
    c = _setup(name)
    _close(
        gn.tool_tip_form_height(c["h"] * c["m_n"], c["rho"] * c["m_n"], c["alpha_n"]),
        REFERENCE[name]["h_FaP0"],
    )


@pytest.mark.eq(SRC, "(125)")
@pytest.mark.parametrize("name", list(CASES))
def test_generated_root_diameter(name: str) -> None:
    c, ref = _setup(name), REFERENCE[name]
    _close(
        gn.generated_root_diameter(c["d"], ref["x_Es"], c["m_n"], c["h"] * c["m_n"]), ref["d_fE"]
    )
    _close(
        gn.generated_root_diameter(c["d"], ref["x_Ei"], c["m_n"], c["h"] * c["m_n"]), ref["d_fEi"]
    )


@pytest.mark.eq(SRC, "(135)")
@pytest.mark.parametrize("name", list(CASES))
def test_min_generating_profile_shift_coefficient(name: str) -> None:
    c, ref = _setup(name), REFERENCE[name]
    _close(
        gn.min_generating_profile_shift_coefficient(
            ref["h_FaP0"], c["m_n"], c["z"], c["alpha_t"], c["beta"]
        ),
        ref["x_Emin"],
    )


@pytest.mark.eq(SRC, "(128)")
@pytest.mark.parametrize("name", list(CASES))
def test_root_form_diameter(name: str) -> None:
    c, ref = _setup(name), REFERENCE[name]
    _close(
        gn.root_form_diameter(c["d"], c["alpha_t"], ref["h_FaP0"], ref["x_Es"], c["m_n"], c["d_b"]),
        ref["d_Ff"],
    )


@pytest.mark.eq(SRC, "(129)")
@pytest.mark.eq(SRC, "(130)")
@pytest.mark.parametrize("name", list(CASES))
def test_root_form_diameter_by_roll_angle_as_printed(name: str) -> None:
    """Eq. (130) as printed (sin alpha_t in the bracket) equals Eq. (128) of Anhang NB for spur
    gears; for helical gears it differs (finding of increment 3, documented in norm_map.md)."""
    c, ref = _setup(name), REFERENCE[name]
    value = gn.root_form_diameter_by_roll_angle(
        c["d_b"],
        c["z"],
        c["alpha_t"],
        c["beta"],
        c["h"] * c["m_n"],
        c["rho"] * c["m_n"],
        c["m_n"],
        ref["x_Es"],
    )
    _close(value, ref["d_Ff_printed_130"])
    if c["beta"] == 0.0:
        _close(value, ref["d_Ff"])
    else:
        assert abs(value - ref["d_Ff"]) > 1e-3, (
            "the printed Eq. (130) is not the corrected Eq. (128)"
        )


def test_iso_tr_example_1_follows_the_corrected_equation_128() -> None:
    """ISO/TR 6336-30:2022 prints d_Ff1 = 132,248 mm (p. 45) for x_E1 = 0,117 79, the value of
    Eq. (128) with (1 - sin alpha_n); Eq. (130) as printed would give 132,243 mm."""
    ref = REFERENCE["H"]
    assert round(ref["d_Ff"], 3) == 132.248
    assert round(ref["d_Ff_printed_130"], 3) == 132.243


@pytest.mark.eq(SRC, "(38)")
@pytest.mark.eq(SRC, "(48)")
@pytest.mark.parametrize("name", list(CASES))
def test_tip_tooth_thickness(name: str) -> None:
    c, ref = _setup(name), REFERENCE[name]
    psi = iv.tooth_thickness_half_angle(c["z"], ref["x_Es"], c["alpha_n"])
    s_at = gn.tip_tooth_thickness(c["d_a"], c["d_b"], psi, c["alpha_t"])
    _close(s_at, ref["s_at"])
    _close(gn.normal_tip_tooth_thickness(s_at, c["d_a"], c["d"], c["beta"]), ref["s_an"])


@pytest.mark.eq(SRC, "(35)")
@pytest.mark.eq(SRC, "(36)")
@pytest.mark.eq(SRC, "(37)")
@pytest.mark.parametrize("name", list(CASES))
def test_heights(name: str) -> None:
    c, ref = _setup(name), REFERENCE[name]
    _close(gn.tooth_depth(c["d_a"], ref["d_fE"]), ref["h"])
    _close(gn.addendum(c["d_a"], c["d"]), ref["h_a"])
    _close(gn.dedendum(c["d"], ref["d_fE"]), ref["h_f"])
    assert gn.tooth_depth(c["d_a"], ref["d_fE"]) == pytest.approx(
        gn.addendum(c["d_a"], c["d"]) + gn.dedendum(c["d"], ref["d_fE"]), abs=1e-12
    )


@pytest.mark.eq(OLD, "(A.3.03)")
@pytest.mark.eq(OLD, "(A.3.05)")
@pytest.mark.eq(OLD, "(A.3.06)")
@pytest.mark.parametrize("name", ["K", "L"])
def test_edge_break_of_the_tool(name: str) -> None:
    c, ref = _setup(name), REFERENCE[name]
    alpha_tK = gn.edge_break_transverse_angle(math.radians(c["alpha_kP"]), c["beta"])
    d_bK = gn.edge_break_base_diameter(c["d"], alpha_tK)
    s_tK = gn.edge_break_transverse_tooth_thickness(
        c["m_n"], c["beta"], c["h_FfP0"] * c["m_n"], c["alpha_t"], alpha_tK, ref["x_Es"]
    )
    psi_bK = gn.edge_break_base_half_angle(s_tK, c["d"], alpha_tK)
    psi_b = iv.base_tooth_thickness_half_angle(
        iv.tooth_thickness_half_angle(c["z"], ref["x_Es"], c["alpha_n"]), c["alpha_t"]
    )
    d_Fa = gn.tip_form_diameter_from_edge_break(c["d_b"], d_bK, psi_b, psi_bK, c["d_a"])
    assert abs(d_Fa - ref["d_Fa"]) < 1e-10
    _close(gn.tip_chamfer_height(c["d_a"], d_Fa), ref["h_K"])
    _close(gn.residual_tip_thickness(c["d_a"], d_bK, psi_bK), ref["s_aK"])
    # at d_Fa both involutes have the same thickness
    thickness = d_Fa * tr.involute_half_angle(0.5 * d_Fa, c["d_b"], psi_b)
    thickness_K = d_Fa * tr.involute_half_angle(0.5 * d_Fa, d_bK, psi_bK)
    assert thickness == pytest.approx(thickness_K, abs=1e-10)
    # the edge break involute is the thinner one above d_Fa, the thicker below (radii)
    assert tr.involute_half_angle(0.5 * c["d_a"], d_bK, psi_bK) < tr.involute_half_angle(
        0.5 * c["d_a"], c["d_b"], psi_b
    )
    lower = 0.25 * (c["d_b"] + d_Fa)
    assert tr.involute_half_angle(lower, d_bK, psi_bK) > tr.involute_half_angle(
        lower, c["d_b"], psi_b
    )


def test_edge_break_flank_not_reaching_the_tip_returns_the_tip_diameter() -> None:
    c = _setup("K")
    alpha_tK = gn.edge_break_transverse_angle(math.radians(45.0), 0.0)
    d_bK = gn.edge_break_base_diameter(c["d"], alpha_tK)
    psi_b = iv.base_tooth_thickness_half_angle(
        iv.tooth_thickness_half_angle(36, c["x_E"], c["alpha_n"]), c["alpha_t"]
    )
    s_tK = gn.edge_break_transverse_tooth_thickness(
        3.0, 0.0, 1.75 * 3.0, c["alpha_t"], alpha_tK, c["x_E"]
    )
    psi_bK = gn.edge_break_base_half_angle(s_tK, c["d"], alpha_tK)
    assert gn.tip_form_diameter_from_edge_break(c["d_b"], d_bK, psi_b, psi_bK, c["d_a"]) == c["d_a"]
    with pytest.raises(GeometryInfeasibleError, match="down to the base circle"):
        gn.tip_form_diameter_from_edge_break(c["d_b"], d_bK, psi_b, psi_bK - 0.3, c["d_a"])
    with pytest.raises(InputRangeError, match="steeper"):
        gn.edge_break_transverse_tooth_thickness(3.0, 0.0, 2.0, c["alpha_t"], c["alpha_t"], 0.0)
    with pytest.raises(InputRangeError, match="smaller base circle"):
        gn.tip_form_diameter_from_edge_break(c["d_b"], c["d_b"] * 1.01, psi_b, psi_bK, c["d_a"])


def test_typed_errors_of_the_single_equations() -> None:
    alpha_n = math.radians(20.0)
    with pytest.raises(GeometryInfeasibleError, match="no straight flank"):
        gn.tool_tip_form_height(1.0, 2.0, alpha_n)
    with pytest.raises(GeometryInfeasibleError, match="not positive"):
        gn.generated_root_diameter(2.0, -1.0, 1.0, 2.0)
    with pytest.raises(GeometryInfeasibleError, match="undercut"):
        gn.root_form_diameter(24.0, alpha_n, 2.5, 0.0, 2.0, 24.0 * math.cos(alpha_n))
    with pytest.raises(GeometryInfeasibleError, match="undercut"):
        gn.root_form_diameter_by_roll_angle(
            24.0 * math.cos(alpha_n), 12, alpha_n, 0.0, 2.5, 0.5, 2.0, 0.0
        )
    with pytest.raises(InputRangeError, match="exceeds"):
        gn.tip_chamfer_height(50.0, 50.1)
    with pytest.raises(GeometryInfeasibleError):
        gn.tooth_depth(50.0, 50.0)
    assert gn.dedendum(50.0, 50.0) == 0.0 and gn.dedendum(50.0, 52.0) == -1.0
    for bad in (float("nan"), float("inf"), "2", None, True):
        with pytest.raises(InputRangeError):
            gn.generating_profile_shift_coefficient(bad, 2.0, alpha_n, 0.0)  # type: ignore[arg-type]
        with pytest.raises(InputRangeError):
            gn.tooth_depth(bad, 40.0)  # type: ignore[arg-type]


# --- invariants -------------------------------------------------------------------------------------


@settings(max_examples=40, deadline=None)
@given(
    z=st.integers(min_value=10, max_value=200),
    x=st.floats(min_value=-0.5, max_value=1.0),
    beta_deg=st.floats(min_value=-45.0, max_value=45.0),
    rho_f=st.floats(min_value=0.05, max_value=0.4),
)
def test_closed_form_root_form_circle_equals_the_fillet_end(
    z: int, x: float, beta_deg: float, rho_f: float
) -> None:
    """Free of undercut, Eq. (128) is the point where the fillet meets the involute."""
    m_n, alpha_n, beta = 2.0, math.radians(20.0), math.radians(beta_deg)
    alpha_t = iv.transverse_pressure_angle(alpha_n, beta)
    h_FaP0 = gn.tool_tip_form_height(2.5, rho_f * m_n, alpha_n)
    if x <= gn.min_generating_profile_shift_coefficient(h_FaP0, m_n, z, alpha_t, beta) + 1e-3:
        return
    d = iv.reference_diameter(z, m_n, beta)
    d_b = iv.base_diameter(z, m_n, alpha_n, beta)
    closed = gn.root_form_diameter(d, alpha_t, h_FaP0, x, m_n, d_b)
    rounding = tr.tip_rounding(z, m_n, alpha_n, beta, 2.5, rho_f * m_n, x)
    r_end, _ = tr.fillet_point(rounding, rounding.flank_parameter_rad)
    assert 2.0 * r_end == pytest.approx(closed, rel=1e-12)


@settings(max_examples=30, deadline=None)
@given(z=st.integers(min_value=10, max_value=120), x=st.floats(min_value=-0.3, max_value=0.8))
def test_x_Emin_is_where_the_root_form_circle_reaches_the_base_circle(z: int, x: float) -> None:
    m_n, alpha_n = 3.0, math.radians(20.0)
    h_FaP0 = gn.tool_tip_form_height(3.75, 0.9, alpha_n)
    x_Emin = gn.min_generating_profile_shift_coefficient(h_FaP0, m_n, z, alpha_n, 0.0)
    d = iv.reference_diameter(z, m_n, 0.0)
    d_b = iv.base_diameter(z, m_n, alpha_n, 0.0)
    assert gn.root_form_diameter(d, alpha_n, h_FaP0, x_Emin, m_n, d_b) == pytest.approx(
        d_b, rel=1e-12
    )
    if x > x_Emin:
        assert gn.root_form_diameter(d, alpha_n, h_FaP0, x, m_n, d_b) > d_b


# --- orchestrator ---------------------------------------------------------------------------------


def _tool(**kwargs: object) -> ToolProfile:
    fields: dict[str, object] = {
        "addendum_factor": 1.25,
        "tip_radius_factor": 0.25,
        "protuberance_mm": 0.0,
        "machining_allowance_mm": 0.0,
    }
    fields.update(kwargs)
    return ToolProfile(**fields)  # type: ignore[arg-type]


def _pair(**kwargs: object) -> PairInput:
    tool = kwargs.pop("tool", _tool())
    tool_2 = kwargs.pop("tool_2", tool)
    allowances = kwargs.pop("allowances", ((-80.0, -130.0), (-100.0, -160.0)))
    gears = Pair(
        pinion=GearInput(
            number_of_teeth=20,
            profile_shift_coefficient=0.2,
            face_width_mm=20.0,
            tip_diameter_mm=44.8,
            tip_chamfer_radial_mm=kwargs.pop("h_K", 0.0),
            residual_tip_thickness_mm=kwargs.pop("s_aK", None),
            tooth_thickness_allowance_um=allowances[0],
            tool=tool,
        ),
        wheel=GearInput(
            number_of_teeth=34,
            profile_shift_coefficient=0.1,
            face_width_mm=20.0,
            tip_diameter_mm=72.4,
            tip_chamfer_radial_mm=0.0,
            tooth_thickness_allowance_um=allowances[1],
            tool=tool_2,
        ),
    )
    base = {
        "normal_module_mm": 2.0,
        "normal_pressure_angle_deg": 20.0,
        "helix_angle_deg": 0.0,
        "gears": gears,
    }
    base.update(kwargs)
    return PairInput(**base)  # type: ignore[arg-type]


def test_compute_generation_assembles_the_pair() -> None:
    result = gn.compute_generation(_pair())
    assert isinstance(result, GenerationResult)
    pinion, wheel = result.gears.pinion, result.gears.wheel
    assert isinstance(pinion, GearGeneration)
    assert (
        pinion.generating_profile_shift_coefficient
        == pinion.upper_generating_profile_shift_coefficient
    )
    assert (
        pinion.upper_generating_profile_shift_coefficient
        > pinion.lower_generating_profile_shift_coefficient
    )
    assert pinion.generated_root_diameter_mm > pinion.lower_generated_root_diameter_mm
    assert not pinion.undercut and not wheel.undercut
    assert pinion.tip_form_diameter_mm == pinion.tip_diameter_mm == 44.8
    assert pinion.residual_tip_thickness_mm is None and pinion.tip_chamfer_radial_mm == 0.0
    assert pinion.tooth_depth_mm == pytest.approx(
        pinion.addendum_mm + pinion.dedendum_mm, abs=1e-12
    )
    assert pinion.normal_tip_tooth_thickness_mm == pinion.transverse_tip_tooth_thickness_mm
    # the pair geometry carries the generated form circles
    geometry = result.pair_geometry
    assert geometry.root_form_diameter_mm == Pair(
        pinion=pinion.root_form_diameter_mm, wheel=wheel.root_form_diameter_mm
    )
    assert geometry.tip_form_diameter_mm == Pair(pinion=44.8, wheel=72.4)
    a_w = geometry.centre_distance_mm
    assert result.tip_clearance_mm.pinion == pytest.approx(
        pr.tip_clearance(a_w, 44.8, wheel.generated_root_diameter_mm), abs=1e-12
    )
    assert result.form_over_dimension_mm.wheel == pytest.approx(
        pr.form_over_dimension(geometry.sap_diameter_mm.wheel, wheel.root_form_diameter_mm),
        abs=1e-12,
    )
    assert result.warnings == ()
    assert GenerationResult.model_validate_json(result.model_dump_json()) == result


def test_without_allowances_the_nominal_tooth_is_generated() -> None:
    result = gn.compute_generation(_pair(allowances=(None, None)))
    for role, gear in zip(("pinion", "wheel"), result.gears.as_tuple(), strict=True):
        assert gear.generating_profile_shift_coefficient == gear.profile_shift_coefficient
        assert gear.lower_generated_root_diameter_mm == gear.generated_root_diameter_mm
        assert [w.code for w in gear.warnings] == ["no_tooth_thickness_allowance"]
        assert w_role(gear) == role
    assert [w.code for w in result.warnings] == ["no_tooth_thickness_allowance"] * 2


def w_role(gear: GearGeneration) -> str:
    return gear.warnings[0].message.split(":")[0]


def test_undercut_is_reported_and_the_root_form_circle_is_the_intersection() -> None:
    pair = _pair()
    gears = pair.gears
    pinion = gears.pinion.model_copy(
        update={"number_of_teeth": 12, "profile_shift_coefficient": 0.0, "tip_diameter_mm": 28.0}
    )
    wheel = gears.wheel.model_copy(
        update={"number_of_teeth": 40, "profile_shift_coefficient": 0.0, "tip_diameter_mm": 83.166}
    )
    result = gn.compute_generation(
        pair.model_copy(update={"gears": Pair(pinion=pinion, wheel=wheel)})
    )
    g = result.gears.pinion
    assert (
        g.undercut
        and g.generating_profile_shift_coefficient < g.min_generating_profile_shift_coefficient
    )
    assert [w.code for w in g.warnings] == ["root_form_diameter_by_intersection"]
    assert iv.base_diameter(12, 2.0, math.radians(20.0), 0.0) < g.root_form_diameter_mm < 24.0
    # the wheel is free of undercut and its root form circle is Eq. (128)
    assert not result.gears.wheel.undercut
    assert result.pair_geometry.root_form_diameter_mm is not None
    assert [w.code for w in result.warnings if w.code.startswith("active_profile")] == [
        "active_profile_limited_by_root_form_circle"
    ]


def test_tool_edge_break_generates_the_tip_form_circle() -> None:
    tool = _tool(tip_radius_factor=0.33, root_form_height_factor=0.6973, edge_break_angle_deg=45.0)
    pair = _pair(normal_module_mm=3.0, tool_2=tool, allowances=(None, None))
    pinion = pair.gears.pinion.model_copy(
        update={"number_of_teeth": 24, "profile_shift_coefficient": 0.2, "tip_diameter_mm": 78.32}
    )
    wheel = pair.gears.wheel.model_copy(
        update={
            "number_of_teeth": 36,
            "profile_shift_coefficient": 0.22105,
            "tip_diameter_mm": 114.69,
        }
    )
    result = gn.compute_generation(
        pair.model_copy(update={"gears": Pair(pinion=pinion, wheel=wheel)})
    )
    g = result.gears.wheel
    assert g.tip_form_diameter_mm == pytest.approx(REFERENCE["K"]["d_Fa"], abs=1e-9)
    assert g.tip_chamfer_radial_mm == pytest.approx(REFERENCE["K"]["h_K"], abs=1e-9)
    assert g.residual_tip_thickness_mm == pytest.approx(REFERENCE["K"]["s_aK"], abs=1e-9)
    assert g.tool_edge_break_angle_deg == 45.0 and g.tool_root_form_height_mm == pytest.approx(
        0.6973 * 3.0
    )
    assert result.pair_geometry.tip_form_diameter_mm.wheel == g.tip_form_diameter_mm
    # a tall root form height: the edge break flank does not reach the tip
    tall = tool.model_copy(update={"root_form_height_factor": 1.75})
    result = gn.compute_generation(
        pair.model_copy(
            update={"gears": Pair(pinion=pinion, wheel=wheel.model_copy(update={"tool": tall}))}
        )
    )
    assert result.gears.wheel.tip_form_diameter_mm == 114.69
    assert [w.code for w in result.gears.wheel.warnings] == [
        "no_tooth_thickness_allowance",
        "edge_break_flank_not_reaching_the_tip",
    ]


def test_given_chamfer_needs_its_shape_for_the_residual_thickness() -> None:
    without = gn.compute_generation(_pair(h_K=0.2))
    g = without.gears.pinion
    assert g.tip_form_diameter_mm == pytest.approx(44.4) and g.tip_chamfer_radial_mm == 0.2
    assert g.residual_tip_thickness_mm is None
    assert [w.code for w in g.warnings] == ["tip_chamfer_shape_not_given"]
    given = gn.compute_generation(_pair(h_K=0.2, s_aK=0.88))
    assert (
        given.gears.pinion.residual_tip_thickness_mm == 0.88 and given.gears.pinion.warnings == ()
    )
    with pytest.raises(InputRangeError, match="exceeds the tip tooth thickness"):
        gn.compute_generation(_pair(h_K=0.2, s_aK=5.0))


def test_root_form_height_without_an_angle() -> None:
    harmless = gn.compute_generation(_pair(tool=_tool(root_form_height_factor=1.75)))
    assert [w.code for w in harmless.gears.pinion.warnings] == ["edge_break_angle_not_given"]
    with pytest.raises(NotSupportedError, match="root rounding"):
        gn.compute_generation(_pair(tool=_tool(root_form_height_factor=0.5)))
    with pytest.raises(InputRangeError, match="needs the height"):
        gn.compute_generation(_pair(tool=_tool(edge_break_angle_deg=45.0)))
    with pytest.raises(InputRangeError, match="must not lie below"):
        gn.compute_generation(
            _pair(
                tool=_tool(
                    root_form_height_factor=1.3, dedendum_factor=1.2, edge_break_angle_deg=45.0
                )
            )
        )


def test_tool_root_line_below_the_tip_circle_cuts_it() -> None:
    """User decision 2026-10-03 (ADR-114): a tip circle above the root line of the tool is cut
    to d + 2 (x_E m_n + h_fP0) with a warning, as STplus does ("Kopfkreis ... von Wkz mit
    Fusshoehenfaktor geschnitten", probe tip_circle_cut_by_tool)."""
    pair = _pair(tool=_tool(dedendum_factor=0.9))
    result = gn.compute_generation(pair)
    codes = [w.code for w in result.gears.pinion.warnings]
    assert codes == ["tip_circle_cut_by_tool"]
    x_E = result.gears.pinion.generating_profile_shift_coefficient
    topping = 40.0 + 2.0 * (x_E * 2.0 + 1.8)
    assert topping < 44.8 and repr(topping) in result.gears.pinion.warnings[0].message
    assert result.gears.pinion.tip_diameter_mm == topping
    assert result.gears.pinion.tip_form_diameter_mm == topping
    # the pair meshes with the cut tip circle; the inputs stay as given
    assert result.pair_geometry.inputs.gears.pinion.tip_diameter_mm == topping
    assert result.inputs.gears.pinion.tip_diameter_mm == 44.8
    uncut = gn.compute_generation(_pair(tool=_tool(dedendum_factor=1.3)))
    assert uncut.gears.pinion.tip_diameter_mm == 44.8
    assert result.gears.pinion.addendum_mm < uncut.gears.pinion.addendum_mm
    assert result.tip_clearance_mm.pinion > uncut.tip_clearance_mm.pinion


def test_extension_points_raise_not_supported() -> None:
    with pytest.raises(NotSupportedError, match="protuberance"):
        gn.compute_generation(_pair(tool=_tool(protuberance_mm=0.1, protuberance_angle_deg=10.0)))
    with pytest.raises(NotSupportedError, match="machining allowance"):
        gn.compute_generation(_pair(tool=din3972_tool("III", 2.0)))
    with pytest.raises(NotSupportedError, match="differs from the gear"):
        gn.compute_generation(
            _pair(
                tool=_tool(
                    normal_module_mm=2.0
                    * math.cos(math.radians(20.0))
                    / math.cos(math.radians(22.0)),
                    profile_angle_deg=22.0,
                )
            )
        )
    with pytest.raises(NotSupportedError, match="together with an edge break"):
        gn.compute_generation(
            _pair(h_K=0.2, tool=_tool(root_form_height_factor=1.0, edge_break_angle_deg=45.0))
        )
    with pytest.raises(NotSupportedError, match="internal"):
        pair = _pair()
        gn.compute_generation(
            pair.model_copy(
                update={
                    "gears": Pair(
                        pinion=pair.gears.pinion.model_copy(update={"kind": GearKind.INTERNAL}),
                        wheel=pair.gears.wheel,
                    )
                }
            )
        )
    with pytest.raises(InputRangeError, match="needs the tip diameter"):
        pair = _pair()
        gn.compute_generation(
            pair.model_copy(
                update={
                    "gears": Pair(
                        pinion=pair.gears.pinion.model_copy(update={"tip_diameter_mm": None}),
                        wheel=pair.gears.wheel,
                    )
                }
            )
        )
    with pytest.raises(InputRangeError):
        gn.compute_generation("pair")  # type: ignore[arg-type]


def test_the_counterpart_of_a_basic_rack_generates_the_nominal_root() -> None:
    """The counterpart tool of ISO 53 type A generates d_fE = d - 2 h_fP + 2 x m_n = the nominal
    root diameter of Eq. (34) when there is no allowance."""
    tool = tool_from_basic_rack(iso53_basic_rack("A"))
    result = gn.compute_generation(_pair(tool=tool, allowances=(None, None)))
    d = iv.reference_diameter(20, 2.0, 0.0)
    assert result.gears.pinion.generated_root_diameter_mm == pytest.approx(
        d - 2.0 * (1.25 * 2.0 - 0.2 * 2.0), abs=1e-12
    )


def test_helical_generation_is_symmetric_in_the_hand() -> None:
    right = gn.compute_generation(_pair(helix_angle_deg=20.0))
    left = gn.compute_generation(_pair(helix_angle_deg=-20.0))
    for field in GearGeneration.model_fields:
        if field in ("warnings",):
            continue
        assert getattr(right.gears.pinion, field) == getattr(left.gears.pinion, field), field
    assert right.tip_clearance_mm == left.tip_clearance_mm
