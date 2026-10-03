"""Regression tests of the adversarial gate of increment 3 (gate_reports/increment_3.md).

Sections: G3A (reviewer A: norm side, generation and trochoid), G3B (reviewer B: comparison,
contour, importer, docs); the findings of the verification review (G3V) stand with the finding
whose fix they concern. Every test names the finding it pins.
"""

import math
from collections import deque

import numpy as np
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from scipy.optimize import brentq

from gearcore import contour as ct
from gearcore import generation as gn
from gearcore import involute as iv
from gearcore import parity
from gearcore import trochoid as tr
from gearcore.data import load_stplus, stplus_case_dirs, stplus_input_path
from gearcore.errors import GeometryInfeasibleError, InputRangeError, NotSupportedError, SolverError
from gearcore.io.ste import load_ste, pair_input_from_ste, parse_ste, tool_from_section
from gearcore.models.common import Pair
from gearcore.models.inputs import GearInput, MaterialKind, PairInput, ToolProfile
from gearcore.parity import compare_generation, compute_generation_from_data, generation_data
from gearcore.trace import equations_of


def _tool(**kwargs: object) -> ToolProfile:
    fields: dict[str, object] = {
        "addendum_factor": 1.25,
        "tip_radius_factor": 0.25,
        "protuberance_mm": 0.0,
        "machining_allowance_mm": 0.0,
    }
    fields.update(kwargs)
    return ToolProfile(**fields)  # type: ignore[arg-type]


def _pair(
    z: tuple[int, int] = (20, 40),
    x: tuple[float | None, float | None] = (0.2, 0.3),
    d_a: tuple[float, float] = (44.8, 84.2),
    m_n: float = 2.0,
    beta: float = 0.0,
    tool: ToolProfile | None = None,
    tool_2: ToolProfile | None = None,
    allowances: bool = False,
) -> PairInput:
    tool = tool or _tool()
    tool_2 = tool_2 or tool
    gears = Pair(
        pinion=GearInput(
            number_of_teeth=z[0],
            profile_shift_coefficient=x[0],
            face_width_mm=20.0,
            tip_diameter_mm=d_a[0],
            tip_chamfer_radial_mm=0.0,
            tooth_thickness_allowance_um=(-80.0, -130.0) if allowances else None,
            tool=tool,
        ),
        wheel=GearInput(
            number_of_teeth=z[1],
            profile_shift_coefficient=x[1],
            face_width_mm=20.0,
            tip_diameter_mm=d_a[1],
            tip_chamfer_radial_mm=0.0,
            tooth_thickness_allowance_um=(-100.0, -160.0) if allowances else None,
            tool=tool_2,
        ),
    )
    return PairInput(
        normal_module_mm=m_n, normal_pressure_angle_deg=20.0, helix_angle_deg=beta, gears=gears
    )


def _x_Emin(z: int, m_n: float, beta_deg: float, h_f: float, rho_f: float) -> float:
    alpha_n, beta = math.radians(20.0), math.radians(beta_deg)
    h_FaP0 = gn.tool_tip_form_height(h_f * m_n, rho_f * m_n, alpha_n)
    return gn.min_generating_profile_shift_coefficient(
        h_FaP0, m_n, z, iv.transverse_pressure_angle(alpha_n, beta), beta
    )


# --- G3A-01 (P0): the band just below the undercut limit ------------------------------------------


@pytest.mark.parametrize("z, beta_deg", [(12, 0.0), (20, 0.0), (30, 0.0), (8, 20.0), (30, 20.0)])
@pytest.mark.parametrize("offset", [-1e-9, -1e-6, -1e-5, -1e-4, -1e-3, -3e-3])
def test_g3a01_generation_just_below_the_undercut_limit(
    z: int, beta_deg: float, offset: float
) -> None:
    """x_E slightly below x_Emin: an ordinary input (x with four decimals lands there). The root
    form circle is the base circle or lies just above it, continuous with Eq. (128) at the limit."""
    m_n = 2.0
    x_Emin = _x_Emin(z, m_n, beta_deg, 1.25, 0.25)
    x_1 = x_Emin + offset
    d = iv.reference_diameter(z, m_n, math.radians(beta_deg))
    d_a1 = d + 2.0 * m_n * (1.0 + x_1)
    pair = _pair(
        z=(z, 60),
        x=(x_1, 0.3),
        d_a=(d_a1, iv.reference_diameter(60, m_n, math.radians(beta_deg)) + 2.6 * m_n),
        m_n=m_n,
        beta=beta_deg,
    )
    result = gn.compute_generation(pair)
    g = result.gears.pinion
    d_b = iv.base_diameter(z, m_n, math.radians(20.0), math.radians(beta_deg))
    assert g.undercut
    assert d_b <= g.root_form_diameter_mm <= d_b * (1.0 + 1e-5)
    if offset >= -1e-4:
        # the cut is below the resolution: the base circle itself, not the fillet end beyond it
        assert g.root_form_diameter_mm == d_b
    else:
        assert g.root_form_diameter_mm > d_b
    # continuity with the closed form at the limit
    at_limit = _pair(
        z=(z, 60),
        x=(x_Emin, 0.3),
        d_a=(d_a1, iv.reference_diameter(60, m_n, math.radians(beta_deg)) + 2.6 * m_n),
        m_n=m_n,
        beta=beta_deg,
    )
    limit = gn.compute_generation(at_limit).gears.pinion
    assert not limit.undercut and limit.root_form_diameter_mm == pytest.approx(d_b, rel=1e-12)
    assert g.root_form_diameter_mm - limit.root_form_diameter_mm < 2e-3 * d_b
    # the contour of such a gear is assembled without error and without a zero-length segment
    # (G3V-01: the fillet ends on the base circle itself, where the involute starts)
    contour = ct.tooth_contour(result, "pinion", points=40)
    assert np.hypot(*contour.segment("left_fillet")[-1]) == pytest.approx(
        0.5 * g.root_form_diameter_mm, rel=1e-12
    )
    steps = np.linalg.norm(np.diff(contour.as_array(), axis=0), axis=1)
    assert np.all(steps > 1e-9 * d_b)


