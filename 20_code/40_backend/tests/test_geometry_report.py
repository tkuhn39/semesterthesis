"""
@module: tests.test_geometry_report
@context: Domain-layer tests — the SSOT geometry report (DIN ISO 21771 / DIN 21773 /
          DIN 3967 / DIN 3964).
@role: Full kst-E parity for the inspection/backlash/sliding block against the STplus
       reference output (Blatt 6–8) — transcribed literals, computed on CURRENT norms.
       Documented deviations from STplus (ADR-011 "the norm wins"): the chordal thickness
       uses the DIN 21773 §5 measurement cylinder d_y = d_a − 2·m_n (STplus uses its own
       caliper-contact cylinder), and the tip tooth thickness is the as-cut value at d_Na.
"""

import math
from pathlib import Path

import pytest

from app.io.ste import Pair, gear_stage_from_ste, load_ste
from app.services.geometry.gear import GearStage, ToolReferenceProfile
from app.services.geometry.report import compute_geometry_report

_REF_STE = (
    Path(__file__).resolve().parents[3]
    / "30_references_and_examples"
    / "33_STplus"
    / "kst-E_eingabe.ste"
)

pytestmark = pytest.mark.skipif(not _REF_STE.exists(), reason="STplus reference .ste not present")


@pytest.fixture(scope="module")
def report():
    data = gear_stage_from_ste(load_ste(_REF_STE))
    stage = GearStage.from_ste(data)
    up = data.tooth_width_allowance_upper_um
    low = data.tooth_width_allowance_lower_um
    return compute_geometry_report(
        stage,
        ball_diameter_mm=Pair(1.75, 1.75),
        span_allowance_upper_mm=Pair(up[0] / 1000.0, up[1] / 1000.0),
        span_allowance_lower_mm=Pair(low[0] / 1000.0, low[1] / 1000.0),
        center_distance_allowance_mm=0.015,  # DIN 3964 js7 for the kst-E case
    )


# (attribute, expected gear1, expected gear2, abs tolerance) — kst-E-ausgabe.sta Blatt 6–8
_GEAR_EXPECTED = [
    ("tooth_thickness_normal_mm", 1.719, 1.800, 1e-3),
    ("space_width_normal_mm", 1.423, 1.342, 1e-3),
    ("span_teeth", 6, 6, 0),
    ("span_measurement_mm", 17.090, 17.180, 1e-3),
    ("span_contact_diameter_mm", 50.788, 51.728, 1e-3),
    ("two_ball_measure_mm", 53.846, 55.064, 1e-3),
    ("two_roller_measure_mm", 53.846, 55.064, 1e-3),
    ("ball_contact_diameter_mm", 50.779, 52.146, 1e-3),
    ("thickness_allowance_upper_mm", -0.296, -0.220, 5e-4),
    ("ball_allowance_factor", 2.489, 2.415, 1e-3),
    ("usable_root_diameter_mm", 50.391, 51.315, 1e-3),
    ("form_reserve_mm", 0.655, 0.578, 1.5e-3),
    ("tooth_height_mm", 2.250, 2.249, 1e-3),
    ("addendum_mm", 0.947, 1.011, 1e-3),
    ("addendum_factor_actual", 0.744, 0.697, 1e-3),
    ("tip_clearance_mm", 0.791, 0.792, 1e-3),
    ("tip_path_of_contact_mm", 1.771, 1.635, 1e-3),
    ("sliding_factor_tip", 0.136, 0.126, 5e-4),
    ("specific_sliding_tip", 0.313, 0.294, 5e-4),
    ("specific_sliding_root", -0.416, -0.457, 1e-3),
    ("rest_tip_thickness_mm", 0.672, 0.634, 1e-3),
    ("generation_profile_shift", -0.2030, 0.0117, 5e-4),
]


@pytest.mark.parametrize(("attr", "e1", "e2", "tol"), _GEAR_EXPECTED, ids=lambda v: str(v))
def test_gear_values_match_reference(report, attr, e1, e2, tol) -> None:
    v1, v2 = getattr(report.gear1, attr), getattr(report.gear2, attr)
    if tol == 0:
        assert (v1, v2) == (e1, e2)
    else:
        assert v1 == pytest.approx(e1, abs=tol)
        assert v2 == pytest.approx(e2, abs=tol)