@pytest.mark.parametrize("m_n", [0.5, 2.0, 100.0])
def test_g3v01_no_zero_length_segment_at_any_size(m_n: float) -> None:
    """The junction on the base circle is closed relative to the size of the gear (m 100: the
    half-EPS band of Eq. (12) alone is 5e-10 mm wide)."""
    z = 20
    x_1 = _x_Emin(z, m_n, 0.0, 1.25, 0.25) - 1e-6
    pair = _pair(z=(z, 60), x=(x_1, 0.3), d_a=(m_n * (z + 2.0), m_n * 62.6), m_n=m_n)
    result = gn.compute_generation(pair)
    d_b = iv.base_diameter(z, m_n, math.radians(20.0), 0.0)
    assert result.gears.pinion.root_form_diameter_mm == d_b
    contour = ct.tooth_contour(result, "pinion")
    steps = np.linalg.norm(np.diff(contour.as_array(), axis=0), axis=1)
    assert np.all(steps > 1e-9 * d_b)
    polygon = ct.gear_polygon(contour)
    assert np.all(np.linalg.norm(np.diff(polygon, axis=0), axis=1) > 1e-9 * d_b)


@pytest.mark.parametrize(
    "z, d_Ff_minus_d_b_um",
    [(12, 0.018_86), (20, 0.011_34), (40, 0.005_677)],
)
def test_g3v06_shallow_crossings_are_resolved_not_folded(z: int, d_Ff_minus_d_b_um: float) -> None:
    """x_Emin - 0,005: the fillet cuts the involute by far less than a nanometre and leaves it a
    hundredth of a micrometre above the base circle. The crossing is resolved (``GAP_TOLERANCE``
    lies far below such a cut), not folded onto the base circle."""
    m_n, alpha_n = 2.0, math.radians(20.0)
    x_E = _x_Emin(z, m_n, 0.0, 1.25, 0.25) - 5e-3
    d_b = iv.base_diameter(z, m_n, alpha_n, 0.0)
    psi_b = iv.base_tooth_thickness_half_angle(
        iv.tooth_thickness_half_angle(z, x_E, alpha_n), alpha_n
    )
    rounding = tr.tip_rounding(z, m_n, alpha_n, 0.0, 2.5, 0.5, x_E)
    d_Ff, theta, undercut = tr.root_form_diameter_by_intersection(
        rounding, d_b, psi_b, undercut_expected=True
    )
    assert undercut
    assert 1.0e3 * (d_Ff - d_b) == pytest.approx(d_Ff_minus_d_b_um, rel=2e-3)

    def gap(t: float) -> float:
        r, p = tr.fillet_point(rounding, t)
        return float(p) - tr.involute_half_angle(float(r), d_b, psi_b)

    # an independent look at the crossing: between the base circle and the crossing the fillet
    # lies inside the involute, beyond it outside, and the fillet end on the mirrored branch lies
    # four times as far above the base circle
    theta_b = brentq(
        lambda t: float(tr.fillet_point(rounding, t)[0]) - 0.5 * d_b, -0.5 * math.pi, theta
    )
    cut = gap(0.5 * (theta_b + theta))
    assert -1e-8 < cut < -10.0 * tr.GAP_TOLERANCE  # the cut the tolerance must stay below
    assert gap(theta + (theta - theta_b)) > 10.0 * tr.GAP_TOLERANCE
    r_end, _ = tr.fillet_point(rounding, rounding.flank_parameter_rad)
    assert 2.0 * r_end - d_b == pytest.approx(4.0 * (d_Ff - d_b), rel=2e-2)
    # the same value without the expectation of the caller
    assert tr.root_form_diameter_by_intersection(rounding, d_b, psi_b) == (d_Ff, theta, True)


@settings(max_examples=40, deadline=None)
@given(
    z=st.integers(min_value=8, max_value=80),
    offset=st.floats(min_value=-5e-3, max_value=-1e-10),
    beta_deg=st.floats(min_value=-40.0, max_value=40.0),
    rho_f=st.floats(min_value=0.05, max_value=0.4),
)
def test_g3a01_band_below_the_limit_never_raises(
    z: int, offset: float, beta_deg: float, rho_f: float
) -> None:
    m_n, alpha_n, beta = 2.0, math.radians(20.0), math.radians(beta_deg)
    x_E = _x_Emin(z, m_n, beta_deg, 1.25, rho_f) + offset
    alpha_t = iv.transverse_pressure_angle(alpha_n, beta)
    d_b = iv.base_diameter(z, m_n, alpha_n, beta)
    psi_b = iv.base_tooth_thickness_half_angle(
        iv.tooth_thickness_half_angle(z, x_E, alpha_n), alpha_t
    )
    rounding = tr.tip_rounding(z, m_n, alpha_n, beta, 2.5, rho_f * m_n, x_E)
    d_Ff, theta, undercut = tr.root_form_diameter_by_intersection(
        rounding, d_b, psi_b, undercut_expected=True
    )
    assert undercut and d_b <= d_Ff <= d_b * (1.0 + 1e-5)
    r, _ = tr.fillet_point(rounding, theta)
    assert 2.0 * r == pytest.approx(d_Ff, rel=1e-13)