def test_pair_values_match_reference(report) -> None:
    p = report.pair
    assert p.common_tooth_height_mm == pytest.approx(1.341, abs=1e-3)
    assert p.common_height_factor == pytest.approx(1.341, abs=1e-3)
    assert p.backlash_circumferential_mm == pytest.approx(0.521, abs=1e-3)
    assert p.backlash_normal_mm == pytest.approx(0.485, abs=1e-3)
    assert p.transverse_pitch_mm == pytest.approx(3.142, abs=1e-3)
    assert p.normal_pitch_mm == pytest.approx(3.142, abs=1e-3)
    assert p.normal_base_pitch_mm == pytest.approx(2.952, abs=1e-3)
    assert p.transverse_base_pitch_mm == pytest.approx(2.952, abs=1e-3)
    assert p.backlash_delta_upper_mm == pytest.approx((0.012, 0.011), abs=5e-4)
    assert p.backlash_delta_lower_mm == pytest.approx((-0.012, -0.011), abs=5e-4)
    assert p.gear_ratio == pytest.approx(52.0 / 51.0, abs=1e-9)


def test_chordal_thickness_is_norm_conform(report) -> None:
    """DIN 21773 §5 with d_y = d_a − 2·m_n (the norm's suggested measurement cylinder).

    STplus prints 1.723/1.808 on ITS caliper-contact cylinder — a tool convention, not the
    norm's; per ADR-011 the norm value is reported. Sanity: the chord is close to (and
    consistent with) the arc thickness at d_y, and the chordal height stays near 1·m_n.
    """
    for gear, d_a in ((report.gear1, 52.894), (report.gear2, 54.022)):
        assert gear.chordal_thickness_mm == pytest.approx(gear.tooth_thickness_normal_mm, abs=0.06)
        assert 0.9 < gear.chordal_height_mm < 1.1
        assert gear.chordal_height_mm < (d_a - 47.0) / 2.0  # sane band


def test_undercut_check_present(report) -> None:
    assert report.gear1.has_undercut is False
    assert report.gear2.has_undercut is False
    assert report.gear1.undercut_min_shift is not None


def test_effective_root_diameter_passthrough() -> None:
    data = gear_stage_from_ste(load_ste(_REF_STE))
    stage = GearStage.from_ste(data)
    rep = compute_geometry_report(stage, fillet_contour_min_radius_mm=Pair(23.852, 24.476))
    assert rep.gear1.effective_root_diameter_mm == pytest.approx(47.704, abs=1e-6)
    assert rep.gear2.effective_root_diameter_mm == pytest.approx(48.952, abs=1e-6)
    # Frühe digs below the tool root circle — the report carries both values side by side
    assert rep.gear1.effective_root_diameter_mm < rep.gear1.root_diameter_mm


# --------------------------------------------------------------------------- #
# Helical stage (DIN 21773 helical forms; z = 25/40, m_n = 2, α_n = 20°, β = 20°,
# b = 26/26, a = 69.172 — the helical reference pair of the ISO 6336 tests)      #
# --------------------------------------------------------------------------- #
def _helical_stage(helix_angle_deg: float = 20.0) -> GearStage:
    tool = ToolReferenceProfile(addendum_factor=1.25, tip_radius_factor=0.38)
    return GearStage.from_parameters(
        normal_module_mm=2.0,
        teeth=Pair(25, 40),
        profile_shift=Pair(0.0, 0.0),
        face_width_mm=Pair(26.0, 26.0),
        tool=Pair(tool, tool),
        normal_pressure_angle_deg=20.0,
        helix_angle_deg=helix_angle_deg,
        center_distance_mm=69.172,
    )


@pytest.fixture(scope="module")
def helical_report():
    return compute_geometry_report(
        _helical_stage(),
        ball_diameter_mm=Pair(3.5, 3.5),
        span_allowance_upper_mm=Pair(-0.05, -0.06),
        span_allowance_lower_mm=Pair(-0.09, -0.10),
        center_distance_allowance_mm=0.02,
    )


def test_helical_pair_values(helical_report) -> None:
    """Transverse plane + overlap: closed-form hand values (ISO 21771)."""
    p = helical_report.pair
    assert p.transverse_module_mm == pytest.approx(2.0 / math.cos(math.radians(20.0)), abs=1e-9)
    # tan α_t = tan α_n / cos β; tan β_b = tan β · cos α_t
    alpha_t = math.atan(math.tan(math.radians(20.0)) / math.cos(math.radians(20.0)))
    assert p.transverse_pressure_angle_deg == pytest.approx(math.degrees(alpha_t), abs=1e-9)
    beta_b = math.atan(math.tan(math.radians(20.0)) * math.cos(alpha_t))
    assert p.base_helix_angle_deg == pytest.approx(math.degrees(beta_b), abs=1e-9)
    # ε_β = b·sin β/(π·m_n) (ISO 21771 eq. 93), hand value
    assert p.overlap_ratio == pytest.approx(26.0 * math.sin(math.radians(20.0)) / (2.0 * math.pi))
    assert p.transverse_contact_ratio == pytest.approx(1.5266, abs=1e-4)
    # p_bt·cos β_b = p_bn (base-plane identity)
    assert p.transverse_base_pitch_mm * math.cos(beta_b) == pytest.approx(
        p.normal_base_pitch_mm, abs=1e-9
    )