def test_g3a01_inconsistent_psi_b_is_a_solver_error() -> None:
    """Without the knowledge of the caller a fillet ending off the involute is an inconsistency."""
    z, m_n, alpha_n = 30, 2.5, math.radians(20.0)
    alpha_t = iv.transverse_pressure_angle(alpha_n, 0.0)
    d_b = iv.base_diameter(z, m_n, alpha_n, 0.0)
    psi_b = iv.base_tooth_thickness_half_angle(
        iv.tooth_thickness_half_angle(z, 0.15, alpha_n), alpha_t
    )
    rounding = tr.tip_rounding(z, m_n, alpha_n, 0.0, 1.25 * m_n, 0.38 * m_n, 0.15)
    regular = tr.root_form_diameter_by_intersection(rounding, d_b, psi_b)
    assert regular[2] is False
    # G3V-08: a psi_b that is off by 1e-8 rad is an inconsistency, not a tangent end
    for offset in (0.01, 1e-4, 1e-6, 1e-8):
        with pytest.raises(SolverError, match="off the involute"):
            tr.root_form_diameter_by_intersection(rounding, d_b, psi_b - offset)
        with pytest.raises(SolverError, match="never leaves"):
            tr.root_form_diameter_by_intersection(rounding, d_b, psi_b + offset)
    # rounding of the last digits of psi_b is not: END_TOLERANCE lies between the two
    assert tr.root_form_diameter_by_intersection(rounding, d_b, psi_b - 1e-11) == regular
    with pytest.raises(InputRangeError):
        tr.root_form_diameter_by_intersection(rounding, d_b, psi_b, undercut_expected="yes")  # type: ignore[arg-type]


# --- G3A-02: pointed tooth at the tip circle ---------------------------------------------------------


def test_g3a02_pointed_tooth_at_the_tip_is_a_typed_error() -> None:
    z, m_n, alpha_n = 20, 2.0, math.radians(20.0)
    alpha_t = alpha_n
    d_b = iv.base_diameter(z, m_n, alpha_n, 0.0)
    psi_b = iv.base_tooth_thickness_half_angle(
        iv.tooth_thickness_half_angle(z, 0.2, alpha_n), alpha_t
    )
    d_pointed = d_b / math.cos(iv.inv_inverse(psi_b))
    for factor in (1.0, 1.0 + 1e-13, 1.0 + 2e-12, 1.01):
        with pytest.raises(GeometryInfeasibleError, match="pointed|flanks intersect"):
            gn.compute_generation(_pair(z=(20, 200), d_a=(d_pointed * factor, 404.0)))
    fine = gn.compute_generation(_pair(z=(20, 200), d_a=(d_pointed * (1.0 - 1e-6), 404.0)))
    assert fine.gears.pinion.transverse_tip_tooth_thickness_mm > 0.0


# --- G3A-03, G3A-06: tool feasibility on every path ------------------------------------------------


@pytest.mark.parametrize("z", [12, 20, 200])
@pytest.mark.parametrize("h_f, rho_f", [(2.5, 0.25), (2.5, 0.0), (1.25, 0.6), (1.25, 0.5)])
def test_g3a03_a_pointed_or_overlapping_tool_is_rejected_on_every_path(
    z: int, h_f: float, rho_f: float
) -> None:
    tool = _tool(addendum_factor=h_f, tip_radius_factor=rho_f)
    d = iv.reference_diameter(z, 2.0, 0.0)
    with pytest.raises(GeometryInfeasibleError, match="pointed or the tip roundings"):
        gn.compute_generation(_pair(z=(z, 300), x=(0.0, 0.0), d_a=(d + 4.0, 604.0), tool=tool))


@pytest.mark.parametrize("h_f", [0.5, 0.7, 0.79])
def test_g3a06_a_short_addendum_with_a_large_rounding_is_a_tool_on_every_path(h_f: float) -> None:
    """h_aP0 < rho_aP0 is fine as long as the straight flank exists (Eq. (128) bracket > 0)."""
    tool = _tool(addendum_factor=h_f, tip_radius_factor=0.6)
    assert gn.tool_tip_form_height(h_f * 2.0, 1.2, math.radians(20.0)) > 0.0
    regular = gn.compute_generation(_pair(z=(20, 34), x=(0.2, 0.1), d_a=(44.8, 72.4), tool=tool))
    assert not regular.gears.pinion.undercut
    # the undercut path builds the same rounding (z = 5, x_E = -0,5 is far below x_Emin)
    rounding = tr.tip_rounding(5, 2.0, math.radians(20.0), 0.0, h_f * 2.0, 1.2, -0.5)
    d_b = iv.base_diameter(5, 2.0, math.radians(20.0), 0.0)
    psi_b = iv.base_tooth_thickness_half_angle(
        iv.tooth_thickness_half_angle(5, -0.5, math.radians(20.0)), math.radians(20.0)
    )
    assert tr.root_form_diameter_by_intersection(rounding, d_b, psi_b, undercut_expected=True)[2]
    with pytest.raises(GeometryInfeasibleError, match="no straight flank"):
        tr.tip_rounding(20, 2.0, math.radians(20.0), 0.0, 1.0, 1.6, 0.0)


# --- G3A-04: dedendum is signed ---------------------------------------------------------------------


def test_g3a04_large_profile_shift_generates_a_root_above_the_reference_circle() -> None:
    result = gn.compute_generation(_pair(z=(50, 80), x=(1.5, 0.0), d_a=(110.0, 164.0)))
    g = result.gears.pinion
    assert g.generated_root_diameter_mm > 100.0 and g.dedendum_mm < 0.0
    assert g.tooth_depth_mm == pytest.approx(g.addendum_mm + g.dedendum_mm, abs=1e-12)
    assert gn.dedendum(100.0, 103.0) == -1.5


# --- G3A-05: sharp tool corner (rho_aP0 = 0) --------------------------------------------------------


def test_g3a05_sharp_corner_is_the_limit_of_the_rounding() -> None:
    d_Ff = {}
    for rho_f in (0.0, 1e-6, 1e-4, 1e-2):
        tool = _tool(tip_radius_factor=rho_f)
        result = gn.compute_generation(_pair(z=(12, 40), x=(0.0, 0.3), d_a=(28.0, 84.0), tool=tool))
        d_Ff[rho_f] = result.gears.pinion.root_form_diameter_mm
        assert result.gears.pinion.undercut
    assert d_Ff[1e-6] == pytest.approx(d_Ff[0.0], abs=1e-6)
    assert abs(d_Ff[1e-4] - d_Ff[0.0]) < abs(d_Ff[1e-2] - d_Ff[0.0])
    contour = ct.tooth_contour(
        result := gn.compute_generation(
            _pair(z=(12, 40), x=(0.0, 0.3), d_a=(28.0, 84.0), tool=_tool(tip_radius_factor=0.0))
        ),
        "pinion",
        points=40,
    )
    assert contour.undercut and result.gears.pinion.tool_tip_radius_mm == 0.0


# --- G3A-07, G3A-08: citations and registry ---------------------------------------------------------


def test_g3a07_abbildung_4_7_is_on_page_30() -> None:
    refs = {(r.eq, r.page) for r in equations_of(tr.generated_point)}
    assert ("Abbildung 4.7", 30) in refs


def test_g3a08_din_3960_writes_x_Ee_for_the_upper_limit() -> None:
    from gearcore.quantities import quantity

    entry = quantity("upper_generating_profile_shift_coefficient")
    assert [p.symbol for p in entry.replaced] == ["x_Ee"]
    assert quantity("lower_generating_profile_shift_coefficient").replaced[0].symbol == "x_Ei"


# --- G3A-10, G3A-12, G3A-13: typed errors and messages ------------------------------------------------


def test_g3a10_fillet_point_rejects_non_numbers() -> None:
    rounding = tr.tip_rounding(20, 2.0, math.radians(20.0), 0.0, 2.5, 0.5, 0.0)
    for bad in ("a", None, True, float("nan"), float("inf"), np.array(["a"]), np.array([True])):
        with pytest.raises(InputRangeError):
            tr.fillet_point(rounding, bad)  # type: ignore[arg-type]
    # G3V-02: the same for the end parameter and the number of points of the curve
    for bad_end in ("a", True, float("nan"), float("inf"), 0.0):
        with pytest.raises(InputRangeError):
            tr.fillet_curve(rounding, bad_end)  # type: ignore[arg-type]
    for bad_n in ("a", True, 2, 10.0, None):
        with pytest.raises(InputRangeError):
            tr.fillet_curve(rounding, None, bad_n)  # type: ignore[arg-type]


def test_g3a12_root_form_height_without_angle_reaching_the_tip_is_an_extension_point() -> None:
    with pytest.raises(NotSupportedError, match="root rounding"):
        gn.compute_generation(_pair(tool=_tool(root_form_height_factor=0.5)))


def test_g3a13_messages_print_plain_floats() -> None:
    rounding = tr.tip_rounding(30, 2.5, math.radians(20.0), 0.0, 1.25 * 2.5, 0.95, 0.15)
    with pytest.raises(GeometryInfeasibleError) as caught:
        tr.root_form_diameter_by_intersection(rounding, 200.0, 0.1)
    assert "np.float64" not in str(caught.value)


# --- G3B-02, G3B-05: importer defaults --------------------------------------------------------------