def test_helical_backlash_chain(helical_report) -> None:
    """ISO 21771 Eq. 102: j_bn = j_wt·cos α_wt·cos β_b; j_bn = −ΣA_We exactly."""
    p = helical_report.pair
    assert p.backlash_normal_mm == pytest.approx(0.11, abs=1e-12)  # −(−0.05 − 0.06)
    awt = math.radians(p.working_pressure_angle_deg)
    bb = math.radians(p.base_helix_angle_deg)
    assert p.backlash_circumferential_mm * math.cos(awt) * math.cos(bb) == pytest.approx(
        p.backlash_normal_mm, abs=1e-12
    )
    # ±A_a: Δj_wt = 2·A_a·tan α_wt and Δj_bn = Δj_wt·cos α_wt·cos β_b
    d_jwt, d_jbn = p.backlash_delta_upper_mm
    assert d_jwt == pytest.approx(2.0 * 0.02 * math.tan(awt), abs=1e-12)
    assert d_jbn == pytest.approx(d_jwt * math.cos(awt) * math.cos(bb), abs=1e-12)


def test_helical_thicknesses(helical_report) -> None:
    """s_n = m_n(π/2 + 2x·tan α_n) stays the normal-plane value; s_t = s_n/cos β."""
    for g in (helical_report.gear1, helical_report.gear2):
        assert g.tooth_thickness_normal_mm == pytest.approx(math.pi, abs=1e-9)  # x = 0, m_n = 2
        assert g.tooth_thickness_transverse_mm == pytest.approx(
            math.pi / math.cos(math.radians(20.0)), abs=1e-9
        )
        # normal-section chord (DIN 21773 eq. 2) is slightly below the arc, height ≈ m_n
        assert g.chordal_thickness_mm < g.tooth_thickness_normal_mm
        assert g.chordal_thickness_mm == pytest.approx(g.tooth_thickness_normal_mm, abs=0.01)
        assert 0.95 * 2.0 < g.chordal_height_mm < 1.1 * 2.0


def test_helical_span_measurement(helical_report) -> None:
    """W_k per DIN 21773 eq. 14 (regression literals) + eq. 17 transverse projection."""
    g1, g2 = helical_report.gear1, helical_report.gear2
    assert (g1.span_teeth, g2.span_teeth) == (3, 5)  # eq. 10 auto choice
    assert (g1.span_teeth_min, g1.span_teeth_max) == (2, 4)  # eqs. 12/13
    assert g1.span_measurement_mm == pytest.approx(15.5967, abs=5e-4)
    assert g2.span_measurement_mm == pytest.approx(27.9068, abs=5e-4)
    # d_M = sqrt(d_b² + (W·cos β_b)²) at the mean allowance, inside the usable flank
    bb = math.radians(helical_report.pair.base_helix_angle_deg)
    w_mean = g1.span_measurement_mm + 0.5 * (-0.05 + -0.09)
    assert g1.span_contact_diameter_mm == pytest.approx(
        math.sqrt(g1.base_diameter_mm**2 + (w_mean * math.cos(bb)) ** 2), abs=1e-9
    )
    assert g1.root_form_diameter_mm < g1.span_contact_diameter_mm < g1.usable_tip_diameter_mm


def test_helical_ball_and_roller_measures(helical_report) -> None:
    """M_dK regression literals; §11: rollers on ODD-z helical gears sit diametrically
    opposite (M_dR = 2·M_rK > M_dK), on even z they equal the ball measure."""
    g1, g2 = helical_report.gear1, helical_report.gear2
    assert g1.two_ball_measure_mm == pytest.approx(58.0771, abs=5e-4)
    assert g2.two_ball_measure_mm == pytest.approx(90.1508, abs=5e-4)
    assert g1.two_roller_measure_mm > g1.two_ball_measure_mm  # z = 25 (odd)
    assert g1.two_roller_measure_mm == pytest.approx(58.1850, abs=5e-4)
    assert g2.two_roller_measure_mm == g2.two_ball_measure_mm  # z = 40 (even)
    # Eq. 36 consistency: M_dK = d_K·cos(π/2z) + D_M with d_K = M_dR − D_M
    d_k = g1.two_roller_measure_mm - 3.5
    assert g1.two_ball_measure_mm == pytest.approx(
        d_k * math.cos(math.pi / (2.0 * 25)) + 3.5, abs=1e-9
    )
    for g in (g1, g2):
        assert g.root_form_diameter_mm < g.ball_contact_diameter_mm < g.usable_tip_diameter_mm