def test_g3b02_dedendum_below_the_default_root_form_height_is_raised_like_stplus() -> None:
    """Since ADR-114 the rule is the one of the probes: the root form height is preset with 1,3
    whether or not an angle is given, a dedendum below it is set equal to it, and a tool without
    a flank between the two heights breaks no tip edge."""
    text = (
        "$ Anfang\n$ GEOMETRIEDATEN\nZAEHNEZAHL = 20 40\nNORMALMODUL = 2\nEINGRIFFSWINKEL = 20\n"
        "SCHRAEGUNGSWINKEL = 0\nPROFILVERSCHIEBUNG_N = 0.2 0.3\nZAHNBREITE = 20 20\n"
        "KOPFKREISDM = 44.8 84.2\nWERKZEUG_VORVERZ. = WKZ_1 WKZ_1\n$ WKZ_1\nKOPFHOEHENFAKTOR = 1.25\n"
        "FUSSHOEHENFAKTOR = 1.25\nKOPFABRUNDUNGSFAKTOR = 0.25\nKANTENBRECHWINKEL = 45\n$ Ende\n"
    )
    imported = pair_input_from_ste(parse_ste(text))
    tool = imported.pair.gears.pinion.tool
    assert tool.root_form_height_factor == 1.3 and tool.dedendum_factor == 1.3
    assert tool.edge_break_angle_deg == 45.0
    assert any(
        "h_fP0* = 1.25 set to the root form height h_FfP0* = 1.3" in note for note in imported.notes
    )
    assert any("FUSSFORMHOEHENFAKTOR not given → h_FfP0* = 1.3" in note for note in imported.notes)
    result = gn.compute_generation(imported.pair)
    assert [w.code for w in result.gears.pinion.warnings] == [
        "no_tooth_thickness_allowance",
        "edge_break_angle_without_flank",
    ]
    assert result.gears.pinion.tip_form_diameter_mm == result.gears.pinion.tip_diameter_mm


def test_g3b05_tool_from_section_records_every_default() -> None:
    ste = parse_ste(
        "$ Anfang\n$ T\nKOPFHOEHENFAKTOR = 1.25\nKOPFABRUNDUNGSFAKTOR = 0.25\nKANTENBRECHWINKEL = 45\n$ Ende\n"
    )
    notes: list[str] = []
    tool = tool_from_section(ste.section("T"), notes, normal_pressure_angle_deg=20.0)  # type: ignore[arg-type]
    assert tool.root_form_height_factor == 1.3 and tool.dedendum_factor == 1.3
    assert len(notes) == 4  # root form height, dedendum, protuberance, allowance
    with pytest.raises(TypeError):
        tool_from_section(ste.section("T"))  # type: ignore[call-arg]
    # G3V-02: anything that cannot take the records is a typed error
    for bad in (None, (), "notes", deque()):
        with pytest.raises(InputRangeError, match="notes must be a list"):
            tool_from_section(ste.section("T"), bad, normal_pressure_angle_deg=20.0)  # type: ignore[arg-type]


def test_g3v04_an_equal_dedendum_is_not_reported_as_raised() -> None:
    ste = parse_ste(
        "$ Anfang\n$ T\nKOPFHOEHENFAKTOR = 1.25\nFUSSHOEHENFAKTOR = 1.3\n"
        "KOPFABRUNDUNGSFAKTOR = 0.25\nKANTENBRECHWINKEL = 45\n$ Ende\n"
    )
    notes: list[str] = []
    tool = tool_from_section(ste.section("T"), notes, normal_pressure_angle_deg=20.0)  # type: ignore[arg-type]
    assert tool.dedendum_factor == 1.3 and tool.root_form_height_factor == 1.3
    assert not [note for note in notes if "set to the root form height" in note]


# --- G3B-03: fixture records state what the importer reads -------------------------------------------


@pytest.mark.parametrize("case", [p.name for p in stplus_case_dirs()])
def test_g3b03_typed_import_of_the_fixture_is_current(case: str) -> None:
    meta = load_stplus(case, "meta")
    recorded = meta["typed_import"]
    kinds = {k: MaterialKind(v) for k, v in (meta.get("material_kinds") or {}).items()}
    imported = pair_input_from_ste(load_ste(stplus_input_path(case)), material_kinds=kinds)
    assert recorded["ok"] is True
    assert list(recorded["notes"]) == list(imported.notes), case
    assert list(recorded["unmapped_keys"]) == list(imported.unmapped_keys), case


# --- G3B-04, G3B-14: contour signature and typed errors -----------------------------------------------


def test_g3b04_the_contour_takes_the_generation_only() -> None:
    data = generation_data("fzg_c")
    result = compute_generation_from_data(data, data.values)
    contour = ct.tooth_contour(result, "pinion", points=32)
    assert contour.number_of_teeth == 16
    with pytest.raises(InputRangeError, match="GenerationResult"):
        ct.tooth_contour(result.inputs, "pinion")  # type: ignore[arg-type]
    with pytest.raises(InputRangeError):
        ct.compare(contour, np.array([["a", "b"]]))
    with pytest.raises(InputRangeError):
        ct.compare(contour, "points")  # type: ignore[arg-type]
    with pytest.raises(InputRangeError, match="tip radius"):
        ct.chamfer_flank(22.4, 0.03, 22.2, 0.5, 5)
    with pytest.raises(InputRangeError):
        ct.distances("contour", np.zeros((2, 2)))  # type: ignore[arg-type]
    with pytest.raises(InputRangeError, match="ToothContour"):
        ct.gear_polygon(result.inputs)  # type: ignore[arg-type]
    short = contour.model_dump()
    short["points"] = short["points"][:-3]
    with pytest.raises(ValueError, match="segments end"):
        ct.ToothContour.model_validate(short)


# --- G3B-08: no zero-length segments ------------------------------------------------------------------


@pytest.mark.parametrize(
    "case, role", [("fzg_c", "pinion"), ("kst_c_rerun", "wheel"), ("chamfer_hk_z20_34", "wheel")]
)
def test_g3b08_no_consecutive_duplicate_points(case: str, role: str) -> None:
    from gearcore.stplus_program import stplus_transverse_residual_tip_thickness

    data = generation_data(case)
    result = compute_generation_from_data(data, data.values)
    gears = []
    for gear, generated in zip(
        result.inputs.gears.as_tuple(), result.gears.as_tuple(), strict=True
    ):
        if gear.tip_chamfer_radial_mm > 0.0 and gear.residual_tip_thickness_mm is None:
            s_aK = stplus_transverse_residual_tip_thickness(
                generated.transverse_tip_tooth_thickness_mm,
                generated.normal_tip_tooth_thickness_mm,
                gear.tip_chamfer_radial_mm,
            )
            gears.append(gear.model_copy(update={"residual_tip_thickness_mm": s_aK}))
        else:
            gears.append(gear)
    result = gn.compute_generation(
        result.inputs.model_copy(update={"gears": Pair(pinion=gears[0], wheel=gears[1])})
    )
    contour = ct.tooth_contour(result, role)  # type: ignore[arg-type]
    points = contour.as_array()
    steps = np.linalg.norm(np.diff(points, axis=0), axis=1)
    assert np.all(steps > 1e-9)
    polygon = ct.gear_polygon(contour)
    assert np.all(np.linalg.norm(np.diff(polygon, axis=0), axis=1) > 1e-9)
    assert ct.distances(contour, points[::5]).max() < 1e-12


def test_g3v07_distances_are_micrometres() -> None:
    """A point moved radially by 2 um lies 2 um sin(alpha_y) from the involute (its normal is
    the tangent to the base circle), and ``distances`` gives what ``compare`` summarises."""
    data = generation_data("fzg_c")
    result = compute_generation_from_data(data, data.values)
    contour = ct.tooth_contour(result, "wheel")
    pair = result.inputs
    d_b = iv.base_diameter(
        contour.number_of_teeth,
        pair.normal_module_mm,
        math.radians(pair.normal_pressure_angle_deg),
        math.radians(pair.helix_angle_deg),
    )
    flank = contour.segment("left_involute")[10:-10:7]
    radius = np.hypot(flank[:, 0], flank[:, 1])
    moved = flank * (1.0 + 2.0e-3 / radius)[:, None]
    gaps = ct.distances(contour, moved)
    assert gaps.shape == (len(moved),)
    # 2 % for the corner of the polyline at the vertex that was moved
    assert np.allclose(gaps, 2.0 * np.sqrt(1.0 - (0.5 * d_b / radius) ** 2), rtol=2e-2, atol=0.0)
    diff = ct.compare(contour, moved)
    assert gaps.max() == pytest.approx(diff.max_um, rel=1e-12)
    assert math.sqrt(float(np.mean(gaps**2))) == pytest.approx(diff.rms_um, rel=1e-12)
    reference = ct.stplus_contour("fzg_c", 2)
    assert ct.distances(contour, reference).max() == pytest.approx(
        ct.compare(contour, reference).max_um, rel=1e-12
    )


# --- G3B-15, G3B-16: the tip arc lies on the tip circle; regions follow the STplus radii --------------


def test_g3b15_tip_arc_of_a_chamfered_gear_lies_on_the_tip_circle() -> None:
    data = generation_data("kst_c_rerun")
    result = compute_generation_from_data(data, data.values)
    contour = ct.tooth_contour(result, "wheel")
    tip = contour.segment("tip")
    assert len(tip) >= 2
    assert np.allclose(
        np.hypot(tip[:, 0], tip[:, 1]), 0.5 * contour.tip_diameter_mm, rtol=0.0, atol=1e-12
    )
    flank = contour.segment("left_tip_flank")
    involute = contour.segment("left_involute")
    assert np.hypot(*involute[-1]) == pytest.approx(0.5 * contour.tip_form_diameter_mm, rel=1e-12)
    assert np.hypot(*flank[-1]) == pytest.approx(0.5 * contour.tip_diameter_mm, rel=1e-12)
    assert contour.tip_form_diameter_mm < contour.tip_diameter_mm


@pytest.mark.parametrize("case, gear", [("kst_c_rerun", 2), ("fzg_c", 1), ("helix30_z25_40", 2)])
def test_g3b16_region_counts_follow_the_reference_radii(case: str, gear: int) -> None:
    data = generation_data(case)
    result = compute_generation_from_data(data, data.values)
    role = "pinion" if gear == 1 else "wheel"
    contour = ct.tooth_contour(result, role)  # type: ignore[arg-type]
    reference = ct.stplus_contour(case, gear)
    diff = ct.compare(contour, reference)
    radius = np.hypot(reference[:, 0], reference[:, 1])
    fillet = int(np.sum(radius < 0.5 * contour.root_form_diameter_mm * (1.0 - ct.REGION_TOLERANCE)))
    tip = int(np.sum(radius > 0.5 * contour.tip_form_diameter_mm * (1.0 + ct.REGION_TOLERANCE)))
    assert (diff.fillet_points, diff.tip_points) == (fillet, tip)
    assert diff.involute_points == len(reference) - fillet - tip
    if gear == 2 and case == "kst_c_rerun":
        assert diff.tip_points > 2  # the edge break involute of the tool
    else:
        assert diff.tip_points == 0  # no chamfer: the tip circle is the tip form circle