def test_helical_root_and_undercut(helical_report) -> None:
    """Tool root circle and the DIN 3960 eq. 3.6.06 minimum shift with cos β."""
    g1 = helical_report.gear1
    # d_f = d − 2·(h_aP0* − x_E)·m_n, x_E = 0 here
    assert g1.root_diameter_mm == pytest.approx(g1.reference_diameter_mm - 2.0 * 1.25 * 2.0)
    alpha_t = math.atan(math.tan(math.radians(20.0)) / math.cos(math.radians(20.0)))
    h_fap0 = 1.25 - 0.38 * (1.0 - math.sin(math.radians(20.0)))
    x_min = h_fap0 - 25 * math.sin(alpha_t) ** 2 / (2.0 * math.cos(math.radians(20.0)))
    assert g1.undercut_min_shift == pytest.approx(x_min, abs=1e-9)
    assert g1.has_undercut is False
    # standard clearance: c = 0.25·m_n for h_aP0* = 1.25, x = 0, a = a_d
    assert g1.tip_clearance_mm == pytest.approx(0.5, abs=1e-3)


def test_helical_reduces_to_spur_continuously() -> None:
    """β → 0 limit: the helical branches converge to the spur values (no formula split).

    Exception BY THE NORM: the two-roller measure of an odd-z gear is discontinuous in β
    (DIN 21773 §11 — on any helical gear the rollers screw into diametrically opposite
    gaps, so M_dR jumps from M_dK to 2·M_rK), checked explicitly below.
    """
    rep0 = compute_geometry_report(_helical_stage(0.0), ball_diameter_mm=Pair(3.5, 3.5))
    rep1 = compute_geometry_report(_helical_stage(1e-6), ball_diameter_mm=Pair(3.5, 3.5))
    for attr in (
        "tooth_thickness_transverse_mm",
        "chordal_thickness_mm",
        "chordal_height_mm",
        "span_measurement_mm",
        "two_ball_measure_mm",
        "ball_contact_diameter_mm",
        "root_diameter_mm",
        "tip_tooth_thickness_mm",
        "undercut_min_shift",
    ):
        assert getattr(rep1.gear1, attr) == pytest.approx(getattr(rep0.gear1, attr), abs=1e-6), attr
    assert rep1.pair.overlap_ratio == pytest.approx(0.0, abs=1e-6)
    # the normative §11 discontinuity: spur rollers = ball measure; helical odd z = 2·M_rK
    assert rep0.gear1.two_roller_measure_mm == rep0.gear1.two_ball_measure_mm
    d_k = rep1.gear1.two_roller_measure_mm - 3.5
    assert rep1.gear1.two_ball_measure_mm == pytest.approx(
        d_k * math.cos(math.pi / (2.0 * 25)) + 3.5, abs=1e-9
    )


def test_helical_narrow_face_width_flags_span(helical_report) -> None:
    """DIN 21773 eqs. 15/16: a face width below b_Fmin makes W_k unmeasurable — noted."""
    tool = ToolReferenceProfile(addendum_factor=1.25, tip_radius_factor=0.38)
    narrow = GearStage.from_parameters(
        normal_module_mm=2.0,
        teeth=Pair(25, 40),
        profile_shift=Pair(0.0, 0.0),
        face_width_mm=Pair(6.0, 6.0),
        tool=Pair(tool, tool),
        normal_pressure_angle_deg=20.0,
        helix_angle_deg=20.0,
        center_distance_mm=69.172,
    )
    rep = compute_geometry_report(narrow)
    assert any("b_Fmin" in n for n in rep.notes)
    assert not any("b_Fmin" in n for n in helical_report.notes)  # b = 26 is wide enough


def test_report_without_allowances_has_no_backlash() -> None:
    data = gear_stage_from_ste(load_ste(_REF_STE))
    stage = GearStage.from_ste(data)
    rep = compute_geometry_report(stage)
    assert rep.pair.backlash_normal_mm is None
    assert rep.gear1.thickness_allowance_upper_mm is None
    assert rep.gear1.span_measurement_mm is not None  # nominal measures still computed
    assert rep.gear1.two_ball_measure_mm is not None
    assert math.isclose(rep.gear1.ball_diameter_mm, 1.75, abs_tol=1e-9)  # 1.75·m_n default