# --- G3B-09, G3B-12: the fourth tolerance part and rows without evidence -----------------------------


def test_g3b09_the_solver_tolerance_is_reported_separately() -> None:
    rows = compare_generation("plastic_m05_z20")
    form = [r for r in rows if r.field == "root_form_diameter_mm" and r.origin == "interface"]
    assert form and all(r.solver_tolerance == parity.FORM_CIRCLE_ACCURACY_MM for r in form)
    assert all(r.arithmetic_tolerance < 1e-4 for r in form)
    depth = [r for r in rows if r.field == "tooth_depth_mm"]
    assert depth and all(r.solver_tolerance == 0.0 for r in depth)
    assert all(r.solver_tolerance == 0.0 for r in parity.compare_pair_geometry("fzg_c"))


def test_g3b12_rows_without_evidence_are_counted() -> None:
    rows = [row for path in stplus_case_dirs() for row in compare_generation(path.name)]
    weak = parity.rows_without_evidence(rows)
    # a form over-dimension of zero or of a few micrometres, a chamfer height of zero
    assert {(r.case, r.field) for r in weak} == {
        ("small_z8_x05", "form_over_dimension_mm"),
        ("neg_shift_z17_xm08", "form_over_dimension_mm"),
        ("undercut_z12_x0", "form_over_dimension_mm"),
    }
    # (G3X-01: the tool of helix20_z25_65 states an edge break angle but has no flank; its chamfer
    # height of zero is an input and is not compared any more)
    assert not [r for r in rows if r.case == "helix20_z25_65" and "chamfer" in r.field]
    assert not [
        r
        for r in rows
        if r.field == "tip_form_diameter_mm" and r.case in ("fzg_c", "chamfer_hk_z20_34")
    ]


# --- G3W: second verification review (2026-10-01) -----------------------------------------------------


def _direct(z: int, x_E: float, m_n: float = 2.0) -> tuple[float, float, tr.TipRounding]:
    """(d_b, psi_b, rounding) of a spur gear cut by the tool 1,25 / 0,25."""
    alpha_n = math.radians(20.0)
    d_b = iv.base_diameter(z, m_n, alpha_n, 0.0)
    psi_b = iv.base_tooth_thickness_half_angle(
        iv.tooth_thickness_half_angle(z, x_E, alpha_n), alpha_n
    )
    return d_b, psi_b, tr.tip_rounding(z, m_n, alpha_n, 0.0, 1.25 * m_n, 0.25 * m_n, x_E)


def test_g3w01_the_strategy_box_of_the_undercut_test_holds_no_tools() -> None:
    """rho* = 0,4 with h* = 1,390 625 (an example hypothesis drew): the roundings overlap."""
    with pytest.raises(GeometryInfeasibleError, match="pointed or the tip roundings"):
        tr.tip_rounding(8, 2.0, math.radians(20.0), 0.0, 2.78125, 0.8, 0.0)


@pytest.mark.parametrize("z, x_E", [(60, 0.0), (20, 0.2), (20, -0.05)])
def test_g3w02_a_wrong_undercut_expectation_is_refuted_by_the_fillet(z: int, x_E: float) -> None:
    """A gear free of undercut whose caller says "undercut": the fillet ends on the involute, not
    on its mirrored branch, and no base circle is returned for it."""
    d_b, psi_b, rounding = _direct(z, x_E)
    assert x_E > _x_Emin(z, 2.0, 0.0, 1.25, 0.25)
    d_Ff, _, undercut = tr.root_form_diameter_by_intersection(rounding, d_b, psi_b)
    assert undercut is False and d_Ff > d_b * (1.0 + 1e-5)
    with pytest.raises(SolverError, match="undercut is expected"):
        tr.root_form_diameter_by_intersection(rounding, d_b, psi_b, undercut_expected=True)


def test_g3w02_an_inconsistent_psi_b_is_not_covered_by_the_expectation() -> None:
    d_b, psi_b, rounding = _direct(20, _x_Emin(20, 2.0, 0.0, 1.25, 0.25) - 1e-6)
    d_Ff, _, undercut = tr.root_form_diameter_by_intersection(
        rounding, d_b, psi_b, undercut_expected=True
    )
    assert (d_Ff, undercut) == (d_b, True)
    for offset in (1e-2, 1e-6, 1e-8):
        with pytest.raises(SolverError, match="undercut is expected"):
            tr.root_form_diameter_by_intersection(
                rounding, d_b, psi_b - offset, undercut_expected=True
            )
    # rounding of the last digits of psi_b is not an inconsistency
    assert tr.root_form_diameter_by_intersection(
        rounding, d_b, psi_b - 1e-11, undercut_expected=True
    ) == (d_b, pytest.approx(rounding.flank_parameter_rad, abs=1e-3), True)


def test_g3w03_wrong_argument_types_are_typed_errors() -> None:
    d_b, psi_b, rounding = _direct(20, 0.2)
    for bad in (None, "a", _pair()):
        with pytest.raises(InputRangeError, match="TipRounding"):
            tr.fillet_point(bad, -1.0)  # type: ignore[arg-type]
        with pytest.raises(InputRangeError, match="TipRounding"):
            tr.fillet_curve(bad)  # type: ignore[arg-type]
        with pytest.raises(InputRangeError, match="TipRounding"):
            tr.root_form_diameter_by_intersection(bad, d_b, psi_b)  # type: ignore[arg-type]
    for bad in (None, "a", 1j, True, np.array(["a"]), np.array([1j]), np.array([np.nan])):
        for position in range(4):
            arguments = [1.0, 1.0, 1.0, 1.0]
            arguments[position] = bad  # type: ignore[call-overload]
            with pytest.raises(InputRangeError):
                tr.pitch_point_position(*arguments)
        for position in range(3):
            arguments = [1.0, -1.0, 0.5]
            arguments[position] = bad  # type: ignore[call-overload]
            with pytest.raises(InputRangeError):
                tr.generated_point(*arguments, 20.0)
    with pytest.raises(InputRangeError, match="one shape"):
        tr.pitch_point_position(np.zeros(3), np.zeros(3), np.ones(2), np.ones(3))
    with pytest.raises(InputRangeError, match="one shape"):
        tr.generated_point(np.zeros(3), np.zeros(2), np.zeros(3), 20.0)
    with pytest.raises(InputRangeError):
        tr.fillet_point(rounding, np.array([-1.0 + 0.0j]))
    # numbers and arrays of one shape are what the functions take
    radius, _ = tr.generated_point(np.zeros(3), np.full(3, -1.0), 0.5, 20.0)
    assert np.shape(radius) == (3,)

    result = gn.compute_generation(_pair())
    contour = ct.tooth_contour(result, "pinion", points=16)
    for bad in ([[0.0, 20.0], [0.1]], np.array([[0.0 + 1.0j, 20.0]])):
        with pytest.raises(InputRangeError):
            ct.compare(contour, bad)  # type: ignore[arg-type]
        with pytest.raises(InputRangeError):
            ct.distances(contour, bad)  # type: ignore[arg-type]
    assert ct.compare(contour, [[0.0, 20.0], [0.1, 20.0]]).reference_points == 2  # type: ignore[arg-type]
    for bad in ("T", 7):
        with pytest.raises(InputRangeError, match="section"):
            tool_from_section(bad, [])  # type: ignore[arg-type]
    # no section is the hob STplus presets (ADR-114), with a note
    notes: list[str] = []
    hob = tool_from_section(None, notes, name="hob", normal_pressure_angle_deg=20.0)
    assert hob.addendum_factor == 1.25 and notes


def test_g3w04_fillet_curve_takes_what_its_neighbours_take() -> None:
    _, _, rounding = _direct(20, 0.2)
    theta, radius, psi = tr.fillet_curve(rounding, None, np.int64(5))  # type: ignore[arg-type]
    assert len(theta) == len(radius) == len(psi) == 5
    # the slack of `fillet_point` at the start of the fillet holds for the end as well
    assert len(tr.fillet_curve(rounding, -0.5 * math.pi - 1e-13, 3)[0]) == 3
    with pytest.raises(InputRangeError):
        tr.fillet_curve(rounding, -0.5 * math.pi - 1e-9, 3)
    with pytest.raises(InputRangeError):
        tr.fillet_curve(rounding, rounding.flank_parameter_rad + 1e-9, 3)


@pytest.mark.parametrize("radius", [1.0, 1000.0])
def test_g3w05_the_join_tolerance_is_relative_and_bounded_from_both_sides(radius: float) -> None:
    """A first point within 1e-11 of the radius repeats the point before it, one at 1e-9 does
    not (and stays), at any size."""
    before = np.array([[0.0, 0.5 * radius], [0.0, radius]])
    for gap, kept in ((1e-9, True), (1e-11, False)):
        block = np.array([[gap * radius, radius], [0.1 * radius, radius]])
        points, ranges = ct._joined([before, block])
        assert len(points) == (4 if kept else 3)
        assert ranges == [(0, 2), (2, 4 if kept else 3)]
        assert np.array_equal(points[-1], block[-1])


@pytest.mark.parametrize(
    "delta, arc_points", [(0.0, -1), (-1e-14, -1), (-1e-9, 0), (-1e-6, 8), (-0.2, 8)]
)
def test_g3w06_gear_polygon_of_a_full_radius_tool(delta: float, arc_points: int) -> None:
    """The fillets of a full-radius tool meet on the root circle: no root arc, the shared point
    placed once (-1); an arc shorter than its points could resolve is one segment (0)."""
    alpha = math.radians(20.0)
    rho_full = (math.pi / 4.0 - 1.25 * math.tan(alpha)) / (1.0 / math.cos(alpha) - math.tan(alpha))
    result = gn.compute_generation(_pair(tool=_tool(tip_radius_factor=rho_full + delta)))
    contour = ct.tooth_contour(result, "pinion")
    polygon = ct.gear_polygon(contour)
    assert len(polygon) == contour.number_of_teeth * (len(contour.points) + arc_points)
    closed = np.vstack((polygon, polygon[:1]))
    steps = np.linalg.norm(np.diff(closed, axis=0), axis=1)
    assert np.all(steps > ct.JOIN_TOLERANCE * 0.5 * contour.generated_root_diameter_mm)
    radius = np.hypot(polygon[:, 0], polygon[:, 1])
    assert np.min(radius) == pytest.approx(0.5 * contour.generated_root_diameter_mm, rel=1e-12)
